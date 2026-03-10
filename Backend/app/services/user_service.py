import hashlib
import logging
import re
import secrets

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User

logger = logging.getLogger(__name__)

EMAIL_BASIC_PATTERN = re.compile(r"[^@]+@[^@]+\.[^@]+")

USERNAME_MAX_LENGTH = 80
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def validate_password(password: str) -> str | None:
    """Validate password. Returns error message or None if valid."""
    if not password:
        return "Password is required"
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters"
    if len(password) > PASSWORD_MAX_LENGTH:
        return f"Password must be at most {PASSWORD_MAX_LENGTH} characters"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one digit"
    return None


def get_user_by_username(username):
    """Return User by username (case-insensitive) or None."""
    if not username or not isinstance(username, str):
        return None
    return User.query.filter(db.func.lower(User.username) == username.strip().lower()).first()


def verify_user(username, password):
    """Return User if username/password match, else None."""
    user = get_user_by_username(username)
    if user and password is not None and check_password_hash(user.password_hash, password):
        return user
    if username:
        logger.warning("Failed login attempt for username=%r", username)
    return None


def get_user_by_email(email: str):
    """Return User by email (case-insensitive) or None."""
    if not email or not isinstance(email, str):
        return None
    return User.query.filter(
        db.func.lower(User.email) == email.strip().lower()
    ).first()


def create_user(username, password, email):
    """
    Create a new user. Returns (user, None) or (None, error_message).
    Email is required; must be valid format and unique.
    """
    username = (username or "").strip()
    if not username:
        return None, "Username is required"
    pw_error = validate_password(password)
    if pw_error:
        return None, pw_error
    if len(username) < 2:
        return None, "Username must be at least 2 characters"
    if len(username) > USERNAME_MAX_LENGTH:
        return None, f"Username must be at most {USERNAME_MAX_LENGTH} characters"
    if not USERNAME_PATTERN.match(username):
        return None, "Username contains invalid characters"
    if get_user_by_username(username):
        return None, "Username already taken"

    if not email or not isinstance(email, str):
        return None, "Email is required"
    email_val = (email or "").strip().lower()
    if not email_val:
        return None, "Email is required"
    if not EMAIL_BASIC_PATTERN.match(email_val):
        return None, "Invalid email format"
    if get_user_by_email(email_val):
        return None, "Email already registered"

    user = User(
        username=username,
        email=email_val,
        password_hash=generate_password_hash(password),
        role=User.ROLE_USER,
    )
    db.session.add(user)
    db.session.commit()
    logger.info("User created: id=%s username=%r", user.id, user.username)
    return user, None


def create_password_reset_token(user) -> str:
    """Generate a reset token, store its hash, return the raw token."""
    from app.models.password_reset_token import PasswordResetToken

    PasswordResetToken.query.filter_by(user_id=user.id, used=False).delete()
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    db.session.add(PasswordResetToken(user_id=user.id, token_hash=token_hash))
    db.session.commit()
    logger.info("Password reset token created for user_id=%s", user.id)
    return raw


def get_valid_reset_token(raw_token: str):
    """Return a valid (unexpired, unused) PasswordResetToken or None."""
    from app.models.password_reset_token import PasswordResetToken

    if not raw_token:
        return None
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    record = PasswordResetToken.query.filter_by(
        token_hash=token_hash, used=False
    ).first()
    if record and not record.is_expired:
        return record
    return None


def reset_password_with_token(raw_token: str, new_password: str):
    """
    Reset password if token is valid. Returns (True, None) or (False, error).
    """
    record = get_valid_reset_token(raw_token)
    if not record:
        return False, "Reset link is invalid or has expired."
    pw_error = validate_password(new_password)
    if pw_error:
        return False, pw_error
    record.user.password_hash = generate_password_hash(new_password)
    record.used = True
    db.session.commit()
    logger.info("Password reset completed for user_id=%s", record.user_id)
    return True, None
