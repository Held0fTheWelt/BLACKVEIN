"""Governance runtime source segment: scope_delete_and_usage_ingest.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
        _audit("setting_updated", scope, setting_key, actor, "Setting updated.", {"scope": scope})
    db.session.commit()
    return read_scope_settings(scope)


def delete_scope_setting(scope: str, setting_key: str, actor: str) -> bool:
    """Remove one scope setting row when present (returns True if deleted)."""
    setting_id = _slug(f"{scope}_{setting_key}")
    row = db.session.get(SystemSettingRecord, setting_id)
    if row is None:
        return False
    db.session.delete(row)
    _audit("setting_deleted", scope, setting_key, actor, "Setting removed.", {"scope": scope})
    db.session.commit()
    return True


def ingest_usage_event(payload: dict, actor: str) -> dict:
    event = AIUsageEvent(
        usage_event_id=payload.get("usage_event_id") or f"evt_{uuid4().hex}",
        provider_id=payload.get("provider_id"),
        model_id=payload.get("model_id"),
        task_kind=payload["task_kind"],
        workflow_scope=payload.get("workflow_scope") or "global",
        request_id=payload["request_id"],
        success=bool(payload.get("success", True)),
        latency_ms=payload.get("latency_ms"),
        input_tokens=payload.get("input_tokens"),
        output_tokens=payload.get("output_tokens"),
        provider_reported_cost=Decimal(str(payload["provider_reported_cost"])) if payload.get("provider_reported_cost") is not None else None,
        estimated_cost=Decimal(str(payload["estimated_cost"])) if payload.get("estimated_cost") is not None else None,
        cost_method_used=payload.get("cost_method_used") or "none",
        degraded_mode_used=bool(payload.get("degraded_mode_used", False)),
        retry_used=bool(payload.get("retry_used", False)),
        fallback_used=bool(payload.get("fallback_used", False)),
    )
    db.session.add(event)
    _audit("usage_event_ingested", "costs", event.usage_event_id, actor, "Usage event ingested.", {})
    db.session.commit()
    return {"usage_event_id": event.usage_event_id, "created_at": event.created_at.isoformat() if event.created_at else None}


def list_usage_events(limit: int = 100) -> list[dict]:
    rows = AIUsageEvent.query.order_by(AIUsageEvent.created_at.desc()).limit(limit).all()
    return [
        {
            "usage_event_id": row.usage_event_id,
            "provider_id": row.provider_id,
            "model_id": row.model_id,
            "task_kind": row.task_kind,
            "workflow_scope": row.workflow_scope,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
            "provider_reported_cost": str(row.provider_reported_cost) if row.provider_reported_cost is not None else None,
            "estimated_cost": str(row.estimated_cost) if row.estimated_cost is not None else None,
            "cost_method_used": row.cost_method_used,
            "fallback_used": row.fallback_used,
            "retry_used": row.retry_used,
            "degraded_mode_used": row.degraded_mode_used,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def upsert_budget(policy_id: str | None, payload: dict, actor: str) -> CostBudgetPolicy:
    warning = int(payload.get("warning_threshold_percent", 80))
    if warning < 1 or warning > 100:
        raise governance_error("budget_invalid_threshold", "warning_threshold_percent must be between 1 and 100.", 400, {"warning_threshold_percent": warning})
    budget_policy_id = policy_id or f"budget_{uuid4().hex}"
    budget = db.session.get(CostBudgetPolicy, budget_policy_id)
    if budget is None:
'''
