"""Unit tests for W3.3 in-memory session store.

Tests verify:
- RuntimeSession creation and retrieval
- State isolation between sessions
- Turn counter incrementation
- Session deletion
- No data leakage between concurrent sessions
"""

import pytest
from datetime import datetime, timezone
from app.runtime.session_store import RuntimeSession, create_session, get_session, update_session, delete_session, clear_registry
from app.runtime.runtime_models import SessionState, SessionStatus


class TestRuntimeSessionModel:
    """Unit tests for RuntimeSession dataclass."""

    def test_create_runtime_session_with_required_fields(self):
        """RuntimeSession can be created with session_id, current_runtime_state, module, turn_counter."""
        session_state = SessionState(
            session_id="test_sess_1",
            module_id="god_of_carnage",
            module_version="1.0.0",
            current_scene_id="act_1_scene_1",
            status=SessionStatus.ACTIVE,
            turn_counter=0,
        )

        # Create a mock module (minimal)
        class MockModule:
            module_id = "god_of_carnage"

        runtime_session = RuntimeSession(
            session_id="test_sess_1",
            current_runtime_state=session_state,
            module=MockModule(),
            turn_counter=0,
        )

        assert runtime_session.session_id == "test_sess_1"
        assert runtime_session.current_runtime_state.session_id == "test_sess_1"
        assert runtime_session.turn_counter == 0
        assert runtime_session.updated_at is not None

    def test_runtime_session_updated_at_timestamp(self):
        """RuntimeSession.updated_at is set to current time."""
        session_state = SessionState(
            session_id="test_sess_2",
            module_id="god_of_carnage",
            module_version="1.0.0",
            current_scene_id="act_1_scene_1",
            status=SessionStatus.ACTIVE,
        )

        class MockModule:
            module_id = "god_of_carnage"

        before = datetime.now(timezone.utc)
        runtime_session = RuntimeSession(
            session_id="test_sess_2",
            current_runtime_state=session_state,
            module=MockModule(),
        )
        after = datetime.now(timezone.utc)

        assert before <= runtime_session.updated_at <= after


class TestSessionStoreRegistry:
    """Unit tests for session store CRUD operations."""

    def setup_method(self):
        """Clear registry before each test."""
        clear_registry()

    def test_create_session_and_retrieve(self):
        """Can create a session and retrieve it by session_id."""
        session_state = SessionState(
            session_id="sess_1",
            module_id="god_of_carnage",
            module_version="1.0.0",
            current_scene_id="start",
            status=SessionStatus.ACTIVE,
        )

        class MockModule:
            module_id = "god_of_carnage"

        runtime_session = create_session("sess_1", session_state, MockModule())

        retrieved = get_session("sess_1")
        assert retrieved is not None
        assert retrieved.session_id == "sess_1"
        assert retrieved.turn_counter == 0

    def test_get_nonexistent_session_returns_none(self):
        """Getting a nonexistent session returns None."""
        result = get_session("nonexistent")
        assert result is None

    def test_update_session_replaces_state(self):
        """Updating a session replaces current_runtime_state."""
        session_state = SessionState(
            session_id="sess_2",
            module_id="god_of_carnage",
            module_version="1.0.0",
            current_scene_id="act_1_scene_1",
            status=SessionStatus.ACTIVE,
            turn_counter=0,
        )

        class MockModule:
            module_id = "god_of_carnage"

        create_session("sess_2", session_state, MockModule())

        # Update with new state
        new_session_state = SessionState(
            session_id="sess_2",
            module_id="god_of_carnage",
            module_version="1.0.0",
            current_scene_id="act_2_scene_1",
            status=SessionStatus.ACTIVE,
            turn_counter=1,
        )

        update_session("sess_2", new_session_state)

        retrieved = get_session("sess_2")
        assert retrieved.current_runtime_state.current_scene_id == "act_2_scene_1"
        assert retrieved.current_runtime_state.turn_counter == 1

    def test_delete_session_removes_from_registry(self):
        """Deleting a session removes it from registry."""
        session_state = SessionState(
            session_id="sess_3",
            module_id="god_of_carnage",
            module_version="1.0.0",
            current_scene_id="start",
            status=SessionStatus.ACTIVE,
        )

        class MockModule:
            module_id = "god_of_carnage"

        create_session("sess_3", session_state, MockModule())
        assert get_session("sess_3") is not None

        delete_session("sess_3")
        assert get_session("sess_3") is None

    def test_multiple_concurrent_sessions_no_leakage(self):
        """Multiple sessions in registry do not leak state into each other."""
        class MockModule:
            module_id = "god_of_carnage"

        session_state_1 = SessionState(
            session_id="sess_a",
            module_id="god_of_carnage",
            module_version="1.0.0",
            current_scene_id="scene_a",
            status=SessionStatus.ACTIVE,
        )

        session_state_2 = SessionState(
            session_id="sess_b",
            module_id="god_of_carnage",
            module_version="1.0.0",
            current_scene_id="scene_b",
            status=SessionStatus.ACTIVE,
        )

        create_session("sess_a", session_state_1, MockModule())
        create_session("sess_b", session_state_2, MockModule())

        sess_a = get_session("sess_a")
        sess_b = get_session("sess_b")

        assert sess_a.current_runtime_state.current_scene_id == "scene_a"
        assert sess_b.current_runtime_state.current_scene_id == "scene_b"

    def test_duplicate_session_registration_raises_value_error(self):
        """Registering the same session_id twice raises a hard error."""
        class MockModule:
            module_id = "god_of_carnage"

        session_state = SessionState(
            session_id="sess_dup",
            module_id="god_of_carnage",
            module_version="1.0.0",
            current_scene_id="start",
            status=SessionStatus.ACTIVE,
        )

        create_session("sess_dup", session_state, MockModule())
        with pytest.raises(ValueError, match="already registered"):
            create_session("sess_dup", session_state, MockModule())
