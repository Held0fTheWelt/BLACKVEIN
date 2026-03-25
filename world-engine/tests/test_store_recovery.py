"""Runtime Recovery and Data Consistency Tests.

WAVE 8: Comprehensive runtime behavior and persistence testing.
Tests recovery after crashes: state consistency, data integrity, and reload cycles.

Mark: @pytest.mark.persistence, @pytest.mark.contract
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.runtime.manager import RuntimeManager
from app.runtime.models import (
    ParticipantState,
    RunStatus,
    RuntimeInstance,
)
from app.runtime.store import JsonRunStore


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_reload_after_save_cycle(tmp_path):
    """Verify instance state is consistent after save and reload."""
    # First session: create and modify
    manager1 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    run1.tension = 25
    run1.flags.add("test_flag")
    manager1.store.save(run1)

    # Second session: reload and verify
    manager2 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run2 = manager2.instances.get(run1.id)

    assert run2 is not None
    assert run2.tension == 25
    assert "test_flag" in run2.flags
    assert run2.template_id == run1.template_id


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_transcript_consistency(tmp_path):
    """Verify transcript remains consistent through recovery."""
    # Create and modify run
    manager1 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager1.engines[run1.id]

    participant = next(iter(run1.participants.values()))
    engine.apply_command(run1, participant.id, {"action": "say", "text": "First message"})
    engine.apply_command(run1, participant.id, {"action": "say", "text": "Second message"})

    transcript_count = len(run1.transcript)
    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run2 = manager2.instances.get(run1.id)

    assert len(run2.transcript) == transcript_count
    messages = [e.text for e in run2.transcript if "message" in (e.text or "")]
    assert len(messages) >= 2


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_participant_state_preserved(tmp_path):
    """Verify participant state is preserved through recovery."""
    manager1 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    participant = next(iter(run1.participants.values()))
    original_id = participant.id
    original_room = participant.current_room_id

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run2 = manager2.instances.get(run1.id)

    assert original_id in run2.participants
    recovered_participant = run2.participants[original_id]
    assert recovered_participant.display_name == participant.display_name
    assert recovered_participant.role_id == participant.role_id


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_props_state_preserved(tmp_path):
    """Verify prop states are preserved through recovery."""
    manager1 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    # Record prop states
    original_props = {pid: prop.state for pid, prop in run1.props.items()}

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run2 = manager2.instances.get(run1.id)

    # Verify states match
    for prop_id, original_state in original_props.items():
        assert prop_id in run2.props
        assert run2.props[prop_id].state == original_state


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_multiple_runs_independent(tmp_path):
    """Verify multiple runs are recovered independently."""
    manager1 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    run2 = manager1.create_run("god_of_carnage_solo", account_id="acct:bob", display_name="Bob")

    run1.tension = 10
    run2.tension = 50
    manager1.store.save(run1)
    manager1.store.save(run2)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path, store_backend="json")

    recovered1 = manager2.instances.get(run1.id)
    recovered2 = manager2.instances.get(run2.id)

    assert recovered1.tension == 10
    assert recovered2.tension == 50


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_metadata_preserved(tmp_path):
    """Verify custom metadata survives recovery."""
    manager1 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    run1.metadata["custom_key"] = "custom_value"
    run1.metadata["nested"] = {"data": 123}
    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run2 = manager2.instances.get(run1.id)

    assert run2.metadata["custom_key"] == "custom_value"
    assert run2.metadata["nested"]["data"] == 123


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_timestamps_preserved(tmp_path):
    """Verify timestamps are preserved correctly."""
    manager1 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    original_created = run1.created_at
    original_updated = run1.updated_at

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run2 = manager2.instances.get(run1.id)

    assert run2.created_at == original_created
    assert run2.updated_at == original_updated


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_flags_preserved(tmp_path):
    """Verify all flags are preserved through recovery."""
    manager1 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    run1.flags.add("flag1")
    run1.flags.add("flag2")
    run1.flags.add("used:action_xyz")

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path, store_backend="json")
    run2 = manager2.instances.get(run1.id)

    assert "flag1" in run2.flags
    assert "flag2" in run2.flags
    assert "used:action_xyz" in run2.flags
