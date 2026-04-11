"""Input validation for ``user_service.update_user`` (DS-005 — control-flow extraction)."""

from __future__ import annotations

from typing import Any, Callable, Pattern

from app.models import User

EmailFormatValidator = Callable[[str], tuple[bool, str]]
UserLookup = Callable[[str], Any]
RoleLookup = Callable[[str], Any | None]


def update_user_build_patch(
    *,
    username: str | None,
    email: str | None,
    role: str | None,
    role_level: int | None,
    preferred_language: str | None,
    current_user_id: int,
    username_max_length: int,
    username_pattern: Pattern[str],
    get_user_by_username: UserLookup,
    get_user_by_email: UserLookup,
    validate_email_format: EmailFormatValidator,
    get_role_by_name: RoleLookup,
    supported_languages: list | tuple,
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Validate optional ``update_user`` fields for ``current_user_id``.

    Returns ``(patch, None)`` where ``patch`` keys are ``username``, ``email``, ``role_id``,
    ``role_level``, ``preferred_language`` — only keys for arguments that were not ``None``.
    """
    patch: dict[str, Any] = {}

    if username is not None:
        u = (username or "").strip()
        if not u:
            return None, "Username cannot be empty"
        if len(u) < 2:
            return None, "Username must be at least 2 characters"
        if len(u) > username_max_length:
            return None, f"Username must be at most {username_max_length} characters"
        if not username_pattern.match(u):
            return None, "Username contains invalid characters"
        other = get_user_by_username(u)
        if other and other.id != current_user_id:
            return None, "Username already taken"
        patch["username"] = u

    if email is not None:
        email_val: str | None = None
        if email:
            email_raw = (email or "").strip().lower()
            if email_raw:
                is_valid, result = validate_email_format(email_raw)
                if not is_valid:
                    return None, result
                email_val = result
        if email_val is not None:
            other = get_user_by_email(email_val)
            if other and other.id != current_user_id:
                return None, "Email already registered"
        patch["email"] = email_val

    if role is not None:
        role_name = (role or "").strip().lower() or User.ROLE_USER
        role_obj = get_role_by_name(role_name)
        if not role_obj:
            return None, "Invalid role"
        patch["role_id"] = role_obj.id

    if role_level is not None:
        try:
            lvl = int(role_level)
            if lvl < 0 or lvl > 9999:
                return None, "role_level must be between 0 and 9999"
            patch["role_level"] = lvl
        except (TypeError, ValueError):
            return None, "role_level must be an integer"

    if preferred_language is not None:
        val = (preferred_language or "").strip().lower() or None
        if val is not None and val not in supported_languages:
            return None, "Unsupported language"
        patch["preferred_language"] = val

    return patch, None
