"""Social state projection from continuity and threads."""

from __future__ import annotations

from ai_stack.goc_yaml_authority import load_goc_yaml_slice_bundle
from ai_stack.director.scene_director_goc import build_scene_assessment
from ai_stack.semantic_planner.social_state_goc import build_social_state_record, social_state_fingerprint


def test_social_state_fingerprint_stable() -> None:
    sa = build_scene_assessment(
        module_id="god_of_carnage",
        current_scene_id="living_room",
        canonical_yaml={"content": {"setting": "Paris", "narrative_scope": "domestic"}},
        prior_continuity_impacts=[{"class": "blame_pressure"}],
        yaml_slice=None,
    )
    s1 = build_social_state_record(
        prior_continuity_impacts=[{"class": "blame_pressure"}],
        active_narrative_threads=[{"thread_id": "t1", "thread_kind": "x", "status": "open", "intensity": 2, "related_entities": []}],
        thread_pressure_summary="heat",
        scene_assessment=sa,
    )
    s2 = build_social_state_record(
        prior_continuity_impacts=[{"class": "blame_pressure"}],
        active_narrative_threads=[{"thread_id": "t1", "thread_kind": "x", "status": "open", "intensity": 2, "related_entities": []}],
        thread_pressure_summary="heat",
        scene_assessment=sa,
    )
    assert social_state_fingerprint(s1) == social_state_fingerprint(s2)


def test_social_state_rehydrates_prior_committed_record() -> None:
    prior = build_social_state_record(
        prior_continuity_impacts=[{"class": "blame_pressure"}],
        active_narrative_threads=[],
        thread_pressure_summary=None,
        scene_assessment={"pressure_state": "high_blame"},
    )
    current = build_social_state_record(
        prior_continuity_impacts=[{"class": "repair_attempt"}],
        active_narrative_threads=[],
        thread_pressure_summary=None,
        scene_assessment={"pressure_state": "moderate_tension"},
        prior_social_state_record=prior.to_runtime_dict(),
    )

    assert current.prior_social_state_fingerprint == social_state_fingerprint(prior)
    assert current.prior_social_risk_band == "high"
    assert current.social_continuity_status == "social_state_shifted"


def test_social_state_treats_thread_pressure_as_high_risk() -> None:
    record = build_social_state_record(
        prior_continuity_impacts=[],
        active_narrative_threads=[],
        thread_pressure_summary="progression_blocked:4",
        scene_assessment={"pressure_state": "thread_pressure_high"},
    )

    assert record.social_risk_band == "high"


def test_social_state_thread_pressure_high_overrides_moderate_continuity_band() -> None:
    assessment = build_scene_assessment(
        module_id="god_of_carnage",
        current_scene_id="living_room",
        canonical_yaml=None,
        prior_continuity_impacts=[{"class": "repair_attempt"}],
        prior_narrative_thread_state={
            "thread_count": 2,
            "thread_pressure_level": 4,
            "thread_pressure_summary": "blocked",
        },
    )

    record = build_social_state_record(
        prior_continuity_impacts=[{"class": "repair_attempt"}],
        active_narrative_threads=[{"thread_id": "t1"}, {"thread_id": "t2"}],
        thread_pressure_summary="blocked",
        scene_assessment=assessment,
    )

    assert assessment["pressure_state"] == "stabilization_attempt"
    assert assessment["thread_pressure_state"] == "high_unresolved_thread_pressure"
    assert record.social_risk_band == "high"

    moderate_record = build_social_state_record(
        prior_continuity_impacts=[{"class": "repair_attempt"}],
        active_narrative_threads=[{"thread_id": "t1"}, {"thread_id": "t2"}],
        thread_pressure_summary="blocked",
        scene_assessment={"pressure_state": "stabilization_attempt"},
    )

    assert moderate_record.social_risk_band == "moderate"
    assert social_state_fingerprint(record) != social_state_fingerprint(moderate_record)


def test_social_state_derives_relationship_axis_codes_from_canonical_yaml() -> None:
    yaml_slice = load_goc_yaml_slice_bundle()
    canonical_axis_ids = set(yaml_slice["relationship_axes"])

    record = build_social_state_record(
        prior_continuity_impacts=[{"class": "blame_pressure"}],
        active_narrative_threads=[{"thread_id": "t1"}],
        thread_pressure_summary="blocked",
        scene_assessment={"pressure_state": "high_blame"},
        yaml_slice=yaml_slice,
    )

    assert record.active_relationship_axis_ids
    assert set(record.active_relationship_axis_ids).issubset(canonical_axis_ids)
    assert record.dominant_relationship_axis_id in record.active_relationship_axis_ids
    assert record.relationship_pressure_codes
    assert all(" " not in code for code in record.relationship_pressure_codes)
