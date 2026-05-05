"""Backend runtime session storage with multi-worker support.

Provides session persistence across worker processes via database + in-memory cache.
In-process sessions are stored in both places for fast local access and reliability
across Flask worker restarts in Docker deployments.

**Not** authoritative for live play (World Engine owns runs). Sessions are volatile
and used only as a bridge until engine-only execution and persistence subsume
these endpoints.

**Threading/async:** Uses database for consistency across workers; in-memory registry
is a process-local cache only. Database provides the single source of truth for
cross-worker retrieval.
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

    Stores in both in-memory registry (for fast local access) and database
    (for cross-worker access in multi-process deployments).

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

    # Also persist to database for cross-worker access
    try:
        _persist_session_to_database(runtime_session, initial_state)
    except Exception as e:
        # Log but don't fail if database persistence fails
        import sys
        print(f"[WARNING] Failed to persist session to database: {e}", file=sys.stderr)

    return runtime_session


def get_session(session_id: str) -> RuntimeSession | None:
    """Retrieve a runtime session by session_id.

    Checks in-memory registry first (fast), then falls back to database
    (for cross-worker retrieval in Docker deployments with multiple workers).

    Args:
        session_id: Unique session identifier

    Returns:
        RuntimeSession if found, None otherwise
    """
    # Fast path: check in-memory registry first
    session = _runtime_registry.get(session_id)
    if session:
        return session

    # Fallback: retrieve from database (for cross-worker access)
    try:
        session = _retrieve_session_from_database(session_id)
        if session:
            # Cache in memory for future accesses
            _runtime_registry.put(session_id, session)
            return session
    except Exception as e:
        # Log but don't fail if database retrieval fails
        import sys
        print(f"[WARNING] Failed to retrieve session from database: {e}", file=sys.stderr)

    return None


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
    """Delete a session from the registry and persistence backing store.

    Args:
        session_id: Unique session identifier

    Returns:
        True if session was deleted, False if not found
    """
    registry_deleted = _runtime_registry.delete(session_id)
    database_deleted = _delete_session_from_database(session_id)
    return registry_deleted or database_deleted


def clear_registry() -> None:
    """Clear all sessions from the registry. Used for testing."""
    _runtime_registry.clear()


def _persist_session_to_database(runtime_session: RuntimeSession, state: SessionState) -> None:
    """Persist a runtime session to the database for cross-worker access.

    Args:
        runtime_session: The RuntimeSession to persist
        state: The SessionState with canonical data
    """
    try:
        from flask import current_app
        from app.extensions import db
        import json
        import sys

        # Only persist if we have a Flask app context
        if not current_app:
            print(f"[SESSION_STORE] No Flask app context for persistence", file=sys.stderr)
            return

        # Create table if it doesn't exist (first-run initialization)
        _ensure_runtime_sessions_table_exists()

        # Use raw SQL for maximum compatibility with SQLite
        session_dict = {
            "session_id": runtime_session.session_id,
            "module_id": state.module_id,
            "module_version": state.module_version,
            "current_scene_id": state.current_scene_id,
            "status": state.status.value if hasattr(state.status, 'value') else str(state.status),
            "turn_counter": runtime_session.turn_counter,
            "canonical_state": json.dumps(state.canonical_state or {}),
            "session_metadata": json.dumps(state.metadata or {}),
        }

        # Try INSERT, fall back to UPDATE
        try:
            db.session.execute(db.text("""
                INSERT INTO runtime_sessions
                (session_id, module_id, module_version, current_scene_id, status, turn_counter, canonical_state, session_metadata, created_at, updated_at)
                VALUES (:session_id, :module_id, :module_version, :current_scene_id, :status, :turn_counter, :canonical_state, :session_metadata, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """), session_dict)
            print(f"[SESSION_STORE] Persisted session {runtime_session.session_id} (INSERT)", file=sys.stderr)
        except Exception as e:
            # Session already exists, update it
            print(f"[SESSION_STORE] Session {runtime_session.session_id} exists, updating: {e}", file=sys.stderr)
            db.session.execute(db.text("""
                UPDATE runtime_sessions
                SET current_scene_id = :current_scene_id, status = :status, turn_counter = :turn_counter,
                    canonical_state = :canonical_state, session_metadata = :session_metadata, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = :session_id
            """), session_dict)

        db.session.commit()
        print(f"[SESSION_STORE] Committed session {runtime_session.session_id} to database", file=sys.stderr)
    except Exception as e:
        # Silently fail - the in-memory registry is sufficient as a fallback
        print(f"[SESSION_STORE] Failed to persist session {runtime_session.session_id}: {e}", file=sys.stderr)


def _ensure_runtime_sessions_table_exists() -> None:
    """Create runtime_sessions table if it doesn't exist."""
    try:
        from app.extensions import db

        # Try to query the table - if it fails, create it
        db.session.execute(db.text("SELECT 1 FROM runtime_sessions LIMIT 1"))
    except:
        # Table doesn't exist, create it
        try:
            db.session.execute(db.text("""
                CREATE TABLE IF NOT EXISTS runtime_sessions (
                    session_id VARCHAR(64) PRIMARY KEY,
                    module_id VARCHAR(120) NOT NULL,
                    module_version VARCHAR(32) DEFAULT '1.0.0',
                    current_scene_id VARCHAR(120) NOT NULL,
                    status VARCHAR(32) DEFAULT 'active',
                    turn_counter INTEGER DEFAULT 0,
                    canonical_state JSON,
                    session_metadata JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.commit()
        except:
            pass


def _delete_session_from_database(session_id: str) -> bool:
    """Delete a runtime session row so ``get_session`` cannot resurrect it."""
    try:
        from flask import current_app
        from app.extensions import db

        if not current_app:
            return False

        _ensure_runtime_sessions_table_exists()
        result = db.session.execute(
            db.text("DELETE FROM runtime_sessions WHERE session_id = :session_id"),
            {"session_id": session_id},
        )
        db.session.commit()
        return bool(result.rowcount)
    except Exception as e:
        import sys
        print(f"[SESSION_STORE] Failed to delete session {session_id} from database: {e}", file=sys.stderr)
        try:
            from app.extensions import db

            db.session.rollback()
        except Exception:
            pass
        return False


def _retrieve_session_from_database(session_id: str) -> RuntimeSession | None:
    """Retrieve a runtime session from the database.

    Used for cross-worker access when session is not in in-memory registry.

    Args:
        session_id: The session ID to retrieve

    Returns:
        RuntimeSession if found and can be reconstructed, None otherwise
    """
    try:
        from flask import current_app
        from app.extensions import db
        import json
        import sys

        # Only retrieve if we have a Flask app context
        if not current_app:
            print(f"[SESSION_STORE] No Flask app context for retrieval of {session_id}", file=sys.stderr)
            return None

        # Ensure table exists first
        _ensure_runtime_sessions_table_exists()

        # Query the database using raw SQL for compatibility
        row = db.session.execute(
            db.text("SELECT * FROM runtime_sessions WHERE session_id = :session_id"),
            {"session_id": session_id}
        ).fetchone()

        if not row:
            print(f"[SESSION_STORE] No row found in database for {session_id}", file=sys.stderr)
            return None

        print(f"[SESSION_STORE] Found session {session_id} in database, reconstructing...", file=sys.stderr)

        # Reconstruct SessionState from database record
        canonical_state = json.loads(row.canonical_state) if row.canonical_state else {}
        session_metadata = json.loads(row.session_metadata) if row.session_metadata else {}

        print(f"[SESSION_STORE] Creating SessionState for {session_id}", file=sys.stderr)
        session_state = SessionState(
            session_id=session_id,
            module_id=row.module_id,
            module_version=row.module_version,
            current_scene_id=row.current_scene_id,
            status=row.status,
            turn_counter=row.turn_counter,
            canonical_state=canonical_state,
            metadata=session_metadata,
        )
        print(f"[SESSION_STORE] SessionState created, loading module {row.module_id}", file=sys.stderr)

        # Reconstruct ContentModule
        from app.content.module_loader import load_module
        module = load_module(row.module_id)
        if not module:
            print(f"[SESSION_STORE] Failed to load module {row.module_id}", file=sys.stderr)
            return None

        print(f"[SESSION_STORE] Module loaded, creating RuntimeSession", file=sys.stderr)
        # Reconstruct RuntimeSession
        runtime_session = RuntimeSession(
            session_id=session_id,
            current_runtime_state=session_state,
            module=module,
            turn_counter=row.turn_counter,
        )

        print(f"[SESSION_STORE] Successfully reconstructed session {session_id}", file=sys.stderr)
        return runtime_session
    except Exception as e:
        # If database access fails, return None
        # Caller will get appropriate error response
        print(f"[SESSION_STORE] Exception during reconstruction of {session_id}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return None
