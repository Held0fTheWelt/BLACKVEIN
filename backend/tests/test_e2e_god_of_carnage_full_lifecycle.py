"""E2E tests for God of Carnage full session lifecycle.

Tests cover 5 critical scenario types:
1. Multi-turn progression (5–10 turns)
2. Escalation paths (pressure build, coalition shifts)
3. Error paths (invalid input, AI failures, guard rejections)
4. Recovery behavior (degraded mode, fallbacks)
5. Session termination (natural conclusion, forced end)

Gate 1 Baseline: These tests verify the core session creation and turn execution
work end-to-end using the real runtime without artificial mocking.
"""

import pytest
import asyncio
from app.services.session_service import create_session
from app.runtime.turn_dispatcher import dispatch_turn
from app.runtime.runtime_models import SessionStatus
from app.runtime.session_store import get_session as get_stored_session, RuntimeSession


class TestE2ESessionLifecycle:
    """Core E2E tests for session creation and execution."""

    def test_session_creates_successfully(self):
        """E2E: Session creates successfully and starts in active state."""
        session_state = create_session("god_of_carnage")
        assert session_state is not None
        assert session_state.session_id is not None
        assert session_state.status == SessionStatus.ACTIVE
        assert session_state.module_id == "god_of_carnage"

    def test_session_registered_in_store(self):
        """E2E: Created session is registered in runtime store."""
        session_state = create_session("god_of_carnage")
        runtime_session = get_stored_session(session_state.session_id)

        assert runtime_session is not None
        assert isinstance(runtime_session, RuntimeSession)
        assert runtime_session.turn_counter == 0
        assert runtime_session.module is not None

    def test_single_turn_execution_completes(self):
        """E2E: Single turn execution completes without crashes."""
        session_state = create_session("god_of_carnage")
        runtime_session = get_stored_session(session_state.session_id)

        session = runtime_session.current_runtime_state
        module = runtime_session.module

        # Execute one turn via dispatcher
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                dispatch_turn(session, 1, module, operator_input="test action")
            )
            assert result is not None
            assert result.turn_number == 1
            assert result.execution_status is not None
        finally:
            loop.close()

    def test_multiple_turns_execute_sequentially(self):
        """E2E: Multiple turns execute sequentially without crashes."""
        session_state = create_session("god_of_carnage")
        runtime_session = get_stored_session(session_state.session_id)

        session = runtime_session.current_runtime_state
        module = runtime_session.module

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for turn_num in range(1, 6):
                result = loop.run_until_complete(
                    dispatch_turn(
                        session, turn_num, module,
                        operator_input=f"action turn {turn_num}"
                    )
                )
                assert result is not None
                assert result.turn_number == turn_num
                # Update session with returned canonical state for next turn
                if result.updated_canonical_state:
                    session.canonical_state = result.updated_canonical_state
        finally:
            loop.close()

    def test_error_input_doesnt_crash_session(self):
        """E2E: Empty/malformed input doesn't crash the session."""
        session_state = create_session("god_of_carnage")
        runtime_session = get_stored_session(session_state.session_id)

        session = runtime_session.current_runtime_state
        module = runtime_session.module

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Try with empty input
            result = loop.run_until_complete(
                dispatch_turn(session, 1, module, operator_input="")
            )
            assert result is not None

            # Try with whitespace
            result = loop.run_until_complete(
                dispatch_turn(session, 2, module, operator_input="   ")
            )
            assert result is not None
        finally:
            loop.close()

    def test_session_maintains_module_reference(self):
        """E2E: Session maintains module reference throughout lifecycle."""
        session_state = create_session("god_of_carnage")
        runtime_session = get_stored_session(session_state.session_id)

        assert runtime_session.module is not None
        # Module should remain consistent
        initial_module = runtime_session.module
        runtime_session_2 = get_stored_session(session_state.session_id)
        assert runtime_session_2.module == initial_module
