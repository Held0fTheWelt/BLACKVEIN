"""Override audit and live evaluation routes."""

from __future__ import annotations

from .common import *

# Override Audit Configuration


@api_v1_bp.route("/admin/mvp4/overrides/audit-config", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def get_override_audit_config():
    """Get audit granularity configuration for all override types."""
    def _do():
        from app.auth.admin_security import OverrideAuditConfigManager
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        manager = OverrideAuditConfigManager(get_runtime_governance_storage())
        configs = manager.get_all_configs()
        return {
            "override_types": {
                ot: config.to_dict() for ot, config in configs.items()
            },
            "description": "Control which override events are logged per override type",
        }

    return _handle("override_audit_config_get", _do)


@api_v1_bp.route("/admin/mvp4/overrides/audit-config/<override_type>", methods=["PATCH"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def update_override_audit_config(override_type: str):
    """Update audit granularity configuration for override type."""
    def _do():
        from app.auth.admin_security import OverrideAuditConfig, OverrideAuditConfigManager
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        body = _body()
        config = OverrideAuditConfig(
            override_type=override_type,
            log_created=body.get("log_created", True),
            log_apply_attempt=body.get("log_apply_attempt", True),
            log_applied=body.get("log_applied", True),
            log_apply_failed=body.get("log_apply_failed", True),
            log_revoked=body.get("log_revoked", True),
            log_revoke_failed=body.get("log_revoke_failed", True),
            log_accessed=body.get("log_accessed", True),
        )

        manager = OverrideAuditConfigManager(get_runtime_governance_storage())
        manager.set_config(config)

        return {
            "override_type": override_type,
            "config": config.to_dict(),
            "updated": True,
        }

    return _handle("override_audit_config_update", _do)


# Evaluation Configuration


@api_v1_bp.route("/admin/mvp4/evaluation/rubric", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def get_evaluation_rubric():
    """Get quality evaluation rubric."""
    def _do():
        from ai_stack.quality_lab.evaluation_pipeline import EvaluationPipeline
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        pipeline = EvaluationPipeline(get_runtime_governance_storage())
        rubric = pipeline.get_rubric("goc_quality_v1")
        return rubric.to_dict()

    return _handle("evaluation_rubric_get", _do)


@api_v1_bp.route("/admin/mvp4/evaluation/baseline", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def get_evaluation_baseline():
    """Get offline baseline test set."""
    def _do():
        from ai_stack.quality_lab.evaluation_pipeline import EvaluationPipeline
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        pipeline = EvaluationPipeline(get_runtime_governance_storage())
        baseline = pipeline.get_baseline("goc_evaluation_baseline")
        return {
            "baseline_id": baseline.baseline_id,
            "version": baseline.version,
            "canonical_turn_count": len(baseline.canonical_turns),
            "metrics": {
                dim: metric.to_dict() for dim, metric in baseline.metrics_per_dimension.items()
            },
            "created_at": baseline.created_at,
        }

    return _handle("evaluation_baseline_get", _do)


@api_v1_bp.route("/admin/mvp4/evaluation/weights/<session_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def get_evaluation_rubric_weights(session_id: str):
    """Get current rubric weights (auto-tuning state) for session."""
    def _do():
        from ai_stack.quality_lab.evaluation_pipeline import EvaluationPipeline
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        pipeline = EvaluationPipeline(get_runtime_governance_storage())
        weights = pipeline.get_rubric_weights(session_id)
        return {
            "session_id": session_id,
            "weights": weights.to_dict(),
        }

    return _handle("evaluation_weights_get", _do)


@api_v1_bp.route("/admin/mvp4/evaluation/weights/<session_id>/manual-tune", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def manual_tune_evaluation_weights(session_id: str):
    """Manually trigger rubric weight tuning from recent turns."""
    def _do():
        from ai_stack.quality_lab.evaluation_pipeline import EvaluationPipeline
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        body = _body()
        turn_count = int(body.get("turn_count", 10))

        pipeline = EvaluationPipeline(get_runtime_governance_storage())
        weights = pipeline.manual_tune_weights(
            session_id=session_id,
            turn_count=turn_count,
            admin_user=_actor_identifier(),
        )

        return {
            "session_id": session_id,
            "weights": weights.to_dict(),
            "tuned_at": weights.last_updated,
        }

    return _handle("evaluation_manual_tune", _do)


@api_v1_bp.route("/admin/mvp4/evaluation/session/<session_id>/recent-turns", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def get_recent_evaluation_turn_scores(session_id: str):
    """List recent human-annotated evaluation turns for a live session."""
    def _do():
        from ai_stack.quality_lab.evaluation_pipeline import EvaluationPipeline
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        limit = int(request.args.get("limit", 10))
        pipeline = EvaluationPipeline(get_runtime_governance_storage())
        turns = pipeline.list_recent_turn_scores(session_id, limit=limit)
        return {
            "session_id": session_id,
            "recent_turns": [turn.to_dict() for turn in turns],
            "quality_summary": pipeline.get_session_quality_summary(session_id, limit=limit),
        }

    return _handle("evaluation_recent_turns_get", _do)


@api_v1_bp.route("/admin/mvp4/evaluation/session/<session_id>/turn-score", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
@require_feature(FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE)
def record_evaluation_turn_score(session_id: str):
    """Record or update a human annotation for one turn."""
    def _do():
        from ai_stack.quality_lab.evaluation_pipeline import EvaluationPipeline, TurnScore
        from app.services.governance.observability_governance_service import get_runtime_governance_storage

        body = _body()
        scores = body.get("scores") if isinstance(body.get("scores"), dict) else {}
        average_score = body.get("average_score")
        if average_score is None and scores:
            average_score = sum(float(value) for value in scores.values()) / len(scores)
        turn_score = TurnScore(
            turn_id=str(body.get("turn_id") or "").strip(),
            session_id=session_id,
            scores={str(key): float(value) for key, value in scores.items()},
            average_score=float(average_score or 0.0),
            passed=bool(body.get("passed", True)),
            annotated_by=_actor_identifier(),
            feedback_tags=[str(tag) for tag in body.get("feedback_tags", []) if str(tag).strip()],
            notes=body.get("notes"),
        )
        if not turn_score.turn_id:
            raise governance_error("invalid_turn_score", "turn_id is required", 400, {})

        pipeline = EvaluationPipeline(get_runtime_governance_storage())
        pipeline.record_turn_score(turn_score, session_id)
        return {
            "session_id": session_id,
            "turn_score": turn_score.to_dict(),
            "recorded": True,
        }

    return _handle("evaluation_turn_score_record", _do)

__all__ = (
    'get_override_audit_config',
    'update_override_audit_config',
    'get_evaluation_rubric',
    'get_evaluation_baseline',
    'get_evaluation_rubric_weights',
    'manual_tune_evaluation_weights',
    'get_recent_evaluation_turn_scores',
    'record_evaluation_turn_score',
)
