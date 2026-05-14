from __future__ import annotations

from story_runtime_core.branching import (
    BRANCHING_TREE_RECORD_SCHEMA_VERSION,
    BRANCHING_TREE_STATUS_SIMULATED,
    branch_tree_is_fresh,
    branch_tree_path_nodes,
    make_branch_tree_record,
    mark_branch_tree_stale,
)


def _simulation_tree() -> dict:
    return {
        "schema_version": "branching_simulation_tree.v1",
        "status": "simulated",
        "story_session_id": "session-branch",
        "module_id": "module-alpha",
        "runtime_profile_id": "profile-alpha",
        "root_canonical_turn_id": "session-branch:turn:3",
        "root_turn_number": 3,
        "node_count": 2,
        "simulated_turn_count": 1,
        "max_depth_observed": 1,
        "nodes": [
            {
                "node_id": "root",
                "node_kind": "root_committed_turn",
                "parent_node_id": None,
                "child_node_ids": ["node-a"],
                "depth": 0,
            },
            {
                "node_id": "node-a",
                "node_kind": "simulated_turn",
                "parent_node_id": "root",
                "child_node_ids": [],
                "depth": 1,
                "path_option_ids": ["option-a"],
                "simulated_input": "Simulate option A.",
                "commit_applied_in_clone": True,
            },
        ],
    }


def _fingerprint(value: str = "fp-1") -> dict:
    return {
        "fingerprint": value,
        "session_id": "session-branch",
        "turn_counter": 3,
        "history_count": 4,
        "current_scene_id": "scene_1",
    }


def test_branch_tree_record_wraps_simulation_as_selectable_but_non_authoritative() -> None:
    record = make_branch_tree_record(
        simulation_tree=_simulation_tree(),
        root_session_fingerprint=_fingerprint(),
        current_session_fingerprint=_fingerprint(),
        trace_id="trace-branch-tree",
    )

    assert record["schema_version"] == BRANCHING_TREE_RECORD_SCHEMA_VERSION
    assert record["status"] == BRANCHING_TREE_STATUS_SIMULATED
    assert record["authoritative"] is False
    assert record["selection_required_to_commit"] is True
    assert record["selection_replays_normal_commit_path"] is True
    assert record["adopts_simulated_snapshot"] is False
    assert record["selectable_node_ids"] == ["node-a"]
    assert record["summary"]["selectable_node_count"] == 1


def test_branch_tree_freshness_uses_root_session_fingerprint() -> None:
    record = make_branch_tree_record(
        simulation_tree=_simulation_tree(),
        root_session_fingerprint=_fingerprint("fp-1"),
        current_session_fingerprint=_fingerprint("fp-1"),
    )

    assert branch_tree_is_fresh(record, _fingerprint("fp-1")) is True
    assert branch_tree_is_fresh(record, _fingerprint("fp-2")) is False

    stale = mark_branch_tree_stale(
        record,
        reason="session_changed",
        current_session_fingerprint=_fingerprint("fp-2"),
    )
    assert stale["status"] == "stale"
    assert stale["stale_reason"] == "session_changed"


def test_branch_tree_path_nodes_returns_ordered_simulated_path() -> None:
    record = make_branch_tree_record(
        simulation_tree=_simulation_tree(),
        root_session_fingerprint=_fingerprint(),
        current_session_fingerprint=_fingerprint(),
    )

    path = branch_tree_path_nodes(record, "node-a")

    assert [node["node_id"] for node in path] == ["node-a"]
