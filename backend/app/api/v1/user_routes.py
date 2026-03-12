"""User CRUD API: list (admin), get (admin or self), update (admin or self), delete (admin)."""
import logging

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_USERS, user_can_access_feature
from app.auth.permissions import (
    admin_may_assign_role_level,
    admin_may_edit_target,
    current_user_is_admin,
    current_user_is_super_admin,
    get_current_user,
    require_jwt_admin,
)
from app.extensions import limiter
from app.services import log_activity
from app.services.user_service import (
    assign_role as assign_role_service,
    ban_user as ban_user_service,
    change_password as change_password_service,
    get_user_by_id,
    list_users,
    unban_user as unban_user_service,
    update_user as update_user_service,
    delete_user as delete_user_service,
)

logger = logging.getLogger(__name__)


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


@api_v1_bp.route("/users", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def users_list():
    """List users (admin only). Query: page, limit, q (search username/email)."""
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    if not user_can_access_feature(get_current_user(), FEATURE_MANAGE_USERS):
        return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    search = request.args.get("q", "").strip() or None
    items, total = list_users(page=page, per_page=limit, search=search)
    return jsonify({
        "items": [u.to_dict(include_email=True, include_ban=True, include_areas=True) for u in items],
        "total": total,
        "page": page,
        "per_page": limit,
    }), 200


@api_v1_bp.route("/users/<int:user_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def users_get(user_id):
    """Get one user by id. Admin: any user; otherwise only self."""
    current = get_current_user()
    if current is None:
        return jsonify({"error": "User not found"}), 404
    if current.id != user_id and not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    if current.id != user_id and not user_can_access_feature(current, FEATURE_MANAGE_USERS):
        return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if current.id == user_id and getattr(user, "is_banned", False):
        return jsonify({"error": "Account is restricted."}), 403
    include_email = current_user_is_admin() or current.id == user_id
    include_ban = current_user_is_admin()
    include_areas = current_user_is_admin()
    return jsonify(user.to_dict(include_email=include_email, include_ban=include_ban, include_areas=include_areas)), 200


@api_v1_bp.route("/users/<int:user_id>/preferences", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def users_preferences(user_id):
    """Update user preferences (e.g. preferred_language). User can update self; admin can update any."""
    current = get_current_user()
    if current is None:
        return jsonify({"error": "User not found"}), 404
    if current.id != user_id and not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    kwargs = {}
    if "preferred_language" in data:
        kwargs["preferred_language"] = data.get("preferred_language")
    if not kwargs:
        return jsonify({"error": "No preference fields to update"}), 400
    user, err = update_user_service(user_id, **kwargs)
    if err:
        status = 400 if err == "Unsupported language" else 404
        return jsonify({"error": err}), status
    include_email = current_user_is_admin() or current.id == user.id
    include_ban = current_user_is_admin()
    include_areas = current_user_is_admin()
    return jsonify(user.to_dict(include_email=include_email, include_ban=include_ban, include_areas=include_areas)), 200


@api_v1_bp.route("/users/<int:user_id>/password", methods=["PUT"])
@limiter.limit("10 per minute")
@jwt_required()
def users_change_password(user_id):
    """
    Change password (self only). Body: current_password, new_password.
    Requires valid current_password. Password changes are not available via generic user update.
    """
    current = get_current_user()
    if current is None:
        return jsonify({"error": "User not found"}), 404
    if current.id != user_id:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    if current_password is None or new_password is None:
        return jsonify({"error": "current_password and new_password are required"}), 400
    user, err = change_password_service(
        user_id,
        current_password=current_password,
        new_password=new_password,
    )
    if err:
        return jsonify({"error": err}), 400
    return jsonify({"message": "Password updated"}), 200


@api_v1_bp.route("/users/<int:user_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def users_update(user_id):
    """
    Update a user. Admin can update users with strictly lower role_level; user can only update self (no role/role_level).
    Body: optional username, email, preferred_language, role (admin only), role_level (admin only, hierarchy rules).
    """
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
            "error": "Password changes are not allowed via this endpoint. Use PUT /api/v1/users/<id>/password with current_password and new_password."
        }), 400

    kwargs = {}
    if "username" in data:
        kwargs["username"] = data.get("username")
    if "email" in data:
        kwargs["email"] = data.get("email")
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
            actor_level = getattr(current, "role_level", 0) or 0
            target_level = getattr(target, "role_level", 0) or 0
            if not admin_may_assign_role_level(actor_level, user_id, new_level, current.id):
                return jsonify({"error": "Forbidden. You may not assign a role level higher than or equal to your own."}), 403
            kwargs["role_level"] = new_level
    elif current.id == user_id and "role_level" in data:
        if not current_user_is_super_admin():
            return jsonify({"error": "Forbidden. Only SuperAdmin may change their own role level."}), 403
        try:
            new_level = int(data.get("role_level"))
        except (TypeError, ValueError):
            return jsonify({"error": "role_level must be an integer"}), 400
        from app.models.user import SUPERADMIN_THRESHOLD
        if new_level < SUPERADMIN_THRESHOLD:
            return jsonify({"error": "Forbidden. SuperAdmin may only set own role level to at least 100."}), 403
        kwargs["role_level"] = new_level

    user, err = update_user_service(user_id, **kwargs)
    if err:
        status = 409 if err in ("Username already taken", "Email already registered") else 400
        if err == "User not found":
            status = 404
        return jsonify({"error": err}), status
    log_activity(
        actor=current,
        category="admin",
        action="user_updated",
        status="success",
        message=f"User updated: {user.username}",
        route=request.path,
        method=request.method,
        target_type="user",
        target_id=str(user.id),
    )
    if "role" in kwargs:
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
    include_email = current_user_is_admin() or current.id == user.id
    include_ban = current_user_is_admin()
    include_areas = current_user_is_admin()
    return jsonify(user.to_dict(include_email=include_email, include_ban=include_ban, include_areas=include_areas)), 200


@api_v1_bp.route("/users/<int:user_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@jwt_required()
def users_delete(user_id):
    """Delete a user (admin only). Admin may only delete users with strictly lower role_level."""
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    if not user_can_access_feature(get_current_user(), FEATURE_MANAGE_USERS):
        return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
    target_user = get_user_by_id(user_id)
    if not target_user:
        return jsonify({"error": "User not found"}), 404
    actor_level = getattr(get_current_user(), "role_level", 0) or 0
    target_level = getattr(target_user, "role_level", 0) or 0
    if not admin_may_edit_target(actor_level, target_level):
        return jsonify({"error": "Forbidden. You may only delete users with a lower role level."}), 403
    ok, err = delete_user_service(user_id)
    if not ok:
        return jsonify({"error": err or "User not found"}), 404
    log_activity(
        actor=get_current_user(),
        category="admin",
        action="user_deleted",
        status="success",
        message=f"User deleted: id={user_id}" + (f" ({target_user.username})" if target_user else ""),
        route=request.path,
        method=request.method,
        target_type="user",
        target_id=str(user_id),
    )
    return jsonify({"message": "Deleted"}), 200


@api_v1_bp.route("/users/<int:user_id>/role", methods=["PATCH"])
@limiter.limit("30 per minute")
@require_jwt_admin
def users_assign_role(user_id):
    """Assign role to a user (admin only). Admin may only assign to users with strictly lower role_level. Body: role (user, qa, moderator, admin)."""
    if not user_can_access_feature(get_current_user(), FEATURE_MANAGE_USERS):
        return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    role_name = data.get("role")
    if role_name is None:
        return jsonify({"error": "role is required"}), 400
    current = get_current_user()
    target = get_user_by_id(user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    actor_level = getattr(current, "role_level", 0) or 0
    target_level = getattr(target, "role_level", 0) or 0
    if not admin_may_edit_target(actor_level, target_level):
        return jsonify({"error": "Forbidden. You may only assign roles to users with a lower role level."}), 403
    from app.models import Role
    role_obj = Role.query.filter_by(name=(role_name or "").strip().lower()).first()
    if not role_obj:
        return jsonify({"error": "Invalid role"}), 400
    user, err = assign_role_service(user_id, role_name, actor_id=current.id if current else None)
    if err:
        status = 404 if err == "User not found" else 400
        return jsonify({"error": err}), status
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
    return jsonify(user.to_dict(include_email=True, include_ban=True, include_areas=True)), 200


@api_v1_bp.route("/users/<int:user_id>/ban", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
def users_ban(user_id):
    """Ban a user (admin only). Admin may only ban users with strictly lower role_level. Body: optional reason."""
    if not user_can_access_feature(get_current_user(), FEATURE_MANAGE_USERS):
        return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
    current = get_current_user()
    target = get_user_by_id(user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    actor_level = getattr(current, "role_level", 0) or 0
    target_level = getattr(target, "role_level", 0) or 0
    if not admin_may_edit_target(actor_level, target_level):
        return jsonify({"error": "Forbidden. You may only ban users with a lower role level."}), 403
    data = request.get_json(silent=True) or {}
    reason = data.get("reason") if isinstance(data.get("reason"), str) else None
    if reason is not None:
        reason = reason.strip() or None
    user, err = ban_user_service(user_id, reason=reason, actor_id=current.id if current else None)
    if err:
        status = 404 if err == "User not found" else 400
        return jsonify({"error": err}), status
    log_activity(
        actor=current,
        category="admin",
        action="user_banned",
        status="success",
        message=f"User banned: {user.username}",
        route=request.path,
        method=request.method,
        target_type="user",
        target_id=str(user.id),
    )
    return jsonify(user.to_dict(include_email=True, include_ban=True, include_areas=True)), 200


@api_v1_bp.route("/users/<int:user_id>/unban", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
def users_unban(user_id):
    """Unban a user (admin only). Admin may only unban users with strictly lower role_level."""
    if not user_can_access_feature(get_current_user(), FEATURE_MANAGE_USERS):
        return jsonify({"error": "Forbidden. You do not have access to this feature."}), 403
    current = get_current_user()
    target = get_user_by_id(user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    actor_level = getattr(current, "role_level", 0) or 0
    target_level = getattr(target, "role_level", 0) or 0
    if not admin_may_edit_target(actor_level, target_level):
        return jsonify({"error": "Forbidden. You may only unban users with a lower role level."}), 403
    user, err = unban_user_service(user_id)
    if err:
        status = 404 if err == "User not found" else 400
        return jsonify({"error": err}), status
    log_activity(
        actor=current,
        category="admin",
        action="user_unbanned",
        status="success",
        message=f"User unbanned: {user.username}",
        route=request.path,
        method=request.method,
        target_type="user",
        target_id=str(user.id),
    )
    return jsonify(user.to_dict(include_email=True, include_ban=True, include_areas=True)), 200
