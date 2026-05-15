"""Deterministic coverage for consequence-cascade derivation."""

from __future__ import annotations

from story_runtime_core.branching.branch_timeline import (
    BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
)
from story_runtime_core.consequences import (
    CONSEQUENCE_CASCADE_FEEDBACK_CONTRACT,
    CONSEQUENCE_CASCADE_RECORD_SCHEMA_VERSION,
    CONSEQUENCE_EDGE_KIND_BRANCH_SELECTION_REALIZED,
    CONSEQUENCE_EDGE_KIND_CARRY_FORWARD,
    CONSEQUENCE_EDGE_KIND_RESOLUTION,
    CONSEQUENCE_EDGE_KIND_THREAD_CONTINUITY,
    CONSEQUENCE_STATUS_FADING,
    CONSEQUENCE_STATUS_RESOLVED,
    build_consequence_cascade_record,
    build_graph_consequence_cascade_export,
    default_consequence_cascade_bounds,
    normalize_consequence_cascade_bounds,
    stable_consequence_cascade_id,
)


def _row(
    *,
    turn_id: str,
    turn_number: int,
    scene: str,
    continuity_class: str,
    resolved: list[str] | None = None,
    open_pressures: list[str] | None = None,
    use_beat_pressure: bool = False,
) -> dict:
    if use_beat_pressure:
        commit: dict = {
            "committed_scene_id": scene,
            "turn_number": turn_number,
            "beat_progression": {"pressure_state": continuity_class},
            "open_pressures": open_pressures or [],
            "resolved_pressures": resolved or [],
        }
    else:
        commit = {
            "committed_scene_id": scene,
            "turn_number": turn_number,
            "planner_truth": {"continuity_impacts": [{"class": continuity_class}]},
            "open_pressures": open_pressures or [],
            "resolved_pressures": resolved or [],
        }
    return {"canonical_turn_id": turn_id, "turn_number": turn_number, "narrative_commit": commit}


def test_stable_consequence_cascade_id_is_deterministic():
    sid = "sess-1"
    a = stable_consequence_cascade_id(story_session_id=sid)
    assert a == stable_consequence_cascade_id(story_session_id=sid)
    assert a.startswith("consequence_cascade_")


def test_normalize_consequence_cascade_bounds():
    base = default_consequence_cascade_bounds()
    out = normalize_consequence_cascade_bounds(
        {"max_atoms": 3, "max_edges": 2, "decay_after_turns": 0, "max_evidence_refs": "x"}
    )
    assert out["max_atoms"] == 8
    assert out["max_edges"] == 8
    assert out["decay_after_turns"] == 1
    assert out["max_evidence_refs"] == base["max_evidence_refs"]


def test_build_consequence_cascade_carry_forward_and_fading():
    history = [
        _row(turn_id="a", turn_number=1, scene="parlor", continuity_class="heat"),
        _row(turn_id="b", turn_number=6, scene="parlor", continuity_class="heat"),
    ]
    rec = build_consequence_cascade_record(
        story_session_id="c1",
        module_id="m",
        history=history,
        bounds={"decay_after_turns": 2, "max_atoms": 40, "max_edges": 40},
    )
    assert rec["schema_version"] == CONSEQUENCE_CASCADE_RECORD_SCHEMA_VERSION
    kinds = {e["edge_kind"] for e in rec["edges"]}
    assert CONSEQUENCE_EDGE_KIND_CARRY_FORWARD in kinds
    statuses = {a["status"] for a in rec["atoms"]}
    assert CONSEQUENCE_STATUS_FADING in statuses


def test_build_consequence_cascade_resolution_edge_when_resolved_pressure_matches():
    history = [
        _row(turn_id="t1", turn_number=1, scene="s", continuity_class="p1"),
        _row(
            turn_id="t2",
            turn_number=2,
            scene="s",
            continuity_class="p1",
            resolved=["p1"],
        ),
    ]
    rec = build_consequence_cascade_record(story_session_id="c2", module_id="m", history=history)
    kinds = {e["edge_kind"] for e in rec["edges"]}
    assert CONSEQUENCE_EDGE_KIND_RESOLUTION in kinds
    assert CONSEQUENCE_STATUS_RESOLVED in {a["status"] for a in rec["atoms"]}


def test_build_consequence_cascade_thread_continuity_edge():
    history = [
        _row(turn_id="t1", turn_number=1, scene="parlor", continuity_class="k1"),
        _row(turn_id="t2", turn_number=2, scene="parlor", continuity_class="k2"),
    ]
    threads = {
        "active": [
            {
                "thread_id": "th1",
                "scene_anchor": "parlor",
                "thread_kind": "",
                "related_scenes": [],
            }
        ]
    }
    rec = build_consequence_cascade_record(
        story_session_id="c3", module_id="m", history=history, narrative_threads=threads
    )
    assert CONSEQUENCE_EDGE_KIND_THREAD_CONTINUITY in {e["edge_kind"] for e in rec["edges"]}


def test_build_consequence_cascade_beat_pressure_source_field():
    history = [
        _row(
            turn_id="t1",
            turn_number=1,
            scene="x",
            continuity_class="silence_pressure",
            use_beat_pressure=True,
        ),
    ]
    rec = build_consequence_cascade_record(story_session_id="c4", module_id="m", history=history)
    atom = rec["atoms"][0]
    assert "beat_progression" in atom["evidence"]["source_fields"][0]


def test_build_consequence_cascade_branch_timeline_replay_committed():
    history = [
        _row(turn_id="root", turn_number=1, scene="s", continuity_class="sel"),
        _row(turn_id="leaf", turn_number=2, scene="s", continuity_class="sel"),
    ]
    timeline = {
        "events": [
            {
                "event_type": BRANCHING_TIMELINE_EVENT_SELECTION_REPLAY_COMMITTED,
                "tree_id": "tr",
                "canonical_turn_id": "leaf",
                "details": {"root_canonical_turn_id": "root"},
            }
        ]
    }
    rec = build_consequence_cascade_record(
        story_session_id="c5",
        module_id="m",
        history=history,
        branch_timeline=timeline,
    )
    assert CONSEQUENCE_EDGE_KIND_BRANCH_SELECTION_REALIZED in {e["edge_kind"] for e in rec["edges"]}


def test_build_consequence_cascade_callback_web_id_echo():
    history = [_row(turn_id="only", turn_number=1, scene="s", continuity_class="z")]
    cb = {"callback_web_id": "cb_123"}
    rec = build_consequence_cascade_record(
        story_session_id="c6", module_id="m", history=history, callback_web=cb
    )
    assert rec["callback_web_id"] == "cb_123"


def test_build_graph_consequence_cascade_export_prefers_active_atoms():
    history = [
        _row(turn_id="old", turn_number=1, scene="s", continuity_class="late_fresh"),
        _row(turn_id="new", turn_number=2, scene="s", continuity_class="late_fresh"),
    ]
    rec = build_consequence_cascade_record(
        story_session_id="c7",
        module_id="m",
        history=history,
        bounds={"decay_after_turns": 10},
    )
    export = build_graph_consequence_cascade_export(rec, max_items=3)
    assert export is not None
    assert export["feedback_contract"] == CONSEQUENCE_CASCADE_FEEDBACK_CONTRACT
    assert export["items"]
    active_export = build_graph_consequence_cascade_export(rec, max_items=1)
    assert active_export["selected_statuses"]


def test_build_graph_consequence_cascade_export_none_for_bad_record():
    assert build_graph_consequence_cascade_export(None) is None


def test_atoms_thread_dicts_model_dump_shim():
    class Shim:
        def model_dump(self, mode="json"):
            return {
                "active": [
                    {
                        "thread_id": "shim_th",
                        "thread_kind": "k_atom",
                        "scene_anchor": "",
                        "related_scenes": [],
                    }
                ]
            }

    history = [_row(turn_id="t1", turn_number=1, scene="s", continuity_class="k_atom")]
    rec = build_consequence_cascade_record(
        story_session_id="c8", module_id="m", history=history, narrative_threads=Shim()
    )
    assert any("shim_th" in (a.get("thread_ids") or []) for a in rec["atoms"])
