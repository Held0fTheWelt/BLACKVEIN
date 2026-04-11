"""Restore- und Safe-Turn-Pfade nach erschöpften Retries bei Generierungsfehler (Feinsplit)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.content.module_models import ContentModule
from app.runtime.ai_adapter import AdapterResponse
from app.runtime.ai_decision import ParsedAIDecision
from app.runtime.ai_decision_logging import construct_ai_decision_log
from app.runtime.ai_failure_recovery import AIFailureClass, RestorePolicy
from app.runtime.ai_turn_orchestration_logging import attachments_from_orchestration_bundle
from app.runtime.ai_turn_shared_types import _AiTurnOrchestrationLogBundle
from app.runtime.runtime_models import (
    ExecutionFailureReason,
    GuardOutcome,
    SessionState,
)
from app.runtime.turn_executor import MockDecision, TurnExecutionResult, execute_turn


def try_restore_turn_after_generation_retry_exhausted(
    *,
    session: SessionState,
    current_turn: int,
    response: AdapterResponse,
    started_at: datetime,
    pre_execution_snapshot: Any,
    log_bundle: _AiTurnOrchestrationLogBundle,
) -> TurnExecutionResult | None:
    """Restore anwenden; bei Erfolg Turn-Ergebnis, bei ValueError oder Fehlschlag None."""
    from app.runtime.ai_turn_recovery_paths import _activate_degraded_marker, store_decision_log
    from app.runtime.runtime_models import DegradedMarker

    try:
        restored_state = RestorePolicy.apply_restore(session.canonical_state, pre_execution_snapshot)
        session.canonical_state = restored_state
        _activate_degraded_marker(session, DegradedMarker.RESTORE_USED)

        failure_class = AIFailureClass.RETRY_EXHAUSTED
        restore_metadata = RestorePolicy.get_restore_metadata(
            failure_class, pre_execution_snapshot.turn_number, current_turn
        )
        completed_at = datetime.now(timezone.utc)
        duration_ms = (completed_at - started_at).total_seconds() * 1000
        turn_result = TurnExecutionResult(
            turn_number=current_turn,
            session_id=session.session_id,
            execution_status="success",
            decision=MockDecision(),
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[],
            rejected_deltas=[],
            updated_canonical_state=restored_state,
            updated_scene_id=session.current_scene_id,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            events=[],
        )
        turn_result.failure_reason = ExecutionFailureReason.GENERATION_ERROR

        decision_log = construct_ai_decision_log(
            session_id=session.session_id,
            turn_number=current_turn,
            parsed_decision=ParsedAIDecision(
                scene_interpretation="[restore: last valid state recovered]",
                detected_triggers=[],
                proposed_deltas=[],
                proposed_scene_id=None,
                rationale="[restore: retry exhaustion triggered state recovery]",
                raw_output="",
                parsed_source="restore_executor",
            ),
            raw_output=response.raw_output or "",
            role_aware_decision=None,
            guard_outcome=GuardOutcome.ACCEPTED,
            accepted_deltas=[],
            rejected_deltas=[],
            guard_notes="restore_mode_active: last_valid_state_restore",
            **attachments_from_orchestration_bundle(log_bundle),
        )
        decision_log.recovery_notes = (
            f"restore_mode_active: last_valid_state_restore; "
            f"failure_class={restore_metadata['failure_class']}; "
            f"snapshot_turn={restore_metadata['snapshot_turn']}; "
            f"turns_discarded={restore_metadata['turns_discarded']}"
        )
        store_decision_log(session, decision_log)
        return turn_result
    except ValueError:
        return None


async def run_safe_turn_after_generation_retry_exhausted(
    *,
    session: SessionState,
    current_turn: int,
    module: ContentModule,
    response: AdapterResponse,
    log_bundle: _AiTurnOrchestrationLogBundle,
) -> TurnExecutionResult:
    from app.runtime.ai_turn_recovery_paths import _activate_degraded_marker, store_decision_log
    from app.runtime.runtime_models import DegradedMarker

    safe_turn_decision = MockDecision(detected_triggers=[], proposed_deltas=[])
    _activate_degraded_marker(session, DegradedMarker.SAFE_TURN_USED)
    turn_result = await execute_turn(
        session,
        current_turn,
        safe_turn_decision,
        module,
        enforce_responder_only=False,
    )
    turn_result.failure_reason = ExecutionFailureReason.GENERATION_ERROR
    decision_log = construct_ai_decision_log(
        session_id=session.session_id,
        turn_number=current_turn,
        parsed_decision=ParsedAIDecision(
            scene_interpretation="[safe-turn: retry exhaustion recovery]",
            detected_triggers=[],
            proposed_deltas=[],
            proposed_scene_id=None,
            rationale="[safe-turn: no-op due to adapter failure after retries]",
            raw_output="",
            parsed_source="safe_turn_executor",
        ),
        raw_output=response.raw_output or "",
        role_aware_decision=None,
        guard_outcome=turn_result.guard_outcome,
        accepted_deltas=turn_result.accepted_deltas,
        rejected_deltas=turn_result.rejected_deltas,
        guard_notes="safe_turn_mode_active: retry_exhausted_recovery",
        **attachments_from_orchestration_bundle(log_bundle),
    )
    store_decision_log(session, decision_log)
    return turn_result
