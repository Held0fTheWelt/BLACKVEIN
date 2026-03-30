"""W3.1 — Session service layer for API exposure.

Provides the canonical service-level interface between API routes and W2 runtime:
- create_session: Start a new session from a module
- get_session: Retrieve active session state
- execute_turn: Execute a turn in an active session
- get_session_logs: Retrieve session event logs
- get_session_state: Get canonical world state
"""

from app.runtime.session_start import start_session
from app.runtime.w2_models import SessionState
from app.content.module_loader import load_module


def create_session(module_id: str) -> SessionState:
    """Start a new story session from a content module.

    Calls the W2 runtime session start workflow directly:
    1. Loads and validates the target module
    2. Determines the initial scene (data-driven)
    3. Constructs initial SessionState with seeded canonical state
    4. Registers session in the runtime session store
    5. Returns the SessionState

    Args:
        module_id: Identifier of the module (e.g., "god_of_carnage")

    Returns:
        SessionState for the newly created session

    Raises:
        SessionStartError: If module loading fails or module is invalid
    """
    result = start_session(module_id)
    session_state = result.session

    # Register session in the runtime session store
    from app.runtime.session_store import create_session as register_session
    module = load_module(module_id)
    register_session(session_state.session_id, session_state, module)

    return session_state


def get_session(session_id: str) -> SessionState:
    """Retrieve an active session by session_id.

    W3.2 Deferral: Requires persistence layer.

    Raises:
        NotImplementedError: Requires W3.2 persistence layer
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
    """Get canonical world state for a session.

    W3.2 Deferral: Requires persistence layer for state retrieval.

    Args:
        session_id: Session identifier

    Returns:
        Canonical world state dict

    Raises:
        NotImplementedError: Requires W3.2 persistence layer
    """
    raise NotImplementedError("get_session_state requires W3.2 state persistence")
