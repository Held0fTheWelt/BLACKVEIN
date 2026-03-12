"""Slogan CRUD API. Moderator+ can manage slogans."""
from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.permissions import current_user_can_write_news, get_current_user
from app.extensions import limiter
from app.services import log_activity
from app.services.slogan_service import (
    activate_slogan as activate_slogan_svc,
    create_slogan as create_slogan_svc,
    deactivate_slogan as deactivate_slogan_svc,
    delete_slogan as delete_slogan_svc,
    get_slogan_by_id,
    list_slogans as list_slogans_svc,
    update_slogan as update_slogan_svc,
)
from flask_jwt_extended import jwt_required


def _require_moderator():
    if not get_current_user():
        return None, "User not found"
    if not current_user_can_write_news():
        return None, "Forbidden. Moderator or Admin required."
    return get_current_user(), None


@api_v1_bp.route("/slogans", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def slogans_list():
    """List slogans. Query: category, placement_key, language_code, active_only."""
    user, err = _require_moderator()
    if err:
        return jsonify({"error": err}), 403 if "Forbidden" in err else 404
    category = request.args.get("category", "").strip() or None
    placement_key = request.args.get("placement_key", "").strip() or None
    language_code = request.args.get("language_code", "").strip() or None
    active_only = request.args.get("active_only", "").lower() in ("1", "true", "yes")
    items = list_slogans_svc(category=category, placement_key=placement_key, language_code=language_code, active_only=active_only)
    return jsonify({"items": [s.to_dict() for s in items]}), 200


@api_v1_bp.route("/slogans/<int:slogan_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def slogans_get(slogan_id):
    """Get one slogan by id."""
    user, err = _require_moderator()
    if err:
        return jsonify({"error": err}), 403 if "Forbidden" in err else 404
    slogan = get_slogan_by_id(slogan_id)
    if not slogan:
        return jsonify({"error": "Slogan not found"}), 404
    return jsonify(slogan.to_dict()), 200


@api_v1_bp.route("/slogans", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def slogans_create():
    """Create a slogan. Body: text, category, placement_key, language_code, is_active, is_pinned, priority, valid_from, valid_until."""
    user, err = _require_moderator()
    if err:
        return jsonify({"error": err}), 403 if "Forbidden" in err else 404
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    slogan, err = create_slogan_svc(
        text=data.get("text"),
        category=data.get("category"),
        placement_key=data.get("placement_key"),
        language_code=data.get("language_code"),
        is_active=data.get("is_active", True),
        is_pinned=data.get("is_pinned", False),
        priority=data.get("priority", 0),
        valid_from=data.get("valid_from"),
        valid_until=data.get("valid_until"),
        created_by=user.id,
    )
    if err:
        return jsonify({"error": err}), 400
    log_activity(actor=user, category="admin", action="slogan_created", status="success", message=f"Slogan {slogan.id} created", route=request.path, method=request.method, target_type="slogan", target_id=str(slogan.id))
    return jsonify(slogan.to_dict()), 201


@api_v1_bp.route("/slogans/<int:slogan_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def slogans_update(slogan_id):
    """Update a slogan. Body: any of text, category, placement_key, language_code, is_active, is_pinned, priority, valid_from, valid_until."""
    user, err = _require_moderator()
    if err:
        return jsonify({"error": err}), 403 if "Forbidden" in err else 404
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    slogan, err = update_slogan_svc(
        slogan_id,
        text=data.get("text"),
        category=data.get("category"),
        placement_key=data.get("placement_key"),
        language_code=data.get("language_code"),
        is_active=data.get("is_active"),
        is_pinned=data.get("is_pinned"),
        priority=data.get("priority"),
        valid_from=data.get("valid_from"),
        valid_until=data.get("valid_until"),
        updated_by=user.id,
    )
    if err:
        return jsonify({"error": err}), 400 if "Invalid" in err or "cannot be empty" in err or "required" in err.lower() else 404
    log_activity(actor=user, category="admin", action="slogan_updated", status="success", message=f"Slogan {slogan.id} updated", route=request.path, method=request.method, target_type="slogan", target_id=str(slogan.id))
    return jsonify(slogan.to_dict()), 200


@api_v1_bp.route("/slogans/<int:slogan_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@jwt_required()
def slogans_delete(slogan_id):
    """Delete a slogan."""
    user, err = _require_moderator()
    if err:
        return jsonify({"error": err}), 403 if "Forbidden" in err else 404
    ok, err = delete_slogan_svc(slogan_id)
    if not ok:
        return jsonify({"error": err or "Slogan not found"}), 404
    log_activity(actor=user, category="admin", action="slogan_deleted", status="success", message=f"Slogan {slogan_id} deleted", route=request.path, method=request.method, target_type="slogan", target_id=str(slogan_id))
    return jsonify({"message": "Slogan deleted"}), 200


@api_v1_bp.route("/slogans/<int:slogan_id>/activate", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def slogans_activate(slogan_id):
    """Set slogan is_active=True."""
    user, err = _require_moderator()
    if err:
        return jsonify({"error": err}), 403 if "Forbidden" in err else 404
    slogan, err = activate_slogan_svc(slogan_id)
    if err:
        return jsonify({"error": err}), 404
    return jsonify(slogan.to_dict()), 200


@api_v1_bp.route("/slogans/<int:slogan_id>/deactivate", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def slogans_deactivate(slogan_id):
    """Set slogan is_active=False."""
    user, err = _require_moderator()
    if err:
        return jsonify({"error": err}), 403 if "Forbidden" in err else 404
    slogan, err = deactivate_slogan_svc(slogan_id)
    if err:
        return jsonify({"error": err}), 404
    return jsonify(slogan.to_dict()), 200
