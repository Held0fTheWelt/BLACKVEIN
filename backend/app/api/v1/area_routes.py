"""Area CRUD and user/feature area assignment API. Admin only."""
from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.permissions import get_current_user, require_feature, require_jwt_admin
from app.auth.feature_registry import FEATURE_IDS, FEATURE_MANAGE_AREAS, FEATURE_MANAGE_FEATURE_AREAS
from app.extensions import limiter
from app.services.area_service import (
    create_area as create_area_service,
    delete_area as delete_area_service,
    get_area_by_id,
    list_areas as list_areas_service,
    list_feature_areas_mapping,
    set_feature_areas as set_feature_areas_service,
    set_user_areas as set_user_areas_service,
    update_area as update_area_service,
)
from app.services.user_service import get_user_by_id


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


@api_v1_bp.route("/areas", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_AREAS)
def areas_list():
    """List areas (admin only). Query: page, limit, q (search name/slug)."""
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 50, min_val=1, max_val=100)
    q = request.args.get("q", "").strip() or None
    items, total = list_areas_service(page=page, per_page=limit, q=q)
    return jsonify({
        "items": [a.to_dict() for a in items],
        "total": total,
        "page": page,
        "per_page": limit,
    }), 200


@api_v1_bp.route("/areas/<int:area_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_AREAS)
def areas_get(area_id):
    """Get one area by id (admin only)."""
    area = get_area_by_id(area_id)
    if not area:
        return jsonify({"error": "Area not found"}), 404
    return jsonify(area.to_dict()), 200


@api_v1_bp.route("/areas", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_AREAS)
def areas_create():
    """Create an area (admin only). Body: name; optional slug, description."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    name = (data.get("name") or "").strip() if data.get("name") is not None else ""
    slug = data.get("slug")
    if slug is not None:
        slug = (slug or "").strip() or None
    description = data.get("description")
    if description is not None:
        description = (description or "").strip() or None
    area, err = create_area_service(name, slug=slug, description=description)
    if err:
        status = 409 if err in ("Area slug already exists", "Area name already exists") else 400
        return jsonify({"error": err}), status
    return jsonify(area.to_dict()), 201


@api_v1_bp.route("/areas/<int:area_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_AREAS)
def areas_update(area_id):
    """Update an area (admin only). Body: optional name, slug, description. System 'all' protected."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    name = data.get("name")
    if name is not None:
        name = (name or "").strip() or None
    slug = data.get("slug")
    if slug is not None:
        slug = (slug or "").strip() or None
    description = data.get("description")
    if description is not None:
        description = (description or "").strip() or None
    area, err = update_area_service(area_id, name=name, slug=slug, description=description)
    if err:
        status = 409 if "already exists" in (err or "") else (404 if err == "Area not found" else 400)
        return jsonify({"error": err}), status
    return jsonify(area.to_dict()), 200


@api_v1_bp.route("/areas/<int:area_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_AREAS)
def areas_delete(area_id):
    """Delete an area (admin only). Fails for system area or if assigned to users/features."""
    ok, err = delete_area_service(area_id)
    if not ok:
        status = 404 if err == "Area not found" else 400
        return jsonify({"error": err or "Area not found"}), status
    return jsonify({"message": "Deleted"}), 200


@api_v1_bp.route("/users/<int:user_id>/areas", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_AREAS)
def user_areas_list(user_id):
    """List areas assigned to a user (admin only)."""
    from app.auth.permissions import admin_may_edit_target
    current = get_current_user()
    target = get_user_by_id(user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    if not admin_may_edit_target(getattr(current, "role_level", 0) or 0, getattr(target, "role_level", 0) or 0):
        return jsonify({"error": "Forbidden. You may only view users with a lower role level."}), 403
    areas = list(target.areas) if target.areas else []
    return jsonify({
        "user_id": user_id,
        "area_ids": [a.id for a in areas],
        "areas": [a.to_dict() for a in areas],
    }), 200


@api_v1_bp.route("/users/<int:user_id>/areas", methods=["PUT"])
@limiter.limit("30 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_AREAS)
def user_areas_set(user_id):
    """Set areas for a user (admin only). Body: area_ids (array). Replaces existing. Hierarchy: target must have lower role_level."""
    from app.auth.permissions import admin_may_edit_target
    current = get_current_user()
    target = get_user_by_id(user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404
    if not admin_may_edit_target(getattr(current, "role_level", 0) or 0, getattr(target, "role_level", 0) or 0):
        return jsonify({"error": "Forbidden. You may only assign areas to users with a lower role level."}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    area_ids = data.get("area_ids")
    if area_ids is not None and not isinstance(area_ids, list):
        return jsonify({"error": "area_ids must be an array"}), 400
    try:
        area_ids = [int(x) for x in (area_ids or [])]
    except (TypeError, ValueError):
        return jsonify({"error": "area_ids must contain integers"}), 400
    user, err = set_user_areas_service(user_id, area_ids)
    if err:
        status = 404 if err == "User not found" else 400
        return jsonify({"error": err}), status
    return jsonify(user.to_dict(include_email=True, include_ban=True, include_areas=True)), 200


@api_v1_bp.route("/feature-areas", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_FEATURE_AREAS)
def feature_areas_list():
    """List all features and their assigned area ids/slugs (admin only)."""
    mapping = list_feature_areas_mapping()
    return jsonify({"items": mapping}), 200


@api_v1_bp.route("/feature-areas/<path:feature_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_FEATURE_AREAS)
def feature_areas_get(feature_id):
    """Get area assignment for one feature (admin only)."""
    if feature_id not in FEATURE_IDS:
        return jsonify({"error": "Unknown feature_id"}), 404
    mapping = next((m for m in list_feature_areas_mapping() if m["feature_id"] == feature_id), None)
    if not mapping:
        return jsonify({"error": "Feature not found"}), 404
    return jsonify(mapping), 200


@api_v1_bp.route("/feature-areas/<path:feature_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_FEATURE_AREAS)
def feature_areas_set(feature_id):
    """Set areas for a feature (admin only). Body: area_ids (array). Replaces existing."""
    if feature_id not in FEATURE_IDS:
        return jsonify({"error": "Unknown feature_id"}), 400
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    area_ids = data.get("area_ids")
    if area_ids is not None and not isinstance(area_ids, list):
        return jsonify({"error": "area_ids must be an array"}), 400
    try:
        area_ids = [int(x) for x in (area_ids or [])]
    except (TypeError, ValueError):
        return jsonify({"error": "area_ids must contain integers"}), 400
    ok, err = set_feature_areas_service(feature_id, area_ids)
    if not ok:
        return jsonify({"error": err}), 400
    from app.services.area_service import list_feature_areas_mapping
    mapping = next((m for m in list_feature_areas_mapping() if m["feature_id"] == feature_id), {})
    return jsonify(mapping), 200
