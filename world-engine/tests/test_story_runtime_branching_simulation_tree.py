from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from story_runtime_core.branching import (
    BRANCHING_TIMELINE_EVENT_NODE_SELECTED,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_STARTED,
    BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE,
    BRANCHING_TIMELINE_EVENT_TREE_CREATED,
    BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION,
    BRANCHING_SIMULATION_TREE_SCHEMA_VERSION,
    BRANCHING_TREE_RECORD_SCHEMA_VERSION,
)

from app.story_runtime import StoryRuntimeManager
from app.story_runtime.branch_timeline_store import JsonBranchTimelineStore
from app.story_runtime.branching_tree_store import JsonBranchingTreeStore


def _disable_langfuse(monkeypatch: Any) -> None:
    adapter = MagicMock()
    adapter.is_enabled.return_value = False
    adapter.is_ready = False
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )


class _FakeTurnGraph:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls: list[dict[str, Any]] = []

    def run(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(dict(kwargs))
        return dict(self._payload)


def _envelope(
    *,
    interpreted_input: dict[str, Any] | None = None,
    generation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gen = dict(generation or {"success": True, "metadata": {}})
    gen.setdefault("content", "branching simulation fixture output")
    return {
        "interpreted_input": interpreted_input
        or {
            "kind": "speech",
            "player_input_kind": "speech",
            "confidence": 0.81,
            "ambiguity": "unresolved pressure",
        },
        "generation": gen,
        "graph_diagnostics": {"errors": []},
        "retrieval": {"domain": "runtime", "status": "ok"},
        "routing": {"selected_model": "mock"},
        "validation_outcome": {"status": "approved", "reason": "test_fixture"},
        "visible_output_bundle": {"gm_narration": ["Fixture narration."]},
        "committed_result": {"commit_applied": True, "committed_effects": []},
    }


def _opening_envelope(start_scene_id: str) -> dict[str, Any]:
    return _envelope(
        generation={
            "success": True,
            "metadata": {
                "structured_output": {
                    "narrative_response": "Opening fixture.",
                    "proposed_scene_id": start_scene_id,
                    "intent_summary": "",
                }
            },
        },
    )


def test_branching_simulation_tree_runs_on_isolated_session_clones(monkeypatch: Any) -> None:
    _disable_langfuse(monkeypatch)
    manager = StoryRuntimeManager()
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "runtime_profile_id": "profile-branching-sim",
            "scenes": [{"id": "scene_1"}],
        },
    )
    manager.turn_graph = _FakeTurnGraph(_envelope())  # type: ignore[assignment]
    turn = manager.execute_turn(session_id=session.session_id, player_input="Where does the pressure go?")
    assert turn["branching_forecast"]["status"] == "forecasted"

    before_state = manager.get_state(session.session_id)
    before_session_ids = set(manager.sessions)
    tree = manager.build_branching_simulation_tree(
        session_id=session.session_id,
        max_depth=2,
        max_branching=2,
        trace_id="trace-branching-sim",
    )
    after_state = manager.get_state(session.session_id)

    assert tree["schema_version"] == BRANCHING_SIMULATION_TREE_SCHEMA_VERSION
    assert tree["status"] in {"simulated", "partial"}
    assert tree["simulation_only"] is True
    assert tree["authoritative"] is False
    assert tree["mutates_active_session"] is False
    assert tree["persists_simulated_turns"] is False
    assert tree["simulated_turn_count"] >= 2
    assert tree["max_depth_observed"] == 2
    assert before_state["turn_counter"] == after_state["turn_counter"]
    assert before_state["history_count"] == after_state["history_count"]
    assert before_state["current_scene_id"] == after_state["current_scene_id"]
    assert set(manager.sessions) == before_session_ids
    assert all(":branch-sim:" not in sid for sid in manager.sessions)


def test_branching_simulation_tree_is_not_applicable_without_expandable_forecast(monkeypatch: Any) -> None:
    _disable_langfuse(monkeypatch)
    manager = StoryRuntimeManager()
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )

    tree = manager.build_branching_simulation_tree(session_id=session.session_id)

    assert tree["schema_version"] == BRANCHING_SIMULATION_TREE_SCHEMA_VERSION
    assert tree["status"] == "not_applicable"
    assert tree["simulated_turn_count"] == 0
    assert tree["nodes"][0]["stop_reason"] == "no_expandable_root_forecast"


def test_branching_tree_record_is_durable_and_restored(monkeypatch: Any, tmp_path) -> None:
    _disable_langfuse(monkeypatch)
    store = JsonBranchingTreeStore(tmp_path / "branching_trees")
    manager = StoryRuntimeManager(branching_tree_store=store)
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "runtime_profile_id": "profile-branching-tree",
            "scenes": [{"id": "scene_1"}],
        },
    )
    manager.turn_graph = _FakeTurnGraph(_envelope())  # type: ignore[assignment]
    manager.execute_turn(session_id=session.session_id, player_input="Build a forecast.")

    record = manager.create_branching_tree(
        session_id=session.session_id,
        max_depth=1,
        max_branching=1,
        trace_id="trace-branching-tree",
    )
    restored = StoryRuntimeManager(branching_tree_store=store)
    restored.sessions[session.session_id] = manager.get_session(session.session_id)

    loaded = restored.get_branching_tree(session_id=session.session_id, tree_id=record["tree_id"])

    assert loaded["schema_version"] == BRANCHING_TREE_RECORD_SCHEMA_VERSION
    assert loaded["tree_id"] == record["tree_id"]
    assert loaded["status"] == "simulated"
    assert loaded["selectable_node_ids"]
    assert loaded["selection_replays_normal_commit_path"] is True
    assert loaded["adopts_simulated_snapshot"] is False


def test_branch_timeline_record_is_durable_and_tracks_tree_creation(monkeypatch: Any, tmp_path) -> None:
    _disable_langfuse(monkeypatch)
    tree_store = JsonBranchingTreeStore(tmp_path / "branching_trees")
    timeline_store = JsonBranchTimelineStore(tmp_path / "branch_timelines")
    manager = StoryRuntimeManager(branching_tree_store=tree_store, branch_timeline_store=timeline_store)
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "runtime_profile_id": "profile-branching-timeline",
            "scenes": [{"id": "scene_1"}],
        },
    )
    manager.turn_graph = _FakeTurnGraph(_envelope())  # type: ignore[assignment]
    manager.execute_turn(session_id=session.session_id, player_input="Build a forecast.")

    record = manager.create_branching_tree(session_id=session.session_id, max_depth=1, max_branching=1)
    restored = StoryRuntimeManager(branching_tree_store=tree_store, branch_timeline_store=timeline_store)
    restored.sessions[session.session_id] = manager.get_session(session.session_id)

    timeline = restored.get_branch_timeline(session_id=session.session_id)
    event_types = [event["event_type"] for event in timeline["events"]]

    assert timeline["schema_version"] == BRANCHING_TIMELINE_RECORD_SCHEMA_VERSION
    assert BRANCHING_TIMELINE_EVENT_TREE_CREATED in event_types
    assert timeline["snapshot"]["active_tree_ids"] == [record["tree_id"]]


def test_branching_tree_becomes_stale_when_session_advances(monkeypatch: Any) -> None:
    _disable_langfuse(monkeypatch)
    manager = StoryRuntimeManager()
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    manager.turn_graph = _FakeTurnGraph(_envelope())  # type: ignore[assignment]
    manager.execute_turn(session_id=session.session_id, player_input="Build a forecast.")
    record = manager.create_branching_tree(session_id=session.session_id, max_depth=1, max_branching=1)

    manager.execute_turn(session_id=session.session_id, player_input="Advance the real session.")
    stale = manager.get_branching_tree(session_id=session.session_id, tree_id=record["tree_id"])

    assert stale["status"] == "stale"
    assert stale["stale_reason"] == "session_changed_since_tree_creation"
    timeline = manager.get_branch_timeline(session_id=session.session_id)
    assert BRANCHING_TIMELINE_EVENT_TREE_BECAME_STALE in [event["event_type"] for event in timeline["events"]]
    assert record["tree_id"] in timeline["snapshot"]["stale_tree_ids"]


def test_selecting_branching_tree_node_replays_normal_commit_path(monkeypatch: Any) -> None:
    _disable_langfuse(monkeypatch)
    manager = StoryRuntimeManager()
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "runtime_profile_id": "profile-branching-select",
            "scenes": [{"id": "scene_1"}],
        },
    )
    manager.turn_graph = _FakeTurnGraph(_envelope())  # type: ignore[assignment]
    manager.execute_turn(session_id=session.session_id, player_input="Build a forecast.")
    record = manager.create_branching_tree(session_id=session.session_id, max_depth=1, max_branching=1)
    before = manager.get_state(session.session_id)
    selected_node_id = record["selectable_node_ids"][0]

    result = manager.select_branching_tree_node(
        session_id=session.session_id,
        tree_id=record["tree_id"],
        node_id=selected_node_id,
        trace_id="trace-select-branch",
    )
    after = manager.get_state(session.session_id)

    assert result["selection"]["status"] == "committed"
    assert result["selection"]["uses_normal_commit_path"] is True
    assert result["selection"]["adopts_simulated_snapshot"] is False
    assert result["branching_tree"]["status"] == "committed"
    assert after["turn_counter"] == before["turn_counter"] + 1
    assert after["history_count"] == before["history_count"] + 1
    assert ":branch-sim:" not in manager.get_session(session.session_id).history[-1]["canonical_turn_id"]
    timeline = manager.get_branch_timeline(session_id=session.session_id)
    event_types = [event["event_type"] for event in timeline["events"]]
    assert BRANCHING_TIMELINE_EVENT_NODE_SELECTED in event_types
    assert BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_STARTED in event_types
    assert BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED in event_types
    assert record["tree_id"] in timeline["snapshot"]["committed_tree_ids"]
