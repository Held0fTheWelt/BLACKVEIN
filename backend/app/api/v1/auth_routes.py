import logging

from flask import current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.extensions import limiter
from app.services import create_user, log_activity, verify_user
from app.services.user_service import create_email_verification_token
from app.services.mail_service import send_verification_email

logger = logging.getLogger(__name__)


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
    email = (email_raw or "").strip().lower() if email_raw is not None else ""
    require_email = current_app.config.get("REGISTRATION_REQUIRE_EMAIL", False)
    if require_email and not email:
        return jsonify({"error": "Email is required"}), 400
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
    user = verify_user(username, password)
    if user:
        if getattr(user, "is_banned", False):
            log_activity(
                actor=user,
                category="auth",
                action="login_blocked_banned",
                status="warning",
                message="API login attempted by banned user",
                route=request.path,
                method=request.method,
                tags=["api"],
            )
            return jsonify({"error": "Account is restricted."}), 403
        if (
            current_app.config.get("EMAIL_VERIFICATION_ENABLED", False)
            and user.email
            and user.email_verified_at is None
        ):
            log_activity(
                actor=user,
                category="auth",
                action="login_blocked_unverified",
                status="warning",
                message="API login attempted before email verification",
                route=request.path,
                method=request.method,
                tags=["api"],
            )
            return jsonify({"error": "Email not verified."}), 403
        log_activity(
            actor=user,
            category="auth",
            action="login",
            status="success",
            message="API login successful",
            route=request.path,
            method=request.method,
            tags=["api"],
        )
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            "access_token": access_token,
            "user": user.to_dict(include_email=True),
        }), 200
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
