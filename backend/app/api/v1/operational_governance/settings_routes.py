"""Operational settings scope routes."""

from __future__ import annotations

from .common import *

def _settings_get(scope: str):
    from app.services.governance.governance_runtime_service import read_scope_settings

    return _handle(f"settings_get_{scope}", lambda: {"scope": scope, "values": read_scope_settings(scope)})


def _settings_patch(scope: str):
    return _handle(
        f"settings_patch_{scope}",
        lambda: {"scope": scope, "values": update_scope_settings(scope, _body(), _actor_identifier())},
    )


@api_v1_bp.route("/admin/settings/backend", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_backend_get():
    return _settings_get("backend")


@api_v1_bp.route("/admin/settings/backend", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_backend_patch():
    return _settings_patch("backend")


@api_v1_bp.route("/admin/settings/world-engine", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_world_engine_get():
    return _settings_get("world_engine")


@api_v1_bp.route("/admin/settings/world-engine", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_world_engine_patch():
    return _settings_patch("world_engine")


@api_v1_bp.route("/admin/settings/retrieval", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_retrieval_get():
    return _settings_get("retrieval")


@api_v1_bp.route("/admin/settings/retrieval", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_retrieval_patch():
    return _settings_patch("retrieval")


@api_v1_bp.route("/admin/settings/notifications", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_notifications_get():
    return _settings_get("notifications")


@api_v1_bp.route("/admin/settings/notifications", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_notifications_patch():
    return _settings_patch("notifications")


@api_v1_bp.route("/admin/settings/costs", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_costs_get():
    return _settings_get("costs")


@api_v1_bp.route("/admin/settings/costs", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_settings_costs_patch():
    return _settings_patch("costs")

__all__ = (
    '_settings_get',
    '_settings_patch',
    'admin_settings_backend_get',
    'admin_settings_backend_patch',
    'admin_settings_world_engine_get',
    'admin_settings_world_engine_patch',
    'admin_settings_retrieval_get',
    'admin_settings_retrieval_patch',
    'admin_settings_notifications_get',
    'admin_settings_notifications_patch',
    'admin_settings_costs_get',
    'admin_settings_costs_patch',
)
