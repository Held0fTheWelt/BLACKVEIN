"""Helpers for persisted AI deltas and structured decision logs.

Links proposals, adapter output, and guard results to stored models.
"""

from __future__ import annotations

from typing import Any

from app.runtime.ai_adapter import AdapterResponse
from app.runtime.runtime_models import (
    AIDecisionLog,
    AIValidationOutcome,
    DeltaValidationStatus,
    GuardOutcome,
    ProposedStateDelta,
    SessionState,
    StateDelta,
)
from app.runtime.turn.turn_execution_types import TurnExecutionResult


def convert_proposed_delta_to_state_delta(
    proposed_delta: ProposedStateDelta,
    validation_status: DeltaValidationStatus,
    turn_number: int,
) -> StateDelta:
    """Map a proposed delta and its validation status to a ``StateDelta``.

    When ``target`` contains at least two dotted segments, the second
    segment becomes ``target_entity``; otherwise it stays ``None``.

    Args:
        proposed_delta: Single AI-proposed change (path, values, type).
        validation_status: Outcome of validation for this proposal.
        turn_number: Turn index attached to the persisted delta.

    Returns:
        StateDelta:
            Persistence row for this proposal: ``delta_type``,
            ``target_path``, values, ``source="ai_proposal"``,
            ``validation_status``, ``turn_number``, and
            ``target_entity`` when the dotted path has a segment.
    """
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
    """Build an ``AIDecisionLog`` row for the current turn.

    Joins session data, adapter I/O, parsed fields, guard verdict,
    validation outcome, delta acceptance, and optional guard notes for
    persistence and operator review.

    Args:
        session: Live session state (ids and context for the turn).
        current_turn: Turn counter written into the log row.
        parsed_decision: Structured model output (scene, triggers,
            rationale, proposed scene and deltas).
        adapter_response: Provider payload plus raw model text wrapper.
        turn_result: Guard verdict, execution status, and validation
            errors plus accepted or rejected delta lists.

    Returns:
        AIDecisionLog:
            One structured audit row for the turn: session and turn
            ids, raw adapter text, parsed model slice, validation and
            guard fields, delta lists, and optional ``guard_notes``.
    """
    # Successful adapter runs map ``guard_outcome`` through ``outcome_map`` so persistence
    # matches what the guard already decided. Any non-success status forces ``ERROR`` so
    # operators see failed turns in telemetry without inferring from raw model text alone.
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
    # When the guard reports structured validation errors, fold count, verdict label, and a
    # short sample into ``guard_notes`` for dashboards. The full list stays on ``turn_result``
    # so ``parsed_output`` stays a compact projection of the model decision only.
    if turn_result.validation_errors:
        errors = turn_result.validation_errors
        count = len(errors)
        outcome_label = turn_result.guard_outcome.value
        sample = "; ".join(errors[:3])
        guard_notes = f"{count} error{'s' if count != 1 else ''}; {outcome_label}: {sample}"

    # Persist one row per turn: raw adapter text, parsed scene fields, validation enum, delta
    # lists, optional ``guard_notes``, and the guard verdict for cross-checks with runtime.
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
