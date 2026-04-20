"""W2.0.1 — Reusable Pydantic models for in-process story session shape (SessionState, turns, deltas, logs).

These types define JSON-serializable structures for tests, tooling, persistence helpers,
and the **non-authoritative** in-process W2 pipeline. They are **not** evidence that the
Flask backend is the live narrative runtime; authoritative play runs in the **World
Engine** (see ``docs/architecture/backend_runtime_classification.md``).

Design: append-oriented event and delta records for reproducibility and logging.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.runtime.decision_policy import AIActionType
from app.runtime.role_contract import ResponderSection


# ===== Session Models =====


class SessionStatus(str, Enum):
    """Status of a story session."""

    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    CRASHED = "crashed"


class DegradedMarker(str, Enum):
    """Canonical markers for degraded session state.

    When recovery actions occur during turn execution, the session is marked
    with appropriate markers. These markers accumulate and persist for the
    session lifetime, creating an auditable recovery history.

    Markers:
    - DEGRADED: Overall flag (set when ANY marker is set)
    - RETRY_EXHAUSTED: Retries were exhausted, fallback attempted
    - REDUCED_CONTEXT_ACTIVE: Reduced-context retry mode was used
    - FALLBACK_ACTIVE: Fallback responder mode was used
    - SAFE_TURN_USED: Safe-turn no-op was invoked
    - RESTORE_USED: State was restored from snapshot
    """

    DEGRADED = "degraded"
    """Overall degraded flag."""

    RETRY_EXHAUSTED = "retry_exhausted"
    """Retries were exhausted."""

    REDUCED_CONTEXT_ACTIVE = "reduced_context_active"
    """Reduced-context retry mode was used."""

    FALLBACK_ACTIVE = "fallback_active"
    """Fallback responder mode was used."""

    SAFE_TURN_USED = "safe_turn_used"
    """Safe-turn no-op was invoked."""

    RESTORE_USED = "restore_used"
    """State was restored from snapshot."""


class DegradedSessionState(BaseModel):
    """Tracks degradation markers for a session.

    When the runtime invokes recovery actions (fallback, safe-turn, restore),
    the session accumulates degradation markers. These markers persist for the
    session lifetime, creating a coherent audit trail of what recovery paths
    were needed.

    Markers accumulate (never clear) so the full recovery history is visible.
    This is intentional: a session that needed fallback remains marked as
    "fallback_active" so diagnostics know the session was degraded.

    Attributes:
        is_degraded: True if any marker is set, False otherwise.
        active_markers: Set of currently active DegradedMarker values.
        marker_timestamps: Dict mapping marker to when it was first set.
        marked_at: When the session first entered degraded mode (set when first marker added).
    """

    is_degraded: bool = False
    """True if session is degraded (any marker active)."""

    active_markers: set[DegradedMarker] = Field(default_factory=set)
    """Markers that have been set."""

    marker_timestamps: dict[DegradedMarker, datetime] = Field(default_factory=dict)
    """When each marker was set."""

    marked_at: datetime | None = None
    """When session first entered degraded mode."""

    def set_marker(self, marker: DegradedMarker) -> None:
        """Set a degradation marker.

        Markers accumulate and persist. Once set, a marker stays set for the
        session lifetime (intentional for audit trail).

        Args:
            marker: The DegradedMarker to set
        """
        if marker not in self.active_markers:
            self.active_markers.add(marker)
            self.marker_timestamps[marker] = datetime.now(timezone.utc)

            # Mark overall degraded on first marker
            if self.marked_at is None:
                self.marked_at = datetime.now(timezone.utc)

            self.is_degraded = True

    def has_marker(self, marker: DegradedMarker) -> bool:
        """Check if a marker is set.

        Args:
            marker: The DegradedMarker to check

        Returns:
            True if marker is set, False otherwise
        """
        return marker in self.active_markers

    def get_recovery_history(self) -> list[tuple[DegradedMarker, datetime]]:
        """Get recovery history in chronological order.

        Returns:
            List of (marker, timestamp) tuples sorted by timestamp
        """
        items = [
            (marker, self.marker_timestamps[marker])
            for marker in self.active_markers
        ]
        return sorted(items, key=lambda x: x[1])


class SessionContextLayers(BaseModel):
    """W2.3 memory and context layers for a session.

    Contains the bounded context layers that enable longer-session coherence:
    - short_term_context: Most recent turn's context (W2.3.1)
    - session_history: Bounded history of turns (W2.3.2)
    - progression_summary: Compressed session progression (W2.3.3)
    - relationship_axis_context: Salient relationship dynamics (W2.3.4)
    - lore_direction_context: Selective module guidance injection (W2.3.5)
    - narrative_threads: Task 1D derived persistent consequence threads (working snapshot)

    All layers are optional (None) until explicitly derived/accumulated.
    This wrapper keeps W2.3 layers grouped and distinct from core session state.

    Attributes:
        short_term_context: Current turn context snapshot (from W2.3.1).
        session_history: Accumulated bounded history (from W2.3.2).
        progression_summary: Compressed progression state (from W2.3.3).
        relationship_axis_context: Relationship dynamics snapshot (from W2.3.4).
        lore_direction_context: Selected module guidance (from W2.3.5).
        narrative_threads: Task 1D bounded thread snapshot; mirrored in session.metadata.
    """

    short_term_context: Optional[Any] = None  # ShortTermTurnContext when populated
    session_history: Optional[Any] = None  # SessionHistory when populated
    progression_summary: Optional[Any] = None  # ProgressionSummary when populated
    relationship_axis_context: Optional[Any] = None  # RelationshipAxisContext when populated
    lore_direction_context: Optional[Any] = None  # LoreDirectionContext when populated
    narrative_threads: Optional[Any] = None  # NarrativeThreadSet when populated (Task 1D)

    # W3 Diagnostic Persistence
    last_turn_execution_result: Optional[dict[str, Any]] = None  # Full TurnExecutionResult for UI
    last_ai_decision_log: Optional[dict[str, Any]] = None  # Full AIDecisionLog for diagnostics
    last_turn_number: int = 0  # Track which turn these diagnostics are from


class SessionState(BaseModel):
    """Represents the state of an active story session.

    Captures the session identity, module reference, current scene,
    overall status, and the canonical state snapshot. Serves as the
    container for a complete story loop session.

    Includes W2.3 memory/context layers for longer-session coherence.

    Attributes:
        session_id: Unique identifier for this session (uuid4).
        module_id: The content module ID (e.g., "god_of_carnage").
        module_version: Version of the module being played.
        current_scene_id: Current active scene/phase identifier.
        status: Session status (active, paused, ended, crashed).
        turn_counter: Number of turns executed in this session.
        canonical_state: Current world state snapshot (dict).
        execution_mode: Turn execution mode ("mock" or "ai"). Default "mock".
        adapter_name: Name of the AI adapter to use when execution_mode="ai". Default "mock".
        seed: Optional seed for reproducibility.
        created_at: Timestamp when session was created.
        updated_at: Timestamp when session was last updated.
        metadata: Extensible metadata dict.
        context_layers: W2.3 memory and context layers (W2.3.1-W2.3.5).
    """

    session_id: str = Field(default_factory=lambda: uuid4().hex)
    module_id: str
    module_version: str
    current_scene_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    turn_counter: int = 0
    canonical_state: dict[str, Any] = Field(default_factory=dict)
    execution_mode: str = "mock"  # "mock" or "ai"
    adapter_name: str = "mock"  # Name of the AI adapter (e.g., "mock", "claude_story", etc.)
    seed: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)
    context_layers: SessionContextLayers = Field(default_factory=SessionContextLayers)
    degraded_state: DegradedSessionState = Field(default_factory=DegradedSessionState)
    """W2.5.7 degraded session tracking."""


# ===== Turn Models =====


class TurnStatus(str, Enum):
    """Status of a story turn."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TurnState(BaseModel):
    """Represents the state of a single story turn.

    Captures input, execution status, pre- and post-snapshots,
    and diagnostic timing information.

    Attributes:
        turn_number: Monotonically increasing turn counter.
        session_id: Parent session identifier.
        input_payload: Operator input for this turn.
        pre_turn_snapshot: World state before turn execution.
        post_turn_result: World state after turn execution.
        status: Turn execution status.
        started_at: Timestamp when turn started.
        completed_at: Timestamp when turn completed.
        duration_ms: Turn execution time in milliseconds.
    """

    turn_number: int
    session_id: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    pre_turn_snapshot: dict[str, Any] | None = None
    post_turn_result: dict[str, Any] | None = None
    status: TurnStatus = TurnStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None


# ===== Event Log Models =====


class EventLogEntry(BaseModel):
    """An immutable event record in the story session.

    Captures what happened, when it happened, and structured data.
    Used for audit trails, logging, and recovery.

    Attributes:
        id: Unique identifier for this event (uuid4).
        event_type: Type of event (e.g., "session_started", "turn_completed").
        occurred_at: Timestamp when event occurred.
        order_index: Monotonic counter within the session.
        summary: Human/audit-readable event summary.
        payload: Structured event data.
        session_id: Parent session identifier.
        turn_number: Turn number (None for session-level events).
    """

    id: str = Field(default_factory=lambda: uuid4().hex)
    event_type: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    order_index: int
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    session_id: str
    turn_number: int | None = None


# ===== State Delta Models =====


class DeltaType(str, Enum):
    """Type of state change."""

    CHARACTER_STATE = "character_state"
    RELATIONSHIP = "relationship"
    SCENE = "scene"
    TRIGGER = "trigger"
    METADATA = "metadata"


class DeltaValidationStatus(str, Enum):
    """Validation status of a delta."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"


class StateDelta(BaseModel):
    """An atomic world state change.

    Represents a single change to the world state, with source attribution,
    validation lifecycle, and before/after values.

    Attributes:
        id: Unique identifier for this delta (uuid4).
        delta_type: Type of change (character_state, relationship, etc.).
        target_path: Dot-path to affected entity (e.g., "characters.veronique.emotional_state").
        target_entity: Entity identifier (e.g., "veronique").
        previous_value: Value before change (None if not applicable).
        next_value: Value after change (None if not applicable).
        source: Source of change ("ai_proposal", "operator", "engine").
        validation_status: Lifecycle status (pending, accepted, rejected, modified).
        turn_number: Turn number when delta was proposed.
    """

    id: str = Field(default_factory=lambda: uuid4().hex)
    delta_type: DeltaType
    target_path: str
    target_entity: str | None = None
    previous_value: Any = None
    next_value: Any = None
    source: str
    validation_status: DeltaValidationStatus = DeltaValidationStatus.PENDING
    turn_number: int | None = None


# ===== Proposal Source Models =====


class ProposalSource(str, Enum):
    """Source origin of a proposal entering the execution path.

    Default is MOCK (non-authoritative). Only RESPONDER_DERIVED proposals
    are authorized to enter the canonical guarded execution path.
    """

    RESPONDER_DERIVED = "responder_derived"
    """Proposal came from responder section of parsed AI role contract.

    Only this source is authorized for canonical execution path.
    """

    MOCK = "mock"
    """Proposal came from mock_decision_provider (test/debug only).

    Conservative default. Requires explicit override for responder authorization.
    """

    ENGINE = "engine"
    """Reserved: Proposal from world engine (not yet integrated)."""

    OPERATOR = "operator"
    """Reserved: Proposal from human operator (not yet integrated)."""


class ProposedStateDelta(BaseModel):
    """A proposed state change from a mock decision.

    Attributes:
        target: Dot-path to affected entity (e.g., "characters.veronique.emotional_state").
        next_value: Value to apply (None if not applicable).
        previous_value: Current value before change (populated during construction).
        delta_type: Type of change (character_state, relationship, etc.).
        source: Source of change attribution (e.g., "ai_proposal").
    """

    target: str
    next_value: Any = None
    previous_value: Any = None
    delta_type: DeltaType | None = None
    source: str = ""


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
        proposal_source: Origin of proposals (responder_derived, mock, engine, operator).
                        Defaults to MOCK (non-authoritative) for safety.
    """

    detected_triggers: list[str] = Field(default_factory=list)
    proposed_deltas: list[ProposedStateDelta] = Field(default_factory=list)
    proposed_scene_id: str | None = None
    narrative_text: str = ""
    rationale: str = ""

    proposal_source: ProposalSource = ProposalSource.MOCK
    """Source of proposals in proposed_deltas.

    Default MOCK requires explicit override to RESPONDER_DERIVED.
    Only RESPONDER_DERIVED proposals are authorized for canonical execution.
    """


class NarrativeCommitRecord(BaseModel):
    """Bounded authoritative summary of what the in-process runtime committed for one turn.

    This is the canonical post-execution narrative outcome for the backend ``SessionState``
    loop (simulation, tests, in-process AI path). It is not a claim of live production
    authority over World Engine execution.

    Separates committed narrative truth from diagnostics (raw AI output, parse traces,
    input interpretation envelopes, rejected proposals).
    """

    turn_number: int
    prior_scene_id: str | None
    committed_scene_id: str
    situation_status: Literal["continue", "transitioned", "ending_reached"]
    committed_ending_id: str | None = None
    accepted_delta_targets: list[str] = Field(default_factory=list)
    rejected_delta_targets: list[str] = Field(default_factory=list)
    committed_trigger_ids: list[str] = Field(default_factory=list)
    guard_outcome: str
    authoritative_reason: str
    canonical_consequences: list[str] = Field(default_factory=list)
    is_terminal: bool = False


# ===== AI Decision Log Models =====


class ExecutionFailureReason(str, Enum):
    """Explicit classification of AI execution failures for diagnostics.

    Allows runtime to distinguish between generation, parsing, validation,
    and non-committed failures for proper error handling and recovery.
    """

    NONE = "none"  # No failure
    GENERATION_ERROR = "generation_error"  # Adapter failed to generate
    PARSING_ERROR = "parsing_error"  # Could not parse output
    VALIDATION_ERROR = "validation_error"  # Runtime validation rejected changes


class GuardOutcome(str, Enum):
    """Canonical guard outcome classification for a turn's proposed deltas.

    Represents the guard's final decision on a set of proposed deltas,
    providing clear semantics for full acceptance, partial acceptance,
    full rejection, and structural invalidity.

    Values:
        ACCEPTED: All proposed deltas passed validation and were applied.
        PARTIALLY_ACCEPTED: Some deltas accepted, some rejected by the guard.
        REJECTED: All proposed deltas rejected; nothing applied.
        STRUCTURALLY_INVALID: No deltas proposed (empty decision) or system error.
    """

    ACCEPTED = "accepted"
    PARTIALLY_ACCEPTED = "partially_accepted"
    REJECTED = "rejected"
    STRUCTURALLY_INVALID = "structurally_invalid"


class AIDecisionAction(BaseModel):
    """An AI decision action with explicit type and validation context.

    Wraps a decision proposal with an explicit action type from the canonical taxonomy.

    Attributes:
        action_type: The explicit action type from AIActionType
        target_path: Target for state/relationship updates (required for STATE_UPDATE, RELATIONSHIP_SHIFT)
        next_value: Proposed value (required for STATE_UPDATE, RELATIONSHIP_SHIFT)
        scene_id: Scene ID for transitions (required for SCENE_TRANSITION)
        trigger_ids: Trigger IDs for assertions (required for TRIGGER_ASSERTION)
        character_id: Character ID for impulses (required for DIALOGUE_IMPULSE)
        impulse_text: Impulse text (required for DIALOGUE_IMPULSE)
        intensity: 0.0-1.0 intensity/confidence
        rationale: Reasoning for this action
    """

    action_type: str  # Must be a valid AIActionType value
    target_path: str | None = None
    next_value: Any = None
    scene_id: str | None = None
    trigger_ids: list[str] | None = None
    character_id: str | None = None
    impulse_text: str | None = None
    intensity: float | None = None
    rationale: str = ""


class AIValidationOutcome(str, Enum):
    """Outcome of AI decision validation."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PARTIAL = "partial"
    ERROR = "error"


class InterpreterDiagnosticSummary(BaseModel):
    """Diagnostic summary of scene interpretation (non-executable).

    Preserves the scene reading and identified tensions for diagnostics.
    Does not feed runtime execution.
    """

    scene_reading: str
    """Narrative description of what the interpreter observed in the scene."""

    detected_tensions: list[str]
    """Interpersonal/situational tensions identified by the interpreter."""


class DirectorDiagnosticSummary(BaseModel):
    """Diagnostic summary of conflict steering (non-executable).

    Preserves the steering rationale and recommended direction for diagnostics.
    Does not feed runtime execution.
    """

    conflict_steering: str
    """Narrative rationale for the chosen conflict direction."""

    recommended_direction: Literal["escalate", "stabilize", "shift_alliance", "redirect", "hold"]
    """Enum: type of narrative movement (bounded set)."""


class SupervisorPlan(BaseModel):
    """Deterministic supervisor planning contract."""

    selected_agents: list[str] = Field(default_factory=list)
    execution_order: list[str] = Field(default_factory=list)
    selection_reason: str = ""
    required_agents: list[str] = Field(default_factory=list)
    optional_agents: list[str] = Field(default_factory=list)
    finalize_strategy: str = "finalizer_subagent"
    merge_strategy: str = "deterministic"
    operator_input_summary: str | None = None


class TokenUsageRecord(BaseModel):
    """Canonical token usage contract for one adapter invocation."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int = 0
    provider_name: str | None = None
    model_name: str | None = None
    usage_mode: Literal["exact", "proxy"] = "proxy"
    raw_usage: dict[str, Any] | None = None


class AgentInvocationRecord(BaseModel):
    """Trace record for a bounded subagent invocation."""

    agent_id: str
    role: str
    invocation_sequence: int
    input_summary: str | None = None
    tool_policy_snapshot: dict[str, Any] = Field(default_factory=dict)
    model_profile: str = "default"
    adapter_name: str = "unknown"
    execution_status: Literal["success", "error", "skipped"] = "success"
    duration_ms: int = 0
    retry_count: int = 0
    budget_snapshot: dict[str, Any] = Field(default_factory=dict)
    budget_consumed: dict[str, Any] = Field(default_factory=dict)
    token_usage: TokenUsageRecord | None = None
    failover_reason: str | None = None
    error_summary: str | None = None
    tool_call_transcript: list[dict[str, Any]] = Field(default_factory=list)
    policy_violations: list[str] = Field(default_factory=list)


class AgentResultRecord(BaseModel):
    """Structured output record from one subagent."""

    agent_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    confidence: str | None = None
    bounded_summary: str = ""
    result_shape: str = "structured_payload"


class MergeFinalizationRecord(BaseModel):
    """Trace for merge and finalization decisions."""

    used_agent_outputs: list[str] = Field(default_factory=list)
    ignored_agent_outputs: list[str] = Field(default_factory=list)
    downgraded_agent_outputs: list[str] = Field(default_factory=list)
    conflict_notes: list[str] = Field(default_factory=list)
    selection_reason: str = ""
    final_output_source: str = ""
    finalizer_agent_id: str | None = None
    finalizer_status: Literal["success", "fallback"] = "success"
    fallback_used: bool = False
    fallback_reason: str | None = None
    policy_violations: list[str] = Field(default_factory=list)


class AIDecisionLog(BaseModel):
    """Record of AI decision for a turn.

    Captures the AI's raw output, parsed interpretation, validation outcome,
    and decisions about which proposed changes to accept or reject.

    Attributes:
        id: Unique identifier for this decision log (uuid4).
        session_id: Parent session identifier.
        turn_number: Turn number for this decision.
        raw_output: Verbatim AI-generated text.
        parsed_output: Structured parsed representation.
        validation_outcome: Overall validation result.
        accepted_deltas: List of deltas that passed validation.
        rejected_deltas: List of deltas that failed validation.
        guard_notes: Reason for guard intervention if applicable.
        recovery_notes: Recovery action taken if applicable.
        created_at: Timestamp when decision was made.
    """

    id: str = Field(default_factory=lambda: uuid4().hex)
    session_id: str
    turn_number: int
    raw_output: str | None = None
    parsed_output: dict[str, Any] | None = None
    validation_outcome: AIValidationOutcome = AIValidationOutcome.ACCEPTED
    accepted_deltas: list[StateDelta] = Field(default_factory=list)
    rejected_deltas: list[StateDelta] = Field(default_factory=list)
    guard_notes: str | None = None
    recovery_notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # W2.4.4 role diagnostic fields (optional for backward compatibility)
    interpreter_output: InterpreterDiagnosticSummary | None = None
    """Diagnostic summary from interpreter role: scene reading and detected tensions."""

    director_output: DirectorDiagnosticSummary | None = None
    """Diagnostic summary from director role: conflict steering and recommended direction."""

    responder_output: ResponderSection | None = None
    """Runtime-relevant proposals from responder role (feeds normalization)."""

    guard_outcome: GuardOutcome
    """Canonical validation result for responder proposals (guard decision)."""

    # B2 Tool Loop diagnostics (optional, backward-compatible)
    tool_loop_summary: dict[str, Any] | None = None
    tool_call_transcript: list[dict[str, Any]] | None = None
    tool_influence: dict[str, Any] | None = None

    # B3 Preview-write diagnostics (optional, backward-compatible)
    preview_diagnostics: dict[str, Any] | None = None

    # C1 Supervisor diagnostics (optional, backward-compatible)
    supervisor_plan: SupervisorPlan | None = None
    subagent_invocations: list[AgentInvocationRecord] | None = None
    subagent_results: list[AgentResultRecord] | None = None
    merge_finalization: MergeFinalizationRecord | None = None
    orchestration_budget_summary: dict[str, Any] | None = None
    orchestration_failover: list[dict[str, Any]] | None = None
    orchestration_cache: dict[str, Any] | None = None
    tool_audit: list[dict[str, Any]] | None = None

    # Task 2B: cross-model routing evidence (Task 2A route_model); not full observability closure
    model_routing_trace: dict[str, Any] | None = None

    # Task 1: multi-stage Runtime orchestration (additive diagnostics; not authoritative)
    runtime_stage_traces: list[dict[str, Any]] | None = None
    runtime_orchestration_summary: dict[str, Any] | None = None

    # Task 3: operator audit layer (derived-only; does not replace routing_evidence / diagnostics_*)
    operator_audit: dict[str, Any] | None = None


__all__ = [
    "AIDecisionAction",
    "AIDecisionLog",
    "AIValidationOutcome",
    "AgentInvocationRecord",
    "AgentResultRecord",
    "DegradedMarker",
    "DegradedSessionState",
    "DeltaType",
    "DeltaValidationStatus",
    "DirectorDiagnosticSummary",
    "EventLogEntry",
    "ExecutionFailureReason",
    "GuardOutcome",
    "InterpreterDiagnosticSummary",
    "MergeFinalizationRecord",
    "MockDecision",
    "NarrativeCommitRecord",
    "ProposalSource",
    "ProposedStateDelta",
    "SessionContextLayers",
    "SessionState",
    "SessionStatus",
    "StateDelta",
    "SupervisorPlan",
    "TokenUsageRecord",
    "TurnState",
    "TurnStatus",
]
