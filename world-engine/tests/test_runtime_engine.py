from __future__ import annotations

import pytest
from app.content.models import ParticipantMode
from app.runtime.engine import RuntimeEngine
from app.runtime.manager import RuntimeManager
from app.runtime.models import ParticipantState, RunStatus, RuntimeInstance
from story_runtime_core.experience_template_models import (
    ActionTemplate,
    BeatTemplate,
    Condition,
    ConditionType,
    Effect,
    EffectType,
    ExperienceKind,
    ExperienceTemplate,
    ExitTemplate,
    JoinPolicy,
    RoleTemplate,
    RoomTemplate,
)


def _build_test_solo_template():
    """Synthetic template for testing generic runtime mechanics (single-use actions, beat advancement)."""
    return ExperienceTemplate(
        id="test_solo_mechanics",
        title="Test Solo Mechanics",
        kind=ExperienceKind.SOLO_STORY,
        join_policy=JoinPolicy.OWNER_ONLY,
        summary="Synthetic fixture for testing generic runtime mechanics",
        max_humans=1,
        initial_beat_id="opening",
        tags=["test-fixture"],
        roles=[
            RoleTemplate(
                id="player",
                display_name="Player",
                description="Player role",
                mode=ParticipantMode.HUMAN,
                initial_room_id="hallway",
                can_join=True,
            ),
            RoleTemplate(
                id="npc",
                display_name="NPC",
                description="NPC role",
                mode=ParticipantMode.NPC,
                initial_room_id="living_room",
            ),
        ],
        rooms=[
            RoomTemplate(
                id="hallway",
                name="Hallway",
                description="Test hallway",
                exits=[ExitTemplate(direction="inside", target_room_id="living_room", label="Enter living room")],
                action_ids=["steady_breath"],
            ),
            RoomTemplate(
                id="living_room",
                name="Living Room",
                description="Test living room",
                exits=[ExitTemplate(direction="out", target_room_id="hallway", label="Exit to hallway")],
                action_ids=["offer_apology", "pour_rum"],
            ),
        ],
        props=[],
        actions=[
            ActionTemplate(
                id="steady_breath",
                label="Take a steady breath",
                description="Compose yourself",
                scope="room",
                single_use=True,
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="composed"),
                    Effect(type=EffectType.TRANSCRIPT, text="You take a deep breath."),
                ],
            ),
            ActionTemplate(
                id="offer_apology",
                label="Offer an apology",
                description="Say sorry",
                scope="room",
                effects=[
                    Effect(type=EffectType.SET_FLAG, key="apology_offered"),
                    Effect(type=EffectType.ADVANCE_BEAT, value="first_fracture"),
                    Effect(type=EffectType.TRANSCRIPT, text="You apologize."),
                ],
            ),
            ActionTemplate(
                id="pour_rum",
                label="Pour rum",
                description="Pour a drink",
                scope="room",
                available_if=[Condition(type=ConditionType.BEAT_EQUALS, value="first_fracture")],
                effects=[
                    Effect(type=EffectType.TRANSCRIPT, text="You pour rum."),
                ],
            ),
        ],
        beats=[
            BeatTemplate(id="opening", name="Opening", description="Start of story", summary="Opening beat"),
            BeatTemplate(id="first_fracture", name="First Fracture", description="Tension rises", summary="Fracture beat"),
        ],
    )


def _solo_manager_with_human(tmp_path, template_id="test_solo_mechanics"):
    manager = RuntimeManager(store_root=tmp_path)

    if template_id == "test_solo_mechanics":
        # For synthetic template, create run directly without manager
        template = _build_test_solo_template()
        run = RuntimeInstance(
            template_id=template.id,
            template_title=template.title,
            kind=template.kind,
            join_policy=template.join_policy,
            beat_id=template.initial_beat_id,
            status=RunStatus.RUNNING,
        )
        human = ParticipantState(
            role_id=template.roles[0].id,
            display_name="Solo",
            mode=ParticipantMode.HUMAN,
            current_room_id="hallway",
            account_id="acct:solo",
        )
        run.participants[human.id] = human
        engine = RuntimeEngine(template)
    else:
        run = manager.create_run(template_id, account_id="acct:solo", display_name="Solo")
        human = next(participant for participant in run.participants.values() if participant.account_id == "acct:solo")
        engine = RuntimeEngine(manager.get_template(run.template_id))

    return manager, run, human, engine



def test_move_changes_room_and_sets_story_flag(tmp_path):
    _, run, human, engine = _solo_manager_with_human(tmp_path)

    result = engine.apply_command(run, human.id, {"action": "move", "target_room_id": "living_room"})

    assert result.accepted
    assert human.current_room_id == "living_room"
    assert "entered_living_room" in run.flags
    assert run.transcript[-1].kind == "room_changed"



def test_move_rejects_unreachable_room(tmp_path):
    _, run, human, engine = _solo_manager_with_human(tmp_path)

    result = engine.apply_command(run, human.id, {"action": "move", "target_room_id": "noodle_bar"})

    assert not result.accepted
    assert result.reason == "That room is not reachable from here."



def test_empty_say_and_emote_commands_are_rejected(tmp_path):
    _, run, human, engine = _solo_manager_with_human(tmp_path)

    say_result = engine.apply_command(run, human.id, {"action": "say", "text": "   "})
    emote_result = engine.apply_command(run, human.id, {"action": "emote", "text": ""})

    assert not say_result.accepted
    assert say_result.reason == "Say what?"
    assert not emote_result.accepted
    assert emote_result.reason == "Emote what?"



def test_inspect_current_room_is_allowed(tmp_path):
    _, run, human, engine = _solo_manager_with_human(tmp_path)

    result = engine.apply_command(run, human.id, {"action": "inspect", "target_id": "hallway"})

    assert result.accepted
    assert run.transcript[-1].kind == "inspection_committed"
    assert run.transcript[-1].payload["target_id"] == "hallway"



def test_single_use_action_adds_flag_and_disappears_from_available_actions(tmp_path):
    # Use synthetic template with required test actions
    template = _build_test_solo_template()

    # Create run instance directly using template
    run = RuntimeInstance(
        template_id=template.id,
        template_title=template.title,
        kind=template.kind,
        join_policy=template.join_policy,
        beat_id=template.initial_beat_id,
        status=RunStatus.RUNNING,
    )

    # Add a participant
    human = ParticipantState(
        role_id=template.roles[0].id,
        display_name="Solo",
        mode=ParticipantMode.HUMAN,
        current_room_id="hallway",
        account_id="acct:solo",
    )
    run.participants[human.id] = human

    engine = RuntimeEngine(template)

    before_ids = {action["id"] for action in engine.available_actions(run, human)}
    result = engine.apply_command(run, human.id, {"action": "use_action", "action_id": "steady_breath"})
    after_ids = {action["id"] for action in engine.available_actions(run, human)}

    assert "steady_breath" in before_ids
    assert result.accepted
    assert "composed" in run.flags
    assert "used:steady_breath" in run.flags
    assert "steady_breath" not in after_ids



def test_conditional_story_actions_unlock_across_beats(tmp_path):
    # Use synthetic template with conditional actions and beat advancement
    template = _build_test_solo_template()

    run = RuntimeInstance(
        template_id=template.id,
        template_title=template.title,
        kind=template.kind,
        join_policy=template.join_policy,
        beat_id=template.initial_beat_id,
        status=RunStatus.RUNNING,
    )

    human = ParticipantState(
        role_id=template.roles[0].id,
        display_name="Solo",
        mode=ParticipantMode.HUMAN,
        current_room_id="hallway",
        account_id="acct:solo",
    )
    run.participants[human.id] = human

    engine = RuntimeEngine(template)

    move_result = engine.apply_command(run, human.id, {"action": "move", "target_room_id": "living_room"})
    assert move_result.accepted

    before_ids = {action["id"] for action in engine.available_actions(run, human)}
    apology_result = engine.apply_command(run, human.id, {"action": "use_action", "action_id": "offer_apology"})
    after_ids = {action["id"] for action in engine.available_actions(run, human)}

    assert "offer_apology" in before_ids
    assert "pour_rum" not in before_ids
    assert apology_result.accepted
    assert run.beat_id == "first_fracture"
    assert "apology_offered" in run.flags
    assert "pour_rum" in after_ids



def test_group_story_actions_are_blocked_while_lobby_is_active(tmp_path):
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    host = next(participant for participant in run.participants.values() if participant.account_id == "acct:host")
    engine = RuntimeEngine(manager.get_template(run.template_id))

    action_result = engine.apply_command(run, host.id, {"action": "use_action", "action_id": "group_open_statement"})
    move_result = engine.apply_command(run, host.id, {"action": "move", "target_room_id": "parlor"})

    assert not action_result.accepted
    assert action_result.reason == "Scene actions unlock after the host starts the group story."
    assert not move_result.accepted
    assert move_result.reason == "The group story is still in the lobby phase. Start the run first."



def test_group_story_npc_cycle_emits_house_ai_only_once(tmp_path):
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    host = next(participant for participant in run.participants.values() if participant.account_id == "acct:host")
    guest = manager.find_or_join_run(run.id, account_id="acct:guest", display_name="Guest", preferred_role_id="parent_a")
    engine = RuntimeEngine(manager.get_template(run.template_id))

    assert engine.apply_command(run, host.id, {"action": "set_ready", "ready": True}).accepted
    assert engine.apply_command(run, guest.id, {"action": "set_ready", "ready": True}).accepted
    assert engine.apply_command(run, host.id, {"action": "start_run"}).accepted
    assert run.status == RunStatus.RUNNING

    first_events = engine.run_npc_cycle(run)
    second_events = engine.run_npc_cycle(run)

    assert len(first_events) == 1
    assert first_events[0].type == "npc_reacted"
    assert second_events == []
    assert "house_ai_prompted" in run.flags



def test_open_world_patrol_flag_triggers_drone_npc_cycle(tmp_path):
    manager = RuntimeManager(store_root=tmp_path)
    run_id = next(run.id for run in manager.list_runs() if run.template_id == "better_tomorrow_district_alpha")
    run = manager.get_instance(run_id)
    citizen = manager.find_or_join_run(run.id, account_id="acct:citizen", display_name="Citizen")
    engine = manager.engines[run.id]

    action_result = engine.apply_command(run, citizen.id, {"action": "use_action", "action_id": "check_patrol_route"})
    npc_events = engine.run_npc_cycle(run)

    assert action_result.accepted
    assert "patrol_pattern_seen" in run.flags
    assert len(npc_events) == 1
    assert npc_events[0].type == "npc_reacted"
    assert "drone_announced" in run.flags
