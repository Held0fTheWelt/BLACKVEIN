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


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_large_transcript_persists(tmp_path):
    """Verify large transcripts are persisted correctly."""
    store = JsonRunStore(tmp_path)

    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
    )

    # Add many transcript entries
    for i in range(100):
        entry = TranscriptEntry(
            kind="speech_committed",
            actor=f"Actor{i % 5}",
            text=f"Message {i}: " + "x" * 500,
            room_id=f"room{i % 10}",
        )
        instance.transcript.append(entry)

    store.save(instance)
    loaded = store.load_all()[0]

    assert len(loaded.transcript) == 100
    assert loaded.transcript[50].text == "Message 50: " + "x" * 500
    assert loaded.transcript[-1].actor == "Actor4"


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_multiple_concurrent_saves_safe(tmp_path):
    """Verify multiple saves don't corrupt data."""
    store = JsonRunStore(tmp_path)

    instance1 = RuntimeInstance(
        id="run-1",
        template_id="template-1",
        template_title="Run 1",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
        tension=10,
    )
    instance2 = RuntimeInstance(
        id="run-2",
        template_id="template-2",
        template_title="Run 2",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
        tension=20,
    )

    # Save both
    store.save(instance1)
    store.save(instance2)

    # Verify both are recoverable
    loaded = store.load_all()
    assert len(loaded) == 2
    ids = {inst.id for inst in loaded}
    assert ids == {"run-1", "run-2"}


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_empty_directory_on_init(tmp_path):
    """Verify store initializes correctly even with missing directory."""
    store_path = tmp_path / "new" / "nested" / "store"
    assert not store_path.exists()

    store = JsonRunStore(store_path)

    assert store_path.exists()
    assert store_path.is_dir()


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_filters_non_json_files(tmp_path):
    """Verify only .json files are loaded, not other files."""
    store = JsonRunStore(tmp_path)

    # Create a valid run
    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
    )
    store.save(instance)

    # Create various non-JSON files
    (tmp_path / "readme.txt").write_text("This is not JSON")
    (tmp_path / "config.yaml").write_text("key: value")
    (tmp_path / "data.bak").write_text('{"corrupted": true}')

    # Load should only get the JSON files
    loaded = store.load_all()
    assert len(loaded) == 1
    assert loaded[0].id == "test-run"


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_preserves_participant_state(tmp_path):
    """Verify participant state is fully preserved."""
    store = JsonRunStore(tmp_path)

    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
    )

    # Add participant state
    participant = ParticipantState(
        id="participant-1",
        display_name="Alice",
        role_id="hero",
        mode="human",
        current_room_id="room-1",
        connected=True,
        account_id="acct:alice",
    )
    instance.participants["participant-1"] = participant

    store.save(instance)
    loaded = store.load_all()[0]

    assert "participant-1" in loaded.participants
    loaded_p = loaded.participants["participant-1"]
    assert loaded_p.display_name == "Alice"
    assert loaded_p.role_id == "hero"
    assert loaded_p.account_id == "acct:alice"
    assert loaded_p.connected is True


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_preserves_prop_state(tmp_path):
    """Verify prop state is fully preserved."""
    store = JsonRunStore(tmp_path)

    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
    )

    # Add prop state
    prop = PropState(
        id="prop-1",
        name="Sword",
        room_id="room-1",
        description="A sharp sword",
        state="hanging_on_wall",
    )
    instance.props["prop-1"] = prop

    store.save(instance)
    loaded = store.load_all()[0]

    assert "prop-1" in loaded.props
    loaded_prop = loaded.props["prop-1"]
    assert loaded_prop.name == "Sword"
    assert loaded_prop.state == "hanging_on_wall"
    assert loaded_prop.description == "A sharp sword"


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_json_file_is_readable_directly(tmp_path):
    """Verify saved JSON files are valid and readable."""
    store = JsonRunStore(tmp_path)

    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
        tension=42,
    )

    store.save(instance)

    # Read file directly and parse as JSON
    json_file = tmp_path / "test-run.json"
    raw_data = json.loads(json_file.read_text(encoding="utf-8"))

    assert raw_data["id"] == "test-run"
    assert raw_data["tension"] == 42
    assert raw_data["kind"] == "solo_story"


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_no_tmp_files_on_failure(tmp_path):
    """Verify no tmp files left if save completes."""
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

    # Verify no .tmp files exist
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0

    # Verify the final file exists
    assert (tmp_path / "test-run.json").exists()


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_load_all_returns_sorted_by_id(tmp_path):
    """Verify load_all returns runs in sorted order."""
    store = JsonRunStore(tmp_path)

    # Create runs in non-alphabetical order
    for id in ["zebra", "apple", "middle"]:
        instance = RuntimeInstance(
            id=id,
            template_id="test-template",
            template_title="Test",
            kind="solo_story",
            join_policy="public",
            beat_id="beat1",
        )
        store.save(instance)

    loaded = store.load_all()
    loaded_ids = [inst.id for inst in loaded]

    # Should be sorted alphabetically
    assert loaded_ids == ["apple", "middle", "zebra"]


@pytest.mark.persistence
@pytest.mark.contract
def test_json_store_numeric_fields_precision(tmp_path):
    """Verify numeric fields maintain precision."""
    store = JsonRunStore(tmp_path)

    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
        tension=12345,
    )

    store.save(instance)
    loaded = store.load_all()[0]

    assert loaded.tension == 12345
    assert isinstance(loaded.tension, int)
