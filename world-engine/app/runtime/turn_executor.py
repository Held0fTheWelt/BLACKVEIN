"""
World-engine turn execution authority.

World-engine is sole executor of turns.
Backend forwards turn requests here.
Results are returned to backend and mirrored.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime, timezone


@dataclass
class TurnResult:
    """Result of executing a turn."""
    success: bool
    new_turn_number: int
    state_delta: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    executed_at: Optional[datetime] = None


class TurnExecutor:
    """Execute turns authoritatively in world-engine."""

    def __init__(self, session_manager):
        """
        Initialize turn executor.

        Args:
            session_manager: SessionManager instance for state access
        """
        self.session_manager = session_manager

    def execute_turn(
        self,
        session_id: str,
        player_id: str,
        action: Dict[str, Any]
    ) -> TurnResult:
        """
        Execute a turn authoritatively.

        Constitutional Law 1: One truth boundary
        - This execution is the source of truth
        - Backend mirrors the result after commitment

        Args:
            session_id: Session to execute in
            player_id: Player executing action
            action: Action to execute

        Returns:
            TurnResult with success/failure and state delta
        """
        # Get authoritative session
        session = self.session_manager.get_session(session_id)
        if not session:
            return TurnResult(
                success=False,
                new_turn_number=-1,
                error_message=f"Session {session_id} not found"
            )

        # Constitutional Law 3: Turn 0 is canonical
        # Verify player is bound to session
        if player_id not in session.players:
            return TurnResult(
                success=False,
                new_turn_number=session.turn_number,
                error_message="Player not bound to session"
            )

        # Validate action format
        if not self._is_valid_action(action):
            return TurnResult(
                success=False,
                new_turn_number=session.turn_number,
                error_message="Invalid action format"
            )

        # Execute action (simplified for this implementation)
        state_delta = self._execute_action(session, player_id, action)

        # Increment turn number (AFTER successful execution)
        session.turn_number += 1

        # Record in history
        session.history.append({
            "turn": session.turn_number - 1,
            "player_id": player_id,
            "action": action,
            "delta": state_delta,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Return result (backend will mirror this)
        return TurnResult(
            success=True,
            new_turn_number=session.turn_number,
            state_delta=state_delta,
            executed_at=datetime.now(timezone.utc)
        )

    def _is_valid_action(self, action: Dict[str, Any]) -> bool:
        """Validate action format."""
        return (
            isinstance(action, dict) and
            "type" in action and
            isinstance(action["type"], str)
        )

    def _execute_action(
        self,
        session,
        player_id: str,
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute action game logic.

        Returns state delta (what changed).
        """
        # Simplified: just return action as delta for now
        # Real implementation would have game logic here
        return {
            "action_executed": action["type"],
            "turn_number": session.turn_number
        }
