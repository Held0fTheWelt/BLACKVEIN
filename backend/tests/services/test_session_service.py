import pytest
from app.services.session_service import create_session, get_session

def test_create_session_returns_session_state():
    """Verify create_session returns a SessionState object."""
    session = create_session(module_id="god_of_carnage")

    assert session is not None
    assert hasattr(session, 'session_id')
    assert hasattr(session, 'module_id')
    assert session.module_id == "god_of_carnage"
    assert session.turn_counter == 0
