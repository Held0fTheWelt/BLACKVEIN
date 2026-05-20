"""QA-facing projection of the canonical dramatic turn record.

Phase D: Converts the full operator canonical turn record into a bounded,
readable QA diagnostics view. Implements three-tier field classification:

Tier A (always visible): responder selection, validation, quality, vitality
Tier B (summarized/collapsed): continuity, social state, scene assessment
Tier C (hidden unless raw JSON enabled): raw nested blobs, internal debug details
"""

from __future__ import annotations

from typing import Any


def _summarize_responder_set(responders: list[Any] | None) -> dict[str, Any]:
    """Summarize responder set (Tier B: flatten for readability)."""
    if not isinstance(responders, list) or not responders:
        return {}

    summary = {
        "primary_responder_id": None,
        "secondary_responder_ids": [],
        "preferred_reaction_order": [],
    }

    for row in responders:
        if not isinstance(row, dict):
            continue
        actor_id = str(row.get("actor_id") or "").strip()
        if not actor_id:
            continue
        role = str(row.get("role") or "").strip().lower()
        if role == "primary_responder":
            summary["primary_responder_id"] = actor_id
        elif role == "secondary_reactor":
            if actor_id not in summary["secondary_responder_ids"]:
                summary["secondary_responder_ids"].append(actor_id)

    # Build preferred reaction order
    scored = []
    for row in responders:
        if not isinstance(row, dict):
            continue
        actor_id = str(row.get("actor_id") or "").strip()
        if not actor_id:
            continue
        try:
            seq = int(row.get("preferred_reaction_order", 999))
        except (TypeError, ValueError):
            seq = 999
        scored.append((seq, actor_id))

    scored.sort(key=lambda x: x[0])
    summary["preferred_reaction_order"] = [aid for _, aid in scored if aid]

    return summary


def _summarize_continuity_impacts(impacts: list[Any] | None) -> list[dict[str, str]]:
    """Summarize continuity impacts (Tier B: extract class + note)."""
    if not isinstance(impacts, list):
        return []
    return [
        {"class": str(item.get("class") or ""), "note": str(item.get("note") or "")}
        for item in impacts
        if isinstance(item, dict)
    ][:5]  # Limit to 5 items


def _summarize_character_profiles(records: list[Any] | None) -> list[dict[str, Any]]:
    """Summarize character mind records (Tier B: key fields only)."""
    if not isinstance(records, list):
        return []

    summaries = []
    for record in records[:6]:  # Limit to 6 characters
        if not isinstance(record, dict):
            continue
        summary = {
            "actor_id": str(record.get("runtime_actor_id") or record.get("character_key") or "").strip(),
            "formal_role": str(record.get("formal_role_label") or "").strip(),
            "tactical_posture": str(record.get("tactical_posture") or "").strip(),
            "pressure_response": str(record.get("pressure_response_bias") or "").strip(),
        }
        if summary["actor_id"]:
            summaries.append(summary)

    return summaries


def _summarize_scene_assessment(assessment: dict[str, Any] | None) -> dict[str, Any]:
    """Summarize scene assessment (Tier B: flatten key metrics)."""
    if not isinstance(assessment, dict):
        return {}

    return {
        "pressure_state": str(assessment.get("pressure_state") or "").strip(),
        "thread_pressure_state": str(assessment.get("thread_pressure_state") or "").strip(),
        "narrative_scope": str(assessment.get("narrative_scope") or "").strip(),
        "canonical_setting": str(assessment.get("canonical_setting") or "").strip(),
    }


def _summarize_social_state(social_state: dict[str, Any] | None) -> dict[str, Any]:
    """Summarize social state record (Tier B: key relationships only)."""
    if not isinstance(social_state, dict):
        return {}

    relationships = social_state.get("relationships", [])
    rel_summaries = []
    if isinstance(relationships, list):
        for rel in relationships[:6]:  # Limit to 6 relationships
            if isinstance(rel, dict):
                rel_summaries.append({
                    "actors": rel.get("actors"),
                    "relationship_type": rel.get("relationship_type"),
                    "tension_level": rel.get("tension_level"),
                })

    return {
        "total_relationships": len(relationships) if isinstance(relationships, list) else 0,
        "relationships_summary": rel_summaries,
        "pressure_state": str(social_state.get("pressure_state") or "").strip(),
    }


def build_qa_canonical_turn_projection(canonical_record: dict[str, Any]) -> dict[str, Any]:
    """Convert operator canonical turn record to QA-readable projection.

    Implements three-tier classification:
    - Tier A: Always visible (responder, validation, quality, vitality)
    - Tier B: Summarized/collapsed (continuity, social, assessment)
    - Tier C: Hidden/raw-JSON-only (large nested blobs, debug details)

    Args:
        canonical_record: Output from build_operator_canonical_turn_record()

    Returns:
        QA projection dict with structured tiers and raw JSON link
    """
    if not isinstance(canonical_record, dict):
        canonical_record = {}

    turn_meta = canonical_record.get("turn_metadata", {})
    if not isinstance(turn_meta, dict):
        turn_meta = {}

    # Tier A: Always visible
    tier_a = {
        "turn_metadata": {
            "session_id": turn_meta.get("session_id"),
            "trace_id": turn_meta.get("trace_id"),
            "turn_number": turn_meta.get("turn_number"),
            "turn_timestamp_iso": turn_meta.get("turn_timestamp_iso"),
            "current_scene_id": turn_meta.get("current_scene_id"),
        },
        "selected_scene_function": canonical_record.get("selected_scene_function"),
        "pacing_mode": canonical_record.get("pacing_mode"),
        "silence_mode": (
            (canonical_record.get("silence_brevity_decision") or {}).get("mode")
            if isinstance(canonical_record.get("silence_brevity_decision"), dict)
            else None
        ),
        "responder_selection": _summarize_responder_set(
            canonical_record.get("selected_responder_set")
        ),
        "validation_outcome": {
            "status": (canonical_record.get("validation_outcome") or {}).get("status"),
            "reason": (canonical_record.get("validation_outcome") or {}).get("reason"),
        },
        "quality_class": canonical_record.get("quality_class"),
        "degradation_signals": canonical_record.get("degradation_signals", []),
        "visibility_class_markers": canonical_record.get("visibility_class_markers", []),
        "vitality_telemetry": canonical_record.get("vitality_telemetry_v1"),
    }

    # Tier B: Summarized/collapsed
    tier_b = {
        "continuity_summary": _summarize_continuity_impacts(
            canonical_record.get("continuity_impacts")
        ),
        "scene_summary": _summarize_scene_assessment(
            canonical_record.get("scene_assessment")
        ),
        "social_state_summary": _summarize_social_state(
            canonical_record.get("social_state_record")
        ),
        "character_profiles_summary": _summarize_character_profiles(
            canonical_record.get("character_mind_records")
        ),
        "committed_result_summary": {
            "committed_effects": (
                (canonical_record.get("committed_result") or {}).get("committed_effects")
                if isinstance(canonical_record.get("committed_result"), dict)
                else None
            ),
            "commit_applied": (
                (canonical_record.get("committed_result") or {}).get("commit_applied")
                if isinstance(canonical_record.get("committed_result"), dict)
                else None
            ),
        },
    }

    return {
        "schema_version": "qa_canonical_turn_projection.v1",
        "tier_a_primary": tier_a,
        "tier_b_detailed": tier_b,
        "graph_execution_summary": canonical_record.get("graph_diagnostics_summary"),
        "raw_canonical_record_available": True,
        "note": "Tier A fields always visible. Tier B fields summarized. Full canonical record available via raw-json toggle.",
    }
