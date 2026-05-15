from __future__ import annotations

from story_runtime_core.callbacks import (
    CALLBACK_EDGE_KIND_BRANCH_SELECTION_REALIZED,
    CALLBACK_EDGE_KIND_REPEATED_CONTINUITY_CLASS,
    CALLBACK_EDGE_KIND_THREAD_CONTINUITY,
    CALLBACK_EDGE_KINDS,
    CALLBACK_EDGE_SCHEMA_VERSION,
    CALLBACK_OBSERVATION_SCHEMA_VERSION,
    CALLBACK_WEB_RECORD_SCHEMA_VERSION,
    CALLBACK_WEB_SNAPSHOT_SCHEMA_VERSION,
    build_callback_web_record,
    default_callback_web_bounds,
)


def _turn(turn_number: int, *, continuity_class: str, scene_id: str, responder_id: str) -> dict:
    return {
        "canonical_turn_id": f"turn-{turn_number}",
        "turn_number": turn_number,
        "narrative_commit": {
            "turn_number": turn_number,
            "committed_scene_id": scene_id,
            "open_pressures": [f"pressure::{continuity_class}::{turn_number}"],
            "committed_consequences": [f"consequence::{continuity_class}::{turn_number}"],
            "planner_truth": {
                "primary_responder_id": responder_id,
                "continuity_impacts": [{"class": continuity_class}],
            },
        },
    }


def _thread(thread_id: str, *, continuity_class: str, scene_id: str) -> dict:
    return {
        "active": [
            {
                "thread_id": thread_id,
                "thread_kind": continuity_class,
                "status": "active",
                "intensity": 4,
                "persistence_turns": 2,
                "scene_anchor": scene_id,
                "related_scenes": [scene_id],
                "related_entities": [],
                "evidence_tokens": [],
                "last_updated_turn": 2,
            }
        ],
        "resolved_recent": [],
    }


def test_callback_web_derives_edges_from_continuity_and_threads() -> None:
    continuity_class = "shared_pressure"
    thread_id = "thread_shared_pressure"
    history = [
        _turn(1, continuity_class=continuity_class, scene_id="scene_a", responder_id="actor_a"),
        _turn(2, continuity_class=continuity_class, scene_id="scene_a", responder_id="actor_a"),
    ]

    record = build_callback_web_record(
        story_session_id="session-callback",
        module_id="module-callback",
        runtime_profile_id="profile-callback",
        history=history,
        narrative_threads=_thread(thread_id, continuity_class=continuity_class, scene_id="scene_a"),
    )

    edge_kinds = {edge["callback_kind"] for edge in record["edges"]}
    assert record["schema_version"] == CALLBACK_WEB_RECORD_SCHEMA_VERSION
    assert record["snapshot"]["schema_version"] == CALLBACK_WEB_SNAPSHOT_SCHEMA_VERSION
    assert {edge["schema_version"] for edge in record["edges"]} == {CALLBACK_EDGE_SCHEMA_VERSION}
    assert {obs["schema_version"] for obs in record["observations"]} == {CALLBACK_OBSERVATION_SCHEMA_VERSION}
    assert edge_kinds.issubset(set(CALLBACK_EDGE_KINDS))
    assert CALLBACK_EDGE_KIND_REPEATED_CONTINUITY_CLASS in edge_kinds
    assert CALLBACK_EDGE_KIND_THREAD_CONTINUITY in edge_kinds
    assert continuity_class in record["snapshot"]["continuity_classes"]
    assert thread_id in record["snapshot"]["thread_ids"]
    assert record["snapshot"]["non_authoritative"] is True
    assert record["snapshot"]["mutates_canonical_state"] is False


def test_callback_web_can_use_opening_turn_as_callback_source() -> None:
    continuity_class = "opening_pressure"
    history = [
        _turn(0, continuity_class=continuity_class, scene_id="scene_opening", responder_id="actor_a"),
        _turn(1, continuity_class=continuity_class, scene_id="scene_followup", responder_id="actor_b"),
    ]

    record = build_callback_web_record(
        story_session_id="session-callback",
        history=history,
        narrative_threads={"active": [], "resolved_recent": []},
    )

    continuity_edges = [
        edge
        for edge in record["edges"]
        if edge["callback_kind"] == CALLBACK_EDGE_KIND_REPEATED_CONTINUITY_CLASS
    ]
    assert continuity_edges
    assert continuity_edges[0]["source_turn_number"] == 0
    assert continuity_edges[0]["target_turn_number"] == 1
    assert continuity_class in continuity_edges[0]["continuity_classes"]


def test_callback_web_links_branch_selection_to_root_turn() -> None:
    continuity_class = "branch_pressure"
    history = [
        _turn(1, continuity_class=continuity_class, scene_id="scene_root", responder_id="actor_a"),
        _turn(2, continuity_class=continuity_class, scene_id="scene_branch", responder_id="actor_b"),
    ]
    branch_tree_id = "branch-tree-for-callback"
    branch_timeline = {
        "events": [
            {
                "event_type": "tree_created",
                "tree_id": branch_tree_id,
                "details": {"root_canonical_turn_id": history[0]["canonical_turn_id"]},
            },
            {
                "event_type": "selection_replay_committed",
                "tree_id": branch_tree_id,
                "canonical_turn_id": history[1]["canonical_turn_id"],
                "details": {},
            },
        ]
    }

    record = build_callback_web_record(
        story_session_id="session-callback",
        history=history,
        narrative_threads={"active": [], "resolved_recent": []},
        branch_timeline=branch_timeline,
    )

    branch_edges = [
        edge
        for edge in record["edges"]
        if edge["callback_kind"] == CALLBACK_EDGE_KIND_BRANCH_SELECTION_REALIZED
    ]
    assert len(branch_edges) == 1
    assert branch_edges[0]["branch_tree_ids"] == [branch_tree_id]
    assert branch_edges[0]["source_turn_id"] == history[0]["canonical_turn_id"]
    assert branch_edges[0]["target_turn_id"] == history[1]["canonical_turn_id"]


def test_callback_web_respects_bounds_without_text_oracles() -> None:
    continuity_class = "bounded_pressure"
    bounds = default_callback_web_bounds()
    bounds["max_edges"] = 8
    bounds["max_observations"] = 6
    history = [
        _turn(i, continuity_class=continuity_class, scene_id=f"scene_{i % 2}", responder_id="actor")
        for i in range(1, 12)
    ]

    record = build_callback_web_record(
        story_session_id="session-callback",
        history=history,
        narrative_threads=_thread("thread_bounded_pressure", continuity_class=continuity_class, scene_id="scene_1"),
        bounds=bounds,
    )

    assert len(record["edges"]) <= record["bounds"]["max_edges"]
    assert len(record["observations"]) <= record["bounds"]["max_observations"]
    assert record["snapshot"]["edge_count"] == len(record["edges"])
