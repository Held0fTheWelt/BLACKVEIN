"""W3.3 In-Memory Session Store

Provides the canonical in-memory registry for RuntimeSession objects.
Sessions are keyed by session_id and lost on server restart (intentional MVP scope).

This is the ONLY server-side runtime session registry for W3.3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.content.module_models import ContentModule
    from app.runtime.runtime_models import SessionState


# Module-level in-memory registry
_runtime_sessions: dict[str, RuntimeSession] = {}


@dataclass
class RuntimeSession:
    """In-memory wrapper for a runtime session.

    Attributes:
        session_id: Unique session identifier
        current_runtime_state: Full SessionState from W2 (canonical)
        module: Loaded ContentModule (required for dispatch_turn)
        turn_counter: Current turn number (incremented after each execution)
        updated_at: Timestamp of last update
    """

    session_id: str
    current_runtime_state: SessionState
    module: ContentModule
    turn_counter: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


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
    _runtime_sessions[session_id] = runtime_session
    return runtime_session


def get_session(session_id: str) -> RuntimeSession | None:
    """Retrieve a runtime session by session_id.

    Args:
        session_id: Unique session identifier

    Returns:
        RuntimeSession if found, None otherwise
    """
    return _runtime_sessions.get(session_id)


def update_session(session_id: str, updated_state: SessionState) -> RuntimeSession | None:
    """Update a session's canonical state.

    Replaces current_runtime_state with new state, updates timestamp.

    Args:
        session_id: Unique session identifier
        updated_state: New SessionState from turn execution

    Returns:
        Updated RuntimeSession if found, None otherwise
    """
    session = _runtime_sessions.get(session_id)
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
    if session_id in _runtime_sessions:
        del _runtime_sessions[session_id]
        return True
    return False


def clear_registry() -> None:
    """Clear all sessions from the registry. Used for testing."""
    global _runtime_sessions
    _runtime_sessions = {}
