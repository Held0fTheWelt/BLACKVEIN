"""DB + logging branches after ``verify_user`` (success vs failed credential path)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, NamedTuple

from flask import request
from sqlalchemy import update

from app.api.v1.auth_login_phases import banned_user_error, unverified_email_error
from app.extensions import db
from app.models import User
from app.services import log_activity
from app.services.identity.token_service import generate_tokens

logger = logging.getLogger(__name__)


class LoginHttpResult(NamedTuple):
    body: dict
    status: int


def run_verified_user_login(
    authenticated_user: Any,
    *,
    require_email_verification_for_login: bool,
) -> LoginHttpResult:
    """Reset failed attempts, apply post-auth gates, return JSON body + HTTP status."""
    db.session.execute(
        update(User)
        .where(User.id == authenticated_user.id)
        .values(failed_login_attempts=0, locked_until=None)
    )
    db.session.commit()

    user = db.session.get(User, authenticated_user.id)

    banned = banned_user_error(user)
    if banned is not None:
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
        return LoginHttpResult(banned.body, banned.status)

    unverified = unverified_email_error(
        user,
        require_email_verification_for_login=require_email_verification_for_login,
    )
    if unverified is not None:
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
        return LoginHttpResult(unverified.body, unverified.status)

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
    tokens = generate_tokens(user.id)
    return LoginHttpResult(
        {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "expires_at": tokens["expires_at"],
            "expires_in": tokens["expires_in"],
            "refresh_expires_at": tokens["refresh_expires_at"],
            "user": user.to_dict(include_email=True),
        },
        200,
    )


def run_failed_credentials_login(user: Any | None, *, username: str) -> LoginHttpResult:
    """Increment failed attempts, maybe lock, log, return 401."""
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
    return LoginHttpResult({"error": "Invalid username or password"}, 401)
