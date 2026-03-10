import logging

from flask import current_app, url_for
from flask_mail import Message

from app.extensions import mail

logger = logging.getLogger(__name__)


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
        logger.info("DEV: Password reset URL for %r: %s", user.username, reset_url)
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
