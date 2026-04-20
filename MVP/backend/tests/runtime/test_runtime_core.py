from __future__ import annotations

import asyncio
import importlib
import json
import sys
import types
from pathlib import Path

import pytest

from app.content.builtins import load_builtin_templates
from app.content.models import ExperienceKind, JoinPolicy, ParticipantMode
from app.runtime.models import (
    LobbySeatState,
    ParticipantState,
    PropState,
    PublicRunSummary,
    RunStatus,
    RuntimeEvent,
    RuntimeInstance,
    RuntimeSnapshot,
    TranscriptEntry,
)
from app.runtime.npc_behaviors import RuntimeNpcDirector
from app.runtime.store import JsonRunStore, SqlAlchemyRunStore, build_run_store


class _FakeVisibilityPolicy:
    def __init__(self, template):
        self.template = template

    def build_current_room_payload(self, instance, viewer):
        room = self.template.room_map()[viewer.current_room_id]
        return {"id": room.id, "name": room.name}

    def visible_occupants(self, instance, viewer):
        return [{"participant_id": viewer.id, "display_name": viewer.display_name}]

    def visible_transcript(self, instance, viewer):
        return instance.transcript[-5:]

    def public_metadata(self, instance):
        return {"kind": instance.kind.value}

    def can_inspect_target(self, instance, actor, target_id):
        return target_id in instance.props or target_id == actor.current_room_id


class _FakeRuntimeEngine:
    def __init__(self, template):
        self.template = template
        self.commands = []

    def build_snapshot(self, instance, participant_id):
        return types.SimpleNamespace(model_dump=lambda mode="json": {"run_id": instance.id, "participant_id": participant_id})

    def build_lobby_payload(self, instance):
        return {"status": instance.status.value, "seats": len(instance.lobby_seats)}

    def apply_command(self, instance, participant_id, command):
        self.commands.append((instance.id, participant_id, command))
        accepted = not command.get("reject")
        if accepted:
            return types.SimpleNamespace(accepted=True, reason=None)
        return types.SimpleNamespace(accepted=False, reason="rejected")

    def run_npc_cycle(self, instance, trigger_actor_id=None):
        instance.flags.add("npc-cycle")
        return []


class _FakeWebSocket:
    def __init__(self, fail_on_send: bool = False):
        self.accepted = False
        self.sent = []
        self.fail_on_send = fail_on_send

    async def accept(self):
        self.accepted = True

    async def send_json(self, payload):
        if self.fail_on_send:
            raise RuntimeError("socket closed")
        self.sent.append(payload)


def _runtime_instance_for(template_id: str) -> RuntimeInstance:
    template = load_builtin_templates()[template_id]
    humans = [role for role in template.roles if role.mode == ParticipantMode.HUMAN]
    human_role = humans[0]
    instance = RuntimeInstance(
        id=f"run-{template_id}",
        template_id=template.id,
        template_title=template.title,
        kind=template.kind,
        join_policy=template.join_policy,
        beat_id=template.initial_beat_id,
        status=RunStatus.LOBBY if template.kind != ExperienceKind.OPEN_WORLD else RunStatus.RUNNING,
        persistent=template.persistent,
        owner_player_name="Owner",
        owner_account_id="owner-1",
    )
    participant = ParticipantState(
        id="human-1",
        display_name="Owner",
        role_id=human_role.id,
        mode=ParticipantMode.HUMAN,
        current_room_id=human_role.initial_room_id,
        account_id="owner-1",
        character_id="char-1",
    )
    instance.participants[participant.id] = participant
    for prop in template.props:
        room_id = next(room.id for room in template.rooms if prop.id in room.prop_ids)
        instance.props[prop.id] = PropState(
            id=prop.id,
            name=prop.name,
            room_id=room_id,
            description=prop.description,
            state=prop.initial_state,
        )
    for role in humans:
        instance.lobby_seats[role.id] = LobbySeatState(role_id=role.id, role_display_name=role.display_name)
    instance.lobby_seats[human_role.id].participant_id = participant.id
    instance.lobby_seats[human_role.id].occupant_display_name = participant.display_name
    instance.lobby_seats[human_role.id].reserved_for_account_id = participant.account_id
    instance.lobby_seats[human_role.id].reserved_for_display_name = participant.display_name
    instance.lobby_seats[human_role.id].ready = template.kind == ExperienceKind.SOLO_STORY
    return instance


def _import_engine_module(monkeypatch):
    fake_visibility = types.ModuleType("app.runtime.visibility")
    fake_visibility.RuntimeVisibilityPolicy = _FakeVisibilityPolicy
    monkeypatch.setitem(sys.modules, "app.runtime.visibility", fake_visibility)
    sys.modules.pop("app.runtime.engine", None)
    return importlib.import_module("app.runtime.engine")


def _import_manager_module(monkeypatch):
    fake_engine = types.ModuleType("app.runtime.engine")
    fake_engine.RuntimeEngine = _FakeRuntimeEngine
    monkeypatch.setitem(sys.modules, "app.runtime.engine", fake_engine)
    sys.modules.pop("app.runtime.manager", None)
    return importlib.import_module("app.runtime.manager")


def test_json_run_store_roundtrip_and_invalid_files(tmp_path):
    store = JsonRunStore(tmp_path)
    instance = _runtime_instance_for("god_of_carnage_solo")
    store.save(instance)
    assert store.path_for(instance.id).exists()

    (tmp_path / "broken.json").write_text("{broken", encoding="utf-8")
    loaded = store.load_all()
    assert len(loaded) == 1
    assert loaded[0].id == instance.id
    assert store.describe() == {"backend": "json", "root": str(tmp_path)}

    with pytest.raises(ValueError, match="Invalid run_id"):
        store.path_for("../../escape")


def test_sqlalchemy_run_store_roundtrip_and_factory(tmp_path):
    url = f"sqlite:///{tmp_path / 'runtime.sqlite'}"
    store = SqlAlchemyRunStore(url)
    first = _runtime_instance_for("god_of_carnage_solo")
    second = _runtime_instance_for("apartment_confrontation_group")
    second.id = "run-2"
    store.save(first)
    store.save(second)

    loaded = store.load_all()
    assert [item.id for item in loaded] == [first.id, second.id]
    assert store.describe() == {"backend": "sqlalchemy", "url": url}

    json_store = build_run_store(root=tmp_path, backend="json")
    assert isinstance(json_store, JsonRunStore)

    sql_store = build_run_store(root=tmp_path, backend="postgresql", url=url)
    assert isinstance(sql_store, SqlAlchemyRunStore)

    with pytest.raises(ValueError, match="RUN_STORE_URL"):
        build_run_store(root=tmp_path, backend="sqlalchemy")

    with pytest.raises(ValueError, match="Unsupported"):
        build_run_store(root=tmp_path, backend="memory")


def test_runtime_model_defaults_and_npc_director_cycles():
    participant = ParticipantState(
        display_name="Alice",
        role_id="visitor",
        mode=ParticipantMode.HUMAN,
        current_room_id="hallway",
        account_id="acct-1",
    )
    assert participant.seat_owner_account_id == "acct-1"
    assert participant.seat_owner_display_name == "Alice"
    assert participant.seat_owner == "acct-1"

    observer = ParticipantState(
        display_name="Observer",
        role_id="observer",
        mode=ParticipantMode.HUMAN,
        current_room_id="hallway",
        seat_owner="Seat Name",
    )
    assert observer.seat_owner_display_name == "Seat Name"
    assert observer.seat_owner == "Seat Name"

    summary = PublicRunSummary(
        id="run-1",
        template_id="solo",
        template_title="Solo",
        kind=ExperienceKind.SOLO_STORY,
        join_policy=JoinPolicy.OWNER_ONLY,
        persistent=False,
        status=RunStatus.RUNNING,
        connected_humans=1,
        total_humans=1,
        tension=2,
        beat_id="courtesy",
        owner_player_name="Alice",
    )
    assert summary.open_human_seats == 0
    assert summary.ready_human_seats == 0

    snapshot = RuntimeSnapshot(
        run_id="run-1",
        template_id="solo",
        template_title="Solo",
        kind=ExperienceKind.SOLO_STORY,
        join_policy=JoinPolicy.OWNER_ONLY,
        status=RunStatus.RUNNING,
        beat_id="courtesy",
        tension=1,
        viewer_participant_id="p1",
        viewer_room_id="hallway",
        viewer_role_id="visitor",
        viewer_display_name="Alice",
        available_actions=[],
        transcript_tail=[TranscriptEntry(kind="note", text="hello")],
        metadata={"kind": "solo_story"},
    )
    assert snapshot.transcript_tail[0].text == "hello"

    emitted = []

    def emit(event_type, text, actor, room_id, payload):
        event = RuntimeEvent(type=event_type, run_id="run-1", payload=payload)
        emitted.append((text, actor, room_id))
        return [event]

    templates = load_builtin_templates()
    solo_instance = _runtime_instance_for("god_of_carnage_solo")
    solo_director = RuntimeNpcDirector(templates["god_of_carnage_solo"], emit)
    solo_events = solo_director.run_cycle(solo_instance)
    assert solo_events == []

    solo_instance.flags.add("entered_living_room")
    solo_events = solo_director.run_cycle(solo_instance)
    assert len(solo_events) == 2
    assert "courtesy_intro_done" in solo_instance.flags

    solo_instance.beat_id = "first_fracture"
    fracture_events = solo_director.run_cycle(solo_instance)
    assert len(fracture_events) == 1
    assert "fracture_exchange_done" in solo_instance.flags

    solo_instance.beat_id = "unmasked"
    assert len(solo_director.run_cycle(solo_instance)) == 1
    solo_instance.beat_id = "collapse"
    assert len(solo_director.run_cycle(solo_instance)) == 1

    group_instance = _runtime_instance_for("apartment_confrontation_group")
    group_director = RuntimeNpcDirector(templates["apartment_confrontation_group"], emit)
    assert group_director.run_cycle(group_instance) == []
    group_instance.status = RunStatus.RUNNING
    assert len(group_director.run_cycle(group_instance)) == 1
    assert group_director.run_cycle(group_instance) == []

    open_world = _runtime_instance_for("better_tomorrow_district_alpha")
    open_world.flags.add("patrol_pattern_seen")
    open_director = RuntimeNpcDirector(templates["better_tomorrow_district_alpha"], emit)
    assert len(open_director.run_cycle(open_world)) == 1
    assert open_director.run_cycle(open_world) == []


def test_runtime_engine_commands_and_snapshot(monkeypatch):
    engine_module = _import_engine_module(monkeypatch)
    template = load_builtin_templates()["god_of_carnage_solo"]
    engine = engine_module.RuntimeEngine(template)
    instance = _runtime_instance_for("god_of_carnage_solo")
    actor = next(iter(instance.participants.values()))

    available = engine.available_actions(instance, actor)
    assert any(action["id"] == "steady_breath" for action in available)

    snapshot = engine.build_snapshot(instance, actor.id)
    assert snapshot.viewer_display_name == "Owner"
    assert snapshot.metadata["store_backend"] == "unknown"

    assert engine.apply_command(instance, actor.id, {"action": "unknown"}).accepted is False
    assert engine.apply_command(instance, actor.id, {"action": "say", "text": ""}).reason == "Say what?"
    assert engine.apply_command(instance, actor.id, {"action": "emote", "text": ""}).reason == "Emote what?"

    moved = engine.apply_command(instance, actor.id, {"action": "move", "target_room_id": "living_room"})
    assert moved.accepted is True
    assert actor.current_room_id == "living_room"
    assert "entered_living_room" in instance.flags

    inspect_prop = engine.apply_command(instance, actor.id, {"action": "inspect", "target_id": "tulips"})
    assert inspect_prop.accepted is True

    inspect_room = engine.apply_command(instance, actor.id, {"action": "inspect", "target_id": "living_room"})
    assert inspect_room.accepted is True

    blocked = engine.apply_command(instance, actor.id, {"action": "inspect", "target_id": "missing"})
    assert blocked.accepted is False

    used = engine.apply_command(instance, actor.id, {"action": "use_action", "action_id": "steady_breath"})
    assert used.accepted is True
    assert "used:steady_breath" in instance.flags
    assert engine.apply_command(instance, actor.id, {"action": "use_action", "action_id": "steady_breath"}).accepted is False

    unknown_action = engine.apply_command(instance, actor.id, {"action": "use_action", "action_id": "missing"})
    assert unknown_action.reason == "Unknown action."

    instance.flags.add("patrol_pattern_seen")
    npc_events = engine.run_npc_cycle(_runtime_instance_for("better_tomorrow_district_alpha"))
    assert npc_events == [] or isinstance(npc_events, list)

    with pytest.raises(RuntimeError, match="NPC cycle invoked"):
        _ = engine._npc_instance


def test_runtime_engine_group_story_ready_and_start(monkeypatch):
    engine_module = _import_engine_module(monkeypatch)
    template = load_builtin_templates()["apartment_confrontation_group"]
    engine = engine_module.RuntimeEngine(template)
    instance = _runtime_instance_for("apartment_confrontation_group")
    actor = next(iter(instance.participants.values()))

    # Add a second participant for the group story (requires at least 2 to start)
    other_humans = [role for role in template.roles if role.mode == ParticipantMode.HUMAN and role.id != actor.role_id]
    if other_humans:
        other_role = other_humans[0]
        other_participant = ParticipantState(
            id="human-2",
            display_name="Other Player",
            role_id=other_role.id,
            mode=ParticipantMode.HUMAN,
            current_room_id=other_role.initial_room_id,
            account_id="other-1",
            character_id="char-2",
        )
        instance.participants[other_participant.id] = other_participant
        instance.lobby_seats[other_role.id].participant_id = other_participant.id
        instance.lobby_seats[other_role.id].occupant_display_name = other_participant.display_name
        instance.lobby_seats[other_role.id].reserved_for_account_id = other_participant.account_id
        instance.lobby_seats[other_role.id].reserved_for_display_name = other_participant.display_name

    blocked_move = engine.apply_command(instance, actor.id, {"action": "move", "target_room_id": "living_room"})
    assert blocked_move.reason.startswith("The group story is still in the lobby")

    blocked_action = engine.apply_command(instance, actor.id, {"action": "use_action", "action_id": "steady_breath"})
    assert blocked_action.reason.startswith("Scene actions unlock")

    ready = engine.apply_command(instance, actor.id, {"action": "set_ready", "ready": True})
    assert ready.accepted is True
    assert instance.lobby_seats[actor.role_id].ready is True

    # Mark the second participant as ready too (required to start group story)
    if other_humans:
        instance.lobby_seats[other_role.id].ready = True

    started = engine.apply_command(instance, actor.id, {"action": "start_run"})
    assert started.accepted is True
    assert instance.status == RunStatus.RUNNING


def test_runtime_manager_core_flow(monkeypatch, tmp_path):
    manager_module = _import_manager_module(monkeypatch)
    manager = manager_module.RuntimeManager(tmp_path, store_backend="json")

    assert any(run_id.startswith("public-") for run_id in manager.instances)

    solo = manager.create_run("god_of_carnage_solo", display_name="Alice", account_id="acct-1", character_id="char-1")
    assert solo.status == RunStatus.RUNNING
    assert solo.owner_player_name == "Alice"

    snapshot = manager.build_snapshot(solo.id, next(iter(solo.participants)))
    assert snapshot.model_dump()["run_id"] == solo.id

    details = manager.get_run_details(solo.id)
    assert details["store"]["backend"] == "json"
    assert details["template"]["id"] == "god_of_carnage_solo"

    joined = manager.find_or_join_run(solo.id, display_name="Alice", account_id="acct-1")
    assert joined.display_name == "Alice"

    with pytest.raises(PermissionError, match="private"):
        manager.find_or_join_run(solo.id, display_name="Bob", account_id="acct-2")

    summaries = manager.list_runs()
    assert any(summary.id == solo.id for summary in summaries)

    assert manager_module.account_id_or_none(None) is None
    assert manager_module.account_id_or_none(123) == "123"


@pytest.mark.asyncio
async def test_runtime_manager_connect_disconnect_and_process(monkeypatch, tmp_path):
    manager_module = _import_manager_module(monkeypatch)
    manager = manager_module.RuntimeManager(tmp_path, store_backend="json")
    run = manager.create_run("god_of_carnage_solo", display_name="Alice", account_id="acct-1")
    participant_id = next(pid for pid, p in run.participants.items() if p.mode == ParticipantMode.HUMAN)

    ws = _FakeWebSocket()
    await manager.connect(run.id, participant_id, ws)
    assert ws.accepted is True
    assert ws.sent[-1]["type"] == "snapshot"

    await manager.process_command(run.id, participant_id, {"action": "say", "text": "hi", "reject": True})
    assert ws.sent[-1] == {"type": "command_rejected", "reason": "rejected"}

    await manager.process_command(run.id, participant_id, {"action": "say", "text": "hi"})
    assert run.flags == {"npc-cycle"}

    closing_ws = _FakeWebSocket(fail_on_send=True)
    manager.connections[run.id][participant_id] = closing_ws
    await manager.broadcast_snapshot(run.id)
    assert participant_id not in manager.connections[run.id]

    await manager.disconnect(run.id, participant_id)
    assert run.participants[participant_id].connected is False
