from __future__ import annotations

from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.contracts.social_pressure_contracts import (
    SOCIAL_PRESSURE_FAILURE_CODES,
    SOCIAL_PRESSURE_POLICY_VERSION,
    SOCIAL_PRESSURE_SCHEMA_VERSION,
)
from ai_stack.social_pressure_engine import (
    derive_social_pressure,
    validate_social_pressure_metric,
)


MODULE_ID = "god_of_carnage"


def _policy() -> dict:
    return load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()


def test_social_pressure_policy_loads_from_module_runtime_policy() -> None:
    policy = _policy()["runtime_governance_policy"]["social_pressure"]

    assert policy["schema_version"] == SOCIAL_PRESSURE_POLICY_VERSION
    assert policy["enabled"] is True
    assert policy["source"] == "module_runtime_policy.social_pressure"
    assert policy["band_thresholds"]["low_max"] < policy["band_thresholds"]["high_min"]
    assert policy["source_scores"]["thread_pressure_state"]["high_unresolved_thread_pressure"] >= (
        policy["band_thresholds"]["high_min"]
    )


def test_social_pressure_derives_continuous_high_metric_from_structured_sources() -> None:
    policy = _policy()
    thresholds = policy["runtime_governance_policy"]["social_pressure"]["band_thresholds"]

    result = derive_social_pressure(
        scene_assessment={
            "pressure_state": "stabilization_attempt",
            "thread_pressure_state": "high_unresolved_thread_pressure",
        },
        social_state_record={
            "social_risk_band": "high",
            "scene_pressure_state": "stabilization_attempt",
            "active_thread_count": 2,
        },
        scene_energy_target={"target_transition": "rise", "pressure_vector": "social"},
        pacing_rhythm_target={"cadence": "press"},
        prior_social_pressure_state={"current_score": 0.42, "current_band": "moderate"},
        prior_narrative_thread_state={"thread_pressure_level": 3},
        module_runtime_policy=policy,
    )

    state = result["state"]
    target = result["target"]
    assert result["schema_version"] == SOCIAL_PRESSURE_SCHEMA_VERSION
    assert state["current_score"] >= thresholds["high_min"]
    assert state["current_band"] == "high"
    assert state["trend"] == "rising"
    assert target["target_score"] == state["current_score"]
    assert target["target_band"] == "high"
    assert target["requires_visible_pressure"] is True
    assert {row["source"] for row in state["source_evidence"]} >= {
        "social_risk_band",
        "thread_pressure_state",
    }


def test_social_pressure_validation_uses_policy_thresholds_not_prose() -> None:
    policy = _policy()
    result = derive_social_pressure(
        scene_assessment={"pressure_state": "moderate_tension"},
        social_state_record={"social_risk_band": "moderate"},
        scene_energy_target={"target_transition": "hold", "pressure_vector": "social"},
        pacing_rhythm_target={"cadence": "hold"},
        module_runtime_policy=policy,
    )

    approved = validate_social_pressure_metric(
        social_pressure_target=result["target"],
        social_pressure_state=result["state"],
        module_runtime_policy=policy,
    )

    assert approved["status"] == "approved"
    assert approved["contract_pass"] is True
    assert approved["failure_codes"] == []
    assert approved["actual"]["validated_from_policy_thresholds"] is True

    rejected = validate_social_pressure_metric(
        social_pressure_target={**result["target"], "target_band": "low"},
        social_pressure_state=result["state"],
        module_runtime_policy=policy,
    )

    assert rejected["status"] == "rejected"
    assert "social_pressure_band_mismatch" in rejected["failure_codes"]
    assert rejected["feedback_code"] in SOCIAL_PRESSURE_FAILURE_CODES
