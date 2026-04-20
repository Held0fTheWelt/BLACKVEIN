"""
Backend session service.

Orchestrates:
- World-engine for authoritative operations
- Backend mirrors for read-only queries
"""

from typing import Dict, Any, Optional


class SessionService:
    """
    Session service for backend.

    Handles:
    - Forwarding session creation to world-engine
    - Querying session state from mirror
    - Forwarding turn execution to world-engine
    - Syncing results back to mirror
    """

    def __init__(self, world_engine_client=None, session_mirror=None):
        """
        Initialize session service.

        Args:
            world_engine_client: Client for world-engine calls
            session_mirror: Backend mirror store
        """
        self.world_engine_client = world_engine_client
        self.session_mirror = session_mirror

    def create_session(
        self,
        world_id: str,
        session_type: str,
        initial_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create a session via world-engine.

        Args:
            world_id: World for session
            session_type: Type of session
            initial_state: Initial game state

        Returns:
            Session data or None if creation failed
        """
        if not self.world_engine_client:
            return None

        # Create in world-engine (authoritative)
        session = self.world_engine_client.create_session(
            world_id=world_id,
            session_type=session_type,
            initial_state=initial_state
        )

        if not session:
            return None

        # Mirror in backend
        if self.session_mirror:
            self.session_mirror.store_session_copy(session.to_dict())

        return session.to_dict() if hasattr(session, 'to_dict') else session

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session from mirror (read-only).

        Args:
            session_id: Session to retrieve

        Returns:
            Session data or None
        """
        if not self.session_mirror:
            return None

        return self.session_mirror.get_session(session_id)

    def bind_player(self, session_id: str, player_id: str) -> bool:
        """
        Bind player to session (world-engine authority).

        Args:
            session_id: Session
            player_id: Player

        Returns:
            True if successful
        """
        if not self.world_engine_client:
            return False

        success = self.world_engine_client.bind_player(session_id, player_id)

        if success and self.session_mirror:
            # Update mirror with new player binding
            session = self.world_engine_client.get_session(session_id)
            if session:
                self.session_mirror.store_session_copy(
                    session.to_dict() if hasattr(session, 'to_dict') else session
                )

        return success

    def execute_turn(
        self,
        session_id: str,
        player_id: str,
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute turn via world-engine.

        Args:
            session_id: Session
            player_id: Player
            action: Action to execute

        Returns:
            Turn result with success/error
        """
        if not self.world_engine_client:
            return {"success": False, "error": "World-engine client not configured"}

        # Execute in world-engine
        result = self.world_engine_client.execute_turn(
            session_id=session_id,
            player_id=player_id,
            action=action
        )

        # Convert TurnResult to dict if needed
        result_dict = result if isinstance(result, dict) else {
            "success": result.success,
            "new_turn_number": result.new_turn_number,
            "turn_number": result.new_turn_number,  # Mirror also needs turn_number
            "state_delta": result.state_delta,
            "error_message": result.error_message,
            "executed_at": result.executed_at.isoformat() if result.executed_at else None
        }

        # Update mirror with result
        if result_dict.get("success") and self.session_mirror:
            self.session_mirror.apply_turn_result(session_id, result_dict)

        return result_dict


# Module-level wrapper functions for backwards compatibility
_session_service = SessionService()


def create_session(world_id: str, session_type: str, initial_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Wrapper for SessionService.create_session."""
    return _session_service.create_session(world_id, session_type, initial_state)


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Wrapper for SessionService.get_session."""
    return _session_service.get_session(session_id)


def execute_turn(session_id: str, player_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for SessionService.execute_turn."""
    return _session_service.execute_turn(session_id, player_id, action)


def get_session_logs(session_id: str) -> Optional[list]:
    """Get session logs (stub for now)."""
    return None


def get_session_state(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session state (stub for now)."""
    session = _session_service.get_session(session_id)
    if session:
        return session.get("state", {})
    return None
