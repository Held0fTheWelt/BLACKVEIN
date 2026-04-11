"""Registration / password-change input validation (DS-005 — control-flow extraction)."""

from __future__ import annotations

import re
from typing import Any, Callable, Pattern

PasswordValidator = Callable[[str], str | None]
EmailFormatValidator = Callable[[str], tuple[bool, str]]
UserLookup = Callable[[str], Any]


def create_user_validate_inputs(
    username: str,
    password: str,
    email: Any,
    *,
    require_email: bool,
    username_max_length: int,
    username_pattern: Pattern[str],
    get_user_by_username: UserLookup,
    get_user_by_email: UserLookup,
    validate_password: PasswordValidator,
    validate_email_format: EmailFormatValidator,
) -> tuple[str, str | None, str | None]:
    """Return ``(normalized_username, email_val_or_none, None)`` or ``(_, _, error_message)``."""
    username_stripped = (username or "").strip()
    if not username_stripped:
        return "", None, "Username is required"
    pw_error = validate_password(password)
    if pw_error:
        return "", None, pw_error
    if len(username_stripped) < 2:
        return "", None, "Username must be at least 2 characters"
    if len(username_stripped) > username_max_length:
        return "", None, f"Username must be at most {username_max_length} characters"
    if not username_pattern.match(username_stripped):
        return "", None, "Username contains invalid characters"
    if get_user_by_username(username_stripped):
        return "", None, "Username already taken"

    email_val: str | None = None
    if email is not None and isinstance(email, str):
        email_raw = (email or "").strip().lower()
        if email_raw:
            is_valid, result = validate_email_format(email_raw)
            if not is_valid:
                return "", None, result
            email_val = result
    if require_email:
        if not email_val:
            return "", None, "Email is required"
        if get_user_by_email(email_val):
            return "", None, "Email already registered"
    elif email_val:
        if get_user_by_email(email_val):
            return "", None, "Email already registered"

    return username_stripped, email_val, None


def change_password_validate_inputs(
    user: Any | None,
    current_password: str | None,
    new_password: str,
    *,
    check_password_hash: Callable[[str, str], bool],
    validate_password: PasswordValidator,
) -> tuple[Any | None, str | None]:
    """Return ``(user, None)`` on success path for password checks, or ``(None, error)``."""
    if not user:
        return None, "User not found"
    if not current_password:
        return None, "Current password is required"
    if not check_password_hash(user.password_hash, current_password):
        return None, "Current password is incorrect"
    pw_error = validate_password(new_password)
    if pw_error:
        return None, pw_error
    if user.is_password_in_history(new_password):
        return None, "Cannot reuse one of your last 3 passwords"
    return user, None
