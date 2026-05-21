"""AI route and runtime configuration routes."""

from __future__ import annotations

from .common import *

@api_v1_bp.route("/admin/ai/routes", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_routes_list():
    return _handle("route_list", lambda: {"routes": list_routes()})


@api_v1_bp.route("/admin/ai/routes", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_route_create():
    return _handle("route_create", lambda: {"route_id": create_route(_body(), _actor_identifier()).route_id, "created": True})


@api_v1_bp.route("/admin/ai/routes/<route_id>", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_route_update(route_id: str):
    return _handle("route_update", lambda: {"route_id": update_route(route_id, _body(), _actor_identifier()).route_id, "updated": True})


@api_v1_bp.route("/admin/ai/runtime-readiness", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_runtime_readiness():
    return _handle("runtime_readiness", evaluate_runtime_readiness)


@api_v1_bp.route("/admin/runtime/modes", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_runtime_modes_get():
    return _handle("runtime_modes_get", get_runtime_modes)


@api_v1_bp.route("/admin/runtime/modes", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_runtime_modes_patch():
    return _handle("runtime_modes_patch", lambda: update_runtime_modes(_body(), _actor_identifier()))


@api_v1_bp.route("/admin/runtime/resolved-config", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_runtime_resolved_config_get():
    return _handle("runtime_resolved_config_get", lambda: build_resolved_runtime_config(persist_snapshot=False, actor=_actor_identifier()))


@api_v1_bp.route("/admin/runtime/reload-resolved-config", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_runtime_resolved_config_reload():
    return _handle("runtime_resolved_config_reload", lambda: build_resolved_runtime_config(persist_snapshot=True, actor=_actor_identifier()))

__all__ = (
    'admin_ai_routes_list',
    'admin_ai_route_create',
    'admin_ai_route_update',
    'admin_ai_runtime_readiness',
    'admin_runtime_modes_get',
    'admin_runtime_modes_patch',
    'admin_runtime_resolved_config_get',
    'admin_runtime_resolved_config_reload',
)
