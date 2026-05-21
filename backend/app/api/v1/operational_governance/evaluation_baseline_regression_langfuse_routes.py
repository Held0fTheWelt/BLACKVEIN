"""Evaluation baseline, regression, and Langfuse routes."""

from __future__ import annotations

from .common import *

@api_v1_bp.route("/admin/mvp4/evaluation/baseline/turns", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def add_evaluation_baseline_turn():
    """Promote an annotated turn into the canonical baseline set."""
    def _do():
        from ai_stack.quality_lab.evaluation_pipeline import EvaluationPipeline, TurnScore
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        body = _body()
        baseline_id = str(body.get("baseline_id") or "goc_evaluation_baseline").strip()
        session_id = str(body.get("session_id") or "").strip()
        turn_id = str(body.get("turn_id") or "").strip()
        if not session_id or not turn_id:
            raise governance_error("invalid_baseline_turn", "session_id and turn_id are required", 400, {})

        pipeline = EvaluationPipeline(get_runtime_governance_storage())
        recent_turns = pipeline.list_recent_turn_scores(session_id, limit=200)
        selected = next((turn for turn in recent_turns if turn.turn_id == turn_id), None)
        if selected is None:
            scores = body.get("scores") if isinstance(body.get("scores"), dict) else {}
            average_score = body.get("average_score")
            if average_score is None and scores:
                average_score = sum(float(value) for value in scores.values()) / len(scores)
            selected = TurnScore(
                turn_id=turn_id,
                session_id=session_id,
                scores={str(key): float(value) for key, value in scores.items()},
                average_score=float(average_score or 0.0),
                passed=bool(body.get("passed", True)),
                annotated_by=_actor_identifier(),
                feedback_tags=[str(tag) for tag in body.get("feedback_tags", []) if str(tag).strip()],
                notes=body.get("notes"),
            )

        baseline = pipeline.add_baseline_turn(
            baseline_id=baseline_id,
            turn_score=selected,
            admin_user=_actor_identifier(),
        )
        return {
            "baseline_id": baseline.baseline_id,
            "canonical_turn_count": len(baseline.canonical_turns),
            "metrics": {key: metric.to_dict() for key, metric in baseline.metrics_per_dimension.items()},
            "updated": True,
        }

    return _handle("evaluation_baseline_turn_add", _do)


@api_v1_bp.route("/admin/mvp4/evaluation/session/<session_id>/regression", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def get_evaluation_session_regression(session_id: str):
    """Compare recent live annotations against the canonical baseline."""
    def _do():
        from ai_stack.quality_lab.evaluation_pipeline import EvaluationPipeline
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        turn_count = int(request.args.get("turn_count", 10))
        baseline_id = str(request.args.get("baseline_id") or "goc_evaluation_baseline").strip()
        pipeline = EvaluationPipeline(get_runtime_governance_storage())
        return pipeline.check_baseline_regression(
            session_id=session_id,
            turn_count=turn_count,
            baseline_id=baseline_id,
        )

    return _handle("evaluation_session_regression_get", _do)


# Langfuse Configuration


@api_v1_bp.route("/admin/mvp4/game/session/<session_id>/langfuse-toggle", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def request_session_langfuse_toggle(session_id: str):
    """Request scoped Langfuse toggle (read-only status until persistence is implemented)."""
    body = _body()
    requested_enabled = bool(body.get("enabled", False))
    reason = str(body.get("reason") or "").strip()
    return fail(
        "langfuse_toggle_not_wired",
        "Session-level Langfuse toggle is not wired to persisted runtime state yet.",
        501,
        {
            "session_id": session_id,
            "requested_enabled": requested_enabled,
            "reason": reason,
            "mutated": False,
            "operator_action_required": (
                "Use observability governance configuration and runtime evidence endpoints "
                "until session-scoped persistence is implemented."
            ),
        },
    )

__all__ = (
    'add_evaluation_baseline_turn',
    'get_evaluation_session_regression',
    'request_session_langfuse_toggle',
)
