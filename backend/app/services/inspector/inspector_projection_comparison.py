"""Turn-to-turn comparison rows for inspector comparison projection."""

from __future__ import annotations

from typing import Any

from app.services.inspector.inspector_projection_turn_view import dramatic_review, visible_narration_fingerprint


def session_has_candidate_matrix(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        dr = dramatic_review(row)
        c = dr.get("multi_pressure_candidates")
        if isinstance(c, list) and len(c) > 0:
            return True
    return False


def build_turn_comparisons(
    rows: list[dict[str, Any]],
    turns: list[dict[str, Any]],
    *,
    has_candidates: bool,
) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    for idx in range(1, len(rows)):
        prev_row, current_row = rows[idx - 1], rows[idx]
        prev, current = turns[idx - 1], turns[idx]
        dr_to = dramatic_review(current_row)
        candidates_to = dr_to.get("multi_pressure_candidates") if has_candidates else None
        if has_candidates and not isinstance(candidates_to, list):
            candidates_to = None

        fp_prev = visible_narration_fingerprint(prev_row)
        fp_curr = visible_narration_fingerprint(current_row)
        surface_comparison: dict[str, Any] | str
        if fp_prev is None or fp_curr is None:
            surface_comparison = "unavailable_missing_visible_output_bundle"
        else:
            surface_comparison = {
                "visible_output_fingerprint_from": fp_prev,
                "visible_output_fingerprint_to": fp_curr,
                "phrasing_identical": fp_prev == fp_curr,
            }

        comparisons.append(
            {
                "from_turn_number": prev["turn_number"],
                "to_turn_number": current["turn_number"],
                "from_trace_id": prev["trace_id"],
                "to_trace_id": current["trace_id"],
                "gate_result_from": prev["gate_result"],
                "gate_result_to": current["gate_result"],
                "validation_status_from": prev["validation_status"],
                "validation_status_to": current["validation_status"],
                "fallback_path_taken_from": prev["fallback_path_taken"],
                "fallback_path_taken_to": current["fallback_path_taken"],
                "selected_scene_function_from": prev["selected_scene_function"],
                "selected_scene_function_to": current["selected_scene_function"],
                "empty_fluency_risk_from": prev["empty_fluency_risk"],
                "empty_fluency_risk_to": current["empty_fluency_risk"],
                "character_plausibility_posture_from": prev["character_plausibility_posture"],
                "character_plausibility_posture_to": current["character_plausibility_posture"],
                "continuity_support_posture_from": prev["continuity_support_posture"],
                "continuity_support_posture_to": current["continuity_support_posture"],
                "structural_fallback_used_from": prev["structural_fallback_used"],
                "structural_fallback_used_to": current["structural_fallback_used"],
                "semantic_move_type_from": prev["semantic_move_type"],
                "semantic_move_type_to": current["semantic_move_type"],
                "scene_risk_band_from": prev["scene_risk_band"],
                "scene_risk_band_to": current["scene_risk_band"],
                "multi_pressure_candidates_to": candidates_to,
                "visible_output_surface_comparison": surface_comparison,
            }
        )
    return comparisons


def comparison_dimension_lists(*, has_candidates: bool) -> tuple[list[str], list[str]]:
    unsupported_dimensions: list[str] = [
        "cross_session_comparison_no_shared_projection_source",
        "cross_run_version_delta_not_emitted",
    ]
    if not has_candidates:
        unsupported_dimensions.append("candidate_matrix_not_emitted_in_diagnostics")

    supported_dimensions = ["turn_to_turn_within_session", "planner_gate_posture_delta"]
    if has_candidates:
        supported_dimensions.append("candidate_matrix_when_present")
    return supported_dimensions, unsupported_dimensions
