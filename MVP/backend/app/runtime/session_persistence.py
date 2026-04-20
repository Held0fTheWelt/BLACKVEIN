"""Session serialization and deserialization.

Provides JSON-compatible serialization of SessionState for disk persistence,
enabling save/load/resume workflows.
"""

from typing import Any, Dict
from app.runtime.runtime_models import SessionState, SessionStatus


def serialize_session(session: SessionState) -> Dict[str, Any]:
    """Serialize session to JSON-compatible dict.

    Args:
        session: SessionState to serialize

    Returns:
        Dict with JSON-serializable session data
    """
    return {
        "session_id": session.session_id,
        "module_id": session.module_id,
        "module_version": session.module_version,
        "current_scene_id": session.current_scene_id,
        "status": session.status.value,
        "turn_counter": session.turn_counter,
        "metadata": session.metadata if hasattr(session, 'metadata') else {},
        "canonical_state": session.canonical_state if hasattr(session, 'canonical_state') else {},
    }


def deserialize_session(data: Dict[str, Any]) -> SessionState:
    """Deserialize session from JSON dict.

    Args:
        data: JSON dict from disk or other source

    Returns:
        Reconstructed SessionState

    Raises:
        KeyError: If required fields missing from data
        ValueError: If status value not recognized
    """
    session = SessionState(
        session_id=data["session_id"],
        module_id=data["module_id"],
        module_version=data["module_version"],
        current_scene_id=data["current_scene_id"],
        status=SessionStatus(data["status"]),
        turn_counter=data["turn_counter"],
    )

    # Restore optional fields
    if "metadata" in data:
        session.metadata = data["metadata"]
    if "canonical_state" in data:
        session.canonical_state = data["canonical_state"]

    return session
