from __future__ import annotations

from typing import Any

from ai_stack.capability_selector import ActiveActor, TurnKind, TurnSituation, select_capabilities
from ai_stack.capability_validator_dispatch import (
    ValidatorDispatchMode,
    build_validator_dispatch_report,
)
from ai_stack.capability_validator_plan import ValidatorPlanEntry, build_validator_execution_plan
from ai_stack.runtime_aspect_ledger import (
    ASPECT_COMMIT,
    ASPECT_VALIDATION,
    initialize_runtime_aspect_ledger,
)

OPENING_ENFORCED_VALIDATORS = (
    "narrator_authority_contract",
    "scene_energy_contract",
    "environment_state_contract",
    "information_disclosure_contract",
    "voice_consistency_contract",
)

OPENING_EXCLUDED_VALIDATORS = (
    "npc_agency_contract",
    "player_intent_contract",
    "action_resolution_contract",
    "consequence_cascade_contract",
    "forecast_contract",
    "silence_negative_space_contract",
    "dramatic_irony_contract",
)


def _opening_plan():
    selection = select_capabilities(
        TurnSituation(
            turn_kind=TurnKind.OPENING,
            active_actor=ActiveActor.NARRATOR,
            player_input_present=False,
            npc_decision_required=False,
            visible_projection_required=True,
            canonical_scene_seed=True,
        )
    )
    return build_validator_execution_plan(selection)


def _opening_registry(*, fail_id: str | None = None) -> dict[str, Any]:
    registry: dict[str, Any] = {}

    def _make(validator_id: str):
        def _run(entry: ValidatorPlanEntry, context: dict[str, Any]) -> dict[str, Any]:
            if validator_id == fail_id:
                return {"validator_id": validator_id, "status": "unavailable"}
            return {
                "validator_id": validator_id,
                "status": "local_stub_executed",
                "capability": entry.capability,
                "proof_level": context.get("proof_level"),
            }

        return _run

    for validator_id in OPENING_ENFORCED_VALIDATORS:
        registry[validator_id] = _make(validator_id)
    return registry


def test_explicit_plan_enforced_mode_is_required() -> None:
    dry_report = build_validator_dispatch_report(_opening_plan())
    enforced_report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=_opening_registry(),
        feature_flag_enabled=True,
    )

    assert dry_report.mode is ValidatorDispatchMode.DRY_RUN
    assert enforced_report.mode is ValidatorDispatchMode.PLAN_ENFORCED
    assert enforced_report.feature_flag_enabled is True


def test_plan_enforced_can_execute_registered_local_validators() -> None:
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=_opening_registry(),
        feature_flag_enabled=True,
    )

    assert report.execution_changed is True
    assert report.actually_executed == OPENING_ENFORCED_VALIDATORS
    assert report.validators_unavailable == ()


def test_plan_enforced_does_not_execute_excluded_validators() -> None:
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=_opening_registry(),
        feature_flag_enabled=True,
    )

    for validator_id in OPENING_EXCLUDED_VALIDATORS:
        assert validator_id in report.validators_would_skip
        assert validator_id not in report.actually_executed


def test_plan_enforced_does_not_execute_judges() -> None:
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=_opening_registry(),
        feature_flag_enabled=True,
    )

    assert report.judges_would_be_disallowed
    assert not any(item.endswith("_judge") for item in report.actually_executed)
    assert report.judge_execution_changed is False


def test_plan_enforced_does_not_change_commit_or_readiness_gates() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="plan-enforced-readiness",
        module_id="example_module",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    aspects = ledger["turn_aspect_ledger"]

    assert aspects[ASPECT_VALIDATION]["status"] == "missing"
    assert aspects[ASPECT_COMMIT]["status"] == "missing"


def test_plan_enforced_projection_is_local_only() -> None:
    projection = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=_opening_registry(),
        feature_flag_enabled=True,
    ).to_runtime_projection()["validator_dispatch_report"]

    assert projection["proof_level"] == "local_only"
    assert projection["live_or_staging_evidence"] is False
    assert projection["capability_promoted"] is False
    assert projection["commit_gate_changed"] is False
    assert projection["readiness_gate_changed"] is False
    assert projection["judge_execution_changed"] is False


def test_plan_enforced_does_not_claim_live_or_staging_evidence() -> None:
    projection = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=_opening_registry(),
        feature_flag_enabled=True,
    ).to_runtime_projection()["validator_dispatch_report"]

    assert projection["live_or_staging_evidence"] is False
    assert projection["live_verified"] is False
    assert projection["staging_verified"] is False
    assert projection["provider_verified"] is False


def test_unknown_validator_is_reported_unavailable_not_passed() -> None:
    registry = _opening_registry()
    registry.pop("scene_energy_contract")
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=registry,
        feature_flag_enabled=True,
    )

    assert "scene_energy_contract" in report.validators_unavailable
    assert "scene_energy_contract" not in report.actually_executed
    unavailable_entries = [entry for entry in report.entries if entry.unavailable]
    assert any(entry.validator_id == "scene_energy_contract" for entry in unavailable_entries)
    assert not any(
        entry.validator_id == "scene_energy_contract" and entry.actually_executed
        for entry in report.entries
    )


def test_opening_plan_enforced_only_runs_opening_enforced_validators() -> None:
    report = build_validator_dispatch_report(
        _opening_plan(),
        mode=ValidatorDispatchMode.PLAN_ENFORCED,
        validator_registry=_opening_registry(),
        feature_flag_enabled=True,
    )

    assert report.validators_would_run == OPENING_ENFORCED_VALIDATORS
    assert report.actually_executed == OPENING_ENFORCED_VALIDATORS
    for validator_id in OPENING_EXCLUDED_VALIDATORS:
        assert validator_id not in report.actually_executed
