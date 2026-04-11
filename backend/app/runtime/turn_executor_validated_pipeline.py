"""Validated turn pipeline (validation → deltas → apply → narrative commit) — DS-054.

DS-007 Task 3: Decision gates extracted to pipeline_decision_guards module.
DS-005 optional: early pipeline stages and narrative logging live in companion modules.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.content.module_models import ContentModule
from app.runtime.event_log import RuntimeEventLog
from app.runtime.narrative_commit import resolve_narrative_commit
from app.runtime.runtime_models import MockDecision, SessionState
from app.runtime.turn_execution_types import TurnExecutionResult
from app.runtime.turn_executor_decision_delta import _compute_guard_outcome
from app.runtime.turn_executor_validated_pipeline_apply import (
    validated_turn_validate_construct_and_apply,
)
from app.runtime.turn_executor_validated_pipeline_narrative_log import (
    log_narrative_outcomes_after_commit,
)


def run_validated_turn_pipeline(
    session: SessionState,
    current_turn: int,
    mock_decision: MockDecision,
    module: ContentModule,
    event_log: RuntimeEventLog,
    started_at: datetime,
    prior_scene_id: str | None,
) -> TurnExecutionResult:
    """Execute validation through completion for a successful source-gate path.

    Args:
        session: Current session state.
        current_turn: Turn number being executed.
        mock_decision: Decision proposal from AI.
        module: Content module context.
        event_log: Event logger for turn execution.
        started_at: Turn start timestamp.
        prior_scene_id: Scene ID before execution.

    Returns:
        TurnExecutionResult with complete execution data and narrative commit.
    """
    validation_outcome, accepted_deltas, rejected_deltas, updated_state = (
        validated_turn_validate_construct_and_apply(
            session, current_turn, mock_decision, module, event_log
        )
    )

    guard_outcome_value = _compute_guard_outcome(accepted_deltas, rejected_deltas, "success")
    narrative_commit = resolve_narrative_commit(
        turn_number=current_turn,
        prior_scene_id=prior_scene_id or session.current_scene_id,
        post_delta_canonical_state=updated_state,
        session_template=session,
        decision=mock_decision,
        module=module,
        guard_outcome=guard_outcome_value,
        accepted_deltas=accepted_deltas,
        rejected_deltas=rejected_deltas,
    )

    updated_scene_id = narrative_commit.committed_scene_id
    updated_ending_id = narrative_commit.committed_ending_id

    log_narrative_outcomes_after_commit(
        event_log,
        narrative_commit,
        session,
        mock_decision,
        updated_state,
        prior_scene_id,
        module,
    )

    completed_at = datetime.now(timezone.utc)
    duration_ms = (completed_at - started_at).total_seconds() * 1000

    event_log.log(
        "turn_completed",
        f"Turn {current_turn} completed: {len(accepted_deltas)} accepted, {len(rejected_deltas)} rejected",
        payload={
            "turn_number": current_turn,
            "accepted_delta_count": len(accepted_deltas),
            "rejected_delta_count": len(rejected_deltas),
            "guard_outcome": guard_outcome_value.value,
            "detected_triggers": mock_decision.detected_triggers,
            "duration_ms": duration_ms,
        },
    )

    return TurnExecutionResult(
        turn_number=current_turn,
        session_id=session.session_id,
        execution_status="success",
        decision=mock_decision,
        validation_outcome=validation_outcome,
        validation_errors=validation_outcome.errors,
        accepted_deltas=accepted_deltas,
        rejected_deltas=rejected_deltas,
        updated_canonical_state=updated_state,
        updated_scene_id=updated_scene_id,
        updated_ending_id=updated_ending_id,
        guard_outcome=guard_outcome_value,
        narrative_commit=narrative_commit,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        events=event_log.flush(),
    )
