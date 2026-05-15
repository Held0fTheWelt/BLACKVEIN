"""Policy-driven narrative-momentum derivation and validation."""

from __future__ import annotations

from typing import Any

from ai_stack.narrative_momentum_contracts import (
    NARRATIVE_MOMENTUM_BUILDING,
    NARRATIVE_MOMENTUM_CRESTING,
    NARRATIVE_MOMENTUM_DRIVING,
    NARRATIVE_MOMENTUM_FAILURE_CODES,
    NARRATIVE_MOMENTUM_FAILURE_EVENT_MISSING,
    NARRATIVE_MOMENTUM_FAILURE_SOURCE_REF_INVALID,
    NARRATIVE_MOMENTUM_FAILURE_STALL_BUDGET_EXCEEDED,
    NARRATIVE_MOMENTUM_FAILURE_TARGET_MISSING,
    NARRATIVE_MOMENTUM_FAILURE_TRANSITION_FORBIDDEN,
    NARRATIVE_MOMENTUM_FAILURE_VELOCITY_EXCEEDED,
    NARRATIVE_MOMENTUM_POLICY_VERSION,
    NARRATIVE_MOMENTUM_RELEASING,
    NARRATIVE_MOMENTUM_RESTING,
    NARRATIVE_MOMENTUM_SCHEMA_VERSION,
    NARRATIVE_MOMENTUM_STALLED,
    NARRATIVE_MOMENTUM_STATES,
    NARRATIVE_MOMENTUM_TRENDS,
    NARRATIVE_MOMENTUM_ALLOWED_SOURCE_REFS,
    NarrativeMomentumState,
    NarrativeMomentumTarget,
    NarrativeMomentumValidation,
    normalize_narrative_momentum_policy,
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _key(value: Any) -> str:
    return _text(value).lower()


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None:
        return []
    return [value]


def _clean_str_list(value: Any) -> list[str]:
    out: list[str] = []
    for item in _as_list(value):
        text = _text(item)
        if text and text not in out:
            out.append(text)
    return out


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, round(value, 3)))


def _runtime_policy_narrative_momentum(
    module_runtime_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    direct = raw.get("narrative_momentum_policy")
    if isinstance(direct, dict):
        return normalize_narrative_momentum_policy(direct)
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    nested = governance.get("narrative_momentum")
    return normalize_narrative_momentum_policy(nested if isinstance(nested, dict) else {})


def _prior_state(
    prior_narrative_momentum_state: dict[str, Any] | None,
    prior_planner_truth: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(prior_narrative_momentum_state, dict) and prior_narrative_momentum_state:
        return prior_narrative_momentum_state
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    for key in ("narrative_momentum_state", "narrative_momentum"):
        value = prior.get(key)
        if isinstance(value, dict) and value:
            return value
    target = prior.get("narrative_momentum_target")
    if isinstance(target, dict) and target:
        return {
            "current_state": target.get("target_state"),
            "current_score": target.get("target_score"),
        }
    return {}


def _prior_score_and_state(state: dict[str, Any]) -> tuple[float | None, str | None, int]:
    try:
        score = _clamp_score(float(state.get("current_score")))
    except (TypeError, ValueError):
        score = None
    prior_state = _key(state.get("current_state"))
    if prior_state not in NARRATIVE_MOMENTUM_STATES:
        prior_state = ""
    try:
        stall_count = int(state.get("stall_turn_count") or 0)
    except (TypeError, ValueError):
        stall_count = 0
    return score, prior_state or None, max(0, stall_count)


def _score_maps(policy: dict[str, Any]) -> dict[str, dict[str, float]]:
    maps = policy.get("source_weights") if isinstance(policy.get("source_weights"), dict) else {}
    out: dict[str, dict[str, float]] = {}
    for source, values in maps.items():
        if not isinstance(values, dict):
            continue
        out[str(source)] = {}
        for raw_key, raw_value in values.items():
            try:
                out[str(source)][_key(raw_key)] = _clamp_score(float(raw_value))
            except (TypeError, ValueError):
                continue
    return out


def _source_ref(source: str, field: str, value: Any) -> dict[str, Any]:
    return {
        "source": source,
        "field": field,
        "value": value,
    }


def _candidate_score(
    *,
    scores: dict[str, dict[str, float]],
    source: str,
    field: str,
    value: Any,
    evidence: list[dict[str, Any]],
    rationale: list[str],
) -> float | None:
    key = _key(value)
    if not key:
        return None
    source_scores = scores.get(source) or {}
    if key not in source_scores:
        return None
    evidence.append(_source_ref(source, field, key))
    rationale.append(f"narrative_momentum_{source}")
    return source_scores[key]


def _state_for_score(
    score: float,
    policy: dict[str, Any],
    *,
    prior_score: float | None = None,
    prior_state: str | None = None,
) -> str:
    thresholds = (
        policy.get("state_thresholds")
        if isinstance(policy.get("state_thresholds"), dict)
        else {}
    )
    resting_max = float(thresholds.get("resting_max") or 0.25)
    driving_min = float(thresholds.get("driving_min") or 0.55)
    cresting_min = float(thresholds.get("cresting_min") or 0.82)
    release_drop_min = float(thresholds.get("release_drop_min") or 0.12)
    if (
        prior_score is not None
        and prior_state in {NARRATIVE_MOMENTUM_DRIVING, NARRATIVE_MOMENTUM_CRESTING}
        and prior_score - score >= release_drop_min
    ):
        return NARRATIVE_MOMENTUM_RELEASING
    if score <= resting_max:
        return NARRATIVE_MOMENTUM_RESTING
    if score >= cresting_min:
        return NARRATIVE_MOMENTUM_CRESTING
    if score >= driving_min:
        return NARRATIVE_MOMENTUM_DRIVING
    return NARRATIVE_MOMENTUM_BUILDING


def _allowed_next_states(policy: dict[str, Any], state_name: str) -> list[str]:
    transitions = (
        policy.get("allowed_transitions")
        if isinstance(policy.get("allowed_transitions"), dict)
        else {}
    )
    allowed = _clean_str_list(transitions.get(state_name))
    allowed = [item for item in allowed if item in NARRATIVE_MOMENTUM_STATES]
    return allowed or [state_name]


def _is_transition_allowed(policy: dict[str, Any], prior_state: str | None, current_state: str) -> bool:
    if not prior_state or prior_state not in NARRATIVE_MOMENTUM_STATES:
        return True
    return current_state in _allowed_next_states(policy, prior_state)


def _clamp_transition_target(
    policy: dict[str, Any],
    *,
    prior_state: str | None,
    desired_state: str,
    trend: str,
    score: float,
) -> str:
    if _is_transition_allowed(policy, prior_state, desired_state):
        return desired_state
    allowed = _allowed_next_states(policy, prior_state or desired_state)
    if trend == "falling" and NARRATIVE_MOMENTUM_RELEASING in allowed:
        return NARRATIVE_MOMENTUM_RELEASING
    thresholds = (
        policy.get("state_thresholds")
        if isinstance(policy.get("state_thresholds"), dict)
        else {}
    )
    driving_min = float(thresholds.get("driving_min") or 0.55)
    if score >= driving_min and NARRATIVE_MOMENTUM_DRIVING in allowed:
        return NARRATIVE_MOMENTUM_DRIVING
    if NARRATIVE_MOMENTUM_BUILDING in allowed:
        return NARRATIVE_MOMENTUM_BUILDING
    return allowed[0] if allowed else desired_state


def _semantic_move_signal(scene_plan_record: dict[str, Any] | None) -> str:
    plan = scene_plan_record if isinstance(scene_plan_record, dict) else {}
    for key in ("semantic_move_kind", "move_type", "selected_scene_function"):
        text = _key(plan.get(key))
        if text:
            if "escalat" in text or "press" in text:
                return "escalate"
            if "challeng" in text or "confront" in text or "blame" in text:
                return "challenge"
            if "deescalat" in text or "repair" in text:
                return "deescalate"
            if "question" in text:
                return "question"
            if "wait" in text or "observe" in text:
                return "observe"
    return ""


def _variation_signal(expectation_variation_target: dict[str, Any] | None) -> str:
    target = expectation_variation_target if isinstance(expectation_variation_target, dict) else {}
    if target.get("selected_variation_ids"):
        return "selected"
    if target.get("withheld_variation_ids"):
        return "withheld"
    return "absent"


def derive_narrative_momentum(
    *,
    scene_plan_record: dict[str, Any] | None = None,
    scene_energy_target: dict[str, Any] | None = None,
    pacing_rhythm_target: dict[str, Any] | None = None,
    social_pressure_target: dict[str, Any] | None = None,
    expectation_variation_target: dict[str, Any] | None = None,
    prior_narrative_momentum_state: dict[str, Any] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive bounded momentum state and selected target from structured state."""

    policy = _runtime_policy_narrative_momentum(module_runtime_policy)
    scores = _score_maps(policy)
    energy = scene_energy_target if isinstance(scene_energy_target, dict) else {}
    rhythm = pacing_rhythm_target if isinstance(pacing_rhythm_target, dict) else {}
    pressure = social_pressure_target if isinstance(social_pressure_target, dict) else {}
    prior = _prior_state(prior_narrative_momentum_state, prior_planner_truth)
    prior_score, prior_state, prior_stall_count = _prior_score_and_state(prior)

    evidence: list[dict[str, Any]] = []
    rationale: list[str] = []
    candidates: list[float] = []
    for source, field, value in (
        ("scene_energy_transition", "target_transition", energy.get("target_transition")),
        ("pacing_cadence", "cadence", rhythm.get("cadence")),
        ("social_pressure_band", "target_band", pressure.get("target_band")),
        ("expectation_variation_signal", "selected_variation_ids", _variation_signal(expectation_variation_target)),
        ("semantic_move", "semantic_move_kind", _semantic_move_signal(scene_plan_record)),
    ):
        score = _candidate_score(
            scores=scores,
            source=source,
            field=field,
            value=value,
            evidence=evidence,
            rationale=rationale,
        )
        if score is not None:
            candidates.append(score)

    if candidates:
        candidate_score = _clamp_score((max(candidates) * 0.65) + ((sum(candidates) / len(candidates)) * 0.35))
    else:
        candidate_score = _clamp_score(float(policy.get("default_score") or 0.35))
        rationale.append("narrative_momentum_default_score")

    max_delta = float(policy.get("max_velocity_delta") or 0.4)
    decay = float(policy.get("decay_per_turn") or 0.05)
    if prior_score is not None:
        if candidate_score < prior_score:
            candidate_score = max(candidate_score, _clamp_score(prior_score - decay))
        delta = max(-max_delta, min(max_delta, candidate_score - prior_score))
        current_score = _clamp_score(prior_score + delta)
    else:
        current_score = candidate_score

    thresholds = (
        policy.get("state_thresholds")
        if isinstance(policy.get("state_thresholds"), dict)
        else {}
    )
    deadband = float(thresholds.get("trend_deadband") or 0.05)
    trend = "stable"
    velocity = 0.0
    if prior_score is not None:
        velocity = round(current_score - prior_score, 3)
        if velocity > deadband:
            trend = "rising"
        elif velocity < -deadband:
            trend = "falling"

    current_state = _state_for_score(
        current_score,
        policy,
        prior_score=prior_score,
        prior_state=prior_state,
    )
    forward_signal = any(
        ref.get("source") in {
            "scene_energy_transition",
            "pacing_cadence",
            "expectation_variation_signal",
            "semantic_move",
        }
        and str(ref.get("value") or "") not in {"release", "deescalate", "breathe", "absent", "observe", "wait"}
        for ref in evidence
    )
    clamped_state = _clamp_transition_target(
        policy,
        prior_state=prior_state,
        desired_state=current_state,
        trend=trend,
        score=current_score,
    )
    if clamped_state != current_state:
        current_state = clamped_state
        rationale.append("narrative_momentum_transition_clamped")
    if (
        prior_state in {NARRATIVE_MOMENTUM_BUILDING, NARRATIVE_MOMENTUM_DRIVING, NARRATIVE_MOMENTUM_STALLED}
        and not forward_signal
        and trend != "rising"
    ):
        stall_turn_count = prior_stall_count + 1
    elif current_state == NARRATIVE_MOMENTUM_STALLED:
        stall_turn_count = prior_stall_count
    else:
        stall_turn_count = 0
    if stall_turn_count > int(policy.get("stall_budget_turns") or 0):
        current_state = NARRATIVE_MOMENTUM_STALLED

    allowed_next = _allowed_next_states(policy, current_state)
    min_events = int(policy.get("min_progress_event_count") or 0)
    requires_forward_motion = bool(
        policy.get("enabled")
        and (
            current_state in {NARRATIVE_MOMENTUM_BUILDING, NARRATIVE_MOMENTUM_DRIVING, NARRATIVE_MOMENTUM_STALLED}
            or trend == "rising"
        )
    )
    if bool(policy.get("require_structured_events")) and requires_forward_motion:
        min_events = max(1, min_events)
    release_allowed = current_state in {"cresting", NARRATIVE_MOMENTUM_DRIVING, NARRATIVE_MOMENTUM_RELEASING}

    state = NarrativeMomentumState(
        current_state=current_state,
        current_score=current_score,
        prior_state=prior_state,
        prior_score=prior_score,
        trend=trend,
        velocity=velocity,
        stall_turn_count=stall_turn_count,
        active_source_count=len(evidence),
        source_evidence=evidence[:8],
        rationale_codes=list(dict.fromkeys(rationale)),
    ).to_dict()
    target = NarrativeMomentumTarget(
        policy_enabled=bool(policy.get("enabled")),
        commit_impact=str(policy.get("default_commit_impact") or "recover"),
        target_state=current_state,
        target_score=current_score,
        allowed_next_states=allowed_next,
        requires_forward_motion=requires_forward_motion,
        release_allowed=release_allowed,
        min_progress_event_count=min_events,
        selected_driver_refs=evidence[:8],
        rationale_codes=list(dict.fromkeys(rationale)),
        source_evidence=evidence[:8],
    ).to_dict()
    return {
        "schema_version": NARRATIVE_MOMENTUM_SCHEMA_VERSION,
        "policy": policy,
        "state": state,
        "target": target,
        "source_evidence": evidence[:8],
        "rationale_codes": list(dict.fromkeys(rationale)),
    }


def compact_narrative_momentum_context(
    target: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return model-visible momentum context without raw prose or hidden state."""

    src = target if isinstance(target, dict) else {}
    if not src or not src.get("policy_enabled"):
        return {}
    return {
        "schema_version": src.get("schema_version"),
        "target_state": src.get("target_state"),
        "target_score": src.get("target_score"),
        "allowed_next_states": src.get("allowed_next_states") or [],
        "requires_forward_motion": bool(src.get("requires_forward_motion")),
        "release_allowed": bool(src.get("release_allowed")),
        "min_progress_event_count": int(src.get("min_progress_event_count") or 0),
        "selected_driver_refs": src.get("selected_driver_refs") or [],
    }


def _event_rows(structured_output: dict[str, Any] | None) -> list[dict[str, Any]]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    events = structured.get("narrative_momentum_events")
    return [row for row in events if isinstance(row, dict)] if isinstance(events, list) else []


def _event_state(event: dict[str, Any]) -> str:
    return _key(
        event.get("momentum_state")
        or event.get("target_state")
        or event.get("state")
    )


def _source_refs_valid(events: list[dict[str, Any]], target: dict[str, Any]) -> bool:
    if not events:
        return True
    selected_refs = target.get("selected_driver_refs")
    requires_refs = isinstance(selected_refs, list) and bool(selected_refs)
    for event in events:
        refs = event.get("source_refs") or event.get("driver_refs")
        if not isinstance(refs, list) or not refs:
            if requires_refs:
                return False
            continue
        for ref in refs:
            if not isinstance(ref, dict):
                return False
            source = _text(ref.get("source"))
            field = _text(ref.get("field"))
            if source not in NARRATIVE_MOMENTUM_ALLOWED_SOURCE_REFS or not field:
                return False
    return True


def validate_narrative_momentum_realization(
    *,
    narrative_momentum_target: dict[str, Any] | None,
    narrative_momentum_state: dict[str, Any] | None = None,
    structured_output: dict[str, Any] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate structured momentum events against policy and state machine."""

    target = narrative_momentum_target if isinstance(narrative_momentum_target, dict) else {}
    state = narrative_momentum_state if isinstance(narrative_momentum_state, dict) else {}
    if not target or not bool(target.get("policy_enabled")):
        return NarrativeMomentumValidation(
            schema_version=NARRATIVE_MOMENTUM_SCHEMA_VERSION,
            status="not_applicable",
            contract_pass=True,
            failure_codes=[] if not target else [],
            target=target,
            actual={"reason": NARRATIVE_MOMENTUM_FAILURE_TARGET_MISSING} if not target else {},
        ).to_dict()

    policy = _runtime_policy_narrative_momentum(module_runtime_policy)
    events = _event_rows(structured_output)
    target_state = _key(target.get("target_state"))
    current_state = _key(state.get("current_state") or target_state)
    prior_state = _key(state.get("prior_state"))
    if prior_state not in NARRATIVE_MOMENTUM_STATES:
        prior_state = ""
    allowed_next = [
        item
        for item in _clean_str_list(target.get("allowed_next_states"))
        if item in NARRATIVE_MOMENTUM_STATES
    ] or _allowed_next_states(policy, current_state)
    realized_states = [row for row in (_event_state(event) for event in events) if row]
    progress_event_count = len(
        [
            event
            for event in events
            if _event_state(event) in set(allowed_next)
            or _key(event.get("event_type")) in {"advance", "turning_point", "stall_recovery"}
        ]
    )

    failure_codes: list[str] = []
    if target_state not in NARRATIVE_MOMENTUM_STATES:
        failure_codes.append(NARRATIVE_MOMENTUM_FAILURE_TARGET_MISSING)
    transition_allowed = _is_transition_allowed(policy, prior_state or None, current_state)
    if not transition_allowed:
        failure_codes.append(NARRATIVE_MOMENTUM_FAILURE_TRANSITION_FORBIDDEN)
    if realized_states and not any(state_name in set(allowed_next) for state_name in realized_states):
        failure_codes.append(NARRATIVE_MOMENTUM_FAILURE_TRANSITION_FORBIDDEN)

    min_events = int(target.get("min_progress_event_count") or 0)
    if bool(target.get("requires_forward_motion")) and min_events <= 0:
        min_events = 1 if bool(policy.get("require_structured_events")) else 0
    if min_events > 0 and progress_event_count < min_events:
        failure_codes.append(NARRATIVE_MOMENTUM_FAILURE_EVENT_MISSING)

    try:
        velocity = float(state.get("velocity") or 0.0)
    except (TypeError, ValueError):
        velocity = 0.0
    max_delta = float(policy.get("max_velocity_delta") or 0.4)
    if abs(velocity) > max_delta:
        failure_codes.append(NARRATIVE_MOMENTUM_FAILURE_VELOCITY_EXCEEDED)

    try:
        stall_turn_count = int(state.get("stall_turn_count") or 0)
    except (TypeError, ValueError):
        stall_turn_count = 0
    stall_budget = int(policy.get("stall_budget_turns") or 0)
    stall_budget_respected = stall_turn_count <= stall_budget
    if not stall_budget_respected:
        failure_codes.append(NARRATIVE_MOMENTUM_FAILURE_STALL_BUDGET_EXCEEDED)

    source_refs_valid = _source_refs_valid(events, target)
    if not source_refs_valid:
        failure_codes.append(NARRATIVE_MOMENTUM_FAILURE_SOURCE_REF_INVALID)

    deduped = [
        code
        for code in dict.fromkeys(failure_codes)
        if code in NARRATIVE_MOMENTUM_FAILURE_CODES
    ]
    actual = {
        "current_state": current_state or None,
        "current_score": state.get("current_score", target.get("target_score")),
        "target_state": target_state or None,
        "target_score": target.get("target_score"),
        "trend": state.get("trend"),
        "velocity": velocity,
        "transition_allowed": transition_allowed,
        "allowed_next_states": allowed_next,
        "structured_events_present": bool(events),
        "event_count": len(events),
        "progress_event_count": progress_event_count,
        "realized_states": list(dict.fromkeys(realized_states)),
        "stall_turn_count": stall_turn_count,
        "stall_budget_respected": stall_budget_respected,
        "source_refs_valid": source_refs_valid,
        "contract_pass": not deduped,
        "failure_codes": deduped,
    }
    return NarrativeMomentumValidation(
        schema_version=NARRATIVE_MOMENTUM_SCHEMA_VERSION,
        status="rejected" if deduped else "approved",
        contract_pass=not deduped,
        failure_codes=deduped,
        feedback_code=deduped[0] if deduped else None,
        target=target,
        actual=actual,
        source_evidence=[
            {
                "source": "structured_output",
                "field": "narrative_momentum_events",
                "present": bool(events),
            }
        ],
    ).to_dict()


def build_narrative_momentum_aspect_record(
    *,
    target: dict[str, Any] | None,
    state: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    source: str = "runtime",
) -> dict[str, Any]:
    """Build a RuntimeAspectLedger-compatible narrative-momentum record."""

    target_dict = target if isinstance(target, dict) else {}
    state_dict = state if isinstance(state, dict) else {}
    validation_dict = validation if isinstance(validation, dict) else {}
    policy_dict = (
        policy if isinstance(policy, dict) else normalize_narrative_momentum_policy(None)
    )
    failure_codes = [
        code for code in _clean_str_list(validation_dict.get("failure_codes")) if code
    ]
    validation_status = _key(validation_dict.get("status"))
    applicable = bool(target_dict.get("policy_enabled"))
    if not validation_dict:
        aspect_status = "partial" if applicable else "not_applicable"
    elif validation_status == "approved":
        aspect_status = "passed"
    elif validation_status == "not_applicable":
        aspect_status = "not_applicable"
        applicable = False
    elif validation_status == "degraded":
        aspect_status = "partial"
    else:
        aspect_status = "failed"

    actual = (
        dict(validation_dict.get("actual"))
        if isinstance(validation_dict.get("actual"), dict)
        else {}
    )
    actual.update(
        {
            "current_state": state_dict.get("current_state")
            or actual.get("current_state")
            or target_dict.get("target_state"),
            "current_score": state_dict.get("current_score")
            if "current_score" in state_dict
            else actual.get("current_score")
            if "current_score" in actual
            else target_dict.get("target_score"),
            "target_state": target_dict.get("target_state"),
            "target_score": target_dict.get("target_score"),
            "trend": state_dict.get("trend") or actual.get("trend"),
            "velocity": state_dict.get("velocity")
            if "velocity" in state_dict
            else actual.get("velocity"),
            "stall_turn_count": state_dict.get("stall_turn_count")
            if "stall_turn_count" in state_dict
            else actual.get("stall_turn_count"),
            "validation_status": validation_status or None,
            "contract_pass": validation_dict.get("contract_pass"),
            "failure_codes": failure_codes,
        }
    )
    return {
        "applicable": applicable,
        "status": aspect_status,
        "expected": {
            "schema_version": target_dict.get("schema_version")
            or NARRATIVE_MOMENTUM_SCHEMA_VERSION,
            "policy_version": target_dict.get("policy_version")
            or NARRATIVE_MOMENTUM_POLICY_VERSION,
            "policy_present": bool(policy_dict),
            "policy_enabled": bool(
                target_dict.get("policy_enabled") or policy_dict.get("enabled")
            ),
            "commit_impact": target_dict.get("commit_impact")
            or policy_dict.get("default_commit_impact"),
            "require_structured_events": bool(
                policy_dict.get("require_structured_events")
            ),
            "max_velocity_delta": policy_dict.get("max_velocity_delta"),
            "stall_budget_turns": policy_dict.get("stall_budget_turns"),
        },
        "selected": {
            "state": state_dict,
            "target": target_dict,
            "target_state": target_dict.get("target_state"),
            "target_score": target_dict.get("target_score"),
            "allowed_next_states": target_dict.get("allowed_next_states") or [],
            "requires_forward_motion": bool(target_dict.get("requires_forward_motion")),
            "release_allowed": bool(target_dict.get("release_allowed")),
            "min_progress_event_count": int(
                target_dict.get("min_progress_event_count") or 0
            ),
            "selected_driver_refs": target_dict.get("selected_driver_refs") or [],
        },
        "actual": actual,
        "reasons": failure_codes
        or (
            ["narrative_momentum_target_selected"]
            if applicable and target_dict and not validation_dict
            else []
        ),
        "source": source,
        "failure_class": "recoverable_dramatic_failure" if failure_codes else None,
        "failure_reason": failure_codes[0] if failure_codes else None,
    }
