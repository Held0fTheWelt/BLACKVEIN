"""Policy-driven tonal consistency derivation and structured validation."""

from __future__ import annotations

import re
from typing import Any

from ai_stack.contracts.tonal_consistency_contracts import (
    TONAL_CONSISTENCY_DEFAULT_CLASSIFICATION_SOURCE,
    TONAL_CONSISTENCY_FAILURE_CODES,
    TONAL_CONSISTENCY_POLICY_VERSION,
    TONAL_CONSISTENCY_SCHEMA_VERSION,
    TonalConsistencyClassification,
    TonalConsistencyEvidenceRef,
    TonalConsistencyTarget,
    TonalConsistencyValidation,
    normalize_tonal_consistency_policy,
)
from ai_stack.tonal_consistency_classifier import classify_tonal_consistency_from_policy


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


def _evidence(source: str, field: str, value: Any) -> TonalConsistencyEvidenceRef:
    return TonalConsistencyEvidenceRef(source=source, field=field, value=value)


def _runtime_policy_tonal_consistency(
    module_runtime_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    direct = raw.get("tonal_consistency_policy")
    if isinstance(direct, dict):
        return normalize_tonal_consistency_policy(direct)
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    nested = governance.get("tonal_consistency")
    return normalize_tonal_consistency_policy(nested if isinstance(nested, dict) else {})


def _profile_id_for_scene_function(policy: dict[str, Any], scene_function: str | None) -> str | None:
    scene_key = _text(scene_function)
    by_scene = policy.get("profile_by_scene_function")
    if scene_key and isinstance(by_scene, dict):
        mapped = _text(by_scene.get(scene_key))
        if mapped:
            return mapped
    return _text(policy.get("default_profile_id")) or None


def _profile(policy: dict[str, Any], profile_id: str | None) -> dict[str, Any]:
    profiles = policy.get("tone_profiles")
    if not isinstance(profiles, dict):
        return {}
    row = profiles.get(_text(profile_id))
    return row if isinstance(row, dict) else {}


def _scene_function(scene_plan_record: dict[str, Any] | None) -> str | None:
    plan = scene_plan_record if isinstance(scene_plan_record, dict) else {}
    for value in (
        plan.get("selected_scene_function"),
        plan.get("scene_function"),
        plan.get("scene_function_id"),
    ):
        text = _text(value)
        if text:
            return text
    return None


def _pressure_band(
    social_pressure_target: dict[str, Any] | None,
    scene_energy_target: dict[str, Any] | None,
) -> str | None:
    social = social_pressure_target if isinstance(social_pressure_target, dict) else {}
    energy = scene_energy_target if isinstance(scene_energy_target, dict) else {}
    for value in (
        social.get("target_band"),
        social.get("current_band"),
        energy.get("pressure_vector"),
    ):
        text = _text(value)
        if text:
            return text
    return None


def derive_tonal_consistency(
    *,
    scene_plan_record: dict[str, Any] | None = None,
    scene_energy_target: dict[str, Any] | None = None,
    pacing_rhythm_target: dict[str, Any] | None = None,
    social_pressure_target: dict[str, Any] | None = None,
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select a bounded tone target from module policy and structured state."""

    policy = _runtime_policy_tonal_consistency(module_runtime_policy)
    scene_function = _scene_function(scene_plan_record)
    profile_id = _profile_id_for_scene_function(policy, scene_function)
    profile = _profile(policy, profile_id)
    enabled = bool(policy.get("enabled") and profile)
    dimensions = _clean_str_list(profile.get("target_dimension_ids"))
    required = _clean_str_list(profile.get("required_dimension_ids")) or dimensions
    allowed_registers = (
        _clean_str_list(profile.get("allowed_registers"))
        or _clean_str_list(policy.get("allowed_registers"))
    )
    forbidden_genres = (
        _clean_str_list(profile.get("forbidden_genre_labels"))
        or _clean_str_list(policy.get("forbidden_genre_labels"))
    )
    forbidden_markers = profile.get("forbidden_marker_map")
    if not isinstance(forbidden_markers, dict):
        forbidden_markers = policy.get("forbidden_marker_map")
    forbidden_markers = forbidden_markers if isinstance(forbidden_markers, dict) else {}
    dimension_markers = profile.get("dimension_marker_map")
    if not isinstance(dimension_markers, dict):
        dimension_markers = policy.get("dimension_marker_map")
    dimension_markers = dimension_markers if isinstance(dimension_markers, dict) else {}
    failure_severity = policy.get("failure_severity")
    if not isinstance(failure_severity, dict):
        failure_severity = {}

    evidence = [
        _evidence("module_runtime_policy", "tonal_consistency.profile_id", profile_id),
    ]
    if scene_function:
        evidence.append(_evidence("scene_plan_record", "selected_scene_function", scene_function))
    energy = scene_energy_target if isinstance(scene_energy_target, dict) else {}
    rhythm = pacing_rhythm_target if isinstance(pacing_rhythm_target, dict) else {}
    if _text(energy.get("target_transition")):
        evidence.append(_evidence("scene_energy_target", "target_transition", energy.get("target_transition")))
    if _text(rhythm.get("cadence")):
        evidence.append(_evidence("pacing_rhythm_target", "cadence", rhythm.get("cadence")))

    target = TonalConsistencyTarget(
        policy_enabled=enabled,
        profile_id=profile_id,
        target_dimension_ids=dimensions,
        required_dimension_ids=required,
        allowed_registers=allowed_registers,
        forbidden_genre_labels=forbidden_genres,
        dimension_marker_map={
            str(key): _clean_str_list(value)
            for key, value in dimension_markers.items()
            if _text(key) and _clean_str_list(value)
        },
        forbidden_marker_map={
            str(key): _clean_str_list(value)
            for key, value in forbidden_markers.items()
            if _text(key) and _clean_str_list(value)
        },
        require_structured_classification=bool(
            policy.get("require_structured_classification")
        ),
        min_required_dimensions_present=_bounded_int(
            policy.get("min_required_dimensions_present"), 1, minimum=0, maximum=16
        ),
        max_forbidden_marker_hits=_bounded_int(
            policy.get("max_forbidden_marker_hits"), 0, minimum=0, maximum=20
        ),
        drift_behavior=_text(policy.get("default_drift_behavior")) or "diagnostic",  # type: ignore[arg-type]
        live_loop_mode=_text(policy.get("live_loop_mode")) or "shadow",  # type: ignore[arg-type]
        max_repair_attempts=_bounded_int(
            policy.get("max_repair_attempts"), 1, minimum=0, maximum=3
        ),
        classification_source=_text(policy.get("classification_source"))
        or TONAL_CONSISTENCY_DEFAULT_CLASSIFICATION_SOURCE,
        failure_severity={
            str(code): str(severity)
            for code, severity in failure_severity.items()
            if _text(code) and _text(severity)
        },
        scene_function=scene_function,
        pressure_band=_pressure_band(social_pressure_target, scene_energy_target),
        source_evidence=evidence,
        rationale_codes=[
            "tonal_consistency_policy_enabled" if enabled else "tonal_consistency_not_applicable",
            "tonal_consistency_profile_selected" if profile_id else "tonal_consistency_profile_missing",
        ],
    ).to_runtime_dict()
    return {"schema_version": TONAL_CONSISTENCY_SCHEMA_VERSION, "policy": policy, "target": target}


def compact_tonal_consistency_context(target: dict[str, Any] | None) -> dict[str, Any]:
    """Return model-visible context without prose examples or judge categories."""

    src = target if isinstance(target, dict) else {}
    if not src or not src.get("policy_enabled"):
        return {}
    return {
        "schema_version": src.get("schema_version"),
        "profile_id": src.get("profile_id"),
        "target_dimension_ids": src.get("target_dimension_ids") or [],
        "required_dimension_ids": src.get("required_dimension_ids") or [],
        "allowed_registers": src.get("allowed_registers") or [],
        "forbidden_marker_classes": sorted(
            (src.get("forbidden_marker_map") or {}).keys()
        )
        if isinstance(src.get("forbidden_marker_map"), dict)
        else [],
        "dimension_marker_classes": sorted(
            (src.get("dimension_marker_map") or {}).keys()
        )
        if isinstance(src.get("dimension_marker_map"), dict)
        else [],
        "drift_behavior": src.get("drift_behavior"),
        "live_loop_mode": src.get("live_loop_mode"),
        "classification_source": src.get("classification_source"),
        "scene_function": src.get("scene_function"),
        "pressure_band": src.get("pressure_band"),
    }


def _classification_payload(structured_output: dict[str, Any] | None) -> dict[str, Any]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    for key in (
        "tonal_consistency_classification",
        "tone_classification",
        "tonal_consistency",
    ):
        payload = structured.get(key)
        if isinstance(payload, dict):
            return payload
    return {}


def _visible_texts(structured_output: dict[str, Any] | None) -> list[str]:
    structured = structured_output if isinstance(structured_output, dict) else {}
    texts: list[str] = []
    for key in (
        "narrative_response",
        "narration_summary",
        "gm_response",
        "visible_output",
        "consequence_summary",
    ):
        text = _text(structured.get(key))
        if text:
            texts.append(text)
    for key in ("spoken_lines", "action_lines", "state_effects"):
        rows = structured.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            for field in ("text", "content", "description"):
                text = _text(row.get(field))
                if text:
                    texts.append(text)
    return texts


def _marker_hits(
    *,
    forbidden_marker_map: dict[str, list[str]],
    structured_output: dict[str, Any] | None,
) -> dict[str, int]:
    visible_text = "\n".join(_visible_texts(structured_output)).casefold()
    if not visible_text:
        return {}
    hits: dict[str, int] = {}
    for label, markers in forbidden_marker_map.items():
        count = 0
        for marker in markers:
            token = _text(marker).casefold()
            if not token:
                continue
            count += len(re.findall(re.escape(token), visible_text))
        if count:
            hits[str(label)] = count
    return hits


def classify_tonal_consistency_realization(
    *,
    tonal_consistency_target: dict[str, Any] | None,
    structured_output: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify tone evidence from structured output and policy markers."""

    target = tonal_consistency_target if isinstance(tonal_consistency_target, dict) else {}
    classification_source = _text(
        target.get("classification_source")
        or TONAL_CONSISTENCY_DEFAULT_CLASSIFICATION_SOURCE
    )
    if classification_source == TONAL_CONSISTENCY_DEFAULT_CLASSIFICATION_SOURCE:
        return classify_tonal_consistency_from_policy(
            tonal_consistency_target=target,
            structured_output=structured_output,
        )
    payload = _classification_payload(structured_output)
    marker_map = target.get("forbidden_marker_map") if isinstance(target.get("forbidden_marker_map"), dict) else {}
    detected_hits = _marker_hits(
        forbidden_marker_map={
            str(key): _clean_str_list(value)
            for key, value in marker_map.items()
            if _text(key) and _clean_str_list(value)
        },
        structured_output=structured_output,
    )
    payload_hits = payload.get("forbidden_marker_hits")
    merged_hits: dict[str, int] = {}
    if isinstance(payload_hits, dict):
        for key, value in payload_hits.items():
            try:
                count = int(value)
            except (TypeError, ValueError):
                count = 0
            if count > 0:
                merged_hits[str(key)] = count
    for key, count in detected_hits.items():
        merged_hits[key] = merged_hits.get(key, 0) + count

    confidence = payload.get("confidence")
    try:
        confidence_value = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        confidence_value = None

    classification = TonalConsistencyClassification(
        structured_classification_present=bool(payload),
        realized_dimension_ids=_clean_str_list(
            payload.get("realized_dimension_ids")
            or payload.get("dimension_ids")
            or payload.get("matched_dimension_ids")
        ),
        register_label=_text(payload.get("register_label") or payload.get("register")) or None,
        genre_label=_text(payload.get("genre_label") or payload.get("genre")) or None,
        forbidden_marker_hits=merged_hits,
        marker_hit_count=sum(merged_hits.values()),
        confidence=confidence_value,
        classification_source=classification_source,
        independent_classifier=False,
        source_evidence=[
            _evidence(
                "structured_output",
                "tonal_consistency_classification",
                bool(payload),
            ),
            _evidence("structured_output", "policy_marker_scan", bool(detected_hits)),
        ],
    )
    return classification.to_runtime_dict()


def validate_tonal_consistency_realization(
    *,
    tonal_consistency_target: dict[str, Any] | None,
    structured_output: dict[str, Any] | None = None,
    classification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate structured tone classification against the selected target."""

    if not isinstance(tonal_consistency_target, dict):
        return TonalConsistencyValidation(
            status="not_applicable",
            contract_pass=True,
            actual={"reason": "tonal_consistency_target_missing"},
        ).to_runtime_dict()
    try:
        target = TonalConsistencyTarget.model_validate(tonal_consistency_target)
    except Exception:
        return TonalConsistencyValidation(
            status="rejected",
            contract_pass=False,
            failure_codes=["tonal_consistency_target_mismatch"],
            feedback_code="tonal_consistency_target_mismatch",
            target=tonal_consistency_target,
            actual={"reason": "invalid_tonal_consistency_target"},
        ).to_runtime_dict()
    if not target.policy_enabled:
        return TonalConsistencyValidation(
            status="not_applicable",
            contract_pass=True,
            target=target.to_runtime_dict(),
            actual={"reason": "tonal_consistency_policy_disabled"},
        ).to_runtime_dict()

    classification_dict = (
        classification
        if isinstance(classification, dict)
        else classify_tonal_consistency_realization(
            tonal_consistency_target=target.to_runtime_dict(),
            structured_output=structured_output,
        )
    )
    try:
        classified = TonalConsistencyClassification.model_validate(classification_dict)
    except Exception:
        classified = TonalConsistencyClassification()

    failure_codes: list[str] = []
    if target.require_structured_classification and not classified.structured_classification_present:
        failure_codes.append("tonal_consistency_classification_missing")

    realized = set(classified.realized_dimension_ids)
    required = set(target.required_dimension_ids)
    missing_required = sorted(required.difference(realized))
    required_present_count = len(required.intersection(realized))
    if missing_required or required_present_count < target.min_required_dimensions_present:
        failure_codes.append("tonal_consistency_required_dimension_missing")

    if target.allowed_registers and classified.register_label:
        if classified.register_label not in set(target.allowed_registers):
            failure_codes.append("tonal_consistency_register_mismatch")

    if classified.genre_label and classified.genre_label in set(target.forbidden_genre_labels):
        failure_codes.append("tonal_consistency_wrong_genre")

    if classified.marker_hit_count > target.max_forbidden_marker_hits:
        failure_codes.append("tonal_consistency_forbidden_marker_detected")

    deduped = [
        code for code in dict.fromkeys(failure_codes) if code in TONAL_CONSISTENCY_FAILURE_CODES
    ]
    if not deduped:
        status = "approved"
    elif target.live_loop_mode == "shadow" and target.drift_behavior == "diagnostic":
        status = "degraded"
    else:
        status = "rejected"

    actual = classified.to_runtime_dict()
    actual.update(
        {
            "missing_required_dimension_ids": missing_required,
            "required_dimension_count": len(required),
            "required_dimension_present_count": required_present_count,
            "failure_codes": deduped,
            "contract_pass": not deduped,
        }
    )
    return TonalConsistencyValidation(
        status=status,  # type: ignore[arg-type]
        contract_pass=not deduped,
        failure_codes=deduped,
        feedback_code=deduped[0] if deduped else None,
        target=target.to_runtime_dict(),
        actual=actual,
        source_evidence=classified.source_evidence,
    ).to_runtime_dict()


def build_tonal_consistency_aspect_record(
    *,
    target: dict[str, Any] | None,
    validation: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
    source: str = "runtime",
) -> dict[str, Any]:
    """Build a RuntimeAspectLedger-compatible tonal-consistency record."""

    target_dict = target if isinstance(target, dict) else {}
    validation_dict = validation if isinstance(validation, dict) else {}
    policy_dict = (
        policy if isinstance(policy, dict) else normalize_tonal_consistency_policy(None)
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
    drift_behavior = _text(
        target_dict.get("drift_behavior") or policy_dict.get("default_drift_behavior")
    )
    return {
        "applicable": applicable,
        "status": aspect_status,
        "expected": {
            "schema_version": target_dict.get("schema_version")
            or TONAL_CONSISTENCY_SCHEMA_VERSION,
            "policy_version": target_dict.get("policy_version")
            or TONAL_CONSISTENCY_POLICY_VERSION,
            "policy_present": bool(policy_dict.get("enabled") or target_dict),
            "policy_enabled": bool(target_dict.get("policy_enabled")),
            "require_structured_classification": bool(
                target_dict.get("require_structured_classification")
            ),
            "drift_behavior": drift_behavior or None,
            "min_required_dimensions_present": int(
                target_dict.get("min_required_dimensions_present")
                if target_dict.get("min_required_dimensions_present") is not None
                else policy_dict.get("min_required_dimensions_present") or 0
            ),
            "max_forbidden_marker_hits": int(
                target_dict.get("max_forbidden_marker_hits")
                if target_dict.get("max_forbidden_marker_hits") is not None
                else policy_dict.get("max_forbidden_marker_hits") or 0
            ),
            "live_loop_mode": target_dict.get("live_loop_mode")
            or policy_dict.get("live_loop_mode"),
            "max_repair_attempts": int(
                target_dict.get("max_repair_attempts")
                if target_dict.get("max_repair_attempts") is not None
                else policy_dict.get("max_repair_attempts") or 0
            ),
            "classification_source": target_dict.get("classification_source")
            or policy_dict.get("classification_source"),
        },
        "selected": {
            "target": target_dict,
            "profile_id": target_dict.get("profile_id"),
            "target_dimension_ids": target_dict.get("target_dimension_ids") or [],
            "required_dimension_ids": target_dict.get("required_dimension_ids") or [],
            "allowed_registers": target_dict.get("allowed_registers") or [],
            "forbidden_genre_labels": target_dict.get("forbidden_genre_labels") or [],
            "forbidden_marker_classes": sorted(
                (target_dict.get("forbidden_marker_map") or {}).keys()
            )
            if isinstance(target_dict.get("forbidden_marker_map"), dict)
            else [],
            "dimension_marker_classes": sorted(
                (target_dict.get("dimension_marker_map") or {}).keys()
            )
            if isinstance(target_dict.get("dimension_marker_map"), dict)
            else [],
            "scene_function": target_dict.get("scene_function"),
            "pressure_band": target_dict.get("pressure_band"),
        },
        "actual": actual,
        "reasons": failure_codes
        or (
            ["tonal_consistency_target_selected"]
            if applicable and target_dict.get("profile_id") and not validation_dict
            else []
        ),
        "source": source,
        "failure_class": (
            "degradation_only"
            if failure_codes and drift_behavior == "diagnostic"
            else "recoverable_dramatic_failure"
            if failure_codes
            else None
        ),
        "failure_reason": failure_codes[0] if failure_codes else None,
    }
