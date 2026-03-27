"""Decision validation for the story runtime.

Provides validation infrastructure for mock decisions and AI proposals
before they are applied to the canonical session state.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    """Status of a validation check."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


class ValidationOutcome(BaseModel):
    """Outcome of validating a decision.

    Captures whether the decision passed validation, any errors or warnings,
    and which proposed changes are acceptable.

    Attributes:
        is_valid: Whether the decision passed all mandatory validation checks.
        status: Overall validation status (pass, fail, warning).
        errors: List of validation error messages.
        warnings: List of validation warning messages.
        accepted_delta_indices: Indices of proposed deltas that passed validation.
        rejected_delta_indices: Indices of proposed deltas that failed validation.
        details: Additional validation details (dict).
    """

    is_valid: bool
    status: ValidationStatus
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    accepted_delta_indices: list[int] = Field(default_factory=list)
    rejected_delta_indices: list[int] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


def validate_decision(decision: Any, session: Any, module: Any) -> ValidationOutcome:
    """Validate a mock decision against the current session and module.

    Checks that the decision contains valid references, valid state mutations,
    and complies with basic module constraints.

    Args:
        decision: The MockDecision to validate.
        session: The current SessionState.
        module: The ContentModule being executed.

    Returns:
        ValidationOutcome with validation results.
    """
    errors = []
    warnings = []
    accepted_indices = []
    rejected_indices = []
    details = {}

    # Check that decision has required fields
    if not hasattr(decision, "proposed_deltas"):
        errors.append("Decision missing required 'proposed_deltas' field")
        return ValidationOutcome(
            is_valid=False,
            status=ValidationStatus.FAIL,
            errors=errors,
            warnings=warnings,
            accepted_delta_indices=accepted_indices,
            rejected_delta_indices=rejected_indices,
            details=details,
        )

    # Validate each proposed delta
    for idx, delta in enumerate(decision.proposed_deltas):
        delta_errors = _validate_delta(delta, session, module)
        if delta_errors:
            rejected_indices.append(idx)
            errors.extend(delta_errors)
        else:
            accepted_indices.append(idx)

    # Check scene transition if present
    if hasattr(decision, "proposed_scene_id") and decision.proposed_scene_id:
        scene_errors = _validate_scene_transition(
            decision.proposed_scene_id, session, module
        )
        if scene_errors:
            errors.extend(scene_errors)

    # Determine overall validation status
    is_valid = len(errors) == 0
    status = ValidationStatus.PASS if is_valid else ValidationStatus.FAIL
    if warnings and is_valid:
        status = ValidationStatus.WARNING

    details["delta_count"] = len(decision.proposed_deltas)
    details["accepted_count"] = len(accepted_indices)
    details["rejected_count"] = len(rejected_indices)

    return ValidationOutcome(
        is_valid=is_valid,
        status=status,
        errors=errors,
        warnings=warnings,
        accepted_delta_indices=accepted_indices,
        rejected_delta_indices=rejected_indices,
        details=details,
    )


def _validate_delta(delta: Any, session: Any, module: Any) -> list[str]:
    """Validate a single proposed state delta.

    Args:
        delta: ProposedStateDelta to validate.
        session: The current SessionState.
        module: The ContentModule.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    if not hasattr(delta, "target"):
        errors.append("Delta missing 'target' field")
        return errors

    target = delta.target
    if not isinstance(target, str):
        errors.append(f"Delta target must be string, got {type(target).__name__}")
        return errors

    # Parse target path (e.g., "characters.veronique.emotional_state")
    parts = target.split(".")
    if not parts or len(parts) < 2:
        errors.append(f"Invalid target path format: {target}")
        return errors

    # Check if entity exists in module
    entity_type = parts[0]
    if entity_type == "characters":
        entity_id = parts[1] if len(parts) > 1 else None
        if entity_id and not _entity_exists(entity_id, module.characters):
            errors.append(f"Unknown character: {entity_id}")
    elif entity_type == "relationships":
        entity_id = parts[1] if len(parts) > 1 else None
        if entity_id and not _entity_exists(entity_id, module.relationship_axes):
            errors.append(f"Unknown relationship axis: {entity_id}")
    elif entity_type not in ["metadata", "scene"]:
        errors.append(f"Unknown entity type in target: {entity_type}")

    # Validate next_value if present
    if hasattr(delta, "next_value") and delta.next_value is not None:
        if isinstance(delta.next_value, (int, float)):
            if not (0 <= delta.next_value <= 100):
                errors.append(
                    f"Numeric delta values must be 0-100, got {delta.next_value}"
                )

    return errors


def _validate_scene_transition(
    scene_id: str, session: Any, module: Any
) -> list[str]:
    """Validate a scene transition is legal from the current canonical scene.

    Checks that:
    1. Target scene exists in module
    2. Target scene is reachable from current scene via defined transitions
    3. Current scene is valid in module

    Args:
        scene_id: Target scene ID.
        session: Current SessionState.
        module: ContentModule.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    # Check target scene exists
    if not _entity_exists(scene_id, module.scene_phases):
        errors.append(f"Unknown scene/phase: {scene_id}")
        return errors  # Can't check reachability if target doesn't exist

    # Check current scene is valid in module
    current_scene_id = session.current_scene_id
    if not _entity_exists(current_scene_id, module.scene_phases):
        errors.append(f"Current scene '{current_scene_id}' not in module")
        return errors

    # Prevent self-transitions (no movement)
    if scene_id == current_scene_id:
        # Self-transitions are allowed (staying in same scene)
        return errors

    # Check if target is reachable: find a valid transition from current to target
    # A transition is valid if it exists and has its target in the module
    reachable = False
    if isinstance(module.phase_transitions, dict):
        for transition_id, transition in module.phase_transitions.items():
            # Check if this transition starts from current scene
            if transition.from_phase == current_scene_id:
                # Check if this transition goes to target scene
                if transition.to_phase == scene_id:
                    # Check if target is valid
                    if _entity_exists(transition.to_phase, module.scene_phases):
                        reachable = True
                        break

    if not reachable:
        errors.append(
            f"Scene '{scene_id}' is not reachable from current scene '{current_scene_id}'"
        )

    return errors


def _entity_exists(entity_id: str, entity_map: dict) -> bool:
    """Check if an entity exists in a map.

    Args:
        entity_id: Entity ID to check.
        entity_map: Dictionary of entities.

    Returns:
        True if entity exists.
    """
    return entity_id in entity_map if isinstance(entity_map, dict) else False
