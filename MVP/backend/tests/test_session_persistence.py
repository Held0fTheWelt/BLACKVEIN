"""Session persistence (save/load/resume) tests.

Tests cover:
1. Serialize session to disk (JSON)
2. Deserialize and restore full state
3. Resume session execution after load
4. Persistence with state changes
5. Error handling (missing files, corrupted data)
"""

import pytest
import json
import tempfile
import asyncio
from pathlib import Path
from app.services.session_service import create_session
from app.services.persistence_service import save_session, load_session
from app.runtime.session_store import delete_session, get_session as get_stored_session
from app.runtime.turn_dispatcher import dispatch_turn


class TestSessionPersistence:
    """Session save/load/resume functionality."""

    def test_persist_session_to_disk_and_restore(self):
        """Persist: Session saved to JSON, loaded back with full state."""
        # Create and execute session
        session = create_session("god_of_carnage")
        runtime_session = get_stored_session(session.session_id)

        # Execute a few turns to build state
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for i in range(1, 3):
                result = loop.run_until_complete(
                    dispatch_turn(
                        session, i, runtime_session.module,
                        operator_input=f"action {i}"
                    )
                )
                if result and result.updated_canonical_state:
                    session.canonical_state = result.updated_canonical_state
                session.turn_counter = i
        finally:
            loop.close()

        turn_at_save = session.turn_counter

        # Save to disk
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            save_session(session, f.name)
            save_path = f.name

        try:
            # Load from disk
            restored = load_session(save_path)
            assert restored.session_id == session.session_id
            assert restored.turn_counter == turn_at_save
            assert restored.module_id == "god_of_carnage"
            assert restored.status == session.status
        finally:
            Path(save_path).unlink()

    def test_session_state_preserved_after_save_load(self):
        """Persist: Session state dict preserved across save/load."""
        session = create_session("god_of_carnage")

        # Add metadata to session
        session.metadata = {
            "test_key": "test_value",
            "nested": {"data": 123}
        }

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            save_session(session, f.name)
            save_path = f.name

        try:
            restored = load_session(save_path)
            assert restored.metadata == session.metadata
        finally:
            Path(save_path).unlink()

    def test_save_session_creates_valid_json(self):
        """Persist: Saved file is valid JSON and human-readable."""
        session = create_session("god_of_carnage")

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            save_session(session, f.name)
            save_path = f.name

        try:
            # Verify it's valid JSON
            with open(save_path, 'r') as f:
                data = json.load(f)

            # Verify structure
            assert "session_id" in data
            assert "module_id" in data
            assert "turn_counter" in data
            assert "status" in data
        finally:
            Path(save_path).unlink()

    def test_load_nonexistent_file_raises_error(self):
        """Persist: Loading non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_session("/nonexistent/path/session.json")

    def test_load_corrupted_json_raises_error(self):
        """Persist: Loading corrupted JSON raises JSONDecodeError."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write("{ invalid json }")
            save_path = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                load_session(save_path)
        finally:
            Path(save_path).unlink()

    def test_resume_session_after_load(self):
        """Persist: Session can execute turns after being loaded from disk."""
        # Create, execute, save
        session = create_session("god_of_carnage")
        runtime_session = get_stored_session(session.session_id)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                dispatch_turn(
                    session, 1, runtime_session.module,
                    operator_input="initial action"
                )
            )
            if result and result.updated_canonical_state:
                session.canonical_state = result.updated_canonical_state
            session.turn_counter = 1
        finally:
            loop.close()

        turn_at_save = session.turn_counter

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            save_session(session, f.name)
            save_path = f.name

        try:
            # Load and resume
            restored = load_session(save_path)

            # Create new runtime session from restored state
            from app.content.module_loader import load_module
            from app.runtime.session_store import create_session as register_session

            restored_module = load_module(restored.module_id)
            # Same process still holds the pre-save registration; resume simulates a fresh runtime.
            delete_session(restored.session_id)
            register_session(restored.session_id, restored, restored_module)
            restored_runtime = get_stored_session(restored.session_id)

            # Execute one more turn on restored session
            loop2 = asyncio.new_event_loop()
            asyncio.set_event_loop(loop2)
            try:
                next_turn = turn_at_save + 1
                result = loop2.run_until_complete(
                    dispatch_turn(
                        restored, next_turn, restored_runtime.module,
                        operator_input="resumed action"
                    )
                )
                assert result is not None
                assert result.turn_number == next_turn
                restored.turn_counter = next_turn
            finally:
                loop2.close()
        finally:
            Path(save_path).unlink()

    def test_multiple_sessions_saved_independently(self):
        """Persist: Multiple sessions can be saved independently."""
        session1 = create_session("god_of_carnage")
        session2 = create_session("god_of_carnage")

        session1.metadata = {"id": 1}
        session2.metadata = {"id": 2}

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f1:
            save_session(session1, f1.name)
            path1 = f1.name

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f2:
            save_session(session2, f2.name)
            path2 = f2.name

        try:
            restored1 = load_session(path1)
            restored2 = load_session(path2)

            assert restored1.session_id != restored2.session_id
            assert restored1.metadata["id"] == 1
            assert restored2.metadata["id"] == 2
        finally:
            Path(path1).unlink()
            Path(path2).unlink()

    def test_session_turn_counter_preserved(self):
        """Persist: Turn counter correctly preserved after multiple turns."""
        session = create_session("god_of_carnage")
        runtime_session = get_stored_session(session.session_id)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for i in range(1, 5):
                result = loop.run_until_complete(
                    dispatch_turn(
                        session, i, runtime_session.module,
                        operator_input=f"action {i}"
                    )
                )
                if result and result.updated_canonical_state:
                    session.canonical_state = result.updated_canonical_state
                # Manually track turn counter
                session.turn_counter = i
        finally:
            loop.close()

        assert session.turn_counter == 4

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            save_session(session, f.name)
            save_path = f.name

        try:
            restored = load_session(save_path)
            assert restored.turn_counter == 4
        finally:
            Path(save_path).unlink()
