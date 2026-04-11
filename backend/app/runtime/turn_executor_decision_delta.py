"""Delta construction/application for the validated turn path (DS-001).

Shared with ``turn_executor`` (re-export) and ``turn_executor_validated_pipeline``.
Validation entrypoint is ``app.runtime.validators.validate_decision`` — not ``turn_executor``.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.runtime.runtime_models import (
    DeltaType,
    DeltaValidationStatus,
    GuardOutcome,
    MockDecision,
    SessionState,
    StateDelta,
)
from app.runtime.validators import ValidationOutcome


class DeltaApplicationError(RuntimeError):
    """Exception raised when delta application fails."""

    pass


def get_current_value(state: dict[str, Any], target_path: str) -> Any:
    """Get the current value at a target path in the state dict (dot notation)."""
    parts = target_path.split(".")
    current = state
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _set_nested_value(state: dict[str, Any], path: str, value: Any) -> None:
    """Set a value at a nested path in the state dict (mutates state in place)."""
    if not path or not isinstance(path, str):
        raise DeltaApplicationError(f"Invalid path: {path}")

    parts = path.split(".")
    if not parts:
        raise DeltaApplicationError("Empty path")

    current = state
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            raise DeltaApplicationError(
                f"Cannot traverse non-dict at {part}: {type(current[part])}"
            )
        current = current[part]

    current[parts[-1]] = value


def infer_delta_type(target_path: str) -> DeltaType:
    """Infer the delta type from the target path."""
    if not target_path or not isinstance(target_path, str):
        return DeltaType.METADATA

    parts = target_path.split(".")
    if not parts:
        return DeltaType.METADATA

    entity_type = parts[0]
    if entity_type == "characters":
        return DeltaType.CHARACTER_STATE
    elif entity_type == "relationships":
        return DeltaType.RELATIONSHIP
    elif entity_type == "scene":
        return DeltaType.SCENE
    elif entity_type == "triggers":
        return DeltaType.TRIGGER
    else:
        return DeltaType.METADATA


def extract_entity_id(target_path: str) -> str | None:
    """Extract the entity ID from a target path (e.g. characters.<id>.…)."""
    if not target_path or not isinstance(target_path, str):
        return None

    parts = target_path.split(".")
    if len(parts) >= 2:
        return parts[1]
    return None


def construct_deltas(
    decision: MockDecision,
    session: SessionState,
    validation_outcome: ValidationOutcome,
    turn_number: int,
) -> tuple[list[StateDelta], list[StateDelta]]:
    """Construct accepted and rejected StateDelta objects from a mock decision."""
    accepted_deltas = []
    rejected_deltas = []

    for idx, proposed in enumerate(decision.proposed_deltas):
        delta_type = (
            proposed.delta_type
            if proposed.delta_type
            else infer_delta_type(proposed.target)
        )

        previous_value = get_current_value(session.canonical_state, proposed.target)

        delta = StateDelta(
            delta_type=delta_type,
            target_path=proposed.target,
            target_entity=extract_entity_id(proposed.target),
            previous_value=previous_value,
            next_value=proposed.next_value,
            source="ai_proposal",
            turn_number=turn_number,
        )

        if idx in validation_outcome.accepted_delta_indices:
            delta.validation_status = DeltaValidationStatus.ACCEPTED
            accepted_deltas.append(delta)
        else:
            delta.validation_status = DeltaValidationStatus.REJECTED
            rejected_deltas.append(delta)

    return accepted_deltas, rejected_deltas


def apply_deltas(
    canonical_state: dict[str, Any], deltas: list[StateDelta]
) -> dict[str, Any]:
    """Apply accepted deltas to the canonical state (returns a new dict)."""
    new_state = deepcopy(canonical_state)

    for delta in deltas:
        if delta.validation_status != DeltaValidationStatus.ACCEPTED:
            continue

        try:
            _set_nested_value(new_state, delta.target_path, delta.next_value)
        except DeltaApplicationError as e:
            raise DeltaApplicationError(
                f"Failed to apply delta at {delta.target_path}: {e}"
            ) from e

    return new_state


def _compute_guard_outcome(
    accepted: list,
    rejected: list,
    execution_status: str,
) -> GuardOutcome:
    """Compute the canonical guard outcome based on delta acceptance status."""
    if execution_status != "success":
        return GuardOutcome.STRUCTURALLY_INVALID
    n_accepted = len(accepted)
    n_rejected = len(rejected)
    if n_accepted == 0 and n_rejected == 0:
        return GuardOutcome.STRUCTURALLY_INVALID
    if n_rejected == 0:
        return GuardOutcome.ACCEPTED
    if n_accepted == 0:
        return GuardOutcome.REJECTED
    return GuardOutcome.PARTIALLY_ACCEPTED
