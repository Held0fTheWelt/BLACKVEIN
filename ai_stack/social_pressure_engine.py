"""Social-pressure metric derivation and contract validation."""

from __future__ import annotations

from typing import Any

from ai_stack.social_pressure_contracts import (
    SOCIAL_PRESSURE_BANDS,
    SOCIAL_PRESSURE_FAILURE_CODES,
    SOCIAL_PRESSURE_SCHEMA_VERSION,
    SocialPressureEvidenceRef,
    SocialPressureState,
    SocialPressureTarget,
    SocialPressureValidation,
    normalize_social_pressure_policy,
)


_DEFAULT_SOURCE_SCORES: dict[str, dict[str, float]] = {
    "social_risk_band": {"low": 0.2, "moderate": 0.5, "high": 0.78},
    "scene_pressure_state": {
        "low": 0.2,
        "moderate_tension": 0.52,
        "stabilization_attempt": 0.56,
        "high_blame": 0.86,
        "thread_pressure_high": 0.82,
    },
    "thread_pressure_state": {
        "thread_pressure_high": 0.82,
        "high_unresolved_thread_pressure": 0.9,
    },
    "scene_energy_transition": {
        "release": 0.38,
        "deescalate": 0.36,
        "hold": 0.48,
        "pivot": 0.58,
        "rise": 0.72,
        "interrupt": 0.86,
    },
    "scene_energy_pressure_vector": {
        "repair": 0.38,
        "evasive": 0.52,
        "social": 0.58,
        "moral": 0.62,
        "exposure": 0.68,
        "rupture": 0.82,
    },
    "pacing_cadence": {
        "breathe": 0.28,
        "release": 0.36,
        "hold": 0.48,
        "pivot": 0.58,
        "press": 0.72,
        "interrupt": 0.84,
    },
    "pressure_shift": {
        "de-escalated": 0.32,
        "held": 0.48,
        "shifted": 0.56,
        "escalated": 0.78,
    },
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_key(value: Any) -> str:
    return _clean_text(value).lower()


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))


def _evidence(source: str, field: str, value: Any) -> SocialPressureEvidenceRef:
    return SocialPressureEvidenceRef(source=source, field=field, value=value)


def _runtime_policy_social_pressure(module_runtime_policy: dict[str, Any] | None) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    policy = governance.get("social_pressure")
    if not isinstance(policy, dict):
        policy = raw.get("social_pressure_policy") if isinstance(raw.get("social_pressure_policy"), dict) else {}
    return normalize_social_pressure_policy(policy)


def _source_score_maps(policy: dict[str, Any]) -> dict[str, dict[str, float]]:
    configured = policy.get("source_scores") if isinstance(policy.get("source_scores"), dict) else {}
    out: dict[str, dict[str, float]] = {}
    for source, defaults in _DEFAULT_SOURCE_SCORES.items():
        values = dict(defaults)
        override = configured.get(source) if isinstance(configured.get(source), dict) else {}
        for key, score in override.items():
            try:
                values[str(key)] = _clamp_score(float(score))
            except (TypeError, ValueError):
                continue
        out[source] = values
    return out


def _band_for_score(score: float, policy: dict[str, Any]) -> str:
    thresholds = policy.get("band_thresholds") if isinstance(policy.get("band_thresholds"), dict) else {}
    low_max = float(thresholds.get("low_max") or 0.33)
    high_min = float(thresholds.get("high_min") or 0.67)
    if score <= low_max:
        return "low"
    if score >= high_min:
        return "high"
    return "moderate"


def _prior_state(
    prior_social_pressure_state: dict[str, Any] | None,
    prior_planner_truth: dict[str, Any] | None,
) -> dict[str, Any]:
    state = prior_social_pressure_state if isinstance(prior_social_pressure_state, dict) else {}
    if state:
        return state
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    for key in ("social_pressure_state", "social_pressure"):
        value = prior.get(key)
        if isinstance(value, dict) and value:
            return value
    target = prior.get("social_pressure_target")
    if isinstance(target, dict) and target:
        return {
            "current_score": target.get("target_score"),
            "current_band": target.get("target_band"),
        }
    return {}


def _prior_score_and_band(state: dict[str, Any], policy: dict[str, Any]) -> tuple[float | None, str | None]:
    try:
        score = float(state.get("current_score"))
    except (TypeError, ValueError):
        score = None
    band = _clean_key(state.get("current_band"))
    if band not in SOCIAL_PRESSURE_BANDS and score is not None:
        band = _band_for_score(score, policy)
    return (_clamp_score(score), band) if score is not None else (None, band or None)


def _candidate(
    *,
    scores: dict[str, dict[str, float]],
    source: str,
    field: str,
    value: Any,
    evidence: list[SocialPressureEvidenceRef],
    rationale: list[str],
) -> float | None:
    key = _clean_key(value)
    if not key:
        return None
    source_scores = scores.get(source) or {}
    if key not in source_scores:
        return None
    evidence.append(_evidence(source, field, key))
    rationale.append(f"social_pressure_{source}")
    return source_scores[key]


def _pressure_shift(prior_planner_truth: dict[str, Any] | None) -> str:
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    return _clean_key(prior.get("social_pressure_shift") or prior.get("pressure_shift"))


def derive_social_pressure(
    *,
    scene_assessment: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    scene_energy_target: dict[str, Any] | None = None,
    pacing_rhythm_target: dict[str, Any] | None = None,
    prior_social_pressure_state: dict[str, Any] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    prior_narrative_thread_state: dict[str, Any] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive a continuous, bounded social-pressure metric from structured state."""

    policy = _runtime_policy_social_pressure(module_runtime_policy)
    scores = _source_score_maps(policy)
    scene = scene_assessment if isinstance(scene_assessment, dict) else {}
    social = social_state_record if isinstance(social_state_record, dict) else {}
    energy = scene_energy_target if isinstance(scene_energy_target, dict) else {}
    rhythm = pacing_rhythm_target if isinstance(pacing_rhythm_target, dict) else {}
    prior_state = _prior_state(prior_social_pressure_state, prior_planner_truth)
    prior_score, prior_band = _prior_score_and_band(prior_state, policy)

    evidence: list[SocialPressureEvidenceRef] = []
    rationale: list[str] = []
    candidates: list[float] = []
    for source, field, value in (
        ("social_risk_band", "social_risk_band", social.get("social_risk_band")),
        ("scene_pressure_state", "pressure_state", scene.get("pressure_state")),
        ("scene_pressure_state", "scene_pressure_state", social.get("scene_pressure_state")),
        ("thread_pressure_state", "thread_pressure_state", scene.get("thread_pressure_state")),
        ("scene_energy_transition", "target_transition", energy.get("target_transition")),
        ("scene_energy_pressure_vector", "pressure_vector", energy.get("pressure_vector")),
        ("pacing_cadence", "cadence", rhythm.get("cadence")),
        ("pressure_shift", "social_pressure_shift", _pressure_shift(prior_planner_truth)),
    ):
        score = _candidate(
            scores=scores,
            source=source,
            field=field,
            value=value,
            evidence=evidence,
            rationale=rationale,
        )
        if score is not None:
            candidates.append(score)

    base_score = max(candidates) if candidates else float(policy.get("default_score") or 0.4)
    increments = policy.get("increments") if isinstance(policy.get("increments"), dict) else {}
    active_threads = 0
    try:
        active_threads = int(social.get("active_thread_count") or scene.get("active_thread_count") or 0)
    except (TypeError, ValueError):
        active_threads = 0
    if active_threads > 0:
        base_score += min(active_threads, 4) * float(increments.get("per_active_thread") or 0.0)
        evidence.append(_evidence("social_state_record", "active_thread_count", active_threads))
        rationale.append("social_pressure_active_threads")

    thread_state = prior_narrative_thread_state if isinstance(prior_narrative_thread_state, dict) else {}
    try:
        thread_pressure_level = int(thread_state.get("thread_pressure_level") or 0)
    except (TypeError, ValueError):
        thread_pressure_level = 0
    if thread_pressure_level > 0:
        base_score += min(thread_pressure_level, 4) * float(increments.get("thread_pressure_level") or 0.0)
        evidence.append(_evidence("prior_narrative_thread_state", "thread_pressure_level", thread_pressure_level))
        rationale.append("social_pressure_thread_pressure_level")

    if prior_band == "high":
        base_score += float(increments.get("prior_high_band") or 0.0)
        evidence.append(_evidence("prior_social_pressure_state", "current_band", prior_band))
        rationale.append("social_pressure_prior_high_band")

    raw_score = _clamp_score(base_score)
    alpha = float(policy.get("smoothing_alpha") or 0.7)
    current_score = (
        _clamp_score((alpha * raw_score) + ((1.0 - alpha) * prior_score))
        if prior_score is not None
        else raw_score
    )
    high_floor = float((policy.get("band_thresholds") or {}).get("high_min") or 0.67)
    if social.get("social_risk_band") == "high" or scene.get("thread_pressure_state") == "high_unresolved_thread_pressure":
        current_score = max(current_score, high_floor)
    current_score = _clamp_score(current_score)
    current_band = _band_for_score(current_score, policy)
    velocity = _clamp_score(current_score - prior_score) if prior_score is not None else 0.0
    deadband = float(policy.get("trend_deadband") or 0.05)
    trend = "stable"
    if prior_score is not None and current_score - prior_score > deadband:
        trend = "rising"
    elif prior_score is not None and prior_score - current_score > deadband:
        trend = "falling"

    max_refs = int(policy.get("max_evidence_refs") or 8)
    compact_evidence = evidence[:max_refs]
    rationale_codes = list(dict.fromkeys(rationale))
    state = SocialPressureState(
        current_score=current_score,
        current_band=current_band,  # type: ignore[arg-type]
        prior_score=prior_score,
        prior_band=prior_band if prior_band in SOCIAL_PRESSURE_BANDS else None,  # type: ignore[arg-type]
        trend=trend,  # type: ignore[arg-type]
        velocity=round(current_score - prior_score, 3) if prior_score is not None else 0.0,
        active_source_count=len(compact_evidence),
        source_evidence=compact_evidence,
        rationale_codes=rationale_codes,
    )
    target = SocialPressureTarget(
        target_score=current_score,
        target_band=current_band,  # type: ignore[arg-type]
        trend=trend,  # type: ignore[arg-type]
        pressure_floor=high_floor if current_band == "high" else 0.0,
        requires_visible_pressure=current_band == "high" or trend == "rising",
        release_allowed=current_band != "high" and trend != "rising",
        source_evidence=compact_evidence,
        rationale_codes=rationale_codes,
    )
    return {
        "schema_version": SOCIAL_PRESSURE_SCHEMA_VERSION,
        "policy": policy,
        "state": state.to_runtime_dict(),
        "target": target.to_runtime_dict(),
        "source_evidence": [row.to_runtime_dict() for row in compact_evidence],
        "rationale_codes": rationale_codes,
    }


def validate_social_pressure_metric(
    *,
    social_pressure_target: dict[str, Any] | None,
    social_pressure_state: dict[str, Any] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate metric consistency using schema and policy thresholds only."""

    if not isinstance(social_pressure_target, dict):
        return SocialPressureValidation(
            status="not_applicable",
            contract_pass=True,
            failure_codes=[],
            actual={"reason": "social_pressure_target_missing"},
        ).to_runtime_dict()
    policy = _runtime_policy_social_pressure(module_runtime_policy)
    try:
        target = SocialPressureTarget.model_validate(social_pressure_target)
    except Exception:
        return SocialPressureValidation(
            status="rejected",
            contract_pass=False,
            failure_codes=["social_pressure_target_mismatch"],
            feedback_code="social_pressure_target_mismatch",
            target=social_pressure_target,
            actual={"reason": "invalid_social_pressure_target"},
        ).to_runtime_dict()
    expected_band = _band_for_score(target.target_score, policy)
    failure_codes: list[str] = []
    if target.target_score < 0.0 or target.target_score > 1.0:
        failure_codes.append("social_pressure_score_out_of_bounds")
    if target.target_band != expected_band:
        failure_codes.append("social_pressure_band_mismatch")
    failure_codes = [code for code in dict.fromkeys(failure_codes) if code in SOCIAL_PRESSURE_FAILURE_CODES]
    state = social_pressure_state if isinstance(social_pressure_state, dict) else {}
    return SocialPressureValidation(
        status="approved" if not failure_codes else "rejected",
        contract_pass=not failure_codes,
        failure_codes=failure_codes,
        feedback_code=failure_codes[0] if failure_codes else None,
        target=target.to_runtime_dict(),
        actual={
            "current_score": state.get("current_score", target.target_score),
            "current_band": state.get("current_band", target.target_band),
            "trend": state.get("trend", target.trend),
            "expected_band": expected_band,
            "validated_from_policy_thresholds": True,
        },
    ).to_runtime_dict()
