import importlib.util

import pytest

SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None

from app.runtime.engine import RuntimeEngine
from app.runtime.manager import RuntimeManager
from app.runtime.models import RunStatus


def test_public_open_world_bootstraps(tmp_path):
    manager = RuntimeManager(store_root=tmp_path, store_backend="json")
    runs = manager.list_runs()
    assert any(run.template_id == "better_tomorrow_district_alpha" for run in runs)


def test_create_solo_run_and_snapshot(tmp_path):
    manager = RuntimeManager(store_root=tmp_path, store_backend="json")
    run = manager.create_run("god_of_carnage_solo", account_id="acct:hollywood", display_name="Hollywood")
    human = next(participant for participant in run.participants.values() if participant.seat_owner_account_id == "acct:hollywood")

    snapshot = manager.build_snapshot(run.id, human.id)
    assert snapshot.template_id == "god_of_carnage_solo"
    assert snapshot.viewer_display_name == "Hollywood"
    assert snapshot.viewer_room_id == "hallway"
    assert snapshot.viewer_account_id == "acct:hollywood"
    assert snapshot.current_room["id"] == "hallway"
    assert any(action["id"] == "steady_breath" for action in snapshot.available_actions)
    assert snapshot.metadata["store_backend"] == "json"


def test_group_run_uses_lobby_and_can_start_after_ready(tmp_path):
    manager = RuntimeManager(store_root=tmp_path, store_backend="json")
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    host = next(participant for participant in run.participants.values() if participant.account_id == "acct:host")
    guest = manager.find_or_join_run(run.id, account_id="acct:guest", display_name="Guest", preferred_role_id="parent_a")

    assert run.status == RunStatus.LOBBY
    host_snapshot = manager.build_snapshot(run.id, host.id)
    assert host_snapshot.lobby is not None
    assert host_snapshot.lobby["occupied_human_seats"] == 2
    assert host_snapshot.lobby["can_start"] is False

    engine = RuntimeEngine(manager.get_template(run.template_id))
    assert engine.apply_command(run, host.id, {"action": "set_ready", "ready": True}).accepted
    assert engine.apply_command(run, guest.id, {"action": "set_ready", "ready": True}).accepted
    started = engine.apply_command(run, host.id, {"action": "start_run"})
    assert started.accepted
    assert run.status == RunStatus.RUNNING


def test_group_rejoin_uses_same_account_and_same_seat(tmp_path):
    manager = RuntimeManager(store_root=tmp_path, store_backend="json")
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    guest = manager.find_or_join_run(run.id, account_id="acct:guest", display_name="Guest", preferred_role_id="parent_a")
    rejoined = manager.find_or_join_run(run.id, account_id="acct:guest", display_name="Guest Reloaded")

    assert guest.id == rejoined.id
    assert rejoined.display_name == "Guest Reloaded"
    snapshot = manager.build_snapshot(run.id, rejoined.id)
    seat = next(seat for seat in snapshot.lobby["seats"] if seat["role_id"] == "parent_a")
    assert seat["participant_id"] == guest.id
    assert seat["occupant_display_name"] == "Guest Reloaded"


def test_snapshot_hides_other_rooms_and_remote_transcript(tmp_path):
    manager = RuntimeManager(store_root=tmp_path, store_backend="json")
    run = manager.create_run("apartment_confrontation_group", account_id="acct:host", display_name="Host")
    second = manager.find_or_join_run(run.id, account_id="acct:guest", display_name="Guest", preferred_role_id="parent_a")

    engine = RuntimeEngine(manager.get_template(run.template_id))
    result = engine.apply_command(run, second.id, {"action": "say", "text": "We should proceed carefully."})
    assert result.accepted

    host = next(participant for participant in run.participants.values() if participant.account_id == "acct:host")
    snapshot = manager.build_snapshot(run.id, host.id)

    assert snapshot.current_room["id"] == "foyer"
    assert snapshot.visible_occupants == [
        {
            "participant_id": host.id,
            "display_name": "Host",
            "role_id": host.role_id,
            "mode": "human",
            "connected": False,
            "is_self": True,
        }
    ]
    assert all(entry.room_id in {None, host.current_room_id} or entry.payload.get("participant_id") == host.id for entry in snapshot.transcript_tail)


def test_identity_rejoin_uses_account_id_not_display_name(tmp_path):
    manager = RuntimeManager(store_root=tmp_path, store_backend="json")
    run = manager.create_run("apartment_confrontation_group", account_id="acct:dup-a", display_name="Alex")
    second = manager.find_or_join_run(run.id, account_id="acct:dup-b", display_name="Alex", preferred_role_id="parent_a")
    rejoined = manager.find_or_join_run(run.id, account_id="acct:dup-b", display_name="Someone Else")

    assert second.id == rejoined.id
    assert len([participant for participant in run.participants.values() if participant.mode.value == "human"]) == 2


def test_inspect_rejects_remote_room_targets(tmp_path):
    manager = RuntimeManager(store_root=tmp_path, store_backend="json")
    run = manager.create_run("god_of_carnage_solo", account_id="acct:hollywood", display_name="Hollywood")
    human = next(participant for participant in run.participants.values() if participant.account_id == "acct:hollywood")
    result = manager.engines[run.id].apply_command(run, human.id, {"action": "inspect", "target_id": "living_room"})
    assert not result.accepted
    assert result.reason == "That target is not visible from your current room."


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="sqlalchemy not installed")
def test_sqlalchemy_store_roundtrip_with_sqlite(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'runtime.db'}"
    manager = RuntimeManager(store_root=tmp_path, store_backend="sqlalchemy", store_url=db_url)
    run = manager.create_run("god_of_carnage_solo", account_id="acct:hollywood", display_name="Hollywood")

    reloaded = RuntimeManager(store_root=tmp_path, store_backend="sqlalchemy", store_url=db_url)
    loaded_run = reloaded.get_instance(run.id)
    assert loaded_run.template_id == "god_of_carnage_solo"
    assert reloaded.store.describe()["backend"] == "sqlalchemy"
