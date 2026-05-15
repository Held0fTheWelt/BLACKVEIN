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


def test_scoped_co_authority_flag_defaults_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_stack.runtime_aspect_ledger import (
        ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
        resolve_adr0041_scoped_co_authority_enabled,
    )

    monkeypatch.delenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, raising=False)

    enabled, warnings = resolve_adr0041_scoped_co_authority_enabled()

    assert enabled is False
    assert warnings == ()


def test_invalid_scoped_co_authority_flag_fails_closed() -> None:
    from ai_stack.runtime_aspect_ledger import resolve_adr0041_scoped_co_authority_enabled

    enabled, warnings = resolve_adr0041_scoped_co_authority_enabled(env_value="maybe")

    assert enabled is False
    assert warnings
    assert "scoped co-authority decision disabled" in warnings[0]


def test_readiness_preview_flag_defaults_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_stack.runtime_aspect_ledger import (
        ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
        resolve_adr0041_readiness_co_authority_preview_enabled,
    )

    monkeypatch.delenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, raising=False)
    enabled, warnings = resolve_adr0041_readiness_co_authority_preview_enabled()

    assert enabled is False
    assert warnings == ()


def test_invalid_readiness_preview_flag_fails_closed() -> None:
    from ai_stack.runtime_aspect_ledger import (
        resolve_adr0041_readiness_co_authority_preview_enabled,
    )

    enabled, warnings = resolve_adr0041_readiness_co_authority_preview_enabled(env_value="later")

    assert enabled is False
    assert warnings
    assert "readiness co-authority preview disabled" in warnings[0]


def test_scoped_readiness_enforcement_flag_defaults_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_stack.runtime_aspect_ledger import (
        ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV,
        resolve_adr0041_scoped_readiness_enforcement_enabled,
    )

    monkeypatch.delenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, raising=False)
    enabled, warnings = resolve_adr0041_scoped_readiness_enforcement_enabled()

    assert enabled is False
    assert warnings == ()


def test_invalid_scoped_readiness_enforcement_flag_fails_closed() -> None:
    from ai_stack.runtime_aspect_ledger import (
        resolve_adr0041_scoped_readiness_enforcement_enabled,
    )

    enabled, warnings = resolve_adr0041_scoped_readiness_enforcement_enabled(env_value="pilot-maybe")

    assert enabled is False
    assert warnings
    assert "scoped readiness enforcement disabled" in warnings[0]


def test_scoped_readiness_aggregation_flag_defaults_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_stack.runtime_aspect_ledger import (
        ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV,
        resolve_adr0041_scoped_readiness_aggregation_enabled,
    )

    monkeypatch.delenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, raising=False)
    enabled, warnings = resolve_adr0041_scoped_readiness_aggregation_enabled()

    assert enabled is False
    assert warnings == ()


def test_invalid_scoped_readiness_aggregation_flag_fails_closed() -> None:
    from ai_stack.runtime_aspect_ledger import resolve_adr0041_scoped_readiness_aggregation_enabled

    enabled, warnings = resolve_adr0041_scoped_readiness_aggregation_enabled(env_value="on-maybe")

    assert enabled is False
    assert warnings
    assert "scoped readiness aggregation disabled" in warnings[0]


def test_runtime_readiness_consumer_flag_defaults_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_stack.runtime_aspect_ledger import (
        ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV,
        resolve_adr0041_runtime_readiness_consumer_enabled,
    )

    monkeypatch.delenv(ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV, raising=False)
    enabled, warnings = resolve_adr0041_runtime_readiness_consumer_enabled()

    assert enabled is False
    assert warnings == ()


def test_invalid_runtime_readiness_consumer_flag_fails_closed() -> None:
    from ai_stack.runtime_aspect_ledger import resolve_adr0041_runtime_readiness_consumer_enabled

    enabled, warnings = resolve_adr0041_runtime_readiness_consumer_enabled(env_value="maybe")

    assert enabled is False
    assert warnings
    assert "runtime readiness consumer disabled" in warnings[0].lower()


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


def test_runtime_projection_without_graph_sidecar_stays_dry_run_with_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ai_stack.runtime_aspect_ledger import (
        initialize_runtime_aspect_ledger,
        normalize_runtime_aspect_ledger,
    )

    monkeypatch.setenv(
        ADR0041_VALIDATOR_DISPATCH_MODE_ENV,
        ValidatorDispatchMode.PLAN_ENFORCED.value,
    )
    ledger = initialize_runtime_aspect_ledger(
        session_id="dispatch-flag-no-sidecar",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )
    normalized = normalize_runtime_aspect_ledger(ledger)
    projection = normalized["runtime_intelligence_projection"]
    report = projection["validator_dispatch_report"]

    assert report["mode"] == ValidatorDispatchMode.DRY_RUN.value
    assert report["execution_changed"] is False
    assert report["actually_executed"] == []
    assert report["validators_unavailable"] == []
    assert report["feature_flag_enabled"] is False
    assert "validation_authority_preview" not in projection
    assert "validation_authority_bridge" not in projection
    assert "authority_handoff_candidate" not in projection


def test_explicit_mode_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, "plan_enforced")

    mode, _warnings = resolve_validator_dispatch_mode(explicit_mode=ValidatorDispatchMode.DRY_RUN)

    assert mode is ValidatorDispatchMode.DRY_RUN
