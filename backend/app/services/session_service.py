"""Session service layer for API exposure (non-authoritative in-process W2 bridge).

The Flask backend is **not** the live narrative runtime. Authoritative runs execute in
the **World Engine** play service (``game_service`` HTTP client). This module wires
content modules into an in-memory ``SessionState`` for tests, MCP/operator endpoints,
and deferred W3.2 work — see ``docs/architecture/backend_runtime_classification.md``.

Exposed operations:
- create_session: start a **local** session from a module (registers in volatile store)
- get_session / execute_turn / logs / state: still deferred (NotImplementedError)
"""

from __future__ import annotations

from app.runtime.session_start import start_session
from app.runtime.runtime_models import SessionState


def create_session(module_id: str) -> SessionState:
    """Bootstrap in-process ``SessionState`` from a content module (deprecated transitional).

    **Not** creation of a World Engine run. Steps: load module, seed initial scene/state,
    register in ``session_store`` (volatile, process-local).

    Args:
        module_id: Identifier of the module (e.g., "god_of_carnage")

    Returns:
        SessionState for the newly created in-process session

    Raises:
        SessionStartError: If module loading fails or module is invalid
    """
    result = start_session(module_id)
    session_state = result.session

    from app.runtime.session_store import create_session as register_session

    register_session(session_state.session_id, session_state, result.module)

    return session_state


def get_session(session_id: str) -> SessionState:
    """Retrieve an active session by session_id.

    W3.2 Deferral: Requires persistence layer.

    Raises:
        NotImplementedError: Requires W3.2 session persistence layer
    """
    raise NotImplementedError("get_session requires W3.2 session persistence")


def execute_turn(session_id: str, decision: dict) -> SessionState:
    """Execute a turn in an active session.

    W3.2 Deferral: Requires persistence layer and turn dispatcher integration.

    Args:
        session_id: Session identifier
        decision: Decision payload for this turn

    Raises:
        NotImplementedError: Requires W3.2 persistence and turn execution
    """
    raise NotImplementedError("execute_turn requires W3.2 turn execution and persistence")


def get_session_logs(session_id: str) -> list:
    """Retrieve event logs for a session.

    W3.2 Deferral: Requires persistence layer for log retrieval.

    Args:
        session_id: Session identifier

    Returns:
        List of event log entries

    Raises:
        NotImplementedError: Requires W3.2 persistence layer
    """
    raise NotImplementedError("get_session_logs requires W3.2 event log persistence")


def get_session_state(session_id: str) -> dict:
    """Get world state dict for a session (W2 ``canonical_state`` field shape).

    W3.2 Deferral: Requires persistence layer for state retrieval.

    Args:
        session_id: Session identifier

    Returns:
        World state dict

    Raises:
        NotImplementedError: Requires W3.2 persistence layer
    """
    raise NotImplementedError("get_session_state requires W3.2 state persistence")
