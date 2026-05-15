from __future__ import annotations

import pytest

from ai_stack.capability_selector import ActiveActor, TurnKind, TurnSituation, select_capabilities
from ai_stack.capability_validator_dispatch import (
    ADR0041_VALIDATOR_DISPATCH_MODE_ENV,
    DEFAULT_VALIDATOR_DISPATCH_MODE,
    ValidatorDispatchMode,
    build_validator_dispatch_report,
    resolve_validator_dispatch_mode,
)
from ai_stack.capability_validator_plan import build_validator_execution_plan


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


def test_default_dispatch_mode_remains_dry_run() -> None:
    mode, warnings = resolve_validator_dispatch_mode()
    report = build_validator_dispatch_report(_opening_plan(), mode=mode)

    assert mode is ValidatorDispatchMode.DRY_RUN
    assert warnings == ()
    assert report.mode is ValidatorDispatchMode.DRY_RUN
    assert report.mode.value == DEFAULT_VALIDATOR_DISPATCH_MODE
    assert report.execution_changed is False
    assert report.actually_executed == ()


def test_missing_feature_flag_uses_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, raising=False)

    mode, warnings = resolve_validator_dispatch_mode()

    assert mode is ValidatorDispatchMode.DRY_RUN
    assert warnings == ()


def test_invalid_feature_flag_fails_closed_or_warns() -> None:
    mode, warnings = resolve_validator_dispatch_mode(env_value="not_a_real_mode")

    assert mode is ValidatorDispatchMode.DRY_RUN
    assert warnings
    assert "falling back" in warnings[0]


def test_env_plan_enforced_requires_explicit_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, "plan_enforced")

    mode, _warnings = resolve_validator_dispatch_mode()

    assert mode is ValidatorDispatchMode.PLAN_ENFORCED


def test_runtime_projection_defaults_to_dry_run_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_stack.runtime_aspect_ledger import initialize_runtime_aspect_ledger

    monkeypatch.delenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, raising=False)
    ledger = initialize_runtime_aspect_ledger(
        session_id="dispatch-flag-opening",
        module_id="example_module",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    report = ledger["runtime_intelligence_projection"]["validator_dispatch_report"]

    assert report["mode"] == "dry_run"
    assert report["execution_changed"] is False
    assert report["actually_executed"] == []
    assert report["feature_flag_enabled"] is False


def test_explicit_mode_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, "plan_enforced")

    mode, _warnings = resolve_validator_dispatch_mode(explicit_mode=ValidatorDispatchMode.DRY_RUN)

    assert mode is ValidatorDispatchMode.DRY_RUN
