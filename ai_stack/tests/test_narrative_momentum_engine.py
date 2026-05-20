from __future__ import annotations

from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.contracts.narrative_momentum_contracts import (
    NARRATIVE_MOMENTUM_BUILDING,
    NARRATIVE_MOMENTUM_FAILURE_EVENT_MISSING,
    NARRATIVE_MOMENTUM_SCHEMA_VERSION,
)
from ai_stack.story_runtime.narrative.narrative_momentum_engine import (
    compact_narrative_momentum_context,
    derive_narrative_momentum,
    validate_narrative_momentum_realization,
)


def _policy() -> dict:
    return load_module_runtime_policy("god_of_carnage", "solo_test").to_dict()


def test_derives_bounded_state_machine_target_from_runtime_policy() -> None:
    result = derive_narrative_momentum(
        scene_plan_record={"semantic_move_kind": "escalate"},
        scene_energy_target={"target_transition": "rise"},
        pacing_rhythm_target={"cadence": "press"},
        social_pressure_target={"target_band": "high"},
        expectation_variation_target={"selected_variation_ids": ["variation_alpha"]},
        prior_narrative_momentum_state={
            "current_state": "resting",
            "current_score": 0.2,
            "stall_turn_count": 0,
        },
        module_runtime_policy=_policy(),
    )

    state = result["state"]
    target = result["target"]
    assert state["schema_version"] == NARRATIVE_MOMENTUM_SCHEMA_VERSION
    assert state["current_state"] == NARRATIVE_MOMENTUM_BUILDING
    assert state["trend"] == "rising"
    assert "narrative_momentum_transition_clamped" in state["rationale_codes"]
    assert target["policy_enabled"] is True
    assert target["target_state"] == NARRATIVE_MOMENTUM_BUILDING
    assert target["requires_forward_motion"] is True
    assert target["min_progress_event_count"] == 1
    assert {ref["source"] for ref in target["selected_driver_refs"]} >= {
        "scene_energy_transition",
        "pacing_cadence",
        "social_pressure_band",
    }


def test_validate_momentum_realization_requires_progress_event_when_forward_motion() -> None:
    derived = derive_narrative_momentum(
        scene_plan_record={"semantic_move_kind": "escalate"},
        scene_energy_target={"target_transition": "rise"},
        pacing_rhythm_target={"cadence": "press"},
        social_pressure_target={"target_band": "high"},
        prior_narrative_momentum_state={"current_state": "resting", "current_score": 0.2},
        module_runtime_policy=_policy(),
    )

    missing = validate_narrative_momentum_realization(
        narrative_momentum_target=derived["target"],
        narrative_momentum_state=derived["state"],
        structured_output={},
        module_runtime_policy=_policy(),
    )
    assert missing["status"] == "rejected"
    assert NARRATIVE_MOMENTUM_FAILURE_EVENT_MISSING in missing["failure_codes"]

    approved = validate_narrative_momentum_realization(
        narrative_momentum_target=derived["target"],
        narrative_momentum_state=derived["state"],
        structured_output={
            "narrative_momentum_events": [
                {
                    "event_type": "advance",
                    "momentum_state": derived["target"]["target_state"],
                    "source_refs": derived["target"]["selected_driver_refs"][:1],
                }
            ]
        },
        module_runtime_policy=_policy(),
    )

    assert approved["status"] == "approved"
    assert approved["contract_pass"] is True
    assert approved["actual"]["progress_event_count"] == 1


def test_compact_context_hides_disabled_policy() -> None:
    assert compact_narrative_momentum_context({"policy_enabled": False}) == {}
