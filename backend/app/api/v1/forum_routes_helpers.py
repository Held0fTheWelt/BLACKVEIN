"""Shared helpers for forum_* route modules (no route registrations)."""

from __future__ import annotations

from flask import jsonify

from app.auth.permissions import get_current_user


def _parse_int(value, default, min_val=None, max_val=None):
    if value is None:
        return default
    try:
        n = int(value)
        if min_val is not None and n < min_val:
            return default
        if max_val is not None and n > max_val:
            return max_val
        return n
    except (TypeError, ValueError):
        return default


def _current_user_optional():
    """Return current user object or None (for optional JWT endpoints)."""
    try:
        return get_current_user()
    except Exception:
        return None


def _validate_content_length(content, min_len=2, max_len=50000):
    if not isinstance(content, str):
        return False, "Content must be a string"
    trimmed = content.strip()
    if len(trimmed) < min_len:
        return False, f"Content must be at least {min_len} characters"
    if len(trimmed) > max_len:
        return False, f"Content must not exceed {max_len} characters"
    return True, None


def _validate_title_length(title, min_len=5, max_len=500):
    if not isinstance(title, str):
        return False, "Title must be a string"
    trimmed = title.strip()
    if len(trimmed) < min_len:
        return False, f"Title must be at least {min_len} characters"
    if len(trimmed) > max_len:
        return False, f"Title must not exceed {max_len} characters"
    return True, None


def _validate_category_title_length(title, min_len=5, max_len=200):
    if not isinstance(title, str):
        return False, "Title must be a string"
    trimmed = title.strip()
    if len(trimmed) < min_len:
        return False, f"Title must be at least {min_len} characters"
    if len(trimmed) > max_len:
        return False, f"Title must not exceed {max_len} characters"
    return True, None


def _require_user():
    """Require a logged-in, non-banned user."""
    user = get_current_user()
    if not user:
        return None, (jsonify({"error": "Authorization required"}), 401)
    if getattr(user, "is_banned", False):
        return None, (jsonify({"error": "Account is restricted."}), 403)
    return user, None
