SOURCE = r'''\
def _emit_langfuse_path_spans(path_summary: dict[str, Any]) -> None:
    try:
        adapter = LangfuseAdapter.get_instance()
    except Exception:
        logger.debug("Langfuse adapter unavailable for path spans", exc_info=True)
        return
    try:
        if not adapter or not adapter.is_enabled():
            return
    except Exception:
        return

    base_input = {
        "session_id": path_summary.get("session_id"),
        "module_id": path_summary.get("module_id"),
        "turn_number": path_summary.get("turn_number"),
        "turn_kind": path_summary.get("turn_kind"),
        "trace_origin": path_summary.get("trace_origin"),
        "execution_tier": path_summary.get("execution_tier"),
        "environment": path_summary.get("environment"),
        "canonical_player_flow": path_summary.get("canonical_player_flow"),
        "runtime_mode": path_summary.get("runtime_mode"),
        "generation_mode": path_summary.get("generation_mode"),
        "evidence_scope": path_summary.get("evidence_scope"),
        "proof_level": path_summary.get("proof_level"),
        "live_or_staging_evidence": path_summary.get("live_or_staging_evidence"),
        "runtime_quality": path_summary.get("runtime_quality"),
        "player_input_kind": path_summary.get("player_input_kind"),
        "semantic_move_kind": path_summary.get("semantic_move_kind"),
        "subtext_function": path_summary.get("subtext_function"),
        "canonical_turn_id": path_summary.get("canonical_turn_id"),
    }
    narrator_path_selected = bool(path_summary.get("narrator_path_selected")) or (
        str(path_summary.get("director_path_mode") or "").strip() == "narrator_path"
    )

    span_specs = [
        (
            "story.graph.path_summary",
            {
                "canonical_turn_id": path_summary.get("canonical_turn_id"),
                "nodes_executed": path_summary.get("nodes_executed"),
                "route_model_called": path_summary.get("route_model_called"),
                "invoke_model_called": path_summary.get("invoke_model_called"),
                "fallback_model_called": path_summary.get("fallback_model_called"),
                "graph_fallback_node_called": path_summary.get("graph_fallback_node_called"),
                "validation_called": path_summary.get("validation_called"),
                "commit_called": path_summary.get("commit_called"),
                "render_visible_called": path_summary.get("render_visible_called"),
                "retrieval_called": path_summary.get("retrieval_called"),
                "retrieval_status": path_summary.get("retrieval_status"),
                "retrieval_hit_count": path_summary.get("retrieval_hit_count"),
                "quality_class": path_summary.get("quality_class"),
                "runtime_quality": path_summary.get("runtime_quality"),
                "degradation_signals": path_summary.get("degradation_signals"),
                "trace_origin": path_summary.get("trace_origin"),
                "execution_tier": path_summary.get("execution_tier"),
                "environment": path_summary.get("environment"),
                "evidence_scope": path_summary.get("evidence_scope"),
                "proof_level": path_summary.get("proof_level"),
                "live_or_staging_evidence": path_summary.get("live_or_staging_evidence"),
                "canonical_player_flow": path_summary.get("canonical_player_flow"),
                "runtime_mode": path_summary.get("runtime_mode"),
                "generation_mode": path_summary.get("generation_mode"),
                "selected_capabilities": path_summary.get("selected_capabilities"),
                "validator_dispatch_mode": path_summary.get("validator_dispatch_mode"),
                "readiness_policy_input": path_summary.get("readiness_policy_input"),
                "turn_aspect_ledger_present": path_summary.get("turn_aspect_ledger_present"),
                "branching_forecast_present": path_summary.get("branching_forecast_present"),
                "branch_option_count": path_summary.get("branch_option_count"),
                "inactive_branches_non_authoritative": path_summary.get(
                    "inactive_branches_non_authoritative"
                ),
                "raw_player_input": path_summary.get("raw_player_input"),
                "player_input_kind": path_summary.get("player_input_kind"),
                "semantic_move_kind": path_summary.get("semantic_move_kind"),
                "subtext_surface_mode": path_summary.get("subtext_surface_mode"),
                "subtext_hidden_intent_hypothesis": path_summary.get(
                    "subtext_hidden_intent_hypothesis"
                ),
                "subtext_function": path_summary.get("subtext_function"),
                "subtext_sincerity_band": path_summary.get("subtext_sincerity_band"),
                "subtext_policy_rule_id": path_summary.get("subtext_policy_rule_id"),
                "scene_director_selection_source": path_summary.get("scene_director_selection_source"),
                "planner_rationale_codes": path_summary.get("planner_rationale_codes"),
                "legacy_keyword_scene_candidates_used": path_summary.get(
                    "legacy_keyword_scene_candidates_used"
                ),
                "intent_surface_contract_pass": path_summary.get("intent_surface_contract_pass"),
                "player_input_attribution_pass": path_summary.get("player_input_attribution_pass"),
                "semantic_move_alignment_pass": path_summary.get("semantic_move_alignment_pass"),
                "subtext_contract_pass": path_summary.get("subtext_contract_pass"),
                "npc_action_narration_boundary_pass": path_summary.get(
                    "npc_action_narration_boundary_pass"
                ),
                "opening_event_coverage_pass": path_summary.get("opening_event_coverage_pass"),
                "hard_forbidden_absent": path_summary.get("hard_forbidden_absent"),
                "opening_summary_only_absent": path_summary.get("opening_summary_only_absent"),
                "p0_player_action_evidence_applicable": (
                    (path_summary.get("p0_action_resolution_evidence") or {}).get(
                        "p0_player_action_evidence_applicable"
                    )
                ),
                "p0_action_resolution_evidence": path_summary.get("p0_action_resolution_evidence"),
            },
        ),
        (
            "story.phase.intent_interpretation",
            {
                "called": True,
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
                "subtext_policy_rule_id": path_summary.get("subtext_policy_rule_id"),
                "scene_director_selection_source": path_summary.get("scene_director_selection_source"),
                "planner_rationale_codes": path_summary.get("planner_rationale_codes"),
                "legacy_keyword_scene_candidates_used": path_summary.get(
                    "legacy_keyword_scene_candidates_used"
                ),
            },
        ),
        (
            "story.phase.model_route",
            {
                "called": path_summary.get("route_model_called"),
                "route_id": path_summary.get("route_id"),
                "route_family": path_summary.get("route_family"),
                "selected_provider": path_summary.get("selected_provider"),
                "selected_model": path_summary.get("selected_model"),
                "fallback_model": path_summary.get("fallback_model"),
                "fallback_chain": path_summary.get("fallback_chain"),
                "registered_adapter_providers": path_summary.get("registered_adapter_providers"),
                "generation_execution_mode": path_summary.get("generation_execution_mode"),
            },
        ),
        (
            "story.phase.model_invoke",
            {
                "called": path_summary.get("invoke_model_called"),
                "attempted": path_summary.get("generation_attempted"),
                "success": path_summary.get("generation_success"),
                "error": path_summary.get("generation_error"),
                "adapter": path_summary.get("adapter"),
                "api_model": path_summary.get("api_model"),
                "adapter_invocation_mode": path_summary.get("adapter_invocation_mode"),
                "primary_attempt_adapter": path_summary.get("primary_attempt_adapter"),
                "primary_attempt_model": path_summary.get("primary_attempt_model"),
                "primary_attempt_invocation_mode": path_summary.get(
                    "primary_attempt_invocation_mode"
                ),
                "final_adapter": path_summary.get("final_adapter"),
                "final_adapter_invocation_mode": path_summary.get(
                    "final_adapter_invocation_mode"
                ),
                "parser_error": path_summary.get("parser_error"),
                "structured_output_present": path_summary.get("structured_output_present"),
                "structured_output_keys": path_summary.get("structured_output_keys"),
                # PRIMARY-PARSER-EVIDENCE-01
                "primary_attempt_api_success": path_summary.get("primary_attempt_api_success"),
                "primary_attempt_parser_error_present": path_summary.get("primary_attempt_parser_error_present"),
                "primary_attempt_parser_error": path_summary.get("primary_attempt_parser_error"),
                "primary_attempt_structured_output_present": path_summary.get("primary_attempt_structured_output_present"),
                "primary_attempt_raw_output_sha256": path_summary.get("primary_attempt_raw_output_sha256"),
                "primary_attempt_raw_output_excerpt": path_summary.get("primary_attempt_raw_output_excerpt"),
                "self_correction_attempted": path_summary.get("self_correction_attempted"),
                "self_correction_attempt_count": path_summary.get("self_correction_attempt_count"),
                "self_correction_success": path_summary.get("self_correction_success"),
                "self_correction_model": path_summary.get("self_correction_model"),
                "self_correction_trigger_source": path_summary.get("self_correction_trigger_source"),
                "runtime_aspect_failure_before_retry": path_summary.get(
                    "runtime_aspect_failure_before_retry"
                ),
                "capability_failure_before_retry": path_summary.get("capability_failure_before_retry"),
                "self_correction_resolved_failure": path_summary.get(
                    "self_correction_resolved_failure"
                ),
            },
        ),
        (
            "story.phase.primary_parse",
            {
                "called": path_summary.get("invoke_model_called"),
                "api_success": path_summary.get("primary_attempt_api_success"),
                "parser_error_present": path_summary.get("primary_attempt_parser_error_present"),
                "parser_error": path_summary.get("primary_attempt_parser_error"),
                "structured_output_present": path_summary.get("primary_attempt_structured_output_present"),
                "raw_output_sha256": path_summary.get("primary_attempt_raw_output_sha256"),
                "raw_output_excerpt": path_summary.get("primary_attempt_raw_output_excerpt"),
                "adapter": path_summary.get("primary_attempt_adapter"),
                "model": path_summary.get("primary_attempt_model"),
                "invocation_mode": path_summary.get("primary_attempt_invocation_mode"),
            },
        ),
        (
            "story.phase.model_fallback",
            {
                "called": path_summary.get("fallback_model_called"),
                "fallback_used": path_summary.get("generation_fallback_used"),
                "fallback_model": path_summary.get("fallback_model"),
                "fallback_reason": path_summary.get("fallback_reason"),
                "final_adapter": path_summary.get("final_adapter"),
                "final_adapter_invocation_mode": path_summary.get(
                    "final_adapter_invocation_mode"
                ),
                "ldss_fallback_after_live_opening_failure": path_summary.get(
                    "ldss_fallback_after_live_opening_failure"
                ),
                "live_opening_failure_reason": path_summary.get("live_opening_failure_reason"),
                "primary_attempt_adapter": path_summary.get("primary_attempt_adapter"),
                "primary_attempt_model": path_summary.get("primary_attempt_model"),
                "generation_error": path_summary.get("generation_error"),
                "graph_errors": path_summary.get("graph_errors"),
            },
        ),
        (
            "story.phase.retrieval",
            {
                "called": path_summary.get("retrieval_called"),
                "status": path_summary.get("retrieval_status"),
                "retrieval_route": path_summary.get("retrieval_route"),
                "hit_count": path_summary.get("retrieval_hit_count"),
                "profile": path_summary.get("retrieval_profile"),
                "domain": path_summary.get("retrieval_domain"),
                "context_attached": path_summary.get("retrieval_context_attached"),
                "top_hit_score": path_summary.get("retrieval_top_hit_score"),
                "documents_used": path_summary.get("retrieval_documents_used"),
                "provenance": path_summary.get("retrieval_provenance"),
                "authority_level": path_summary.get("retrieval_authority_level"),
                "corpus_fingerprint": path_summary.get("retrieval_corpus_fingerprint"),
                "index_version": path_summary.get("retrieval_index_version"),
                "degradation_mode": path_summary.get("retrieval_degradation_mode"),
                "governance_summary": path_summary.get("retrieval_governance_summary"),
'''
