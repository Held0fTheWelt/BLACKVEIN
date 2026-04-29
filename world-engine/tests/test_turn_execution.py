import pytest
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.runtime.session_manager import SessionManager
from app.runtime.turn_executor import TurnExecutor, TurnResult


class TestTurnExecution:
    """World-engine executes turns authoritatively."""

    @pytest.fixture
    def session_mgr(self):
        return SessionManager()

    @pytest.fixture
    def turn_executor(self, session_mgr):
        return TurnExecutor(session_mgr)

    def test_execute_turn_increments_turn_number(self, session_mgr, turn_executor):
        """Executing a turn increments turn number authoritatively."""
        session = session_mgr.create_session(
            "wos", "player_game",
            {"players": [], "turn": 0}
        )

        # Bind player to session
        session_mgr.bind_player(session.session_id, "p_1")

        result = turn_executor.execute_turn(
            session_id=session.session_id,
            player_id="p_1",
            action={"type": "move", "direction": "north"}
        )

        assert result.success
        assert result.new_turn_number == 1
        assert result.state_delta is not None

    def test_turn_number_is_sequential(self, session_mgr, turn_executor):
        """Constitutional Law 3: Turn 0 is canonical, then sequential."""
        session = session_mgr.create_session("wos", "player_game", {})

        # Bind player to session
        session_mgr.bind_player(session.session_id, "p_1")

        # Execute turns 1, 2, 3...
        for expected_turn in range(1, 4):
            result = turn_executor.execute_turn(
                session_id=session.session_id,
                player_id="p_1",
                action={"type": "wait"}
            )
            assert result.new_turn_number == expected_turn

    def test_turn_result_includes_state_delta(self, session_mgr, turn_executor):
        """Turn results include what changed."""
        session = session_mgr.create_session(
            "wos", "player_game",
            {"player_pos": (0, 0)}
        )

        # Bind player to session
        session_mgr.bind_player(session.session_id, "p_1")

        result = turn_executor.execute_turn(
            session_id=session.session_id,
            player_id="p_1",
            action={"type": "move", "direction": "north"}
        )

        assert result.state_delta is not None
        assert "action_executed" in result.state_delta or len(result.state_delta) > 0

    def test_execution_fails_for_nonexistent_session(self, turn_executor):
        """Execution fails gracefully for bad session ID."""
        result = turn_executor.execute_turn(
            session_id="s_nonexistent",
            player_id="p_1",
            action={"type": "move"}
        )

        assert not result.success
        assert "session" in result.error_message.lower()
