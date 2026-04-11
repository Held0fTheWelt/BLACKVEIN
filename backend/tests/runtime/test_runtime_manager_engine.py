"""Real RuntimeManager / RuntimeEngine coverage (JsonRunStore, lobby, commands)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.content.builtins import load_builtin_templates
from app.content.models import ExperienceKind, ParticipantMode
from app.runtime.engine import RuntimeEngine
from app.runtime.manager import RuntimeManager
from app.runtime.models import LobbySeatState, ParticipantState, PropState, RunStatus, RuntimeInstance, TranscriptEntry
from app.runtime.store import JsonRunStore
from app.runtime.visibility import RuntimeVisibilityPolicy
from app.utils.html_sanitizer import sanitize_wiki_html


def _solo_instance(template_id: str = "god_of_carnage_solo") -> RuntimeInstance:
    template = load_builtin_templates()[template_id]
    humans = [r for r in template.roles if r.mode == ParticipantMode.HUMAN]
    human_role = humans[0]
    inst = RuntimeInstance(
        id=f"run-{template_id}",
        template_id=template.id,
        template_title=template.title,
        kind=template.kind,
        join_policy=template.join_policy,
        beat_id=template.initial_beat_id,
        status=RunStatus.RUNNING,
        persistent=template.persistent,
        owner_player_name="Owner",
        owner_account_id="owner-1",
    )
    p = ParticipantState(
        id="human-1",
        display_name="Owner",
        role_id=human_role.id,
        mode=ParticipantMode.HUMAN,
        current_room_id=human_role.initial_room_id,
        account_id="owner-1",
        character_id="char-1",
    )
    inst.participants[p.id] = p
    for prop in template.props:
        room_id = next(room.id for room in template.rooms if prop.id in room.prop_ids)
        inst.props[prop.id] = PropState(
            id=prop.id,
            name=prop.name,
            room_id=room_id,
            description=prop.description,
            state=prop.initial_state,
        )
    return inst


def test_manager_skips_persisted_run_with_unknown_template(tmp_path: Path):
    solo = _solo_instance()
    data = json.loads(solo.model_dump_json())
    data["template_id"] = "unknown_template_xyz"
    data["id"] = "orphan-run"
    (tmp_path / "orphan-run.json").write_text(json.dumps(data), encoding="utf-8")

    mgr = RuntimeManager(tmp_path)
    assert "orphan-run" not in mgr.instances


def test_manager_ensures_public_persistent_open_world(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    public_ids = [rid for rid in mgr.instances if rid.startswith("public-")]
    assert public_ids
    assert any("better_tomorrow" in rid for rid in public_ids)


def test_manager_normalize_instance_restores_lobby_seats(tmp_path: Path):
    template = load_builtin_templates()["apartment_confrontation_group"]
    raw = _solo_instance("apartment_confrontation_group")
    raw.status = RunStatus.LOBBY
    raw.lobby_seats = {}
    JsonRunStore(tmp_path).save(raw)

    mgr = RuntimeManager(tmp_path)
    loaded = mgr.instances[raw.id]
    assert loaded.lobby_seats
    human_seat_ids = {r.id for r in template.roles if r.mode == ParticipantMode.HUMAN and r.can_join}
    assert human_seat_ids.issubset(set(loaded.lobby_seats.keys()))


def test_manager_find_or_join_returns_existing_participant(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    run = mgr.create_run("god_of_carnage_solo", "Alice", account_id="acc-1", character_id="c1")
    rid = run.id
    p1 = mgr.find_or_join_run(rid, "Alice Renamed", account_id="acc-1", character_id="c1")
    p2 = mgr.find_or_join_run(rid, "Alice Renamed", account_id="acc-1", character_id="c1")
    assert p1.id == p2.id


def test_engine_group_lobby_payload_and_move_blocked_in_lobby():
    template = load_builtin_templates()["apartment_confrontation_group"]
    engine = RuntimeEngine(template)
    inst = _solo_instance("apartment_confrontation_group")
    inst.status = RunStatus.LOBBY
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)
    lobby = engine.build_lobby_payload(inst)
    assert lobby is not None
    assert "seats" in lobby

    res = engine.apply_command(inst, human.id, {"action": "move", "target_room_id": "parlor"})
    assert res.accepted is False
    assert "lobby" in (res.reason or "").lower()


def test_engine_solo_say_emote_and_unknown_command():
    template = load_builtin_templates()["god_of_carnage_solo"]
    engine = RuntimeEngine(template)
    inst = _solo_instance()
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)

    bad_say = engine.apply_command(inst, human.id, {"action": "say", "text": ""})
    assert bad_say.accepted is False

    bad_emote = engine.apply_command(inst, human.id, {"action": "emote", "text": "  "})
    assert bad_emote.accepted is False

    ok_say = engine.apply_command(inst, human.id, {"action": "say", "text": "hello"})
    assert ok_say.accepted is True

    unknown = engine.apply_command(inst, human.id, {"action": "nope", "x": 1})
    assert unknown.accepted is False
    assert "Unknown" in (unknown.reason or "")


def test_engine_move_invalid_exit():
    template = load_builtin_templates()["god_of_carnage_solo"]
    engine = RuntimeEngine(template)
    inst = _solo_instance()
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)
    res = engine.apply_command(inst, human.id, {"action": "move", "target_room_id": "nowhere"})
    assert res.accepted is False


def test_engine_set_ready_rejected_for_solo():
    template = load_builtin_templates()["god_of_carnage_solo"]
    engine = RuntimeEngine(template)
    inst = _solo_instance()
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)
    res = engine.apply_command(inst, human.id, {"action": "set_ready", "ready": True})
    assert res.accepted is False


def test_engine_start_run_rejected_for_solo_story():
    template = load_builtin_templates()["god_of_carnage_solo"]
    engine = RuntimeEngine(template)
    inst = _solo_instance()
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)
    res = engine.apply_command(inst, human.id, {"action": "start_run"})
    assert res.accepted is False
    assert "group" in (res.reason or "").lower()


def test_engine_use_action_unknown_id():
    template = load_builtin_templates()["god_of_carnage_solo"]
    engine = RuntimeEngine(template)
    inst = _solo_instance()
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)
    res = engine.apply_command(inst, human.id, {"action": "use_action", "action_id": "no_such_action"})
    assert res.accepted is False


def test_engine_use_action_prop_not_in_room_rejected():
    template = load_builtin_templates()["god_of_carnage_solo"]
    engine = RuntimeEngine(template)
    inst = _solo_instance()
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)
    assert human.current_room_id == "hallway"
    res = engine.apply_command(inst, human.id, {"action": "use_action", "action_id": "inspect_tulips"})
    assert res.accepted is False


def test_engine_ring_again_adds_tension():
    template = load_builtin_templates()["god_of_carnage_solo"]
    engine = RuntimeEngine(template)
    inst = _solo_instance()
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)
    before = inst.tension
    assert engine.apply_command(inst, human.id, {"action": "use_action", "action_id": "ring_again"}).accepted is True
    assert inst.tension > before


def test_engine_offer_apology_advances_beat():
    template = load_builtin_templates()["god_of_carnage_solo"]
    engine = RuntimeEngine(template)
    inst = _solo_instance()
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)
    assert engine.apply_command(inst, human.id, {"action": "move", "target_room_id": "living_room"}).accepted is True
    assert engine.apply_command(inst, human.id, {"action": "use_action", "action_id": "offer_apology"}).accepted is True
    assert inst.beat_id == "first_fracture"
    assert "apology_offered" in inst.flags


def _open_world_plaza_instance():
    template = load_builtin_templates()["better_tomorrow_district_alpha"]
    human_role = next(r for r in template.roles if r.mode == ParticipantMode.HUMAN)
    inst = RuntimeInstance(
        id="ow-test",
        template_id=template.id,
        template_title=template.title,
        kind=template.kind,
        join_policy=template.join_policy,
        beat_id=template.initial_beat_id,
        status=RunStatus.RUNNING,
        persistent=True,
    )
    p = ParticipantState(
        display_name="Walker",
        role_id=human_role.id,
        mode=ParticipantMode.HUMAN,
        current_room_id="plaza",
        account_id="u1",
    )
    inst.participants[p.id] = p
    for prop in template.props:
        room_id = next(room.id for room in template.rooms if prop.id in room.prop_ids)
        inst.props[prop.id] = PropState(
            id=prop.id,
            name=prop.name,
            room_id=room_id,
            description=prop.description,
            state=prop.initial_state,
        )
    return template, inst, p


def test_engine_open_world_snapshot_lobby_is_none():
    template, inst, human = _open_world_plaza_instance()
    engine = RuntimeEngine(template)
    snap = engine.build_snapshot(inst, human.id)
    assert snap.lobby is None


def test_engine_open_world_npc_cycle_patrol_drone_branch():
    template, inst, human = _open_world_plaza_instance()
    engine = RuntimeEngine(template)
    assert engine.apply_command(
        inst, human.id, {"action": "use_action", "action_id": "check_patrol_route"}
    ).accepted is True
    assert "patrol_pattern_seen" in inst.flags
    first = engine.run_npc_cycle(inst, human.id)
    assert len(first) > 0
    assert "drone_announced" in inst.flags
    second = engine.run_npc_cycle(inst, human.id)
    assert second == []


def test_wiki_html_sanitizer_guards_and_bleach_path():
    """Guard branches + bleach path (XSS cases also in tests/test_security_and_correctness.py)."""
    assert sanitize_wiki_html(None) == ""
    assert sanitize_wiki_html(99) == ""
    ws = "  \n"
    assert sanitize_wiki_html(ws) is ws
    cleaned = sanitize_wiki_html("<p>ok</p><script>x</script>")
    assert "script" not in cleaned.lower()
    assert "ok" in cleaned


def test_runtime_visibility_policy_all_methods():
    """RuntimeVisibilityPolicy maps template rooms, occupants, transcript tail, inspect rules."""
    template = load_builtin_templates()["god_of_carnage_solo"]
    inst = _solo_instance()
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)
    policy = RuntimeVisibilityPolicy(template)

    room_payload = policy.build_current_room_payload(inst, human)
    assert room_payload["id"] == human.current_room_id
    assert room_payload["name"] == template.room_map()[human.current_room_id].name

    occ = policy.visible_occupants(inst, human)
    assert len(occ) == 1
    assert occ[0]["participant_id"] == human.id
    assert occ[0]["display_name"] == human.display_name

    for i in range(7):
        inst.transcript.append(
            TranscriptEntry(kind="speech_committed", text=f"line{i}", payload={})
        )
    tail = policy.visible_transcript(inst, human)
    assert len(tail) == 5
    assert tail[-1].text == "line6"

    meta = policy.public_metadata(inst)
    assert meta["kind"] == inst.kind.value

    assert policy.can_inspect_target(inst, human, "tulips")
    assert policy.can_inspect_target(inst, human, human.current_room_id)
    assert not policy.can_inspect_target(inst, human, "nonexistent_prop_xyz")


def test_engine_solo_move_sets_flag_inspect_prop_and_room_npc_cycle():
    """Solo move to living_room, inspect targets, prop-linked actions, NPC cycle emits events."""
    template = load_builtin_templates()["god_of_carnage_solo"]
    engine = RuntimeEngine(template)
    inst = _solo_instance()
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)

    move = engine.apply_command(inst, human.id, {"action": "move", "target_room_id": "living_room"})
    assert move.accepted is True
    assert "entered_living_room" in inst.flags

    action_ids = {a["id"] for a in engine.available_actions(inst, human)}
    assert "inspect_tulips" in action_ids or "steady_breath" in action_ids

    bad_inspect = engine.apply_command(inst, human.id, {"action": "inspect", "target_id": "void"})
    assert bad_inspect.accepted is False

    ok_prop = engine.apply_command(inst, human.id, {"action": "inspect", "target_id": "tulips"})
    assert ok_prop.accepted is True

    ok_room = engine.apply_command(inst, human.id, {"action": "inspect", "target_id": "living_room"})
    assert ok_room.accepted is True

    events = engine.run_npc_cycle(inst, human.id)
    assert len(events) > 0

    assert engine.apply_command(inst, human.id, {"action": "move", "target_room_id": "bathroom"}).accepted is True
    wash = engine.apply_command(inst, human.id, {"action": "use_action", "action_id": "wash_face"})
    assert wash.accepted is True
    assert inst.props["washbasin"].state == "running"

    assert engine.apply_command(
        inst, human.id, {"action": "use_action", "action_id": "return_composure"}
    ).accepted is True
    assert human.current_room_id == "living_room"


def test_engine_group_use_action_blocked_in_lobby():
    template = load_builtin_templates()["apartment_confrontation_group"]
    engine = RuntimeEngine(template)
    inst = _solo_instance("apartment_confrontation_group")
    inst.status = RunStatus.LOBBY
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)
    res = engine.apply_command(inst, human.id, {"action": "use_action", "action_id": "group_ready_check"})
    assert res.accepted is False
    reason = (res.reason or "").lower()
    assert "lobby" in reason or "group story" in reason or "scene actions" in reason


def test_engine_steady_breath_effect_sets_flag_and_single_use():
    template = load_builtin_templates()["god_of_carnage_solo"]
    engine = RuntimeEngine(template)
    inst = _solo_instance()
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)
    first = engine.apply_command(inst, human.id, {"action": "use_action", "action_id": "steady_breath"})
    assert first.accepted is True
    assert "composed" in inst.flags
    second = engine.apply_command(inst, human.id, {"action": "use_action", "action_id": "steady_breath"})
    assert second.accepted is False


def test_engine_npc_instance_getter_raises_without_cycle_binding():
    engine = RuntimeEngine(load_builtin_templates()["god_of_carnage_solo"])
    with pytest.raises(RuntimeError, match="NPC cycle"):
        _ = engine._npc_instance


def test_manager_list_templates_and_get_run_details(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    assert mgr.list_templates()
    run = mgr.create_run("god_of_carnage_solo", "Host", account_id="h1")
    details = mgr.get_run_details(run.id)
    assert details["run"]["id"] == run.id
    assert details["template"]["id"] == "god_of_carnage_solo"


def test_manager_list_runs_includes_created_run(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    run = mgr.create_run("god_of_carnage_solo", "Listed", account_id="l1")
    summaries = mgr.list_runs()
    assert any(s.id == run.id for s in summaries)


def test_manager_find_or_join_same_display_name_without_account(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    run = mgr.create_run("god_of_carnage_solo", "Sam", account_id=None)
    again = mgr.find_or_join_run(run.id, "Sam", account_id=None)
    assert again.display_name == "Sam"


def test_manager_find_or_join_owner_only_denies_stranger(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    run = mgr.create_run("god_of_carnage_solo", "Owner", account_id="owner-acc")
    rid = run.id
    with pytest.raises(PermissionError):
        mgr.find_or_join_run(rid, "Stranger", account_id="other-acc")


def test_manager_owner_only_rejects_wrong_display_name_when_no_owner_account(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    run = mgr.create_run("god_of_carnage_solo", "SoloHost", account_id=None)
    rid = run.id
    with pytest.raises(PermissionError):
        mgr.find_or_join_run(rid, "SomeoneElse", account_id=None)


def test_manager_find_or_join_preferred_role_invalid_raises(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    run = mgr.create_run("apartment_confrontation_group", "Host", account_id="h1")
    with pytest.raises(RuntimeError, match="No joinable"):
        mgr.find_or_join_run(
            run.id, "X", account_id="x1", preferred_role_id="not_a_real_role_id"
        )


@pytest.mark.asyncio
async def test_manager_broadcast_snapshot_no_connections_is_noop(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    run = mgr.create_run("god_of_carnage_solo", "P", account_id="p1")
    await mgr.broadcast_snapshot(run.id)


def test_manager_find_or_join_preferred_role(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    run = mgr.create_run("apartment_confrontation_group", "Host", account_id="h1")
    rid = run.id
    guest = mgr.find_or_join_run(rid, "Guest", account_id="g1", preferred_role_id="parent_a")
    assert guest.role_id == "parent_a"


def test_engine_group_lobby_set_ready_and_start_run(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    run = mgr.create_run("apartment_confrontation_group", "Host", account_id="h1")
    rid = run.id
    inst = mgr.instances[rid]
    host_id = next(p.id for p in inst.participants.values() if p.account_id == "h1")
    guest = mgr.find_or_join_run(rid, "Guest", account_id="g1")
    engine = mgr.engines[rid]

    r1 = engine.apply_command(inst, host_id, {"action": "set_ready", "ready": True})
    r2 = engine.apply_command(inst, guest.id, {"action": "set_ready", "ready": True})
    assert r1.accepted and r2.accepted

    bad_start = engine.apply_command(inst, guest.id, {"action": "start_run"})
    assert bad_start.accepted is False

    start = engine.apply_command(inst, host_id, {"action": "start_run"})
    assert start.accepted is True
    assert inst.status == RunStatus.RUNNING

    again = engine.apply_command(inst, host_id, {"action": "start_run"})
    assert again.accepted is False

    npc_events = engine.run_npc_cycle(inst, host_id)
    assert npc_events
    assert "house_ai_prompted" in inst.flags


def test_manager_sync_seat_skips_when_lobby_seat_row_missing(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    run = mgr.create_run("god_of_carnage_solo", "A", account_id="a1")
    inst = mgr.instances[run.id]
    human = next(p for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)
    inst.lobby_seats.pop(human.role_id, None)
    mgr._sync_seat_from_participant(inst, human)


@pytest.mark.asyncio
async def test_manager_connect_process_rejected_command_broadcast(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    run = mgr.create_run("god_of_carnage_solo", "Player", account_id="p1")
    inst = mgr.instances[run.id]
    pid = next(p.id for p in inst.participants.values() if p.mode == ParticipantMode.HUMAN)

    ws = AsyncMock()
    await mgr.connect(run.id, pid, ws)
    assert inst.participants[pid].connected is True
    ws.send_json.assert_called()

    ws.reset_mock()
    mgr.connections[run.id].pop(pid, None)
    await mgr.process_command(run.id, pid, {"action": "invalid_action_xyz"})
    ws.send_json.assert_not_called()

    ws = AsyncMock()
    await mgr.connect(run.id, pid, ws)
    await mgr.process_command(run.id, pid, {"action": "invalid_action_xyz"})
    ws.send_json.assert_called()
    call_kw = ws.send_json.call_args[0][0]
    assert call_kw.get("type") == "command_rejected"

    ws2 = AsyncMock()
    ws2.send_json = AsyncMock(side_effect=RuntimeError("send failed"))
    mgr.connections[run.id][pid] = ws2
    await mgr.broadcast_snapshot(run.id)
    assert pid not in mgr.connections[run.id]


@pytest.mark.asyncio
async def test_manager_disconnect(tmp_path: Path):
    mgr = RuntimeManager(tmp_path)
    run = mgr.create_run("god_of_carnage_solo", "Player", account_id="p2")
    pid = next(p.id for p in mgr.instances[run.id].participants.values() if p.mode == ParticipantMode.HUMAN)
    ws = AsyncMock()
    await mgr.connect(run.id, pid, ws)
    await mgr.disconnect(run.id, pid)
    assert not mgr.instances[run.id].participants[pid].connected
