import pytest
import sys
import os
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Add parent directory to path to allow imports
backend_parent = str(Path(__file__).parent.parent.parent)
sys.path.insert(0, backend_parent)

from app.runtime.session_mirror import SessionMirror
from app.services.session_service import SessionService


# Inline SessionManager and TurnExecutor for testing without importing from world-engine
@dataclass
class Session:
    """Authoritative session state (owned by world-engine)."""
    session_id: str
    world_id: str
    session_type: str
    turn_number: int
    created_at: datetime
    state: Dict[str, Any]
    players: Dict[str, str] = None
    history: list = None

    def __post_init__(self):
        if self.players is None:
            self.players = {}
        if self.history is None:
            self.history = []

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
    """World-engine session authority."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create_session(
        self,
        world_id: str,
        session_type: str,
        initial_state: Dict[str, Any]
    ) -> Session:
        """Create authoritative session."""
        import uuid
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

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get authoritative session state."""
        return self._sessions.get(session_id)

    def bind_player(self, session_id: str, player_id: str) -> bool:
        """Bind player to session."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.players[player_id] = player_id
        return True


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
        self.session_manager = session_manager

    def execute_turn(
        self,
        session_id: str,
        player_id: str,
        action: Dict[str, Any]
    ) -> TurnResult:
        """Execute a turn authoritatively."""
        session = self.session_manager.get_session(session_id)
        if not session:
            return TurnResult(
                success=False,
                new_turn_number=-1,
                error_message=f"Session {session_id} not found"
            )

        if player_id not in session.players:
            return TurnResult(
                success=False,
                new_turn_number=session.turn_number,
                error_message="Player not bound to session"
            )

        if not self._is_valid_action(action):
            return TurnResult(
                success=False,
                new_turn_number=session.turn_number,
                error_message="Invalid action format"
            )

        state_delta = self._execute_action(session, player_id, action)
        session.turn_number += 1

        session.history.append({
            "turn": session.turn_number - 1,
            "player_id": player_id,
            "action": action,
            "delta": state_delta,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

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
        """Execute action game logic."""
        return {
            "action_executed": action["type"],
            "turn_number": session.turn_number
        }


class MockWorldEngineClient:
    """Mock world-engine for testing without actual service."""

    def __init__(self):
        self.session_manager = SessionManager()
        self.turn_executor = TurnExecutor(self.session_manager)

    def create_session(self, world_id, session_type, initial_state):
        return self.session_manager.create_session(world_id, session_type, initial_state)

    def get_session(self, session_id):
        return self.session_manager.get_session(session_id)

    def bind_player(self, session_id, player_id):
        return self.session_manager.bind_player(session_id, player_id)

    def execute_turn(self, session_id, player_id, action):
        return self.turn_executor.execute_turn(session_id, player_id, action)


class TestSessionIntegration:
    """Integration test: world-engine authority + backend mirrors."""

    @pytest.fixture
    def we_client(self):
        return MockWorldEngineClient()

    @pytest.fixture
    def session_service(self, we_client):
        return SessionService(
            world_engine_client=we_client,
            session_mirror=SessionMirror()
        )

    def test_session_created_in_both_world_engine_and_mirror(self, session_service, we_client):
        """Session creation creates in world-engine and mirrors to backend."""
        # Create via service
        result = session_service.create_session(
            world_id="wos",
            session_type="player_game",
            initial_state={"players": []}
        )

        assert result is not None
        session_id = result["session_id"]

        # Verify in world-engine (authoritative)
        we_session = we_client.get_session(session_id)
        assert we_session is not None
        assert we_session.world_id == "wos"

        # Verify in backend mirror
        be_session = session_service.get_session(session_id)
        assert be_session is not None
        assert be_session["world_id"] == "wos"

    def test_turn_execution_updates_both_world_engine_and_mirror(self, session_service, we_client):
        """Turn execution updates world-engine, then mirrors to backend."""
        # Create session
        session_data = session_service.create_session(
            world_id="wos",
            session_type="player_game",
            initial_state={"turn": 0}
        )
        session_id = session_data["session_id"]

        # Bind player
        session_service.bind_player(session_id, "p_1")

        # Execute turn
        result = session_service.execute_turn(
            session_id=session_id,
            player_id="p_1",
            action={"type": "move"}
        )

        assert result["success"]
        assert result["new_turn_number"] == 1

        # Verify in world-engine
        we_session = we_client.get_session(session_id)
        assert we_session.turn_number == 1

        # Verify in backend mirror
        be_session = session_service.get_session(session_id)
        assert be_session["turn_number"] == 1

    def test_authority_principle_backend_reflects_world_engine(self, session_service, we_client):
        """Constitutional Law 1: Backend mirrors what world-engine says."""
        # Create and bind
        session_data = session_service.create_session(
            world_id="wos",
            session_type="player_game",
            initial_state={}
        )
        session_id = session_data["session_id"]
        session_service.bind_player(session_id, "p_1")

        # Execute multiple turns
        for expected_turn in range(1, 4):
            result = session_service.execute_turn(
                session_id=session_id,
                player_id="p_1",
                action={"type": "wait"}
            )

            assert result["new_turn_number"] == expected_turn

            # Backend must match world-engine exactly
            we_session = we_client.get_session(session_id)
            be_session = session_service.get_session(session_id)

            assert be_session["turn_number"] == we_session.turn_number == expected_turn
