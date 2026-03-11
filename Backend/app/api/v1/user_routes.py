"""User CRUD API: list (admin), get (admin or self), update (admin or self), delete (admin)."""
import logging

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.auth.permissions import current_user_is_admin, get_current_user, require_jwt_admin
from app.extensions import limiter
from app.services import log_activity
from app.services.user_service import (
    assign_role as assign_role_service,
    ban_user as ban_user_service,
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
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    search = request.args.get("q", "").strip() or None
    items, total = list_users(page=page, per_page=limit, search=search)
    return jsonify({
        "items": [u.to_dict(include_email=True) for u in items],
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
    user = get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    include_email = current_user_is_admin() or current.id == user_id
    return jsonify(user.to_dict(include_email=include_email)), 200


@api_v1_bp.route("/users/<int:user_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def users_update(user_id):
    """
    Update a user. Admin can update any user and set role; user can only update self (no role).
    Body: optional username, email, password (new), current_password (required when changing own password), role (admin only).
    """
    current = get_current_user()
    if current is None:
        return jsonify({"error": "User not found"}), 404
    if current.id != user_id and not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    kwargs = {}
    if "username" in data:
        kwargs["username"] = data.get("username")
    if "email" in data:
        kwargs["email"] = data.get("email")
    if "password" in data:
        kwargs["new_password"] = data.get("password")
    if "current_password" in data:
        kwargs["current_password"] = data.get("current_password")

    if current_user_is_admin() and "role" in data:
        kwargs["role"] = data.get("role")

    user, err = update_user_service(user_id, **kwargs)
    if err:
        status = 409 if err in ("Username already taken", "Email already registered") else 400
        if err == "User not found":
            status = 404
        if err == "Current password is incorrect":
            status = 400
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
    return jsonify(user.to_dict(include_email=include_email)), 200


@api_v1_bp.route("/users/<int:user_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@jwt_required()
def users_delete(user_id):
    """Delete a user (admin only)."""
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    target_user = get_user_by_id(user_id)
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
    """Assign role to a user (admin only). Body: role (user, moderator, or admin)."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    role_name = data.get("role")
    if role_name is None:
        return jsonify({"error": "role is required"}), 400
    current = get_current_user()
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
    return jsonify(user.to_dict(include_email=True, include_ban=True)), 200


@api_v1_bp.route("/users/<int:user_id>/ban", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
def users_ban(user_id):
    """Ban a user (admin only). Body: optional reason."""
    data = request.get_json(silent=True) or {}
    reason = data.get("reason") if isinstance(data.get("reason"), str) else None
    if reason is not None:
        reason = reason.strip() or None
    current = get_current_user()
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
    return jsonify(user.to_dict(include_email=True, include_ban=True)), 200


@api_v1_bp.route("/users/<int:user_id>/unban", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
def users_unban(user_id):
    """Unban a user (admin only)."""
    current = get_current_user()
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
    return jsonify(user.to_dict(include_email=True, include_ban=True)), 200
