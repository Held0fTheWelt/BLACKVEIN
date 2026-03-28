"""W2.0.1 — Canonical story runtime models.

Establishes the foundational data structures for the story loop:
- SessionState: session identity, module reference, current scene, status
- TurnState: turn metadata, input/output snapshots, execution status
- EventLogEntry: immutable event record with audit trail
- StateDelta: atomic world state change with validation lifecycle
- AIDecisionLog: AI proposal record with acceptance/rejection tracking

These models are append-only and designed for reproducibility and logging.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ===== Session Models =====


class SessionStatus(str, Enum):
    """Status of a story session."""

    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    CRASHED = "crashed"


class SessionState(BaseModel):
    """Represents the state of an active story session.

    Captures the session identity, module reference, current scene,
    overall status, and the canonical state snapshot. Serves as the
    container for a complete story loop session.

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


class AIValidationOutcome(str, Enum):
    """Outcome of AI decision validation."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PARTIAL = "partial"
    ERROR = "error"


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
