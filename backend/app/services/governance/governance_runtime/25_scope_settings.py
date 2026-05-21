"""Governance runtime source segment: scope_settings.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
    if enabled_non_mock_provider and not enabled_non_mock_model:
        next_actions.append("Create or enable a model on an eligible non-mock provider.")
    if enabled_non_mock_model and not enabled_ai_route:
        next_actions.append("Assign preferred or fallback non-mock models to at least one enabled route.")
    if ai_only_valid:
        next_actions.append("Switch generation_execution_mode to ai_only when desired.")

    if ai_only_valid:
        readiness_headline = "AI-only generation is currently valid for governed routes."
        readiness_severity = "healthy"
    elif mock_only_required:
        readiness_headline = "Stay on mock_only (or hybrid with mock fallback) until the blockers below are cleared."
        readiness_severity = "blocked" if len([b for b in blockers if b["entity_id"] is None]) else "degraded"
    else:
        readiness_headline = "Review readiness signals before enabling ai_only."
        readiness_severity = "degraded"

    readiness_legend: list[str] = [
        "mock_only_required=true means at least one governed AI precondition is still missing; keep generation_execution_mode on mock_only until blockers clear.",
        "ai_only_valid=true means an eligible non-mock provider, a runtime-eligible model on it, and at least one enabled route with a working AI model chain are all satisfied.",
        "Each blocker lists entity_type/entity_id when a specific provider or route is at fault; global rows (no entity_id) describe missing prerequisites.",
        "When at least one non-mock provider is enabled, disabled providers are omitted from provider-scoped readiness rows.",
        "Provider no_enabled_models rows are omitted when every enabled task route already reports AI path ready.",
    ]

    play_story_runtime_governance: dict[str, object] = {"status": "skipped", "reason": "play_service_not_configured"}
    try:
        from flask import has_app_context

        from app.services.game.game_service import GameServiceError, get_play_story_runtime_config_status, has_complete_play_service_config

        if has_app_context() and has_complete_play_service_config():
            probe = get_play_story_runtime_config_status()
            st = probe.get("runtime_config_status") if isinstance(probe, dict) else {}
            play_story_runtime_governance = {"status": "ok", "runtime_config_status": st}
            if not isinstance(st, dict):
                play_story_runtime_governance = {"status": "error", "message": "unexpected_runtime_config_status_shape"}
            else:
                if not bool(st.get("governed_runtime_active")):
                    blockers.append(
                        {
                            "code": "play_story_runtime_not_governed",
                            "entity_type": "play_service",
                            "entity_id": None,
                            "message": "Play-service story runtime is not bound to governed resolved config (or execution is blocked).",
                            "suggested_action": "Rebuild resolved runtime config from Administration Center, verify BACKEND_RUNTIME_CONFIG_URL and INTERNAL_RUNTIME_CONFIG_TOKEN on the play service, then POST /api/internal/story/runtime/reload-config or restart the play service.",
                        }
                    )
                if bool(st.get("legacy_default_registry_path")):
                    # P1-4: This blocker can no longer occur (escape hatch removed in P0-1)
                    # Kept for backwards compatibility with older play-service versions
                    blockers.append(
                        {
                            "code": "play_story_runtime_legacy_default_registry",
                            "entity_type": "play_service",
                            "entity_id": None,
                            "message": "Play-service story runtime reports legacy default registry posture (should not occur in current version).",
                            "suggested_action": "Rebuild governed resolved runtime config and restart play-service.",
                        }
                    )
                if bool(st.get("live_execution_blocked")):
                    blockers.append(
                        {
                            "code": "play_story_runtime_live_execution_blocked",
                            "entity_type": "play_service",
                            "entity_id": None,
                            "message": "Play-service story runtime reports live_execution_blocked.",
                            "suggested_action": "Fix governed runtime configuration completeness, then reload the play-service story runtime from the backend rebuild path.",
                        }
                    )
                if not str(st.get("config_version") or "").strip():
                    blockers.append(
'''
