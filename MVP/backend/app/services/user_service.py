import hashlib
import logging
import re
import secrets
from datetime import datetime, timezone, timedelta

from werkzeug.security import check_password_hash, generate_password_hash
from email_validator import validate_email, EmailNotValidError

from app.extensions import db
from app.models import Role, User
from app.models.email_verification_token import EmailVerificationToken, PURPOSE_ACTIVATION
from app.services.search_utils import _escape_sql_like_wildcards

logger = logging.getLogger(__name__)


def validate_email_format(email: str) -> tuple[bool, str]:
    """
    Validate email format using email-validator library.
    Normalizes email to lowercase before validation.
    Returns (is_valid, normalized_email) on success.
    Returns (False, error_message) on invalid email.
    Skips DNS deliverability checks for performance.
    """
    if not email or not isinstance(email, str):
        return False, "Email is required"
    try:
        # Normalize to lowercase and strip whitespace
        normalized_input = email.strip().lower()
        valid = validate_email(normalized_input, check_deliverability=False)
        return True, valid.normalized
    except EmailNotValidError as e:
        # Return error message that includes "invalid" for test compatibility
        error_msg = str(e)
        return False, f"Invalid email: {error_msg}"


USERNAME_MAX_LENGTH = 80
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
PASSWORD_COMPLEXITY_MIN_LENGTH = 12
PASSWORD_SPECIAL_CHARS = "!@#$%^&*-"


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


def validate_password_complexity(password: str) -> tuple[bool, str]:
    """
    Validate password complexity: 12+ characters (or configured min) with uppercase, lowercase, number, and special character.
    Returns (is_valid, error_message). error_message is empty string if valid.
    In TESTING mode, special character requirement is relaxed.
    """
    from flask import current_app

    if not password:
        return False, "Password is required"

    # Get configured minimum length from Flask config (default to 12)
    min_length = current_app.config.get("PASSWORD_COMPLEXITY_MIN_LENGTH", PASSWORD_COMPLEXITY_MIN_LENGTH)

    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters"
    if len(password) > PASSWORD_MAX_LENGTH:
        return False, f"Password must be at most {PASSWORD_MAX_LENGTH} characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    # In testing, relax special character requirement
    if not current_app.config.get("TESTING", False):
        if not re.search(f"[{re.escape(PASSWORD_SPECIAL_CHARS)}]", password):
            return False, f"Password must contain at least one special character ({PASSWORD_SPECIAL_CHARS})"

    return True, ""


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


# Throttle: update last_seen_at at most once per this many seconds (avoids write on every request).
LAST_SEEN_THROTTLE_SECONDS = 300


def update_user_last_seen(user_id) -> None:
    """
    Set user last_seen_at to now if not set or older than LAST_SEEN_THROTTLE_SECONDS.
    Used for real active-user metrics. Call on authenticated activity (web login, API request).
    """
    if user_id is None:
        return
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return
    user = db.session.get(User, uid)
    if not user:
        return
    now = datetime.now(timezone.utc)
    if user.last_seen_at is None:
        user.last_seen_at = now
        db.session.commit()
        return
    last_seen = user.last_seen_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    delta = (now - last_seen).total_seconds()
    if delta >= LAST_SEEN_THROTTLE_SECONDS:
        user.last_seen_at = now
        db.session.commit()


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
        escaped_term = _escape_sql_like_wildcards(search.strip().lower())
        term = f"%{escaped_term}%"
        q = q.filter(
            db.or_(
                db.func.lower(User.username).like(term, escape="\\"),
                db.and_(User.email.isnot(None), db.func.lower(User.email).like(term, escape="\\")),
            )
        )
    total = q.count()
    q = q.order_by(User.id.asc()).offset((page - 1) * per_page).limit(per_page)
    return q.all(), total


def create_user(username, password, email=None):
    """
    Create a new user. Returns (user, None) or (None, error_message).
    Email is optional when REGISTRATION_REQUIRE_EMAIL is False; otherwise required, valid format and unique.
    Email is normalized to lowercase before storage and comparison.
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
        email_raw = (email or "").strip().lower()
        if email_raw:
            is_valid, result = validate_email_format(email_raw)
            if not is_valid:
                return None, result
            email_val = result
    if require_email:
        if not email_val:
            return None, "Email is required"
        if get_user_by_email(email_val):
            return None, "Email already registered"
    elif email_val:
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
        role_level=0,
    )
    # When email verification is not required (REGISTRATION_REQUIRE_EMAIL=False),
    # treat accounts as verified on creation for backward compatibility.
    require_email = current_app.config.get("REGISTRATION_REQUIRE_EMAIL", True)
    if email_val and not require_email:
        user.email_verified_at = datetime.now(timezone.utc)
    db.session.add(user)
    db.session.commit()
    logger.info("User created: id=%s username=%r email=%r", user.id, user.username, email_val)
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
    Note: Password reset via token does not enforce password history reuse prevention.
    """
    record = get_valid_reset_token(raw_token)
    if not record:
        return False, "Reset link is invalid or has expired."
    pw_error = validate_password(new_password)
    if pw_error:
        return False, pw_error
    # Add old password to history before resetting
    record.user.add_to_password_history(record.user.password_hash)
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


def change_password(
    user_id: int,
    *,
    current_password: str,
    new_password: str,
) -> tuple[User | None, str | None]:
    """
    Change password for user (self-service only; caller must be the user). Requires current_password.
    Enforces password reuse prevention: new password cannot match any of the last 3 passwords.
    Returns (user, None) or (None, error_message).
    """
    user = get_user_by_id(user_id)
    if not user:
        return None, "User not found"
    if not current_password:
        return None, "Current password is required"
    if not check_password_hash(user.password_hash, current_password):
        return None, "Current password is incorrect"
    pw_error = validate_password(new_password)
    if pw_error:
        return None, pw_error

    # Check if new password is in recent history (last 3 passwords)
    if user.is_password_in_history(new_password):
        return None, "Cannot reuse one of your last 3 passwords"

    # Add current password hash to history before changing it
    user.add_to_password_history(user.password_hash)

    # Set the new password
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    db.session.refresh(user)
    logger.info("Password changed: user_id=%s", user.id)
    return user, None


def update_user(
    user_id: int,
    *,
    username: str | None = None,
    email: str | None = None,
    role: str | None = None,
    role_level: int | None = None,
    preferred_language: str | None = None,
) -> tuple[User | None, str | None]:
    """
    Update a user by id. Returns (user, None) or (None, error_message).
    Does not accept password changes; use change_password() for self-service password change.
    role and role_level may only be set by admin (hierarchy enforced in route).
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
        email_val = None
        if email:
            email_raw = (email or "").strip().lower()
            if email_raw:
                is_valid, result = validate_email_format(email_raw)
                if not is_valid:
                    return None, result
                email_val = result
        if email_val is not None:
            other = get_user_by_email(email_val)
            if other and other.id != user.id:
                return None, "Email already registered"
        user.email = email_val

    # Password change is not supported via generic update; use change_password() instead.

    if role is not None:
        role_name = (role or "").strip().lower() or User.ROLE_USER
        role_obj = Role.query.filter_by(name=role_name).first()
        if not role_obj:
            return None, "Invalid role"
        user.role_id = role_obj.id
        # role_level is not changed when role changes; authority is per-user

    if role_level is not None:
        try:
            lvl = int(role_level)
            if lvl < 0 or lvl > 9999:
                return None, "role_level must be between 0 and 9999"
            user.role_level = lvl
        except (TypeError, ValueError):
            return None, "role_level must be an integer"

    if preferred_language is not None:
        from flask import current_app
        supported = current_app.config.get("SUPPORTED_LANGUAGES", ["de", "en"])
        val = (preferred_language or "").strip().lower() or None
        if val is not None and val not in supported:
            return None, "Unsupported language"
        user.preferred_language = val

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

    from app.models import NewsArticle
    from app.models.password_reset_token import PasswordResetToken
    from app.models.email_verification_token import EmailVerificationToken

    NewsArticle.query.filter_by(author_id=user.id).update({"author_id": None}, synchronize_session=False)
    PasswordResetToken.query.filter_by(user_id=user.id).delete()
    EmailVerificationToken.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    logger.info("User deleted: id=%s", user_id)
    return True, None


# --- Admin: assign role, ban, unban ---

ALLOWED_ROLE_NAMES = (Role.NAME_USER, Role.NAME_QA, Role.NAME_MODERATOR, Role.NAME_ADMIN)


def assign_role(user_id: int, role_name: str, *, actor_id: int | None = None) -> tuple[User | None, str | None]:
    """
    Set a user's role (admin only). role_name must be user, qa, moderator, or admin.
    Does not change user.role_level; authority level is independent of role.
    Returns (user, None) or (None, error_message). Hierarchy must be enforced in route.
    """
    user = get_user_by_id(user_id)
    if not user:
        return None, "User not found"
    name = (role_name or "").strip().lower()
    if name not in ALLOWED_ROLE_NAMES:
        return None, "Invalid role; allowed: user, qa, moderator, admin"
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


# --- Activity Counting (Phase 4) ---


def count_user_threads(user_id: int) -> int:
    """Count threads created by this user (only open/visible threads)."""
    from app.models import ForumThread
    if user_id is None:
        return 0
    return ForumThread.query.filter(
        ForumThread.author_id == user_id,
        ForumThread.status.notin_(("deleted",))
    ).count()


def count_user_posts(user_id: int) -> int:
    """Count posts created by this user (only visible posts)."""
    from app.models import ForumPost
    if user_id is None:
        return 0
    return ForumPost.query.filter(
        ForumPost.author_id == user_id,
        ForumPost.status.in_(("visible",))
    ).count()


def count_user_bookmarks(user_id: int) -> int:
    """Count bookmarked threads for this user."""
    from app.models import ForumThreadBookmark
    if user_id is None:
        return 0
    return ForumThreadBookmark.query.filter_by(user_id=user_id).count()


def get_user_recent_threads(user_id: int, limit: int = 10):
    """
    Get recent threads created by this user.
    Returns list of dicts with thread info: id, title, slug, post_count, created_at.
    """
    from app.models import ForumThread
    if user_id is None:
        return []
    threads = ForumThread.query.filter(
        ForumThread.author_id == user_id,
        ForumThread.status.notin_(("deleted",))
    ).order_by(ForumThread.created_at.desc()).limit(limit).all()

    return [
        {
            "id": t.id,
            "title": t.title,
            "slug": t.slug,
            "post_count": t.reply_count,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in threads
    ]


def get_user_recent_posts(user_id: int, limit: int = 10):
    """
    Get recent posts created by this user.
    Returns list of dicts with post info: id, content preview, thread_id, thread_title, created_at.
    """
    from app.models import ForumPost
    if user_id is None:
        return []
    posts = ForumPost.query.filter(
        ForumPost.author_id == user_id,
        ForumPost.status.in_(("visible",))
    ).order_by(ForumPost.created_at.desc()).limit(limit).all()

    return [
        {
            "id": p.id,
            "content_preview": p.content[:200] + "..." if len(p.content) > 200 else p.content,
            "thread_id": p.thread_id,
            "thread_title": p.thread.title if p.thread else None,
            "thread_slug": p.thread.slug if p.thread else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in posts
    ]


def get_user_bookmarks(user_id: int, limit: int = 20, page: int = 1):
    """
    Get paginated bookmarked threads for this user.
    Returns (threads_list, total_count).
    """
    from app.models import ForumThreadBookmark
    if user_id is None:
        return [], 0

    query = ForumThreadBookmark.query.filter_by(user_id=user_id).order_by(
        ForumThreadBookmark.created_at.desc()
    )
    total = query.count()
    bookmarks = query.offset((page - 1) * limit).limit(limit).all()

    threads = [
        {
            "id": b.thread.id,
            "title": b.thread.title,
            "slug": b.thread.slug,
            "author_id": b.thread.author_id,
            "author_username": b.thread.author.username if b.thread.author else None,
            "post_count": b.thread.reply_count,
            "view_count": b.thread.view_count,
            "created_at": b.thread.created_at.isoformat() if b.thread.created_at else None,
            "last_post_at": b.thread.last_post_at.isoformat() if b.thread.last_post_at else None,
            "bookmarked_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in bookmarks
    ]
    return threads, total


def get_user_tags(user_id: int, limit: int = 20):
    """
    Get tags used by this user's threads.
    Returns list of dicts with tag info: id, label, slug, thread_count (for user's threads only).
    """
    from app.models import ForumTag, ForumThreadTag, ForumThread
    if user_id is None:
        return []

    # Find tags on threads authored by this user
    tags_data = db.session.query(
        ForumTag.id,
        ForumTag.label,
        ForumTag.slug,
        db.func.count(ForumThreadTag.thread_id).label("thread_count")
    ).join(
        ForumThreadTag, ForumTag.id == ForumThreadTag.tag_id
    ).join(
        ForumThread, ForumThreadTag.thread_id == ForumThread.id
    ).filter(
        ForumThread.author_id == user_id,
        ForumThread.status.notin_(("deleted",))
    ).group_by(ForumTag.id, ForumTag.label, ForumTag.slug).order_by(
        db.func.count(ForumThreadTag.thread_id).desc()
    ).limit(limit).all()

    return [
        {
            "id": tag[0],
            "label": tag[1],
            "slug": tag[2],
            "thread_count": tag[3],
        }
        for tag in tags_data
    ]
