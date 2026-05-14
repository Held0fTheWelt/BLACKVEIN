from __future__ import annotations

from story_runtime_core.branching import (
    BRANCHING_SIMULATION_TREE_SCHEMA_VERSION,
    clamp_simulation_limits,
    finalize_simulation_tree,
    make_simulated_turn_node,
    make_simulation_tree,
)


def _forecast() -> dict:
    return {
        "schema_version": "branching_forecast.v1",
        "status": "forecasted",
        "option_count": 1,
        "options": [
            {
                "option_id": "branch_option_a",
                "family": "press_pressure",
                "label": "press pressure",
                "forecasted_consequence": "Pressure increases.",
            }
        ],
    }


def test_simulation_tree_contract_is_non_authoritative() -> None:
    depth, branching, max_nodes = clamp_simulation_limits(max_depth=2, max_branching=2)
    tree = make_simulation_tree(
        story_session_id="session-sim",
        module_id="module-alpha",
        runtime_profile_id="profile-alpha",
        root_canonical_turn_id="session-sim:turn:3",
        root_turn_number=3,
        root_branching_forecast=_forecast(),
        max_depth=depth,
        max_branching=branching,
        max_nodes=max_nodes,
    )

    assert tree["schema_version"] == BRANCHING_SIMULATION_TREE_SCHEMA_VERSION
    assert tree["simulation_only"] is True
    assert tree["authoritative"] is False
    assert tree["mutates_canonical_state"] is False
    assert tree["mutates_active_session"] is False
    assert tree["persists_simulated_turns"] is False
    assert tree["nodes"][0]["node_kind"] == "root_committed_turn"


def test_simulation_tree_summarizes_simulated_nodes() -> None:
    depth, branching, max_nodes = clamp_simulation_limits(max_depth=1, max_branching=1)
    tree = make_simulation_tree(
        story_session_id="session-sim",
        module_id="module-alpha",
        runtime_profile_id="profile-alpha",
        root_canonical_turn_id="session-sim:turn:3",
        root_turn_number=3,
        root_branching_forecast=_forecast(),
        max_depth=depth,
        max_branching=branching,
        max_nodes=max_nodes,
    )
    node = make_simulated_turn_node(
        tree=tree,
        parent_node_id=tree["root_node_id"],
        depth=1,
        option=_forecast()["options"][0],
        option_index=0,
        path_option_ids=["branch_option_a"],
        simulated_input="Simulate branch depth 1.",
        simulated_event={
            "canonical_turn_id": "session-sim:branch-sim:abc:turn:4",
            "turn_number": 4,
            "turn_kind": "player",
            "validation_outcome": {"status": "approved"},
            "committed_result": {"commit_applied": True},
            "narrative_commit": {"situation_status": "continue"},
            "branching_forecast": {"schema_version": "branching_forecast.v1", "status": "not_applicable"},
        },
        stop_reason="max_depth",
    )
    tree["nodes"][0]["child_node_ids"].append(node["node_id"])
    tree["nodes"].append(node)

    finalized = finalize_simulation_tree(tree)

    assert finalized["node_count"] == 2
    assert finalized["simulated_turn_count"] == 1
    assert finalized["summary"]["max_depth_observed"] == 1
    assert finalized["summary"]["mutates_active_session"] is False
