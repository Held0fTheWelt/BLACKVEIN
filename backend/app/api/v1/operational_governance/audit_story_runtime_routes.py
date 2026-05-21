"""Governance audit and story runtime experience routes."""

from __future__ import annotations

from .common import *

@api_v1_bp.route("/admin/audit/governance", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_governance_audit():
    limit = min(int(request.args.get("limit", "300")), 1000)
    return _handle("governance_audit", lambda: {"items": list_audit_events(limit=limit)})


@api_v1_bp.route("/admin/story-runtime-experience", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_story_runtime_experience_get():
    from app.services.story_runtime.story_runtime_experience_service import (
        build_story_runtime_experience_truth_surface,
    )

    return _handle(
        "story_runtime_experience_get",
        lambda: build_story_runtime_experience_truth_surface(),
    )


@api_v1_bp.route("/admin/story-runtime-experience", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_story_runtime_experience_update():
    from app.services.story_runtime.story_runtime_experience_service import (
        build_story_runtime_experience_truth_surface,
        update_story_runtime_experience_settings,
    )

    def _do():
        result = update_story_runtime_experience_settings(_body(), _actor_identifier())
        # Rebuild resolved runtime config so world-engine fetches the new
        # Story Runtime Experience section on its next reload call.
        rebind_result = None
        try:
            resolved = build_resolved_runtime_config(persist_snapshot=True, actor=_actor_identifier())
            if isinstance(resolved, dict):
                rebind_result = resolved.get("world_engine_story_runtime_rebind")
        except GovernanceError as exc:
            # Settings are persisted even if full resolve fails; the admin
            # truth surface will reflect the new values on next GET.
            rebind_result = {"attempted": False, "skipped": True, "ok": False, "error": str(exc)}
        truth = build_story_runtime_experience_truth_surface()
        truth["update_warnings"] = result.get("warnings") or []
        truth["world_engine_story_runtime_rebind"] = rebind_result
        return truth

    return _handle("story_runtime_experience_update", _do)

__all__ = (
    'admin_governance_audit',
    'admin_story_runtime_experience_get',
    'admin_story_runtime_experience_update',
)
