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
from app.runtime.event_log import RuntimeEventLog
from app.runtime.scene_legality import SceneTransitionLegality
from app.runtime.validators import ValidationOutcome, validate_decision
from app.runtime.w2_models import (
    DeltaType,
    DeltaValidationStatus,
    EventLogEntry,
    ExecutionFailureReason,
    GuardOutcome,
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
        updated_scene_id: Scene ID after execution (if changed, via canonical legality check).
        updated_ending_id: Ending ID if an ending was triggered (via canonical legality check).
        guard_outcome: Canonical guard classification (accepted, partially_accepted, rejected, structurally_invalid).
        failure_reason: Explicit classification of any failure (generation, parsing, validation, or none).
        started_at: Timestamp when turn execution began.
        completed_at: Timestamp when turn execution completed.
        duration_ms: Execution time in milliseconds.
        events: Audit events created during execution.
    """

    turn_number: int
    session_id: str
    execution_status: str  # "success", "validation_failed", or "system_error"
    decision: MockDecision
    validation_outcome: ValidationOutcome | None = None
    validation_errors: list[str] = Field(default_factory=list)
    accepted_deltas: list[StateDelta] = Field(default_factory=list)
    rejected_deltas: list[StateDelta] = Field(default_factory=list)
    updated_canonical_state: dict[str, Any] = Field(default_factory=dict)
    updated_scene_id: str | None = None
    updated_ending_id: str | None = None
    guard_outcome: GuardOutcome = GuardOutcome.STRUCTURALLY_INVALID
    failure_reason: ExecutionFailureReason = ExecutionFailureReason.NONE
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


def _compute_guard_outcome(
    accepted: list,
    rejected: list,
    execution_status: str,
) -> GuardOutcome:
    """Compute the canonical guard outcome based on delta acceptance status.

    Args:
        accepted: List of accepted deltas.
        rejected: List of rejected deltas.
        execution_status: Turn execution status ("success", "validation_failed", "system_error").

    Returns:
        GuardOutcome classification for the turn.
    """
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


async def execute_turn(
    session: SessionState,
    current_turn: int,
    mock_decision: MockDecision,
    module: ContentModule,
) -> TurnExecutionResult:
    """Execute a story turn with deterministic mock decision.

    Orchestrates: validation → construction → application → finalization.
    Emits structured events for every phase.

    Args:
        session: Current session state
        current_turn: Turn number (e.g., 1, 2, 3)
        mock_decision: Deterministic proposal with triggers and deltas
        module: Loaded content module for validation

    Returns:
        TurnExecutionResult with execution status, deltas, state, and events
    """
    started_at = datetime.now(timezone.utc)
    event_log = RuntimeEventLog(session_id=session.session_id, turn_number=current_turn)

    # Always emit turn_started first — even if execution fails below
    event_log.log(
        "turn_started",
        f"Turn {current_turn} started",
        payload={
            "turn_number": current_turn,
            "scene_id": session.current_scene_id,
        },
    )

    try:
        # Step 1: Validate decision
        validation_outcome = validate_decision(mock_decision, session, module)

        event_log.log(
            "decision_validated",
            f"Decision validated: {validation_outcome.status} "
            f"({len(validation_outcome.accepted_delta_indices)} accepted, "
            f"{len(validation_outcome.rejected_delta_indices)} rejected)",
            payload={
                "status": validation_outcome.status,
                "is_valid": validation_outcome.is_valid,
                "accepted_delta_count": len(validation_outcome.accepted_delta_indices),
                "rejected_delta_count": len(validation_outcome.rejected_delta_indices),
                "errors": validation_outcome.errors,
            },
        )

        # Step 2: Construct deltas
        accepted_deltas, rejected_deltas = construct_deltas(
            mock_decision, session, validation_outcome, current_turn
        )

        # Create delta payload with full accepted delta content
        accepted_delta_payloads = [
            {
                "id": d.id,
                "delta_type": d.delta_type,
                "target_path": d.target_path,
                "target_entity": d.target_entity,
                "previous_value": d.previous_value,
                "next_value": d.next_value,
                "source": d.source,
            }
            for d in accepted_deltas
        ]

        event_log.log(
            "deltas_generated",
            f"Deltas generated: {len(accepted_deltas)} accepted, {len(rejected_deltas)} rejected",
            payload={
                "accepted_count": len(accepted_deltas),
                "rejected_count": len(rejected_deltas),
                "accepted_deltas": accepted_delta_payloads,
                "rejected_delta_ids": [d.id for d in rejected_deltas],
            },
        )

        # Step 3: Apply accepted deltas
        updated_state = apply_deltas(session.canonical_state, accepted_deltas)

        event_log.log(
            "deltas_applied",
            f"{len(accepted_deltas)} delta(s) applied to canonical state",
            payload={
                "applied_count": len(accepted_deltas),
                "delta_ids": [d.id for d in accepted_deltas],
            },
        )

        # Step 4: Handle scene transition (W2.2.4 - enforce canonical legality)
        updated_scene_id = session.current_scene_id
        updated_ending_id = None

        # Check scene transition legality using canonical rules
        if mock_decision.proposed_scene_id:
            legality_decision = SceneTransitionLegality.check_transition_legal(
                session.current_scene_id,
                mock_decision.proposed_scene_id,
                module,
                session=session,
                detected_triggers=mock_decision.detected_triggers  # Use actual triggers from execution
            )
            if legality_decision.allowed:
                updated_scene_id = mock_decision.proposed_scene_id
                event_log.log(
                    "scene_changed",
                    f"Scene transitioned to {updated_scene_id}",
                    payload={
                        "from_scene": session.current_scene_id,
                        "to_scene": updated_scene_id,
                    },
                )
            else:
                # Scene transition was rejected by canonical legality rules
                # Log this for debugging - decision passed validation but doesn't meet execution criteria
                event_log.log(
                    "scene_transition_blocked",
                    f"Scene transition to {mock_decision.proposed_scene_id} blocked: {legality_decision.reason}",
                    payload={
                        "from_scene": session.current_scene_id,
                        "proposed_scene": mock_decision.proposed_scene_id,
                        "reason": legality_decision.reason,
                    },
                )

        # Step 4.5: Check ending legality (W2.2.4 - ending coherence)
        # Determine if any ending is legal at current scene with detected triggers
        ending_id, ending_legality = SceneTransitionLegality.check_ending_legal(
            module,
            session=session,
            detected_triggers=mock_decision.detected_triggers
        )
        if ending_id and ending_legality.allowed:
            updated_ending_id = ending_id
            event_log.log(
                "ending_triggered",
                f"Ending triggered: {ending_id}",
                payload={
                    "ending_id": ending_id,
                },
            )

        # Step 5: Finalize
        completed_at = datetime.now(timezone.utc)
        duration_ms = (completed_at - started_at).total_seconds() * 1000

        guard_outcome_value = _compute_guard_outcome(accepted_deltas, rejected_deltas, "success")

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
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            events=event_log.flush(),
        )

    except Exception as e:
        completed_at = datetime.now(timezone.utc)
        duration_ms = (completed_at - started_at).total_seconds() * 1000

        event_log.log(
            "turn_failed",
            f"Turn {current_turn} failed: {str(e)}",
            payload={
                "error": str(e),
                "error_type": type(e).__name__,
                "guard_outcome": GuardOutcome.STRUCTURALLY_INVALID.value,
            },
        )

        return TurnExecutionResult(
            turn_number=current_turn,
            session_id=session.session_id,
            execution_status="system_error",
            decision=mock_decision,
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[],
            rejected_deltas=[],
            updated_canonical_state=session.canonical_state,
            updated_scene_id=session.current_scene_id,
            guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            events=event_log.flush(),
        )


def commit_turn_result(
    session: SessionState,
    result: TurnExecutionResult,
) -> SessionState:
    """Commit successful turn result into canonical session state.

    After a successful turn execution, the TurnExecutionResult contains
    updated canonical state and potentially a new scene ID. This function
    commits those changes back into the SessionState so the session is
    ready for the next turn.

    Args:
        session: Current SessionState before turn
        result: TurnExecutionResult from successful turn execution

    Returns:
        Updated SessionState with committed progress

    Raises:
        ValueError: If result execution_status is not "success"
    """
    if result.execution_status != "success":
        raise ValueError(
            f"Cannot commit non-successful result (status: {result.execution_status})"
        )

    # Create updated session with committed progress
    updated_session = session.model_copy(deep=True)

    # Commit canonical state from result
    updated_session.canonical_state = result.updated_canonical_state

    # Commit scene progression if scene changed
    if result.updated_scene_id:
        updated_session.current_scene_id = result.updated_scene_id

    # Increment turn counter
    updated_session.turn_counter += 1

    # Update modification timestamp
    updated_session.updated_at = datetime.now(timezone.utc)

    return updated_session
