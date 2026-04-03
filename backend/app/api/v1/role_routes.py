"""Role CRUD API. Admin only."""
from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.feature_registry import FEATURE_MANAGE_ROLES
from app.auth.permissions import require_feature, require_jwt_admin
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
@require_jwt_admin
@require_feature(FEATURE_MANAGE_ROLES)
def roles_list():
    """List roles (admin only). Query: page, limit, q (search name)."""
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
@require_jwt_admin
@require_feature(FEATURE_MANAGE_ROLES)
def roles_get(role_id):
    """Get one role by id (admin only)."""
    role = get_role_by_id(role_id)
    if not role:
        return jsonify({"error": "Role not found"}), 404
    return jsonify(role.to_dict()), 200


@api_v1_bp.route("/roles", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_ROLES)
def roles_create():
    """Create a role (admin only). Body: name; optional description, default_role_level."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    name = (data.get("name") or "").strip() if data.get("name") is not None else ""
    description = data.get("description")
    if description is not None:
        description = (description or "").strip() or None
    default_role_level = data.get("default_role_level")
    role, err = create_role_service(name, description=description, default_role_level=default_role_level)
    if err:
        status = 409 if err == "Role name already exists" else 400
        return jsonify({"error": err}), status
    return jsonify(role.to_dict()), 201


@api_v1_bp.route("/roles/<int:role_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_ROLES)
def roles_update(role_id):
    """Update a role (admin only). Body: optional name, description, default_role_level."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    name = data.get("name")
    if name is not None:
        name = (name or "").strip() or None
    # If key is present, always patch description; pass "" so service clears to NULL (None alone = skip).
    description = data.get("description")
    if "description" in data:
        raw = data["description"]
        if raw is None:
            description = ""
        else:
            stripped = (raw or "").strip() or None
            description = "" if stripped is None else stripped
    default_role_level = data.get("default_role_level")
    role, err = update_role_service(role_id, name=name, description=description, default_role_level=default_role_level)
    if err:
        status = 409 if err == "Role name already exists" else (404 if err == "Role not found" else 400)
        return jsonify({"error": err}), status
    return jsonify(role.to_dict()), 200


@api_v1_bp.route("/roles/<int:role_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_ROLES)
def roles_delete(role_id):
    """Delete a role (admin only). Fails if any user has this role."""
    ok, err = delete_role_service(role_id)
    if not ok:
        status = 404 if err == "Role not found" else 400
        return jsonify({"error": err or "Role not found"}), status
    return jsonify({"message": "Deleted"}), 200
