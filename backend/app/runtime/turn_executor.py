"""Mock turn executor for the story runtime.

W2.0.3 implementation: Canonical mock turn executor that processes deterministic
mock decisions through validation, delta construction, and state application
without real AI integration.

Implements the core pipeline: validate -> construct deltas -> apply -> finalize.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.content.module_models import ContentModule
from app.runtime.validators import ValidationOutcome, validate_decision
from app.runtime.w2_models import (
    DeltaType,
    DeltaValidationStatus,
    EventLogEntry,
    SessionState,
    StateDelta,
    TurnStatus,
)


# ===== Model Classes =====


class ProposedStateDelta(BaseModel):
    """A proposed state change from a mock decision.

    Attributes:
        target: Dot-path to affected entity (e.g., "characters.veronique.emotional_state").
        next_value: Value to apply (None if not applicable).
        previous_value: Current value before change (populated during construction).
        delta_type: Type of change (character_state, relationship, etc.).
    """

    target: str
    next_value: Any = None
    previous_value: Any = None
    delta_type: DeltaType | None = None


class MockDecision(BaseModel):
    """A deterministic mock story decision.

    Represents what the AI would propose: triggered events, state changes,
    scene progression, and narrative text.

    Attributes:
        detected_triggers: List of trigger IDs detected in this turn.
        proposed_deltas: List of ProposedStateDelta objects (state changes).
        proposed_scene_id: Optional target scene/phase ID for scene transitions.
        narrative_text: AI-generated narrative text for this turn.
        rationale: Explanation of the decision (for audit/debugging).
    """

    detected_triggers: list[str] = Field(default_factory=list)
    proposed_deltas: list[ProposedStateDelta] = Field(default_factory=list)
    proposed_scene_id: str | None = None
    narrative_text: str = ""
    rationale: str = ""


class TurnExecutionResult(BaseModel):
    """Result of executing a complete turn.

    Captures everything that happened: validation outcome, accepted/rejected deltas,
    updated state, execution timing, and audit events.

    Attributes:
        turn_number: Monotonically increasing turn counter.
        session_id: Parent session identifier.
        execution_status: Status of turn execution (success/failure).
        decision: The MockDecision that was executed.
        validation_outcome: ValidationOutcome from decision validation.
        validation_errors: List of validation errors encountered.
        accepted_deltas: StateDelta objects that passed validation and were applied.
        rejected_deltas: StateDelta objects that failed validation.
        updated_canonical_state: Full canonical state after applying deltas.
        updated_scene_id: Scene ID after execution (if changed).
        started_at: Timestamp when turn execution began.
        completed_at: Timestamp when turn execution completed.
        duration_ms: Execution time in milliseconds.
        events: Audit events created during execution.
    """

    turn_number: int
    session_id: str
    execution_status: str  # "success" or "failure"
    decision: MockDecision
    validation_outcome: ValidationOutcome
    validation_errors: list[str] = Field(default_factory=list)
    accepted_deltas: list[StateDelta] = Field(default_factory=list)
    rejected_deltas: list[StateDelta] = Field(default_factory=list)
    updated_canonical_state: dict[str, Any] = Field(default_factory=dict)
    updated_scene_id: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    events: list[EventLogEntry] = Field(default_factory=list)


# ===== Exception Classes =====


class TurnExecutionException(RuntimeError):
    """Base exception for turn execution errors."""

    pass


class DeltaApplicationError(RuntimeError):
    """Exception raised when delta application fails."""

    pass


# ===== Helper Functions =====


def get_current_value(state: dict[str, Any], target_path: str) -> Any:
    """Get the current value at a target path in the state.

    Uses dot-notation for nested navigation (e.g., "characters.veronique.emotional_state").

    Args:
        state: The canonical state dict.
        target_path: Dot-separated path to the value.

    Returns:
        Current value at the path, or None if path doesn't exist.

    Example:
        >>> state = {"characters": {"veronique": {"emotional_state": 50}}}
        >>> get_current_value(state, "characters.veronique.emotional_state")
        50
    """
    parts = target_path.split(".")
    current = state
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _set_nested_value(state: dict[str, Any], path: str, value: Any) -> None:
    """Set a value at a nested path in the state dict.

    Creates intermediate dicts as needed. Mutates state in place.

    Args:
        state: The state dict to modify.
        path: Dot-separated path to the target.
        value: Value to set.

    Raises:
        DeltaApplicationError: If path is invalid or malformed.

    Example:
        >>> state = {}
        >>> _set_nested_value(state, "characters.veronique.emotional_state", 70)
        >>> state["characters"]["veronique"]["emotional_state"]
        70
    """
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
    """Infer the delta type from the target path.

    Args:
        target_path: Dot-separated path (e.g., "characters.veronique.emotional_state").

    Returns:
        Inferred DeltaType.

    Example:
        >>> infer_delta_type("characters.veronique.emotional_state")
        DeltaType.CHARACTER_STATE
    """
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
    """Extract the entity ID from a target path.

    Args:
        target_path: Dot-separated path (e.g., "characters.veronique.emotional_state").

    Returns:
        Entity ID (e.g., "veronique"), or None if not present.

    Example:
        >>> extract_entity_id("characters.veronique.emotional_state")
        "veronique"
    """
    if not target_path or not isinstance(target_path, str):
        return None

    parts = target_path.split(".")
    if len(parts) >= 2:
        return parts[1]
    return None


# ===== Core Functions =====


def construct_deltas(
    decision: MockDecision,
    session: SessionState,
    validation_outcome: ValidationOutcome,
    turn_number: int,
) -> tuple[list[StateDelta], list[StateDelta]]:
    """Construct accepted and rejected StateDelta objects from a mock decision.

    Converts ProposedStateDelta objects into canonical StateDelta objects with
    validation status lifecycle tracking. Separates accepted from rejected based
    on validation_outcome.

    Args:
        decision: The MockDecision being executed.
        session: The current SessionState (for baseline state).
        validation_outcome: Result of decision validation.
        turn_number: Current turn number.

    Returns:
        Tuple of (accepted_deltas, rejected_deltas).

    Example:
        >>> decision = MockDecision(
        ...     proposed_deltas=[
        ...         ProposedStateDelta(
        ...             target="characters.veronique.emotional_state",
        ...             next_value=70
        ...         )
        ...     ]
        ... )
        >>> accepted, rejected = construct_deltas(decision, session, outcome, 1)
        >>> len(accepted)
        1
        >>> accepted[0].validation_status == DeltaValidationStatus.ACCEPTED
        True
    """
    accepted_deltas = []
    rejected_deltas = []

    for idx, proposed in enumerate(decision.proposed_deltas):
        # Infer delta type from target path
        delta_type = (
            proposed.delta_type
            if proposed.delta_type
            else infer_delta_type(proposed.target)
        )

        # Get current value from session state
        previous_value = get_current_value(session.canonical_state, proposed.target)

        # Create base StateDelta
        delta = StateDelta(
            delta_type=delta_type,
            target_path=proposed.target,
            target_entity=extract_entity_id(proposed.target),
            previous_value=previous_value,
            next_value=proposed.next_value,
            source="ai_proposal",
            turn_number=turn_number,
        )

        # Determine validation status
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
    """Apply accepted deltas to the canonical state.

    Returns a new state dict without mutating the input. Uses deep copy for safety.

    Args:
        canonical_state: Current canonical state (not modified).
        deltas: List of StateDelta objects to apply (should all be ACCEPTED).

    Returns:
        New canonical state dict with deltas applied.

    Raises:
        DeltaApplicationError: If a delta cannot be applied.

    Example:
        >>> state = {"characters": {"veronique": {"emotional_state": 50}}}
        >>> delta = StateDelta(
        ...     target_path="characters.veronique.emotional_state",
        ...     next_value=70,
        ...     validation_status=DeltaValidationStatus.ACCEPTED
        ... )
        >>> new_state = apply_deltas(state, [delta])
        >>> new_state["characters"]["veronique"]["emotional_state"]
        70
    """
    # Deep copy to avoid mutating input
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


async def execute_turn(
    session: SessionState,
    current_turn: int,
    mock_decision: MockDecision,
    *,
    module: ContentModule,
) -> TurnExecutionResult:
    """Execute a complete story turn with a mock decision.

    Main entry point for turn execution. Implements the core pipeline:
    1. Validate the decision against session and module
    2. Construct StateDelta objects
    3. Apply accepted deltas to canonical state
    4. Create audit events
    5. Return comprehensive result

    Args:
        session: Active SessionState to execute against.
        current_turn: Turn number for this execution.
        mock_decision: MockDecision object with proposed changes.
        module: ContentModule being executed.

    Returns:
        TurnExecutionResult with full execution details.

    Raises:
        TurnExecutionException: If turn execution fails critically.

    Example:
        >>> session = SessionState(
        ...     session_id="test-123",
        ...     module_id="god_of_carnage",
        ...     module_version="0.1.0",
        ...     current_scene_id="phase_1",
        ...     canonical_state={"characters": {"veronique": {"emotional_state": 50}}}
        ... )
        >>> decision = MockDecision(
        ...     proposed_deltas=[
        ...         ProposedStateDelta(
        ...             target="characters.veronique.emotional_state",
        ...             next_value=70
        ...         )
        ...     ]
        ... )
        >>> result = await execute_turn(session, 1, decision, module=module)
        >>> result.execution_status
        "success"
        >>> result.accepted_deltas[0].next_value
        70
    """
    started_at = datetime.now(timezone.utc)
    events = []

    try:
        # Step 1: Validate decision
        validation_outcome = validate_decision(mock_decision, session, module)

        # Step 2: Construct deltas
        accepted_deltas, rejected_deltas = construct_deltas(
            mock_decision, session, validation_outcome, current_turn
        )

        # Step 3: Apply accepted deltas
        updated_state = apply_deltas(session.canonical_state, accepted_deltas)

        # Step 4: Handle scene transition if present
        updated_scene_id = session.current_scene_id
        if mock_decision.proposed_scene_id:
            # Verify scene exists in module
            if mock_decision.proposed_scene_id in module.scene_phases:
                updated_scene_id = mock_decision.proposed_scene_id
                # Create scene changed event
                scene_event = EventLogEntry(
                    event_type="scene_changed",
                    order_index=1,
                    summary=f"Scene transitioned to {updated_scene_id}",
                    payload={
                        "from_scene": session.current_scene_id,
                        "to_scene": updated_scene_id,
                    },
                    session_id=session.session_id,
                    turn_number=current_turn,
                )
                events.append(scene_event)

        # Step 5: Create turn_executed event
        turn_event = EventLogEntry(
            event_type="turn_executed",
            order_index=0,
            summary=f"Turn {current_turn} executed with {len(accepted_deltas)} accepted deltas",
            payload={
                "turn_number": current_turn,
                "accepted_delta_count": len(accepted_deltas),
                "rejected_delta_count": len(rejected_deltas),
                "detected_triggers": mock_decision.detected_triggers,
            },
            session_id=session.session_id,
            turn_number=current_turn,
        )
        events.insert(0, turn_event)

        # Step 6: Finalize result
        completed_at = datetime.now(timezone.utc)
        duration_ms = (completed_at - started_at).total_seconds() * 1000

        result = TurnExecutionResult(
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
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            events=events,
        )

        return result

    except Exception as e:
        completed_at = datetime.now(timezone.utc)
        duration_ms = (completed_at - started_at).total_seconds() * 1000

        # Create error event
        error_event = EventLogEntry(
            event_type="turn_failed",
            order_index=0,
            summary=f"Turn {current_turn} failed: {str(e)}",
            payload={"error": str(e), "error_type": type(e).__name__},
            session_id=session.session_id,
            turn_number=current_turn,
        )
        events.append(error_event)

        return TurnExecutionResult(
            turn_number=current_turn,
            session_id=session.session_id,
            execution_status="failure",
            decision=mock_decision,
            validation_outcome=ValidationOutcome(
                is_valid=False,
                status="fail",
                errors=[str(e)],
            ),
            validation_errors=[str(e)],
            accepted_deltas=[],
            rejected_deltas=[],
            updated_canonical_state=session.canonical_state,
            updated_scene_id=session.current_scene_id,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            events=events,
        )
