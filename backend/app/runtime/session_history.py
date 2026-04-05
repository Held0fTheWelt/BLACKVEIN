"""W2.3.2 — Canonical session-history layer for longer-running story sessions.

Maintains a bounded ordered sequence of historical context entries, distinct from
both raw event logs and future compressed summaries. Provides longitudinal information
for session continuity without uncontrolled accumulation.

SessionHistory tracks progression markers (scene transitions, endings) and turn
ordering while remaining compact and deterministic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from app.runtime.short_term_context import ShortTermTurnContext

# Task 1C: tighter caps for long-lived history rows (JSON-safe, compact).
_MAX_HISTORY_CONSEQUENCES = 16
_MAX_HISTORY_REASON_LEN = 200


def _cap_history_reason(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if len(s) <= _MAX_HISTORY_REASON_LEN:
        return s
    return s[: _MAX_HISTORY_REASON_LEN - 1] + "…"


class HistoryEntry(BaseModel):
    """A single bounded historical record from a completed turn.

    Derived from ShortTermTurnContext but may be enriched with metadata
    useful for longitudinal tracking. Each entry captures the essential
    facts about what happened in that turn.

    Attributes:
        turn_number: The turn this entry originated from.
        scene_id: Scene after the turn completed.
        guard_outcome: Classification of turn's guard result.
        detected_triggers: Triggers that fired this turn.
        scene_changed: Whether a scene transition occurred.
        prior_scene_id: Scene before transition (if changed).
        ending_reached: Whether an ending was triggered.
        ending_id: The ending ID if reached.
        created_at: When this history entry was recorded.
        situation_status: Narrative situation label when recorded (Task 1C).
        canonical_consequences: Bounded consequence tokens carried from short-term context.
        authoritative_reason: Truncated authoritative reason for continuity.
        is_terminal: Whether the turn committed a terminal ending.
        active_thread_ids: Task 1D thread id markers (compact).
        dominant_thread_kind: Task 1D dominant thread kind.
        thread_pressure_level: Task 1D max thread intensity snapshot.
    """

    turn_number: int
    scene_id: str
    guard_outcome: str  # ACCEPTED, PARTIALLY_ACCEPTED, REJECTED, STRUCTURALLY_INVALID
    detected_triggers: list[str] = Field(default_factory=list)
    scene_changed: bool = False
    prior_scene_id: Optional[str] = None
    ending_reached: bool = False
    ending_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    situation_status: str = ""
    canonical_consequences: list[str] = Field(default_factory=list)
    authoritative_reason: Optional[str] = None
    is_terminal: bool = False

    active_thread_ids: list[str] = Field(default_factory=list)
    dominant_thread_kind: str = ""
    thread_pressure_level: int = 0

    @classmethod
    def from_short_term_context(cls, context: ShortTermTurnContext) -> HistoryEntry:
        """Create a history entry from a short-term turn context.

        Extracts the most relevant information for long-term session tracking.
        """
        consequences = list(context.canonical_consequences or [])[:_MAX_HISTORY_CONSEQUENCES]
        return cls(
            turn_number=context.turn_number,
            scene_id=context.scene_id,
            guard_outcome=context.guard_outcome,
            detected_triggers=context.detected_triggers,
            scene_changed=context.scene_changed,
            prior_scene_id=context.prior_scene_id,
            ending_reached=context.ending_reached,
            ending_id=context.ending_id,
            situation_status=context.situation_status or "",
            canonical_consequences=consequences,
            authoritative_reason=_cap_history_reason(context.authoritative_reason),
            is_terminal=context.is_terminal,
            active_thread_ids=list(context.active_thread_ids or []),
            dominant_thread_kind=context.dominant_thread_kind or "",
            thread_pressure_level=int(context.thread_pressure_level or 0),
        )


class SessionHistory(BaseModel):
    """A bounded, ordered sequence of historical context entries for a session.

    Maintains longitudinal information across multiple turns while staying
    compact and deterministic. Distinct from raw event logs and single-turn
    context. Serves as input for later summarization and relationship tracking.

    Attributes:
        entries: Ordered list of historical entries (oldest to newest).
        max_size: Maximum number of entries to retain (default 100).
    """

    entries: list[HistoryEntry] = Field(default_factory=list)
    max_size: int = 100

    def add_entry(self, entry: HistoryEntry) -> None:
        """Add a new history entry, trimming oldest if needed.

        Maintains FIFO ordering. Automatically removes oldest entries
        when max_size is exceeded.

        Args:
            entry: The HistoryEntry to append.
        """
        self.entries.append(entry)

        # Trim oldest entries if we exceed max_size
        if len(self.entries) > self.max_size:
            self.entries = self.entries[-self.max_size :]

    def add_from_short_term_context(self, context: ShortTermTurnContext) -> None:
        """Convenience method to add an entry directly from short-term context.

        Args:
            context: A ShortTermTurnContext to add to history.
        """
        entry = HistoryEntry.from_short_term_context(context)
        self.add_entry(entry)

    def get_recent_entries(self, count: int) -> list[HistoryEntry]:
        """Get the N most recent history entries.

        Args:
            count: Number of recent entries to retrieve.

        Returns:
            List of most recent entries (newest last), up to `count` items.
        """
        return self.entries[-count:] if self.entries else []

    def get_entries_since_turn(self, turn_number: int) -> list[HistoryEntry]:
        """Get all entries from a specific turn number onwards.

        Args:
            turn_number: The starting turn number (inclusive).

        Returns:
            List of entries from turn_number onwards (oldest to newest).
        """
        return [e for e in self.entries if e.turn_number >= turn_number]

    def get_scene_transitions(self) -> list[HistoryEntry]:
        """Get all entries where scene changed.

        Returns:
            List of entries with scene_changed=True (oldest to newest).
        """
        return [e for e in self.entries if e.scene_changed]

    def get_endings_reached(self) -> list[HistoryEntry]:
        """Get all entries where an ending was triggered.

        Returns:
            List of entries with ending_reached=True (oldest to newest).
        """
        return [e for e in self.entries if e.ending_reached]

    @property
    def last_entry(self) -> Optional[HistoryEntry]:
        """Get the most recent entry, or None if history is empty."""
        return self.entries[-1] if self.entries else None

    @property
    def size(self) -> int:
        """Current number of entries in the history."""
        return len(self.entries)

    @property
    def is_full(self) -> bool:
        """Whether history has reached max capacity."""
        return len(self.entries) >= self.max_size

    def clear(self) -> None:
        """Clear all entries from the history."""
        self.entries.clear()
