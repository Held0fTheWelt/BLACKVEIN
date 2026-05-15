from __future__ import annotations

from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.pacing_rhythm_contracts import (
    PACING_RHYTHM_FAILURE_CODES,
    PACING_RHYTHM_POLICY_VERSION,
    PACING_RHYTHM_SCHEMA_VERSION,
)
from ai_stack.pacing_rhythm_engine import (
    derive_pacing_rhythm,
    validate_pacing_rhythm_realization,
)
from ai_stack.story_runtime_playability import (
    decide_playability_recovery,
    is_hard_boundary_failure,
)


MODULE_ID = "god_of_carnage"


def _policy() -> dict:
    return load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()


def _profile_requiring_turn_change(policy: dict) -> tuple[str, dict]:
    profiles = policy["runtime_governance_policy"]["pacing_rhythm"]["cadence_profiles"]
    for cadence, profile in profiles.items():
        if int(profile.get("min_actor_turns") or 0) >= 2:
            return cadence, profile
    raise AssertionError("pacing_rhythm_policy_missing_turn_change_profile")


def _density_code() -> str:
    for code in PACING_RHYTHM_FAILURE_CODES:
        if code.endswith("visible_density_exceeded"):
            return code
    raise AssertionError("pacing_rhythm_contract_missing_density_failure_code")


def test_pacing_rhythm_policy_loads_from_module_runtime_policy() -> None:
    policy = _policy()["runtime_governance_policy"]["pacing_rhythm"]

    assert policy["schema_version"] == PACING_RHYTHM_POLICY_VERSION
    assert policy["enabled"] is True
    assert policy["source"] == "module_runtime_policy.pacing_rhythm"
    cadence, profile = _profile_requiring_turn_change(_policy())
    assert cadence in policy["cadence_profiles"]
    assert int(profile["min_actor_turns"]) >= 2


def test_pacing_rhythm_derives_target_from_policy_and_scene_energy() -> None:
    policy = _policy()
    cadence, profile = _profile_requiring_turn_change(policy)

    result = derive_pacing_rhythm(
        scene_plan_record={
            "selected_scene_function": "escalate_conflict",
            "pacing_mode": "multi_pressure",
            "selected_beat": {"id": "scene_alpha:beat_alpha"},
        },
        pacing_mode="multi_pressure",
        scene_energy_target={"target_transition": "interrupt"},
        selected_responder_set=[{"actor_id": "actor_a"}, {"actor_id": "actor_b"}],
        module_runtime_policy=policy,
    )

    assert result["schema_version"] == PACING_RHYTHM_SCHEMA_VERSION
    assert result["target"]["cadence"] == cadence
    for key, expected in profile.items():
        if key in result["target"]:
            assert result["target"][key] == expected
    assert result["state"]["last_beat_id"] == "scene_alpha:beat_alpha"
    assert result["policy"]["source"] == "module_runtime_policy.pacing_rhythm"


def test_pacing_rhythm_validation_uses_structured_counts() -> None:
    policy = _policy()
    result = derive_pacing_rhythm(
        scene_plan_record={"selected_scene_function": "escalate_conflict", "pacing_mode": "multi_pressure"},
        pacing_mode="multi_pressure",
        scene_energy_target={"target_transition": "interrupt"},
        selected_responder_set=[{"actor_id": "actor_a"}, {"actor_id": "actor_b"}],
        module_runtime_policy=policy,
    )

    rejected = validate_pacing_rhythm_realization(
        pacing_rhythm_target=result["target"],
        pacing_rhythm_state=result["state"],
        structured_output={"spoken_lines": [{"speaker_id": "actor_a", "text": "x"}]},
    )

    assert rejected["status"] == "rejected"
    assert rejected["feedback_code"] in PACING_RHYTHM_FAILURE_CODES
    assert "pacing_rhythm_required_turn_change_missing" in rejected["failure_codes"]
    assert rejected["actual"]["actor_turn_count"] == 1

    approved = validate_pacing_rhythm_realization(
        pacing_rhythm_target=result["target"],
        pacing_rhythm_state=result["state"],
        structured_output={
            "spoken_lines": [
                {"speaker_id": "actor_a", "text": "x"},
                {"speaker_id": "actor_b", "text": "y"},
            ],
        },
    )

    assert approved["status"] == "approved"
    assert approved["failure_codes"] == []
    assert approved["actual"]["actor_turn_count"] == 2


def test_pacing_rhythm_density_rejection_is_recoverable() -> None:
    code = _density_code()
    outcome = {
        "status": "rejected",
        "reason": code,
        "pacing_rhythm_validation": {"failure_codes": [code]},
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
