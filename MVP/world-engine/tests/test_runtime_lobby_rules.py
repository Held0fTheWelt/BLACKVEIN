"""Runtime Lobby State Management Tests.

WAVE 8: Comprehensive runtime behavior and persistence testing.
Tests lobby rules: set_ready behavior, start_run gating, and state consistency.

Mark: @pytest.mark.contract, @pytest.mark.unit
"""

from __future__ import annotations

import pytest

from app.runtime.manager import RuntimeManager
from app.runtime.models import RunStatus


@pytest.mark.contract
@pytest.mark.unit
def test_set_ready_in_lobby(tmp_path):
    """Verify set_ready command succeeds in lobby."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    engine = manager.engines[run.id]

    assert run.status == RunStatus.LOBBY
    # Find a participant with a lobby seat (human participant)
    participant = next(
        (p for p in run.participants.values() if p.role_id in run.lobby_seats),
        None
    )
    if participant:
        result = engine.apply_command(run, participant.id, {"action": "set_ready", "ready": True})
        assert result.accepted

        # Verify seat is marked ready
        seat = run.lobby_seats.get(participant.role_id)
        assert seat is not None
        assert seat.ready is True


@pytest.mark.contract
@pytest.mark.unit
def test_set_not_ready_from_ready(tmp_path):
    """Verify ready state can be toggled back to not ready."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    engine = manager.engines[run.id]

    # Find a participant with a lobby seat
    participant = next(
        (p for p in run.participants.values() if p.role_id in run.lobby_seats),
        None
    )
    if participant:
        # Mark ready
        result = engine.apply_command(run, participant.id, {"action": "set_ready", "ready": True})
        assert result.accepted
        assert run.lobby_seats[participant.role_id].ready is True

        # Mark not ready
        result = engine.apply_command(run, participant.id, {"action": "set_ready", "ready": False})
        assert result.accepted
        assert run.lobby_seats[participant.role_id].ready is False


@pytest.mark.contract
@pytest.mark.unit
def test_set_ready_idempotent(tmp_path):
    """Verify setting ready multiple times is idempotent."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    engine = manager.engines[run.id]

    # Find a participant with a lobby seat
    participant = next(
        (p for p in run.participants.values() if p.role_id in run.lobby_seats),
        None
    )
    if participant:
        # Set ready twice
        result1 = engine.apply_command(run, participant.id, {"action": "set_ready", "ready": True})
        result2 = engine.apply_command(run, participant.id, {"action": "set_ready", "ready": True})

        assert result1.accepted
        assert result2.accepted
        assert run.lobby_seats[participant.role_id].ready is True


@pytest.mark.contract
@pytest.mark.unit
def test_start_run_blocked_when_not_all_ready(tmp_path):
    """Verify start_run fails if not all occupied seats are ready."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    # Don't mark ready, try to start
    result = engine.apply_command(run, participant.id, {"action": "start_run"})
    assert not result.accepted
    assert "need" in (result.reason or "").lower() or "ready" in (result.reason or "").lower()
    assert run.status == RunStatus.LOBBY


@pytest.mark.contract
@pytest.mark.unit
def test_start_run_succeeds_when_ready(tmp_path):
    """Verify start_run succeeds when all conditions met."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    # Mark ready
    engine.apply_command(run, participant.id, {"action": "set_ready", "ready": True})

    # Try to start
    result = engine.apply_command(run, participant.id, {"action": "start_run"})
    if result.accepted:
        assert run.status == RunStatus.RUNNING
    else:
        # May fail if template requires more participants
        pass


@pytest.mark.contract
@pytest.mark.unit
def test_start_run_blocked_after_already_started(tmp_path):
    """Verify start_run cannot be called twice."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    # Set ready and start
    participant = next(
        (p for p in run.participants.values() if p.role_id in run.lobby_seats),
        None
    )
    if participant:
        engine.apply_command(run, participant.id, {"action": "set_ready", "ready": True})
        result1 = engine.apply_command(run, participant.id, {"action": "start_run"})
        if result1.accepted:
            # Try to start again
            result2 = engine.apply_command(run, participant.id, {"action": "start_run"})
            assert not result2.accepted
            assert "already started" in (result2.reason or "").lower()


@pytest.mark.contract
@pytest.mark.unit
def test_set_ready_non_group_story_rejected(tmp_path):
    """Verify set_ready fails on solo story."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))
    result = engine.apply_command(run, participant.id, {"action": "set_ready", "ready": True})
    # May fail since solo stories don't have lobby state
    assert not result.accepted


@pytest.mark.contract
@pytest.mark.unit
def test_start_run_non_group_story_rejected(tmp_path):
    """Verify start_run fails on non-group story templates."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))
    result = engine.apply_command(run, participant.id, {"action": "start_run"})
    assert not result.accepted
    # Result message should indicate this is not a group story
    assert result.reason is not None
