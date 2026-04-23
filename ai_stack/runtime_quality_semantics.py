"""Canonical runtime quality and degradation semantics for live turn output."""

from __future__ import annotations

from typing import Any

from ai_stack.runtime_turn_contracts import (
    DEGRADATION_SIGNAL_ACTOR_LANES_VALIDATION_GATED,
    DEGRADATION_SIGNAL_DEGRADED_COMMIT,
    DEGRADATION_SIGNAL_FALLBACK_USED,
    DEGRADATION_SIGNAL_NON_FACTUAL_STAGING,
    DEGRADATION_SIGNAL_PROSE_ONLY_RECOVERY,
    DEGRADATION_SIGNAL_RETRY_EXHAUSTED,
    DEGRADATION_SIGNAL_THIN_PROSE_OVERRIDE,
    DEGRADATION_SIGNAL_VALUES,
    DEGRADATION_SIGNAL_WEAK_SIGNAL_ACCEPTED,
    QUALITY_CLASS_DEGRADED,
    QUALITY_CLASS_FAILED,
    QUALITY_CLASS_HEALTHY,
    QUALITY_CLASS_WEAK_BUT_LEGAL,
    QualityClass,
)

_DEGRADED_SIGNALS = frozenset(
    {
        DEGRADATION_SIGNAL_FALLBACK_USED,
        DEGRADATION_SIGNAL_NON_FACTUAL_STAGING,
        DEGRADATION_SIGNAL_DEGRADED_COMMIT,
        DEGRADATION_SIGNAL_ACTOR_LANES_VALIDATION_GATED,
        DEGRADATION_SIGNAL_RETRY_EXHAUSTED,
    }
)

_WEAK_SIGNALS = frozenset(
    {
        DEGRADATION_SIGNAL_WEAK_SIGNAL_ACCEPTED,
        DEGRADATION_SIGNAL_PROSE_ONLY_RECOVERY,
        DEGRADATION_SIGNAL_THIN_PROSE_OVERRIDE,
    }
)


def _append_signal(signals: list[str], signal: str) -> None:
    if signal not in DEGRADATION_SIGNAL_VALUES:
        return
    if signal not in signals:
        signals.append(signal)


def canonical_degradation_signals(
    *,
    state: dict[str, Any],
    fallback_taken: bool,
) -> list[str]:
    """Build canonical degradation signals from runtime turn state."""
    signals: list[str] = []

    generation = state.get("generation") if isinstance(state.get("generation"), dict) else {}
    validation = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
    visibility_markers = (
        state.get("visibility_class_markers")
        if isinstance(state.get("visibility_class_markers"), list)
        else []
    )
    self_correction = state.get("self_correction") if isinstance(state.get("self_correction"), dict) else {}
    gate_outcome = (
        validation.get("dramatic_effect_gate_outcome")
        if isinstance(validation.get("dramatic_effect_gate_outcome"), dict)
        else {}
    )

    if fallback_taken or bool(generation.get("fallback_used")):
        _append_signal(signals, DEGRADATION_SIGNAL_FALLBACK_USED)

    if (
        validation.get("dramatic_effect_weak_signal") is True
        or validation.get("dramatic_quality_gate") == "effect_gate_weak_signal"
        or gate_outcome.get("gate_result") == "accepted_with_weak_signal"
    ):
        _append_signal(signals, DEGRADATION_SIGNAL_WEAK_SIGNAL_ACCEPTED)

    if "non_factual_staging" in visibility_markers:
        _append_signal(signals, DEGRADATION_SIGNAL_NON_FACTUAL_STAGING)
    if "actor_lanes_validation_gated" in visibility_markers:
        _append_signal(signals, DEGRADATION_SIGNAL_ACTOR_LANES_VALIDATION_GATED)

    reason = str(validation.get("reason") or "").strip().lower()
    if reason == "degraded_commit_after_retries":
        _append_signal(signals, DEGRADATION_SIGNAL_DEGRADED_COMMIT)
        _append_signal(signals, DEGRADATION_SIGNAL_RETRY_EXHAUSTED)
    elif reason == "opening_leniency_approved":
        _append_signal(signals, DEGRADATION_SIGNAL_PROSE_ONLY_RECOVERY)

    attempts = self_correction.get("attempts") if isinstance(self_correction.get("attempts"), list) else []
    if any(isinstance(attempt, dict) and attempt.get("preserve_actor_lanes") for attempt in attempts):
        _append_signal(signals, DEGRADATION_SIGNAL_PROSE_ONLY_RECOVERY)

    rationale_codes = gate_outcome.get("effect_rationale_codes")
    if isinstance(rationale_codes, list):
        for code in rationale_codes:
            if str(code).strip() == "actor_lanes_thin_prose_override":
                _append_signal(signals, DEGRADATION_SIGNAL_THIN_PROSE_OVERRIDE)
                break

    return signals


def canonical_quality_class(
    *,
    validation_outcome: dict[str, Any],
    commit_applied: bool,
    degradation_signals: list[str],
) -> QualityClass:
    """Classify turn quality using canonical health/weak/degraded/failed rules."""
    status = str(validation_outcome.get("status") or "").strip().lower()
    if status != "approved":
        return QUALITY_CLASS_FAILED

    signal_set = {s for s in degradation_signals if s}
    if any(signal in _DEGRADED_SIGNALS for signal in signal_set):
        return QUALITY_CLASS_DEGRADED
    if any(signal in _WEAK_SIGNALS for signal in signal_set):
        return QUALITY_CLASS_WEAK_BUT_LEGAL
    if not commit_applied:
        return QUALITY_CLASS_DEGRADED
    return QUALITY_CLASS_HEALTHY


def canonical_quality_summary(
    *,
    state: dict[str, Any],
    fallback_taken: bool,
) -> dict[str, Any]:
    """Return canonical quality fields shared across graph/package/ui surfaces."""
    validation = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
    committed = state.get("committed_result") if isinstance(state.get("committed_result"), dict) else {}
    signals = canonical_degradation_signals(state=state, fallback_taken=fallback_taken)
    quality_class = canonical_quality_class(
        validation_outcome=validation,
        commit_applied=bool(committed.get("commit_applied")),
        degradation_signals=signals,
    )
    summary = {
        "quality_class": quality_class,
        "degradation_signals": signals,
        "degradation_summary": ", ".join(signals) if signals else "none",
    }
    return summary

