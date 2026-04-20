import pytest
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.runtime.session_mirror import SessionMirror


class TestSessionMirror:
    """Backend holds read-only mirrors of world-engine state."""

    @pytest.fixture
    def mirror(self):
        return SessionMirror()

    def test_mirror_stores_session_copy(self, mirror):
        """Backend can store a copy of world-engine session."""
        session_data = {
            "session_id": "s_test123",
            "world_id": "wos",
            "turn_number": 0,
            "state": {"players": []},
            "created_at": "2026-04-20T14:40:00Z",
            "players": {},
            "history": []
        }

        mirror.store_session_copy(session_data)

        retrieved = mirror.get_session("s_test123")
        assert retrieved is not None
        assert retrieved["session_id"] == "s_test123"

    def test_mirror_updates_with_turn_result(self, mirror):
        """Backend mirror updates when turn executes."""
        # Store initial session
        mirror.store_session_copy({
            "session_id": "s_test",
            "turn_number": 0,
            "state": {"pos": 0},
            "created_at": "2026-04-20T14:40:00Z",
            "players": {"p_1": "p_1"},
            "history": []
        })

        # Apply turn result
        turn_result = {
            "turn_number": 1,
            "state_delta": {"pos": 1},
            "timestamp": "2026-04-20T14:40:01Z"
        }

        mirror.apply_turn_result("s_test", turn_result)

        updated = mirror.get_session("s_test")
        assert updated["turn_number"] == 1
        assert updated["state"]["pos"] == 1

    def test_mirror_is_readonly(self, mirror):
        """Backend should not modify session directly (only via sync)."""
        mirror.store_session_copy({
            "session_id": "s_test",
            "state": {"data": "original"},
            "turn_number": 0,
            "created_at": "2026-04-20T14:40:00Z",
            "players": {},
            "history": []
        })

        # Try to get and modify (should return copy, not reference)
        session = mirror.get_session("s_test")
        session["state"]["data"] = "modified"

        # Original should be unchanged
        original = mirror.get_session("s_test")
        assert original["state"]["data"] == "original"
