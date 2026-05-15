"""Deterministic coverage for callback-web derivation (committed-turn projections)."""

from __future__ import annotations

from story_runtime_core.callbacks import (
    CALLBACK_EDGE_KIND_BRANCH_SELECTION_REALIZED,
    CALLBACK_EDGE_KIND_REPEATED_CONTINUITY_CLASS,
    CALLBACK_EDGE_KIND_REPEATED_SCENE_ANCHOR,
    CALLBACK_EDGE_KIND_THREAD_CONTINUITY,
    CALLBACK_WEB_FEEDBACK_CONTRACT,
    CALLBACK_WEB_RECORD_SCHEMA_VERSION,
    build_callback_web_record,
    build_callback_web_snapshot,
    build_graph_callback_web_export,
    default_callback_web_bounds,
    normalize_callback_web_bounds,
    stable_callback_web_id,
)


def _row(
    *,
    turn_id: str,
    turn_number: int,
    scene: str,
    continuity_class: str,
    open_pressures: list[str] | None = None,
    entities: list[str] | None = None,
) -> dict:
    planner: dict = {
        "continuity_impacts": [{"class": continuity_class}],
    }
    if entities:
        planner["primary_responder_id"] = entities[0]
        if len(entities) > 1:
            planner["secondary_responder_ids"] = entities[1:]
    commit = {
        "committed_scene_id": scene,
        "turn_number": turn_number,
        "planner_truth": planner,
        "open_pressures": open_pressures or [],
    }
    return {
        "canonical_turn_id": turn_id,
        "turn_number": turn_number,
        "narrative_commit": commit,
    }


def test_stable_callback_web_id_is_deterministic():
    sid = "session-alpha"
    assert stable_callback_web_id(story_session_id=sid) == stable_callback_web_id(story_session_id=sid)
    assert stable_callback_web_id(story_session_id=sid).startswith("callback_web_")


def test_normalize_callback_web_bounds_clamps_and_ignores_bad_values():
    base = default_callback_web_bounds()
    assert base["max_edges"] >= 8
    out = normalize_callback_web_bounds(
        {"max_edges": 3, "max_observations": 2, "max_evidence_refs": "nope", "extra": 1}
    )
    assert out["max_edges"] == 8
    assert out["max_observations"] == 4
    assert out["max_evidence_refs"] == base["max_evidence_refs"]


def test_build_callback_web_record_repeated_continuity_class_edge():
    history = [
        _row(turn_id="t1", turn_number=1, scene="parlor", continuity_class="tension_spike"),
        _row(turn_id="t2", turn_number=2, scene="kitchen", continuity_class="tension_spike"),
    ]
    record = build_callback_web_record(story_session_id="s1", history=history)
    assert record["schema_version"] == CALLBACK_WEB_RECORD_SCHEMA_VERSION
    assert len(record["observations"]) == 2
    kinds = {e["callback_kind"] for e in record["edges"]}
    assert CALLBACK_EDGE_KIND_REPEATED_CONTINUITY_CLASS in kinds


def test_build_callback_web_record_thread_continuity_via_scene_anchor():
    history = [
        _row(turn_id="t1", turn_number=1, scene="parlor", continuity_class="a"),
        _row(turn_id="t2", turn_number=2, scene="parlor", continuity_class="b"),
    ]
    threads = {
        "active": [
            {
                "thread_id": "th_parlor",
                "scene_anchor": "parlor",
                "thread_kind": "",
                "related_scenes": [],
                "evidence_tokens": [],
            }
        ]
    }
    record = build_callback_web_record(story_session_id="s2", history=history, narrative_threads=threads)
    kinds = {e["callback_kind"] for e in record["edges"]}
    assert CALLBACK_EDGE_KIND_THREAD_CONTINUITY in kinds


def test_build_callback_web_record_repeated_scene_anchor_when_turn_gap_gt_one():
    history = [
        _row(turn_id="t1", turn_number=1, scene="salon", continuity_class="x"),
        _row(turn_id="t3", turn_number=3, scene="salon", continuity_class="y"),
    ]
    record = build_callback_web_record(story_session_id="s3", history=history)
    kinds = {e["callback_kind"] for e in record["edges"]}
    assert CALLBACK_EDGE_KIND_REPEATED_SCENE_ANCHOR in kinds


def test_build_callback_web_record_branch_timeline_selection_replay_edge():
    history = [
        _row(turn_id="root", turn_number=1, scene="r1", continuity_class="c1"),
        _row(turn_id="leaf", turn_number=2, scene="r2", continuity_class="c1"),
    ]
    branch_timeline = {
        "events": [
            {
                "event_type": "selection_replay_committed",
                "tree_id": "bt_1",
                "canonical_turn_id": "leaf",
                "details": {"root_canonical_turn_id": "root"},
            }
        ]
    }
    record = build_callback_web_record(
        story_session_id="s4",
        history=history,
        branch_timeline=branch_timeline,
    )
    kinds = {e["callback_kind"] for e in record["edges"]}
    assert CALLBACK_EDGE_KIND_BRANCH_SELECTION_REALIZED in kinds


def test_build_callback_web_snapshot_aggregates_counts():
    history = [
        _row(turn_id="a", turn_number=1, scene="s", continuity_class="k"),
        _row(turn_id="b", turn_number=2, scene="s", continuity_class="k"),
    ]
    record = build_callback_web_record(story_session_id="snap", history=history)
    snap = build_callback_web_snapshot(record)
    assert snap["edge_count"] == len(record["edges"])
    assert snap["observation_count"] == 2
    assert snap["latest_turn_id"] == "b"


def test_build_graph_callback_web_export_truncates_edges_and_flags_contract():
    history = [
        _row(turn_id=f"t{i}", turn_number=i, scene="parlor", continuity_class="shared")
        for i in range(1, 6)
    ]
    record = build_callback_web_record(story_session_id="g", history=history)
    export = build_graph_callback_web_export(record, max_edges=2)
    assert export is not None
    assert export["feedback_contract"] == CALLBACK_WEB_FEEDBACK_CONTRACT
    assert export["exported_edge_count"] <= 2
    assert export["edges"]


def test_build_graph_callback_web_export_observations_without_edges_returns_payload():
    history = [_row(turn_id="only", turn_number=1, scene="s", continuity_class="solo")]
    record = build_callback_web_record(story_session_id="solo", history=history)
    # Single turn: no pairwise edges, but observations exist
    assert record["edges"] == []
    export = build_graph_callback_web_export(record, max_edges=4)
    assert export is not None
    assert int(export["observation_count"]) >= 1


def test_build_graph_callback_web_export_invalid_record_returns_none():
    assert build_graph_callback_web_export(None) is None
    assert build_graph_callback_web_export("nope") is None


def test_thread_dicts_accepts_simple_model_dump_shim():
    class Shim:
        def model_dump(self, mode="json"):
            return {
                "active": [
                    {
                        "thread_id": "from_shim",
                        "scene_anchor": "parlor",
                        "thread_kind": "x_class",
                        "related_scenes": [],
                        "evidence_tokens": [],
                    }
                ]
            }

    history = [
        _row(turn_id="t1", turn_number=1, scene="parlor", continuity_class="x_class"),
    ]
    record = build_callback_web_record(story_session_id="shim", history=history, narrative_threads=Shim())
    assert any("from_shim" in (o.get("thread_ids") or []) for o in record["observations"])
