"""Pydantic types for turn execution results — acyclic leaf module for import graph hygiene.

``TurnExecutionResult`` lives here so context helpers (e.g. ``short_term_context``) do not
need to import ``turn_executor``, breaking the runtime SCC with ``turn_executor``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from app.runtime.runtime_models import (
    EventLogEntry,
    ExecutionFailureReason,
    GuardOutcome,
    MockDecision,
    NarrativeCommitRecord,
    StateDelta,
)
from app.runtime.validators import ValidationOutcome


class TurnExecutionResult(BaseModel):
    """Result of executing a complete turn.

    Captures everything that happened: validation outcome, accepted/rejected deltas,
    updated state, execution timing, and audit events.
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
