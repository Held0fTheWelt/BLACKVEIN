from __future__ import annotations

from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.scene_energy_contracts import SCENE_ENERGY_FAILURE_CODES
from ai_stack.scene_energy_engine import (
    derive_scene_energy,
    validate_scene_energy_realization,
)
from ai_stack.story_runtime_playability import (
    decide_playability_recovery,
    is_hard_boundary_failure,
)


MODULE_ID = "god_of_carnage"


def _policy() -> dict:
    return load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()


def _profile_requiring_multiple_actor_responses(policy: dict) -> tuple[str, dict]:
    profiles = policy["runtime_governance_policy"]["scene_energy"]["scene_function_profiles"]
    for scene_function, profile in profiles.items():
        if int(profile.get("minimum_actor_response_count") or 0) >= 2:
            return scene_function, profile
    raise AssertionError("scene_energy_policy_missing_multi_actor_profile")


def _pacing_overlay_with_actor_pressure(policy: dict) -> tuple[str, dict]:
    overlays = policy["runtime_governance_policy"]["scene_energy"]["pacing_profiles"]
    for pacing_mode, overlay in overlays.items():
        if int(overlay.get("minimum_actor_response_count") or 0) >= 2:
            return pacing_mode, overlay
    raise AssertionError("scene_energy_policy_missing_actor_pressure_overlay")


def _missing_pressure_code() -> str:
    for code in SCENE_ENERGY_FAILURE_CODES:
        if code.endswith("missing_required_pressure"):
            return code
    raise AssertionError("scene_energy_contract_missing_pressure_failure_code")


def test_scene_energy_derives_target_from_module_policy() -> None:
    policy = _policy()
    scene_function, profile = _profile_requiring_multiple_actor_responses(policy)

    result = derive_scene_energy(
        scene_plan_record={
            "selected_scene_function": scene_function,
            "pacing_mode": "standard",
        },
        pacing_mode="standard",
        selected_responder_set=[{"actor_id": "actor_a"}, {"actor_id": "actor_b"}],
        module_runtime_policy=policy,
    )

    target = result["target"]
    for key in (
        "energy_level",
        "pressure_vector",
        "tempo",
        "density",
        "volatility",
        "target_transition",
        "minimum_actor_response_count",
    ):
        assert target[key] == profile[key]
    assert result["policy"]["source"] == "module_runtime_policy.scene_energy"


def test_scene_energy_pacing_overlay_comes_from_policy() -> None:
    policy = _policy()
    pacing_mode, overlay = _pacing_overlay_with_actor_pressure(policy)
    scene_function = next(
        iter(policy["runtime_governance_policy"]["scene_energy"]["scene_function_profiles"])
    )

    result = derive_scene_energy(
        scene_plan_record={
            "selected_scene_function": scene_function,
            "pacing_mode": pacing_mode,
        },
        pacing_mode=pacing_mode,
        selected_responder_set=[{"actor_id": "actor_a"}, {"actor_id": "actor_b"}],
        module_runtime_policy=policy,
    )

    target = result["target"]
    for key, expected in overlay.items():
        assert target[key] == expected


def test_scene_energy_validation_uses_structured_realization_counts() -> None:
    policy = _policy()
    scene_function, _profile = _profile_requiring_multiple_actor_responses(policy)
    result = derive_scene_energy(
        scene_plan_record={
            "selected_scene_function": scene_function,
            "pacing_mode": "standard",
        },
        pacing_mode="standard",
        selected_responder_set=[{"actor_id": "actor_a"}, {"actor_id": "actor_b"}],
        module_runtime_policy=policy,
    )

    rejected = validate_scene_energy_realization(
        scene_energy_target=result["target"],
        scene_energy_transition=result["transition"],
        structured_output={"spoken_lines": [{"speaker_id": "actor_a", "text": "x"}]},
    )

    assert rejected["status"] == "rejected"
    assert rejected["feedback_code"] in SCENE_ENERGY_FAILURE_CODES
    assert _missing_pressure_code() in rejected["failure_codes"]
    assert rejected["actual"]["actual_actor_response_count"] == 1

    approved = validate_scene_energy_realization(
        scene_energy_target=result["target"],
        scene_energy_transition=result["transition"],
        structured_output={
            "spoken_lines": [
                {"speaker_id": "actor_a", "text": "x"},
                {"speaker_id": "actor_b", "text": "y"},
            ],
        },
    )

    assert approved["status"] == "approved"
    assert approved["failure_codes"] == []
    assert approved["actual"]["actual_actor_response_count"] == 2


def test_scene_energy_rejections_are_recoverable_playability_failures() -> None:
    missing_pressure_code = _missing_pressure_code()
    outcome = {
        "status": "rejected",
        "reason": missing_pressure_code,
        "scene_energy_validation": {
            "failure_codes": [missing_pressure_code],
        },
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
    assert missing_pressure_code in decision.feedback_codes
