"""Governance runtime source segment: operational_activity_and_runtime_secret.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
    return route


def _current_bootstrap() -> BootstrapConfig:
    bootstrap = BootstrapConfig.query.order_by(BootstrapConfig.created_at.desc()).first()
    if bootstrap is None:
        bootstrap = BootstrapConfig(
            bootstrap_state="uninitialized",
            bootstrap_locked=False,
            selected_preset=None,
            secret_storage_mode="same_db_encrypted",
            runtime_profile="safe_local",
            generation_execution_mode="mock_only",
            retrieval_execution_mode="disabled",
            validation_execution_mode="schema_only",
            provider_selection_mode="local_only",
            reopen_requires_elevated_auth=True,
            trust_anchor_metadata_json={},
        )
        db.session.add(bootstrap)
        _seed_default_presets()
        db.session.commit()
    return bootstrap


def get_runtime_modes() -> dict:
    bootstrap = _current_bootstrap()
    return {
        "generation_execution_mode": bootstrap.generation_execution_mode,
        "retrieval_execution_mode": bootstrap.retrieval_execution_mode,
        "validation_execution_mode": bootstrap.validation_execution_mode,
        "provider_selection_mode": bootstrap.provider_selection_mode,
        "runtime_profile": bootstrap.runtime_profile,
    }


def update_runtime_modes(payload: dict, actor: str) -> dict:
    bootstrap = _current_bootstrap()
    updates = {
        "generation_execution_mode": payload.get("generation_execution_mode", bootstrap.generation_execution_mode),
        "retrieval_execution_mode": payload.get("retrieval_execution_mode", bootstrap.retrieval_execution_mode),
        "validation_execution_mode": payload.get("validation_execution_mode", bootstrap.validation_execution_mode),
        "provider_selection_mode": payload.get("provider_selection_mode", bootstrap.provider_selection_mode),
        "runtime_profile": payload.get("runtime_profile", bootstrap.runtime_profile),
    }
    _validate_runtime_modes(updates)
    for key, value in updates.items():
        setattr(bootstrap, key, value)
    _audit("runtime_modes_updated", "ai_runtime", "runtime_modes", actor, "Runtime modes updated.", updates)
    db.session.commit()
    return {"updated": True, "runtime_profile": bootstrap.runtime_profile, "effective_generation_execution_mode": bootstrap.generation_execution_mode}


def _validate_runtime_modes(modes: dict) -> None:
    generation_mode = modes["generation_execution_mode"]
    providers = AIProviderConfig.query.filter_by(is_enabled=True).all()
    routes = AITaskRoute.query.filter_by(is_enabled=True).all()
    real_provider_ids = {p.provider_id for p in providers if p.provider_type != "mock" and p.credential_configured}
    route_models: set[str] = set()
    has_mock_fallback = False
    for route in routes:
        for mid in (route.preferred_model_id, route.fallback_model_id):
            if mid:
                model = db.session.get(AIModelConfig, mid)
                if model and model.provider_id in real_provider_ids and model.is_enabled and _is_generation_model(model):
                    route_models.add(mid)
        if route.mock_model_id:
            model = db.session.get(AIModelConfig, route.mock_model_id)
            if model and model.is_enabled and model.model_role == "mock":
                has_mock_fallback = True
    if generation_mode in {"ai_only", "routed_llm_slm"} and (not real_provider_ids or not route_models):
        raise governance_error(
'''
