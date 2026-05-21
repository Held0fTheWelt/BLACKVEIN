"""Governance runtime source segment: runtime_readiness_summary.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
        provider_id=provider_id,
        model_name=model_name,
        display_name=(payload.get("display_name") or model_name).strip(),
        model_role=model_role,
        is_enabled=bool(payload.get("is_enabled", True)),
        structured_output_capable=bool(payload.get("supports_structured_output", payload.get("structured_output_capable", False))),
        timeout_seconds=int(payload.get("timeout_seconds", 30)),
        max_context_tokens=payload.get("max_context_tokens"),
        cost_method=(payload.get("cost_method") or "none").strip(),
        input_price_per_1k=Decimal(str(payload["input_price_per_1k"])) if payload.get("input_price_per_1k") is not None else None,
        output_price_per_1k=Decimal(str(payload["output_price_per_1k"])) if payload.get("output_price_per_1k") is not None else None,
        flat_request_price=Decimal(str(payload["flat_request_price"])) if payload.get("flat_request_price") is not None else None,
    )
    db.session.add(model)
    _audit("model_created", "ai_runtime", model_id, actor, "Model created.", {"provider_id": provider_id})
    db.session.commit()
    return model


def update_model(model_id: str, payload: dict, actor: str) -> AIModelConfig:
    model = db.session.get(AIModelConfig, model_id)
    if model is None:
        raise governance_error("model_not_found", f"Model '{model_id}' not found.", 404, {"model_id": model_id})

    for key in (
        "model_name",
        "display_name",
        "is_enabled",
        "structured_output_capable",
        "timeout_seconds",
        "max_context_tokens",
        "cost_method",
    ):
        if key in payload:
            setattr(model, key, payload[key])

    if "model_role" in payload or "model_name" in payload:
        model.model_role = _normalize_model_role(payload.get("model_role", model.model_role), model_name=model.model_name)

    for key in ("input_price_per_1k", "output_price_per_1k", "flat_request_price"):
        if key in payload:
            value = payload[key]
            setattr(model, key, Decimal(str(value)) if value is not None else None)

    model.updated_at = datetime.now(timezone.utc)
    _audit("model_updated", "ai_runtime", model_id, actor, "Model updated.", {})
    db.session.commit()
    _attempt_runtime_rebind()

    return model


def _candidate_mock_model_id(*, excluding_model_id: str) -> str | None:
    preferred = db.session.get(AIModelConfig, "mock_deterministic")
    if preferred and preferred.model_id != excluding_model_id and preferred.is_enabled and preferred.model_role == "mock":
        return preferred.model_id
    row = (
        AIModelConfig.query.filter(
            AIModelConfig.model_id != excluding_model_id,
            AIModelConfig.is_enabled.is_(True),
            AIModelConfig.model_role == "mock",
        )
        .order_by(AIModelConfig.model_id.asc())
        .first()
    )
    return row.model_id if row is not None else None


def delete_model(model_id: str, actor: str) -> dict:
    model = db.session.get(AIModelConfig, model_id)
    if model is None:
        raise governance_error("model_not_found", f"Model '{model_id}' not found.", 404, {"model_id": model_id})
'''
