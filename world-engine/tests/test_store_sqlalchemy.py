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
