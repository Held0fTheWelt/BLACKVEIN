"""
World-engine session authority.

World-engine is authoritative for:
- Session creation
- Session state
- Turn numbering
- Player bindings

Backend has read-only mirrors.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid


@dataclass
class Session:
    """Authoritative session state (owned by world-engine)."""
    session_id: str
    world_id: str
    session_type: str  # player_game, npc_scene, tutorial, etc.
    turn_number: int
    created_at: datetime
    state: Dict[str, Any]
    players: Dict[str, str] = field(default_factory=dict)  # player_id -> binding
    history: list = field(default_factory=list)  # Turn history

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage/transmission."""
        return {
            "session_id": self.session_id,
            "world_id": self.world_id,
            "session_type": self.session_type,
            "turn_number": self.turn_number,
            "created_at": self.created_at.isoformat(),
            "state": self.state,
            "players": self.players,
            "history": self.history,
        }


class SessionManager:
    """
    World-engine session authority.

    Owns: creation, state, turn execution, player binding.
    Does NOT own: operator surfaces (backend mirrors those).
    """

    def __init__(self):
        """Initialize session manager."""
        self._sessions: Dict[str, Session] = {}

    def create_session(
        self,
        world_id: str,
        session_type: str,
        initial_state: Dict[str, Any]
    ) -> Session:
        """
        Create authoritative session.

        Args:
            world_id: World this session belongs to
            session_type: Type of session (player_game, npc_scene, etc.)
            initial_state: Initial game state

        Returns:
            Newly created Session with authority

        Constitutional Law: Publish-bound authoritative birth
        - Session is created here, authoritative here
        - Backend mirrors will observe this session
        - No parallel sessions in backend
        """
        session_id = f"s_{uuid.uuid4().hex[:12]}"

        session = Session(
            session_id=session_id,
            world_id=world_id,
            session_type=session_type,
            turn_number=0,
            created_at=datetime.now(timezone.utc),
            state=initial_state,
            players={},
            history=[],
        )

        # Store in world-engine authority
        self._sessions[session_id] = session

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get authoritative session state.

        Constitutional Law: One truth boundary
        - This is the source of truth
        - Backend mirrors query this when needed
        """
        return self._sessions.get(session_id)

    def bind_player(self, session_id: str, player_id: str) -> bool:
        """
        Bind player to session (world-engine authority).

        Args:
            session_id: Session to bind to
            player_id: Player to bind

        Returns:
            True if binding succeeded, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session.players[player_id] = player_id
        return True

    def list_sessions(self) -> list:
        """List all sessions in world-engine (for testing, admin)."""
        return list(self._sessions.values())
