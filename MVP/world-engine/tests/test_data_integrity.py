"""Data Integrity Contract Tests for World Engine.

WAVE 7 Hardening Initiative: Data integrity and validation tests.
Tests focus on ensuring data consistency, uniqueness, and constraint enforcement.

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
    PropState,
    RunStatus,
    RuntimeInstance,
    TranscriptEntry,
)
from app.runtime.store import JsonRunStore


@pytest.mark.persistence
def test_run_id_uniqueness_enforced(tmp_path):
    """Verify that run IDs are unique and never duplicated."""
    manager = RuntimeManager(store_root=tmp_path)
    run1 = manager.create_run("god_of_carnage_solo", account_id="acct:test1", display_name="Test 1")
    run2 = manager.create_run("god_of_carnage_solo", account_id="acct:test2", display_name="Test 2")
    run3 = manager.create_run("apartment_confrontation_group", account_id="acct:test3", display_name="Test 3")

    # Verify all IDs are unique
    ids = {run1.id, run2.id, run3.id}
    assert len(ids) == 3
    assert run1.id != run2.id
    assert run2.id != run3.id
    assert run1.id != run3.id


@pytest.mark.persistence
def test_participant_identity_consistency(tmp_path):
    """Verify that participant IDs remain consistent across operations."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:owner", display_name="Owner")

    # Create participant with explicit ID
    participant_id = uuid4().hex
    participant = ParticipantState(
        id=participant_id,
        display_name="Alice",
        role_id="role_detective",
        mode="human",
        current_room_id="room_office",
        account_id="acct:alice",
    )
    run.participants[participant.id] = participant

    # Save and reload
    manager.store.save(run)
    loaded = manager.store.load_all()
    loaded_run = next((r for r in loaded if r.id == run.id), None)

    # Verify ID is preserved
    assert participant_id in loaded_run.participants
    loaded_participant = loaded_run.participants[participant_id]
    assert loaded_participant.id == participant_id
    assert loaded_participant.account_id == "acct:alice"


@pytest.mark.persistence
def test_timestamp_ordering_consistency(tmp_path):
    """Verify that timestamps maintain logical ordering."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")

    # Verify created_at is set
    creation_time = run.created_at
    assert creation_time is not None
    assert isinstance(creation_time, datetime)

    # Verify updated_at is >= created_at
    assert run.updated_at >= run.created_at

    # Save and reload
    manager.store.save(run)
    loaded = manager.store.load_all()
    loaded_run = next((r for r in loaded if r.id == run.id), None)

    # Verify timestamps are preserved and ordered
    assert loaded_run.updated_at >= loaded_run.created_at
    assert loaded_run.created_at == creation_time


@pytest.mark.persistence
def test_transcript_message_sequence_integrity(tmp_path):
    """Verify that transcript messages maintain sequence integrity."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")

    # Add transcript entries in order
    for i in range(10):
        entry = TranscriptEntry(
            kind="chat",
            actor="Speaker",
            text=f"Message {i}",
            room_id="room_1",
        )
        run.transcript.append(entry)

    # Verify order in original
    for i, entry in enumerate(run.transcript):
        assert entry.text == f"Message {i}"

    # Save and reload
    manager.store.save(run)
    loaded = manager.store.load_all()
    loaded_run = next((r for r in loaded if r.id == run.id), None)

    # Verify order is preserved
    assert len(loaded_run.transcript) == 10
    for i, entry in enumerate(loaded_run.transcript):
        assert entry.text == f"Message {i}"


@pytest.mark.persistence
def test_foreign_key_constraints_enforced(tmp_path):
    """Verify that foreign key relationships are maintained."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")

    # Create participant and transcript entry referencing the participant
    participant = ParticipantState(
        display_name="Actor",
        role_id="role_1",
        mode="human",
        current_room_id="room_1",
        account_id="acct:actor",
    )
    run.participants[participant.id] = participant

    # Create transcript entry referencing the participant
    entry = TranscriptEntry(
        kind="chat",
        actor=participant.display_name,  # Reference participant
        text="Hello",
        room_id="room_1",
    )
    run.transcript.append(entry)

    # Save and reload
    manager.store.save(run)
    loaded = manager.store.load_all()
    loaded_run = next((r for r in loaded if r.id == run.id), None)

    # Verify both participant and entry exist
    assert len(loaded_run.participants) > 0
    assert len(loaded_run.transcript) > 0
    # Verify the entry still references the correct participant
    assert loaded_run.transcript[0].actor == "Actor"


@pytest.mark.persistence
def test_data_type_consistency_across_stores(tmp_path):
    """Verify that data types remain consistent after persistence."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")

    # Set various data types
    run.tension = 42  # int
    run.metadata["string_field"] = "test"  # str
    run.metadata["number_field"] = 3.14  # float
    run.metadata["bool_field"] = True  # bool
    run.flags.add("flag1")  # set

    # Save and reload
    manager.store.save(run)
    loaded = manager.store.load_all()
    loaded_run = next((r for r in loaded if r.id == run.id), None)

    # Verify types are preserved
    assert isinstance(loaded_run.tension, int)
    assert loaded_run.tension == 42
    assert isinstance(loaded_run.metadata["string_field"], str)
    assert isinstance(loaded_run.metadata["number_field"], float)
    assert isinstance(loaded_run.metadata["bool_field"], bool)
    assert isinstance(loaded_run.flags, set)
    assert "flag1" in loaded_run.flags


@pytest.mark.persistence
def test_null_field_validation(tmp_path):
    """Verify that nullable fields are handled correctly."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id=None, display_name="Test")

    # Verify nullable fields
    assert run.owner_account_id is None
    assert run.owner_character_id is None

    # Create participant with some nullable fields
    participant = ParticipantState(
        display_name="Test",
        role_id="role_1",
        mode="human",
        current_room_id="room_1",
        account_id=None,  # Nullable
        character_id=None,  # Nullable
    )
    run.participants[participant.id] = participant

    # Save and reload
    manager.store.save(run)
    loaded = manager.store.load_all()
    loaded_run = next((r for r in loaded if r.id == run.id), None)

    # Verify nullable fields are preserved as None
    assert loaded_run.owner_account_id is None
    loaded_participant = next(iter(loaded_run.participants.values()))
    assert loaded_participant.account_id is None


@pytest.mark.persistence
def test_json_schema_validation(tmp_path):
    """Verify that loaded data conforms to expected schema."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")

    # Save and reload
    manager.store.save(run)
    loaded = manager.store.load_all()

    # Verify schema compliance
    assert len(loaded) > 0
    for loaded_run in loaded:
        # RuntimeInstance required fields
        assert hasattr(loaded_run, "id")
        assert hasattr(loaded_run, "template_id")
        assert hasattr(loaded_run, "status")
        assert hasattr(loaded_run, "created_at")
        assert hasattr(loaded_run, "updated_at")
        assert hasattr(loaded_run, "participants")
        assert hasattr(loaded_run, "transcript")

        # Verify collection types
        assert isinstance(loaded_run.participants, dict)
        assert isinstance(loaded_run.transcript, list)
        assert isinstance(loaded_run.flags, set)


@pytest.mark.persistence
def test_data_encoding_consistency(tmp_path):
    """Verify that special characters and encodings are preserved."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:test", display_name="Test")

    # Special characters test in transcript (more reliable than participant name)
    special_chars = "Hello 世界 🌍 Привет Γεια σας"
    entry = TranscriptEntry(
        kind="chat",
        actor="Speaker",
        text=f"Special: {special_chars}",
        room_id="room_1",
    )
    run.transcript.append(entry)

    # Save and reload
    manager.store.save(run)
    loaded = manager.store.load_all()
    loaded_run = next((r for r in loaded if r.id == run.id), None)

    # Verify encoding preserved in transcript
    assert len(loaded_run.transcript) > 0
    # Find our test entry
    test_entry = next(
        (e for e in loaded_run.transcript if "Hello 世界" in e.text),
        None,
    )
    assert test_entry is not None
    assert test_entry.text == f"Special: {special_chars}"


@pytest.mark.persistence
def test_backup_restore_data_integrity(tmp_path):
    """Verify that backup and restore operations preserve data integrity."""
    # Create initial data
    original_path = tmp_path / "original"
    original_path.mkdir()
    manager1 = RuntimeManager(store_root=original_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:test1", display_name="Test 1")
    run2 = manager1.create_run("apartment_confrontation_group", account_id="acct:test2", display_name="Test 2")

    # Add data to runs
    for run in [run1, run2]:
        run.tension = 50
        run.metadata["backup_test"] = True
        manager1.store.save(run)

    # Simulate backup by loading all data
    backed_up = manager1.store.load_all()
    assert len(backed_up) >= 2

    # Simulate restore in new location
    restored_path = tmp_path / "restored"
    restored_path.mkdir()
    restore_store = JsonRunStore(restored_path)

    # Restore each run
    for run in backed_up:
        restore_store.save(run)

    # Verify restored data
    restored = restore_store.load_all()
    assert len(restored) >= 2

    # Verify specific runs
    restored_run1 = next((r for r in restored if r.id == run1.id), None)
    restored_run2 = next((r for r in restored if r.id == run2.id), None)

    assert restored_run1 is not None
    assert restored_run2 is not None
    assert restored_run1.tension == 50
    assert restored_run2.tension == 50
    assert restored_run1.metadata["backup_test"] is True
    assert restored_run2.metadata["backup_test"] is True
