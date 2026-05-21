"""Governance runtime source segment: scope_settings_and_snapshot_persistence.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
            "timeout_seconds": model.timeout_seconds,
            "structured_output_capable": model.structured_output_capable,
        }
        for model in models
        if model.provider_id in selected_provider_ids
    ]


def _collect_scope_settings() -> dict[str, dict]:
    # Story Runtime Experience is a first-class section — it rides the same
    # resolved-runtime-config propagation path as the rest of governance, so
    # the world-engine can honor it without a parallel fetch.
    from app.services.story_runtime.story_runtime_experience_service import (
        serialize_for_resolved_runtime_config as _serialize_story_runtime_experience,
    )

    return {
        "backend_settings": read_scope_settings("backend"),
        "world_engine_settings": read_scope_settings("world_engine"),
        "retrieval_settings": read_scope_settings("retrieval"),
        "cost_settings": read_scope_settings("costs"),
        "notification_settings": read_scope_settings("notifications"),
        "story_runtime_experience": _serialize_story_runtime_experience(),
    }


def _persist_resolved_snapshot(*, config_version: str, bootstrap: BootstrapConfig, resolved: dict, actor: str) -> None:
    ResolvedRuntimeConfigSnapshot.query.filter_by(is_active=True).update({"is_active": False})
    db.session.add(
        ResolvedRuntimeConfigSnapshot(
            snapshot_id=f"snap_{uuid4().hex}",
            config_version=config_version,
            generation_execution_mode=bootstrap.generation_execution_mode,
            retrieval_execution_mode=bootstrap.retrieval_execution_mode,
            validation_execution_mode=bootstrap.validation_execution_mode,
            runtime_profile=bootstrap.runtime_profile,
            provider_selection_mode=bootstrap.provider_selection_mode,
            resolved_config_json=resolved,
            is_active=True,
        )
    )
    _audit("resolved_config_rebuilt", "ai_runtime", config_version, actor, "Resolved runtime config rebuilt.", {})
    db.session.commit()


def build_resolved_runtime_config(*, persist_snapshot: bool, actor: str) -> dict:
    """Resolve active runtime config and validate route completeness."""
    bootstrap = _current_bootstrap()
    providers = AIProviderConfig.query.filter_by(is_enabled=True).all()
    providers = _resolve_provider_selection(providers, bootstrap.provider_selection_mode)
    models = AIModelConfig.query.filter_by(is_enabled=True).all()
    models_by_id = {m.model_id: m for m in models}
    selected_provider_ids = {p.provider_id for p in providers}
    routes = AITaskRoute.query.filter_by(is_enabled=True).all()
    resolved_routes = _validate_and_resolve_routes(
        routes=routes,
        models_by_id=models_by_id,
        selected_provider_ids=selected_provider_ids,
        generation_execution_mode=bootstrap.generation_execution_mode,
    )
    providers_out = _serialize_provider_rows(providers)
    models_out = _serialize_model_rows(models, selected_provider_ids)
    scoped_settings = _collect_scope_settings()
    try:
        from app.services.prompts.prompt_store_service import get_active_prompt_bundle

        prompt_store_bundle = get_active_prompt_bundle()
    except Exception:
        prompt_store_bundle = {"schema_version": "prompt_store_bundle.v1", "count": 0, "prompts": []}

    generated_at = datetime.now(timezone.utc)
    config_version = f"cfg_{generated_at.strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
'''
