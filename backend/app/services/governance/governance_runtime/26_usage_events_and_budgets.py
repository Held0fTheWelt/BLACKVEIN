"""Governance runtime source segment: usage_events_and_budgets.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
                        {
                            "code": "play_story_runtime_missing_config_version",
                            "entity_type": "play_service",
                            "entity_id": None,
                            "message": "Play-service story runtime is missing an active config_version.",
                            "suggested_action": "Rebuild resolved runtime config and rebind the play service story runtime.",
                        }
                    )
    except GameServiceError as exc:
        play_story_runtime_governance = {"status": "error", "message": str(exc)}
        blockers.append(
            {
                "code": "play_story_runtime_governance_probe_failed",
                "entity_type": "play_service",
                "entity_id": None,
                "message": f"Backend could not read play-service story runtime governance status: {exc}",
                "suggested_action": "Verify play-service health, internal URL, and X-Play-Service-Key alignment, then retry.",
            }
        )

    if play_story_runtime_governance.get("status") == "error" or any(
        b.get("code", "").startswith("play_story_runtime") for b in blockers
    ):
        if readiness_severity == "healthy":
            readiness_severity = "degraded"
        if readiness_headline.startswith("AI-only generation is currently valid"):
            readiness_headline = "Governance inventory looks eligible, but play-service story-runtime binding needs attention."

    return {
        "mock_only_required": mock_only_required,
        "ai_only_valid": ai_only_valid,
        "readiness_headline": readiness_headline,
        "readiness_severity": readiness_severity,
        "status_semantics": STATUS_SEMANTICS,
        "readiness_legend": readiness_legend,
        "enabled_non_mock_provider_present": enabled_non_mock_provider,
        "enabled_non_mock_model_present": enabled_non_mock_model,
        "enabled_ai_route_present": enabled_ai_route,
        "blockers": blockers,
        "next_actions": next_actions,
        "provider_summary": {
            "total": len(provider_rows),
            "eligible_non_mock": sum(1 for p in provider_rows if p["eligible_for_runtime_assignment"] and p["provider_type"] != "mock"),
        },
        "model_summary": {
            "total": len(model_rows),
            "runtime_eligible_non_mock": sum(
                1
                for m in model_rows
                if m.get("generation_runtime_eligible")
                and (next((p for p in provider_rows if p["provider_id"] == m["provider_id"]), {}).get("provider_type") != "mock")
            ),
        },
        "route_summary": {
            "total": len(route_rows),
            "ai_ready": sum(1 for r in route_rows if r["ai_path_ready"]),
            "runtime_eligible": sum(1 for r in route_rows if r["runtime_eligible"]),
        },
        "task_routes_green": task_routes_green,
        "play_story_runtime_governance": play_story_runtime_governance,
    }


def _ensure_model_exists(
    model_id: str | None,
    *,
    route_field: str | None = None,
    task_kind: str | None = None,
    route_id: str | None = None,
) -> None:
    if model_id is None:
        return
'''
