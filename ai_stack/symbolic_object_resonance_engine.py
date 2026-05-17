"""Policy-driven symbolic-object-resonance derivation and validation."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from ai_stack.symbolic_object_resonance_contracts import (
    SYMBOLIC_OBJECT_RESONANCE_FAILURE_BUDGET_EXCEEDED,
    SYMBOLIC_OBJECT_RESONANCE_FAILURE_CODES,
    SYMBOLIC_OBJECT_RESONANCE_FAILURE_MISSING_REQUIRED_EVENT,
    SYMBOLIC_OBJECT_RESONANCE_FAILURE_ROLE_MISMATCH,
    SYMBOLIC_OBJECT_RESONANCE_FAILURE_SOURCE_REF_MISMATCH,
    SYMBOLIC_OBJECT_RESONANCE_FAILURE_TARGET_MISMATCH,
    SYMBOLIC_OBJECT_RESONANCE_FAILURE_UNSELECTED_OBJECT,
    SYMBOLIC_OBJECT_RESONANCE_POLICY_VERSION,
    SYMBOLIC_OBJECT_RESONANCE_ROLES,
    SYMBOLIC_OBJECT_RESONANCE_SCHEMA_VERSION,
    SymbolicObjectResonanceEvidenceRef,
    SymbolicObjectResonanceSignal,
    SymbolicObjectResonanceState,
    SymbolicObjectResonanceTarget,
    SymbolicObjectResonanceValidation,
    normalize_symbolic_object_resonance_policy,
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


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _stable_id(*parts: Any) -> str:
    material = "|".join(
        " ".join(_TOKEN_RE.findall(str(part or "").casefold())) for part in parts
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"symbolic_object_resonance:{digest}"


def _fingerprint(value: Any) -> str | None:
    if not value:
        return None
    try:
        material = json.dumps(value, sort_keys=True, ensure_ascii=True)
    except TypeError:
        material = str(value)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _evidence(source: str, field: str, value: Any) -> SymbolicObjectResonanceEvidenceRef:
    return SymbolicObjectResonanceEvidenceRef(source=source, field=field, value=value)


def _runtime_policy_symbolic_object_resonance(
    module_runtime_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    direct = raw.get("symbolic_object_resonance_policy")
    if isinstance(direct, dict):
        return normalize_symbolic_object_resonance_policy(direct)
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    nested = governance.get("symbolic_object_resonance")
    return normalize_symbolic_object_resonance_policy(nested if isinstance(nested, dict) else {})


def symbolic_object_resonance_policy_from_module_runtime(
    module_runtime_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    """Public helper for tests and adjacent runtime surfaces."""

    return _runtime_policy_symbolic_object_resonance(module_runtime_policy)


def _unwrap(payload: dict[str, Any] | None, key: str) -> dict[str, Any]:
    src = payload if isinstance(payload, dict) else {}
    nested = src.get(key)
    return nested if isinstance(nested, dict) else src


def _merge_object_row(rows: dict[str, dict[str, Any]], object_id: str, row: dict[str, Any]) -> None:
    oid = _text(object_id or row.get("id"))
    if not oid:
        return
    existing = rows.setdefault(oid, {"id": oid})
    existing.update({str(key): value for key, value in row.items()})
    existing["id"] = oid


def _object_rows(
    *,
    scene_affordances: dict[str, Any] | None,
    environment_model: dict[str, Any] | None,
    module_runtime_policy: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    model_objects = (
        environment_model.get("objects")
        if isinstance(environment_model, dict) and isinstance(environment_model.get("objects"), dict)
        else {}
    )
    for object_id, row in model_objects.items():
        if isinstance(row, dict):
            _merge_object_row(rows, str(object_id), row)

    policy = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    policy_object_model = (
        policy.get("object_model") if isinstance(policy.get("object_model"), dict) else {}
    )
    for object_id, row in (
        policy_object_model.get("objects")
        if isinstance(policy_object_model.get("objects"), dict)
        else {}
    ).items():
        if isinstance(row, dict):
            _merge_object_row(rows, str(object_id), row)

    affordances = _unwrap(scene_affordances, "scene_affordances")
    for row in affordances.get("objects") if isinstance(affordances.get("objects"), list) else []:
        if isinstance(row, dict):
            _merge_object_row(rows, _text(row.get("id")), row)
    return rows


def _roles_for_object(row: dict[str, Any], allowed_roles: set[str]) -> list[str]:
    roles = _clean_str_list(
        row.get("symbolic_roles")
        or row.get("resonance_roles")
        or row.get("symbolic_object_roles")
    )
    roles.extend(_clean_str_list(row.get("risk_tags")))
    out: list[str] = []
    for role in roles:
        if role in allowed_roles and role not in out:
            out.append(role)
    return out


def _target_object_id(player_action_frame: dict[str, Any] | None) -> str | None:
    frame = player_action_frame if isinstance(player_action_frame, dict) else {}
    target = frame.get("resolved_target") if isinstance(frame.get("resolved_target"), dict) else {}
    return (
        _text(target.get("target_id"))
        or _text(target.get("object_id"))
        or _text(frame.get("object_id"))
        or None
    )


def _source_ref(source: str, field: str, value: Any) -> SymbolicObjectResonanceEvidenceRef | None:
    text = _text(value)
    if not text:
        return None
    return _evidence(source, field, text)


def _append_candidate(
    candidates: list[dict[str, Any]],
    *,
    object_id: str,
    role: str,
    priority: int,
    source: str,
    field: str,
    value: Any,
    rationale_code: str,
) -> None:
    if not object_id or role not in SYMBOLIC_OBJECT_RESONANCE_ROLES:
        return
    ref = _source_ref(source, field, value)
    if not ref:
        return
    candidates.append(
        {
            "object_id": object_id,
            "resonance_role": role,
            "priority": max(0, min(100, int(priority))),
            "source_refs": [ref],
            "rationale_codes": [rationale_code],
        }
    )


def _prior_state(
    prior_symbolic_object_resonance_state: dict[str, Any] | None,
    prior_planner_truth: dict[str, Any] | None,
) -> dict[str, Any]:
    if (
        isinstance(prior_symbolic_object_resonance_state, dict)
        and prior_symbolic_object_resonance_state
    ):
        return prior_symbolic_object_resonance_state
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    for key in ("symbolic_object_resonance_state", "symbolic_object_resonance"):
        value = prior.get(key)
        if isinstance(value, dict) and value:
            return value
    return {}


def _ids_in_payload(payload: Any, object_ids: set[str]) -> list[str]:
    found: list[str] = []
    if not object_ids:
        return found
    if isinstance(payload, dict):
        for value in payload.values():
            for oid in _ids_in_payload(value, object_ids):
                if oid not in found:
                    found.append(oid)
    elif isinstance(payload, list):
        for value in payload:
            for oid in _ids_in_payload(value, object_ids):
                if oid not in found:
                    found.append(oid)
    else:
        text = _text(payload)
        if text in object_ids and text not in found:
            found.append(text)
    return found


def derive_symbolic_object_resonance(
    *,
    environment_state: dict[str, Any] | None = None,
    environment_model: dict[str, Any] | None = None,
    scene_affordances: dict[str, Any] | None = None,
    player_action_frame: dict[str, Any] | None = None,
    sensory_context_target: dict[str, Any] | None = None,
    social_pressure_target: dict[str, Any] | None = None,
    relationship_state_record: dict[str, Any] | None = None,
    expectation_variation_target: dict[str, Any] | None = None,
    prior_callback_web_state: dict[str, Any] | None = None,
    prior_consequence_cascade_state: dict[str, Any] | None = None,
    prior_symbolic_object_resonance_state: dict[str, Any] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select bounded symbolic object-role targets from structured state."""

    policy = _runtime_policy_symbolic_object_resonance(module_runtime_policy)
    allowed_roles = {
        role
        for role in _clean_str_list(policy.get("allowed_resonance_roles"))
        if role in SYMBOLIC_OBJECT_RESONANCE_ROLES
    } or set(SYMBOLIC_OBJECT_RESONANCE_ROLES)
    max_symbols = _bounded_int(policy.get("max_symbols_per_turn"), 2, minimum=0, maximum=8)
    max_refs = _bounded_int(policy.get("max_source_refs"), 6, minimum=0, maximum=16)
    rows = _object_rows(
        scene_affordances=scene_affordances,
        environment_model=environment_model,
        module_runtime_policy=module_runtime_policy,
    )
    prior = _prior_state(prior_symbolic_object_resonance_state, prior_planner_truth)
    prior_recent_ids = _clean_str_list(prior.get("recent_symbol_ids"))
    prior_counts = {
        str(key): int(value or 0)
        for key, value in (prior.get("resonance_counts") or {}).items()
        if str(key).strip()
    } if isinstance(prior.get("resonance_counts"), dict) else {}

    if not bool(policy.get("enabled")) or max_symbols <= 0:
        target = SymbolicObjectResonanceTarget(
            policy_enabled=bool(policy.get("enabled")),
            commit_impact=str(policy.get("default_commit_impact") or "diagnostic"),
            require_structured_events=bool(policy.get("require_structured_events")),
            max_symbols_per_turn=max_symbols,
            allowed_resonance_roles=sorted(allowed_roles),  # type: ignore[list-item]
            rationale_codes=["symbolic_object_resonance_not_applicable"],
        )
        state = SymbolicObjectResonanceState(
            recent_symbol_ids=prior_recent_ids[:12],
            resonance_counts=prior_counts,
            prior_state_fingerprint=_fingerprint(prior),
        )
        return {"policy": policy, "target": target.to_runtime_dict(), "state": state.to_runtime_dict()}

    candidates: list[dict[str, Any]] = []
    object_ids = set(rows)
    action_object_id = _target_object_id(player_action_frame)
    if action_object_id in rows:
        for role in _roles_for_object(rows[action_object_id], allowed_roles)[:2]:
            _append_candidate(
                candidates,
                object_id=action_object_id,
                role=role,
                priority=100,
                source="player_action_frame",
                field="resolved_target.target_id",
                value=action_object_id,
                rationale_code="symbolic_object_resonance_player_object_focus",
            )

    env = environment_state if isinstance(environment_state, dict) else {}
    for object_id in _clean_str_list(env.get("salient_object_ids"))[:6]:
        if object_id not in rows:
            continue
        for role in _roles_for_object(rows[object_id], allowed_roles)[:2]:
            _append_candidate(
                candidates,
                object_id=object_id,
                role=role,
                priority=78,
                source="environment_state",
                field="salient_object_ids",
                value=object_id,
                rationale_code="symbolic_object_resonance_salient_environment_object",
            )

    sensory = sensory_context_target if isinstance(sensory_context_target, dict) else {}
    sensory_object_id = _text(sensory.get("object_id"))
    if sensory_object_id in rows:
        for role in _roles_for_object(rows[sensory_object_id], allowed_roles)[:2]:
            _append_candidate(
                candidates,
                object_id=sensory_object_id,
                role=role,
                priority=88,
                source="sensory_context_target",
                field="object_id",
                value=sensory_object_id,
                rationale_code="symbolic_object_resonance_sensory_object_focus",
            )

    pressure = social_pressure_target if isinstance(social_pressure_target, dict) else {}
    pressure_band = _text(pressure.get("target_band") or pressure.get("current_band")).lower()
    if pressure_band in {"high", "moderate"}:
        for object_id, row in rows.items():
            roles = _roles_for_object(row, allowed_roles)
            weighted_roles = [
                role
                for role in roles
                if role in {"territorial_anchor", "exposure_surface", "status_surface"}
            ]
            for role in weighted_roles[:1]:
                _append_candidate(
                    candidates,
                    object_id=object_id,
                    role=role,
                    priority=66 if pressure_band == "high" else 54,
                    source="social_pressure_target",
                    field="target_band",
                    value=pressure_band,
                    rationale_code="symbolic_object_resonance_pressure_surface",
                )

    relationship = relationship_state_record if isinstance(relationship_state_record, dict) else {}
    active_axis_ids = _clean_str_list(
        relationship.get("active_relationship_axis_ids")
        or relationship.get("target_axis_ids")
    )
    if active_axis_ids:
        for object_id, row in rows.items():
            for role in [
                role
                for role in _roles_for_object(row, allowed_roles)
                if role in {"territorial_anchor", "hospitality_surface", "status_surface"}
            ][:1]:
                _append_candidate(
                    candidates,
                    object_id=object_id,
                    role=role,
                    priority=60,
                    source="relationship_state_record",
                    field="active_relationship_axis_ids",
                    value=active_axis_ids[0],
                    rationale_code="symbolic_object_resonance_relationship_axis_surface",
                )

    expectation = expectation_variation_target if isinstance(expectation_variation_target, dict) else {}
    if _clean_str_list(expectation.get("selected_variation_ids")) and sensory_object_id in rows:
        for role in _roles_for_object(rows[sensory_object_id], allowed_roles)[:1]:
            _append_candidate(
                candidates,
                object_id=sensory_object_id,
                role=role,
                priority=58,
                source="expectation_variation_target",
                field="selected_variation_ids",
                value=_clean_str_list(expectation.get("selected_variation_ids"))[0],
                rationale_code="symbolic_object_resonance_variation_reframe_surface",
            )

    for source, payload in (
        ("prior_callback_web_state", prior_callback_web_state),
        ("prior_consequence_cascade_state", prior_consequence_cascade_state),
    ):
        for object_id in _ids_in_payload(payload, object_ids)[:4]:
            for role in _roles_for_object(rows[object_id], allowed_roles)[:1]:
                _append_candidate(
                    candidates,
                    object_id=object_id,
                    role=role,
                    priority=48,
                    source=source,
                    field="structured_payload_object_id",
                    value=object_id,
                    rationale_code="symbolic_object_resonance_committed_continuity_object",
                )

    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for row in candidates:
        key = (_text(row.get("object_id")), _text(row.get("resonance_role")))
        if not key[0] or not key[1]:
            continue
        existing = merged.get(key)
        if not existing:
            merged[key] = row
            continue
        existing["priority"] = max(int(existing.get("priority") or 0), int(row.get("priority") or 0))
        refs = existing.setdefault("source_refs", [])
        for ref in row.get("source_refs") or []:
            if ref not in refs:
                refs.append(ref)
        rationale = existing.setdefault("rationale_codes", [])
        for code in row.get("rationale_codes") or []:
            if code not in rationale:
                rationale.append(code)

    sorted_candidates = sorted(
        merged.values(),
        key=lambda row: (
            -int(row.get("priority") or 0),
            int(prior_counts.get(str(row.get("symbol_id") or ""), 0)),
            str(row.get("object_id") or ""),
            str(row.get("resonance_role") or ""),
        ),
    )
    selected_rows = sorted_candidates[:max_symbols]
    signals: list[SymbolicObjectResonanceSignal] = []
    required_refs: list[SymbolicObjectResonanceEvidenceRef] = []
    for row in selected_rows:
        object_id = _text(row.get("object_id"))
        role = _text(row.get("resonance_role"))
        symbol_id = _stable_id(object_id, role)
        refs = [
            ref
            for ref in row.get("source_refs") or []
            if isinstance(ref, SymbolicObjectResonanceEvidenceRef)
        ][:max_refs]
        for ref in refs:
            if ref not in required_refs and len(required_refs) < max_refs:
                required_refs.append(ref)
        signals.append(
            SymbolicObjectResonanceSignal(
                symbol_id=symbol_id,
                object_id=object_id,
                resonance_role=role,  # type: ignore[arg-type]
                priority=int(row.get("priority") or 0),
                source_refs=refs,
                rationale_codes=_clean_str_list(row.get("rationale_codes")),
            )
        )

    selected_symbol_ids = [signal.symbol_id for signal in signals]
    selected_object_ids = list(dict.fromkeys(signal.object_id for signal in signals))
    selected_roles = list(dict.fromkeys(signal.resonance_role for signal in signals))
    rationale = (
        ["symbolic_object_resonance_selected"] if signals else ["symbolic_object_resonance_no_candidate"]
    )
    resonance_counts = dict(prior_counts)
    for symbol_id in selected_symbol_ids:
        resonance_counts[symbol_id] = int(resonance_counts.get(symbol_id, 0)) + 1
    target = SymbolicObjectResonanceTarget(
        policy_enabled=True,
        commit_impact=str(policy.get("default_commit_impact") or "diagnostic"),
        require_structured_events=bool(policy.get("require_structured_events")),
        max_symbols_per_turn=max_symbols,
        allowed_resonance_roles=sorted(allowed_roles),  # type: ignore[list-item]
        selected_symbol_ids=selected_symbol_ids,
        selected_object_ids=selected_object_ids,
        selected_resonance_roles=selected_roles,  # type: ignore[list-item]
        selected_signals=signals,
        required_source_refs=required_refs,
        rationale_codes=rationale,
        source_evidence=required_refs,
    )
    state = SymbolicObjectResonanceState(
        recent_symbol_ids=list(dict.fromkeys(selected_symbol_ids + prior_recent_ids))[:12],
        active_object_ids=selected_object_ids,
        resonance_counts=resonance_counts,
        prior_state_fingerprint=_fingerprint(prior),
        source_evidence=required_refs,
    )
    return {
        "schema_version": SYMBOLIC_OBJECT_RESONANCE_SCHEMA_VERSION,
        "policy": policy,
        "target": target.to_runtime_dict(),
        "state": state.to_runtime_dict(),
        "source_evidence": [ref.to_runtime_dict() for ref in required_refs],
        "rationale_codes": rationale,
    }


def compact_symbolic_object_resonance_context(target: dict[str, Any] | None) -> dict[str, Any]:
    """Return model-visible context without raw prose or unbounded content."""

    src = target if isinstance(target, dict) else {}
    if not src or not src.get("policy_enabled"):
        return {}
    return {
        "schema_version": src.get("schema_version"),
        "selected_symbol_ids": src.get("selected_symbol_ids") or [],
        "selected_object_ids": src.get("selected_object_ids") or [],
        "selected_resonance_roles": src.get("selected_resonance_roles") or [],
        "selected_signals": src.get("selected_signals") or [],
        "required_source_refs": src.get("required_source_refs") or [],
        "max_symbols_per_turn": int(src.get("max_symbols_per_turn") or 0),
        "require_structured_events": bool(src.get("require_structured_events")),
    }


def _event_rows(structured_output: dict[str, Any] | None) -> list[dict[str, Any]]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    events = structured.get("symbolic_object_resonance_events")
    return [row for row in events if isinstance(row, dict)] if isinstance(events, list) else []


def _ref_tokens(refs: Any) -> set[str]:
    out: set[str] = set()
    for ref in _as_list(refs):
        if isinstance(ref, dict):
            for key in ("source", "field", "value", "source_ref", "id", "object_id"):
                text = _text(ref.get(key))
                if text:
                    out.add(text)
        elif isinstance(ref, SymbolicObjectResonanceEvidenceRef):
            out.update({_text(ref.source), _text(ref.field), _text(ref.value)})
        else:
            text = _text(ref)
            if text:
                out.add(text)
    return {item for item in out if item}


def validate_symbolic_object_resonance_realization(
    *,
    symbolic_object_resonance_target: dict[str, Any] | None,
    symbolic_object_resonance_state: dict[str, Any] | None = None,
    structured_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate symbolic-object events using structured output only."""

    target_dict = (
        symbolic_object_resonance_target
        if isinstance(symbolic_object_resonance_target, dict)
        else {}
    )
    if not target_dict or not bool(target_dict.get("policy_enabled")):
        return SymbolicObjectResonanceValidation(
            status="not_applicable",
            contract_pass=True,
            target=target_dict,
        ).to_runtime_dict()
    try:
        target = SymbolicObjectResonanceTarget.model_validate(target_dict)
    except Exception:
        return SymbolicObjectResonanceValidation(
            status="rejected",
            contract_pass=False,
            failure_codes=[SYMBOLIC_OBJECT_RESONANCE_FAILURE_TARGET_MISMATCH],
            feedback_code=SYMBOLIC_OBJECT_RESONANCE_FAILURE_TARGET_MISMATCH,
            target=target_dict,
            actual={"reason": "invalid_symbolic_object_resonance_target"},
        ).to_runtime_dict()

    events = _event_rows(structured_output)
    selected_object_ids = set(target.selected_object_ids)
    selected_symbol_ids = set(target.selected_symbol_ids)
    selected_roles = set(target.selected_resonance_roles)
    allowed_roles = set(target.allowed_resonance_roles)
    required_tokens = _ref_tokens([ref.to_runtime_dict() for ref in target.required_source_refs])
    failure_codes: list[str] = []
    realized_object_ids: list[str] = []
    realized_symbol_ids: list[str] = []
    realized_roles: list[str] = []

    if len(events) > target.max_symbols_per_turn:
        failure_codes.append(SYMBOLIC_OBJECT_RESONANCE_FAILURE_BUDGET_EXCEEDED)
    if target.require_structured_events and target.selected_object_ids and not events:
        failure_codes.append(SYMBOLIC_OBJECT_RESONANCE_FAILURE_MISSING_REQUIRED_EVENT)

    for event in events:
        object_id = _text(event.get("object_id") or event.get("target_object_id"))
        symbol_id = _text(event.get("symbol_id") or event.get("resonance_id") or event.get("id"))
        role = _text(event.get("resonance_role") or event.get("role"))
        if object_id:
            realized_object_ids.append(object_id)
        if symbol_id:
            realized_symbol_ids.append(symbol_id)
        if role:
            realized_roles.append(role)
        if object_id and object_id not in selected_object_ids:
            failure_codes.append(SYMBOLIC_OBJECT_RESONANCE_FAILURE_UNSELECTED_OBJECT)
        if symbol_id and selected_symbol_ids and symbol_id not in selected_symbol_ids:
            failure_codes.append(SYMBOLIC_OBJECT_RESONANCE_FAILURE_TARGET_MISMATCH)
        if role and (role not in allowed_roles or (selected_roles and role not in selected_roles)):
            failure_codes.append(SYMBOLIC_OBJECT_RESONANCE_FAILURE_ROLE_MISMATCH)
        event_tokens = _ref_tokens(
            event.get("source_refs")
            or event.get("required_source_refs")
            or event.get("evidence_refs")
        )
        if required_tokens and event_tokens and event_tokens.isdisjoint(required_tokens):
            failure_codes.append(SYMBOLIC_OBJECT_RESONANCE_FAILURE_SOURCE_REF_MISMATCH)

    if target.require_structured_events:
        missing_objects = selected_object_ids.difference(realized_object_ids)
        if missing_objects:
            failure_codes.append(SYMBOLIC_OBJECT_RESONANCE_FAILURE_MISSING_REQUIRED_EVENT)

    deduped_failures = [
        code
        for code in dict.fromkeys(failure_codes)
        if code in SYMBOLIC_OBJECT_RESONANCE_FAILURE_CODES
    ]
    commit_impact = _text(target.commit_impact or "diagnostic")
    failed = bool(deduped_failures)
    status = "approved"
    if failed:
        status = "degraded" if commit_impact == "diagnostic" else "rejected"
    state = symbolic_object_resonance_state if isinstance(symbolic_object_resonance_state, dict) else {}
    actual = {
        "structured_events_present": bool(events),
        "event_count": len(events),
        "realized_object_ids": list(dict.fromkeys(realized_object_ids)),
        "realized_symbol_ids": list(dict.fromkeys(realized_symbol_ids)),
        "realized_resonance_roles": list(dict.fromkeys(realized_roles)),
        "active_object_ids": state.get("active_object_ids") or [],
        "contract_pass": not failed,
        "failure_codes": deduped_failures,
    }
    return SymbolicObjectResonanceValidation(
        status=status,  # type: ignore[arg-type]
        contract_pass=not failed,
        failure_codes=deduped_failures,
        feedback_code=deduped_failures[0] if deduped_failures else None,
        target=target.to_runtime_dict(),
        actual=actual,
        source_evidence=[
            _evidence(
                "structured_output",
                "symbolic_object_resonance_events",
                {"present": bool(events), "event_count": len(events)},
            )
        ],
    ).to_runtime_dict()


def build_symbolic_object_resonance_aspect_record(
    *,
    target: dict[str, Any] | None,
    state: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    source: str = "runtime",
) -> dict[str, Any]:
    """Build a RuntimeAspectLedger-compatible symbolic-object record."""

    target_dict = target if isinstance(target, dict) else {}
    state_dict = state if isinstance(state, dict) else {}
    validation_dict = validation if isinstance(validation, dict) else {}
    policy_dict = (
        policy if isinstance(policy, dict) else normalize_symbolic_object_resonance_policy(None)
    )
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
            or SYMBOLIC_OBJECT_RESONANCE_SCHEMA_VERSION,
            "policy_version": target_dict.get("policy_version")
            or SYMBOLIC_OBJECT_RESONANCE_POLICY_VERSION,
            "policy_present": bool(policy_dict.get("enabled") or target_dict),
            "policy_enabled": bool(target_dict.get("policy_enabled")),
            "commit_impact": target_dict.get("commit_impact")
            or policy_dict.get("default_commit_impact"),
            "require_structured_events": bool(target_dict.get("require_structured_events")),
            "max_symbols_per_turn": int(
                target_dict.get("max_symbols_per_turn")
                if target_dict.get("max_symbols_per_turn") is not None
                else policy_dict.get("max_symbols_per_turn") or 0
            ),
            "allowed_resonance_roles": target_dict.get("allowed_resonance_roles")
            or policy_dict.get("allowed_resonance_roles")
            or [],
            "validation_uses_structured_events": True,
        },
        "selected": {
            "state": state_dict,
            "target": target_dict,
            "selected_symbol_ids": target_dict.get("selected_symbol_ids") or [],
            "selected_object_ids": target_dict.get("selected_object_ids") or [],
            "selected_resonance_roles": target_dict.get("selected_resonance_roles") or [],
            "required_source_refs": target_dict.get("required_source_refs") or [],
            "source_evidence": target_dict.get("source_evidence") or [],
            "rationale_codes": target_dict.get("rationale_codes") or [],
        },
        "actual": actual,
        "reasons": failure_codes
        or (
            ["symbolic_object_resonance_target_selected"]
            if applicable and target_dict.get("selected_object_ids") and not validation_dict
            else []
        ),
        "source": source,
        "failure_class": "recoverable_dramatic_failure" if failure_codes else None,
        "failure_reason": failure_codes[0] if failure_codes else None,
    }
