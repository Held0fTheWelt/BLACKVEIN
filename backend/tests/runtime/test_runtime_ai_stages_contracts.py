"""Unit tests for Task 1 runtime stage contracts (deterministic gates and hints)."""

from app.runtime.model_routing_contracts import EscalationHint
from app.runtime.runtime_ai_stages import (
    PreflightStageOutput,
    SignalStageOutput,
    compute_needs_llm_synthesis,
    escalation_hints_from_preflight,
)


def test_escalation_hints_from_preflight_deterministic():
    pf = PreflightStageOutput(
        ambiguity_score=0.9,
        repetition_risk="high",
        trigger_signals=[],
    )
    hints = escalation_hints_from_preflight(pf)
    assert EscalationHint.continuity_risk in hints
    assert EscalationHint.ambiguity_high in hints


def test_compute_needs_llm_synthesis_forces_on_signal_parse_failure():
    sig = SignalStageOutput(needs_llm_synthesis=False, skip_synthesis_reason="slm_sufficient")
    need, reason = compute_needs_llm_synthesis(
        signal=sig,
        signal_parse_ok=False,
        preflight_parse_ok=True,
    )
    assert need is True
    assert "forcing_synthesis" in reason


def test_compute_needs_llm_synthesis_respects_slm_sufficient_signal():
    sig = SignalStageOutput(
        needs_llm_synthesis=False,
        skip_synthesis_reason="slm_sufficient",
        narrative_summary="ok",
    )
    need, reason = compute_needs_llm_synthesis(
        signal=sig,
        signal_parse_ok=True,
        preflight_parse_ok=True,
    )
    assert need is False
    assert reason == "slm_sufficient"
