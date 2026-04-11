"""Data Transfer Objects for narrative commit pipeline.

Replaces dict-based passing and enables type-safe state transfers between
turn execution → narrative thread derivation → commit application.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass(frozen=True)
class NarrativeCommitEvent:
    """Represents a narrative commit event from a turn execution context.

    Replaces dict unpacking in narrative_threads_update_from_commit.py
    and provides type-safe boundaries between turn_executor and narrative layer.

    Attributes:
        commit_id: Unique identifier for this commit event.
        turn_id: Turn identifier from execution context.
        narrative_id: Narrative/session identifier.
        user_id: User/player identifier.
        commit_payload: Raw commit data (unchanged for backwards compatibility).
        timestamp: When this commit event was created.
        metadata: Optional additional metadata for extensibility.
    """

    commit_id: str
    turn_id: str
    narrative_id: str
    user_id: str
    commit_payload: Dict[str, Any]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate commit event invariants."""
        if not self.commit_id:
            raise ValueError("commit_id is required and must be non-empty")
        if not self.turn_id:
            raise ValueError("turn_id is required and must be non-empty")
        if not self.narrative_id:
            raise ValueError("narrative_id is required and must be non-empty")
        if not self.user_id:
            raise ValueError("user_id is required and must be non-empty")
        if not isinstance(self.timestamp, datetime):
            raise ValueError("timestamp must be a datetime object")


@dataclass(frozen=True)
class ThreadUpdateResult:
    """Represents the result of updating a narrative thread.

    Wraps update result with metrics (escalated count, resolved count, etc.)
    and replaces dict-based return values from update_narrative_thread().

    Attributes:
        thread_id: Unique identifier for the updated thread.
        escalated_count: Number of escalated events/markers.
        resolved_count: Number of resolved events/markers.
        thread_version: Current version of the thread state.
        updated_at: Timestamp when the thread was last updated.
        metadata: Optional metadata about the update operation.
    """

    thread_id: str
    escalated_count: int
    resolved_count: int
    thread_version: int
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        """Validate result invariants."""
        if not self.thread_id:
            raise ValueError("thread_id is required and must be non-empty")
        if self.escalated_count < 0:
            raise ValueError("escalated_count must be non-negative")
        if self.resolved_count < 0:
            raise ValueError("resolved_count must be non-negative")
        if self.thread_version < 0:
            raise ValueError("thread_version must be non-negative")
        if not isinstance(self.updated_at, datetime):
            raise ValueError("updated_at must be a datetime object")


@dataclass(frozen=True)
class ThreadUpdateInput:
    """Groups 4 context inputs for thread updater.

    Consolidates the primary inputs needed for narrative thread updates,
    replacing scattered parameter passing in narrative_threads_update_from_commit.py.

    Attributes:
        history: Historical thread data (session history snapshots).
        progression: Thread progression metadata (momentum, stalled turns, etc.).
        relationship: Relationship context for characters involved.
        commit_event: Current commit event triggering the update.
    """

    history: List[Dict[str, Any]]
    progression: Dict[str, Any]
    relationship: Dict[str, Any]
    commit_event: NarrativeCommitEvent

    def __post_init__(self) -> None:
        """Validate input invariants."""
        if not isinstance(self.history, list):
            raise ValueError("history must be a list")
        if not isinstance(self.progression, dict):
            raise ValueError("progression must be a dict")
        if not isinstance(self.relationship, dict):
            raise ValueError("relationship must be a dict")
        if not isinstance(self.commit_event, NarrativeCommitEvent):
            raise ValueError("commit_event must be a NarrativeCommitEvent instance")
