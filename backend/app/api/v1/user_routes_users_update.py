"""User PUT /users/<id> — validation and privilege paths (DS-050)."""

from __future__ import annotations

from flask import jsonify, request

from app.auth.permissions import current_user_is_admin, get_current_user
from app.services import log_activity
from app.services.user_service import get_user_by_id, update_user as update_user_service

from app.api.v1.user_routes_users_update_guards import (
    user_put_authorization_error,
    user_put_collect_service_kwargs,
    user_put_password_field_error,
)


def execute_users_update_put(user_id: int):
    """Update user (admin or self); same contract as ``user_routes.users_update``."""
    from app.api.v1 import user_routes as ur

    current = get_current_user()
    target = get_user_by_id(user_id)
    auth_err = user_put_authorization_error(current, target, user_id=user_id)
    if auth_err:
        body, status = auth_err
        return jsonify(body), status

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    pwd_err = user_put_password_field_error(data)
    if pwd_err:
        body, status = pwd_err
        return jsonify(body), status

    kwargs, kerr = user_put_collect_service_kwargs(
        data, current=current, target=target, user_id=user_id
    )
    if kerr:
        body, status = kerr
        return jsonify(body), status

    old_role = target.role if "role" in kwargs else None
    old_role_level = target.role_level if "role_level" in kwargs else None

    user, err = update_user_service(user_id, **kwargs)
    if err:
        status = 409 if err in ("Username already taken", "Email already registered") else 400
        if err == "User not found":
            status = 404
        return jsonify({"error": err}), status

    action = "user_updated"
    if "role" in kwargs or "role_level" in kwargs:
        action = "user_role_changed"

    log_activity(
        actor=current,
        category="admin",
        action=action,
        status="success",
        message=f"User updated: {user.username}",
        route=request.path,
        method=request.method,
        target_type="user",
        target_id=str(user.id),
    )

    if "role" in kwargs or "role_level" in kwargs:
        reason_str = None
        if isinstance(data, dict) and "reason" in data:
            reason_str = data.get("reason")
        ur._log_privilege_change(
            admin_id=current.id,
            user_id=user.id,
            old_role=old_role or target.role,
            new_role=user.role,
            old_level=old_role_level,
            new_level=user.role_level,
            reason=reason_str,
        )

    include_email = current_user_is_admin() or current.id == user.id
    include_ban = current_user_is_admin()
    include_areas = current_user_is_admin()
    return jsonify(user.to_dict(include_email=include_email, include_ban=include_ban, include_areas=include_areas)), 200
