"""
Backend session mirrors (read-only copies of world-engine state).

Backend mirrors what world-engine owns.
Backend never modifies mirrors directly.
Mirrors are updated via sync from world-engine.
"""

from typing import Dict, Any, Optional
from copy import deepcopy


class SessionMirror:
    """
    Read-only backend mirror of world-engine sessions.

    Constitutional Law 1: One truth boundary
    - World-engine is source of truth
    - Backend holds copies for fast query access
    - Conflicts: world-engine is always correct
    """

    def __init__(self):
        """Initialize session mirror store."""
        self._mirrors: Dict[str, Dict[str, Any]] = {}

    def store_session_copy(self, session_data: Dict[str, Any]) -> None:
        """
        Store a copy of world-engine session.

        Args:
            session_data: Full session data from world-engine

        Note:
            This should be called by sync mechanism, not directly.
        """
        session_id = session_data.get("session_id")
        if not session_id:
            raise ValueError("session_data must include session_id")

        # Store deep copy (prevent accidental modification)
        self._mirrors[session_id] = deepcopy(session_data)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a copy of mirrored session state.

        Args:
            session_id: Session to retrieve

        Returns:
            Deep copy of session data (or None if not found)

        Note:
            Returns a copy, not a reference, to enforce read-only.
        """
        if session_id not in self._mirrors:
            return None

        # Return deep copy to prevent accidental modification
        return deepcopy(self._mirrors[session_id])

    def apply_turn_result(
        self,
        session_id: str,
        turn_result: Dict[str, Any]
    ) -> bool:
        """
        Apply turn result to mirror.

        Args:
            session_id: Session to update
            turn_result: Result from world-engine turn execution

        Returns:
            True if update succeeded, False if session not found

        Note:
            This is called by sync mechanism after world-engine commits.
        """
        if session_id not in self._mirrors:
            return False

        session = self._mirrors[session_id]

        # Update turn number
        if "turn_number" in turn_result:
            session["turn_number"] = turn_result["turn_number"]

        # Apply state delta
        if "state_delta" in turn_result and turn_result["state_delta"]:
            if "state" not in session:
                session["state"] = {}
            session["state"].update(turn_result["state_delta"])

        # Record in history
        if "history" not in session:
            session["history"] = []
        session["history"].append(turn_result)

        return True

    def list_sessions(self) -> list:
        """List all mirrored sessions."""
        return list(self._mirrors.keys())

    def clear_mirror(self, session_id: str) -> bool:
        """
        Remove session mirror.

        Args:
            session_id: Session to remove

        Returns:
            True if removed, False if not found
        """
        if session_id in self._mirrors:
            del self._mirrors[session_id]
            return True
        return False
