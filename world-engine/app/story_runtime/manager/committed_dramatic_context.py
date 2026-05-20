"""Committed dramatic-context projection.

Extracts dramatic context from committed turn state for subsequent planner, validator, and visible-projection consumers.
"""
from __future__ import annotations

from ._deps import *

def _build_committed_dramatic_context_summary(
    *,
    graph_state: dict[str, Any],
    narrative_commit_payload: dict[str, Any],
    thread_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Merge packaged runtime context with committed planner truth."""
    base = (
        graph_state.get("dramatic_context_summary")
        if isinstance(graph_state.get("dramatic_context_summary"), dict)
        else {}
    )
    planner = (
        narrative_commit_payload.get("planner_truth")
        if isinstance(narrative_commit_payload.get("planner_truth"), dict)
        else {}
    )
    scene_assessment = (
        planner.get("scene_assessment_core")
        if isinstance(planner.get("scene_assessment_core"), dict)
        else {}
    )
    social_summary = (
        planner.get("social_state_summary")
        if isinstance(planner.get("social_state_summary"), dict)
        else {}
    )
    beat = (
        narrative_commit_payload.get("beat_progression")
        if isinstance(narrative_commit_payload.get("beat_progression"), dict)
        else {}
    )
    retrieval = graph_state.get("retrieval") if isinstance(graph_state.get("retrieval"), dict) else {}
    continuity_query = (
        retrieval.get("continuity_query_signal")
        if isinstance(retrieval.get("continuity_query_signal"), dict)
        else {}
    )
    base_responder = base.get("responder") if isinstance(base.get("responder"), dict) else {}
    base_pacing = base.get("pacing") if isinstance(base.get("pacing"), dict) else {}
    base_scene_energy = (
        base.get("scene_energy")
        if isinstance(base.get("scene_energy"), dict)
        else {}
    )
    base_pacing_rhythm = (
        base.get("pacing_rhythm")
        if isinstance(base.get("pacing_rhythm"), dict)
        else {}
    )
    base_temporal_control = (
        base.get("temporal_control")
        if isinstance(base.get("temporal_control"), dict)
        else {}
    )
    base_genre_awareness = (
        base.get("genre_awareness")
        if isinstance(base.get("genre_awareness"), dict)
        else {}
    )
    base_scene = (
        base.get("scene_assessment")
        if isinstance(base.get("scene_assessment"), dict)
        else {}
    )
    committed_context = dict(base)
    committed_context.update(
        {
            "contract": "bounded_dramatic_context.v1",
            "source": "narrative_commit.planner_truth+runtime_turn_state",
            "committed_scene_id": narrative_commit_payload.get("committed_scene_id"),
            "commit_reason_code": narrative_commit_payload.get("commit_reason_code"),
            "selected_scene_function": planner.get("selected_scene_function")
            or base.get("selected_scene_function"),
            "function_type": planner.get("function_type") or base.get("function_type"),
            "responder": {
                "responder_id": planner.get("responder_id")
                or planner.get("primary_responder_id")
                or base_responder.get("responder_id"),
                "responder_scope": _compact_context_list(
                    planner.get("responder_scope") or base_responder.get("responder_scope")
                ),
                "secondary_responder_ids": _compact_context_list(
                    planner.get("secondary_responder_ids")
                ),
            },
            "pacing": {
                "pacing_mode": planner.get("pacing_mode") or base_pacing.get("pacing_mode"),
                "silence_mode": planner.get("silence_mode") or base_pacing.get("silence_mode"),
            },
            "scene_energy": {
                "target": planner.get("scene_energy_target")
                if isinstance(planner.get("scene_energy_target"), dict)
                else base_scene_energy.get("target") or {},
                "transition": planner.get("scene_energy_transition")
                if isinstance(planner.get("scene_energy_transition"), dict)
                else base_scene_energy.get("transition") or {},
                "validation_status": (
                    planner.get("scene_energy_validation", {}).get("status")
                    if isinstance(planner.get("scene_energy_validation"), dict)
                    else base_scene_energy.get("validation_status")
                ),
            },
            "pacing_rhythm": {
                "state": planner.get("pacing_rhythm_state")
                if isinstance(planner.get("pacing_rhythm_state"), dict)
                else base_pacing_rhythm.get("state") or {},
                "target": planner.get("pacing_rhythm_target")
                if isinstance(planner.get("pacing_rhythm_target"), dict)
                else base_pacing_rhythm.get("target") or {},
                "validation_status": (
                    planner.get("pacing_rhythm_validation", {}).get("status")
                    if isinstance(planner.get("pacing_rhythm_validation"), dict)
                    else base_pacing_rhythm.get("validation_status")
                ),
            },
            "temporal_control": {
                "state": planner.get("temporal_control_state")
                if isinstance(planner.get("temporal_control_state"), dict)
                else base_temporal_control.get("state") or {},
                "target": planner.get("temporal_control_target")
                if isinstance(planner.get("temporal_control_target"), dict)
                else base_temporal_control.get("target") or {},
                "validation_status": (
                    planner.get("temporal_control_validation", {}).get("status")
                    if isinstance(planner.get("temporal_control_validation"), dict)
                    else base_temporal_control.get("validation_status")
                ),
            },
            "genre_awareness": {
                "state": planner.get("genre_awareness_state")
                if isinstance(planner.get("genre_awareness_state"), dict)
                else base_genre_awareness.get("state") or {},
                "target": planner.get("genre_awareness_target")
                if isinstance(planner.get("genre_awareness_target"), dict)
                else base_genre_awareness.get("target") or {},
                "validation_status": (
                    planner.get("genre_awareness_validation", {}).get("status")
                    if isinstance(planner.get("genre_awareness_validation"), dict)
                    else base_genre_awareness.get("validation_status")
                ),
            },
            "social_pressure": {
                "state": planner.get("social_pressure_state")
                if isinstance(planner.get("social_pressure_state"), dict)
                else {},
                "target": planner.get("social_pressure_target")
                if isinstance(planner.get("social_pressure_target"), dict)
                else {},
                "validation_status": (
                    planner.get("social_pressure_validation", {}).get("status")
                    if isinstance(planner.get("social_pressure_validation"), dict)
                    else None
                ),
            },
            "expectation_variation": {
                "state": planner.get("expectation_variation_state")
                if isinstance(planner.get("expectation_variation_state"), dict)
                else {},
                "target": planner.get("expectation_variation_target")
                if isinstance(planner.get("expectation_variation_target"), dict)
                else {},
                "validation_status": (
                    planner.get("expectation_variation_validation", {}).get("status")
                    if isinstance(planner.get("expectation_variation_validation"), dict)
                    else None
                ),
            },
            "narrative_momentum": {
                "state": planner.get("narrative_momentum_state")
                if isinstance(planner.get("narrative_momentum_state"), dict)
                else {},
                "target": planner.get("narrative_momentum_target")
                if isinstance(planner.get("narrative_momentum_target"), dict)
                else {},
                "validation_status": (
                    planner.get("narrative_momentum_validation", {}).get("status")
                    if isinstance(planner.get("narrative_momentum_validation"), dict)
                    else None
                ),
            },
            "scene_assessment": {
                "pressure_state": scene_assessment.get("pressure_state")
                or base_scene.get("pressure_state"),
                "thread_pressure_state": scene_assessment.get("thread_pressure_state")
                or base_scene.get("thread_pressure_state"),
                "assessment_summary": _compact_context_str(
                    scene_assessment.get("assessment_summary") or base_scene.get("assessment_summary")
                ),
            },
            "social_state": {
                "fingerprint": social_summary.get("fingerprint"),
                "social_risk_band": social_summary.get("social_risk_band"),
                "responder_asymmetry_code": social_summary.get("responder_asymmetry_code"),
                "social_continuity_status": social_summary.get("social_continuity_status"),
                "prior_social_state_fingerprint": social_summary.get("prior_social_state_fingerprint"),
            },
            "dramatic_outcome": {
                "social_outcome": planner.get("social_outcome"),
                "dramatic_direction": planner.get("dramatic_direction"),
                "continuity_classes": _compact_context_list(
                    [
                        item.get("class") or item.get("continuity_class")
                        for item in (planner.get("continuity_impacts") or [])
                        if isinstance(item, dict)
                    ]
                ),
                "spoken_line_count": planner.get("spoken_line_count"),
                "action_line_count": planner.get("action_line_count"),
                "initiative_summary": planner.get("initiative_summary")
                if isinstance(planner.get("initiative_summary"), dict)
                else {},
                "last_actor_outcome_summary": planner.get("last_actor_outcome_summary"),
            },
            "beat": {
                "beat_id": beat.get("beat_id"),
                "beat_slot": beat.get("beat_slot"),
                "advanced": beat.get("advanced"),
                "advancement_reason": beat.get("advancement_reason"),
                "pressure_state": beat.get("pressure_state"),
            },
            "narrative_threads": {
                "thread_count": thread_metrics.get("thread_count", 0),
                "dominant_thread_kind": thread_metrics.get("dominant_thread_kind"),
                "thread_pressure_level": thread_metrics.get("thread_pressure_level", 0),
            },
            "retrieval_context": {
                "continuity_query_attached": bool(continuity_query.get("attached")),
                "continuity_query_sources": _compact_context_list(continuity_query.get("sources")),
                "retrieval_status": retrieval.get("status"),
                "retrieval_route": retrieval.get("retrieval_route"),
            },
        }
    )
    return committed_context

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
