"""Policy-driven genre-awareness derivation and structured validation."""

from __future__ import annotations

from typing import Any

from ai_stack.contracts.genre_awareness_contracts import (
    GENRE_AWARENESS_FAILURE_EVENT_BUDGET_EXCEEDED,
    GENRE_AWARENESS_FAILURE_FORBIDDEN_MARKER,
    GENRE_AWARENESS_FAILURE_MISSING_REQUIRED_CONVENTION,
    GENRE_AWARENESS_FAILURE_MISSING_REQUIRED_EVENT,
    GENRE_AWARENESS_FAILURE_REGISTER_NOT_ALLOWED,
    GENRE_AWARENESS_FAILURE_TARGET_MISMATCH,
    GENRE_AWARENESS_FAILURE_UNSELECTED_PROFILE,
    GENRE_AWARENESS_POLICY_VERSION,
    GENRE_AWARENESS_SCHEMA_VERSION,
    GenreAwarenessState,
    GenreAwarenessTarget,
    GenreAwarenessValidation,
    normalize_genre_awareness_policy,
)


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


def _runtime_policy_genre_awareness(
    module_runtime_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    direct = raw.get("genre_awareness_policy")
    if isinstance(direct, dict):
        return normalize_genre_awareness_policy(direct)
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    nested = governance.get("genre_awareness")
    return normalize_genre_awareness_policy(nested if isinstance(nested, dict) else {})


def _prior_profile_id(
    prior_genre_awareness_state: dict[str, Any] | None,
    prior_planner_truth: dict[str, Any] | None,
) -> str | None:
    if isinstance(prior_genre_awareness_state, dict):
        value = _text(
            prior_genre_awareness_state.get("current_genre_profile_id")
            or prior_genre_awareness_state.get("genre_profile_id")
        )
        if value:
            return value
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    state = prior.get("genre_awareness_state")
    if isinstance(state, dict):
        value = _text(
            state.get("current_genre_profile_id") or state.get("genre_profile_id")
        )
        if value:
            return value
    return None


def _source_ref(source: str, field: str, value: Any) -> dict[str, Any]:
    return {"source": source, "field": field, "value": value}


def derive_genre_awareness(
    *,
    module_runtime_policy: dict[str, Any] | None = None,
    scene_plan_record: dict[str, Any] | None = None,
    selected_scene_function: str | None = None,
    current_scene_id: str | None = None,
    scene_energy_target: dict[str, Any] | None = None,
    social_pressure_target: dict[str, Any] | None = None,
    prior_genre_awareness_state: dict[str, Any] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive a bounded genre target from normalized module policy."""
    policy = _runtime_policy_genre_awareness(module_runtime_policy)
    profile_id = _text(policy.get("genre_profile_id"))
    selected_registers = _clean_str_list(policy.get("allowed_registers"))
    required_conventions = _clean_str_list(policy.get("required_conventions"))
    forbidden_marker_ids = _clean_str_list(policy.get("forbidden_marker_ids"))
    max_signals = int(policy.get("max_genre_signals_per_turn") or 0)
    prior_profile_id = _prior_profile_id(prior_genre_awareness_state, prior_planner_truth)

    if not policy.get("enabled") or not profile_id or max_signals <= 0:
        target = GenreAwarenessTarget(
            policy_enabled=bool(policy.get("enabled")),
            commit_impact=str(policy.get("default_commit_impact") or "diagnostic"),
            genre_profile_id=profile_id or None,
            selected_registers=selected_registers,
            required_conventions=required_conventions,
            forbidden_marker_ids=forbidden_marker_ids,
            require_structured_events=bool(policy.get("require_structured_events")),
            max_genre_signals_per_turn=max_signals,
            rationale_codes=["genre_awareness_not_applicable"],
        ).to_dict()
        state = GenreAwarenessState(
            current_genre_profile_id=profile_id or None,
            prior_genre_profile_id=prior_profile_id,
            selected_registers=selected_registers,
        ).to_dict()
        return {"policy": policy, "target": target, "state": state}

    plan = scene_plan_record if isinstance(scene_plan_record, dict) else {}
    energy = scene_energy_target if isinstance(scene_energy_target, dict) else {}
    pressure = social_pressure_target if isinstance(social_pressure_target, dict) else {}
    scene_function = _text(
        selected_scene_function
        or plan.get("selected_scene_function")
        or plan.get("scene_function")
    )
    evidence = [
        _source_ref("module_runtime_policy", "genre_profile_id", profile_id),
        _source_ref("scene_plan_record", "selected_scene_function", scene_function),
    ]
    if current_scene_id:
        evidence.append(_source_ref("runtime_state", "current_scene_id", current_scene_id))
    if energy:
        evidence.append(
            _source_ref("scene_energy_target", "energy_level", energy.get("energy_level"))
        )
    if pressure:
        evidence.append(
            _source_ref("social_pressure_target", "target_band", pressure.get("target_band"))
        )
    evidence = [row for row in evidence if _text(row.get("value"))]
    rationale = ["genre_awareness_policy_selected"]
    if prior_profile_id and prior_profile_id != profile_id:
        rationale.append("genre_awareness_profile_changed_from_prior_state")

    target = GenreAwarenessTarget(
        policy_enabled=True,
        commit_impact=str(policy.get("default_commit_impact") or "diagnostic"),
        genre_profile_id=profile_id,
        selected_registers=selected_registers,
        required_conventions=required_conventions,
        forbidden_marker_ids=forbidden_marker_ids,
        require_structured_events=bool(policy.get("require_structured_events")),
        max_genre_signals_per_turn=max_signals,
        source_evidence=evidence,
        rationale_codes=rationale,
    ).to_dict()
    state = GenreAwarenessState(
        current_genre_profile_id=profile_id,
        prior_genre_profile_id=prior_profile_id,
        selected_registers=selected_registers,
        source_evidence=evidence,
    ).to_dict()
    return {"policy": policy, "target": target, "state": state}


def compact_genre_awareness_context(target: dict[str, Any] | None) -> dict[str, Any]:
    """Return model-visible genre context without raw prompt or example prose."""
    src = target if isinstance(target, dict) else {}
    if not src or not src.get("policy_enabled"):
        return {}
    return {
        "schema_version": src.get("schema_version"),
        "genre_profile_id": src.get("genre_profile_id"),
        "selected_registers": src.get("selected_registers") or [],
        "required_conventions": src.get("required_conventions") or [],
        "forbidden_marker_ids": src.get("forbidden_marker_ids") or [],
        "max_genre_signals_per_turn": int(src.get("max_genre_signals_per_turn") or 0),
        "require_structured_events": bool(src.get("require_structured_events")),
        "structured_event_field": "genre_awareness_events",
    }


def _event_rows(structured_output: dict[str, Any] | None) -> list[dict[str, Any]]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    events = structured.get("genre_awareness_events")
    return [row for row in events if isinstance(row, dict)] if isinstance(events, list) else []


def validate_genre_awareness_realization(
    *,
    genre_awareness_target: dict[str, Any] | None,
    genre_awareness_state: dict[str, Any] | None = None,
    structured_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate genre realization through structured events only."""
    target = genre_awareness_target if isinstance(genre_awareness_target, dict) else {}
    if not target or not bool(target.get("policy_enabled")):
        return GenreAwarenessValidation(
            schema_version=GENRE_AWARENESS_SCHEMA_VERSION,
            status="not_applicable",
            contract_pass=True,
            target=target,
        ).to_dict()

    profile_id = _text(target.get("genre_profile_id"))
    allowed_registers = set(_clean_str_list(target.get("selected_registers")))
    required_conventions = set(_clean_str_list(target.get("required_conventions")))
    forbidden_marker_ids = set(_clean_str_list(target.get("forbidden_marker_ids")))
    max_signals = int(target.get("max_genre_signals_per_turn") or 0)
    events = _event_rows(structured_output)
    failure_codes: list[str] = []
    realized_profile_ids: list[str] = []
    realized_registers: list[str] = []
    realized_conventions: list[str] = []
    realized_forbidden_markers: list[str] = []

    if len(events) > max_signals:
        failure_codes.append(GENRE_AWARENESS_FAILURE_EVENT_BUDGET_EXCEEDED)
    if bool(target.get("require_structured_events")) and required_conventions and not events:
        failure_codes.append(GENRE_AWARENESS_FAILURE_MISSING_REQUIRED_EVENT)

    for event in events:
        event_profile = _text(
            event.get("genre_profile_id")
            or event.get("profile_id")
            or event.get("genre_id")
        )
        event_register = _text(event.get("register") or event.get("genre_register"))
        event_conventions = _clean_str_list(
            event.get("convention_ids")
            or event.get("realized_conventions")
            or event.get("required_conventions")
        )
        event_forbidden = _clean_str_list(
            event.get("forbidden_marker_ids")
            or event.get("forbidden_genre_markers")
            or event.get("forbidden_markers")
        )
        if event.get("forbidden_marker_present") is True:
            event_forbidden.append("forbidden_marker_present")
        if event_profile:
            realized_profile_ids.append(event_profile)
        else:
            failure_codes.append(GENRE_AWARENESS_FAILURE_TARGET_MISMATCH)
        if event_profile and event_profile != profile_id:
            failure_codes.append(GENRE_AWARENESS_FAILURE_UNSELECTED_PROFILE)
        if event_register:
            realized_registers.append(event_register)
            if allowed_registers and event_register not in allowed_registers:
                failure_codes.append(GENRE_AWARENESS_FAILURE_REGISTER_NOT_ALLOWED)
        elif allowed_registers:
            failure_codes.append(GENRE_AWARENESS_FAILURE_REGISTER_NOT_ALLOWED)
        realized_conventions.extend(event_conventions)
        intersecting_forbidden = [
            marker for marker in event_forbidden if marker in forbidden_marker_ids
        ]
        if "forbidden_marker_present" in event_forbidden or intersecting_forbidden:
            realized_forbidden_markers.extend(intersecting_forbidden or event_forbidden)
            failure_codes.append(GENRE_AWARENESS_FAILURE_FORBIDDEN_MARKER)

    missing_conventions = sorted(required_conventions.difference(realized_conventions))
    if bool(target.get("require_structured_events")) and missing_conventions:
        failure_codes.append(GENRE_AWARENESS_FAILURE_MISSING_REQUIRED_CONVENTION)

    deduped_failures = [
        code for code in dict.fromkeys(failure_codes) if _text(code)
    ]
    actual = {
        "structured_events_present": bool(events),
        "event_count": len(events),
        "realized_profile_ids": list(dict.fromkeys(realized_profile_ids)),
        "realized_registers": list(dict.fromkeys(realized_registers)),
        "realized_conventions": list(dict.fromkeys(realized_conventions)),
        "missing_required_conventions": missing_conventions,
        "forbidden_marker_ids": list(dict.fromkeys(realized_forbidden_markers)),
        "contract_pass": not deduped_failures,
        "failure_codes": deduped_failures,
    }
    return GenreAwarenessValidation(
        schema_version=GENRE_AWARENESS_SCHEMA_VERSION,
        status="rejected" if deduped_failures else "approved",
        contract_pass=not deduped_failures,
        failure_codes=deduped_failures,
        feedback_code=deduped_failures[0] if deduped_failures else None,
        target=target,
        actual=actual,
        source_evidence=[
            {
                "source": "structured_output",
                "field": "genre_awareness_events",
                "present": bool(events),
            }
        ],
    ).to_dict()


def build_genre_awareness_aspect_record(
    *,
    target: dict[str, Any] | None,
    state: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    source: str = "runtime",
) -> dict[str, Any]:
    """Build a RuntimeAspectLedger-compatible genre-awareness record."""
    target_dict = target if isinstance(target, dict) else {}
    state_dict = state if isinstance(state, dict) else {}
    validation_dict = validation if isinstance(validation, dict) else {}
    policy_dict = policy if isinstance(policy, dict) else normalize_genre_awareness_policy(None)
    failure_codes = _clean_str_list(validation_dict.get("failure_codes"))
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
            or GENRE_AWARENESS_SCHEMA_VERSION,
            "policy_version": target_dict.get("policy_version")
            or GENRE_AWARENESS_POLICY_VERSION,
            "policy_present": bool(policy_dict.get("enabled") or target_dict),
            "policy_enabled": bool(target_dict.get("policy_enabled")),
            "commit_impact": target_dict.get("commit_impact")
            or policy_dict.get("default_commit_impact"),
            "require_structured_events": bool(
                target_dict.get("require_structured_events")
            ),
            "max_genre_signals_per_turn": int(
                target_dict.get("max_genre_signals_per_turn")
                if target_dict.get("max_genre_signals_per_turn") is not None
                else policy_dict.get("max_genre_signals_per_turn") or 0
            ),
        },
        "selected": {
            "state": state_dict,
            "target": target_dict,
            "genre_profile_id": target_dict.get("genre_profile_id"),
            "selected_registers": target_dict.get("selected_registers") or [],
            "required_conventions": target_dict.get("required_conventions") or [],
            "forbidden_marker_ids": target_dict.get("forbidden_marker_ids") or [],
        },
        "actual": actual,
        "reasons": failure_codes
        or (
            ["genre_awareness_target_selected"]
            if applicable and target_dict and not validation_dict
            else []
        ),
        "source": source,
        "failure_class": "recoverable_dramatic_failure" if failure_codes else None,
        "failure_reason": failure_codes[0] if failure_codes else None,
    }
