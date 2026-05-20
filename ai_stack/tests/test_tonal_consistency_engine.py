from __future__ import annotations

from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.contracts.tonal_consistency_contracts import (
    TONAL_CONSISTENCY_DEFAULT_CLASSIFICATION_SOURCE,
    TONAL_CONSISTENCY_FAILURE_CODES,
    TONAL_CONSISTENCY_POLICY_VERSION,
    TONAL_CONSISTENCY_SCHEMA_VERSION,
)
from ai_stack.story_runtime.narrative.tonal_consistency_classifier import classify_tonal_consistency_from_policy
from ai_stack.story_runtime.narrative.tonal_consistency_engine import (
    build_tonal_consistency_aspect_record,
    compact_tonal_consistency_context,
    derive_tonal_consistency,
    validate_tonal_consistency_realization,
)


MODULE_ID = "god_of_carnage"


def _policy() -> dict:
    return load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()


def _tone_policy() -> dict:
    return _policy()["runtime_governance_policy"]["tonal_consistency"]


def _first_profile(policy: dict) -> tuple[str, dict]:
    profiles = policy["tone_profiles"]
    for profile_id, profile in profiles.items():
        return profile_id, profile
    raise AssertionError("tonal_consistency_policy_missing_profile")


def _first_profile_scene(policy: dict, profile_id: str) -> str:
    for scene_function, mapped_profile in policy["profile_by_scene_function"].items():
        if mapped_profile == profile_id:
            return scene_function
    raise AssertionError("tonal_consistency_policy_missing_scene_profile_mapping")


def _first_marker(policy: dict) -> tuple[str, str]:
    for marker_class, markers in policy["forbidden_marker_map"].items():
        if markers:
            return marker_class, markers[0]
    raise AssertionError("tonal_consistency_policy_missing_marker")


def test_tonal_consistency_policy_loads_from_module_runtime_policy() -> None:
    policy = _tone_policy()
    profile_id, profile = _first_profile(policy)

    assert policy["schema_version"] == TONAL_CONSISTENCY_POLICY_VERSION
    assert policy["enabled"] is True
    assert policy["source"] == "module_runtime_policy.tonal_consistency"
    assert policy["live_loop_mode"] == "recover"
    assert policy["classification_source"] == TONAL_CONSISTENCY_DEFAULT_CLASSIFICATION_SOURCE
    assert profile["required_dimension_ids"]
    assert profile["dimension_marker_map"]
    assert profile_id == policy["default_profile_id"]


def test_tonal_consistency_derives_target_from_policy_and_scene_function() -> None:
    policy = _policy()
    tone_policy = policy["runtime_governance_policy"]["tonal_consistency"]
    profile_id, profile = _first_profile(tone_policy)
    scene_function = _first_profile_scene(tone_policy, profile_id)

    result = derive_tonal_consistency(
        scene_plan_record={"selected_scene_function": scene_function},
        scene_energy_target={"target_transition": "rise"},
        pacing_rhythm_target={"cadence": "press"},
        social_pressure_target={"target_band": "high"},
        module_runtime_policy=policy,
    )

    assert result["schema_version"] == TONAL_CONSISTENCY_SCHEMA_VERSION
    assert result["policy"]["schema_version"] == TONAL_CONSISTENCY_POLICY_VERSION
    assert result["target"]["profile_id"] == profile_id
    assert result["target"]["required_dimension_ids"] == profile["required_dimension_ids"]
    assert result["target"]["policy_enabled"] is True
    assert result["target"]["pressure_band"] == "high"
    assert result["target"]["live_loop_mode"] == "recover"
    assert result["target"]["dimension_marker_map"]


def test_tonal_consistency_validation_uses_independent_classifier() -> None:
    policy = _policy()
    target = derive_tonal_consistency(
        scene_plan_record={
            "selected_scene_function": _first_profile_scene(
                _tone_policy(), _tone_policy()["default_profile_id"]
            )
        },
        module_runtime_policy=policy,
    )["target"]
    register = target["allowed_registers"][0]

    approved_text = "Please stay at the table; perhaps we can understand the pressure in the room."
    approved = validate_tonal_consistency_realization(
        tonal_consistency_target=target,
        structured_output={
            "narrative_response": approved_text,
            "tonal_consistency_classification": {
                "realized_dimension_ids": [],
                "register_label": "fantasy_adventure",
            },
        },
    )

    assert approved["status"] == "approved"
    assert approved["failure_codes"] == []
    assert approved["actual"]["independent_classifier"] is True
    assert approved["actual"]["classification_source"] == TONAL_CONSISTENCY_DEFAULT_CLASSIFICATION_SOURCE
    assert approved["actual"]["required_dimension_present_count"] == len(
        target["required_dimension_ids"]
    )

    marker_class, marker = _first_marker(_tone_policy())
    rejected = validate_tonal_consistency_realization(
        tonal_consistency_target=target,
        structured_output={
            "narrative_response": marker,
            "tonal_consistency_classification": {
                "realized_dimension_ids": [],
                "register_label": register,
                "genre_label": register,
            },
        },
    )

    assert rejected["status"] == "rejected"
    assert rejected["contract_pass"] is False
    assert "tonal_consistency_required_dimension_missing" in rejected["failure_codes"]
    assert "tonal_consistency_forbidden_marker_detected" in rejected["failure_codes"]
    assert rejected["actual"]["forbidden_marker_hits"][marker_class] >= 1
    for code in rejected["failure_codes"]:
        assert code in TONAL_CONSISTENCY_FAILURE_CODES


def test_tonal_consistency_classifier_ignores_generator_self_attestation() -> None:
    policy = _policy()
    target = derive_tonal_consistency(
        scene_plan_record={
            "selected_scene_function": _first_profile_scene(
                _tone_policy(), _tone_policy()["default_profile_id"]
            )
        },
        module_runtime_policy=policy,
    )["target"]

    classification = classify_tonal_consistency_from_policy(
        tonal_consistency_target=target,
        structured_output={
            "narrative_response": "Quest debug fallback.",
            "tonal_consistency_classification": {
                "realized_dimension_ids": target["required_dimension_ids"],
                "register_label": target["allowed_registers"][0],
            },
        },
    )

    assert classification["independent_classifier"] is True
    assert classification["realized_dimension_ids"] == []
    assert classification["marker_hit_count"] > 0


def test_tonal_consistency_context_omits_policy_marker_literals() -> None:
    policy = _policy()
    target = derive_tonal_consistency(
        scene_plan_record={"selected_scene_function": _first_profile_scene(_tone_policy(), _tone_policy()["default_profile_id"])},
        module_runtime_policy=policy,
    )["target"]
    marker_class, marker = _first_marker(_tone_policy())

    context = compact_tonal_consistency_context(target)

    assert marker_class in context["forbidden_marker_classes"]
    assert marker not in str(context)
    assert context["required_dimension_ids"] == target["required_dimension_ids"]


def test_tonal_consistency_aspect_record_maps_local_evidence() -> None:
    policy = _policy()
    target = derive_tonal_consistency(
        scene_plan_record={"selected_scene_function": _first_profile_scene(_tone_policy(), _tone_policy()["default_profile_id"])},
        module_runtime_policy=policy,
    )["target"]

    partial = build_tonal_consistency_aspect_record(
        target=target,
        policy=policy["runtime_governance_policy"]["tonal_consistency"],
    )
    assert partial["status"] == "partial"
    assert partial["expected"]["policy_enabled"] is True
    assert partial["selected"]["required_dimension_ids"] == target["required_dimension_ids"]

    validation = validate_tonal_consistency_realization(
        tonal_consistency_target=target,
        structured_output={
            "narrative_response": "Please stay at the table; perhaps we can understand the pressure.",
        },
    )
    passed = build_tonal_consistency_aspect_record(
        target=target,
        validation=validation,
        policy=policy["runtime_governance_policy"]["tonal_consistency"],
    )

    assert passed["status"] == "passed"
    assert passed["actual"]["contract_pass"] is True
