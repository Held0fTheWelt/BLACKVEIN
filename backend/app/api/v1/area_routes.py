"""Area CRUD and user/feature area assignment API. Admin only."""
from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.permissions import get_current_user, require_feature, require_jwt_admin
from app.auth.feature_registry import FEATURE_IDS, FEATURE_MANAGE_AREAS, FEATURE_MANAGE_FEATURE_AREAS
from app.extensions import limiter
from app.services.content.area_service import (
    create_area as create_area_service,
    delete_area as delete_area_service,
    get_area_by_id,
    list_areas as list_areas_service,
    list_feature_areas_mapping,
    set_feature_areas as set_feature_areas_service,
    set_user_areas as set_user_areas_service,
    update_area as update_area_service,
)
from app.services.identity.user_service import get_user_by_id
from app.config.route_constants import route_status_codes, route_pagination_config
from app.api.v1._route_utils import _parse_int


@api_v1_bp.route("/areas", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_AREAS)
def areas_list():
    """List areas (admin only). Query: page, limit, q (search name/slug)."""
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), route_pagination_config.page_size_medium, min_val=1, max_val=route_pagination_config.page_size_large)
    q = request.args.get("q", "").strip() or None
    items, total = list_areas_service(page=page, per_page=limit, q=q)
    return jsonify({
        "items": [a.to_dict() for a in items],
        "total": total,
        "page": page,
        "per_page": limit,
    }), route_status_codes.ok


@api_v1_bp.route("/areas/<int:area_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_AREAS)
def areas_get(area_id):
    """Get one area by id (admin only)."""
    area = get_area_by_id(area_id)
    if not area:
        return jsonify({"error": "Area not found"}), route_status_codes.not_found
    return jsonify(area.to_dict()), route_status_codes.ok


@api_v1_bp.route("/areas", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_AREAS)
def areas_create():
    """Create an area (admin only). Body: name; optional slug, description."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), route_status_codes.bad_request
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
    return jsonify(area.to_dict()), route_status_codes.created


@api_v1_bp.route("/areas/<int:area_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_AREAS)
def areas_update(area_id):
    """Update an area (admin only). Body: optional name, slug, description. System 'all' protected."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), route_status_codes.bad_request
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
    return jsonify(area.to_dict()), route_status_codes.ok


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
    return jsonify({"message": "Deleted"}), route_status_codes.ok


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
        return jsonify({"error": "User not found"}), route_status_codes.not_found
    if not admin_may_edit_target(getattr(current, "role_level", 0) or 0, getattr(target, "role_level", 0) or 0):
        return jsonify({"error": "Forbidden. You may only view users with a lower role level."}), route_status_codes.forbidden
    areas = list(target.areas) if target.areas else []
    return jsonify({
        "user_id": user_id,
        "area_ids": [a.id for a in areas],
        "areas": [a.to_dict() for a in areas],
    }), route_status_codes.ok


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
        return jsonify({"error": "User not found"}), route_status_codes.not_found
    if not admin_may_edit_target(getattr(current, "role_level", 0) or 0, getattr(target, "role_level", 0) or 0):
        return jsonify({"error": "Forbidden. You may only assign areas to users with a lower role level."}), route_status_codes.forbidden
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), route_status_codes.bad_request
    area_ids = data.get("area_ids")
    if area_ids is not None and not isinstance(area_ids, list):
        return jsonify({"error": "area_ids must be an array"}), route_status_codes.bad_request
    try:
        area_ids = [int(x) for x in (area_ids or [])]
    except (TypeError, ValueError):
        return jsonify({"error": "area_ids must contain integers"}), route_status_codes.bad_request
    user, err = set_user_areas_service(user_id, area_ids)
    if err:
        status = 404 if err == "User not found" else 400
        return jsonify({"error": err}), status
    return jsonify(user.to_dict(include_email=True, include_ban=True, include_areas=True)), route_status_codes.ok


@api_v1_bp.route("/feature-areas", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_FEATURE_AREAS)
def feature_areas_list():
    """List all features and their assigned area ids/slugs (admin only)."""
    mapping = list_feature_areas_mapping()
    return jsonify({"items": mapping}), route_status_codes.ok


@api_v1_bp.route("/feature-areas/<path:feature_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_FEATURE_AREAS)
def feature_areas_get(feature_id):
    """Get area assignment for one feature (admin only)."""
    if feature_id not in FEATURE_IDS:
        return jsonify({"error": "Unknown feature_id"}), route_status_codes.not_found
    mapping = next((m for m in list_feature_areas_mapping() if m["feature_id"] == feature_id), None)
    if not mapping:
        return jsonify({"error": "Feature not found"}), route_status_codes.not_found
    return jsonify(mapping), route_status_codes.ok


@api_v1_bp.route("/feature-areas/<path:feature_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@require_jwt_admin
@require_feature(FEATURE_MANAGE_FEATURE_AREAS)
def feature_areas_set(feature_id):
    """Set areas for a feature (admin only). Body: area_ids (array). Replaces existing."""
    if feature_id not in FEATURE_IDS:
        return jsonify({"error": "Unknown feature_id"}), route_status_codes.bad_request
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), route_status_codes.bad_request
    area_ids = data.get("area_ids")
    if area_ids is not None and not isinstance(area_ids, list):
        return jsonify({"error": "area_ids must be an array"}), route_status_codes.bad_request
    try:
        area_ids = [int(x) for x in (area_ids or [])]
    except (TypeError, ValueError):
        return jsonify({"error": "area_ids must contain integers"}), route_status_codes.bad_request
    ok, err = set_feature_areas_service(feature_id, area_ids)
    if not ok:
        return jsonify({"error": err}), route_status_codes.bad_request
    from app.services.content.area_service import list_feature_areas_mapping
    mapping = next((m for m in list_feature_areas_mapping() if m["feature_id"] == feature_id), {})
    return jsonify(mapping), route_status_codes.ok
