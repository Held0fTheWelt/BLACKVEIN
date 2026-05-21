"""Governance runtime source segment: runtime_mode_route_selection.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
            "generation_mode_invalid",
            "This generation mode needs at least one enabled non-mock provider with a stored credential, "
            "and at least one enabled AI task route whose preferred or fallback model uses that provider. "
            "Create a provider, save its API key, add models and routes, or stay on mock_only until then.",
            400,
            {"generation_execution_mode": generation_mode},
        )
    if generation_mode == "hybrid_routed_with_mock_fallback" and not has_mock_fallback:
        raise governance_error(
            "route_requires_mock_model_for_hybrid_mode",
            "Hybrid mode requires a mock-capable fallback route.",
            409,
            {},
        )


def _resolve_provider_selection(providers: list[AIProviderConfig], provider_selection_mode: str) -> list[AIProviderConfig]:
    if provider_selection_mode == "local_only":
        selected = [p for p in providers if p.is_local]
    elif provider_selection_mode == "remote_preferred":
        remote = [p for p in providers if not p.is_local]
        selected = remote or providers
    else:
        selected = providers
    return selected


def _validate_and_resolve_routes(*, routes: list[AITaskRoute], models_by_id: dict[str, AIModelConfig], selected_provider_ids: set[str], generation_execution_mode: str) -> list[dict]:
    """Validate route model references and return resolved route payload.

    Routes are allowed to reference models from non-selectable providers (e.g., unconfigured)
    as long as at least one model in the route is selectable. This allows partial provider
    configuration (e.g., OpenAI ready, Anthropic/OpenRouter/Ollama still being configured).
    """
    missing_required_tasks = {task for task in _REQUIRED_TASK_KINDS}
    resolved_routes: list[dict] = []
    for route in routes:
        missing_required_tasks.discard(route.task_kind)
        route_model_role = _route_model_role_kind(task_kind=route.task_kind, route_id=route.route_id)

        # Validate all model references exist, and check if route has at least one selectable model
        has_selectable_model = False
        for ref_name in ("preferred_model_id", "fallback_model_id", "mock_model_id"):
            ref_id = getattr(route, ref_name)
            if ref_id is None:
                continue
            model = models_by_id.get(ref_id)
            if model is None:
                raise governance_error("resolved_config_generation_failed", "Route references missing model.", 500, {"route_id": route.route_id, "model_id": ref_id})
            if ref_name in {"preferred_model_id", "fallback_model_id"}:
                model_role = (model.model_role or "").strip().lower()
                if model_role == "mock" and generation_execution_mode == "mock_only":
                    pass
                elif route_model_role == _EMBEDDING_MODEL_ROLE:
                    if not _is_embedding_model(model):
                        raise governance_error(
                            "resolved_config_generation_failed",
                            "Retrieval embedding route preferred/fallback reference is not an embedding model.",
                            500,
                            {"route_id": route.route_id, "model_id": ref_id, "model_role": model.model_role},
                        )
                elif not _is_generation_model(model):
                    raise governance_error(
                        "resolved_config_generation_failed",
                        "Route preferred/fallback reference is not a generation model.",
                        500,
                        {"route_id": route.route_id, "model_id": ref_id, "model_role": model.model_role},
                    )
            if ref_name == "mock_model_id" and (model.model_role or "").strip().lower() != "mock":
                raise governance_error(
                    "resolved_config_generation_failed",
                    "Route mock reference is not a mock model.",
'''
