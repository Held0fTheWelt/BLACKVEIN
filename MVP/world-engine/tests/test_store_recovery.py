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
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    run1.tension = 25
    run1.flags.add("test_flag")
    manager1.store.save(run1)

    # Second session: reload and verify
    manager2 = RuntimeManager(store_root=tmp_path)
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
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager1.engines[run1.id]

    participant = next(iter(run1.participants.values()))
    engine.apply_command(run1, participant.id, {"action": "say", "text": "First message"})
    engine.apply_command(run1, participant.id, {"action": "say", "text": "Second message"})

    transcript_count = len(run1.transcript)
    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    assert len(run2.transcript) == transcript_count
    messages = [e.text for e in run2.transcript if "message" in (e.text or "")]
    assert len(messages) >= 2


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_participant_state_preserved(tmp_path):
    """Verify participant state is preserved through recovery."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    participant = next(iter(run1.participants.values()))
    original_id = participant.id
    original_room = participant.current_room_id

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    assert original_id in run2.participants
    recovered_participant = run2.participants[original_id]
    assert recovered_participant.display_name == participant.display_name
    assert recovered_participant.role_id == participant.role_id


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_props_state_preserved(tmp_path):
    """Verify prop states are preserved through recovery."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    # Record prop states
    original_props = {pid: prop.state for pid, prop in run1.props.items()}

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    # Verify states match
    for prop_id, original_state in original_props.items():
        assert prop_id in run2.props
        assert run2.props[prop_id].state == original_state


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_multiple_runs_independent(tmp_path):
    """Verify multiple runs are recovered independently."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    run2 = manager1.create_run("god_of_carnage_solo", account_id="acct:bob", display_name="Bob")

    run1.tension = 10
    run2.tension = 50
    manager1.store.save(run1)
    manager1.store.save(run2)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)

    recovered1 = manager2.instances.get(run1.id)
    recovered2 = manager2.instances.get(run2.id)

    assert recovered1.tension == 10
    assert recovered2.tension == 50


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_metadata_preserved(tmp_path):
    """Verify custom metadata survives recovery."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    run1.metadata["custom_key"] = "custom_value"
    run1.metadata["nested"] = {"data": 123}
    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    assert run2.metadata["custom_key"] == "custom_value"
    assert run2.metadata["nested"]["data"] == 123


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_timestamps_preserved(tmp_path):
    """Verify timestamps are preserved correctly."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    original_created = run1.created_at
    original_updated = run1.updated_at

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    assert run2.created_at == original_created
    assert run2.updated_at == original_updated


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_flags_preserved(tmp_path):
    """Verify all flags are preserved through recovery."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    run1.flags.add("flag1")
    run1.flags.add("flag2")
    run1.flags.add("used:action_xyz")

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    assert "flag1" in run2.flags
    assert "flag2" in run2.flags
    assert "used:action_xyz" in run2.flags


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_partial_write_scenario(tmp_path):
    """Verify recovery from partial write (incomplete file)."""
    # First: Create a complete run
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    run1.tension = 25
    manager1.store.save(run1)

    # Simulate partial write: truncate the JSON file
    json_file = tmp_path / f"{run1.id}.json"
    content = json_file.read_text(encoding="utf-8")
    json_file.write_text(content[:len(content)//2], encoding="utf-8")

    # Reload should skip the corrupted file
    manager2 = RuntimeManager(store_root=tmp_path)

    # The corrupted run should not be loaded
    recovered = manager2.instances.get(run1.id)
    assert recovered is None


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_lobby_seats_preserved(tmp_path):
    """Verify lobby seat state is preserved through recovery."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    # Record lobby seats
    original_seats = dict(run1.lobby_seats)

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    # Verify lobby seats match
    assert len(run2.lobby_seats) == len(original_seats)
    for seat_id, seat in original_seats.items():
        assert seat_id in run2.lobby_seats
        loaded_seat = run2.lobby_seats[seat_id]
        assert loaded_seat.role_id == seat.role_id


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_status_field_preserved(tmp_path):
    """Verify run status is preserved through recovery."""
    from app.runtime.models import RunStatus

    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    # Record initial status
    original_status = run1.status
    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    # Status should be preserved
    assert run2.status == original_status


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_join_policy_preserved(tmp_path):
    """Verify join policy is preserved through recovery."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    assert run2.join_policy == run1.join_policy


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_persistent_flag_preserved(tmp_path):
    """Verify persistent flag is preserved."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    run1.persistent = True
    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    assert run2.persistent is True


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_owner_account_preserved(tmp_path):
    """Verify owner account ID is preserved."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    assert run2.owner_account_id == run1.owner_account_id


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_beat_id_preserved(tmp_path):
    """Verify beat_id is preserved through recovery."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    assert run2.beat_id == run1.beat_id


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_consistent_across_multiple_cycles(tmp_path):
    """Verify data remains consistent through multiple save/load cycles."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    # Original state - set these after creation
    original_id = run.id
    original_template = run.template_id

    for cycle in range(3):
        # Set unique flag for this cycle
        run.flags.add(f"cycle_{cycle}")
        manager.store.save(run)

        # Reload
        manager2 = RuntimeManager(store_root=tmp_path)
        run = manager2.instances.get(original_id)

        # Verify basic fields preserved
        assert run.id == original_id
        assert run.template_id == original_template
        assert f"cycle_{cycle}" in run.flags

        manager = manager2


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_empty_collections_preserved(tmp_path):
    """Verify empty collections are handled correctly."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    # At creation, these should be empty
    assert len(run1.transcript) == 0
    assert len(run1.flags) == 0

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    assert len(run2.transcript) == 0
    assert len(run2.flags) == 0


@pytest.mark.persistence
@pytest.mark.contract
def test_recovery_template_id_preserved_enables_engine_reload(tmp_path):
    """Verify template_id is preserved so engine can be reloaded."""
    manager1 = RuntimeManager(store_root=tmp_path)
    run1 = manager1.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")

    manager1.store.save(run1)

    # Reload
    manager2 = RuntimeManager(store_root=tmp_path)
    run2 = manager2.instances.get(run1.id)

    # Verify we can get the template
    assert run2.template_id in manager2.templates
    engine = manager2.engines.get(run2.id)
    assert engine is not None
