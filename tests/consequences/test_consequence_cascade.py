from __future__ import annotations

from ai_stack.contracts.consequence_cascade_contracts import (
    consequence_cascade_bounds_from_policy,
    consequence_cascade_policy_from_module_runtime,
    validate_consequence_cascade_record,
)
from ai_stack.module_runtime_policy import load_module_runtime_policy
from story_runtime_core.branching import (
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
    BRANCHING_TIMELINE_EVENT_TREE_CREATED,
)
from story_runtime_core.consequences import (
    CONSEQUENCE_CASCADE_FEEDBACK_CONTRACT,
    CONSEQUENCE_CASCADE_RECORD_SCHEMA_VERSION,
    CONSEQUENCE_EDGE_KIND_BRANCH_SELECTION_REALIZED,
    CONSEQUENCE_EDGE_KIND_CARRY_FORWARD,
    build_consequence_cascade_record,
    build_graph_consequence_cascade_export,
)


def _policy() -> dict:
    module_policy = load_module_runtime_policy("god_of_carnage").to_dict()
    return consequence_cascade_policy_from_module_runtime(module_policy)


def _continuity_class(policy: dict) -> str:
    classes = policy["allowed_continuity_classes"]
    assert classes
    return str(classes[0])


def _history(continuity_class: str) -> list[dict]:
    return [
        {
            "canonical_turn_id": "turn-1",
            "turn_number": 1,
            "narrative_commit": {
                "committed_scene_id": "scene_1",
                "planner_truth": {
                    "primary_responder_id": "actor_alpha",
                    "continuity_impacts": [{"class": continuity_class}],
                },
                "open_pressures": [continuity_class],
            },
        },
        {
            "canonical_turn_id": "turn-2",
            "turn_number": 2,
            "narrative_commit": {
                "committed_scene_id": "scene_1",
                "planner_truth": {
                    "primary_responder_id": "actor_beta",
                    "continuity_impacts": [{"class": continuity_class}],
                },
                "open_pressures": [continuity_class],
            },
        },
    ]


def test_consequence_cascade_derives_edges_from_committed_turns() -> None:
    policy = _policy()
    continuity_class = _continuity_class(policy)
    record = build_consequence_cascade_record(
        story_session_id="cascade-session",
        module_id="god_of_carnage",
        history=_history(continuity_class),
        bounds=consequence_cascade_bounds_from_policy(policy),
    )
    validation = validate_consequence_cascade_record(record, policy=policy)
    export = build_graph_consequence_cascade_export(record, max_items=policy["max_graph_items"])

    assert record["schema_version"] == CONSEQUENCE_CASCADE_RECORD_SCHEMA_VERSION
    assert record["derived_from_committed_truth"] is True
    assert record["mutates_canonical_state"] is False
    assert validation["contract_pass"] is True
    assert record["snapshot"]["atom_count"] == len(record["atoms"])
    assert record["snapshot"]["edge_count"] == len(record["edges"])
    assert any(edge["edge_kind"] == CONSEQUENCE_EDGE_KIND_CARRY_FORWARD for edge in record["edges"])
    assert export is not None
    assert export["feedback_contract"] == CONSEQUENCE_CASCADE_FEEDBACK_CONTRACT
    assert export["exported_item_count"] <= policy["max_graph_items"]
    assert "evidence" not in export["items"][0]


def test_consequence_cascade_marks_realized_branch_selection_edges() -> None:
    policy = _policy()
    continuity_class = _continuity_class(policy)
    timeline = {
        "events": [
            {
                "event_type": BRANCHING_TIMELINE_EVENT_TREE_CREATED,
                "tree_id": "tree-alpha",
                "details": {"root_canonical_turn_id": "turn-1"},
            },
            {
                "event_type": BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
                "tree_id": "tree-alpha",
                "canonical_turn_id": "turn-2",
                "details": {},
            },
        ]
    }

    record = build_consequence_cascade_record(
        story_session_id="cascade-session",
        module_id="god_of_carnage",
        history=_history(continuity_class),
        branch_timeline=timeline,
        bounds=consequence_cascade_bounds_from_policy(policy),
    )

    assert any(
        edge["edge_kind"] == CONSEQUENCE_EDGE_KIND_BRANCH_SELECTION_REALIZED
        for edge in record["edges"]
    )
