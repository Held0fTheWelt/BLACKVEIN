"""ADR-0041 runtime readiness consumer (veto-only overlay on legacy readiness)."""

from __future__ import annotations

import pytest

from ai_stack.capabilities.capability_validator_dispatch import (
    ADR0041_VALIDATOR_DISPATCH_MODE_ENV,
    ValidatorDispatchMode,
)
from ai_stack.runtime_aspect_ledger import (
    ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
    ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV,
    ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV,
    resolve_adr0041_runtime_readiness_consumer_enabled,
)
from ai_stack.runtime_readiness_consumer import (
    build_adr0041_readiness_projection_echo,
    degradation_signals_from_latest_turn,
    resolve_runtime_readiness_with_adr0041,
    runtime_intelligence_projection_from_turn_aspect_ledger,
)


def _set_full_adr0041_readiness_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV, "true")


def _agg(*, aggregated: str, veto: bool = False) -> dict:
    return {
        "aggregated_readiness": aggregated,
        "adr0041_veto_applied": veto,
        "blockers": [],
    }


def test_default_final_readiness_unchanged_without_consumer_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_adr0041_readiness_stack(monkeypatch)
    monkeypatch.delenv(ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV, raising=False)
    rip = {"readiness_aggregation_decision": _agg(aggregated="block", veto=True)}
    r = resolve_runtime_readiness_with_adr0041(
        legacy_runtime_session_ready=True,
        legacy_can_execute=True,
        opening_generation_status="ready_with_opening",
        runtime_intelligence_projection=rip,
        degradation_signals=[],
    )
    assert r["runtime_ready"] is True
    assert r["can_execute"] is True
    assert r["source"] == "legacy_readiness"
    assert r["consumer_enabled"] is False
    assert r["validation_outcome_changed"] is False
    assert r["commit_gate_changed"] is False


def test_invalid_consumer_flag_fail_closed() -> None:
    enabled, warnings = resolve_adr0041_runtime_readiness_consumer_enabled(env_value="yellow")
    assert enabled is False
    assert warnings
    assert "runtime readiness consumer disabled" in warnings[0].lower()


def test_no_aggregation_decision_legacy_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_adr0041_readiness_stack(monkeypatch)
    r = resolve_runtime_readiness_with_adr0041(
        legacy_runtime_session_ready=True,
        legacy_can_execute=True,
        opening_generation_status="ready_with_opening",
        runtime_intelligence_projection={"validator_dispatch_report": {}},
        degradation_signals=[],
    )
    assert r["runtime_ready"] is True
    assert r["can_execute"] is True
    assert r["reason"] == "readiness_aggregation_decision_absent"


def test_allow_plus_legacy_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_adr0041_readiness_stack(monkeypatch)
    rip = {"readiness_aggregation_decision": _agg(aggregated="allow")}
    r = resolve_runtime_readiness_with_adr0041(
        legacy_runtime_session_ready=True,
        legacy_can_execute=True,
        opening_generation_status="ready_with_opening",
        runtime_intelligence_projection=rip,
        degradation_signals=[],
    )
    assert r["runtime_ready"] is True
    assert r["can_execute"] is True
    assert r["reason"] == "legacy_allow_adr0041_allow"


def test_block_plus_legacy_allow_veto(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_adr0041_readiness_stack(monkeypatch)
    rip = {"readiness_aggregation_decision": _agg(aggregated="block", veto=True)}
    r = resolve_runtime_readiness_with_adr0041(
        legacy_runtime_session_ready=True,
        legacy_can_execute=True,
        opening_generation_status="ready_with_opening",
        runtime_intelligence_projection=rip,
        degradation_signals=[],
    )
    assert r["runtime_ready"] is False
    assert r["can_execute"] is False
    assert r["reason"] == "adr0041_veto_over_legacy_allow"


def test_allow_plus_legacy_reject_no_upgrade(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_adr0041_readiness_stack(monkeypatch)
    rip = {"readiness_aggregation_decision": _agg(aggregated="allow")}
    r = resolve_runtime_readiness_with_adr0041(
        legacy_runtime_session_ready=False,
        legacy_can_execute=False,
        opening_generation_status="blocked_missing_opening",
        runtime_intelligence_projection=rip,
        degradation_signals=[],
    )
    assert r["runtime_ready"] is False
    assert r["can_execute"] is False
    assert r["reason"] == "legacy_reject_no_adr0041_upgrade"


def test_block_plus_legacy_reject(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_adr0041_readiness_stack(monkeypatch)
    rip = {"readiness_aggregation_decision": _agg(aggregated="block", veto=True)}
    r = resolve_runtime_readiness_with_adr0041(
        legacy_runtime_session_ready=False,
        legacy_can_execute=False,
        opening_generation_status="blocked_missing_opening",
        runtime_intelligence_projection=rip,
        degradation_signals=[],
    )
    assert r["runtime_ready"] is False
    assert r["can_execute"] is False


def test_unknown_base_does_not_become_allow_on_adr_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_adr0041_readiness_stack(monkeypatch)
    rip = {"readiness_aggregation_decision": _agg(aggregated="allow")}
    r = resolve_runtime_readiness_with_adr0041(
        legacy_runtime_session_ready=True,
        legacy_can_execute=False,
        opening_generation_status="mixed",
        runtime_intelligence_projection=rip,
        degradation_signals=[],
    )
    assert r["runtime_ready"] is True
    assert r["can_execute"] is False
    assert r["base_readiness"] == "unknown"


def test_upstream_not_met_no_veto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.delenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, raising=False)
    rip = {"readiness_aggregation_decision": _agg(aggregated="block")}
    r = resolve_runtime_readiness_with_adr0041(
        legacy_runtime_session_ready=True,
        legacy_can_execute=True,
        opening_generation_status="ready_with_opening",
        runtime_intelligence_projection=rip,
        degradation_signals=[],
    )
    assert r["runtime_ready"] is True
    assert r["reason"] == "adr0041_upstream_prerequisites_not_met"


def test_runtime_intelligence_projection_extraction() -> None:
    turn = {
        "turn_aspect_ledger": {
            "runtime_intelligence_projection": {"readiness_aggregation_decision": _agg(aggregated="allow")}
        }
    }
    rip = runtime_intelligence_projection_from_turn_aspect_ledger(turn)
    assert isinstance(rip, dict)
    assert "readiness_aggregation_decision" in rip


def test_degradation_signals_from_governance_surface() -> None:
    turn = {"runtime_governance_surface": {"degradation_signals": ["x"]}}
    assert degradation_signals_from_latest_turn(turn) == ["x"]


def test_readiness_projection_echo_read_only_shape() -> None:
    rip = {
        "readiness_policy_input": {"readiness_input": "block"},
        "readiness_aggregation_decision": {"aggregated_readiness": "block"},
        "readiness_co_authority_enforcement": {"readiness_input": "allow"},
        "readiness_co_authority_preview": {"policy_stage": "shadow_only"},
    }
    echo = build_adr0041_readiness_projection_echo(rip)
    assert echo["read_only"] is True
    assert echo["readiness_policy_input"]["readiness_input"] == "block"
    assert echo["adr0041_runtime_readiness_consumer"]["value"] is None


def test_resolve_includes_mutating_consumer_anchor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ADR0041_VALIDATOR_DISPATCH_MODE_ENV, ValidatorDispatchMode.PLAN_ENFORCED.value)
    monkeypatch.setenv(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV, "true")
    monkeypatch.setenv(ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV, "true")
    rip = {"readiness_aggregation_decision": _agg(aggregated="allow")}
    r = resolve_runtime_readiness_with_adr0041(
        legacy_runtime_session_ready=True,
        legacy_can_execute=True,
        opening_generation_status="ready_with_opening",
        runtime_intelligence_projection=rip,
        degradation_signals=[],
    )
    assert r["mutating_readiness_consumer_anchor"].endswith("_player_session_bundle")
    assert r["mutates_bundle_fields"] == ["runtime_session_ready", "can_execute"]


def test_retrieval_authority_is_reported_but_not_used_as_readiness_truth(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_adr0041_readiness_stack(monkeypatch)
    rip = {"readiness_aggregation_decision": _agg(aggregated="allow")}
    r = resolve_runtime_readiness_with_adr0041(
        legacy_runtime_session_ready=True,
        legacy_can_execute=True,
        opening_generation_status="ready_with_opening",
        runtime_intelligence_projection=rip,
        degradation_signals=[],
        retrieval_payload={"retrieval_authority": {"authority_level": "retrieved_unverified"}},
    )
    assert r["runtime_ready"] is True
    assert r["can_execute"] is True
    assert r["retrieval_unverified"] is True
    assert r["retrieval_authority_level"] == "retrieved_unverified"


def test_blocking_degradation_signal_vetoes_legacy_allow(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_full_adr0041_readiness_stack(monkeypatch)
    rip = {"readiness_aggregation_decision": _agg(aggregated="allow")}
    r = resolve_runtime_readiness_with_adr0041(
        legacy_runtime_session_ready=True,
        legacy_can_execute=True,
        opening_generation_status="ready_with_opening",
        runtime_intelligence_projection=rip,
        degradation_signals=["fallback", "diagnostic_only_marker"],
    )
    assert r["runtime_ready"] is False
    assert r["can_execute"] is False
    assert r["reason"] == "adr0041_degradation_veto_over_legacy_allow"
    assert r["degradation_blocking_signal"] is True
    assert "fallback" in r["degradation_blockers"]
