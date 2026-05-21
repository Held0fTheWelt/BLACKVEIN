"""Governance runtime source segment: runtime_readiness_issues.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
        )

    out: list[dict] = []
    for row in rows:
        provider = providers.get(row.provider_id)
        normalized_role = _normalize_model_role(row.model_role, model_name=row.model_name)
        provider_runtime_eligible = _provider_runtime_eligible(provider)
        runtime_eligible = row.is_enabled and provider_runtime_eligible
        generation_runtime_eligible = runtime_eligible and _is_generation_model(row)
        embedding_runtime_eligible = runtime_eligible and _is_embedding_model(row)
        blockers: list[str] = []
        if provider is None:
            blockers.append("provider_missing")
        else:
            if not provider.is_enabled:
                blockers.append("provider_disabled")
            if provider.health_status in {"failing", "disabled"}:
                blockers.append(f"provider_health_{provider.health_status}")
            contract = _provider_contract(provider.provider_type)
            if bool(contract.get("requires_credential")) and not provider.credential_configured:
                blockers.append("provider_credential_missing")
        if not row.is_enabled:
            blockers.append("model_disabled")
        out.append(
            {
                "model_id": row.model_id,
                "provider_id": row.provider_id,
                "model_name": row.model_name,
                "display_name": row.display_name,
                "model_role": normalized_role,
                "is_enabled": row.is_enabled,
                "structured_output_capable": row.structured_output_capable,
                "timeout_seconds": row.timeout_seconds,
                "max_context_tokens": row.max_context_tokens,
                "cost_method": row.cost_method,
                "input_price_per_1k": str(row.input_price_per_1k) if row.input_price_per_1k is not None else None,
                "output_price_per_1k": str(row.output_price_per_1k) if row.output_price_per_1k is not None else None,
                "flat_request_price": str(row.flat_request_price) if row.flat_request_price is not None else None,
                "provider_runtime_eligible": provider_runtime_eligible,
                "runtime_eligible": runtime_eligible,
                "generation_runtime_eligible": generation_runtime_eligible,
                "embedding_runtime_eligible": embedding_runtime_eligible,
                "readiness_blockers": blockers,
            }
        )
    return out


def create_model(payload: dict, actor: str) -> AIModelConfig:
    provider_id = (payload.get("provider_id") or "").strip()
    provider = db.session.get(AIProviderConfig, provider_id)
    if provider is None:
        raise governance_error("provider_not_found", f"Provider '{provider_id}' not found.", 404, {"provider_id": provider_id})
    if not provider.is_enabled:
        raise governance_error(
            "provider_not_eligible_for_model_assignment",
            "Cannot assign models to a disabled provider.",
            409,
            {"provider_id": provider_id},
        )
    model_name = (payload.get("model_name") or "").strip()
    if not model_name:
        raise governance_error("setting_value_invalid", "model_name is required.", 400, {})
    # model_id: operator-facing internal identifier. If omitted, derive one deterministically
    # from provider_id + model_name so UI, docs, and tests can stay compact.
    model_id = (payload.get("model_id") or "").strip() or _derive_model_id(provider_id, model_name)
    model = db.session.get(AIModelConfig, model_id)
    if model:
        return model
    model_role = _normalize_model_role(payload.get("model_role"), model_name=model_name)
    model = AIModelConfig(
        model_id=model_id,
'''
