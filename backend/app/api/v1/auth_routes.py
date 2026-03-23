import logging
import time
from datetime import datetime, timedelta, timezone

from flask import current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, get_jwt, jwt_required
from sqlalchemy import update

from app.api.v1 import api_v1_bp
from app.extensions import limiter, db
from app.models import User
from app.services import create_user, log_activity, verify_user
from app.services.token_service import generate_tokens, refresh_access_token, revoke_user_tokens
from app.services.user_service import (
    create_email_verification_token,
    get_user_by_username,
    validate_password_complexity,
    create_password_reset_token,
    reset_password_with_token,
    get_user_by_email,
    validate_email_format,
)
from app.services.mail_service import send_verification_email, send_password_reset_email
from app.utils.error_handler import log_full_error, ERROR_MESSAGES

logger = logging.getLogger(__name__)

# Constant-time delay (milliseconds) to prevent timing-based email enumeration attacks
CONSTANT_TIME_DELAY_SECONDS = 0.2


@api_v1_bp.route("/auth/register", methods=["POST"])
@limiter.limit("10 per minute")
def register():
    """Register a new user; return 201 with id and username or error."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    username = (data.get("username") or "").strip()
    password = data.get("password")
    email_raw = data.get("email")
    # Normalize email to lowercase and strip whitespace before any operations
    email = (email_raw or "").strip().lower() if email_raw is not None else ""
    require_email = current_app.config.get("REGISTRATION_REQUIRE_EMAIL", False)
    if require_email and not email:
        return jsonify({"error": "Email is required"}), 400
    # Validate password complexity
    is_valid, error_msg = validate_password_complexity(password)
    if not is_valid:
        return jsonify({"error": error_msg, "code": "PASSWORD_WEAK"}), 400
    user, err = create_user(username, password, email or None)
    if err:
        status = 409 if err in ("Username already taken", "Email already registered") else 400
        return jsonify({"error": err}), status
    log_activity(
        actor=user,
        category="auth",
        action="register",
        status="success",
        message="API registration successful",
        route=request.path,
        method=request.method,
        tags=["api"],
    )
    if user.email:
        ttl = current_app.config.get("EMAIL_VERIFICATION_TTL_HOURS", 24)
        raw_token = create_email_verification_token(user, ttl_hours=ttl)
        send_verification_email(user, raw_token)
        log_activity(
            actor=user,
            category="auth",
            action="verification_email_sent",
            status="success",
            message="Verification email sent",
            route=request.path,
            method=request.method,
            tags=["api", "email"],
        )
    return jsonify({"id": user.id, "username": user.username}), 201


@api_v1_bp.route("/auth/login", methods=["POST"])
@limiter.limit("20 per minute")
def login():
    """Authenticate and return JWT access_token and user info."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    username = (data.get("username") or "").strip()
    password = data.get("password")
    if not username or password is None:
        return jsonify({"error": "Username and password are required"}), 400

    # Get user by username
    user = get_user_by_username(username)

    # Check if account is locked
    if user and user.locked_until:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > datetime.now(timezone.utc):
            log_activity(
                actor=user,
                category="auth",
                action="login_blocked_locked",
                status="warning",
                message="API login attempted for locked account",
                route=request.path,
                method=request.method,
                tags=["api"],
            )
            return jsonify({"error": "Account temporarily locked. Try again in 15 minutes."}), 429

    # Verify credentials
    authenticated_user = verify_user(username, password)
    if authenticated_user:
        # Success: reset counter and lock timestamp using atomic update
        # This prevents race conditions in multi-threaded/multi-process environments
        db.session.execute(
            update(User)
            .where(User.id == authenticated_user.id)
            .values(failed_login_attempts=0, locked_until=None)
        )
        db.session.commit()

        # Refresh user object from database to get updated values
        authenticated_user = db.session.get(User, authenticated_user.id)

        if getattr(authenticated_user, "is_banned", False):
            log_activity(
                actor=authenticated_user,
                category="auth",
                action="login_blocked_banned",
                status="warning",
                message="API login attempted by banned user",
                route=request.path,
                method=request.method,
                tags=["api"],
            )
            return jsonify({"error": "Account is restricted."}), 403
        # Check email verification if REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN is enabled
        # This enforces verification in production but allows it in dev/testing for easier testing
        if (
            current_app.config.get("REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN", True)
            and authenticated_user.email
            and authenticated_user.email_verified_at is None
        ):
            log_activity(
                actor=authenticated_user,
                category="auth",
                action="login_blocked_unverified",
                status="warning",
                message="API login attempted before email verification",
                route=request.path,
                method=request.method,
                tags=["api"],
            )
            return jsonify({
                "error": "Please verify your email before logging in",
                "code": "EMAIL_NOT_VERIFIED"
            }), 403
        log_activity(
            actor=authenticated_user,
            category="auth",
            action="login",
            status="success",
            message="API login successful",
            route=request.path,
            method=request.method,
            tags=["api"],
        )
        tokens = generate_tokens(authenticated_user.id)
        return jsonify({
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_at": tokens["expires_at"],
            "expires_in": tokens["expires_in"],
            "refresh_expires_at": tokens["refresh_expires_at"],
            "user": authenticated_user.to_dict(include_email=True),
        }), 200

    # Failure: increment counter atomically using database UPDATE with WHERE
    # This ensures that even with concurrent requests, the counter is incremented exactly once
    # and account lockout is triggered atomically without race conditions
    if user:
        # Use atomic UPDATE to increment counter
        db.session.execute(
            update(User)
            .where(User.id == user.id)
            .values(failed_login_attempts=User.failed_login_attempts + 1)
        )
        db.session.commit()

        # Refresh user object to get updated counter value
        user = db.session.get(User, user.id)

        # Check if we've reached the lockout threshold and lock atomically in same transaction
        if user.failed_login_attempts >= 5:
            # Lock the account atomically
            db.session.execute(
                update(User)
                .where(User.id == user.id)
                .values(locked_until=datetime.now(timezone.utc) + timedelta(minutes=15))
            )
            db.session.commit()
            # Refresh to get the updated locked_until time
            user = db.session.get(User, user.id)

        log_activity(
            actor=user,
            category="auth",
            action="login_failed",
            status="warning",
            message=f"Failed login attempt ({user.failed_login_attempts} total)",
            route=request.path,
            method=request.method,
            tags=["api"],
        )
    else:
        log_activity(
            actor=None,
            category="auth",
            action="login",
            status="error",
            message="Invalid username or password",
            route=request.path,
            method=request.method,
            tags=["api"],
            metadata={"username_provided": bool(username)},
        )
    logger.warning("API login 401 for username=%r", username)
    return jsonify({"error": "Invalid username or password"}), 401


@api_v1_bp.route("/auth/resend-verification", methods=["POST"])
@limiter.limit("5 per minute")
def resend_verification():
    """Resend email verification link to user by email address."""
    # Start timing to implement constant-time response (prevents email enumeration)
    start_time = time.time()

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    email_raw = data.get("email")
    if not email_raw:
        return jsonify({"error": "Email is required"}), 400
    # Validate email format
    is_valid, email = validate_email_format(email_raw)
    if not is_valid:
        # Apply constant-time delay for invalid emails too (defense in depth)
        elapsed = time.time() - start_time
        delay_needed = CONSTANT_TIME_DELAY_SECONDS - elapsed
        if delay_needed > 0:
            time.sleep(delay_needed)
        return jsonify({"error": "Invalid email format"}), 400
    user = db.session.execute(
        db.select(User).filter(db.func.lower(User.email) == email)
    ).scalar_one_or_none()
    if not user:
        # Apply constant-time delay before responding (prevents timing-based email enumeration)
        elapsed = time.time() - start_time
        delay_needed = CONSTANT_TIME_DELAY_SECONDS - elapsed
        if delay_needed > 0:
            time.sleep(delay_needed)
        # Return success anyway to prevent email enumeration
        return jsonify({"message": "If the email exists, a verification link has been sent"}), 200
    if user.email_verified_at is not None:
        # Apply constant-time delay before responding
        elapsed = time.time() - start_time
        delay_needed = CONSTANT_TIME_DELAY_SECONDS - elapsed
        if delay_needed > 0:
            time.sleep(delay_needed)
        # User is already verified
        return jsonify({"message": "This email is already verified"}), 200
    ttl = current_app.config.get("EMAIL_VERIFICATION_TTL_HOURS", 24)
    raw_token = create_email_verification_token(user, ttl_hours=ttl)
    send_verification_email(user, raw_token)
    log_activity(
        actor=user,
        category="auth",
        action="verification_email_resent",
        status="success",
        message="Verification email resent",
        route=request.path,
        method=request.method,
        tags=["api", "email"],
    )
    # Apply constant-time delay before responding
    elapsed = time.time() - start_time
    delay_needed = CONSTANT_TIME_DELAY_SECONDS - elapsed
    if delay_needed > 0:
        time.sleep(delay_needed)
    return jsonify({"message": "Verification email sent"}), 200


@api_v1_bp.route("/auth/me", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def me():
    """Return current user from JWT. Banned users receive 403."""
    from app.models import User
    from app.extensions import db
    uid = get_jwt_identity()
    user = db.session.get(User, int(uid))
    if user is None:
        return jsonify({"error": "User not found"}), 404
    if getattr(user, "is_banned", False):
        return jsonify({"error": "Account is restricted."}), 403
    from app.auth.feature_registry import FEATURE_IDS, user_can_access_feature
    allowed = [fid for fid in FEATURE_IDS if user_can_access_feature(user, fid)]
    out = user.to_dict(include_email=True, include_areas=True)
    out["allowed_features"] = allowed
    return jsonify(out), 200


@api_v1_bp.route("/auth/logout", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
def logout():
    """Logout user by revoking their JWT token and all refresh tokens."""
    from app.models import TokenBlacklist

    uid = get_jwt_identity()
    user = db.session.get(User, int(uid))
    jwt_payload = get_jwt()
    jti = jwt_payload.get("jti")

    # Calculate token expiration time for blacklist cleanup
    expires_at = None
    if "exp" in jwt_payload:
        expires_at = datetime.fromtimestamp(jwt_payload["exp"], tz=timezone.utc)

    # Add current access token to blacklist
    TokenBlacklist.add(jti=jti, user_id=int(uid), expires_at=expires_at)

    # Revoke all refresh tokens for the user
    revoke_user_tokens(int(uid))

    log_activity(
        actor=user,
        category="auth",
        action="logout",
        status="success",
        message="API logout successful",
        route=request.path,
        method=request.method,
        tags=["api"],
    )

    return jsonify({"message": "Logged out successfully"}), 200


@api_v1_bp.route("/auth/forgot-password", methods=["POST"])
@limiter.limit("5 per hour", key_func=lambda: request.json.get("email") if request.json else "")
def forgot_password():
    """Request a password reset link by email address.

    Rate limited to 5 attempts per hour per email to prevent brute force attacks.
    Uses email as rate limit key to prevent enumeration across accounts.
    """
    # Start timing to implement constant-time response (prevents email enumeration)
    start_time = time.time()

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    email_raw = data.get("email")
    if not email_raw:
        return jsonify({"error": "Email is required"}), 400
    # Validate email format
    is_valid, email = validate_email_format(email_raw)
    if not is_valid:
        # Apply constant-time delay for invalid emails too (defense in depth)
        elapsed = time.time() - start_time
        delay_needed = CONSTANT_TIME_DELAY_SECONDS - elapsed
        if delay_needed > 0:
            time.sleep(delay_needed)
        return jsonify({"error": "Invalid email format"}), 400
    user = get_user_by_email(email)
    if not user:
        # Apply constant-time delay before responding (prevents timing-based email enumeration)
        elapsed = time.time() - start_time
        delay_needed = CONSTANT_TIME_DELAY_SECONDS - elapsed
        if delay_needed > 0:
            time.sleep(delay_needed)
        # Return success anyway to prevent email enumeration
        return jsonify({"message": "If the email exists, a password reset link has been sent"}), 200
    # Create reset token and send email
    raw_token = create_password_reset_token(user)
    send_password_reset_email(user, raw_token)
    log_activity(
        actor=user,
        category="auth",
        action="password_reset_requested",
        status="success",
        message="Password reset email sent",
        route=request.path,
        method=request.method,
        tags=["api", "email"],
    )
    # Apply constant-time delay before responding
    elapsed = time.time() - start_time
    delay_needed = CONSTANT_TIME_DELAY_SECONDS - elapsed
    if delay_needed > 0:
        time.sleep(delay_needed)
    return jsonify({"message": "If the email exists, a password reset link has been sent"}), 200


@api_v1_bp.route("/auth/reset-password", methods=["POST"])
@limiter.limit("5 per hour")
def reset_password():
    """Reset password using a valid reset token.

    Rate limited to 5 attempts per hour per IP to prevent brute force token enumeration.
    Tokens are one-time use and expire after 60 minutes.
    Failed attempts (invalid/expired token) also consume rate limit quota.
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    token = data.get("token")
    new_password = data.get("new_password")
    if not token:
        return jsonify({"error": "Reset token is required"}), 400
    if not new_password:
        return jsonify({"error": "new_password is required"}), 400
    # Validate password complexity
    is_valid, error_msg = validate_password_complexity(new_password)
    if not is_valid:
        return jsonify({"error": error_msg, "code": "PASSWORD_WEAK"}), 400
    # Reset the password
    ok, err = reset_password_with_token(token, new_password)
    if not ok:
        return jsonify({"error": err or "Reset link is invalid or has expired."}), 400
    log_activity(
        actor=None,
        category="auth",
        action="password_reset_completed",
        status="success",
        message="Password reset completed",
        route=request.path,
        method=request.method,
        tags=["api"],
    )
    return jsonify({"message": "Password reset successfully"}), 200


@api_v1_bp.route("/auth/refresh", methods=["POST"])
@limiter.limit("10 per minute")
def refresh():
    """Refresh access token using a valid refresh token.

    Accepts a refresh token in the Authorization header and returns
    a new access token and new refresh token.

    Request:
        Authorization: Bearer <refresh_token>

    Response:
        {
            "access_token": "<new_access_token>",
            "refresh_token": "<new_refresh_token>",
            "message": "Token refreshed successfully"
        }

    Returns:
        200: Successfully refreshed tokens
        401: Refresh token is invalid or expired
        403: Refresh token is revoked
    """
    from flask_jwt_extended import decode_token

    # Manual JWT extraction and validation
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header.split(" ", 1)[1]

    try:
        jwt_payload = decode_token(token)
    except Exception as e:
        log_full_error(e, "Failed to decode refresh token", route=request.path, method=request.method)
        return jsonify({"error": ERROR_MESSAGES["invalid_token"]}), 401

    uid = jwt_payload.get("sub")
    token_type = jwt_payload.get("type", "access")
    jti = jwt_payload.get("jti")

    # Only allow refresh tokens to be used for refresh
    if token_type != "refresh":
        return jsonify({"error": "Only refresh tokens can be used for refresh endpoint"}), 401

    try:
        # Verify and refresh
        new_tokens = refresh_access_token(int(uid), jti)

        user = db.session.get(User, int(uid))
        log_activity(
            actor=user,
            category="auth",
            action="token_refresh",
            status="success",
            message="API token refresh successful",
            route=request.path,
            method=request.method,
            tags=["api"],
        )

        return jsonify({
            "access_token": new_tokens["access_token"],
            "refresh_token": new_tokens["refresh_token"],
            "expires_at": new_tokens["expires_at"],
            "expires_in": new_tokens["expires_in"],
            "refresh_expires_at": new_tokens["refresh_expires_at"],
            "message": "Token refreshed successfully",
        }), 200

    except ValueError as e:
        log_full_error(e, "Token refresh validation failed", user_id=uid, route=request.path, method=request.method)
        log_activity(
            actor=None,
            category="auth",
            action="token_refresh_failed",
            status="warning",
            message="Token refresh failed: validation error",
            route=request.path,
            method=request.method,
            tags=["api"],
            metadata={"user_id": uid},
        )
        return jsonify({"error": ERROR_MESSAGES["invalid_token"]}), 401
