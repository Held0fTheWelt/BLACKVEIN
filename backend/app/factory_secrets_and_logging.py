"""SECRET_KEY, JWT, production invariants, and logging setup (DS-042)."""

from __future__ import annotations

import logging
import secrets

from flask import Flask


def configure_app_secrets_jwt_and_logging(app: Flask) -> None:
    secret_key = app.config.get("SECRET_KEY", "")
    if not secret_key or secret_key == "change-me-in-production":
        if app.config.get("TESTING"):
            app.config["SECRET_KEY"] = "test-secret-key-for-testing"
        elif app.config.get("ENV") != "production":
            app.config["SECRET_KEY"] = secrets.token_urlsafe(32)
        else:
            raise ValueError("SECRET_KEY must be set in environment. Use .env or export.")

    jwt_secret = app.config.get("JWT_SECRET_KEY", "")

    if not jwt_secret or jwt_secret == "change-me-in-production-jwt" or len(jwt_secret.encode("utf-8")) < 32:
        if app.config.get("TESTING"):
            jwt_secret = "test-key-32-bytes-minimum-value"
            app.config["JWT_SECRET_KEY"] = jwt_secret
        elif app.config.get("ENV") != "production":
            jwt_secret = secrets.token_urlsafe(32)
            app.config["JWT_SECRET_KEY"] = jwt_secret
            app.logger.warning(
                "Generated JWT_SECRET_KEY automatically. Update .env to persist across restarts."
            )
        else:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 bytes (256 bits). "
                "Generate a strong key with: python -c 'import secrets; print(secrets.token_urlsafe(32))' "
                "and set it in your .env file."
            )

    if app.config.get("ENV") == "production":
        if not app.config.get("REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN"):
            raise ValueError(
                "SECURITY VIOLATION: Email verification MUST be enforced in production. "
                "Set REQUIRE_EMAIL_VERIFICATION_FOR_LOGIN=true in your environment. "
                "This prevents unauthorized account access and protects user accounts."
            )

    app.logger.setLevel(logging.DEBUG if (app.config.get("TESTING") or app.debug) else logging.WARNING)
    if not app.logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
        app.logger.addHandler(h)

    pkg_logger = logging.getLogger("app")
    level = logging.DEBUG if (app.config.get("TESTING") or app.debug) else logging.WARNING
    pkg_logger.setLevel(level)
    if not pkg_logger.handlers:
        ph = logging.StreamHandler()
        ph.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
        pkg_logger.addHandler(ph)

    if app.config.get("TESTING"):
        mode = "TESTING"
    elif app.config.get("MAIL_ENABLED"):
        mode = "NORMAL (MAIL_ENABLED=1)"
    else:
        mode = "DEV (MAIL_ENABLED=0)"
    _startup_msg = "Running BETTER TOMORROW Backend [mode: %s]"
    if app.testing:
        app.logger.info(_startup_msg, mode)
    else:
        app.logger.warning(_startup_msg, mode)
