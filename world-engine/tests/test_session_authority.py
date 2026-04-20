import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.runtime.session_manager import SessionManager


class TestSessionAuthority:
    """World-engine holds all session authority."""

    @pytest.fixture
    def session_mgr(self):
        return SessionManager()

    def test_create_session_creates_with_authority(self, session_mgr):
        """World-engine creates sessions with authoritative state."""
        session = session_mgr.create_session(
            world_id="wos",
            session_type="player_game",
            initial_state={"version": 1, "players": []}
        )

        assert session.session_id.startswith("s_")
        assert session.world_id == "wos"
        assert session.turn_number == 0
        assert session.created_at is not None
        assert session.state == {"version": 1, "players": []}

    def test_session_has_unique_id(self, session_mgr):
        """Each session gets unique ID from world-engine."""
        s1 = session_mgr.create_session("wos", "player_game", {})
        s2 = session_mgr.create_session("wos", "player_game", {})

        assert s1.session_id != s2.session_id

    def test_session_turn_starts_at_zero(self, session_mgr):
        """All sessions start at turn 0."""
        session = session_mgr.create_session("wos", "player_game", {})
        assert session.turn_number == 0

    def test_session_stored_in_world_engine_authority(self, session_mgr):
        """Created session is stored only in world-engine (not yet mirrored)."""
        session = session_mgr.create_session("wos", "player_game", {"data": "test"})

        # Retrieve from session manager (authoritative)
        retrieved = session_mgr.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.state == {"data": "test"}
