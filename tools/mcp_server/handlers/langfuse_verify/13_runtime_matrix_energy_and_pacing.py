"""Langfuse verify source segment: runtime_matrix_energy_and_pacing.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
    "visible_origin_present",
    "narrative_aspect_policy_present",
    "narrative_aspect_selected",
    "selected_narrative_aspects",
    "realized_narrative_aspects",
    "narrative_aspect_visible_when_required",
    "narrative_aspect_contract_pass",
    "theme_tracking_policy_present",
    "theme_tracking_selected",
    "selected_theme_aspects",
    "realized_theme_aspects",
    "theme_semantic_classification_present",
    "theme_semantic_classification_count",
    "theme_weak_alignment_count",
    "theme_tracking_contract_pass",
    "voice_consistency_policy_present",
    "voice_semantic_classification_enabled",
    "voice_semantic_classification_present",
    "voice_semantic_classification_count",
    "voice_spoken_line_count",
    "voice_cross_actor_confusion_absent",
    "voice_cross_actor_confusion_count",
    "voice_forbidden_markers_absent",
    "voice_consistency_contract_pass",
    "tonal_consistency_policy_present",
    "tonal_consistency_target_selected",
    "tonal_consistency_profile_id",
    "tonal_consistency_required_dimensions",
    "tonal_consistency_realized_dimensions",
    "tonal_consistency_classification_source",
    "tonal_consistency_independent_classification_present",
    "tonal_consistency_classification_present",
    "tonal_consistency_marker_hits_absent",
    "tonal_consistency_contract_pass",
    "tonal_consistency_failure_codes",
    "hierarchical_memory_present",
    "memory_policy_applied",
    "selected_memory_tiers",
    "memory_written_item_count",
    "memory_context_item_count",
    "memory_write_from_committed_turn",
    "memory_context_bounded",
    "hierarchical_memory_contract_pass",
    "turn_status",
    "http_status",
    "main_failure",
    "recommended_repair",
)


def _extract_path_summary_from_trace(raw_trace: dict[str, Any]) -> dict[str, Any]:
    trace_output = _coerce_dict_or_json(raw_trace.get("output"))
    nested = _coerce_dict_or_json(trace_output.get("path_summary")) if trace_output else {}
    if nested:
        return nested
    if trace_output.get("contract") == "story_runtime_path_observability.v1":
        return trace_output
    ps_obs = _find_observation_by_name(_get_observations(raw_trace), "story.graph.path_summary")
    if ps_obs:
        for block_key in ("output", "input", "metadata"):
            block = _coerce_dict_or_json(ps_obs.get(block_key))
            if block.get("contract") == "story_runtime_path_observability.v1" or block.get("turn_aspect_ledger"):
                return block
    return {}


def _extract_runtime_aspect_ledger_from_trace(raw_trace: dict[str, Any]) -> dict[str, Any]:
    path_summary = _extract_path_summary_from_trace(raw_trace)
    ledger = path_summary.get("turn_aspect_ledger") if isinstance(path_summary, dict) else None
    if isinstance(ledger, dict) and isinstance(ledger.get("turn_aspect_ledger"), dict):
        return ledger
    aspect_obs = _find_observation_by_name(_get_observations(raw_trace), "story.turn.aspect_summary")
'''
