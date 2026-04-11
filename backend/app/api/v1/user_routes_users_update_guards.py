"""Authorization and body validation for PUT ``/users/<id>`` (DS-005 — control-flow extraction)."""

from __future__ import annotations

from typing import Any

from app.auth.feature_registry import FEATURE_MANAGE_USERS, user_can_access_feature
from app.auth.permissions import (
    admin_may_edit_target,
    current_user_is_admin,
    current_user_is_super_admin,
)
from app.models.user import SUPERADMIN_THRESHOLD

ErrorPair = tuple[dict[str, Any], int]


def user_put_authorization_error(
    current: Any | None,
    target: Any | None,
    *,
    user_id: int,
) -> ErrorPair | None:
    """Return ``(body, status)`` when the caller must reject the request; otherwise ``None``."""
    if current is None:
        return ({"error": "User not found"}, 404)
    if not target:
        return ({"error": "User not found"}, 404)
    if current.id != user_id:
        if not current_user_is_admin():
            return ({"error": "Forbidden"}, 403)
        if not user_can_access_feature(current, FEATURE_MANAGE_USERS):
            return ({"error": "Forbidden. You do not have access to this feature."}, 403)
        actor_level = getattr(current, "role_level", 0) or 0
        target_level = getattr(target, "role_level", 0) or 0
        if not admin_may_edit_target(actor_level, target_level):
            return ({"error": "Forbidden. You may only edit users with a lower role level."}, 403)
    return None


def user_put_password_field_error(data: dict[str, Any]) -> ErrorPair | None:
    if "password" in data or "current_password" in data:
        return (
            {
                "error": (
                    "Password changes are not allowed via this endpoint. "
                    "Use PUT /api/v1/users/<id>/password with current_password and new_password."
                )
            },
            400,
        )
    return None


def user_put_validate_format_only_fields(data: dict[str, Any]) -> ErrorPair | None:
    """Validate ``display_name`` / ``bio`` / ``phone`` / ``birthday`` when present (not persisted via ``update_user``)."""
    from app.api.v1 import user_routes as ur

    checks: list[tuple[str, Any]] = [
        ("display_name", ur._validate_display_name),
        ("bio", ur._validate_bio),
        ("phone", ur._validate_phone),
        ("birthday", ur._validate_birthday),
    ]
    for key, validator in checks:
        if key not in data:
            continue
        val = data.get(key)
        ok, err = validator(val)
        if not ok:
            return ({"error": f"Invalid {key}: {err}"}, 400)
    return None


def user_put_username_email_kwargs(data: dict[str, Any]) -> tuple[dict[str, Any], ErrorPair | None]:
    """Build ``kwargs`` for fields accepted by ``user_service.update_user`` (username, email only here)."""
    from app.api.v1 import user_routes as ur

    kwargs: dict[str, Any] = {}
    for key, validator in (("username", ur._validate_username), ("email", ur._validate_email)):
        if key not in data:
            continue
        val = data.get(key)
        ok, err = validator(val)
        if not ok:
            return {}, ({"error": f"Invalid {key}: {err}"}, 400)
        kwargs[key] = val
    return kwargs, None


def user_put_role_level_kwargs_for_admin_other(
    data: dict[str, Any],
    *,
    current: Any,
    target: Any,
    user_id: int,
) -> tuple[dict[str, Any], ErrorPair | None]:
    """When admin edits another user: parse optional ``role_level`` with privilege checks."""
    from app.api.v1 import user_routes as ur
    from app.auth.permissions import admin_may_assign_role_level

    kwargs: dict[str, Any] = {}
    if "role" in data:
        kwargs["role"] = data.get("role")
    if "role_level" not in data:
        return kwargs, None
    try:
        new_level = int(data.get("role_level"))
    except (TypeError, ValueError):
        return {}, ({"error": "role_level must be an integer"}, 400)
    is_valid, err = ur._validate_role_level_bounds(new_level)
    if not is_valid:
        return {}, ({"error": err}, 400)
    actor_level = getattr(current, "role_level", 0) or 0
    target_level = getattr(target, "role_level", 0) or 0
    if not admin_may_assign_role_level(actor_level, user_id, new_level, current.id):
        return {}, (
            {"error": "Forbidden. You may not assign a role level higher than or equal to your own."},
            403,
        )
    kwargs["role_level"] = new_level
    return kwargs, None


def user_put_role_level_kwargs_for_self(
    data: dict[str, Any],
    *,
    current: Any,
) -> tuple[dict[str, Any], ErrorPair | None]:
    """Self-edit path for ``role_level`` (SuperAdmin vs admin rules)."""
    from app.api.v1 import user_routes as ur

    kwargs: dict[str, Any] = {}
    if "role_level" not in data:
        return kwargs, None
    if current_user_is_super_admin():
        try:
            new_level = int(data.get("role_level"))
        except (TypeError, ValueError):
            return {}, ({"error": "role_level must be an integer"}, 400)
        is_valid, err = ur._validate_role_level_bounds(new_level)
        if not is_valid:
            return {}, ({"error": err}, 400)
        if new_level < SUPERADMIN_THRESHOLD:
            return {}, (
                {"error": "Forbidden. SuperAdmin may only set own role level to at least 100."},
                403,
            )
        kwargs["role_level"] = new_level
        return kwargs, None
    if current_user_is_admin():
        return {}, ({"error": "Forbidden. Only SuperAdmin may change their own role_level."}, 403)
    return kwargs, None
