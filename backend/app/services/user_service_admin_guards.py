"""Admin-path validation for ``assign_role`` / ``ban_user`` (DS-005 — control-flow extraction)."""

from __future__ import annotations

from typing import Any, Callable

from app.models import Role

ALLOWED_ASSIGN_ROLE_NAMES = (
    Role.NAME_USER,
    Role.NAME_QA,
    Role.NAME_MODERATOR,
    Role.NAME_ADMIN,
)

RoleLookup = Callable[[str], Any | None]


def assign_role_build_patch(
    role_name: str,
    *,
    get_role_by_name: RoleLookup,
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Validate ``role_name`` against allowed admin-assignable roles.

    Returns ``({"role_id": int, "role_name": str}, None)`` or ``(None, error_message)``.
    """
    name = (role_name or "").strip().lower()
    if name not in ALLOWED_ASSIGN_ROLE_NAMES:
        return None, "Invalid role; allowed: user, qa, moderator, admin"
    role_obj = get_role_by_name(name)
    if not role_obj:
        return None, "Invalid role"
    return {"role_id": role_obj.id, "role_name": name}, None


def ban_user_validate_actor(*, user_id: int, actor_id: int | None) -> str | None:
    """Return an error message if the ban must be rejected, else ``None``."""
    if actor_id is not None and actor_id == user_id:
        return "Cannot ban yourself"
    return None


def normalize_ban_reason(reason: str) -> str | None:
    """Strip ban reason to ``None`` if empty (used when ``reason`` was explicitly passed)."""
    return (reason or "").strip() or None
