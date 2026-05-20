"""Policy-driven expectation-variation derivation and validation."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from ai_stack.contracts.expectation_variation_contracts import (
    EXPECTATION_VARIATION_BOUNDED_REVEAL,
    EXPECTATION_VARIATION_CONSEQUENCE_RETURN,
    EXPECTATION_VARIATION_FAILURE_COOLDOWN_VIOLATION,
    EXPECTATION_VARIATION_FAILURE_MISSING_REQUIRED_EVENT,
    EXPECTATION_VARIATION_FAILURE_OVER_BUDGET,
    EXPECTATION_VARIATION_FAILURE_TARGET_MISMATCH,
    EXPECTATION_VARIATION_FAILURE_UNEARNED_EVENT,
    EXPECTATION_VARIATION_FAILURE_UNSELECTED_EVENT,
    EXPECTATION_VARIATION_IRONIC_MISREAD,
    EXPECTATION_VARIATION_POLICY_VERSION,
    EXPECTATION_VARIATION_PRESSURE_REVERSAL,
    EXPECTATION_VARIATION_RESPONDER_HANDOFF,
    EXPECTATION_VARIATION_SCHEMA_VERSION,
    EXPECTATION_VARIATION_SENSORY_REFRAME,
    EXPECTATION_VARIATION_SILENCE_PIVOT,
    EXPECTATION_VARIATION_SOCIAL_ALIGNMENT_SHIFT,
    EXPECTATION_VARIATION_TYPES,
    ExpectationVariationState,
    ExpectationVariationTarget,
    ExpectationVariationValidation,
    normalize_expectation_variation_policy,
)


_TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)


def _text(value: Any) -> str:
    return str(value or "").strip()


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


def _stable_id(*parts: Any) -> str:
    material = "|".join(
        " ".join(_TOKEN_RE.findall(str(part or "").casefold())) for part in parts
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"expectation_variation:{digest}"


def _runtime_policy_expectation_variation(
    module_runtime_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    direct = raw.get("expectation_variation_policy")
    if isinstance(direct, dict):
        return normalize_expectation_variation_policy(direct)
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    nested = governance.get("expectation_variation")
    return normalize_expectation_variation_policy(nested if isinstance(nested, dict) else {})


def _prior_state(
    prior_expectation_variation_state: dict[str, Any] | None,
    prior_planner_truth: dict[str, Any] | None,
) -> dict[str, Any]:
    if isinstance(prior_expectation_variation_state, dict) and prior_expectation_variation_state:
        return prior_expectation_variation_state
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    for key in ("expectation_variation_state", "expectation_variation"):
        value = prior.get(key)
        if isinstance(value, dict) and value:
            return value
    return {}


def _prior_recent_ids(state: dict[str, Any]) -> list[str]:
    return _clean_str_list(
        state.get("recent_variation_ids")
        or state.get("selected_variation_ids")
        or state.get("last_selected_variation_ids")
    )


def _source_ref(source: str, field: str, value: Any) -> dict[str, Any] | None:
    text = _text(value)
    if not text:
        return None
    return {"source": source, "field": field, "value": text}


def _candidate(
    *,
    variation_type: str,
    source: str,
    field: str,
    value: Any,
    priority: int,
    extra_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    if variation_type not in EXPECTATION_VARIATION_TYPES:
        return None
    ref = _source_ref(source, field, value)
    refs = [ref] if ref else []
    for row in extra_refs or []:
        if isinstance(row, dict):
            refs.append(row)
    if not refs:
        return None
    return {
        "variation_id": _stable_id(variation_type, source, field, value),
        "variation_type": variation_type,
        "source": source,
        "source_field": field,
        "source_value": _text(value),
        "priority": int(priority),
        "required_setup_refs": refs,
    }


def _selected_ids_from(value: Any) -> list[str]:
    return _clean_str_list(value)


def _candidate_rows(
    *,
    scene_plan_record: dict[str, Any] | None,
    scene_energy_target: dict[str, Any] | None,
    pacing_rhythm_target: dict[str, Any] | None,
    social_pressure_target: dict[str, Any] | None,
    sensory_context_target: dict[str, Any] | None,
    improvisational_coherence_target: dict[str, Any] | None,
    information_disclosure_target: dict[str, Any] | None,
    dramatic_irony_record: dict[str, Any] | None,
    prior_consequence_cascade_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    plan = scene_plan_record if isinstance(scene_plan_record, dict) else {}
    energy = scene_energy_target if isinstance(scene_energy_target, dict) else {}
    rhythm = pacing_rhythm_target if isinstance(pacing_rhythm_target, dict) else {}
    pressure = social_pressure_target if isinstance(social_pressure_target, dict) else {}
    sensory = sensory_context_target if isinstance(sensory_context_target, dict) else {}
    improv = (
        improvisational_coherence_target
        if isinstance(improvisational_coherence_target, dict)
        else {}
    )
    disclosure = (
        information_disclosure_target
        if isinstance(information_disclosure_target, dict)
        else {}
    )
    irony = dramatic_irony_record if isinstance(dramatic_irony_record, dict) else {}
    cascade = (
        prior_consequence_cascade_state
        if isinstance(prior_consequence_cascade_state, dict)
        else {}
    )

    candidates: list[dict[str, Any]] = []

    for unit_id in _selected_ids_from(disclosure.get("selected_unit_ids"))[:3]:
        row = _candidate(
            variation_type=EXPECTATION_VARIATION_BOUNDED_REVEAL,
            source="information_disclosure_target",
            field="selected_unit_ids",
            value=unit_id,
            priority=90,
        )
        if row:
            candidates.append(row)

    for opportunity_id in _selected_ids_from(irony.get("selected_opportunity_ids"))[:3]:
        row = _candidate(
            variation_type=EXPECTATION_VARIATION_IRONIC_MISREAD,
            source="dramatic_irony_record",
            field="selected_opportunity_ids",
            value=opportunity_id,
            priority=85,
        )
        if row:
            candidates.append(row)

    selected_consequence_ids = _selected_ids_from(cascade.get("selected_consequence_ids"))
    if not selected_consequence_ids:
        items = cascade.get("items") if isinstance(cascade.get("items"), list) else []
        selected_consequence_ids = [
            _text(item.get("consequence_id"))
            for item in items
            if isinstance(item, dict) and _text(item.get("consequence_id"))
        ]
    for consequence_id in selected_consequence_ids[:3]:
        row = _candidate(
            variation_type=EXPECTATION_VARIATION_CONSEQUENCE_RETURN,
            source="consequence_cascade_state",
            field="selected_consequence_ids",
            value=consequence_id,
            priority=75,
        )
        if row:
            candidates.append(row)

    transition = _text(energy.get("target_transition")).lower()
    cadence = _text(rhythm.get("cadence")).lower()
    scene_function = _text(
        plan.get("selected_scene_function") or plan.get("scene_function")
    )
    if transition in {"pivot", "interrupt"} or cadence in {"pivot", "interrupt"}:
        row = _candidate(
            variation_type=EXPECTATION_VARIATION_RESPONDER_HANDOFF
            if cadence == "interrupt"
            else EXPECTATION_VARIATION_PRESSURE_REVERSAL,
            source="pacing_rhythm_target" if cadence else "scene_energy_target",
            field="cadence" if cadence else "target_transition",
            value=cadence or transition,
            priority=70,
            extra_refs=[
                ref
                for ref in (
                    _source_ref("scene_plan_record", "selected_scene_function", scene_function),
                )
                if ref
            ],
        )
        if row:
            candidates.append(row)

    pressure_band = _text(pressure.get("target_band") or pressure.get("current_band")).lower()
    pressure_trend = _text(pressure.get("trend")).lower()
    if pressure_band == "high" and pressure_trend in {"rising", "held", "escalating"}:
        row = _candidate(
            variation_type=EXPECTATION_VARIATION_SOCIAL_ALIGNMENT_SHIFT,
            source="social_pressure_target",
            field="target_band",
            value=f"{pressure_band}:{pressure_trend or 'steady'}",
            priority=65,
        )
        if row:
            candidates.append(row)

    sensory_intensity = _text(sensory.get("intensity")).lower()
    layer_ids = _selected_ids_from(
        sensory.get("selected_layer_ids")
        or sensory.get("required_layer_ids")
        or [
            item.get("layer_id")
            for item in sensory.get("selected_layers", [])
            if isinstance(item, dict)
        ]
    )
    if sensory_intensity == "high" and layer_ids:
        row = _candidate(
            variation_type=EXPECTATION_VARIATION_SENSORY_REFRAME,
            source="sensory_context_target",
            field="selected_layer_ids",
            value=layer_ids[0],
            priority=55,
        )
        if row:
            candidates.append(row)

    acceptance_mode = _text(improv.get("acceptance_mode"))
    visible_actor_ids = _selected_ids_from(improv.get("visible_actor_ids"))
    if acceptance_mode and acceptance_mode != "accept":
        row = _candidate(
            variation_type=EXPECTATION_VARIATION_SILENCE_PIVOT,
            source="improvisational_coherence_target",
            field="acceptance_mode",
            value=acceptance_mode,
            priority=50,
        )
        if row:
            candidates.append(row)
    elif len(visible_actor_ids) > 1:
        row = _candidate(
            variation_type=EXPECTATION_VARIATION_RESPONDER_HANDOFF,
            source="improvisational_coherence_target",
            field="visible_actor_ids",
            value=visible_actor_ids[1],
            priority=45,
        )
        if row:
            candidates.append(row)

    deduped: dict[str, dict[str, Any]] = {}
    for row in candidates:
        deduped.setdefault(row["variation_id"], row)
    return sorted(
        deduped.values(),
        key=lambda row: (-int(row.get("priority") or 0), str(row.get("variation_id") or "")),
    )


def derive_expectation_variation(
    *,
    scene_plan_record: dict[str, Any] | None = None,
    scene_energy_target: dict[str, Any] | None = None,
    pacing_rhythm_target: dict[str, Any] | None = None,
    social_pressure_target: dict[str, Any] | None = None,
    sensory_context_target: dict[str, Any] | None = None,
    improvisational_coherence_target: dict[str, Any] | None = None,
    information_disclosure_target: dict[str, Any] | None = None,
    dramatic_irony_record: dict[str, Any] | None = None,
    prior_consequence_cascade_state: dict[str, Any] | None = None,
    prior_expectation_variation_state: dict[str, Any] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select bounded expectation-variation targets from structured state."""
    policy = _runtime_policy_expectation_variation(module_runtime_policy)
    allowed_types = [
        item
        for item in _clean_str_list(policy.get("allowed_variation_types"))
        if item in EXPECTATION_VARIATION_TYPES
    ]
    if not allowed_types:
        allowed_types = list(EXPECTATION_VARIATION_TYPES)
    max_units = int(policy.get("max_variation_units_per_turn") or 0)
    cooldown_turns = int(policy.get("cooldown_turns") or 0)
    if not policy.get("enabled") or max_units <= 0:
        target = ExpectationVariationTarget(
            policy_enabled=bool(policy.get("enabled")),
            commit_impact=str(policy.get("default_commit_impact") or "diagnostic"),
            require_structured_events=bool(policy.get("require_structured_events")),
            max_variation_units_per_turn=max_units,
            cooldown_turns=cooldown_turns,
            allowed_variation_types=allowed_types,
            rationale_codes=["expectation_variation_not_applicable"],
        ).to_dict()
        state = ExpectationVariationState(
            budget_remaining=max(0, max_units),
        ).to_dict()
        return {"policy": policy, "target": target, "state": state}

    candidates = [
        row
        for row in _candidate_rows(
            scene_plan_record=scene_plan_record,
            scene_energy_target=scene_energy_target,
            pacing_rhythm_target=pacing_rhythm_target,
            social_pressure_target=social_pressure_target,
            sensory_context_target=sensory_context_target,
            improvisational_coherence_target=improvisational_coherence_target,
            information_disclosure_target=information_disclosure_target,
            dramatic_irony_record=dramatic_irony_record,
            prior_consequence_cascade_state=prior_consequence_cascade_state,
        )
        if row.get("variation_type") in allowed_types
    ]
    prior_state = _prior_state(prior_expectation_variation_state, prior_planner_truth)
    recent_ids = _prior_recent_ids(prior_state)
    cooldown_blocked: list[str] = []
    selected: list[dict[str, Any]] = []
    withheld: list[str] = []
    for row in candidates:
        variation_id = _text(row.get("variation_id"))
        if not variation_id:
            continue
        if cooldown_turns > 0 and variation_id in recent_ids:
            cooldown_blocked.append(variation_id)
            withheld.append(variation_id)
            continue
        if len(selected) < max_units:
            selected.append(row)
        else:
            withheld.append(variation_id)

    selected_ids = [str(row.get("variation_id")) for row in selected]
    selected_types = [str(row.get("variation_type")) for row in selected]
    setup_refs: list[dict[str, Any]] = []
    max_setup_refs = int(policy.get("max_setup_refs") or 6)
    for row in selected:
        for ref in row.get("required_setup_refs") or []:
            if isinstance(ref, dict) and ref not in setup_refs:
                setup_refs.append(ref)
            if len(setup_refs) >= max_setup_refs:
                break
        if len(setup_refs) >= max_setup_refs:
            break

    rationale = (
        ["expectation_variation_selected"]
        if selected_ids
        else ["expectation_variation_no_candidate"]
    )
    if cooldown_blocked:
        rationale.append("expectation_variation_cooldown_applied")
    target = ExpectationVariationTarget(
        policy_enabled=True,
        commit_impact=str(policy.get("default_commit_impact") or "recover"),
        require_structured_events=bool(policy.get("require_structured_events")),
        max_variation_units_per_turn=max_units,
        cooldown_turns=cooldown_turns,
        allowed_variation_types=allowed_types,
        selected_variation_ids=selected_ids,
        selected_variation_types=selected_types,
        withheld_variation_ids=list(dict.fromkeys(withheld)),
        required_setup_refs=setup_refs,
        rationale_codes=rationale,
        source_evidence=setup_refs,
    ).to_dict()
    state = ExpectationVariationState(
        recent_variation_ids=list(dict.fromkeys(selected_ids + recent_ids))[:8],
        cooldown_blocked_ids=list(dict.fromkeys(cooldown_blocked)),
        selected_variation_ids=selected_ids,
        budget_remaining=max(0, max_units - len(selected_ids)),
        source_evidence=setup_refs,
    ).to_dict()
    return {"policy": policy, "target": target, "state": state}


def compact_expectation_variation_context(
    target: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return model-visible context without raw prose or hidden planning blobs."""
    src = target if isinstance(target, dict) else {}
    if not src or not src.get("policy_enabled"):
        return {}
    return {
        "schema_version": src.get("schema_version"),
        "selected_variation_ids": src.get("selected_variation_ids") or [],
        "selected_variation_types": src.get("selected_variation_types") or [],
        "allowed_variation_types": src.get("allowed_variation_types") or [],
        "max_variation_units_per_turn": int(src.get("max_variation_units_per_turn") or 0),
        "require_structured_events": bool(src.get("require_structured_events")),
        "required_setup_refs": src.get("required_setup_refs") or [],
        "withheld_variation_ids": src.get("withheld_variation_ids") or [],
    }


def _event_rows(structured_output: dict[str, Any] | None) -> list[dict[str, Any]]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    events = structured.get("expectation_variation_events")
    return [row for row in events if isinstance(row, dict)] if isinstance(events, list) else []


def _ref_tokens(refs: Any) -> set[str]:
    out: set[str] = set()
    for ref in _as_list(refs):
        if isinstance(ref, dict):
            for key in ("source", "field", "value", "source_ref", "id"):
                text = _text(ref.get(key))
                if text:
                    out.add(text)
        else:
            text = _text(ref)
            if text:
                out.add(text)
    return out


def validate_expectation_variation_realization(
    *,
    expectation_variation_target: dict[str, Any] | None,
    expectation_variation_state: dict[str, Any] | None = None,
    structured_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate structured variation events against the selected target."""
    target = (
        expectation_variation_target
        if isinstance(expectation_variation_target, dict)
        else {}
    )
    if not target or not bool(target.get("policy_enabled")):
        return ExpectationVariationValidation(
            schema_version=EXPECTATION_VARIATION_SCHEMA_VERSION,
            status="not_applicable",
            contract_pass=True,
            target=target,
        ).to_dict()

    events = _event_rows(structured_output)
    selected_ids = set(_clean_str_list(target.get("selected_variation_ids")))
    selected_types = set(_clean_str_list(target.get("selected_variation_types")))
    allowed_types = set(_clean_str_list(target.get("allowed_variation_types")))
    cooldown_blocked = set(
        _clean_str_list(
            (expectation_variation_state or {}).get("cooldown_blocked_ids")
            if isinstance(expectation_variation_state, dict)
            else []
        )
    )
    max_units = int(target.get("max_variation_units_per_turn") or 0)
    required_tokens = _ref_tokens(target.get("required_setup_refs"))
    failure_codes: list[str] = []
    realized_ids: list[str] = []
    realized_types: list[str] = []

    if len(events) > max_units:
        failure_codes.append(EXPECTATION_VARIATION_FAILURE_OVER_BUDGET)
    if bool(target.get("require_structured_events")) and selected_ids and not events:
        failure_codes.append(EXPECTATION_VARIATION_FAILURE_MISSING_REQUIRED_EVENT)

    for event in events:
        variation_id = _text(
            event.get("variation_id")
            or event.get("expectation_variation_id")
            or event.get("id")
        )
        variation_type = _text(event.get("variation_type") or event.get("type"))
        if variation_id:
            realized_ids.append(variation_id)
        if variation_type:
            realized_types.append(variation_type)
        if variation_id not in selected_ids:
            failure_codes.append(EXPECTATION_VARIATION_FAILURE_UNSELECTED_EVENT)
        if variation_id in cooldown_blocked:
            failure_codes.append(EXPECTATION_VARIATION_FAILURE_COOLDOWN_VIOLATION)
        if variation_type and variation_type not in allowed_types:
            failure_codes.append(EXPECTATION_VARIATION_FAILURE_UNEARNED_EVENT)
        if selected_types and variation_type and variation_type not in selected_types:
            failure_codes.append(EXPECTATION_VARIATION_FAILURE_TARGET_MISMATCH)
        event_tokens = _ref_tokens(
            event.get("source_refs")
            or event.get("setup_refs")
            or event.get("required_setup_refs")
        )
        if required_tokens and event_tokens.isdisjoint(required_tokens):
            failure_codes.append(EXPECTATION_VARIATION_FAILURE_UNEARNED_EVENT)

    if bool(target.get("require_structured_events")):
        missing_selected = selected_ids.difference(realized_ids)
        if missing_selected:
            failure_codes.append(EXPECTATION_VARIATION_FAILURE_MISSING_REQUIRED_EVENT)

    deduped_failures = list(dict.fromkeys(failure_codes))
    actual = {
        "structured_events_present": bool(events),
        "event_count": len(events),
        "budget_used": len(events),
        "budget_remaining": max(0, max_units - len(events)),
        "realized_variation_ids": list(dict.fromkeys(realized_ids)),
        "realized_variation_types": list(dict.fromkeys(realized_types)),
        "failure_codes": deduped_failures,
        "contract_pass": not deduped_failures,
    }
    return ExpectationVariationValidation(
        schema_version=EXPECTATION_VARIATION_SCHEMA_VERSION,
        status="rejected" if deduped_failures else "approved",
        contract_pass=not deduped_failures,
        failure_codes=deduped_failures,
        feedback_code=deduped_failures[0] if deduped_failures else None,
        target=target,
        actual=actual,
        source_evidence=[
            {
                "source": "structured_output",
                "field": "expectation_variation_events",
                "present": bool(events),
            }
        ],
    ).to_dict()


def build_expectation_variation_aspect_record(
    *,
    target: dict[str, Any] | None,
    state: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    source: str = "runtime",
) -> dict[str, Any]:
    """Build a RuntimeAspectLedger-compatible expectation-variation record."""
    target_dict = target if isinstance(target, dict) else {}
    state_dict = state if isinstance(state, dict) else {}
    validation_dict = validation if isinstance(validation, dict) else {}
    policy_dict = (
        policy if isinstance(policy, dict) else normalize_expectation_variation_policy(None)
    )
    failure_codes = [
        code for code in _clean_str_list(validation_dict.get("failure_codes")) if code
    ]
    validation_status = _text(validation_dict.get("status")).lower()
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
            or EXPECTATION_VARIATION_SCHEMA_VERSION,
            "policy_version": target_dict.get("policy_version")
            or EXPECTATION_VARIATION_POLICY_VERSION,
            "policy_present": bool(policy_dict.get("enabled") or target_dict),
            "policy_enabled": bool(target_dict.get("policy_enabled")),
            "commit_impact": target_dict.get("commit_impact")
            or policy_dict.get("default_commit_impact"),
            "require_structured_events": bool(target_dict.get("require_structured_events")),
            "max_variation_units_per_turn": int(
                target_dict.get("max_variation_units_per_turn")
                if target_dict.get("max_variation_units_per_turn") is not None
                else policy_dict.get("max_variation_units_per_turn") or 0
            ),
            "cooldown_turns": int(
                target_dict.get("cooldown_turns")
                if target_dict.get("cooldown_turns") is not None
                else policy_dict.get("cooldown_turns") or 0
            ),
            "allowed_variation_types": target_dict.get("allowed_variation_types")
            or policy_dict.get("allowed_variation_types")
            or [],
        },
        "selected": {
            "selected_variation_ids": target_dict.get("selected_variation_ids") or [],
            "selected_variation_types": target_dict.get("selected_variation_types") or [],
            "withheld_variation_ids": target_dict.get("withheld_variation_ids") or [],
            "required_setup_refs": target_dict.get("required_setup_refs") or [],
            "budget_remaining": int(state_dict.get("budget_remaining") or 0),
            "cooldown_blocked_ids": state_dict.get("cooldown_blocked_ids") or [],
        },
        "actual": actual,
        "reasons": failure_codes
        or (
            ["expectation_variation_target_selected"]
            if applicable and target_dict.get("selected_variation_ids") and not validation_dict
            else []
        ),
        "source": source,
        "failure_class": "recoverable_dramatic_failure" if failure_codes else None,
        "failure_reason": failure_codes[0] if failure_codes else None,
    }
