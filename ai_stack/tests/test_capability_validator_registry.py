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
    build_opening_enforced_semantic_validator_registry,
    build_semantic_validator_registry,
    unavailable_validator_result,
)
from ai_stack.environment_state_contracts import build_environment_model, initial_environment_state
from ai_stack.narrator_authority_validation import evaluate_narrator_authority_contract
from ai_stack.environment_state_contracts import evaluate_environment_state_contract
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


def test_opening_registry_contains_safe_opening_enforced_adapters() -> None:
    opening_registry = build_opening_enforced_semantic_validator_registry()

    assert set(opening_registry) == set(OPENING_ENFORCED_VALIDATORS)


def test_narrator_authority_adapter_requires_context() -> None:
    result = evaluate_narrator_authority_contract(structured_output=None, proposed_state_effects=None)

    assert result["available"] is False
    assert result["passed"] is False
    assert result["reason"] == "missing_required_context"


def test_environment_state_adapter_requires_context() -> None:
    result = evaluate_environment_state_contract(environment_state=None, module_id=None)

    assert result["available"] is False
    assert result["passed"] is False
    assert result["reason"] == "missing_required_context"


def test_narrator_authority_adapter_returns_local_only_result() -> None:
    result = evaluate_narrator_authority_contract(
        structured_output={"narration_summary": "A narrator sets the room."},
        turn_number=0,
        narrator_required=True,
    )

    assert result["available"] is True
    assert result["passed"] is True
    assert result["proof_level"] == "local_only"
    assert result["live_or_staging_evidence"] is False


def test_environment_state_adapter_returns_local_only_result() -> None:
    model = build_environment_model(module_id="god_of_carnage")
    state = initial_environment_state(module_id="god_of_carnage", environment_model=model, turn_number=0)
    result = evaluate_environment_state_contract(
        environment_state=state,
        module_id="god_of_carnage",
        environment_model=model,
        turn_number=0,
    )

    assert result["available"] is True
    assert result["passed"] is True
    assert result["proof_level"] == "local_only"
    assert result["live_or_staging_evidence"] is False


def _opening_dispatch_context() -> dict:
    module_id = "god_of_carnage"
    model = build_environment_model(module_id=module_id)
    environment_state = initial_environment_state(
        module_id=module_id,
        environment_model=model,
        turn_number=0,
    )
    return {
        "module_id": module_id,
        "turn_number": 0,
        "narrator_required": True,
        "structured_output": {
            "narration_summary": "The foyer waits in brittle calm.",
            "spoken_lines": [{"speaker_id": "narrator", "text": "The light stays low."}],
        },
        "environment_state": environment_state,
        "environment_model": model,
        "scene_energy_target": {"minimum_actor_response_count": 1, "energy_level": "medium"},
        "information_disclosure_target": {"policy_enabled": False},
        "voice_profiles": [],
    }


def test_opening_plan_enforced_executes_all_available_opening_enforced_validators() -> None:
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_opening_enforced_semantic_validator_registry(),
        dispatch_context=_opening_dispatch_context(),
        feature_flag_enabled=True,
    )

    assert set(report.actually_executed) == set(OPENING_ENFORCED_VALIDATORS)
    assert report.execution_changed is True


def test_opening_plan_enforced_does_not_execute_excluded_validators() -> None:
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=build_opening_enforced_semantic_validator_registry(),
        dispatch_context=_opening_dispatch_context(),
        feature_flag_enabled=True,
    )

    for validator_id in (
        "npc_agency_contract",
        "player_intent_contract",
        "action_resolution_contract",
        "consequence_cascade_contract",
        "forecast_contract",
        "silence_negative_space_contract",
        "dramatic_irony_contract",
    ):
        assert validator_id in report.validators_would_skip
        assert validator_id not in report.actually_executed


def test_default_registry_remains_empty() -> None:
    assert build_default_semantic_validator_registry() == {}


def test_default_dispatch_remains_dry_run() -> None:
    report = build_validator_dispatch_report(_opening_plan())

    assert report.mode.value == "dry_run"
    assert report.execution_changed is False
    assert report.actually_executed == ()


def test_unavailable_still_does_not_false_green() -> None:
    registry = build_opening_enforced_semantic_validator_registry()
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=registry,
        dispatch_context={},
        feature_flag_enabled=True,
    )

    assert report.actually_executed == ()
    assert set(report.validators_unavailable) == set(OPENING_ENFORCED_VALIDATORS)
