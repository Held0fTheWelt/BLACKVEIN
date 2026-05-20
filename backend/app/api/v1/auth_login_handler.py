"""Auth login flow — credential check, lockout, tokens (DS-050)."""

from __future__ import annotations

from datetime import datetime, timezone

from flask import current_app, jsonify, request

from app.api.v1.auth_login_execution import (
    run_failed_credentials_login,
    run_verified_user_login,
)
from app.api.v1.auth_login_phases import (
    LoginParseError,
    locked_account_error_if_active,
    parse_login_request,
)
from app.services import log_activity, verify_user
from app.services.identity.user_service import get_user_by_username


def execute_auth_login():
    """Authenticate and return JWT access_token and user info (same as ``auth_routes.login``)."""
    parsed = parse_login_request(request.get_json(silent=True))
    if isinstance(parsed, LoginParseError):
        return jsonify(parsed.body), parsed.status

    user = get_user_by_username(parsed.username)

    lock_err = locked_account_error_if_active(
        user, now_utc=datetime.now(timezone.utc)
    )
    if lock_err is not None:
        if user:
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
        return jsonify(lock_err.body), lock_err.status

    authenticated_user = verify_user(parsed.username, parsed.password)
    if authenticated_user:
        result = run_verified_user_login(
            authenticated_user,
            require_email_verification_for_login=current_app.config.get(
                "REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN", True
            ),
        )
        return jsonify(result.body), result.status

    result = run_failed_credentials_login(user, username=parsed.username)
    return jsonify(result.body), result.status
