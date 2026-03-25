"""JSON File-Based Persistence Tests.

WAVE 8: Comprehensive runtime behavior and persistence testing.
Tests JsonRunStore: create, load, save roundtrips, and error handling.

Mark: @pytest.mark.persistence, @pytest.mark.contract
"""

from __future__ import annotations

import json
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
@pytest.mark.contract
def test_json_store_create_and_save(tmp_path):
    """Verify JsonRunStore saves instances to disk."""
    store = JsonRunStore(tmp_path)
    instance = RuntimeInstance(
        id="test-run-1",
        template_id="test-template",
        template_title="Test Template",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
    )

    store.save(instance)

    # Verify file exists
    saved_file = tmp_path / "test-run-1.json"
    assert saved_file.exists()


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_load_all_returns_saved_instances(tmp_path):
    """Verify load_all retrieves all saved instances."""
    store = JsonRunStore(tmp_path)

    # Create and save multiple instances
    for i in range(3):
        instance = RuntimeInstance(
            id=f"test-run-{i}",
            template_id="test-template",
            template_title="Test Template",
            kind="solo_story",
            join_policy="public",
            beat_id="beat1",
        )
        store.save(instance)

    # Load all
    loaded = store.load_all()
    assert len(loaded) == 3
    ids = {inst.id for inst in loaded}
    assert ids == {"test-run-0", "test-run-1", "test-run-2"}


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_roundtrip_preserves_data(tmp_path):
    """Verify data is preserved through save/load cycle."""
    store = JsonRunStore(tmp_path)

    # Create instance with various fields
    instance = RuntimeInstance(
        id="test-run",
        template_id="god_of_carnage_solo",
        template_title="God of Carnage Solo",
        kind="solo_story",
        join_policy="owner_only",
        beat_id="beat_confrontation",
        tension=42,
        persistent=True,
        owner_account_id="acct:alice",
    )
    instance.flags.add("entered_living_room")
    instance.metadata["custom_key"] = "custom_value"

    # Save and load
    store.save(instance)
    loaded_list = store.load_all()
    assert len(loaded_list) == 1
    loaded = loaded_list[0]

    # Verify all fields preserved
    assert loaded.id == "test-run"
    assert loaded.template_id == "god_of_carnage_solo"
    assert loaded.tension == 42
    assert loaded.persistent is True
    assert "entered_living_room" in loaded.flags
    assert loaded.metadata["custom_key"] == "custom_value"


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_transcript_persists(tmp_path):
    """Verify transcript entries are saved and restored."""
    store = JsonRunStore(tmp_path)

    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
    )

    # Add transcript entries
    entry1 = TranscriptEntry(
        kind="speech_committed",
        actor="Alice",
        text="Hello world",
        room_id="room1",
    )
    entry2 = TranscriptEntry(
        kind="emote_committed",
        actor="Alice",
        text="nods",
        room_id="room1",
    )
    instance.transcript.append(entry1)
    instance.transcript.append(entry2)

    # Save and load
    store.save(instance)
    loaded = store.load_all()[0]

    assert len(loaded.transcript) == 2
    assert loaded.transcript[0].text == "Hello world"
    assert loaded.transcript[1].text == "nods"


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_missing_file_handled_gracefully(tmp_path):
    """Verify load_all handles missing files gracefully."""
    store = JsonRunStore(tmp_path)

    # Manually create a corrupted JSON file
    bad_file = tmp_path / "corrupted.json"
    bad_file.write_text("{ invalid json }")

    # Should not crash, just skip corrupted file
    loaded = store.load_all()
    assert len(loaded) == 0


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_atomic_write_with_temp_file(tmp_path):
    """Verify save uses atomic write (temp file rename)."""
    store = JsonRunStore(tmp_path)

    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
    )

    store.save(instance)

    # Verify no .tmp files left behind
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0

    # Verify final file exists
    final_file = tmp_path / "test-run.json"
    assert final_file.exists()


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_update_overwrites_existing(tmp_path):
    """Verify saving over existing file updates data."""
    store = JsonRunStore(tmp_path)

    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
        tension=10,
    )

    store.save(instance)

    # Modify and save again
    instance.tension = 50
    instance.flags.add("test_flag")
    store.save(instance)

    # Load and verify update
    loaded = store.load_all()[0]
    assert loaded.tension == 50
    assert "test_flag" in loaded.flags


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_describe_returns_backend_info(tmp_path):
    """Verify describe returns backend name and root."""
    store = JsonRunStore(tmp_path)

    desc = store.describe()
    assert desc["backend"] == "json"
    assert str(tmp_path) in desc["root"]


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_handles_special_characters_in_data(tmp_path):
    """Verify special characters in data are preserved."""
    store = JsonRunStore(tmp_path)

    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test™ with «special» chars",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
    )

    entry = TranscriptEntry(
        kind="speech_committed",
        actor="Alice",
        text='Say "hello" & goodbye! 测试',
        room_id="room1",
    )
    instance.transcript.append(entry)

    store.save(instance)
    loaded = store.load_all()[0]

    assert "™" in loaded.template_title
    assert "«" in loaded.template_title
    assert '测试' in loaded.transcript[0].text
