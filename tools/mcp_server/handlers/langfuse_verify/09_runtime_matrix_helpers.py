"""Langfuse verify source segment: runtime_matrix_helpers.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        "npc_takeover_absent",
        "npc_agency_plan_present",
        "npc_independent_planning_used",
        "npc_long_horizon_state_present",
        "npc_private_plan_resolution_present",
        "npc_private_plan_visibility_respected",
        "npc_intention_threads_carried_forward",
        "npc_required_initiatives_realized",
        "multi_npc_initiative_realized",
        "npc_carry_forward_closed",
        "npc_forbidden_actor_absent",
        "capability_selection_present",
        "selected_capabilities_realized",
        "visible_block_origin_present",
        "narrative_aspect_policy_present",
        "narrative_aspect_selected",
        "narrative_aspect_visible_when_required",
        "narrative_aspect_contract_pass",
        "theme_tracking_policy_present",
        "theme_tracking_selected",
        "theme_semantic_classification_present",
        "theme_weak_alignment_absent",
        "theme_tracking_contract_pass",
        "voice_consistency_policy_present",
        "voice_semantic_classification_present",
        "voice_cross_actor_confusion_absent",
        "voice_forbidden_markers_absent",
        "voice_consistency_contract_pass",
        "tonal_consistency_policy_present",
        "tonal_consistency_target_selected",
        "tonal_consistency_independent_classification_present",
        "tonal_consistency_classification_present",
        "tonal_consistency_marker_hits_absent",
        "tonal_consistency_contract_pass",
        "hierarchical_memory_present",
        "memory_policy_applied",
        "memory_write_from_committed_turn",
        "memory_context_bounded",
        "hierarchical_memory_contract_pass",
        ADR0041_LANGFUSE_SCORE_PARENT_PRESENT,
        ADR0041_LANGFUSE_SCORE_PLAN_ENFORCED,
        ADR0041_LANGFUSE_SCORE_READINESS_AGG,
        ADR0041_LANGFUSE_SCORE_READINESS_PREVIEW,
    ):
        ev[gate] = det_scores.get(gate)

    # --- ADR-0041 runtime intelligence (dedicated Langfuse observation + scores) ---
    adr_obs = _find_observation_by_name(obs_list, WOS_ADR0041_RUNTIME_INTELLIGENCE_OBSERVATION_NAME)
    ev["adr0041_runtime_intelligence_observation_present"] = bool(adr_obs)
    if adr_obs:
        meta = _coerce_dict_or_json(adr_obs.get("metadata"))
        inp = _coerce_dict_or_json(adr_obs.get("input"))
        out_b = _coerce_dict_or_json(adr_obs.get("output"))
        summary = _coerce_dict_or_json(inp.get("projection_summary"))
        merged: dict[str, Any] = {**summary, **meta}
        oid = str(adr_obs.get("id") or "").strip()
        if oid:
            ev["adr0041_langfuse_observation_id"] = oid
        ev["adr0041_schema_version"] = merged.get("schema_version")
        ev["adr0041_story_session_id"] = merged.get("story_session_id")
        ev["adr0041_validator_dispatch_mode"] = merged.get("validator_dispatch_mode")
        ev["adr0041_validator_dispatch_feature_flag_enabled"] = merged.get(
            "validator_dispatch_feature_flag_enabled"
        )
        ev["adr0041_readiness_aggregation_present"] = merged.get("readiness_aggregation_present")
        ev["adr0041_readiness_aggregation_aggregated"] = merged.get("readiness_aggregation_aggregated")
        ev["adr0041_readiness_co_authority_preview_present"] = merged.get(
            "readiness_co_authority_preview_present"
        )
        ev["adr0041_readiness_co_authority_enforcement_present"] = merged.get(
            "readiness_co_authority_enforcement_present"
        )
'''
