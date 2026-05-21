"""Governance runtime source segment: resolved_runtime_snapshots.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
                "runtime_eligible": row.is_enabled and ((pref_ok or fb_ok) or (row.use_mock_when_provider_unavailable and mock_ok)),
                "readiness_blockers": blockers,
            }
        )
    return out


def _readiness_suggested_action(*, code: str, entity_id: str | None, limitation: str | None = None) -> str:
    """Return a concrete operator-facing remediation line for readiness blockers."""
    if code == "enabled_non_mock_provider_missing":
        return (
            "Create or enable a non-mock provider (openai, ollama, openrouter, or anthropic), set base URL when prompted, "
            "store the API key for cloud providers, then run **Test provider health** on this page."
        )
    if code == "enabled_non_mock_model_missing":
        return (
            "Under **Model governance**, create at least one enabled model bound to an eligible non-mock provider, "
            "then attach it to a route."
        )
    if code == "enabled_ai_route_missing":
        return (
            "Under **Route governance**, enable a route whose preferred or fallback model points at a non-mock model on a healthy provider."
        )
    if code.startswith("provider_") and entity_id:
        lim = limitation or code.removeprefix("provider_")
        if lim == "credential_missing":
            return (
                f"Open provider `{entity_id}`: paste the API key in the credential field, save, then run **Test provider health**."
            )
        if lim.startswith("health_"):
            return (
                f"Fix base URL and credentials for `{entity_id}`, then run **Test provider health** until status is healthy."
            )
        if lim == "no_enabled_models":
            return f"Create or enable at least one model for provider `{entity_id}`."
        return f"Review provider `{entity_id}` in **Provider governance** and clear limitation `{lim}`."
    if code.startswith("route_") and entity_id:
        return (
            f"Edit route `{entity_id}`: ensure preferred/fallback models reference enabled models on healthy providers, "
            "or enable a valid mock fallback when **Use mock when provider unavailable** is checked."
        )
    return "Review **Runtime readiness** details and the raw inventory below."


def _has_enabled_non_mock_provider(provider_rows: list[dict]) -> bool:
    return any(bool(p.get("is_enabled")) and p.get("provider_type") != "mock" for p in provider_rows)


def _task_routes_operator_green(route_rows: list[dict]) -> bool:
    """True when every enabled route has a working preferred/fallback chain (matches rail AI-path semantics)."""
    enabled = [r for r in route_rows if r.get("is_enabled")]
    if not enabled:
        return False
    return all(bool(r.get("ai_path_ready")) for r in enabled)


def evaluate_runtime_readiness() -> dict:
    """Deterministic readiness and blocker report for operator runtime decisions."""
    provider_rows = list_providers()
    model_rows = list_models()
    route_rows = list_routes()

    enabled_non_mock_provider = any(
        p["eligible_for_runtime_assignment"] and p["provider_type"] != "mock" for p in provider_rows
    )
    enabled_non_mock_model = any(
        m.get("generation_runtime_eligible")
        and (next((p for p in provider_rows if p["provider_id"] == m["provider_id"]), {}).get("provider_type") != "mock")
        for m in model_rows
    )
    enabled_ai_route = any(r["ai_path_ready"] and r.get("route_model_role") != _EMBEDDING_MODEL_ROLE for r in route_rows)

'''
