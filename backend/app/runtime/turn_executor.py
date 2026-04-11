"""Transitional: in-process turn pipeline (mock path + validation) for ``SessionState``.

Deterministic mock decisions through validate → deltas → apply → finalize for **local
simulation and tests**. Not authoritative live play; World Engine owns server-side
execution for real runs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.content.module_models import ContentModule
from app.runtime.event_log import RuntimeEventLog
from app.runtime.narrative_commit import narrative_commit_for_source_gate_rejection
from app.runtime.runtime_models import (
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
from app.runtime.turn_execution_types import TurnExecutionResult
from app.runtime.turn_executor_decision_delta import (
    DeltaApplicationError,
    _compute_guard_outcome,
    apply_deltas,
    construct_deltas,
    extract_entity_id,
    get_current_value,
    infer_delta_type,
    _set_nested_value,
)


# ===== Exception Classes =====


class TurnExecutionException(RuntimeError):
    """Base exception for turn execution errors."""

    pass


# ===== Helper Functions =====
# Delta path helpers and construct/apply deltas live in ``turn_executor_decision_delta``
# (re-exported above for backward compatibility).


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


def _turn_source_gate_rejection(
    *,
    session: SessionState,
    current_turn: int,
    mock_decision: MockDecision,
    event_log: RuntimeEventLog,
    started_at: datetime,
    prior_scene_id: str | None,
) -> TurnExecutionResult:
    completed_at = datetime.now(timezone.utc)
    duration_ms = (completed_at - started_at).total_seconds() * 1000

    gate_rejection_error = (
        f"Proposals rejected: source is {mock_decision.proposal_source.value}, "
        "only RESPONDER_DERIVED allowed"
    )

    event_log.log(
        "source_gate_rejected",
        gate_rejection_error,
        payload={
            "proposal_source": mock_decision.proposal_source.value,
            "enforce_responder_only": True,
        },
    )

    rejected_deltas: list[StateDelta] = []
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

    return TurnExecutionResult(
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


def _execute_turn_validated_pipeline(
    session: SessionState,
    current_turn: int,
    mock_decision: MockDecision,
    module: ContentModule,
    event_log: RuntimeEventLog,
    started_at: datetime,
    prior_scene_id: str | None,
) -> TurnExecutionResult:
    from app.runtime.turn_executor_validated_pipeline import run_validated_turn_pipeline

    return run_validated_turn_pipeline(
        session,
        current_turn,
        mock_decision,
        module,
        event_log,
        started_at,
        prior_scene_id,
    )


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
        if enforce_responder_only and mock_decision.proposal_source != ProposalSource.RESPONDER_DERIVED:
            gate_result = _turn_source_gate_rejection(
                session=session,
                current_turn=current_turn,
                mock_decision=mock_decision,
                event_log=event_log,
                started_at=started_at,
                prior_scene_id=prior_scene_id,
            )
            _finalize_success_turn(session, module, gate_result, prior_scene_id=prior_scene_id)
            return gate_result

        result = _execute_turn_validated_pipeline(
            session,
            current_turn,
            mock_decision,
            module,
            event_log,
            started_at,
            prior_scene_id,
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
