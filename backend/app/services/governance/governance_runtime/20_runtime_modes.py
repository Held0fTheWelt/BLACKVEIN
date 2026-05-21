"""Governance runtime source segment: runtime_modes.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
        "Model deleted and route references repaired.",
        {"route_count": len(route_changes)},
    )
    db.session.commit()
    rebind = _attempt_runtime_rebind()
    return {
        "model_id": model_id,
        "deleted": True,
        "affected_route_count": len(route_changes),
        "affected_routes": route_changes,
        "world_engine_story_runtime_rebind": rebind,
    }


def test_model_connection(model_id: str, actor: str) -> dict:
    model = db.session.get(AIModelConfig, model_id)
    if model is None:
        raise governance_error("model_not_found", f"Model '{model_id}' not found.", 404, {"model_id": model_id})
    if not model.is_enabled:
        raise governance_error("model_disabled", "Model is disabled.", 409, {"model_id": model_id})

    provider = db.session.get(AIProviderConfig, model.provider_id)
    if provider is None:
        raise governance_error("provider_not_found", f"Provider '{model.provider_id}' not found.", 404, {"provider_id": model.provider_id})
    if not provider.is_enabled:
        raise governance_error("provider_disabled", "Provider is disabled.", 409, {"provider_id": provider.provider_id})

    contract = _provider_contract(provider.provider_type)
    capabilities = contract.get("capabilities", {}) if isinstance(contract.get("capabilities"), dict) else {}
    if _is_embedding_model(model):
        supported = bool(capabilities.get("embeddings"))
        unsupported_message = "Provider does not expose a supported embedding test path."
    else:
        supported = bool(capabilities.get("text_generation"))
        unsupported_message = "Provider does not expose a supported text-generation test path."
    if not supported:
        raise governance_error(
            "model_test_unsupported",
            unsupported_message,
            409,
            {"provider_id": provider.provider_id, "provider_type": provider.provider_type},
        )

    secret = _active_provider_secret(provider.provider_id) if provider.credential_configured else None
    if bool(contract.get("requires_credential")) and not secret:
        raise governance_error(
            "provider_credential_required",
            "Provider requires credential before model test.",
            400,
            {"provider_id": provider.provider_id},
        )

    base_url = _normalize_provider_url(provider.base_url, contract)
    if provider.provider_type == "mock":
        adapter = MockModelAdapter()
    elif provider.provider_type == "ollama":
        adapter = OllamaAdapter(base_url=base_url)
    elif provider.provider_type in {"openai", "openrouter"} or bool(contract.get("openai_compatible")):
        adapter = OpenAIChatAdapter(base_url=base_url, api_key=secret)
    else:
        raise governance_error(
            "model_test_unsupported",
            "Provider type is not yet supported for concrete model tests.",
            409,
            {"provider_id": provider.provider_id, "provider_type": provider.provider_type},
        )

    started = perf_counter()
    try:
        if provider.provider_type == "openai":
            probe = _minimal_openai_probe(
                base_url=base_url,
'''
