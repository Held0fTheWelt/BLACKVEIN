from __future__ import annotations

from ai_stack.story_runtime.god_of_carnage.god_of_carnage_yaml_authority import load_goc_yaml_slice_bundle
from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.contracts.sensory_context_contracts import (
    SENSORY_CONTEXT_FAILURE_CODES,
    SENSORY_CONTEXT_POLICY_VERSION,
    SENSORY_CONTEXT_SCHEMA_VERSION,
)
from ai_stack.story_runtime.narrative.sensory_context_engine import (
    derive_sensory_context,
    validate_sensory_context_realization,
)
from ai_stack.story_runtime.story_runtime_playability import decide_playability_recovery, is_hard_boundary_failure


MODULE_ID = "god_of_carnage"


def _policy() -> dict:
    return load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()


def _yaml_slice() -> dict:
    return load_goc_yaml_slice_bundle()


def _missing_required_code() -> str:
    for code in SENSORY_CONTEXT_FAILURE_CODES:
        if code.endswith("missing_required_layer"):
            return code
    raise AssertionError("sensory_context_contract_missing_required_layer_code")


def test_sensory_context_policy_loads_from_module_runtime_policy() -> None:
    policy = _policy()["runtime_governance_policy"]["sensory_context"]

    assert policy["schema_version"] == SENSORY_CONTEXT_POLICY_VERSION
    assert policy["enabled"] is True
    assert policy["source"] == "module_runtime_policy.sensory_context"
    assert policy["min_layers_per_turn"] >= 1
    assert policy["max_layers_per_turn"] >= policy["min_layers_per_turn"]


def test_sensory_context_derives_layers_from_authored_sources() -> None:
    policy = _policy()
    bundle = _yaml_slice()

    result = derive_sensory_context(
        scene_plan_record={
            "selected_scene_function": "escalate_conflict",
            "pacing_mode": "multi_pressure",
        },
        current_scene_id="living_room",
        player_action_frame={
            "verb": "look_at",
            "action_kind": "perception",
            "resolved_target": {"target_id": "window"},
        },
        narrator_sensory_palette=bundle["narrator_sensory_palette"],
        scene_affordances=bundle["scene_affordances"],
        scene_energy_target={"energy_level": "volatile"},
        social_pressure_target={"target_band": "high"},
        module_runtime_policy=policy,
        session_output_language="de",
    )

    assert result["schema_version"] == SENSORY_CONTEXT_SCHEMA_VERSION
    assert result["policy"]["source"] == "module_runtime_policy.sensory_context"
    target = result["target"]
    assert target["intensity"] == "high"
    assert target["location_id"] == "living_room"
    assert target["object_id"] == "window"
    assert target["selected_layers"]
    source_refs = {layer["source_ref"] for layer in target["selected_layers"]}
    assert any(ref.startswith("objects/") for ref in source_refs)
    assert all(
        ref.startswith("locations/")
        or ref.startswith("objects/")
        or ref.startswith("narrator_sensory_palette.")
        or ref.startswith("scene_affordances.")
        for ref in source_refs
    )


def test_sensory_context_validation_uses_structured_layer_events() -> None:
    policy = _policy()
    bundle = _yaml_slice()
    result = derive_sensory_context(
        scene_plan_record={"selected_scene_function": "establish_pressure"},
        current_scene_id="living_room",
        narrator_sensory_palette=bundle["narrator_sensory_palette"],
        scene_affordances=bundle["scene_affordances"],
        module_runtime_policy=policy,
    )
    target = result["target"]
    required_layer_id = target["required_layer_ids"][0]
    required_layer = next(
        layer for layer in target["selected_layers"] if layer["layer_id"] == required_layer_id
    )

    rejected = validate_sensory_context_realization(
        sensory_context_target=target,
        sensory_context_state=result["state"],
        structured_output={"sensory_context_events": []},
    )

    assert rejected["status"] == "rejected"
    assert rejected["feedback_code"] in SENSORY_CONTEXT_FAILURE_CODES
    assert _missing_required_code() in rejected["failure_codes"]

    approved = validate_sensory_context_realization(
        sensory_context_target=target,
        sensory_context_state=result["state"],
        structured_output={
            "sensory_context_events": [
                {
                    "layer_id": required_layer_id,
                    "source_ref": required_layer["source_ref"],
                    "surface_lane": "narration_summary",
                }
            ]
        },
    )

    assert approved["status"] == "approved"
    assert approved["failure_codes"] == []
    assert approved["actual"]["realized_layer_ids"] == [required_layer_id]


def test_sensory_context_rejections_are_recoverable_playability_failures() -> None:
    code = _missing_required_code()
    outcome = {
        "status": "rejected",
        "reason": code,
        "sensory_context_validation": {"failure_codes": [code]},
    }

    assert is_hard_boundary_failure(outcome) is False
    decision = decide_playability_recovery(
        turn_number=2,
        attempt_index=1,
        max_attempts=1,
        outcome=outcome,
        generation={"success": True, "content": "visible structured attempt"},
        proposed_state_effects=[{"effect_type": "narrative", "description": "visible"}],
        actor_lane_validation={"status": "approved", "reason": "actor_lane_legal"},
    )

    assert decision.should_retry is True
    assert code in decision.feedback_codes
