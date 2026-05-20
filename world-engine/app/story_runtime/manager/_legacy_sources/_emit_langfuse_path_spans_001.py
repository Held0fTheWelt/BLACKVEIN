SOURCE = r'''\
            },
        ),
        (
            "story.phase.validation",
            {
                "called": path_summary.get("validation_called"),
                "status": path_summary.get("validation_status"),
                "reason": path_summary.get("validation_reason"),
                "actor_lane_validation_status": path_summary.get("actor_lane_validation_status"),
                "actor_lane_validation_reason": path_summary.get("actor_lane_validation_reason"),
                "response_present": path_summary.get("response_present"),
                "why_turn_felt_passive": path_summary.get("why_turn_felt_passive"),
                "primary_passivity_factors": path_summary.get("primary_passivity_factors"),
                "player_input_kind": path_summary.get("player_input_kind"),
                "player_action_committed": path_summary.get("player_action_committed"),
                "player_speech_committed": path_summary.get("player_speech_committed"),
                "narrator_response_expected": path_summary.get("narrator_response_expected"),
                "npc_response_expected": path_summary.get("npc_response_expected"),
                "semantic_move_kind": path_summary.get("semantic_move_kind"),
                "subtext_surface_mode": path_summary.get("subtext_surface_mode"),
                "subtext_hidden_intent_hypothesis": path_summary.get(
                    "subtext_hidden_intent_hypothesis"
                ),
                "subtext_function": path_summary.get("subtext_function"),
                "subtext_contract_pass": path_summary.get("subtext_contract_pass"),
                "scene_director_selection_source": path_summary.get("scene_director_selection_source"),
                "planner_rationale_codes": path_summary.get("planner_rationale_codes"),
                "legacy_keyword_scene_candidates_used": path_summary.get(
                    "legacy_keyword_scene_candidates_used"
                ),
                "intent_surface_contract_pass": path_summary.get("intent_surface_contract_pass"),
                "player_input_attribution_pass": path_summary.get("player_input_attribution_pass"),
                "semantic_move_alignment_pass": path_summary.get("semantic_move_alignment_pass"),
                "npc_action_narration_boundary_pass": path_summary.get(
                    "npc_action_narration_boundary_pass"
                ),
                "npc_narrated_player_action_violation": path_summary.get(
                    "npc_narrated_player_action_violation"
                ),
                "intent_surface_diagnostics": path_summary.get("intent_surface_diagnostics"),
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
            },
        ),
        (
            "story.phase.commit",
            {
                "called": path_summary.get("commit_called"),
                "commit_applied": path_summary.get("commit_applied"),
                "quality_class": path_summary.get("quality_class"),
                "degradation_summary": path_summary.get("degradation_summary"),
                "failure_markers": path_summary.get("failure_markers"),
                "player_input_kind": path_summary.get("player_input_kind"),
                "semantic_move_kind": path_summary.get("semantic_move_kind"),
                "subtext_function": path_summary.get("subtext_function"),
                "subtext_policy_rule_id": path_summary.get("subtext_policy_rule_id"),
                "scene_director_selection_source": path_summary.get("scene_director_selection_source"),
                "planner_rationale_codes": path_summary.get("planner_rationale_codes"),
                "legacy_keyword_scene_candidates_used": path_summary.get(
                    "legacy_keyword_scene_candidates_used"
                ),
                "npc_narrated_player_action_violation": path_summary.get(
                    "npc_narrated_player_action_violation"
                ),
            },
        ),
        (
            "story.branch.forecast",
            {
                "called": bool(path_summary.get("branching_forecast"))
                and path_summary.get("branching_forecast_status") != "not_applicable",
                "status": path_summary.get("branching_forecast_status"),
                "forecast_present": path_summary.get("branching_forecast_present"),
                "option_count": path_summary.get("branch_option_count"),
                "forecast_only": path_summary.get("branching_forecast_only"),
                "inactive_branches_non_authoritative": path_summary.get(
                    "inactive_branches_non_authoritative"
                ),
                "inactive_branches_mutate_state": path_summary.get("inactive_branches_mutate_state"),
                "forecast": path_summary.get("branching_forecast"),
            },
        ),
    ]
    if narrator_path_selected:
        span_specs.insert(
            1,
            (
                "story.phase.narrator_path",
                {
                    "called": True,
                    "director_path_mode": path_summary.get("director_path_mode"),
                    "selected_capabilities": path_summary.get("selected_capabilities"),
                    "speech_allowed": False,
                    "npc_agency_required": False,
                    "narrator_path": path_summary.get("narrator_path"),
                    "director_plan": path_summary.get("director_narrator_path_plan"),
                },
            ),
        )

    for name, output in span_specs:
        if narrator_path_selected:
            skip_when_not_called = {
                "story.phase.model_route",
                "story.phase.model_invoke",
                "story.phase.primary_parse",
                "story.phase.model_fallback",
                "story.phase.retrieval",
                "story.branch.forecast",
            }
            if name == "story.phase.intent_interpretation":
                continue
            if name == "story.branch.forecast":
                continue
            if name in skip_when_not_called and not bool(output.get("called")):
                continue
        level = _langfuse_level_for_output(output)
        status_message = _langfuse_status_for_output(name, output)
        try:
            span = adapter.create_child_span(
                name=name,
                input=base_input,
                output=output,
                metadata={
                    "phase": name.rsplit(".", 1)[-1],
                    "turn_number": path_summary.get("turn_number"),
                    "session_id": path_summary.get("session_id"),
                    "canonical_turn_id": path_summary.get("canonical_turn_id"),
                    "called": bool(output.get("called", True)),
                    "quality_class": path_summary.get("quality_class"),
                    "degradation_summary": path_summary.get("degradation_summary"),
                    "trace_origin": path_summary.get("trace_origin"),
                    "execution_tier": path_summary.get("execution_tier"),
                    "canonical_player_flow": path_summary.get("canonical_player_flow"),
                    "test_case_id": path_summary.get("test_case_id"),
                    "runtime_mode": path_summary.get("runtime_mode"),
                    "generation_mode": path_summary.get("generation_mode"),
                },
                level=level,
                status_message=status_message,
            )
        except Exception:
            logger.debug("Langfuse child span creation failed for %s", name, exc_info=True)
            continue
        _finish_langfuse_span(
            span,
            output=output,
            level=level,
            status_message=status_message,
        )
'''
