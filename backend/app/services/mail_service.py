import logging

from flask import current_app, url_for
from flask_mail import Message

from app.extensions import mail

logger = logging.getLogger(__name__)


def _activation_url(raw_token: str) -> str:
    """Build activation URL from config base URL or request context."""
    base = current_app.config.get("APP_PUBLIC_BASE_URL")
    if base:
        return f"{base.rstrip('/')}/activate/{raw_token}"
    return url_for("web.activate", token=raw_token, _external=True)


def send_verification_email(user, raw_token: str) -> bool:
    """
    Send email verification (activation) link to user.email.
    If MAIL_ENABLED is False or TESTING/localhost without MAIL_USERNAME, log URL and return True.
    Returns True on success, False on send failure.
    """
    url = _activation_url(raw_token)
    if current_app.config.get("TESTING") or not current_app.config.get("MAIL_ENABLED"):
        mode = "TESTING" if current_app.config.get("TESTING") else "MAIL_ENABLED=False"
        logger.warning(
            "DEV email verification mode (%s). Activation link sent for user %r (token not logged).",
            mode,
            user.username,
        )
        return True
    try:
        msg = Message(
            subject="World of Shadows – Verify your email",
            recipients=[user.email],
            body=(
                f"Hello {user.username},\n\n"
                f"Please click the link below to verify your email and activate your account.\n\n"
                f"{url}\n\n"
                f"If you did not create an account, ignore this email.\n"
            ),
        )
        mail.send(msg)
        return True
    except Exception:
        logger.exception("Failed to send verification email to user_id=%s", user.id)
        return False


def send_password_reset_email(user, raw_token: str) -> bool:
    """
    Send password reset email to user.email.
    In TESTING mode or when MAIL_SERVER is 'localhost' with no MAIL_USERNAME:
    logs the reset URL instead of sending (dev fallback).
    Returns True on success, False on failure.
    """
    reset_url = url_for("web.reset_password", token=raw_token, _external=True)

    if current_app.config.get("TESTING") or (
        current_app.config.get("MAIL_SERVER") == "localhost"
        and not current_app.config.get("MAIL_USERNAME")
    ):
        logger.info("DEV: Password reset link sent for user %r (URL not logged).", user.username)
        return True

    try:
        msg = Message(
            subject="World of Shadows – Password reset",
            recipients=[user.email],
            body=(
                f"Hello {user.username},\n\n"
                f"Click the link below to reset your password.\n"
                f"The link expires in 60 minutes.\n\n"
                f"{reset_url}\n\n"
                f"If you did not request this, ignore this email.\n"
            ),
        )
        mail.send(msg)
        return True
    except Exception:
        logger.exception(
            "Failed to send password reset email to user_id=%s", user.id
        )
        return False
