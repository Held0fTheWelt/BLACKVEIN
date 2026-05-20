"""Langfuse evidence observation source chunk 002.

Contributes ordered source lines for legacy emission of evidence observations into Langfuse. This chunk is intentionally small and ordered by the legacy manifest.
"""
SOURCE = r'''\
        # short-path — so dashboards observe degraded/fallback behaviour rather than gaps.
        _action_diag = _compute_action_consequence_diagnostics(path_summary)
        for _name in (
            "local_context_transition_present",
            "narrator_consequence_present",
            "new_location_established",
            "perception_result_present",
            "action_consequence_contract_pass",
            "npc_consequence_takeover_absent",
        ):
            _value = _action_diag.get(_name)
            if isinstance(_value, (int, float)):
                deterministic_scores[_name] = float(_value)
    # live_opening_contract_pass is only meaningful on the opening turn (turn 0).
    # Writing it on subsequent turns would produce false negatives that pollute
    # the trace score history and make passing openings appear to have failed.
    _live_subgates: dict[str, bool] = {}
    _live_failure_reasons: list[str] = []
    if _turn_number == 0:
        final_adapter = str(path_summary.get("final_adapter") or path_summary.get("adapter") or "").strip().lower()
        trace_origin = str(path_summary.get("trace_origin") or "").strip().lower()
        execution_tier = str(path_summary.get("execution_tier") or "").strip().lower()
        canonical_player_flow = bool(path_summary.get("canonical_player_flow"))
        _live_subgates = {
            "turn_0": True,
            "trace_origin_live_ui": trace_origin == "live_ui",
            "execution_tier_live": execution_tier == "live",
            "canonical_player_flow": canonical_player_flow,
            "opening_shape_pass": deterministic_scores["opening_shape_contract_pass"] == 1.0,
            (
                "narrator_path_transition_pass"
                if narrator_path_selected
                else "opening_transition_pass"
            ): (
                bool(_transition_diag_for_scores.get("narrator_path_transition_contract_pass"))
                if narrator_path_selected
                else deterministic_scores.get("opening_transition_contract_pass", 1.0) == 1.0
            ),
            "live_runtime_pass": deterministic_scores["live_runtime_contract_pass"] == 1.0,
            "not_ldss_fallback": final_adapter not in {"ldss_fallback"},
            "fallback_absent": deterministic_scores["fallback_absent"] == 1.0,
            "non_mock_generation": deterministic_scores["non_mock_generation_pass"] == 1.0,
            "quality_class_ok": qc not in {"degraded", "failed"},
        }
        _live_failure_reasons = [k for k, v in _live_subgates.items() if not v]
        live_opening_ok = all(_live_subgates.values())
        deterministic_scores["live_opening_contract_pass"] = 1.0 if live_opening_ok else 0.0
    canonical_signals = _build_canonical_degradation_signals(path_summary)
    degradation_chain = _build_degradation_chain(path_summary)
    degradation_prose_summary = _build_degradation_prose_summary(path_summary)
    live_opening_failure_reason = path_summary.get("live_opening_failure_reason")
    score_metadata_base = {
        "session_id": path_summary.get("session_id"),
        "turn_number": path_summary.get("turn_number"),
        "canonical_turn_id": path_summary.get("canonical_turn_id"),
        "selected_player_role": path_summary.get("selected_player_role"),
        "human_actor_id": path_summary.get("human_actor_id"),
        "quality_class": path_summary.get("quality_class"),
        "degradation_signals": canonical_signals,
        "degradation_chain": degradation_chain,
        "degradation_summary": degradation_prose_summary,
        "player_input_kind": path_summary.get("player_input_kind"),
        "player_input_kind_family": path_summary.get("player_input_kind_family")
        or player_input_kind_family(path_summary.get("player_input_kind")),
        "intent_contract_version": path_summary.get("intent_contract_version")
        or INTENT_CONTRACT_VERSION,
        "player_action_committed": path_summary.get("player_action_committed"),
        "player_speech_committed": path_summary.get("player_speech_committed"),
        "narrator_response_expected": path_summary.get("narrator_response_expected"),
        "npc_response_expected": path_summary.get("npc_response_expected"),
        "p0_action_resolution_evidence": path_summary.get("p0_action_resolution_evidence"),
        "semantic_move_kind": path_summary.get("semantic_move_kind"),
        "subtext_surface_mode": path_summary.get("subtext_surface_mode"),
        "subtext_hidden_intent_hypothesis": path_summary.get(
            "subtext_hidden_intent_hypothesis"
        ),
        "subtext_function": path_summary.get("subtext_function"),
        "subtext_sincerity_band": path_summary.get("subtext_sincerity_band"),
        "subtext_policy_source": path_summary.get("subtext_policy_source"),
        "subtext_policy_rule_id": path_summary.get("subtext_policy_rule_id"),
        "subtext_evidence_codes": path_summary.get("subtext_evidence_codes"),
        "scene_director_selection_source": path_summary.get("scene_director_selection_source"),
        "planner_rationale_codes": path_summary.get("planner_rationale_codes"),
        "keyword_scene_candidates_used": path_summary.get(
            "keyword_scene_candidates_used"
        ),
        "npc_narrated_player_action_violation": path_summary.get(
            "npc_narrated_player_action_violation"
        ),
        "intent_surface_contract_pass": deterministic_scores.get("intent_surface_contract_pass"),
        "player_input_attribution_pass": deterministic_scores.get("player_input_attribution_pass"),
        "semantic_move_alignment_pass": deterministic_scores.get("semantic_move_alignment_pass"),
        "subtext_contract_pass": deterministic_scores.get("subtext_contract_pass"),
        "npc_action_narration_boundary_pass": deterministic_scores.get(
            "npc_action_narration_boundary_pass"
        ),
        "live_opening_failure_reason": live_opening_failure_reason,
        "live_opening_subgates": _live_subgates,
        "live_opening_failure_reasons": _live_failure_reasons,
        # OPEN-SHAPE-EVIDENCE-01: opening_shape_contract_pass subgate decomposition
        # + truncated scene_block excerpts. Surfaced on every score row to mirror
        # the live_opening_* pattern; only populated on turn 0 (empty otherwise).
        "opening_shape_subgates": _opening_shape_subgates,
        "opening_shape_failure_reasons": _opening_shape_failure_reasons,
        "scene_block_summary": _scene_block_summary,
        "first_actor_block_index": first_actor_block_index_val,
        "narrator_block_count": narrator_block_count_val,
        "structured_narration_summary_kind": structured_narration_summary_kind,
        "opening_event_coverage_pass": path_summary.get("opening_event_coverage_pass"),
        "opening_missing_event_ids": path_summary.get("opening_missing_event_ids"),
        "opening_missing_must_establish": path_summary.get("opening_missing_must_establish"),
        "opening_first_playable_scene_phase_expected": path_summary.get(
            "opening_first_playable_scene_phase_expected"
        ),
        "opening_first_playable_scene_phase_actual": path_summary.get(
            "opening_first_playable_scene_phase_actual"
        ),
        "hard_forbidden_absent": path_summary.get("hard_forbidden_absent"),
        "opening_summary_only_absent": path_summary.get("opening_summary_only_absent"),
        "hard_forbidden_detection": path_summary.get("hard_forbidden_detection"),
        # ADR-0033 §13.10 primary-vs-final clarity (metadata only; no gate semantics).
        "primary_attempt_adapter": path_summary.get("primary_attempt_adapter"),
        "primary_attempt_model": path_summary.get("primary_attempt_model"),
        "primary_attempt_provider": path_summary.get("primary_attempt_provider"),
        "primary_attempt_invocation_mode": path_summary.get("primary_attempt_invocation_mode"),
        "final_adapter": path_summary.get("final_adapter"),
        "final_adapter_invocation_mode": path_summary.get("final_adapter_invocation_mode"),
        "fallback_reason": path_summary.get("fallback_reason"),
        "ldss_fallback_after_live_opening_failure": path_summary.get(
            "ldss_fallback_after_live_opening_failure"
        ),
        "trace_origin": path_summary.get("trace_origin"),
        "execution_tier": path_summary.get("execution_tier"),
        "canonical_player_flow": path_summary.get("canonical_player_flow"),
        "test_case_id": path_summary.get("test_case_id"),
        "runtime_mode": path_summary.get("runtime_mode"),
        "generation_mode": path_summary.get("generation_mode"),
        # PRIMARY-PARSER-EVIDENCE-01: primary attempt diagnosis (score context only; no gate semantics).
        "primary_attempt_api_success": path_summary.get("primary_attempt_api_success"),
        "primary_attempt_parser_error_present": path_summary.get("primary_attempt_parser_error_present"),
        "self_correction_attempted": path_summary.get("self_correction_attempted"),
        "self_correction_attempt_count": path_summary.get("self_correction_attempt_count"),
        "self_correction_success": path_summary.get("self_correction_success"),
        "self_correction_model": path_summary.get("self_correction_model"),
        "self_correction_trigger_source": path_summary.get("self_correction_trigger_source"),
        "runtime_aspect_failure_before_retry": path_summary.get(
            "runtime_aspect_failure_before_retry"
        ),
        "capability_failure_before_retry": path_summary.get("capability_failure_before_retry"),
        "self_correction_resolved_failure": path_summary.get("self_correction_resolved_failure"),
        # OPEN-ACTOR-BLOCK-PROJECTION-01: structured lane → scene_blocks audit fields.
        "actor_block_source": path_summary.get("actor_block_source"),
        "actor_block_filtered_reason": path_summary.get("actor_block_filtered_reason"),
        "actor_line_count_before_projection": path_summary.get("actor_line_count_before_projection"),
        "action_line_count_before_projection": path_summary.get("action_line_count_before_projection"),
        "actor_block_count_after_projection": path_summary.get("actor_block_count_after_projection"),
        # VISIBLE-NARRATIVE-CONTRACT-01 (metadata only; not part of deterministic_scores gates).
        "visible_language_detected": path_summary.get("visible_language_detected"),
        "mixed_language_detected": path_summary.get("mixed_language_detected"),
        "visible_language_contract_pass": path_summary.get("visible_language_contract_pass"),
        "selected_role_visible_in_opening": path_summary.get("selected_role_visible_in_opening"),
        "player_identity_anchor_present": path_summary.get("player_identity_anchor_present"),
        "visible_narrative_contract_version": path_summary.get("visible_narrative_contract_version"),
        "name_only_actor_block_removed": path_summary.get("name_only_actor_block_removed"),
        "label_only_line_removed": path_summary.get("label_only_line_removed"),
        "duplicate_actor_label_removed": path_summary.get("duplicate_actor_label_removed"),
        "placeholder_action_removed": path_summary.get("placeholder_action_removed"),
        "actor_line_action_tail_stripped": path_summary.get("actor_line_action_tail_stripped"),
        "near_duplicate_visible_block_removed": path_summary.get("near_duplicate_visible_block_removed"),
        "player_role_display_name": path_summary.get("player_role_display_name"),
        "session_output_language": path_summary.get("session_output_language"),
        **_transition_diag_for_scores,
    }
    if narrator_path_selected and _turn_number == 0:
        narrator_path_gate_scores = {
            "non_mock_generation_pass",
            "visible_output_present",
            "actor_lane_safety_pass",
            "fallback_absent",
            "usage_present",
            "rag_context_attached",
            "opening_shape_contract_pass",
            "opening_contract_pass",
            "opening_role_anchor_pass",
            "hard_forbidden_absent",
            "opening_summary_only_absent",
            "opening_event_coverage_pass",
            "opening_player_speech_absent",
            "opening_npc_exposition_absent",
            "npc_exposition_absent",
            "player_agency_violation_absent",
            "meta_runtime_language_absent",
            "stage_direction_labels_absent",
            "source_reproduction_absent",
            "live_runtime_contract_pass",
            "live_runtime_visible_surface_pass",
            "live_opening_contract_pass",
        }
        deterministic_scores = {
            key: value
            for key, value in deterministic_scores.items()
            if key in narrator_path_gate_scores
        }
    for name, value in deterministic_scores.items():
        try:
            adapter.add_score(
                name=name,
                value=value,
                comment="deterministic live story runtime evidence gate",
                metadata=dict(score_metadata_base),
            )
        except Exception:
            logger.debug("Langfuse score write failed for %s", name, exc_info=True)
'''
