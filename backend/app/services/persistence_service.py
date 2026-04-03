"""Session save/load/resume orchestration.

Provides high-level API for persisting sessions to disk and restoring them
with full state recovery, enabling pause/resume workflows.
"""

import json
from pathlib import Path
from app.runtime.session_persistence import serialize_session, deserialize_session
from app.runtime.runtime_models import SessionState


def save_session(session: SessionState, file_path: str) -> None:
    """Save session to disk in JSON format.

    Args:
        session: SessionState to persist
        file_path: Path where session JSON will be written

    Raises:
        IOError: If file cannot be written
        TypeError: If session contains non-serializable data
    """
    data = serialize_session(session)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)


def load_session(file_path: str) -> SessionState:
    """Load session from disk JSON file.

    Args:
        file_path: Path to session JSON file

    Returns:
        Reconstructed SessionState with full state

    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file is not valid JSON
        KeyError: If session data is missing required fields
        ValueError: If session data is malformed
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    return deserialize_session(data)
