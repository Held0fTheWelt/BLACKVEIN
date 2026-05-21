"""Runtime token budget, session summary, and cost routes."""

from __future__ import annotations

from .common import *

# ============================================================================
# Runtime governance, evaluation, and operator surfaces
# ============================================================================

# Token Budget Management


@api_v1_bp.route("/admin/mvp4/game/session/<session_id>/token-budget", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def get_runtime_token_budget(session_id: str):
    """Get current token budget and usage for session."""
    def _do():
        from app.services.governance.observability_governance_service import TokenBudgetService, get_runtime_governance_storage

        service = TokenBudgetService(get_runtime_governance_storage())
        budget = service.get_budget(session_id)
        usage_percent = (budget.used_tokens / budget.total_budget * 100) if budget.total_budget > 0 else 0

        return {
            "session_id": session_id,
            "total_budget": budget.total_budget,
            "used_tokens": budget.used_tokens,
            "remaining_tokens": max(0, budget.total_budget - budget.used_tokens),
            "usage_percent": usage_percent,
            "warning_threshold": int(budget.warning_threshold * 100),
            "ceiling_threshold": int(budget.ceiling_threshold * 100),
            "degradation_strategy": budget.degradation_strategy,
            "degradation_level": "warning" if usage_percent >= budget.warning_threshold * 100 else (
                "critical" if usage_percent >= budget.ceiling_threshold * 100 else "none"
            ),
        }

    return _handle("token_budget_get", _do)


@api_v1_bp.route("/admin/mvp4/game/session/<session_id>/token-budget/override", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def override_runtime_token_budget(session_id: str):
    """Admin override: add tokens to session budget."""
    def _do():
        from app.services.governance.observability_governance_service import TokenBudgetService, get_runtime_governance_storage

        body = _body()
        tokens_to_add = int(body.get("tokens_to_add", 0))
        reason = body.get("reason", "")

        service = TokenBudgetService(get_runtime_governance_storage())
        service.override_budget(
            session_id=session_id,
            tokens_to_add=tokens_to_add,
            admin_user=_actor_identifier(),
            reason=reason,
        )

        budget = service.get_budget(session_id)
        return {
            "session_id": session_id,
            "new_total": budget.total_budget,
            "new_used": budget.used_tokens,
            "override_applied": True,
        }

    return _handle("token_budget_override", _do)


@api_v1_bp.route("/admin/mvp4/game/session/<session_id>/summary", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def get_runtime_session_summary(session_id: str):
    """Return live runtime, cost, budget, override, and evaluation truth for one session."""
    def _do():
        from ai_stack.quality_lab.evaluation_pipeline import EvaluationPipeline
        from app.services.game.game_service import get_story_state
        from app.services.governance.observability_governance_service import (
            CostDashboard,
            TokenBudgetService,
            get_runtime_governance_storage,
        )

        storage = get_runtime_governance_storage()
        state = get_story_state(session_id)
        latest_turn = state.get("last_committed_turn") if isinstance(state.get("last_committed_turn"), dict) else {}
        diagnostics_envelope = (
            latest_turn.get("diagnostics_envelope")
            if isinstance(latest_turn.get("diagnostics_envelope"), dict)
            else {}
        )
        overrides = _active_session_overrides(storage, session_id)

        budget_service = TokenBudgetService(storage)
        cost_dashboard = CostDashboard(storage)
        evaluation = EvaluationPipeline(storage)

        recent_turns = [turn.to_dict() for turn in evaluation.list_recent_turn_scores(session_id, limit=10)]
        return {
            "session_id": session_id,
            "state": {
                "module_id": state.get("module_id"),
                "turn_counter": state.get("turn_counter"),
                "current_scene_id": state.get("current_scene_id"),
                "story_window": state.get("story_window") if isinstance(state.get("story_window"), dict) else {},
                "runtime_projection": (
                    state.get("runtime_projection") if isinstance(state.get("runtime_projection"), dict) else {}
                ),
                "updated_at": state.get("updated_at"),
            },
            "narrator_streaming": (
                latest_turn.get("narrator_streaming") if isinstance(latest_turn.get("narrator_streaming"), dict) else None
            ),
            "diagnostics_envelope": diagnostics_envelope,
            "budget_status": budget_service.get_budget_status(session_id),
            "cost_summary": cost_dashboard.get_session_cost_summary(session_id).to_dict(),
            "evaluation": {
                "weights": evaluation.get_rubric_weights(session_id).to_dict(),
                "recent_turns": recent_turns,
                "quality_summary": evaluation.get_session_quality_summary(session_id, limit=10),
                "regression": evaluation.check_baseline_regression(session_id=session_id, turn_count=10),
            },
            "overrides": {
                "object_admission": overrides["object_admission"],
                "state_delta_boundary": overrides["state_delta_boundary"],
                "active_count": len(overrides["object_admission"]) + len(overrides["state_delta_boundary"]),
            },
        }

    return _handle("runtime_session_summary", _do)


@api_v1_bp.route("/admin/mvp4/costs/daily", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def get_runtime_daily_cost_report():
    """Return aggregated truthful cost usage for one UTC day."""
    def _do():
        from app.services.governance.observability_governance_service import CostDashboard, get_runtime_governance_storage

        date_value = (request.args.get("date") or datetime.now(timezone.utc).date().isoformat()).strip()
        dashboard = CostDashboard(get_runtime_governance_storage())
        return dashboard.get_daily_cost_report(date_value)

    return _handle("runtime_daily_cost_report", _do)


@api_v1_bp.route("/admin/mvp4/costs/weekly", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def get_runtime_weekly_cost_report():
    """Return aggregated truthful cost usage for the requested UTC week window."""
    def _do():
        from app.services.governance.observability_governance_service import CostDashboard, get_runtime_governance_storage

        week_start = (request.args.get("week_start") or datetime.now(timezone.utc).date().isoformat()).strip()
        dashboard = CostDashboard(get_runtime_governance_storage())
        return dashboard.get_weekly_cost_report(week_start)

    return _handle("runtime_weekly_cost_report", _do)

__all__ = (
    'get_runtime_token_budget',
    'override_runtime_token_budget',
    'get_runtime_session_summary',
    'get_runtime_daily_cost_report',
    'get_runtime_weekly_cost_report',
)
