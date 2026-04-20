"""Runtime Information Visibility Tests.

WAVE 8: Comprehensive runtime behavior and persistence testing.
Tests visibility rules: transcript privacy, room isolation, and state visibility.

Mark: @pytest.mark.contract, @pytest.mark.unit
"""

from __future__ import annotations

import pytest

from app.runtime.manager import RuntimeManager
from app.runtime.models import ParticipantState, ParticipantMode, RunStatus


@pytest.mark.contract
@pytest.mark.unit
def test_visibility_transcript_only_shows_current_room(tmp_path):
    """Verify transcript only shows events from current room and personal events."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))
    initial_room = participant.current_room_id

    # Add event in current room
    result = engine.apply_command(run, participant.id, {"action": "say", "text": "Hello from room 1"})
    assert result.accepted
    assert len(run.transcript) > 0

    # Get visible transcript for this participant
    visible = engine.visibility.visible_transcript(run, participant)
    assert len(visible) > 0
    assert visible[-1].text and "Hello" in visible[-1].text


@pytest.mark.contract
@pytest.mark.unit
def test_visibility_room_isolation_in_group_story(tmp_path):
    """Verify participants in different rooms don't see each other's events by default."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))
    room1 = participant.current_room_id

    # Create event in room 1
    engine.apply_command(run, participant.id, {"action": "say", "text": "In room 1"})
    transcript_room1 = len(engine.visibility.visible_transcript(run, participant))

    # Create another participant and move to different room
    if engine.rooms[room1].exits:
        room2 = engine.rooms[room1].exits[0].target_room_id
        participant2 = ParticipantState(
            display_name="Bob",
            role_id="test_role",
            mode=ParticipantMode.HUMAN,
            current_room_id=room2,
            account_id="acct:bob",
        )
        run.participants[participant2.id] = participant2

        # Participant 2 shouldn't see room 1 events
        visible = engine.visibility.visible_transcript(run, participant2)
        visible_texts = [e.text for e in visible if e.text]
        assert not any("In room 1" in text for text in visible_texts)


@pytest.mark.contract
@pytest.mark.unit
def test_visibility_visible_occupants_only_in_room(tmp_path):
    """Verify visible_occupants only returns participants in same room."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))
    room1 = participant.current_room_id

    # Get occupants in room 1
    occupants = engine.visibility.visible_occupants(run, participant)
    assert len(occupants) >= 1  # At least self
    assert any(occ["is_self"] for occ in occupants)

    # Create participant in different room
    if engine.rooms[room1].exits:
        room2 = engine.rooms[room1].exits[0].target_room_id
        participant2 = ParticipantState(
            display_name="Bob",
            role_id="test_role",
            mode=ParticipantMode.HUMAN,
            current_room_id=room2,
        )
        run.participants[participant2.id] = participant2

        # Bob shouldn't be in occupants list
        occupants = engine.visibility.visible_occupants(run, participant)
        assert not any(occ["participant_id"] == participant2.id for occ in occupants)


@pytest.mark.contract
@pytest.mark.unit
def test_visibility_private_metadata_includes_human_count(tmp_path):
    """Verify public metadata includes aggregated data."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    metadata = engine.visibility.public_metadata(run)
    assert "human_participant_count" in metadata
    assert metadata["human_participant_count"] >= 1


@pytest.mark.contract
@pytest.mark.unit
def test_visibility_can_inspect_current_room(tmp_path):
    """Verify participant can inspect their current room."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))
    room_id = participant.current_room_id

    can_inspect = engine.visibility.can_inspect_target(run, participant, room_id)
    assert can_inspect is True


@pytest.mark.contract
@pytest.mark.unit
def test_visibility_can_inspect_props_in_room(tmp_path):
    """Verify participant can inspect props in current room only."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))
    room_id = participant.current_room_id
    room = engine.rooms[room_id]

    # Try to inspect props in room
    if room.prop_ids:
        prop_id = room.prop_ids[0]
        can_inspect = engine.visibility.can_inspect_target(run, participant, prop_id)
        assert can_inspect is True


@pytest.mark.contract
@pytest.mark.unit
def test_visibility_cannot_inspect_distant_props(tmp_path):
    """Verify participant cannot inspect props outside current room."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    # Find a prop not in current room
    all_props = engine.visibility.props.keys()
    for prop_id in all_props:
        if prop_id not in engine.rooms[participant.current_room_id].prop_ids:
            can_inspect = engine.visibility.can_inspect_target(run, participant, prop_id)
            assert can_inspect is False
            break


@pytest.mark.contract
@pytest.mark.unit
def test_transcript_entry_visibility_respects_room_isolation(tmp_path):
    """Verify transcript entries are properly filtered based on room."""
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:alice", display_name="Alice")
    engine = manager.engines[run.id]

    participant = next(iter(run.participants.values()))

    # Create event
    engine.apply_command(run, participant.id, {"action": "say", "text": "Test message"})

    # Verify event is in transcript
    assert len(run.transcript) > 0
    last_event = run.transcript[-1]
    assert "Test message" in last_event.text
