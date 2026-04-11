"""User PUT /users/<id> — validation and privilege paths (DS-050)."""

from __future__ import annotations

from flask import jsonify, request

from app.auth.feature_registry import FEATURE_MANAGE_USERS, user_can_access_feature
from app.auth.permissions import (
    admin_may_assign_role_level,
    admin_may_edit_target,
    current_user_is_admin,
    current_user_is_super_admin,
    get_current_user,
)
from app.models.user import SUPERADMIN_THRESHOLD
from app.services import log_activity
from app.services.user_service import get_user_by_id, update_user as update_user_service


def execute_users_update_put(user_id: int):
    """Update user (admin or self); same contract as ``user_routes.users_update``."""
    from app.api.v1 import user_routes as ur

    current = get_current_user()
    if current is None:
        return jsonify({"error": "User not found"}), 404
    target = get_user_by_id(user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    if current.id != user_id:
        if not current_user_is_admin():
            return jsonify({"error": "Forbidden"}), 403
        if not user_can_access_feature(current, FEATURE_MANAGE_USERS):
            return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
        actor_level = getattr(current, "role_level", 0) or 0
        target_level = getattr(target, "role_level", 0) or 0
        if not admin_may_edit_target(actor_level, target_level):
            return jsonify({"error": "Forbidden. You may only edit users with a lower role level."}), 403

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    if "password" in data or "current_password" in data:
        return jsonify({
            "error": (
                "Password changes are not allowed via this endpoint. "
                "Use PUT /api/v1/users/<id>/password with current_password and new_password."
            )
        }), 400

    kwargs = {}

    if "username" in data:
        username_val = data.get("username")
        is_valid, error = ur._validate_username(username_val)
        if not is_valid:
            return jsonify({"error": f"Invalid username: {error}"}), 400
        kwargs["username"] = username_val

    if "email" in data:
        email_val = data.get("email")
        is_valid, error = ur._validate_email(email_val)
        if not is_valid:
            return jsonify({"error": f"Invalid email: {error}"}), 400
        kwargs["email"] = email_val

    if "display_name" in data:
        display_name_val = data.get("display_name")
        is_valid, error = ur._validate_display_name(display_name_val)
        if not is_valid:
            return jsonify({"error": f"Invalid display_name: {error}"}), 400

    if "bio" in data:
        bio_val = data.get("bio")
        is_valid, error = ur._validate_bio(bio_val)
        if not is_valid:
            return jsonify({"error": f"Invalid bio: {error}"}), 400

    if "phone" in data:
        phone_val = data.get("phone")
        is_valid, error = ur._validate_phone(phone_val)
        if not is_valid:
            return jsonify({"error": f"Invalid phone: {error}"}), 400

    if "birthday" in data:
        birthday_val = data.get("birthday")
        is_valid, error = ur._validate_birthday(birthday_val)
        if not is_valid:
            return jsonify({"error": f"Invalid birthday: {error}"}), 400

    if "preferred_language" in data:
        kwargs["preferred_language"] = data.get("preferred_language")
    if current.id != user_id and current_user_is_admin():
        if "role" in data:
            kwargs["role"] = data.get("role")
        if "role_level" in data:
            try:
                new_level = int(data.get("role_level"))
            except (TypeError, ValueError):
                return jsonify({"error": "role_level must be an integer"}), 400
            is_valid, err = ur._validate_role_level_bounds(new_level)
            if not is_valid:
                return jsonify({"error": err}), 400
            actor_level = getattr(current, "role_level", 0) or 0
            target_level = getattr(target, "role_level", 0) or 0
            if not admin_may_assign_role_level(actor_level, user_id, new_level, current.id):
                return jsonify({
                    "error": "Forbidden. You may not assign a role level higher than or equal to your own."
                }), 403
            kwargs["role_level"] = new_level
    elif current.id == user_id and "role_level" in data:
        if current_user_is_super_admin():
            try:
                new_level = int(data.get("role_level"))
            except (TypeError, ValueError):
                return jsonify({"error": "role_level must be an integer"}), 400
            is_valid, err = ur._validate_role_level_bounds(new_level)
            if not is_valid:
                return jsonify({"error": err}), 400
            if new_level < SUPERADMIN_THRESHOLD:
                return jsonify({
                    "error": "Forbidden. SuperAdmin may only set own role level to at least 100."
                }), 403
            kwargs["role_level"] = new_level
        elif current_user_is_admin():
            return jsonify({"error": "Forbidden. Only SuperAdmin may change their own role_level."}), 403

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
