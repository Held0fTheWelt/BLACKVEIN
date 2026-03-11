import hashlib
import logging
import re
import secrets
from datetime import datetime, timezone, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import Role, User
from app.models.email_verification_token import EmailVerificationToken, PURPOSE_ACTIVATION

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


def get_user_by_id(user_id):
    """Return User by id or None."""
    if user_id is None:
        return None
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, uid)


def list_users(page: int = 1, per_page: int = 20, search: str | None = None):
    """
    Return (list of User, total count) for paginated list.
    search: optional string to filter by username or email (case-insensitive contains).
    """
    q = User.query
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        q = q.filter(
            db.or_(
                db.func.lower(User.username).like(term),
                db.and_(User.email.isnot(None), db.func.lower(User.email).like(term)),
            )
        )
    total = q.count()
    q = q.order_by(User.id.asc()).offset((page - 1) * per_page).limit(per_page)
    return q.all(), total


def create_user(username, password, email=None):
    """
    Create a new user. Returns (user, None) or (None, error_message).
    Email is optional when REGISTRATION_REQUIRE_EMAIL is False; otherwise required, valid format and unique.
    """
    from flask import current_app
    require_email = current_app.config.get("REGISTRATION_REQUIRE_EMAIL", False)

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

    email_val = None
    if email is not None and isinstance(email, str):
        email_val = (email or "").strip().lower()
    if require_email:
        if not email_val:
            return None, "Email is required"
        if not EMAIL_BASIC_PATTERN.match(email_val):
            return None, "Invalid email format"
        if get_user_by_email(email_val):
            return None, "Email already registered"
    elif email_val:
        if not EMAIL_BASIC_PATTERN.match(email_val):
            return None, "Invalid email format"
        if get_user_by_email(email_val):
            return None, "Email already registered"

    default_role = Role.query.filter_by(name=Role.NAME_USER).first()
    if not default_role:
        return None, "Default role not found; run migrations and ensure roles are seeded."
    user = User(
        username=username,
        email=email_val,
        password_hash=generate_password_hash(password),
        role_id=default_role.id,
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


# --- Email verification (0.0.7) ---


def create_email_verification_token(user, ttl_hours: int = 24) -> str:
    """Create an activation token for user; invalidate existing ones. Return raw token."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=ttl_hours)
    invalidate_existing_verification_tokens(user, PURPOSE_ACTIVATION)
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    record = EmailVerificationToken(
        user_id=user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=expires_at,
        purpose=PURPOSE_ACTIVATION,
        sent_to_email=user.email,
    )
    db.session.add(record)
    db.session.commit()
    logger.info("Email verification token created for user_id=%s", user.id)
    return raw


def invalidate_existing_verification_tokens(user, purpose: str = PURPOSE_ACTIVATION):
    """Mark all existing verification tokens for this user/purpose as invalidated."""
    now = datetime.now(timezone.utc)
    EmailVerificationToken.query.filter_by(
        user_id=user.id, purpose=purpose
    ).filter(EmailVerificationToken.invalidated_at.is_(None)).update(
        {"invalidated_at": now}, synchronize_session=False
    )
    db.session.commit()


def get_valid_verification_token(raw_token: str, purpose: str = PURPOSE_ACTIVATION):
    """Return a usable EmailVerificationToken for the raw token and purpose, or None."""
    if not raw_token:
        return None
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    record = EmailVerificationToken.query.filter_by(
        token_hash=token_hash, purpose=purpose
    ).first()
    if record and record.is_usable:
        return record
    return None


def verify_email_with_token(raw_token: str):
    """
    Mark user as verified if token is valid. Returns (True, None) or (False, error_message).
    """
    record = get_valid_verification_token(raw_token, PURPOSE_ACTIVATION)
    if not record:
        return False, "Activation link is invalid or has expired."
    now = datetime.now(timezone.utc)
    record.user.email_verified_at = now
    record.used_at = now
    db.session.commit()
    logger.info("Email verified for user_id=%s", record.user_id)
    return True, None


# --- User CRUD (list, get, update, delete) ---


def update_user(
    user_id: int,
    *,
    username: str | None = None,
    email: str | None = None,
    new_password: str | None = None,
    role: str | None = None,
    current_password: str | None = None,
) -> tuple[User | None, str | None]:
    """
    Update a user by id. Returns (user, None) or (None, error_message).
    When changing password, pass current_password if the caller is the user themselves (verified in route).
    role may only be set by admin (enforced in route).
    """
    user = get_user_by_id(user_id)
    if not user:
        return None, "User not found"

    if username is not None:
        username = (username or "").strip()
        if not username:
            return None, "Username cannot be empty"
        if len(username) < 2:
            return None, "Username must be at least 2 characters"
        if len(username) > USERNAME_MAX_LENGTH:
            return None, f"Username must be at most {USERNAME_MAX_LENGTH} characters"
        if not USERNAME_PATTERN.match(username):
            return None, "Username contains invalid characters"
        other = get_user_by_username(username)
        if other and other.id != user.id:
            return None, "Username already taken"
        user.username = username

    if email is not None:
        email_val = (email or "").strip().lower() if email else None
        if email_val is not None:
            if not EMAIL_BASIC_PATTERN.match(email_val):
                return None, "Invalid email format"
            other = get_user_by_email(email_val)
            if other and other.id != user.id:
                return None, "Email already registered"
        user.email = email_val

    if new_password is not None:
        if current_password is not None and not check_password_hash(user.password_hash, current_password):
            return None, "Current password is incorrect"
        pw_error = validate_password(new_password)
        if pw_error:
            return None, pw_error
        user.password_hash = generate_password_hash(new_password)

    if role is not None:
        role_name = (role or "").strip().lower() or User.ROLE_USER
        role_obj = Role.query.filter_by(name=role_name).first()
        if not role_obj:
            return None, "Invalid role"
        user.role_id = role_obj.id

    db.session.commit()
    db.session.refresh(user)
    logger.info("User updated: id=%s", user.id)
    return user, None


def delete_user(user_id: int) -> tuple[bool, str | None]:
    """
    Delete a user by id. News authored by this user get author_id set to None.
    Returns (True, None) or (False, error_message).
    """
    user = get_user_by_id(user_id)
    if not user:
        return False, "User not found"

    from app.models import News
    from app.models.password_reset_token import PasswordResetToken
    from app.models.email_verification_token import EmailVerificationToken

    News.query.filter_by(author_id=user.id).update({"author_id": None}, synchronize_session=False)
    PasswordResetToken.query.filter_by(user_id=user.id).delete()
    EmailVerificationToken.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    logger.info("User deleted: id=%s", user_id)
    return True, None


# --- Admin: assign role, ban, unban ---

ALLOWED_ROLE_NAMES = (Role.NAME_USER, Role.NAME_MODERATOR, Role.NAME_ADMIN)


def assign_role(user_id: int, role_name: str, *, actor_id: int | None = None) -> tuple[User | None, str | None]:
    """
    Set a user's role (admin only). role_name must be user, moderator, or admin.
    Returns (user, None) or (None, error_message).
    actor_id: optional caller user id (e.g. to prevent self-demotion; not enforced here).
    """
    user = get_user_by_id(user_id)
    if not user:
        return None, "User not found"
    name = (role_name or "").strip().lower()
    if name not in ALLOWED_ROLE_NAMES:
        return None, "Invalid role; allowed: user, moderator, admin"
    role_obj = Role.query.filter_by(name=name).first()
    if not role_obj:
        return None, "Invalid role"
    user.role_id = role_obj.id
    db.session.commit()
    db.session.refresh(user)
    logger.info("User role assigned: user_id=%s role=%s", user_id, name)
    return user, None


def ban_user(user_id: int, reason: str | None = None, *, actor_id: int | None = None) -> tuple[User | None, str | None]:
    """
    Ban a user. Sets is_banned=True, banned_at=now, ban_reason=reason.
    Returns (user, None) or (None, error_message).
    If actor_id is set and equals user_id, returns (None, "Cannot ban yourself").
    Idempotent if already banned (updates reason if provided).
    """
    user = get_user_by_id(user_id)
    if not user:
        return None, "User not found"
    if actor_id is not None and actor_id == user_id:
        return None, "Cannot ban yourself"
    now = datetime.now(timezone.utc)
    user.is_banned = True
    user.banned_at = user.banned_at or now
    if reason is not None:
        user.ban_reason = (reason or "").strip() or None
    db.session.commit()
    db.session.refresh(user)
    logger.info("User banned: user_id=%s", user_id)
    return user, None


def unban_user(user_id: int) -> tuple[User | None, str | None]:
    """
    Remove ban from a user. Sets is_banned=False, banned_at=None, ban_reason=None.
    Returns (user, None) or (None, error_message). Idempotent if not banned.
    """
    user = get_user_by_id(user_id)
    if not user:
        return None, "User not found"
    user.is_banned = False
    user.banned_at = None
    user.ban_reason = None
    db.session.commit()
    db.session.refresh(user)
    logger.info("User unbanned: user_id=%s", user_id)
    return user, None
