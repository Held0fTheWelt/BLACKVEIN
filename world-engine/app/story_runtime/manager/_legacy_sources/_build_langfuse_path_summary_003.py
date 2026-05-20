SOURCE = r'''\
            if isinstance(scene_plan_record.get("expectation_variation_state"), dict)
            else {}
        ),
        "expectation_variation_target": (
            graph_state.get("expectation_variation_target")
            if isinstance(graph_state.get("expectation_variation_target"), dict)
            else scene_plan_record.get("expectation_variation_target")
            if isinstance(scene_plan_record.get("expectation_variation_target"), dict)
            else {}
        ),
        "expectation_variation_validation": (
            graph_state.get("expectation_variation_validation")
            if isinstance(graph_state.get("expectation_variation_validation"), dict)
            else {}
        ),
        "narrative_momentum_state": (
            graph_state.get("narrative_momentum_state")
            if isinstance(graph_state.get("narrative_momentum_state"), dict)
            else scene_plan_record.get("narrative_momentum_state")
            if isinstance(scene_plan_record.get("narrative_momentum_state"), dict)
            else {}
        ),
        "narrative_momentum_target": (
            graph_state.get("narrative_momentum_target")
            if isinstance(graph_state.get("narrative_momentum_target"), dict)
            else scene_plan_record.get("narrative_momentum_target")
            if isinstance(scene_plan_record.get("narrative_momentum_target"), dict)
            else {}
        ),
        "narrative_momentum_validation": (
            graph_state.get("narrative_momentum_validation")
            if isinstance(graph_state.get("narrative_momentum_validation"), dict)
            else {}
        ),
        "legacy_keyword_scene_candidates_used": bool(
            multi_pressure_resolution.get("legacy_keyword_scene_candidates_used")
        ),
        "intent_surface_contract_pass": 1 if _intent_surface_contract_pass else 0,
        "player_input_attribution_pass": 1 if _player_input_attribution_pass else 0,
        "semantic_move_alignment_pass": 1 if _semantic_move_alignment_pass else 0,
        "subtext_contract_pass": 1 if _subtext_contract_pass else 0,
        "npc_action_narration_boundary_pass": 1 if _npc_action_narration_boundary_pass else 0,
        "quality_class": governance.get("quality_class") or graph_state.get("quality_class"),
        "degradation_signals": list(governance.get("degradation_signals") or graph_state.get("degradation_signals") or []),
        "degradation_summary": governance.get("degradation_summary") or graph_state.get("degradation_summary"),
        "live_opening_failure_reason": gen_meta.get("live_opening_failure_reason") or generation.get("live_opening_failure_reason"),
        "graph_errors": graph_errors,
        "failure_markers": _str_list(graph_state.get("failure_markers")),
        "primary_responder_id": (
            graph_state.get("primary_responder_id")
            or graph_state.get("responder_id")
            or (event.get("actor_turn_summary") or {}).get("primary_responder_id")
        ),
        "response_present": bool(vitality.get("response_present"))
        or _final_visible_actor_response_in_event(event),
        "initiative_present": vitality.get("initiative_present"),
        "multi_actor_realized": vitality.get("multi_actor_realized"),
        "realized_actor_ids": list(vitality.get("realized_actor_ids") or []),
        "rendered_actor_ids": list(vitality.get("rendered_actor_ids") or []),
        "why_turn_felt_passive": (
            list(governance.get("why_turn_felt_passive"))
            if isinstance(governance.get("why_turn_felt_passive"), list)
            else list(passivity.get("why_turn_felt_passive") or [])
        ),
        "primary_passivity_factors": (
            list(governance.get("primary_passivity_factors"))
            if isinstance(governance.get("primary_passivity_factors"), list)
            else list(passivity.get("primary_passivity_factors") or [])
        ),
        "trace_origin": trace_origin,
        "execution_tier": execution_tier,
        "langfuse_environment": environment,
        "canonical_player_flow": canonical_player_flow,
        "test_case_id": test_case_id,
        "runtime_mode": runtime_mode,
    }
    if local_evidence_meta:
        summary.update(local_evidence_meta)
        summary["langfuse_environment"] = summary.get("environment")
    _quality = str(summary.get("quality_class") or "").strip().lower()
    if bool(summary.get("fallback_model_called")) or bool(summary.get("generation_fallback_used")):
        summary["runtime_quality"] = "fallback"
    elif _quality == "healthy":
        summary["runtime_quality"] = "healthy"
    elif _quality:
        summary["runtime_quality"] = "degraded"
    else:
        summary["runtime_quality"] = None
    opening_norm = graph_state.get("_opening_narration_normalization")
    if isinstance(opening_norm, dict):
        for key in (
            "opening_narration_normalized",
            "opening_narration_source",
            "opening_narration_beat_count",
            "narration_summary_input_kind",
        ):
            if key in opening_norm:
                summary[key] = opening_norm[key]
    ev_proj = graph_state.get("_actor_block_projection_evidence")
    if isinstance(ev_proj, dict):
        for key in (
            "actor_block_source",
            "actor_block_filtered_reason",
            "actor_line_count_before_projection",
            "action_line_count_before_projection",
            "actor_block_count_after_projection",
        ):
            if key in ev_proj:
                summary[key] = ev_proj[key]
    vis_contract = graph_state.get("_visible_narrative_contract")
    if isinstance(vis_contract, dict):
        for key in (
            "visible_language_detected",
            "mixed_language_detected",
            "visible_language_contract_pass",
            "selected_role_visible_in_opening",
            "player_identity_anchor_present",
            "visible_narrative_contract_version",
            "name_only_actor_block_removed",
            "label_only_line_removed",
            "duplicate_actor_label_removed",
            "placeholder_action_removed",
            "actor_line_action_tail_stripped",
            "near_duplicate_visible_block_removed",
        ):
            if key in vis_contract:
                summary[key] = vis_contract[key]
    transition_diag = graph_state.get("_opening_transition_diagnostics")
    if isinstance(transition_diag, dict):
        for key, val in transition_diag.items():
            summary[key] = val
    if session.module_id == GOD_OF_CARNAGE_MODULE_ID:
        actor_lane_context = StoryRuntimeManager._extract_actor_lane_context(session)
        knowledge_summary = build_knowledge_path_summary(
            graph_state=graph_state,
            event=event,
            actor_lane_context=actor_lane_context,
        )
        summary.update(knowledge_summary)
    _plc_gs = graph_state.get("player_local_context")
    summary["player_local_context"] = _plc_gs if isinstance(_plc_gs, dict) else None
    _lct_gs = graph_state.get("local_context_transition")
    summary["local_context_transition"] = _lct_gs if isinstance(_lct_gs, dict) else None
    _ncp_gs = graph_state.get("narrator_consequence_plan")
    summary["narrator_consequence_plan"] = _ncp_gs if isinstance(_ncp_gs, dict) else None
    _env_gs = graph_state.get("environment_state")
    summary["environment_state"] = _env_gs if isinstance(_env_gs, dict) else None
    _env_tr = graph_state.get("environment_transition")
    summary["environment_transition"] = _env_tr if isinstance(_env_tr, dict) else None
    summary["movement_return_intent"] = bool(interpreted_input.get("movement_return_intent"))
    if "speech_projection_allowed" in interpreted_input:
        summary["speech_projection_allowed"] = bool(interpreted_input.get("speech_projection_allowed"))
    _aff_gs = graph_state.get("affordance_resolution") if isinstance(graph_state.get("affordance_resolution"), dict) else {}
    summary["resolved_target_id"] = _aff_gs.get("resolved_target_id")
    summary["target_resolution_source"] = _aff_gs.get("target_resolution_source")
    summary["authoritative_action_surface"] = bool(
        gen_meta.get("authoritative_action_resolution") is True
        or str(gen_meta.get("adapter") or "").strip().lower() == "action_resolution_authoritative"
    )
    if (
        bool(interpreted_input.get("movement_return_intent"))
        and str(summary.get("affordance_status") or "").strip().lower() == "ambiguous"
        and str(summary.get("action_commit_policy") or "").strip().lower() == "needs_clarification"
    ):
        summary["turn_status"] = "needs_clarification"

    summary["p0_action_resolution_evidence"] = _build_p0_action_resolution_evidence(
        event=event,
        graph_state=graph_state,
        interpreted_input=interpreted_input,
        validation=validation,
        committed_result=committed,
    )
    summary["generation_mode"] = _infer_generation_mode(summary)
    tn = event.get("turn_number")
    summary["canonical_turn_id"] = _canonical_turn_id(session.session_id, int(tn or 0))
    return summary
'''
