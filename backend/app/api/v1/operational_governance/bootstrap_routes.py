"""Bootstrap and public status routes."""

from __future__ import annotations

from .common import *

@api_v1_bp.route("/admin/bootstrap/status", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_bootstrap_status():
    return _handle("bootstrap_status", lambda: get_bootstrap_status())


@api_v1_bp.route("/bootstrap/public-status", methods=["GET"])
@limiter.limit("120 per minute")
def bootstrap_public_status():
    """Public, non-sensitive bootstrap readiness signal for docker-up guidance."""
    try:
        status = get_bootstrap_status()
        return ok(
            {
                "bootstrap_required": status["bootstrap_required"],
                "bootstrap_locked": status["bootstrap_locked"],
                "available_presets": status["available_presets"],
            }
        )
    except GovernanceError as err:
        return fail_from_error(err)


@api_v1_bp.route("/admin/bootstrap/presets", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_bootstrap_presets():
    return _handle("bootstrap_presets", lambda: {"presets": list_bootstrap_presets()})


@api_v1_bp.route("/admin/bootstrap/initialize", methods=["POST"])
@limiter.limit("10 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_bootstrap_initialize():
    return _handle("bootstrap_initialize", lambda: initialize_bootstrap(_body(), _actor_identifier()))


@api_v1_bp.route("/admin/bootstrap/reopen", methods=["POST"])
@limiter.limit("10 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_bootstrap_reopen():
    return _handle("bootstrap_reopen", lambda: reopen_bootstrap(_body(), _actor_identifier()))

__all__ = (
    'admin_bootstrap_status',
    'bootstrap_public_status',
    'admin_bootstrap_presets',
    'admin_bootstrap_initialize',
    'admin_bootstrap_reopen',
)
