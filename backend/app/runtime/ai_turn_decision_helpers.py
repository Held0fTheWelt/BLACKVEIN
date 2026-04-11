from __future__ import annotations

from typing import Any

from app.runtime.ai_adapter import AdapterResponse
from app.runtime.runtime_models import (
    AIDecisionLog,
    AIValidationOutcome,
    DeltaValidationStatus,
    GuardOutcome,
    SessionState,
    StateDelta,
)
from app.runtime.turn_executor import ProposedStateDelta, TurnExecutionResult


def convert_proposed_delta_to_state_delta(
    proposed_delta: ProposedStateDelta,
    validation_status: DeltaValidationStatus,
    turn_number: int,
) -> StateDelta:
    target_entity = None
    path_parts = proposed_delta.target.split(".")
    if len(path_parts) >= 2:
        target_entity = path_parts[1]

    return StateDelta(
        delta_type=proposed_delta.delta_type,
        target_path=proposed_delta.target,
        target_entity=target_entity,
        previous_value=proposed_delta.previous_value,
        next_value=proposed_delta.next_value,
        source="ai_proposal",
        validation_status=validation_status,
        turn_number=turn_number,
    )


def create_decision_log(
    session: SessionState,
    current_turn: int,
    parsed_decision: Any,
    adapter_response: AdapterResponse,
    turn_result: TurnExecutionResult,
) -> AIDecisionLog:
    if turn_result.execution_status == "success":
        outcome_map = {
            GuardOutcome.ACCEPTED: AIValidationOutcome.ACCEPTED,
            GuardOutcome.PARTIALLY_ACCEPTED: AIValidationOutcome.PARTIAL,
            GuardOutcome.REJECTED: AIValidationOutcome.REJECTED,
            GuardOutcome.STRUCTURALLY_INVALID: AIValidationOutcome.ERROR,
        }
        validation_outcome = outcome_map.get(turn_result.guard_outcome, AIValidationOutcome.ERROR)
    else:
        validation_outcome = AIValidationOutcome.ERROR

    guard_notes = None
    if turn_result.validation_errors:
        errors = turn_result.validation_errors
        count = len(errors)
        outcome_label = turn_result.guard_outcome.value
        sample = "; ".join(errors[:3])
        guard_notes = f"{count} error{'s' if count != 1 else ''}; {outcome_label}: {sample}"

    return AIDecisionLog(
        session_id=session.session_id,
        turn_number=current_turn,
        raw_output=adapter_response.raw_output,
        parsed_output={
            "scene_interpretation": parsed_decision.scene_interpretation,
            "detected_triggers": parsed_decision.detected_triggers,
            "rationale": parsed_decision.rationale,
            "proposed_scene_id": parsed_decision.proposed_scene_id,
            "proposed_deltas_count": len(parsed_decision.proposed_deltas),
        },
        validation_outcome=validation_outcome,
        accepted_deltas=turn_result.accepted_deltas,
        rejected_deltas=turn_result.rejected_deltas,
        guard_notes=guard_notes,
        guard_outcome=turn_result.guard_outcome,
    )
