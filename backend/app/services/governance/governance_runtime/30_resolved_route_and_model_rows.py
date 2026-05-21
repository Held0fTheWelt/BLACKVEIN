"""Governance runtime source segment: resolved_route_and_model_rows.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
                    500,
                    {"route_id": route.route_id, "model_id": ref_id, "model_role": model.model_role},
                )
            if ref_name in {"preferred_model_id", "fallback_model_id"} and model.provider_id in selected_provider_ids:
                has_selectable_model = True
            if ref_name == "mock_model_id" and model.model_role == "mock":
                has_selectable_model = True

        # Only fail if route has NO selectable models in non-mock_only modes
        if not has_selectable_model and generation_execution_mode != "mock_only":
            model_refs = [getattr(route, n) for n in ("preferred_model_id", "fallback_model_id", "mock_model_id") if getattr(route, n)]
            raise governance_error(
                "resolved_config_generation_failed",
                "Route has no selectable models. Add credentials to at least one provider or enable a mock fallback.",
                500,
                {"route_id": route.route_id, "model_ids": model_refs},
            )

        resolved_routes.append(
            {
                "route_id": route.route_id,
                "task_kind": route.task_kind,
                "workflow_scope": route.workflow_scope,
                "preferred_model_id": route.preferred_model_id,
                "fallback_model_id": route.fallback_model_id,
                "mock_model_id": route.mock_model_id,
                "route_model_role": route_model_role,
                "effective_strategy": "hybrid" if route.use_mock_when_provider_unavailable else "strict",
            }
        )
    if missing_required_tasks and generation_execution_mode != "mock_only":
        raise governance_error(
            "resolved_config_generation_failed",
            "Not all required task kinds have enabled routes.",
            500,
            {"missing_task_kinds": sorted(missing_required_tasks)},
        )
    return resolved_routes


def _serialize_provider_rows(providers: list[AIProviderConfig]) -> list[dict]:
    out: list[dict] = []
    for provider in providers:
        contract = _provider_contract(provider.provider_type)

        out.append(
            {
                "provider_id": provider.provider_id,
                "provider_type": provider.provider_type,
                "base_url": _normalize_provider_url(provider.base_url, contract),
                "credential_configured": provider.credential_configured,
                "credential_endpoint": f"/api/v1/internal/provider-credential/{provider.provider_id}" if provider.credential_configured else None,
                "is_enabled": True,
                "health_status": provider.health_status,
                "auth_mode": contract.get("auth_mode"),
                "required_headers": contract.get("required_headers", []),
                "static_headers": contract.get("static_headers", {}),
                "capabilities": contract.get("capabilities", {}),
                "supports_model_discovery": bool(contract.get("supports_model_discovery")),
                "openai_compatible": bool(contract.get("openai_compatible")),
            }
        )
    return out


def _serialize_model_rows(models: list[AIModelConfig], selected_provider_ids: set[str]) -> list[dict]:
    return [
        {
            "model_id": model.model_id,
            "provider_id": model.provider_id,
            "model_name": model.model_name,
            "model_role": _normalize_model_role(model.model_role, model_name=model.model_name),
'''
