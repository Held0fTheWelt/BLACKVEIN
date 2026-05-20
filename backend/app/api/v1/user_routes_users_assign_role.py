"""User PATCH /users/<id>/role — validation, privilege gates, persistence (DS-017)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from flask import jsonify, request

from app.auth.feature_registry import FEATURE_MANAGE_USERS, user_can_access_feature
from app.auth.permissions import (
    admin_may_edit_target,
    current_user_is_super_admin,
    get_current_user,
)
from app.config.route_constants import route_status_codes
from app.extensions import db
from app.models import Role
from app.services import log_activity
from app.services.identity.user_service import assign_role as assign_role_service, get_user_by_id


@dataclass
class _AssignRoleContext:
    data: dict
    current: Any
    target: Any
    has_role_level_in_request: bool
    new_role_level: int
    old_role: str


def _assign_role_phase_parse_and_load(user_id: int) -> Tuple[Optional[_AssignRoleContext], Optional[Tuple[Any, int]]]:
    """Parse JSON, resolve target and role row; return context or (jsonify body, status)."""
    from app.api.v1 import user_routes as ur

    data = request.get_json(silent=True)
    if data is None:
        return None, (jsonify({"error": "Invalid or missing JSON body"}), route_status_codes.bad_request)
    role_name = data.get("role")
    if role_name is None:
        return None, (jsonify({"error": "role is required"}), route_status_codes.bad_request)

    current = get_current_user()
    target = get_user_by_id(user_id)
    if not target:
        return None, (jsonify({"error": "User not found"}), route_status_codes.not_found)

    role_obj = Role.query.filter_by(name=(role_name or "").strip().lower()).first()
    if not role_obj:
        return None, (jsonify({"error": "Invalid role"}), route_status_codes.bad_request)

    has_role_level_in_request = "role_level" in data
    if has_role_level_in_request:
        try:
            new_role_level = int(data.get("role_level"))
        except (TypeError, ValueError):
            return None, (jsonify({"error": "role_level must be an integer"}), route_status_codes.bad_request)
        is_valid, err = ur._validate_role_level_bounds(new_role_level)
        if not is_valid:
            return None, (jsonify({"error": err}), route_status_codes.bad_request)
    else:
        new_role_level = getattr(target, "role_level", 0) or 0

    old_role = target.role
    return (
        _AssignRoleContext(
            data=data,
            current=current,
            target=target,
            has_role_level_in_request=has_role_level_in_request,
            new_role_level=new_role_level,
            old_role=old_role,
        ),
        None,
    )


def _assign_role_phase_privilege_gates(
    user_id: int, ctx: _AssignRoleContext
) -> Optional[Tuple[Any, int]]:
    """Self vs other, editability, and role_level escalation rules."""
    current = ctx.current
    target = ctx.target
    data = ctx.data
    has_role_level_in_request = ctx.has_role_level_in_request
    new_role_level = ctx.new_role_level
    role_name = data.get("role")
    actor_level = getattr(current, "role_level", 0) or 0
    target_level = getattr(target, "role_level", 0) or 0

    if user_id == current.id:
        is_super_admin = current_user_is_super_admin()
        if not is_super_admin and (has_role_level_in_request or role_name != current.role):
            return (
                jsonify(
                    {
                        "error": "Cannot modify your own role or role level via this endpoint. "
                        "Use PUT /users/<id> for self-changes if allowed.",
                        "code": "PRIVILEGE_ESCALATION_DENIED",
                    }
                ),
                route_status_codes.forbidden,
            )
        if is_super_admin and has_role_level_in_request:
            if new_role_level > actor_level:
                return (
                    jsonify(
                        {
                            "error": f"Cannot elevate yourself higher than your own role level ({actor_level}). "
                            "You may only assign equal or lower levels.",
                            "code": "INSUFFICIENT_PRIVILEGE",
                        }
                    ),
                    route_status_codes.forbidden,
                )

    if user_id != current.id:
        if not admin_may_edit_target(actor_level, target_level):
            return (
                jsonify({"error": "Forbidden. You may only assign roles to users with a lower role level."}),
                route_status_codes.forbidden,
            )

    if has_role_level_in_request:
        if user_id == current.id:
            if not current_user_is_super_admin():
                return (
                    jsonify(
                        {
                            "error": "Cannot elevate yourself to SuperAdmin. Only SuperAdmin may assign themselves a higher role level.",
                            "code": "PRIVILEGE_ESCALATION_DENIED",
                        }
                    ),
                    route_status_codes.forbidden,
                )
            if new_role_level > actor_level:
                return (
                    jsonify(
                        {
                            "error": f"Cannot elevate yourself higher than your own role level ({actor_level}). "
                            "You may only assign equal or lower levels.",
                            "code": "INSUFFICIENT_PRIVILEGE",
                        }
                    ),
                    route_status_codes.forbidden,
                )
        else:
            if new_role_level >= actor_level:
                return (
                    jsonify(
                        {
                            "error": f"Cannot assign a role level higher than your own ({actor_level}). "
                            "You may only assign strictly lower levels.",
                            "code": "PRIVILEGE_ESCALATION_DENIED",
                        }
                    ),
                    route_status_codes.forbidden,
                )
    return None


def _assign_role_phase_persist_and_response(
    user_id: int, ctx: _AssignRoleContext
) -> Tuple[Any, int]:
    """Call service, optional role_level commit, activity + privilege logs, JSON body."""
    from app.api.v1 import user_routes as ur

    current = ctx.current
    target = ctx.target
    data = ctx.data
    has_role_level_in_request = ctx.has_role_level_in_request
    new_role_level = ctx.new_role_level
    old_role = ctx.old_role
    role_name = data.get("role")

    user, err = assign_role_service(user_id, role_name, actor_id=current.id if current else None)
    if err:
        status = route_status_codes.not_found if err == "User not found" else route_status_codes.bad_request
        return jsonify({"error": err}), status

    if has_role_level_in_request:
        user.role_level = new_role_level
        db.session.commit()

    log_activity(
        actor=current,
        category="admin",
        action="user_role_changed",
        status="success",
        message=f"User role set to {user.role}",
        route=request.path,
        method=request.method,
        target_type="user",
        target_id=str(user.id),
        metadata={"new_role": user.role},
    )

    reason_str = data.get("reason") if isinstance(data.get("reason"), str) else None
    ur._log_privilege_change(
        admin_id=current.id,
        user_id=user.id,
        old_role=old_role,
        new_role=user.role,
        old_level=target.role_level,
        new_level=user.role_level,
        reason=reason_str,
    )

    return (
        jsonify(user.to_dict(include_email=True, include_ban=True, include_areas=True)),
        route_status_codes.ok,
    )


def execute_users_assign_role_patch(user_id: int) -> Tuple[Any, int]:
    """Same contract as ``user_routes.users_assign_role``."""
    if not user_can_access_feature(get_current_user(), FEATURE_MANAGE_USERS):
        return jsonify({"error": "Forbidden. You do not have access to this feature."}), route_status_codes.forbidden

    ctx, err = _assign_role_phase_parse_and_load(user_id)
    if err is not None:
        return err

    gate_err = _assign_role_phase_privilege_gates(user_id, ctx)
    if gate_err is not None:
        return gate_err

    return _assign_role_phase_persist_and_response(user_id, ctx)
