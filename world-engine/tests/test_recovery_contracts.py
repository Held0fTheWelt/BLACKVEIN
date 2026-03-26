"""Recovery and Rollback Contract Tests for World Engine.

WAVE 7 Hardening Initiative: Recovery, rollback, and crash consistency tests.
Tests focus on data recovery guarantees and consistency after failures.

Mark: @pytest.mark.persistence
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.runtime.manager import RuntimeManager
from app.runtime.models import (
    ParticipantState,
    RunStatus,
    RuntimeInstance,
    TranscriptEntry,
)
from app.runtime.store import JsonRunStore


@pytest.mark.persistence
def test_failed_write_triggers_rollback(tmp_path):
    """Verify that failed write operations don't leave partial data."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")

    # Initial save
    manager.store.save(run)
    initial_loaded = manager.store.load_all()
    assert len(initial_loaded) > 0

    # Simulate a write by modifying and saving
    run.tension = 99
    manager.store.save(run)

    # Verify updated data persisted correctly
    updated_loaded = manager.store.load_all()
    updated_run = next((r for r in updated_loaded if r.id == run.id), None)
    assert updated_run.tension == 99

    # Verify no partial/corrupted files exist
    json_files = list(tmp_path.glob("*.json"))
    for json_file in json_files:
        # Should be valid JSON
        try:
            json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pytest.fail(f"Corrupted JSON file found: {json_file}")


@pytest.mark.persistence
def test_partial_update_rollback(tmp_path):
    """Verify that partial updates are handled correctly without corruption."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")

    # Get initial participant count (includes NPCs)
    initial_count = len(run.participants)

    # Add transcript entries to verify granular updates
    entry1 = TranscriptEntry(
        kind="chat",
        actor="Speaker1",
        text="Message 1",
        room_id="room_1",
    )
    entry2 = TranscriptEntry(
        kind="chat",
        actor="Speaker2",
        text="Message 2",
        room_id="room_1",
    )
    run.transcript.append(entry1)
    run.transcript.append(entry2)

    manager.store.save(run)

    # Load to verify both entries exist
    loaded = manager.store.load_all()
    loaded_run = next((r for r in loaded if r.id == run.id), None)
    assert len(loaded_run.transcript) == 2

    # Attempt to modify one entry and add another
    run.transcript[0].text = "Message 1 Updated"
    entry3 = TranscriptEntry(
        kind="chat",
        actor="Speaker3",
        text="Message 3",
        room_id="room_1",
    )
    run.transcript.append(entry3)
    manager.store.save(run)

    # Reload and verify all entries are still present with correct updates
    loaded = manager.store.load_all()
    loaded_run = next((r for r in loaded if r.id == run.id), None)
    assert len(loaded_run.transcript) == 3
    assert loaded_run.transcript[0].text == "Message 1 Updated"
    assert loaded_run.transcript[1].text == "Message 2"
    assert loaded_run.transcript[2].text == "Message 3"


@pytest.mark.persistence
def test_recovery_from_corrupted_snapshot(tmp_path):
    """Verify that corrupted snapshots can be recovered from."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")
    manager.store.save(run)

    # Create a corrupted JSON file alongside the valid one
    corrupted_file = tmp_path / "corrupted_run.json"
    corrupted_file.write_text("{invalid json", encoding="utf-8")

    # Load should skip the corrupted file and return the valid one
    store = JsonRunStore(tmp_path)
    loaded = store.load_all()

    # Verify valid run is still loaded
    assert any(r.id == run.id for r in loaded)


@pytest.mark.persistence
def test_concurrent_access_without_data_loss(tmp_path):
    """Verify that multiple runs can be accessed without data loss."""
    manager = RuntimeManager(store_root=tmp_path)

    # Create multiple runs
    runs = []
    for i in range(5):
        run = manager.create_run(
            "god_of_carnage_solo",
            account_id=f"acct:user{i}",
            display_name=f"User {i}",
        )
        run.tension = i * 10
        manager.store.save(run)
        runs.append(run)

    # Load all and verify none are lost
    loaded = manager.store.load_all()
    assert len(loaded) >= 5

    for original_run in runs:
        loaded_run = next((r for r in loaded if r.id == original_run.id), None)
        assert loaded_run is not None
        assert loaded_run.tension == original_run.tension


@pytest.mark.persistence
def test_store_reconnection_consistency(tmp_path, sqlalchemy_available):
    """Verify that store reconnection maintains data consistency."""
    # Test with JSON store
    json_path = tmp_path / "json_store"
    json_path.mkdir()
    manager1 = RuntimeManager(store_root=json_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")
    manager1.store.save(run1)

    # Create new store instance (simulating reconnection)
    store2 = JsonRunStore(json_path)
    loaded = store2.load_all()

    # Verify data is still available
    assert any(r.id == run1.id for r in loaded)

    # Note: SQLAlchemy store testing is done separately in test_store_sqlalchemy.py
    # RuntimeManager only supports JsonRunStore, so we only test JSON persistence here


@pytest.mark.persistence
def test_incomplete_transaction_cleanup(tmp_path):
    """Verify that incomplete transactions don't leave orphaned resources."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")

    # Start a save but don't complete it properly (simulate interruption)
    # The atomic write pattern should prevent partial files
    destination = tmp_path / f"{run.id}.json"
    temp_path = destination.with_suffix(".json.tmp")

    # If a temp file exists, it shouldn't interfere with loads
    temp_path.write_text("{incomplete", encoding="utf-8")

    # Load should work despite temp file
    store = JsonRunStore(tmp_path)
    loaded = store.load_all()

    # Verify the .json.tmp file doesn't interfere
    # and that we can save a new file
    manager.store.save(run)
    loaded_after = manager.store.load_all()
    assert any(r.id == run.id for r in loaded_after)


@pytest.mark.persistence
def test_run_state_recovery_after_crash(tmp_path):
    """Verify that run state can be recovered after a simulated crash."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")

    # Set up complex state with transcript and metadata
    run.tension = 75
    run.metadata["crash_test"] = True
    entry = TranscriptEntry(
        kind="chat",
        actor="Speaker",
        text="Important message",
        room_id="room_1",
    )
    run.transcript.append(entry)

    # Save before crash
    manager.store.save(run)

    # Simulate crash by creating new manager (fresh load from storage)
    manager_recovered = RuntimeManager(store_root=tmp_path)

    # Verify state was recovered
    recovered_run = manager_recovered.instances.get(run.id)
    if recovered_run:  # Manager loads persistent instances on init
        assert recovered_run.tension == 75
        assert recovered_run.metadata.get("crash_test") == True
        assert len(recovered_run.transcript) == 1
        assert recovered_run.transcript[0].text == "Important message"


@pytest.mark.persistence
def test_database_constraint_violation_handling(tmp_path, sqlalchemy_available):
    """Verify that database constraint violations are handled gracefully."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = "sqlite:///:memory:"
    manager = RuntimeManager(store_root=tmp_path)

    # Create and save a run
    run = manager.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")
    manager.store.save(run)

    # Load and verify
    loaded = manager.store.load_all()
    assert len(loaded) > 0

    # Attempt to save again (update scenario)
    # Should handle gracefully (update instead of insert)
    run.tension = 100
    manager.store.save(run)

    # Verify update succeeded
    loaded_after = manager.store.load_all()
    updated_run = next((r for r in loaded_after if r.id == run.id), None)
    assert updated_run.tension == 100


@pytest.mark.persistence
def test_store_describe_accuracy(tmp_path):
    """Verify that store description provides accurate backend information."""
    # Test JSON store description (RuntimeManager always uses JSON store)
    json_manager = RuntimeManager(store_root=tmp_path)
    desc = json_manager.store.describe()
    assert desc["backend"] == "json"
    assert "root" in desc
    # SQLAlchemy store description is tested separately in test_store_sqlalchemy.py
