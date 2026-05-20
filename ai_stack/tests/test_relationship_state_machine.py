"""Tests for the durable Pi27 relationship-state machine."""

from __future__ import annotations

from ai_stack.story_runtime.god_of_carnage.god_of_carnage_yaml_authority import load_goc_yaml_slice_bundle
from ai_stack.contracts.relationship_state_contracts import (
    RELATIONSHIP_STATE_SCHEMA_VERSION,
    RelationshipStateRecord,
)
from ai_stack.story_runtime.narrative.relationship_state_engine import (
    derive_relationship_state,
    relationship_state_fingerprint,
    validate_relationship_state_realization,
)
from ai_stack.story_runtime.semantic_planner.god_of_carnage_social_state import build_social_state_record


def _policy() -> dict:
    return {
        "runtime_governance_policy": {
            "relationship_state_machine": {
                "enabled": True,
                "schema_version": "relationship_state_policy.v1",
                "max_tracked_pairs": 12,
                "max_tracked_axes": 8,
                "max_transition_events": 12,
            }
        }
    }


def test_relationship_state_derives_durable_transitions_from_structured_sources() -> None:
    yaml_slice = load_goc_yaml_slice_bundle()
    social = build_social_state_record(
        prior_continuity_impacts=[{"class": "blame_pressure"}],
        active_narrative_threads=[{"thread_id": "thread-1"}],
        thread_pressure_summary="blocked",
        scene_assessment={"pressure_state": "high_blame"},
        yaml_slice=yaml_slice,
    ).to_runtime_dict()

    result = derive_relationship_state(
        yaml_slice=yaml_slice,
        social_state_record=social,
        social_pressure_state={"schema_version": "social_pressure.v1", "current_band": "high"},
        module_runtime_policy=_policy(),
        turn_number=3,
    )

    record = result["state"]
    target = result["target"]
    canonical_axis_ids = set(yaml_slice["relationship_axes"])
    canonical_relationship_ids = set(yaml_slice["relationships"])

    assert record["schema_version"] == RELATIONSHIP_STATE_SCHEMA_VERSION
    assert record["transition_events"]
    assert set(record["active_relationship_axis_ids"]).issubset(canonical_axis_ids)
    assert {row["relationship_id"] for row in record["pair_states"]}.issubset(
        canonical_relationship_ids
    )
    assert target["target_relationship_ids"]
    assert target["requires_visible_relationship_beat"] is True


def test_relationship_state_rehydrates_prior_record_and_applies_repair_transition() -> None:
    yaml_slice = load_goc_yaml_slice_bundle()
    initial_social = build_social_state_record(
        prior_continuity_impacts=[{"class": "blame_pressure"}],
        active_narrative_threads=[],
        thread_pressure_summary=None,
        scene_assessment={"pressure_state": "high_blame"},
        yaml_slice=yaml_slice,
    ).to_runtime_dict()
    initial = derive_relationship_state(
        yaml_slice=yaml_slice,
        social_state_record=initial_social,
        social_pressure_state={"schema_version": "social_pressure.v1", "current_band": "high"},
        module_runtime_policy=_policy(),
        turn_number=1,
    )["state"]
    prior_fp = relationship_state_fingerprint(RelationshipStateRecord.model_validate(initial))
    repair_social = build_social_state_record(
        prior_continuity_impacts=[{"class": "repair_attempt"}],
        active_narrative_threads=[],
        thread_pressure_summary=None,
        scene_assessment={"pressure_state": "stabilization_attempt"},
        yaml_slice=yaml_slice,
    ).to_runtime_dict()

    repaired = derive_relationship_state(
        yaml_slice=yaml_slice,
        social_state_record=repair_social,
        social_pressure_state={"schema_version": "social_pressure.v1", "current_band": "moderate"},
        prior_relationship_state_record=initial,
        module_runtime_policy=_policy(),
        turn_number=2,
    )["state"]

    assert repaired["prior_record_fingerprint"] == prior_fp
    assert {event["transition_code"] for event in repaired["transition_events"]} == {
        "repair_attempt"
    }
    assert min(row["tension_score"] for row in repaired["pair_states"]) < min(
        row["tension_score"] for row in initial["pair_states"]
    )


def test_relationship_state_validation_rejects_forbidden_actor_events() -> None:
    yaml_slice = load_goc_yaml_slice_bundle()
    social = build_social_state_record(
        prior_continuity_impacts=[{"class": "blame_pressure"}],
        active_narrative_threads=[],
        thread_pressure_summary=None,
        scene_assessment={"pressure_state": "high_blame"},
        yaml_slice=yaml_slice,
    ).to_runtime_dict()
    result = derive_relationship_state(
        yaml_slice=yaml_slice,
        social_state_record=social,
        module_runtime_policy=_policy(),
        turn_number=1,
    )

    validation = validate_relationship_state_realization(
        relationship_state_record=result["state"],
        relationship_dynamics_target=result["target"],
        structured_output={
            "relationship_dynamics_events": [
                {
                    "transition_code": result["target"]["required_transition_codes"][0],
                    "source_actor_id": "visitor",
                }
            ]
        },
        actor_lane_context={"ai_forbidden_actor_ids": ["visitor"]},
        module_runtime_policy=_policy(),
    )

    assert validation["status"] == "rejected"
    assert "relationship_event_actor_lane_violation" in validation["failure_codes"]
