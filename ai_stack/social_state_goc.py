"""Bounded social-state projection from continuity, threads, and scene assessment (derived only)."""

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
) -> SocialStateRecord:
    prior_classes = prior_continuity_classes(prior_continuity_impacts)
    threads = active_narrative_threads if isinstance(active_narrative_threads, list) else []
    n = sum(1 for t in threads if isinstance(t, dict))
    tsum = (thread_pressure_summary or "").strip()
    sa = scene_assessment if isinstance(scene_assessment, dict) else {}
    pressure = str(sa.get("pressure_state") or "moderate_tension")
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
    if pressure == "high_blame" or "blame_pressure" in prior_classes:
        risk = "high"
    elif not prior_classes and n == 0:
        risk = "low"

    return SocialStateRecord(
        prior_continuity_classes=prior_classes,
        scene_pressure_state=pressure,
        active_thread_count=n,
        thread_pressure_summary_present=bool(tsum),
        guidance_phase_key=phase_s,
        responder_asymmetry_code=asym,
        social_risk_band=risk,
    )


def social_state_fingerprint(record: SocialStateRecord) -> str:
    payload = "|".join(
        [
            ",".join(record.prior_continuity_classes),
            record.scene_pressure_state,
            str(record.active_thread_count),
            str(record.thread_pressure_summary_present),
            record.guidance_phase_key or "",
            record.responder_asymmetry_code,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
