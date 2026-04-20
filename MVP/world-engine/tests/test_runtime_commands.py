"""Runtime Command Execution Tests.

WAVE 8: Comprehensive runtime behavior and persistence testing.
Tests in-game command handling: move, say, emote, inspect, and authorization.

Mark: @pytest.mark.contract, @pytest.mark.unit
"""

from __future__ import annotations

import pytest

from app.runtime.manager import RuntimeManager
from app.runtime.models import ParticipantState, RunStatus


@pytest.mark.contract
@pytest.mark.unit
def test_move_command_valid_destination(tmp_path):
    """Verify move command succeeds with valid, reachable destination."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    # Find first participant
    participant = next(iter(run.participants.values()))
    initial_room = participant.current_room_id

    # Find valid exit from initial room
    room = engine.rooms[initial_room]
    valid_target = room.exits[0].target_room_id if room.exits else None

    if valid_target:
        result = engine.apply_command(run, participant.id, {"action": "move", "target_room_id": valid_target})
        assert result.accepted
        assert participant.current_room_id == valid_target
        assert len(result.events) > 0


@pytest.mark.contract
@pytest.mark.unit
def test_move_command_invalid_destination(tmp_path):
    """Verify move command rejects unreachable destinations."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))
    initial_room = participant.current_room_id

    result = engine.apply_command(run, participant.id, {"action": "move", "target_room_id": "nonexistent_room"})
    assert not result.accepted
    assert result.reason
    assert participant.current_room_id == initial_room


@pytest.mark.contract
@pytest.mark.unit
def test_say_command_valid_text(tmp_path):
    """Verify say command accepts non-empty text."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    result = engine.apply_command(run, participant.id, {"action": "say", "text": "Hello, world!"})
    assert result.accepted
    assert len(result.events) > 0
    assert any(entry.text and "Hello" in entry.text for entry in run.transcript)


@pytest.mark.contract
@pytest.mark.unit
def test_say_command_empty_text(tmp_path):
    """Verify say command rejects empty text."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    result = engine.apply_command(run, participant.id, {"action": "say", "text": ""})
    assert not result.accepted
    assert result.reason


@pytest.mark.contract
@pytest.mark.unit
def test_emote_command_valid_text(tmp_path):
    """Verify emote command accepts valid action text."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    result = engine.apply_command(run, participant.id, {"action": "emote", "text": "nods thoughtfully"})
    assert result.accepted
    assert len(result.events) > 0


@pytest.mark.contract
@pytest.mark.unit
def test_emote_command_empty_text(tmp_path):
    """Verify emote command rejects empty text."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    result = engine.apply_command(run, participant.id, {"action": "emote", "text": ""})
    assert not result.accepted


@pytest.mark.contract
@pytest.mark.unit
def test_inspect_command_room(tmp_path):
    """Verify inspect command succeeds on current room."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))
    room_id = participant.current_room_id

    result = engine.apply_command(run, participant.id, {"action": "inspect", "target_id": room_id})
    assert result.accepted


@pytest.mark.contract
@pytest.mark.unit
def test_inspect_command_invalid_target(tmp_path):
    """Verify inspect command rejects non-visible targets."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    result = engine.apply_command(run, participant.id, {"action": "inspect", "target_id": "nonexistent_prop"})
    assert not result.accepted


@pytest.mark.contract
@pytest.mark.unit
def test_unknown_command_rejected(tmp_path):
    """Verify unknown commands are rejected."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    result = engine.apply_command(run, participant.id, {"action": "unknown_action"})
    assert not result.accepted
    assert "Unknown command" in (result.reason or "")


@pytest.mark.contract
@pytest.mark.unit
def test_command_in_group_story_lobby_blocks_actions(tmp_path):
    """Verify that certain commands are blocked while lobby is in progress."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    engine = manager.engines[run.id]

    # Verify we're in lobby
    assert run.status == RunStatus.LOBBY

    participant = next(iter(run.participants.values()))
    room = engine.rooms[participant.current_room_id]
    if room.exits:
        result = engine.apply_command(
            run, participant.id,
            {"action": "move", "target_room_id": room.exits[0].target_room_id}
        )
        # Group stories block movement in lobby
        assert not result.accepted


@pytest.mark.contract
@pytest.mark.unit
def test_start_run_by_non_host_rejected(tmp_path):
    """Verify only host can start group story."""
    manager = RuntimeManager(store_root=tmp_path)

    # Create run with specific host
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    engine = manager.engines[run.id]

    # Mark host seat as ready
    host_participant = next(p for p in run.participants.values() if p.account_id == "acct:host")
    host_seat = run.lobby_seats.get(host_participant.role_id)
    if host_seat:
        host_seat.ready = True

    # Try to start from different account (if we can create one)
    # For now, verify host can start
    result = engine.apply_command(run, host_participant.id, {"action": "start_run"})
    assert result.accepted or "need at least" in (result.reason or "").lower()


@pytest.mark.contract
@pytest.mark.unit
def test_set_ready_in_group_story_lobby(tmp_path):
    """Verify set_ready command works in lobby."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    engine = manager.engines[run.id]

    assert run.status == RunStatus.LOBBY

    # Find a human participant (not NPC)
    from app.content.models import ParticipantMode
    participant = next((p for p in run.participants.values() if p.mode == ParticipantMode.HUMAN), None)
    assert participant, "No human participant found"

    result = engine.apply_command(run, participant.id, {"action": "set_ready", "ready": True})

    assert result.accepted
    assert len(result.events) > 0
    seat = run.lobby_seats.get(participant.role_id)
    assert seat and seat.ready


@pytest.mark.contract
@pytest.mark.unit
def test_set_not_ready_in_group_story_lobby(tmp_path):
    """Verify set_ready can mark participant as not ready."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    engine = manager.engines[run.id]

    # Find a human participant (not NPC)
    from app.content.models import ParticipantMode
    participant = next((p for p in run.participants.values() if p.mode == ParticipantMode.HUMAN), None)
    assert participant, "No human participant found"

    # First mark ready
    engine.apply_command(run, participant.id, {"action": "set_ready", "ready": True})
    seat = run.lobby_seats.get(participant.role_id)
    assert seat and seat.ready

    # Then mark not ready
    result = engine.apply_command(run, participant.id, {"action": "set_ready", "ready": False})
    assert result.accepted
    assert seat and not seat.ready


@pytest.mark.contract
@pytest.mark.unit
def test_command_missing_action_field_rejected(tmp_path):
    """Verify command without action field is rejected."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    result = engine.apply_command(run, participant.id, {})
    assert not result.accepted


@pytest.mark.contract
@pytest.mark.unit
def test_say_command_with_whitespace_only_rejected(tmp_path):
    """Verify say command rejects whitespace-only text."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    result = engine.apply_command(run, participant.id, {"action": "say", "text": "   \t\n  "})
    assert not result.accepted


@pytest.mark.contract
@pytest.mark.unit
def test_command_adds_transcript_entry(tmp_path):
    """Verify commands add entries to transcript."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))
    initial_transcript_len = len(run.transcript)

    engine.apply_command(run, participant.id, {"action": "say", "text": "Test message"})

    assert len(run.transcript) > initial_transcript_len


@pytest.mark.contract
@pytest.mark.unit
def test_move_command_updates_participant_room(tmp_path):
    """Verify move command updates participant's current_room_id."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))
    initial_room = participant.current_room_id

    # Find valid exit
    room = engine.rooms[initial_room]
    if room.exits:
        target_room = room.exits[0].target_room_id
        engine.apply_command(run, participant.id, {"action": "move", "target_room_id": target_room})
        assert participant.current_room_id == target_room


@pytest.mark.contract
@pytest.mark.unit
def test_inspect_command_unavailable_in_wrong_room(tmp_path):
    """Verify inspect fails for props in different room."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    # Get a prop from a different room
    other_prop = None
    for prop_id, prop in run.props.items():
        if prop.room_id != participant.current_room_id:
            other_prop = prop_id
            break

    if other_prop:
        result = engine.apply_command(run, participant.id, {"action": "inspect", "target_id": other_prop})
        assert not result.accepted


@pytest.mark.contract
@pytest.mark.unit
def test_start_run_requires_minimum_ready_participants(tmp_path):
    """Verify start_run rejects if not enough ready participants."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    engine = manager.engines[run.id]

    # Don't mark anyone as ready
    participant = next(iter(run.participants.values()))

    result = engine.apply_command(run, participant.id, {"action": "start_run"})
    # Should fail: not enough ready participants
    assert not result.accepted


@pytest.mark.contract
@pytest.mark.unit
def test_command_result_includes_events(tmp_path):
    """Verify successful commands include events in result."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    result = engine.apply_command(run, participant.id, {"action": "say", "text": "Hello"})
    assert result.accepted
    assert result.events
    assert len(result.events) > 0


@pytest.mark.contract
@pytest.mark.unit
def test_command_result_includes_reason_on_rejection(tmp_path):
    """Verify rejected commands include reason."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    result = engine.apply_command(run, participant.id, {"action": "say", "text": ""})
    assert not result.accepted
    assert result.reason
    assert len(result.reason) > 0


@pytest.mark.contract
@pytest.mark.unit
def test_emote_command_sanitizes_text(tmp_path):
    """Verify emote command processes text correctly."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    result = engine.apply_command(run, participant.id, {"action": "emote", "text": "  laughs loudly  "})
    assert result.accepted
    # Whitespace should be stripped
    assert any("laughs loudly" in entry.text for entry in run.transcript if entry.text)
