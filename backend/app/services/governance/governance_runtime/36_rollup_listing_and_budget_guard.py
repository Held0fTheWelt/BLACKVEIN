"""Governance runtime source segment: rollup_listing_and_budget_guard.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
                "request_count": rollup.request_count,
                "estimated_cost_total": str(rollup.estimated_cost_total),
                "provider_reported_cost_total": str(rollup.provider_reported_cost_total) if rollup.provider_reported_cost_total is not None else None,
                "retry_count": rollup.retry_count,
                "fallback_count": rollup.fallback_count,
            }
        )
    _audit("cost_rollup_rebuilt", "costs", "cost_rollups", actor, "Cost rollups rebuilt.", {"count": len(out)})
    db.session.commit()
    return out


def list_rollups(limit: int = 100) -> list[dict]:
    rows = CostRollup.query.order_by(CostRollup.rollup_date.desc()).limit(limit).all()
    return [
        {
            "rollup_id": row.rollup_id,
            "rollup_date": row.rollup_date.isoformat(),
            "provider_id": row.provider_id,
            "model_id": row.model_id,
            "workflow_scope": row.workflow_scope,
            "request_count": row.request_count,
            "estimated_cost_total": str(row.estimated_cost_total),
            "provider_reported_cost_total": str(row.provider_reported_cost_total) if row.provider_reported_cost_total is not None else None,
            "retry_count": row.retry_count,
            "fallback_count": row.fallback_count,
        }
        for row in rows
    ]


def list_audit_events(limit: int = 200) -> list[dict]:
    rows = SettingAuditEvent.query.order_by(SettingAuditEvent.changed_at.desc()).limit(limit).all()
    return [row.to_dict() for row in rows]


def enforce_budget_guard(provider_id: str | None, workflow_scope: str | None) -> None:
    """Raise if hard-stop budget has been exceeded."""
    today = datetime.now(timezone.utc).date()
    day_rollups = CostRollup.query.filter(CostRollup.rollup_date == today).all()
    totals = Decimal("0")
    for roll in day_rollups:
        if provider_id and roll.provider_id not in {provider_id, None}:
            continue
        if workflow_scope and roll.workflow_scope not in {workflow_scope, None}:
            continue
        totals += roll.provider_reported_cost_total or roll.estimated_cost_total
    budgets = CostBudgetPolicy.query.filter_by(hard_stop_enabled=True).all()
    for budget in budgets:
        if budget.scope_kind == "provider" and budget.scope_ref and provider_id != budget.scope_ref:
            continue
        if budget.scope_kind == "workflow" and budget.scope_ref and workflow_scope != budget.scope_ref:
            continue
        if budget.daily_limit is not None and totals > budget.daily_limit:
            raise governance_error(
                "budget_limit_exceeded",
                "Hard-stop budget policy blocks this runtime action.",
                409,
                {"scope_kind": budget.scope_kind, "scope_ref": budget.scope_ref, "daily_limit": str(budget.daily_limit), "current_total": str(totals)},
            )


def record_operational_activity(actor_user, action: str, message: str, metadata: dict | None = None) -> None:
    """Mirror key governance events to shared activity log."""
    log_activity(
        actor=actor_user,
        category="governance",
        action=action,
        status="success",
        message=message,
        route="governance",
        method="SYSTEM",
'''
