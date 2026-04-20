"""Transitional: in-process turn pipeline (mock path + validation) for ``SessionState``.

Deterministic mock decisions through validate → deltas → apply → finalize for **local
simulation and tests**. Not authoritative live play; World Engine owns server-side
execution for real runs.
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
from app.runtime.narrative_commit import (
    narrative_commit_for_source_gate_rejection,
    resolve_narrative_commit,
)
from app.runtime.runtime_models import (
    DeltaType,
    DeltaValidationStatus,
    EventLogEntry,
    ExecutionFailureReason,
    GuardOutcome,
    MockDecision,
    NarrativeCommitRecord,
    ProposalSource,
    ProposedStateDelta,
    SessionState,
    SessionStatus,
    StateDelta,
    TurnStatus,
)


# ===== Imported Model Classes =====
#
# ProposedStateDelta, MockDecision imported from runtime_models


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
        narrative_commit: Bounded authoritative narrative outcome for this turn (in-process
            runtime); None on system_error.
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
    narrative_commit: NarrativeCommitRecord | None = None


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


def _accumulate_turn_context(
    session: SessionState,
    result: TurnExecutionResult,
    prior_scene_id: str | None = None,
) -> None:
    """Accumulate short-term context and session history from turn result.

    W2.3-R2: Wire W2.3 layers into real runtime flow.

    Derives ShortTermTurnContext from the turn result and updates:
    1. session.context_layers.short_term_context
    2. session.context_layers.session_history

    This is called after every turn (success or system_error) to accumulate
    real continuity data into the session state.

    Args:
        session: The SessionState to update (modified in place).
        result: The TurnExecutionResult from the completed turn.
        prior_scene_id: The scene ID before this turn (for transition detection).

    Note:
        - Initializes SessionHistory if not yet present
        - Maintains bounded history (max_size=100)
        - Works for all guard_outcome values (accepted, partially_accepted, rejected, structurally_invalid)
    """
    # Local imports to avoid circular dependency
    from app.runtime.session_history import HistoryEntry, SessionHistory
    from app.runtime.short_term_context import build_short_term_context

    # Initialize SessionHistory if not present
    if session.context_layers.session_history is None:
        session.context_layers.session_history = SessionHistory(max_size=100)

    # Derive short-term context from result
    short_term_context = build_short_term_context(
        result, prior_scene_id=prior_scene_id, session_state=session
    )
    session.context_layers.short_term_context = short_term_context

    # Convert to history entry and add to session history
    if isinstance(session.context_layers.session_history, SessionHistory):
        history_entry = HistoryEntry.from_short_term_context(short_term_context)
        session.context_layers.session_history.add_entry(history_entry)


def _derive_runtime_context(
    session: SessionState,
    module: ContentModule,
    last_result: TurnExecutionResult | None = None,
) -> None:
    """Derive progression, relationship, narrative threads, and lore from accumulated history.

    W2.3-R3 + Task 1D: Wire downstream context layers into real runtime flow.

    Called after _accumulate_turn_context() to keep downstream layers current.
    Skips derivation if session history is not yet populated (guard for early calls).

    Derivation order:
    1. ProgressionSummary — from SessionHistory
    2. RelationshipAxisContext — from SessionHistory
    3. NarrativeThreadSet — derived when ``last_result.narrative_commit`` is present;
       migration-on-read hydrates ``context_layers.narrative_threads`` from metadata if missing
    4. LoreDirectionContext — single pass; optional ``thread_set`` only when step 3 ran

    Args:
        session: The SessionState to update (modified in place).
        module: The ContentModule for lore/direction extraction.
        last_result: Last turn result; if missing or without narrative_commit, threads are not
            updated, lore runs without thread_set, and thread markers are not applied.

    Note:
        - Deterministic bounded derivations; salient_axes ≤ 10, selected_units ≤ 15
        - Thread snapshot is dual-written to ``session.metadata["narrative_threads"]`` on update
    """
    from app.runtime.lore_direction_context import derive_lore_direction_context
    from app.runtime.narrative_threads import (
        NarrativeThreadSet,
        apply_thread_markers_to_layers,
        hydrate_narrative_threads_layer,
        sync_narrative_thread_set,
        update_narrative_threads_from_commit,
    )
    from app.runtime.progression_summary import derive_progression_summary
    from app.runtime.relationship_context import derive_relationship_axis_context

    history = session.context_layers.session_history
    if history is None or history.size == 0:
        return

    # Step 1: ProgressionSummary (depends only on SessionHistory)
    progression = derive_progression_summary(history)
    session.context_layers.progression_summary = progression

    # Step 2: RelationshipAxisContext (depends only on SessionHistory)
    relationship = derive_relationship_axis_context(history)
    session.context_layers.relationship_axis_context = relationship

    # Task 1D: hydrate working thread layer (metadata → context_layers if needed)
    hydrate_narrative_threads_layer(session)

    thread_for_lore: NarrativeThreadSet | None = None
    nc = last_result.narrative_commit if last_result is not None else None
    if nc is not None:
        prior = session.context_layers.narrative_threads
        if not isinstance(prior, NarrativeThreadSet):
            prior = NarrativeThreadSet()
        updated = update_narrative_threads_from_commit(
            prior,
            narrative_commit=nc,
            _history=history,
            progression=progression,
            relationship=relationship,
        )
        sync_narrative_thread_set(session, updated)
        apply_thread_markers_to_layers(session)
        thread_for_lore = updated

    # Step 4: LoreDirectionContext (single pass; threads optional)
    lore = derive_lore_direction_context(
        module=module,
        current_scene_id=session.current_scene_id,
        history=history,
        progression_summary=progression,
        relationship_context=relationship,
        thread_set=thread_for_lore,
    )
    session.context_layers.lore_direction_context = lore


def _finalize_success_turn(
    session: SessionState,
    module: ContentModule,
    result: TurnExecutionResult,
    prior_scene_id: str | None,
) -> None:
    """Run shared post-turn accumulation for successful execution paths (including gate reject)."""
    _accumulate_turn_context(session, result, prior_scene_id=prior_scene_id)
    _derive_runtime_context(session, module, last_result=result)


NARRATIVE_COMMIT_LOG_MAX_ENTRIES = 100


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
    enforce_responder_only: bool = False,
) -> TurnExecutionResult:
    """Execute a story turn with deterministic mock decision.

    Orchestrates: validation → construction → application → finalization.
    Emits structured events for every phase.
    Accumulates short-term context and session history (W2.3-R2).

    Args:
        session: Current session state
        current_turn: Turn number (e.g., 1, 2, 3)
        mock_decision: Deterministic proposal with triggers and deltas
        module: Loaded content module for validation
        enforce_responder_only: If True, only RESPONDER_DERIVED proposals are allowed.
                              Rejects all non-responder proposals at gate.
                              Default False for backward compatibility with non-AI paths.

    Returns:
        TurnExecutionResult with execution status, deltas, state, and events
    """
    started_at = datetime.now(timezone.utc)
    prior_scene_id = session.current_scene_id  # Capture before turn execution
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
        # Enforce responder-only proposal gate if enabled (W2.4.5)
        if enforce_responder_only and mock_decision.proposal_source != ProposalSource.RESPONDER_DERIVED:
            completed_at = datetime.now(timezone.utc)
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            gate_rejection_error = f"Proposals rejected: source is {mock_decision.proposal_source.value}, only RESPONDER_DERIVED allowed"

            event_log.log(
                "source_gate_rejected",
                gate_rejection_error,
                payload={
                    "proposal_source": mock_decision.proposal_source.value,
                    "enforce_responder_only": enforce_responder_only,
                },
            )

            # Convert ProposedStateDelta to StateDelta for rejected_deltas
            rejected_deltas = []
            for proposed in mock_decision.proposed_deltas:
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
                    source="source_gate_rejected",
                    turn_number=current_turn,
                    validation_status=DeltaValidationStatus.REJECTED,
                )
                rejected_deltas.append(delta)

            narrative_commit = narrative_commit_for_source_gate_rejection(
                turn_number=current_turn,
                prior_scene_id=prior_scene_id or session.current_scene_id,
                decision=mock_decision,
                guard_outcome=GuardOutcome.REJECTED,
                rejected_deltas=rejected_deltas,
            )

            event_log.log(
                "turn_completed",
                f"Turn {current_turn} completed: source gate rejected proposals",
                payload={
                    "turn_number": current_turn,
                    "accepted_delta_count": 0,
                    "rejected_delta_count": len(rejected_deltas),
                    "guard_outcome": GuardOutcome.REJECTED.value,
                    "detected_triggers": mock_decision.detected_triggers,
                    "duration_ms": duration_ms,
                },
            )

            gate_result = TurnExecutionResult(
                turn_number=current_turn,
                session_id=session.session_id,
                execution_status="success",
                decision=mock_decision,
                validation_outcome=None,
                validation_errors=[gate_rejection_error],
                accepted_deltas=[],
                rejected_deltas=rejected_deltas,
                updated_canonical_state=session.canonical_state,
                updated_scene_id=prior_scene_id,
                updated_ending_id=None,
                guard_outcome=GuardOutcome.REJECTED,
                failure_reason=ExecutionFailureReason.NONE,
                narrative_commit=narrative_commit,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                events=event_log.flush(),
            )
            _finalize_success_turn(session, module, gate_result, prior_scene_id=prior_scene_id)
            return gate_result
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

        # Step 4–5: Narrative commit (post-delta): ending before explicit proposed transition
        guard_outcome_value = _compute_guard_outcome(accepted_deltas, rejected_deltas, "success")
        narrative_commit = resolve_narrative_commit(
            turn_number=current_turn,
            prior_scene_id=prior_scene_id or session.current_scene_id,
            post_delta_canonical_state=updated_state,
            session_template=session,
            decision=mock_decision,
            module=module,
            guard_outcome=guard_outcome_value,
            accepted_deltas=accepted_deltas,
            rejected_deltas=rejected_deltas,
        )
        updated_scene_id = narrative_commit.committed_scene_id
        updated_ending_id = narrative_commit.committed_ending_id

        if narrative_commit.situation_status == "ending_reached" and updated_ending_id:
            event_log.log(
                "ending_triggered",
                f"Ending triggered: {updated_ending_id}",
                payload={"ending_id": updated_ending_id},
            )
        elif narrative_commit.situation_status == "transitioned":
            event_log.log(
                "scene_changed",
                f"Scene transitioned to {updated_scene_id}",
                payload={
                    "from_scene": prior_scene_id,
                    "to_scene": updated_scene_id,
                },
            )
        elif mock_decision.proposed_scene_id:
            post_delta_session = session.model_copy(deep=True)
            post_delta_session.canonical_state = deepcopy(updated_state)
            post_delta_session.current_scene_id = prior_scene_id or session.current_scene_id
            td = SceneTransitionLegality.check_transition_legal(
                prior_scene_id or session.current_scene_id,
                mock_decision.proposed_scene_id,
                module,
                session=post_delta_session,
                detected_triggers=mock_decision.detected_triggers,
            )
            if not td.allowed:
                event_log.log(
                    "scene_transition_blocked",
                    (
                        f"Scene transition to {mock_decision.proposed_scene_id} "
                        f"blocked: {td.reason}"
                    ),
                    payload={
                        "from_scene": prior_scene_id,
                        "proposed_scene": mock_decision.proposed_scene_id,
                        "reason": td.reason,
                    },
                )

        # Step 6: Finalize
        completed_at = datetime.now(timezone.utc)
        duration_ms = (completed_at - started_at).total_seconds() * 1000

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
            updated_ending_id=updated_ending_id,
            guard_outcome=guard_outcome_value,
            narrative_commit=narrative_commit,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            events=event_log.flush(),
        )

        _finalize_success_turn(session, module, result, prior_scene_id=prior_scene_id)

        return result

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

        result = TurnExecutionResult(
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
            narrative_commit=None,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            events=event_log.flush(),
        )

        # W2.3-R2: Accumulate context even on failure
        _accumulate_turn_context(session, result, prior_scene_id=prior_scene_id)
        # W2.3-R3: Derive downstream context layers from updated history
        _derive_runtime_context(session, module, last_result=None)

        return result


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

    if result.narrative_commit is not None:
        updated_session.current_scene_id = result.narrative_commit.committed_scene_id
        if result.narrative_commit.is_terminal:
            updated_session.status = SessionStatus.ENDED
    elif result.updated_scene_id:
        updated_session.current_scene_id = result.updated_scene_id

    # Increment turn counter
    updated_session.turn_counter += 1

    # Update modification timestamp
    updated_session.updated_at = datetime.now(timezone.utc)

    if result.narrative_commit is not None:
        log_key = "narrative_commit_log"
        if log_key not in updated_session.metadata:
            updated_session.metadata[log_key] = []
        log_list: list = updated_session.metadata[log_key]
        log_list.append(result.narrative_commit.model_dump(mode="json"))
        updated_session.metadata[log_key] = log_list[-NARRATIVE_COMMIT_LOG_MAX_ENTRIES:]

    return updated_session
