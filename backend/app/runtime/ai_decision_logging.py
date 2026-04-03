"""W2.4.4 — AI Decision Logging with Role Diagnostics

Constructs and populates AIDecisionLog with role-separated diagnostics
(interpreter, director, responder) when role-structured parsing is available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from app.runtime.ai_decision import ParsedAIDecision
from app.runtime.w2_models import (
    AIDecisionLog,
    AIValidationOutcome,
    DirectorDiagnosticSummary,
    GuardOutcome,
    InterpreterDiagnosticSummary,
    StateDelta,
)

if TYPE_CHECKING:
    from app.runtime.role_structured_decision import ParsedRoleAwareDecision


def construct_ai_decision_log(
    session_id: str,
    turn_number: int,
    parsed_decision: ParsedAIDecision,
    raw_output: str,
    role_aware_decision: Optional[ParsedRoleAwareDecision],
    guard_outcome: GuardOutcome,
    accepted_deltas: Optional[list[StateDelta]] = None,
    rejected_deltas: Optional[list[StateDelta]] = None,
    guard_notes: Optional[str] = None,
    recovery_notes: Optional[str] = None,
    tool_loop_summary: Optional[dict] = None,
    tool_call_transcript: Optional[list[dict]] = None,
    tool_influence: Optional[dict] = None,
) -> AIDecisionLog:
    """Construct a fully-populated AIDecisionLog with role diagnostics if available.

    Type detection:
    - If role_aware_decision is present, extract and populate interpreter/director/responder fields
    - If role_aware_decision is None, leave role fields as None (legacy path)

    Args:
        session_id: Parent session identifier.
        turn_number: Turn number for this decision.
        parsed_decision: Canonical ParsedAIDecision (only runtime decision object).
        raw_output: Raw adapter output (explicit parameter).
        role_aware_decision: Optional ParsedRoleAwareDecision from role-structured parsing.
        guard_outcome: Canonical guard outcome for responder-derived proposals.
        accepted_deltas: Deltas that passed validation (optional).
        rejected_deltas: Deltas that failed validation (optional).
        guard_notes: Guard intervention notes (optional).
        recovery_notes: Recovery action notes (optional).

    Returns:
        AIDecisionLog with role fields populated if role_aware_decision is present.
    """
    interpreter_output = None
    director_output = None
    responder_output = None

    # Type-based detection: if role_aware_decision is present, populate role fields
    if role_aware_decision is not None:
        interpreter_output = InterpreterDiagnosticSummary(
            scene_reading=role_aware_decision.interpreter.scene_reading,
            detected_tensions=role_aware_decision.interpreter.detected_tensions,
        )
        director_output = DirectorDiagnosticSummary(
            conflict_steering=role_aware_decision.director.conflict_steering,
            recommended_direction=role_aware_decision.director.recommended_direction,
        )
        responder_output = role_aware_decision.responder  # Full typed ResponderSection

    # Derive validation_outcome from guard_outcome (not hardcoded)
    # Use explicit mapping to catch unexpected values
    validation_outcome_mapping = {
        GuardOutcome.ACCEPTED: AIValidationOutcome.ACCEPTED,
        GuardOutcome.PARTIALLY_ACCEPTED: AIValidationOutcome.PARTIAL,
        GuardOutcome.REJECTED: AIValidationOutcome.REJECTED,
        GuardOutcome.STRUCTURALLY_INVALID: AIValidationOutcome.ERROR,
    }
    try:
        validation_outcome = validation_outcome_mapping[guard_outcome]
    except KeyError:
        raise ValueError(f"Unknown guard_outcome value: {guard_outcome}") from None

    return AIDecisionLog(
        session_id=session_id,
        turn_number=turn_number,
        raw_output=raw_output,  # Explicit parameter
        parsed_output=parsed_decision.model_dump(),  # Full canonical decision as dict
        interpreter_output=interpreter_output,  # Diagnostic only
        director_output=director_output,  # Diagnostic only
        responder_output=responder_output,  # Diagnostic only
        validation_outcome=validation_outcome,  # Derived from guard_outcome
        guard_outcome=guard_outcome,  # Canonical validation result
        accepted_deltas=accepted_deltas or [],
        rejected_deltas=rejected_deltas or [],
        guard_notes=guard_notes,
        recovery_notes=recovery_notes,
        tool_loop_summary=tool_loop_summary,
        tool_call_transcript=tool_call_transcript,
        tool_influence=tool_influence,
    )
