"""Governance runtime source segment: resolved_config_and_default_providers.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
    resolved = {
        "config_version": config_version,
        "generated_at": generated_at.isoformat(),
        "generation_execution_mode": bootstrap.generation_execution_mode,
        "retrieval_execution_mode": bootstrap.retrieval_execution_mode,
        "validation_execution_mode": bootstrap.validation_execution_mode,
        "runtime_profile": bootstrap.runtime_profile,
        "provider_selection_mode": bootstrap.provider_selection_mode,
        "providers": providers_out,
        "models": models_out,
        "routes": resolved_routes,
        "prompt_store": prompt_store_bundle,
        **scoped_settings,
    }
    if persist_snapshot:
        _persist_resolved_snapshot(
            config_version=config_version,
            bootstrap=bootstrap,
            resolved=resolved,
            actor=actor,
        )
        rebind: dict[str, object] = {"attempted": False, "skipped": True}
        try:
            from app.services.game.game_service import has_complete_play_service_config, reload_play_story_runtime_governed_config

            if has_complete_play_service_config():
                rebind["skipped"] = False
                rebind["attempted"] = True
                rebind.update(reload_play_story_runtime_governed_config())
        except Exception as exc:  # noqa: BLE001 — operator-facing best-effort rebind must not roll back DB snapshot
            rebind["skipped"] = False
            rebind["attempted"] = True
            rebind["ok"] = False
            rebind["error"] = str(exc)[:500]
        resolved["world_engine_story_runtime_rebind"] = rebind
    return resolved


def get_active_runtime_snapshot() -> dict | None:
    """Return active resolved snapshot, if one exists."""
    row = ResolvedRuntimeConfigSnapshot.query.filter_by(is_active=True).order_by(ResolvedRuntimeConfigSnapshot.generated_at.desc()).first()
    if row is None:
        return None
    return row.resolved_config_json or None


def _seed_default_providers(actor: str) -> None:
    """Seed provider templates from all presets with their default base URLs."""
    all_providers: dict[str, dict] = {}
    for preset in _DEFAULT_PRESETS:
        for template in preset.get("default_provider_templates_json") or []:
            provider_type = template.get("provider_type", "").strip()
            if not provider_type or provider_type == "mock":
                continue
            key = provider_type
            if key not in all_providers:
                contract = _provider_contract(provider_type)
                all_providers[key] = {
                    "provider_id": provider_type,
                    "provider_type": provider_type,
                    "display_name": template.get("display_name", provider_type),
                    "base_url": template.get("base_url") or contract.get("default_base_url"),
                    "is_enabled": template.get("enabled_by_default", False),
                    "is_local": contract.get("is_local_default", False),
                    "supports_structured_output": contract.get("capabilities", {}).get("structured_json_output", False),
                    "credential_configured": False,
                    "health_status": "unknown",
                }
    for provider_config in all_providers.values():
        if db.session.get(AIProviderConfig, provider_config["provider_id"]) is None:
            db.session.add(AIProviderConfig(**provider_config))
    _audit("default_providers_seeded", "ai_runtime", "system", actor, "Default provider templates seeded.", {})
'''
