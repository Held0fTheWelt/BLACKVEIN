"""SQLAlchemy Persistence Tests.

WAVE 8: Comprehensive runtime behavior and persistence testing.
Tests SqlAlchemyRunStore: initialization, persistence, reload, and error handling.

Mark: @pytest.mark.persistence, @pytest.mark.contract
"""

from __future__ import annotations

import pytest

from app.runtime.models import (
    RuntimeInstance,
    TranscriptEntry,
)
from app.runtime.store import SqlAlchemyRunStore


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_init_creates_table(tmp_path, sqlalchemy_available):
    """Verify SqlAlchemyRunStore creates table on init."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

    # Verify metadata was created
    assert store.metadata is not None
    assert store.runs is not None


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_save_persists_data(tmp_path, sqlalchemy_available):
    """Verify SqlAlchemyRunStore saves instances to database."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

    instance = RuntimeInstance(
        id="test-run-1",
        template_id="test-template",
        template_title="Test Template",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
    )

    store.save(instance)

    # Load and verify
    loaded = store.load_all()
    assert len(loaded) == 1
    assert loaded[0].id == "test-run-1"


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_load_all_multiple(tmp_path, sqlalchemy_available):
    """Verify load_all returns all persisted instances."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

    # Save multiple instances
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

    loaded = store.load_all()
    assert len(loaded) == 3


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_roundtrip_preserves_data(tmp_path, sqlalchemy_available):
    """Verify data is preserved through save/load cycle."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

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

    store.save(instance)
    loaded = store.load_all()[0]

    assert loaded.id == "test-run"
    assert loaded.template_id == "god_of_carnage_solo"
    assert loaded.tension == 42
    assert loaded.persistent is True
    assert "entered_living_room" in loaded.flags
    assert loaded.metadata["custom_key"] == "custom_value"


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_update_overwrites(tmp_path, sqlalchemy_available):
    """Verify updating instance overwrites previous data."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

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
    instance.tension = 75
    instance.flags.add("modified")
    store.save(instance)

    # Load and verify
    loaded = store.load_all()[0]
    assert loaded.tension == 75
    assert "modified" in loaded.flags


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_transcript_persists(tmp_path, sqlalchemy_available):
    """Verify transcript entries are persisted."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
    )

    entry1 = TranscriptEntry(
        kind="speech_committed",
        actor="Alice",
        text="Hello from DB",
        room_id="room1",
    )
    instance.transcript.append(entry1)

    store.save(instance)
    loaded = store.load_all()[0]

    assert len(loaded.transcript) == 1
    assert loaded.transcript[0].text == "Hello from DB"


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_describe_returns_url(tmp_path, sqlalchemy_available):
    """Verify describe returns backend name and connection URL."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

    desc = store.describe()
    assert desc["backend"] == "sqlalchemy"
    assert "sqlite" in desc["url"]


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_handles_special_characters(tmp_path, sqlalchemy_available):
    """Verify special characters in data are preserved in database."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

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
def test_sqlalchemy_store_large_transcript_persists(tmp_path, sqlalchemy_available):
    """Verify large transcripts are persisted correctly."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

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
def test_sqlalchemy_store_multiple_instances_independent(tmp_path, sqlalchemy_available):
    """Verify multiple instances don't interfere with each other."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

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

    store.save(instance1)
    store.save(instance2)

    loaded = store.load_all()
    assert len(loaded) == 2

    run1 = next(r for r in loaded if r.id == "run-1")
    run2 = next(r for r in loaded if r.id == "run-2")

    assert run1.tension == 10
    assert run2.tension == 20


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_preserves_participant_state(tmp_path, sqlalchemy_available):
    """Verify participant state is fully preserved in database."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    from app.runtime.models import ParticipantState

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
    )

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


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_preserves_prop_state(tmp_path, sqlalchemy_available):
    """Verify prop state is fully preserved in database."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    from app.runtime.models import PropState

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

    instance = RuntimeInstance(
        id="test-run",
        template_id="test-template",
        template_title="Test",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
    )

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


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_load_all_sorted_by_updated_at(tmp_path, sqlalchemy_available):
    """Verify load_all returns instances sorted by updated_at."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    from datetime import datetime, timedelta, timezone

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

    # Create instances with different timestamps
    base_time = datetime.now(timezone.utc)

    instance1 = RuntimeInstance(
        id="run-1",
        template_id="template-1",
        template_title="Run 1",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
        updated_at=base_time,
    )

    instance2 = RuntimeInstance(
        id="run-2",
        template_id="template-2",
        template_title="Run 2",
        kind="solo_story",
        join_policy="public",
        beat_id="beat1",
        updated_at=base_time + timedelta(seconds=1),
    )

    store.save(instance1)
    store.save(instance2)

    loaded = store.load_all()
    assert loaded[0].id == "run-1"
    assert loaded[1].id == "run-2"


@pytest.mark.persistence
@pytest.mark.contract
def test_sqlalchemy_store_numeric_fields_precision(tmp_path, sqlalchemy_available):
    """Verify numeric fields maintain precision in database."""
    if not sqlalchemy_available:
        pytest.skip("sqlalchemy not available")

    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    store = SqlAlchemyRunStore(db_url)

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
