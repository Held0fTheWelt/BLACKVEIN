"""W2.0.4 — RuntimeEventLog: monotonic event logging helper for the story runtime.

Provides in-memory event accumulation with automatic order_index assignment and
session/turn context injection. No persistence, no side effects, no threading.
"""

from __future__ import annotations

from app.runtime.runtime_models import EventLogEntry


class RuntimeEventLog:
    """Stateful event log accumulator with monotonic order_index assignment.

    Intended to be constructed once per operation (session-start or turn execution),
    populated via .log(), then drained via .flush() into the result object.

    Attributes:
        _session_id: Session identifier injected into every event.
        _turn_number: Optional turn number injected into every event.
        _counter: Monotonic order_index counter, starts at 0.
        _entries: Accumulated EventLogEntry list in call order.
    """

    def __init__(self, session_id: str, turn_number: int | None = None) -> None:
        """Initialize a new event log for a session or turn operation.

        Args:
            session_id: Session identifier to inject into every event.
            turn_number: Optional turn number to inject. None for session-level operations.
        """
        self._session_id = session_id
        self._turn_number = turn_number
        self._counter: int = 0
        self._entries: list[EventLogEntry] = []

    def log(self, event_type: str, summary: str, payload: dict | None = None) -> EventLogEntry:
        """Create and accumulate an EventLogEntry with auto-assigned order_index.

        Args:
            event_type: Canonical event type string (e.g., 'turn_started', 'decision_validated').
            summary: Human-readable one-line summary of the event.
            payload: Optional structured payload dict. Defaults to empty dict if None.

        Returns:
            The created EventLogEntry for testing/inspection convenience.
        """
        entry = EventLogEntry(
            event_type=event_type,
            order_index=self._counter,
            summary=summary,
            payload=payload or {},
            session_id=self._session_id,
            turn_number=self._turn_number,
        )
        self._entries.append(entry)
        self._counter += 1
        return entry

    def flush(self) -> list[EventLogEntry]:
        """Return all accumulated entries and reset the log.

        After flush, the log is ready to accumulate a new sequence of events.

        Returns:
            List of EventLogEntry in call order (order_index 0..N-1).
        """
        entries = list(self._entries)
        self._entries = []
        self._counter = 0
        return entries

    @property
    def count(self) -> int:
        """Number of events currently accumulated (before flush)."""
        return len(self._entries)
