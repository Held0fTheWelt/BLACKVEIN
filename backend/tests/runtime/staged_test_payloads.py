"""Shared bounded payloads for Task 1 multi-stage Runtime tests (preflight / signal)."""

from __future__ import annotations

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse


PREFLIGHT_PAYLOAD = {
    "runtime_stage": "preflight",
    "ambiguity_score": 0.15,
    "trigger_signals": [],
    "repetition_risk": "low",
    "classification_label": "test",
    "preflight_ok": True,
}


def signal_payload(*, needs_llm_synthesis: bool, skip_reason: str | None = None) -> dict:
    return {
        "runtime_stage": "signal_consistency",
        "needs_llm_synthesis": needs_llm_synthesis,
        "skip_synthesis_reason": skip_reason,
        "narrative_summary": "[test] signal narrative summary",
        "consistency_notes": "test stable",
        "consistency_flags": [],
    }


def maybe_staged_prelude_response(request: AdapterRequest) -> AdapterResponse | None:
    """If ``runtime_stage`` is set for early pipeline stages, return a valid bounded payload."""
    stage = (request.metadata or {}).get("runtime_stage")
    if stage == "preflight":
        return AdapterResponse(
            raw_output="[test preflight]",
            structured_payload=dict(PREFLIGHT_PAYLOAD),
            error=None,
        )
    if stage == "signal_consistency":
        return AdapterResponse(
            raw_output="[test signal]",
            structured_payload=signal_payload(needs_llm_synthesis=True),
            error=None,
        )
    return None
