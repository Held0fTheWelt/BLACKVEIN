"""Decision validation for the story runtime.

Provides validation infrastructure for mock decisions and AI proposals
before they are applied to the canonical session state.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.runtime.reference_policy import ReferencePolicy
from app.runtime.scene_legality import SceneTransitionLegality


def validate_action_type(action_type: str) -> tuple[bool, str | None]:
    """Validate that an action type is in the canonical taxonomy.

    Args:
        action_type: The proposed action type

    Returns:
        Tuple of (is_valid, error_message)
        If valid: (True, None)
        If invalid: (False, error_message)
    """
    from app.runtime.decision_policy import AIActionType

    if not action_type:
        return False, "action_type cannot be empty"

    try:
        AIActionType(action_type)
        return True, None
    except ValueError:
        allowed = ", ".join([at.value for at in AIActionType])
        return False, (
            f"Unknown action type: '{action_type}'. "
            f"Allowed types: {allowed}"
        )


def validate_action_structure(
    action_type: str, action_data: dict, module: Any = None, session: Any = None
) -> tuple[bool, list[str]]:
    """Validate that an action has required fields for its type.

    Also validates action references (trigger IDs, character IDs) when module is provided.

    Args:
        action_type: The action type (must be valid AIActionType)
        action_data: Dict of action fields
        module: Optional ContentModule for reference validation
        session: Optional SessionState for context-aware reference checks

    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    from app.runtime.decision_policy import AIActionType

    errors = []

    try:
        action = AIActionType(action_type)
    except ValueError:
        # This should have been caught by validate_action_type()
        errors.append(f"Invalid action type: {action_type}")
        return False, errors

    # Validate required fields based on action type
    if action == AIActionType.STATE_UPDATE:
        if not action_data.get("target_path"):
            errors.append("STATE_UPDATE requires 'target_path'")
        if action_data.get("next_value") is None:
            errors.append("STATE_UPDATE requires 'next_value'")

    elif action == AIActionType.RELATIONSHIP_SHIFT:
        if not action_data.get("target_path"):
            errors.append("RELATIONSHIP_SHIFT requires 'target_path'")
        if action_data.get("next_value") is None:
            errors.append("RELATIONSHIP_SHIFT requires 'next_value'")

    elif action == AIActionType.SCENE_TRANSITION:
        if not action_data.get("scene_id"):
            errors.append("SCENE_TRANSITION requires 'scene_id'")

    elif action == AIActionType.TRIGGER_ASSERTION:
        if not action_data.get("trigger_ids"):
            errors.append("TRIGGER_ASSERTION requires 'trigger_ids'")
        elif module is not None:
            # Validate trigger references (W2.2.3)
            current_scene_id = session.current_scene_id if session else None
            for trigger_id in action_data["trigger_ids"]:
                ref_decision = ReferencePolicy.evaluate(
                    "trigger", trigger_id, module,
                    session=session, current_scene_id=current_scene_id
                )
                if not ref_decision.allowed:
                    errors.append(
                        f"Trigger reference validation failed: {ref_decision.reason_message} "
                        f"(reason: {ref_decision.reason_code})"
                    )

    elif action == AIActionType.DIALOGUE_IMPULSE:
        if not action_data.get("character_id"):
            errors.append("DIALOGUE_IMPULSE requires 'character_id'")
        elif module is not None:
            # Validate character reference (W2.2.3)
            char_id = action_data["character_id"]
            ref_decision = ReferencePolicy.evaluate("character", char_id, module)
            if not ref_decision.allowed:
                errors.append(
                    f"Character reference validation failed: {ref_decision.reason_message} "
                    f"(reason: {ref_decision.reason_code})"
                )
        if not action_data.get("impulse_text"):
            errors.append("DIALOGUE_IMPULSE requires 'impulse_text'")

    elif action == AIActionType.CONFLICT_SIGNAL:
        if not action_data.get("intensity") and action_data.get("intensity") != 0:
            errors.append("CONFLICT_SIGNAL requires 'intensity'")

    return len(errors) == 0, errors


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

    # Check scene transition legality (W2.2.4)
    # Validates against canonical scene transition rules with actual detected triggers
    # This ensures validation-time and execution-time semantics are coherent
    if hasattr(decision, "proposed_scene_id") and decision.proposed_scene_id:
        current_scene_id = session.current_scene_id if session else None
        # Get detected triggers from decision; they're available at validation time
        decision_triggers = getattr(decision, "detected_triggers", [])
        legality_decision = SceneTransitionLegality.check_transition_legal(
            current_scene_id, decision.proposed_scene_id, module,
            session=session, detected_triggers=decision_triggers  # W2.2.4: Use actual triggers from decision
        )
        if not legality_decision.allowed:
            errors.append(
                f"Scene transition rejected: {legality_decision.reason}"
            )

    # Check ending legality (W2.2.4)
    # Validates if any ending condition is legally triggered with actual detected triggers
    # This is a pre-check; actual ending determination happens in next_situation
    if hasattr(decision, "proposed_ending_id") and decision.proposed_ending_id:
        # Get detected triggers from decision; they're available at validation time
        decision_triggers = getattr(decision, "detected_triggers", [])
        ending_id, legality_decision = SceneTransitionLegality.check_ending_legal(
            module, session=session, detected_triggers=decision_triggers  # W2.2.4: Use actual triggers from decision
        )
        # Check if the proposed ending matches a legally available ending
        if ending_id != decision.proposed_ending_id:
            errors.append(
                f"Ending '{decision.proposed_ending_id}' is not currently legal. "
                f"Legal ending (if any): {ending_id}"
            )

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

    # Check reference integrity for entity types (W2.2.3)
    entity_type = parts[0]
    entity_id = parts[1] if len(parts) > 1 else None

    if entity_type == "characters" and entity_id:
        ref_decision = ReferencePolicy.evaluate("character", entity_id, module)
        if not ref_decision.allowed:
            errors.append(
                f"Reference validation failed: {ref_decision.reason_message} "
                f"(reason: {ref_decision.reason_code})"
            )
            return errors
    elif entity_type == "relationships" and entity_id:
        ref_decision = ReferencePolicy.evaluate("relationship", entity_id, module)
        if not ref_decision.allowed:
            errors.append(
                f"Reference validation failed: {ref_decision.reason_message} "
                f"(reason: {ref_decision.reason_code})"
            )
            return errors
    elif entity_type == "scene_state" and entity_id:
        current_scene_id = session.current_scene_id if session else None
        ref_decision = ReferencePolicy.evaluate(
            "scene", entity_id, module,
            session=session, current_scene_id=current_scene_id
        )
        if not ref_decision.allowed:
            errors.append(
                f"Reference validation failed: {ref_decision.reason_message} "
                f"(reason: {ref_decision.reason_code})"
            )
            return errors
    elif entity_type not in ["metadata", "conflict_state", "runtime", "system", "logs", "decision", "session", "turn", "cache"]:
        errors.append(f"Unknown entity type in target: {entity_type}")

    # Step 4: Check mutation permission (W2.2.2)
    # =========================================
    from app.runtime.mutation_policy import MutationPolicy

    policy_decision = MutationPolicy.evaluate(target)
    if not policy_decision.allowed:
        errors.append(
            f"Mutation blocked: target '{target}' — {policy_decision.reason_message} "
            f"(reason: {policy_decision.reason_code})"
        )
        return errors

    # Validate next_value if present
    if hasattr(delta, "next_value") and delta.next_value is not None:
        if isinstance(delta.next_value, (int, float)):
            if not (0 <= delta.next_value <= 100):
                errors.append(
                    f"Numeric delta values must be 0-100, got {delta.next_value}"
                )

    return errors


