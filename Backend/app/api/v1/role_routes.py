"""Role CRUD API. Admin only."""
from flask import jsonify, request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.auth.permissions import current_user_is_admin
from app.extensions import limiter
from app.services.role_service import (
    create_role as create_role_service,
    delete_role as delete_role_service,
    get_role_by_id,
    list_roles as list_roles_service,
    update_role as update_role_service,
)


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


@api_v1_bp.route("/roles", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def roles_list():
    """List roles (admin only). Query: page, limit, q (search name)."""
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 50, min_val=1, max_val=100)
    q = request.args.get("q", "").strip() or None
    items, total = list_roles_service(page=page, per_page=limit, q=q)
    return jsonify({
        "items": [r.to_dict() for r in items],
        "total": total,
        "page": page,
        "per_page": limit,
    }), 200


@api_v1_bp.route("/roles/<int:role_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def roles_get(role_id):
    """Get one role by id (admin only)."""
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    role = get_role_by_id(role_id)
    if not role:
        return jsonify({"error": "Role not found"}), 404
    return jsonify(role.to_dict()), 200


@api_v1_bp.route("/roles", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def roles_create():
    """Create a role (admin only). Body: name."""
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    name = (data.get("name") or "").strip() if data.get("name") is not None else ""
    role, err = create_role_service(name)
    if err:
        status = 409 if err == "Role name already exists" else 400
        return jsonify({"error": err}), status
    return jsonify(role.to_dict()), 201


@api_v1_bp.route("/roles/<int:role_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def roles_update(role_id):
    """Update a role's name (admin only). Body: name."""
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    name = (data.get("name") or "").strip() if data.get("name") is not None else ""
    role, err = update_role_service(role_id, name)
    if err:
        status = 409 if err == "Role name already exists" else (404 if err == "Role not found" else 400)
        return jsonify({"error": err}), status
    return jsonify(role.to_dict()), 200


@api_v1_bp.route("/roles/<int:role_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@jwt_required()
def roles_delete(role_id):
    """Delete a role (admin only). Fails if any user has this role."""
    if not current_user_is_admin():
        return jsonify({"error": "Forbidden"}), 403
    ok, err = delete_role_service(role_id)
    if not ok:
        status = 404 if err == "Role not found" else 400
        return jsonify({"error": err or "Role not found"}), status
    return jsonify({"message": "Deleted"}), 200
