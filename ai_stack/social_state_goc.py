"""
Bounded social-state projection from continuity, threads, and scene
assessment (derived only).
"""

from __future__ import annotations

import hashlib
from typing import Any

from ai_stack.scene_director_goc import prior_continuity_classes
from ai_stack.social_state_contract import SocialStateRecord


def build_social_state_record(
    *,
    prior_continuity_impacts: list[dict[str, Any]] | None,
    active_narrative_threads: list[dict[str, Any]] | None,
    thread_pressure_summary: str | None,
    scene_assessment: dict[str, Any] | None,
    prior_social_state_record: dict[str, Any] | None = None,
    yaml_slice: dict[str, Any] | None = None,
) -> SocialStateRecord:
    """Describe what ``build_social_state_record`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        prior_continuity_impacts: ``prior_continuity_impacts`` (list[dict[str, Any]] | None); meaning follows the type and call sites.
        active_narrative_threads: ``active_narrative_threads`` (list[dict[str, Any]] | None); meaning follows the type and call sites.
        thread_pressure_summary: ``thread_pressure_summary`` (str | None); meaning follows the type and call sites.
        scene_assessment: ``scene_assessment`` (dict[str,
            Any] | None); meaning follows the type and call sites.
        prior_social_state_record: previously committed social-state record
            rehydrated from planner truth, if available.
        yaml_slice: optional canonical YAML slice used to map pressure to
            relationship-axis ids.
    
    Returns:
        SocialStateRecord:
            Returns a value of type ``SocialStateRecord``; see the function body for structure, error paths, and sentinels.
    """
    prior_classes = prior_continuity_classes(prior_continuity_impacts)
    threads = active_narrative_threads if isinstance(active_narrative_threads, list) else []
    n = sum(1 for t in threads if isinstance(t, dict))
    tsum = (thread_pressure_summary or "").strip()
    sa = scene_assessment if isinstance(scene_assessment, dict) else {}
    pressure = str(sa.get("pressure_state") or "moderate_tension")
    thread_pressure_state = str(sa.get("thread_pressure_state") or "")
    phase = sa.get("guidance_phase_key")
    phase_s = str(phase) if phase else None

    asym = "neutral"
    if "blame_pressure" in prior_classes and "repair_attempt" in prior_classes:
        asym = "blame_under_repair_tension"
    elif "blame_pressure" in prior_classes:
        asym = "blame_on_host_spouse_axis"
    elif "alliance_shift" in prior_classes:
        asym = "alliance_reposition_active"

    risk = "moderate"
    if (
        pressure in {"high_blame", "thread_pressure_high"}
        or thread_pressure_state == "high_unresolved_thread_pressure"
        or "blame_pressure" in prior_classes
    ):
        risk = "high"
    elif not prior_classes and n == 0:
        risk = "low"

    axis_ids = _derive_relationship_axis_ids(
        yaml_slice=yaml_slice,
        prior_classes=prior_classes,
        pressure=pressure,
        thread_pressure_state=thread_pressure_state,
        guidance_phase_key=phase_s,
        responder_asymmetry_code=asym,
        social_risk_band=risk,
    )

    prior_fp: str | None = None
    prior_risk: str | None = None
    continuity_status = "initial_social_state"
    if isinstance(prior_social_state_record, dict) and prior_social_state_record:
        try:
            prior_model = SocialStateRecord.model_validate(prior_social_state_record)
            prior_fp = social_state_fingerprint(prior_model)
            prior_risk = prior_model.social_risk_band
            stable = (
                prior_model.scene_pressure_state == pressure
                and prior_model.responder_asymmetry_code == asym
                and prior_model.social_risk_band == risk
                and prior_model.active_relationship_axis_ids == axis_ids
            )
            continuity_status = (
                "stable_prior_social_state" if stable else "social_state_shifted"
            )
        except Exception:
            continuity_status = "social_state_shifted"

    relationship_pressure_codes = _derive_relationship_pressure_codes(
        prior_classes=prior_classes,
        pressure=pressure,
        thread_pressure_state=thread_pressure_state,
        responder_asymmetry_code=asym,
        social_risk_band=risk,
        social_continuity_status=continuity_status,
        axis_ids=axis_ids,
    )

    return SocialStateRecord(
        prior_continuity_classes=prior_classes,
        scene_pressure_state=pressure,
        active_thread_count=n,
        thread_pressure_summary_present=bool(tsum),
        guidance_phase_key=phase_s,
        responder_asymmetry_code=asym,
        social_risk_band=risk,
        prior_social_state_fingerprint=prior_fp,
        prior_social_risk_band=prior_risk,
        social_continuity_status=continuity_status,
        relationship_pressure_codes=relationship_pressure_codes,
        active_relationship_axis_ids=axis_ids,
        dominant_relationship_axis_id=axis_ids[0] if axis_ids else None,
    )


def _bounded_unique_strings(values: list[Any], *, limit: int) -> list[str]:
    out: list[str] = []
    for raw in values:
        value = str(raw or "").strip()
        if value and value not in out:
            out.append(value)
        if len(out) >= limit:
            break
    return out


def _relationship_axis_text(axis_id: str, axis: Any) -> str:
    if not isinstance(axis, dict):
        return axis_id.lower()
    parts: list[str] = [axis_id, str(axis.get("id") or "")]
    for key in ("name", "description", "type"):
        value = axis.get(key)
        if isinstance(value, str):
            parts.append(value)
    rels = axis.get("relationships")
    if isinstance(rels, list):
        parts.extend(str(item) for item in rels[:8])
    return " ".join(parts).lower()


def _matching_axis_ids(
    axes: dict[str, Any],
    *,
    tokens: set[str],
    limit: int,
) -> list[str]:
    matches: list[str] = []
    for axis_id, axis in axes.items():
        axis_key = str(axis_id or "").strip()
        if not axis_key:
            continue
        text = _relationship_axis_text(axis_key, axis)
        if any(token in text for token in tokens):
            matches.append(axis_key)
        if len(matches) >= limit:
            break
    return matches


def _derive_relationship_axis_ids(
    *,
    yaml_slice: dict[str, Any] | None,
    prior_classes: list[str],
    pressure: str,
    thread_pressure_state: str,
    guidance_phase_key: str | None,
    responder_asymmetry_code: str,
    social_risk_band: str,
) -> list[str]:
    yslice = yaml_slice if isinstance(yaml_slice, dict) else {}
    axes = yslice.get("relationship_axes") if isinstance(yslice.get("relationship_axes"), dict) else {}
    if not axes:
        return []

    candidates: list[str] = []
    high_pressure = (
        social_risk_band == "high"
        or pressure in {"high_blame", "thread_pressure_high"}
        or thread_pressure_state == "high_unresolved_thread_pressure"
    )
    if responder_asymmetry_code in {"blame_on_host_spouse_axis", "blame_under_repair_tension"}:
        candidates.extend(
            _matching_axis_ids(
                axes,
                tokens={"spousal", "spouse", "partner", "internal", "couple"},
                limit=2,
            )
        )
    if responder_asymmetry_code == "alliance_reposition_active" or "alliance_shift" in prior_classes:
        candidates.extend(
            _matching_axis_ids(
                axes,
                tokens={"host", "guest", "power", "cross", "alliance"},
                limit=2,
            )
        )
    if high_pressure or "blame_pressure" in prior_classes:
        candidates.extend(
            _matching_axis_ids(
                axes,
                tokens={"moral", "pragmatic", "worldview", "dominance", "devaluation", "status", "contempt"},
                limit=2,
            )
        )
    if guidance_phase_key and "faction" in guidance_phase_key.lower():
        candidates.extend(
            _matching_axis_ids(
                axes,
                tokens={"host", "guest", "power", "alliance"},
                limit=1,
            )
        )

    if not candidates and (high_pressure or responder_asymmetry_code != "neutral"):
        candidates.append(sorted(str(axis_id) for axis_id in axes.keys())[0])
    return _bounded_unique_strings(candidates, limit=4)


def _derive_relationship_pressure_codes(
    *,
    prior_classes: list[str],
    pressure: str,
    thread_pressure_state: str,
    responder_asymmetry_code: str,
    social_risk_band: str,
    social_continuity_status: str,
    axis_ids: list[str],
) -> list[str]:
    codes: list[Any] = []
    if responder_asymmetry_code != "neutral":
        codes.append(f"asymmetry:{responder_asymmetry_code}")
    if social_risk_band == "high":
        codes.append("risk:high")
    if pressure and pressure not in {"moderate_tension", "unknown"}:
        codes.append(f"scene_pressure:{pressure}")
    if thread_pressure_state:
        codes.append(f"thread_pressure:{thread_pressure_state}")
    if "alliance_shift" in prior_classes:
        codes.append("continuity_class:alliance_shift")
    if "blame_pressure" in prior_classes:
        codes.append("continuity_class:blame_pressure")
    if social_continuity_status == "social_state_shifted":
        codes.append("continuity:social_state_shifted")
    if axis_ids:
        codes.append("relationship_axis_active")
    return _bounded_unique_strings(codes, limit=8)


def social_state_fingerprint(record: SocialStateRecord) -> str:
    """Describe what ``social_state_fingerprint`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        record: ``record`` (SocialStateRecord); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    payload = "|".join(
        [
            ",".join(record.prior_continuity_classes),
            record.scene_pressure_state,
            str(record.active_thread_count),
            str(record.thread_pressure_summary_present),
            record.guidance_phase_key or "",
            record.responder_asymmetry_code,
            record.social_risk_band,
            ",".join(record.relationship_pressure_codes),
            ",".join(record.active_relationship_axis_ids),
            record.dominant_relationship_axis_id or "",
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
