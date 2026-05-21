"""Langfuse verify source segment: handler_opening_quality_context.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        ),
        "voice_cross_actor_confusion_count": voice_cross_actor_count,
        "voice_forbidden_markers_absent": (
            voice_forbidden_marker_count == 0
            if voice_actual
            else det_scores.get("voice_forbidden_markers_absent")
        ),
        "voice_consistency_contract_pass": det_scores.get("voice_consistency_contract_pass"),
        "tonal_consistency_policy_present": (
            tonal_expected.get("policy_present")
            if "policy_present" in tonal_expected
            else det_scores.get("tonal_consistency_policy_present")
        ),
        "tonal_consistency_target_selected": (
            bool(
                tonal_target.get("profile_id")
                or tonal_target.get("target_dimension_ids")
                or tonal_selected.get("required_dimension_ids")
            )
            if tonal_selected
            else det_scores.get("tonal_consistency_target_selected")
        ),
        "tonal_consistency_profile_id": tonal_target.get("profile_id"),
        "tonal_consistency_required_dimensions": tonal_target.get("required_dimension_ids")
        or tonal_selected.get("required_dimension_ids")
        or [],
        "tonal_consistency_realized_dimensions": tonal_actual.get("realized_dimension_ids")
        or [],
        "tonal_consistency_classification_source": tonal_actual.get("classification_source"),
        "tonal_consistency_independent_classification_present": (
            bool(tonal_actual.get("structured_classification_present"))
            and tonal_actual.get("independent_classifier") is not False
            if "structured_classification_present" in tonal_actual
            else det_scores.get("tonal_consistency_independent_classification_present")
        ),
        "tonal_consistency_classification_present": (
            bool(tonal_actual.get("structured_classification_present"))
            and tonal_actual.get("independent_classifier") is not False
            if "structured_classification_present" in tonal_actual
            else det_scores.get("tonal_consistency_classification_present")
        ),
        "tonal_consistency_marker_hits_absent": (
            int(tonal_actual.get("marker_hit_count") or 0) == 0
            if tonal_actual
            else det_scores.get("tonal_consistency_marker_hits_absent")
        ),
        "tonal_consistency_contract_pass": (
            tonal_actual.get("contract_pass")
            if "contract_pass" in tonal_actual
            else det_scores.get("tonal_consistency_contract_pass")
        ),
        "tonal_consistency_failure_codes": tonal_failure_codes,
        "hierarchical_memory_present": memory_actual.get("memory_present") if "memory_present" in memory_actual else det_scores.get("hierarchical_memory_present"),
        "memory_policy_applied": det_scores.get("memory_policy_applied"),
        "selected_memory_tiers": memory_selected.get("selected_tiers") or [],
        "memory_written_item_count": memory_actual.get("written_item_count"),
        "memory_context_item_count": memory_actual.get("context_item_count"),
        "memory_write_from_committed_turn": det_scores.get("memory_write_from_committed_turn"),
        "memory_context_bounded": memory_actual.get("context_bounded") if "context_bounded" in memory_actual else det_scores.get("memory_context_bounded"),
        "hierarchical_memory_contract_pass": det_scores.get("hierarchical_memory_contract_pass"),
        "turn_status": path_summary.get("turn_status"),
        "http_status": path_summary.get("http_status"),
        "main_failure": main_failure,
        "recommended_repair": _runtime_aspect_recommended_repair(main_failure),
    }
    return {col: row.get(col) for col in _RUNTIME_ASPECT_MATRIX_COLUMNS}


def _runtime_aspect_trace_matches_filters(raw_trace: dict[str, Any], arguments: dict[str, Any]) -> bool:
    path_summary = _extract_path_summary_from_trace(raw_trace)
    meta = _extract_metadata(raw_trace)
    trace_origin = arguments.get("trace_origin")
'''
