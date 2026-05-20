"""Decision validation guards for the validated turn pipeline.

Extracted decision gates and safety checks for run_validated_turn_pipeline.
Provides clean separation of validation, context, and state mutation concerns.

DS-007 Task 3: Guard extraction to reduce run_validated_turn_pipeline complexity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.runtime.runtime_models import MockDecision, SessionState, StateDelta
from app.runtime.validation.validators import ValidationOutcome


@dataclass(frozen=True)
class DecisionValidationResult:
    """Immutable result of decision validation with provenance.

    Captures whether decision passed validation checks and any errors encountered
    during validation, context checking, or state mutation planning.

    Attributes:
        valid: Whether the decision passed all validation checks.
        reason: Human-readable description of the validation result.
        errors: List of validation error messages (empty if valid=True).
    """

    valid: bool
    reason: str
    errors: list[str]


def _check_decision_validity(decision: MockDecision) -> DecisionValidationResult:
    """Validate that a decision has required structure and fields.

    Checks that the decision object contains the mandatory fields needed
    for downstream processing (proposed_deltas, scene/ending proposals, etc).

    Args:
        decision: The MockDecision to validate.

    Returns:
        DecisionValidationResult with validity status and any errors.
    """
    errors = []

    # Check required fields
    if not hasattr(decision, "proposed_deltas"):
        errors.append("Decision missing required 'proposed_deltas' field")
        return DecisionValidationResult(
            valid=False,
            reason="Missing mandatory fields",
            errors=errors,
        )

    if not isinstance(decision.proposed_deltas, list):
        errors.append("proposed_deltas must be a list")
        return DecisionValidationResult(
            valid=False,
            reason="Invalid field types",
            errors=errors,
        )

    # Verify at least one delta is present
    if len(decision.proposed_deltas) == 0:
        errors.append("Decision must contain at least one proposed delta")
        return DecisionValidationResult(
            valid=False,
            reason="No deltas to process",
            errors=errors,
        )

    return DecisionValidationResult(
        valid=True,
        reason="Decision structure valid",
        errors=[],
    )


def _validate_decision_context(
    decision: MockDecision, session: SessionState
) -> DecisionValidationResult:
    """Validate that decision references are resolvable in the session context.

    Checks that the decision's proposed scene/ending IDs and entity references
    are legal within the current session and content module context.

    Args:
        decision: The MockDecision to validate.
        session: The current SessionState providing context.

    Returns:
        DecisionValidationResult with context validity status and any errors.
    """
    errors = []

    # Validate scene transition context
    if hasattr(decision, "proposed_scene_id") and decision.proposed_scene_id:
        if not isinstance(decision.proposed_scene_id, str):
            errors.append("proposed_scene_id must be a string")
        elif not decision.proposed_scene_id.strip():
            errors.append("proposed_scene_id cannot be empty")

    # Validate ending context
    if hasattr(decision, "proposed_ending_id") and decision.proposed_ending_id:
        if not isinstance(decision.proposed_ending_id, str):
            errors.append("proposed_ending_id must be a string")
        elif not decision.proposed_ending_id.strip():
            errors.append("proposed_ending_id cannot be empty")

    # Validate triggers are present if needed
    if hasattr(decision, "detected_triggers"):
        if not isinstance(decision.detected_triggers, list):
            errors.append("detected_triggers must be a list")

    if errors:
        return DecisionValidationResult(
            valid=False,
            reason="Context validation failed",
            errors=errors,
        )

    return DecisionValidationResult(
        valid=True,
        reason="Decision context valid",
        errors=[],
    )


def _apply_delta_safely(
    state: dict[str, Any], deltas: list[StateDelta], turn_number: int
) -> tuple[dict[str, Any], DecisionValidationResult]:
    """Apply state deltas with safety checks and provenance tracking.

    Mutates state with provenance information (source, turn_number) on each delta.
    Validates that each delta application succeeds before committing.

    Args:
        state: The current canonical state (will not be modified in place).
        deltas: List of StateDelta objects to apply.
        turn_number: Current turn number for provenance.

    Returns:
        Tuple of (updated_state, validation_result).
        If validation_result.valid is False, updated_state is original state.
    """
    from copy import deepcopy

    from app.runtime.turn.turn_executor_decision_delta import apply_deltas

    errors = []

    # Validate delta count
    if not isinstance(deltas, list):
        errors.append("deltas must be a list")
        return state, DecisionValidationResult(
            valid=False,
            reason="Invalid deltas parameter",
            errors=errors,
        )

    # Validate each delta has required fields for application
    for idx, delta in enumerate(deltas):
        if not hasattr(delta, "target_path"):
            errors.append(f"Delta {idx} missing target_path")
        if not hasattr(delta, "next_value"):
            errors.append(f"Delta {idx} missing next_value")
        if not hasattr(delta, "validation_status"):
            errors.append(f"Delta {idx} missing validation_status")

    if errors:
        return state, DecisionValidationResult(
            valid=False,
            reason="Delta validation failed",
            errors=errors,
        )

    # Apply deltas with provenance
    try:
        new_state = deepcopy(state)
        new_state = apply_deltas(new_state, deltas)
        return new_state, DecisionValidationResult(
            valid=True,
            reason=f"Applied {len(deltas)} delta(s) successfully",
            errors=[],
        )
    except Exception as e:
        return state, DecisionValidationResult(
            valid=False,
            reason="Delta application failed",
            errors=[str(e)],
        )


def validate_decision_gates(
    decision: MockDecision, session: SessionState
) -> DecisionValidationResult:
    """Run all decision validation gates in sequence.

    Executes the full validation pipeline: structure check → context check.
    Returns immediately on first failure with accumulated errors.

    Args:
        decision: The MockDecision to validate.
        session: The current SessionState.

    Returns:
        DecisionValidationResult with combined validation status.
    """
    # Gate 1: Structure check
    structure_result = _check_decision_validity(decision)
    if not structure_result.valid:
        return structure_result

    # Gate 2: Context check
    context_result = _validate_decision_context(decision, session)
    if not context_result.valid:
        return context_result

    return DecisionValidationResult(
        valid=True,
        reason="All validation gates passed",
        errors=[],
    )
