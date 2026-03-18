from pathlib import Path

from app.runtime.manager import RuntimeManager


def test_public_open_world_bootstraps(tmp_path: Path):
    manager = RuntimeManager(store_root=tmp_path)
    runs = manager.list_runs()
    assert any(run.template_id == "better_tomorrow_district_alpha" for run in runs)


def test_create_solo_run_and_snapshot(tmp_path: Path):
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", "Hollywood")
    human = next(participant for participant in run.participants.values() if participant.seat_owner == "Hollywood")

    snapshot = manager.build_snapshot(run.id, human.id)
    assert snapshot.template_id == "god_of_carnage_solo"
    assert snapshot.viewer_display_name == "Hollywood"
    assert snapshot.viewer_room_id == "hallway"
    assert any(action["id"] == "steady_breath" for action in snapshot.available_actions)


def test_group_run_accepts_second_human(tmp_path: Path):
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("apartment_confrontation_group", "Host")
    second = manager.find_or_join_run(run.id, "Guest", preferred_role_id="parent_a")
    assert second.role_id == "parent_a"
