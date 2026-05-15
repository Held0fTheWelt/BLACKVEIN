from __future__ import annotations

import re

from ai_stack.capability_selector import validate_semantic_capability_name
from ai_stack.capability_validator_dispatch import (
    ValidatorDispatchMode,
    build_validator_dispatch_report,
)
from ai_stack.capability_validator_plan import JUDGE_VALIDATORS, build_validator_execution_plan
from ai_stack.capability_validator_registry import (
    PLANNED_ALL_DISPATCH_IDS,
    PLANNED_JUDGE_IDS,
    build_available_semantic_validator_registry,
    build_default_semantic_validator_registry,
    build_semantic_validator_registry,
    unavailable_validator_result,
)
from ai_stack.tests.test_capability_validator_dispatch_plan_enforced import (
    OPENING_ENFORCED_VALIDATORS,
    _opening_plan,
)


def test_default_registry_does_not_register_unavailable_validators_as_success() -> None:
    registry = build_default_semantic_validator_registry()

    assert registry == {}
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=registry,
        feature_flag_enabled=True,
    )

    assert report.actually_executed == ()
    assert set(report.validators_unavailable) == set(report.validators_would_run)


def test_registry_uses_semantic_ids_only() -> None:
    active_pi = re.compile(
        r"(?<![A-Za-z0-9])pi_\d+\b|(?<![A-Za-z0-9])pi\d+_[A-Za-z0-9_]+\b|Π\d+\b",
        re.IGNORECASE,
    )
    registry = build_available_semantic_validator_registry()

    for validator_id in registry:
        validate_semantic_capability_name(validator_id)
        assert not active_pi.search(validator_id)
    for judge_id in PLANNED_JUDGE_IDS:
        assert judge_id not in registry


def test_registry_does_not_register_judges_by_default() -> None:
    default_registry = build_default_semantic_validator_registry()
    available_registry = build_available_semantic_validator_registry()

    for judge_id in JUDGE_VALIDATORS.values():
        assert judge_id not in default_registry
        assert judge_id not in available_registry


def test_unknown_validator_reports_unavailable() -> None:
    result = unavailable_validator_result("scene_energy_contract", reason="validator_not_registered")

    assert result["available"] is False
    assert result["passed"] is False
    assert result["status"] == "unavailable"


def test_plan_enforced_with_available_registry_does_not_false_green_missing_context() -> None:
    registry = build_available_semantic_validator_registry()
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=registry,
        dispatch_context={},
        feature_flag_enabled=True,
    )

    assert "scene_energy_contract" in report.validators_unavailable
    assert "scene_energy_contract" not in report.actually_executed


def test_plan_enforced_with_populated_context_can_execute_scene_energy() -> None:
    registry = build_available_semantic_validator_registry()
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=registry,
        dispatch_context={
            "scene_energy_target": {"minimum_actor_response_count": 1, "energy_level": "medium"},
            "structured_output": {"spoken_lines": [{"speaker_id": "narrator", "text": "A door opens."}]},
        },
        feature_flag_enabled=True,
    )

    assert "scene_energy_contract" in report.actually_executed


def test_build_semantic_validator_registry_include_flag() -> None:
    assert build_semantic_validator_registry() == {}
    available = build_semantic_validator_registry(include_available_adapters=True)
    assert "scene_energy_contract" in available
    assert available == build_available_semantic_validator_registry()


def test_opening_enforced_ids_subset_of_planned_local_validators() -> None:
    for validator_id in OPENING_ENFORCED_VALIDATORS:
        assert validator_id in PLANNED_ALL_DISPATCH_IDS
