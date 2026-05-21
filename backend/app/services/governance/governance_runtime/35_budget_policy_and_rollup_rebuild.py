"""Governance runtime source segment: budget_policy_and_rollup_rebuild.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
        budget = CostBudgetPolicy(
            budget_policy_id=budget_policy_id,
            scope_kind=(payload.get("scope_kind") or "global").strip(),
            scope_ref=(payload.get("scope_ref") or "").strip() or None,
        )
        db.session.add(budget)
    budget.daily_limit = Decimal(str(payload["daily_limit"])) if payload.get("daily_limit") is not None else None
    budget.monthly_limit = Decimal(str(payload["monthly_limit"])) if payload.get("monthly_limit") is not None else None
    budget.warning_threshold_percent = warning
    budget.hard_stop_enabled = bool(payload.get("hard_stop_enabled", False))
    _audit("budget_updated", "costs", budget_policy_id, actor, "Budget policy upserted.", {})
    db.session.commit()
    return budget


def list_budgets() -> list[dict]:
    rows = CostBudgetPolicy.query.order_by(CostBudgetPolicy.scope_kind.asc(), CostBudgetPolicy.scope_ref.asc()).all()
    return [
        {
            "budget_policy_id": row.budget_policy_id,
            "scope_kind": row.scope_kind,
            "scope_ref": row.scope_ref,
            "daily_limit": str(row.daily_limit) if row.daily_limit is not None else None,
            "monthly_limit": str(row.monthly_limit) if row.monthly_limit is not None else None,
            "warning_threshold_percent": row.warning_threshold_percent,
            "hard_stop_enabled": row.hard_stop_enabled,
        }
        for row in rows
    ]


def rebuild_rollups(actor: str) -> list[dict]:
    """Rebuild daily rollups from usage events."""
    rows = AIUsageEvent.query.all()
    grouped: dict[tuple[date, str | None, str | None, str | None], list[AIUsageEvent]] = defaultdict(list)
    for row in rows:
        if row.created_at is None:
            continue
        grouped[(row.created_at.date(), row.provider_id, row.model_id, row.workflow_scope)].append(row)
    CostRollup.query.delete()
    out: list[dict] = []
    for key, events in grouped.items():
        rollup_date, provider_id, model_id, workflow_scope = key
        estimated_total = Decimal("0")
        provider_total: Decimal | None = Decimal("0")
        for event in events:
            if event.estimated_cost is not None:
                estimated_total += event.estimated_cost
            if event.provider_reported_cost is None:
                provider_total = None
            elif provider_total is not None:
                provider_total += event.provider_reported_cost
        rollup = CostRollup(
            rollup_id=f"roll_{uuid4().hex}",
            rollup_date=rollup_date,
            provider_id=provider_id,
            model_id=model_id,
            workflow_scope=workflow_scope,
            request_count=len(events),
            estimated_cost_total=estimated_total,
            provider_reported_cost_total=provider_total,
            retry_count=sum(1 for event in events if event.retry_used),
            fallback_count=sum(1 for event in events if event.fallback_used),
        )
        db.session.add(rollup)
        out.append(
            {
                "rollup_id": rollup.rollup_id,
                "rollup_date": rollup_date.isoformat(),
                "provider_id": provider_id,
                "model_id": model_id,
                "workflow_scope": workflow_scope,
'''
