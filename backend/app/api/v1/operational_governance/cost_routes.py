"""Cost usage, rollup, and budget routes."""

from __future__ import annotations

from .common import *

@api_v1_bp.route("/admin/costs/usage-events", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_usage_events():
    limit = min(int(request.args.get("limit", "200")), 1000)
    return _handle("costs_usage_events", lambda: {"items": list_usage_events(limit=limit)})


@api_v1_bp.route("/admin/costs/usage-events", methods=["POST"])
@limiter.limit("120 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_usage_events_ingest():
    def _do():
        body = _body()
        enforce_budget_guard(body.get("provider_id"), body.get("workflow_scope"))
        return ingest_usage_event(body, _actor_identifier())

    return _handle("costs_usage_events_ingest", _do)


@api_v1_bp.route("/admin/costs/rollups", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_rollups():
    limit = min(int(request.args.get("limit", "200")), 1000)
    return _handle("costs_rollups", lambda: {"items": list_rollups(limit=limit)})


@api_v1_bp.route("/admin/costs/rollups/rebuild", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_rollups_rebuild():
    return _handle("costs_rollups_rebuild", lambda: {"items": rebuild_rollups(_actor_identifier())})


@api_v1_bp.route("/admin/costs/budgets", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_budgets():
    return _handle("costs_budgets", lambda: {"items": list_budgets()})


@api_v1_bp.route("/admin/costs/budgets", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_budgets_create():
    return _handle(
        "costs_budget_create",
        lambda: {"budget_policy_id": upsert_budget(None, _body(), _actor_identifier()).budget_policy_id, "created": True},
    )


@api_v1_bp.route("/admin/costs/budgets/<budget_policy_id>", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def admin_costs_budgets_patch(budget_policy_id: str):
    return _handle(
        "costs_budget_patch",
        lambda: {"budget_policy_id": upsert_budget(budget_policy_id, _body(), _actor_identifier()).budget_policy_id, "updated": True},
    )

__all__ = (
    'admin_costs_usage_events',
    'admin_costs_usage_events_ingest',
    'admin_costs_rollups',
    'admin_costs_rollups_rebuild',
    'admin_costs_budgets',
    'admin_costs_budgets_create',
    'admin_costs_budgets_patch',
)
