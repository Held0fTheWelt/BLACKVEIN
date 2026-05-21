"""AI model governance routes."""

from __future__ import annotations

from .common import *

@api_v1_bp.route("/admin/ai/models", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_models_list():
    return _handle("model_list", lambda: {"models": list_models()})


@api_v1_bp.route("/admin/ai/models", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_model_create():
    return _handle("model_create", lambda: {"model_id": create_model(_body(), _actor_identifier()).model_id, "created": True})


@api_v1_bp.route("/admin/ai/models/<model_id>", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_model_update(model_id: str):
    return _handle("model_update", lambda: {"model_id": update_model(model_id, _body(), _actor_identifier()).model_id, "updated": True})


@api_v1_bp.route("/admin/ai/models/<model_id>", methods=["DELETE"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_model_delete(model_id: str):
    return _handle("model_delete", lambda: delete_model(model_id, _actor_identifier()))


@api_v1_bp.route("/admin/ai/models/<model_id>/test", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_ai_model_test(model_id: str):
    return _handle("model_test", lambda: test_model_connection(model_id, _actor_identifier()))

__all__ = (
    'admin_ai_models_list',
    'admin_ai_model_create',
    'admin_ai_model_update',
    'admin_ai_model_delete',
    'admin_ai_model_test',
)
