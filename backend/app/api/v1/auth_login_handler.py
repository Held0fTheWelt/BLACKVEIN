"""Auth login flow — credential check, lockout, tokens (DS-050)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from flask import jsonify, request
from sqlalchemy import update

from app.extensions import db
from app.models import User
from app.services import log_activity, verify_user
from app.services.token_service import generate_tokens
from app.services.user_service import get_user_by_username

logger = logging.getLogger(__name__)


def execute_auth_login():
    """Authenticate and return JWT access_token and user info (same as ``auth_routes.login``)."""
    from flask import current_app

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    username = (data.get("username") or "").strip()
    password = data.get("password")
    if not username or password is None:
        return jsonify({"error": "Username and password are required"}), 400

    user = get_user_by_username(username)

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

    authenticated_user = verify_user(username, password)
    if authenticated_user:
        db.session.execute(
            update(User)
            .where(User.id == authenticated_user.id)
            .values(failed_login_attempts=0, locked_until=None)
        )
        db.session.commit()

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

    if user:
        db.session.execute(
            update(User)
            .where(User.id == user.id)
            .values(failed_login_attempts=User.failed_login_attempts + 1)
        )
        db.session.commit()

        user = db.session.get(User, user.id)

        if user.failed_login_attempts >= 5:
            db.session.execute(
                update(User)
                .where(User.id == user.id)
                .values(locked_until=datetime.now(timezone.utc) + timedelta(minutes=15))
            )
            db.session.commit()
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
