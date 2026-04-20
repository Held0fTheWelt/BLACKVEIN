import pytest
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.session_service import SessionService


class TestSessionService:
    """Backend session service orchestrates world-engine and mirrors."""

    @pytest.fixture
    def session_service(self):
        # Mock world-engine client for testing
        return SessionService()

    def test_create_session_via_world_engine(self, session_service):
        """Session creation goes through world-engine."""
        # This test will use mock world-engine
        pass  # Placeholder - full tests in next step

    def test_get_session_from_mirror(self, session_service):
        """Session reads come from backend mirror."""
        pass  # Placeholder

    def test_execute_turn_via_world_engine(self, session_service):
        """Turn execution goes through world-engine."""
        pass  # Placeholder
