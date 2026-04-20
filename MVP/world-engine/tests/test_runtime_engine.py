from __future__ import annotations

from app.runtime.engine import RuntimeEngine
from app.runtime.manager import RuntimeManager
from app.runtime.models import RunStatus



def _solo_manager_with_human(tmp_path):
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:solo", display_name="Solo")
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
    _, run, human, engine = _solo_manager_with_human(tmp_path)

    before_ids = {action["id"] for action in engine.available_actions(run, human)}
    result = engine.apply_command(run, human.id, {"action": "use_action", "action_id": "steady_breath"})
    after_ids = {action["id"] for action in engine.available_actions(run, human)}

    assert "steady_breath" in before_ids
    assert result.accepted
    assert "composed" in run.flags
    assert "used:steady_breath" in run.flags
    assert "steady_breath" not in after_ids



def test_conditional_story_actions_unlock_across_beats(tmp_path):
    _, run, human, engine = _solo_manager_with_human(tmp_path)
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
