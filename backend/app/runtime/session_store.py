"""DEPRECATED (transitional): volatile in-memory registry for W2 ``RuntimeSession`` wrappers.

Maps ``session_id`` → in-process ``SessionState`` for operator/MCP routes and tests.
**Not** authoritative for live play (World Engine owns runs). **Not** a durable or
global registry — data is lost on restart. Rationale: bridge until engine-only
execution and persistence subsume these endpoints.

**Threading/async:** The registry is a plain dict on a process-local singleton; no
locks. Only use from the same event loop / request worker as other Flask/async
session routes; not safe for concurrent mutation across threads without external
synchronization.

All session entries are accessed through ``RuntimeSessionRegistry``; do not bypass
the registry with a raw module-level dict.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType

from app.content.module_models import ContentModule
from app.runtime.runtime_models import SessionState


@dataclass
class RuntimeSession:
    """In-memory wrapper for a runtime session.

    Attributes:
        session_id: Unique session identifier
        current_runtime_state: Full in-process ``SessionState`` (not live-engine authority)
        module: Loaded ContentModule (required for dispatch_turn)
        turn_counter: Current turn number (incremented after each execution)
        updated_at: Timestamp of last update
    """

    session_id: str
    current_runtime_state: SessionState
    module: ContentModule
    turn_counter: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RuntimeSessionRegistry:
    """Process-local in-memory store for :class:`RuntimeSession` records."""

    __slots__ = ("_sessions",)

    def __init__(self) -> None:
        self._sessions: dict[str, RuntimeSession] = {}

    def get(self, session_id: str) -> RuntimeSession | None:
        return self._sessions.get(session_id)

    def put(self, session_id: str, session: RuntimeSession) -> None:
        """Register ``session`` under ``session_id``. Raises if ``session_id`` already exists."""
        if session_id in self._sessions:
            raise ValueError(f"Session '{session_id}' is already registered")
        self._sessions[session_id] = session

    def delete(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def snapshot_readonly(self) -> Mapping[str, RuntimeSession]:
        """Shallow copy of id → session as a read-only mapping (keys fixed at call time)."""
        return MappingProxyType(dict(self._sessions))

    def clear(self) -> None:
        """Drop all entries (primarily for tests)."""
        self._sessions = {}


# Process-local singleton used by facade functions below.
_runtime_registry = RuntimeSessionRegistry()


def get_runtime_session_registry() -> RuntimeSessionRegistry:
    """Return the process-local session registry (for diagnostics or advanced callers)."""
    return _runtime_registry


def create_session(session_id: str, initial_state: SessionState, module: ContentModule) -> RuntimeSession:
    """Create and register a new runtime session.

    Args:
        session_id: Unique session identifier
        initial_state: Initial SessionState from W2
        module: Loaded ContentModule

    Returns:
        RuntimeSession registered in the in-memory store
    """
    runtime_session = RuntimeSession(
        session_id=session_id,
        current_runtime_state=initial_state,
        module=module,
        turn_counter=0,
    )
    _runtime_registry.put(session_id, runtime_session)
    return runtime_session


def get_session(session_id: str) -> RuntimeSession | None:
    """Retrieve a runtime session by session_id.

    Args:
        session_id: Unique session identifier

    Returns:
        RuntimeSession if found, None otherwise
    """
    return _runtime_registry.get(session_id)


def update_session(session_id: str, updated_state: SessionState) -> RuntimeSession | None:
    """Replace ``current_runtime_state`` after an in-process turn (volatile store).

    Replaces ``current_runtime_state`` with new state, updates timestamp.

    Args:
        session_id: Unique session identifier
        updated_state: New SessionState from turn execution

    Returns:
        Updated RuntimeSession if found, None otherwise
    """
    session = _runtime_registry.get(session_id)
    if not session:
        return None

    session.current_runtime_state = updated_state
    session.updated_at = datetime.now(timezone.utc)
    return session


def delete_session(session_id: str) -> bool:
    """Delete a session from the registry.

    Args:
        session_id: Unique session identifier

    Returns:
        True if session was deleted, False if not found
    """
    return _runtime_registry.delete(session_id)


def clear_registry() -> None:
    """Clear all sessions from the registry. Used for testing."""
    _runtime_registry.clear()
