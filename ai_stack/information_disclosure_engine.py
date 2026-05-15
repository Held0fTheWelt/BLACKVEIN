"""Policy-driven information-disclosure derivation and validation."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from ai_stack.information_disclosure_contracts import (
    DISCLOSURE_FAILURE_CODES,
    DISCLOSURE_MODES,
    DISCLOSURE_STAGES,
    INFORMATION_DISCLOSURE_SCHEMA_VERSION,
    InformationDisclosureTarget,
    InformationDisclosureValidation,
    normalize_information_disclosure_policy,
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


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.casefold()) if len(token) >= 4}


def _stable_hash(text: str) -> str:
    normalized = " ".join(_TOKEN_RE.findall(str(text or "").casefold()))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _runtime_policy_information_disclosure(module_runtime_policy: dict[str, Any] | None) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    direct = raw.get("information_disclosure_policy")
    if isinstance(direct, dict):
        return normalize_information_disclosure_policy(direct)
    governance = raw.get("runtime_governance_policy") if isinstance(raw.get("runtime_governance_policy"), dict) else {}
    nested = governance.get("information_disclosure")
    return normalize_information_disclosure_policy(nested if isinstance(nested, dict) else {})


def _context_values(
    *,
    scene_plan_record: dict[str, Any] | None,
    semantic_move_record: dict[str, Any] | None,
    pacing_mode: str | None,
    prior_continuity_impacts: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    plan = scene_plan_record if isinstance(scene_plan_record, dict) else {}
    semantic = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    prior_classes = [
        _text(item.get("class") or item.get("continuity_class"))
        for item in (prior_continuity_impacts or [])
        if isinstance(item, dict) and _text(item.get("class") or item.get("continuity_class"))
    ]
    return {
        "scene_function": _text(plan.get("scene_function") or plan.get("selected_scene_function")),
        "semantic_move": _text(semantic.get("move_type") or semantic.get("semantic_move")),
        "semantic_family": _text(semantic.get("social_move_family")),
        "pacing_mode": _text(pacing_mode),
        "prior_continuity_classes": prior_classes,
    }


def _matches_any(value: str, allowed: Any) -> bool:
    values = {_text(item) for item in _as_list(allowed) if _text(item)}
    return bool(value and value in values)


def _unit_unlocked(unit: dict[str, Any], context: dict[str, Any]) -> bool:
    conditions = unit.get("unlock_conditions") if isinstance(unit.get("unlock_conditions"), dict) else {}
    if not conditions or conditions.get("always") is True:
        return True
    checks: list[bool] = []
    if "scene_functions_any" in conditions:
        checks.append(_matches_any(context.get("scene_function", ""), conditions.get("scene_functions_any")))
    if "semantic_moves_any" in conditions:
        checks.append(_matches_any(context.get("semantic_move", ""), conditions.get("semantic_moves_any")))
    if "semantic_families_any" in conditions:
        checks.append(_matches_any(context.get("semantic_family", ""), conditions.get("semantic_families_any")))
    if "pacing_modes_any" in conditions:
        checks.append(_matches_any(context.get("pacing_mode", ""), conditions.get("pacing_modes_any")))
    if "prior_continuity_classes_any" in conditions:
        expected = {_text(item) for item in _as_list(conditions.get("prior_continuity_classes_any")) if _text(item)}
        actual = set(context.get("prior_continuity_classes") or [])
        checks.append(bool(expected.intersection(actual)))
    return any(checks)


def _mode_for_context(scene_function: str, selected_units: list[dict[str, Any]]) -> str | None:
    if not selected_units:
        return None
    if scene_function == "reveal_surface":
        preferred = "confirmation"
    elif scene_function == "withhold_or_evade":
        preferred = "withheld"
    else:
        preferred = "visible_hint"
    allowed = {
        mode
        for unit in selected_units
        for mode in _clean_str_list(unit.get("allowed_modes"))
        if mode in DISCLOSURE_MODES
    }
    return preferred if preferred in allowed else sorted(allowed)[0] if allowed else None


def derive_information_disclosure(
    *,
    scene_plan_record: dict[str, Any] | None,
    semantic_move_record: dict[str, Any] | None = None,
    pacing_mode: str | None = None,
    prior_continuity_impacts: list[dict[str, Any]] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select bounded disclosure units from module policy and structured state."""
    policy = _runtime_policy_information_disclosure(module_runtime_policy)
    units = [row for row in (policy.get("units") or []) if isinstance(row, dict)]
    context = _context_values(
        scene_plan_record=scene_plan_record,
        semantic_move_record=semantic_move_record,
        pacing_mode=pacing_mode,
        prior_continuity_impacts=prior_continuity_impacts,
    )
    if not policy.get("enabled") or not units:
        return {
            "policy": policy,
            "target": InformationDisclosureTarget(
                policy_enabled=bool(policy.get("enabled")),
                rationale_codes=["information_disclosure_not_applicable"],
            ).to_dict(),
        }

    eligible = [unit for unit in units if _unit_unlocked(unit, context)]
    budget = int(policy.get("max_visible_units_per_turn") or 0)
    selected = eligible[:budget] if budget > 0 else []
    selected_ids = [str(unit.get("id")) for unit in selected if _text(unit.get("id"))]
    eligible_ids = [str(unit.get("id")) for unit in eligible if _text(unit.get("id"))]
    withheld_ids = [
        str(unit.get("id"))
        for unit in units
        if _text(unit.get("id")) and str(unit.get("id")) not in selected_ids
    ]
    target = InformationDisclosureTarget(
        policy_enabled=True,
        commit_impact=str(policy.get("default_commit_impact") or "diagnostic"),
        require_structured_events=bool(policy.get("require_structured_events")),
        max_visible_units_per_turn=budget,
        selected_unit_ids=selected_ids,
        allowed_unit_ids=eligible_ids,
        withheld_unit_ids=withheld_ids,
        forbidden_unit_ids=withheld_ids,
        selected_units=[
            {
                "id": unit.get("id"),
                "stage": unit.get("stage"),
                "allowed_modes": unit.get("allowed_modes") or [],
                "semantic_profile_keys": sorted((unit.get("semantic_profile") or {}).keys())
                if isinstance(unit.get("semantic_profile"), dict)
                else [],
            }
            for unit in selected
        ],
        disclosure_mode=_mode_for_context(context.get("scene_function", ""), selected),
        rationale_codes=[
            "information_disclosure_policy_enabled",
            "information_disclosure_units_selected" if selected_ids else "information_disclosure_units_withheld",
        ],
        source_evidence=[
            {"source": "scene_plan_record", "field": "scene_function", "value": context.get("scene_function")},
            {"source": "semantic_move_record", "field": "move_type", "value": context.get("semantic_move")},
        ],
    ).to_dict()
    return {"policy": policy, "target": target}


def _event_rows(structured_output: dict[str, Any] | None) -> list[dict[str, Any]]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    events = structured.get("disclosure_events")
    return [row for row in events if isinstance(row, dict)] if isinstance(events, list) else []


def _visible_text(visible_blocks: list[dict[str, Any]] | None) -> str:
    bits: list[str] = []
    for block in visible_blocks or []:
        if not isinstance(block, dict):
            continue
        for key in ("text", "line", "content", "narration"):
            value = _text(block.get(key))
            if value:
                bits.append(value)
        payload = block.get("payload") if isinstance(block.get("payload"), dict) else {}
        for key in ("text", "content"):
            value = _text(payload.get(key))
            if value:
                bits.append(value)
    return "\n".join(bits)


def validate_information_disclosure_realization(
    *,
    information_disclosure_target: dict[str, Any] | None,
    structured_output: dict[str, Any] | None = None,
    visible_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate disclosure events against the selected target."""
    target = information_disclosure_target if isinstance(information_disclosure_target, dict) else {}
    if not target or not bool(target.get("policy_enabled")):
        return InformationDisclosureValidation(
            schema_version=INFORMATION_DISCLOSURE_SCHEMA_VERSION,
            status="not_applicable",
            contract_pass=True,
            target=target,
        ).to_dict()

    events = _event_rows(structured_output)
    max_units = int(target.get("max_visible_units_per_turn") or 0)
    selected_ids = set(_clean_str_list(target.get("selected_unit_ids")))
    forbidden_ids = set(_clean_str_list(target.get("forbidden_unit_ids")))
    selected_units = {
        _text(row.get("id")): row
        for row in (target.get("selected_units") or [])
        if isinstance(row, dict) and _text(row.get("id"))
    }
    failure_codes: list[str] = []
    event_unit_ids = [_text(row.get("unit_id") or row.get("id")) for row in events]
    visible_event_unit_ids = [unit_id for unit_id in event_unit_ids if unit_id]
    if bool(target.get("require_structured_events")) and selected_ids and not visible_event_unit_ids:
        failure_codes.append("information_disclosure_missing_required_event")
    if max_units >= 0 and len(visible_event_unit_ids) > max_units:
        failure_codes.append("information_disclosure_over_budget")
    forbidden_event_ids = [
        unit_id
        for unit_id in visible_event_unit_ids
        if unit_id in forbidden_ids or unit_id not in selected_ids
    ]
    if forbidden_event_ids:
        failure_codes.append("information_disclosure_forbidden_unit")
    stage_failures: list[str] = []
    mode_failures: list[str] = []
    for event in events:
        unit_id = _text(event.get("unit_id") or event.get("id"))
        if unit_id not in selected_ids:
            continue
        expected = selected_units.get(unit_id) or {}
        stage = _text(event.get("stage"))
        if stage and stage in DISCLOSURE_STAGES and stage != _text(expected.get("stage")):
            stage_failures.append(unit_id)
        mode = _text(event.get("mode"))
        allowed_modes = set(_clean_str_list(expected.get("allowed_modes")))
        if mode and mode in DISCLOSURE_MODES and allowed_modes and mode not in allowed_modes:
            mode_failures.append(unit_id)
    if stage_failures:
        failure_codes.append("information_disclosure_forbidden_stage")
    if mode_failures:
        failure_codes.append("information_disclosure_forbidden_mode")
    failure_codes = [
        code for code in dict.fromkeys(failure_codes) if code in DISCLOSURE_FAILURE_CODES
    ]
    visible_text = _visible_text(visible_blocks)
    actual = {
        "structured_events_present": bool(events),
        "event_count": len(events),
        "visible_unit_ids": visible_event_unit_ids,
        "selected_unit_ids": sorted(selected_ids),
        "withheld_unit_ids": _clean_str_list(target.get("withheld_unit_ids")),
        "forbidden_event_unit_ids": forbidden_event_ids,
        "stage_failure_unit_ids": stage_failures,
        "mode_failure_unit_ids": mode_failures,
        "budget_used": len(visible_event_unit_ids),
        "max_visible_units_per_turn": max_units,
        "visible_text_sha256": _stable_hash(visible_text),
        "visible_token_count": len(_tokens(visible_text)),
    }
    contract_pass = not failure_codes
    commit_impact = _text(target.get("commit_impact")) or "diagnostic"
    status = "approved" if contract_pass else "rejected" if commit_impact in {"recover", "reject"} else "degraded"
    return InformationDisclosureValidation(
        schema_version=INFORMATION_DISCLOSURE_SCHEMA_VERSION,
        status=status,
        contract_pass=contract_pass,
        failure_codes=failure_codes,
        feedback_code=failure_codes[0] if failure_codes else None,
        target=target,
        actual=actual,
        source_evidence=target.get("source_evidence") if isinstance(target.get("source_evidence"), list) else [],
    ).to_dict()
