SOURCE = r'''\
    branching_forecast = (
        event.get("branching_forecast")
        if isinstance(event.get("branching_forecast"), dict)
        else graph_state.get("branching_forecast")
        if isinstance(graph_state.get("branching_forecast"), dict)
        else turn_aspect_ledger.get("branching_forecast")
        if isinstance(turn_aspect_ledger, dict) and isinstance(turn_aspect_ledger.get("branching_forecast"), dict)
        else {}
    )
    branch_option_count = int(branching_forecast.get("option_count") or 0) if branching_forecast else 0
    branching_forecast_present = (
        bool(branching_forecast)
        and str(branching_forecast.get("status") or "").strip() == "forecasted"
        and branch_option_count > 0
    )
    inactive_branches_non_authoritative = bool(
        branching_forecast
        and branching_forecast.get("forecast_only") is True
        and branching_forecast.get("authoritative") is False
        and branching_forecast.get("inactive_branches_authoritative") is False
        and branching_forecast.get("mutates_canonical_state") is False
    )
    _capability_projection = (
        turn_aspect_ledger.get("capability")
        if isinstance(turn_aspect_ledger, dict) and isinstance(turn_aspect_ledger.get("capability"), dict)
        else {}
    )
    _capability_selection_projection = (
        turn_aspect_ledger.get("capability_selection")
        if isinstance(turn_aspect_ledger, dict)
        and isinstance(turn_aspect_ledger.get("capability_selection"), dict)
        else {}
    )
    _validator_dispatch_report = (
        turn_aspect_ledger.get("validator_dispatch_report")
        if isinstance(turn_aspect_ledger, dict)
        and isinstance(turn_aspect_ledger.get("validator_dispatch_report"), dict)
        else {}
    )
    _readiness_policy_input = (
        graph_state.get("readiness_policy_input")
        if isinstance(graph_state.get("readiness_policy_input"), dict)
        else turn_aspect_ledger.get("readiness_policy_input")
        if isinstance(turn_aspect_ledger, dict)
        and isinstance(turn_aspect_ledger.get("readiness_policy_input"), dict)
        else None
    )
    narrator_path_selected = str(graph_state.get("director_path_mode") or "").strip() == "narrator_path"
    summary = {
        "contract": "story_runtime_path_observability.v1",
        "session_id": session.session_id,
        "module_id": session.module_id,
        "runtime_profile_id": _runtime_profile_id,
        "environment": environment,
        "turn_number": event.get("turn_number"),
        "turn_kind": event.get("turn_kind"),
        "raw_player_input": str(event.get("raw_input") or graph_state.get("player_input") or "").strip() or None,
        "turn_aspect_ledger_present": bool(
            isinstance(turn_aspect_ledger, dict)
            and isinstance(turn_aspect_ledger.get("turn_aspect_ledger"), dict)
        ),
        "turn_aspect_ledger": turn_aspect_ledger,
        "branching_forecast": branching_forecast,
        "branching_forecast_status": branching_forecast.get("status") if branching_forecast else None,
        "branching_forecast_present": branching_forecast_present,
        "branch_option_count": branch_option_count,
        "branching_forecast_only": bool(branching_forecast.get("forecast_only")) if branching_forecast else False,
        "inactive_branches_non_authoritative": inactive_branches_non_authoritative,
        "inactive_branches_mutate_state": bool(branching_forecast.get("mutates_canonical_state"))
        if branching_forecast
        else False,
        "selected_player_role": _spr or None,
        "human_actor_id": (session.runtime_projection or {}).get("human_actor_id") if isinstance(session.runtime_projection, dict) else None,
        "player_role_display_name": goc_player_role_display_name(_spr or None),
        "session_input_language": getattr(session, "session_input_language", None) or getattr(session, "session_output_language", None) or DEFAULT_SESSION_LANGUAGE,
        "session_output_language": getattr(session, "session_output_language", None) or DEFAULT_SESSION_LANGUAGE,
        "npc_actor_ids": list((session.runtime_projection or {}).get("npc_actor_ids") or []) if isinstance(session.runtime_projection, dict) else [],
        "nodes_executed": nodes,
        "route_model_called": False if narrator_path_selected else "route_model" in nodes or bool(routing),
        "invoke_model_called": False if narrator_path_selected else "invoke_model" in nodes,
        "fallback_model_called": "fallback_model" in nodes or bool(generation.get("fallback_used")),
        "graph_fallback_node_called": "fallback_model" in nodes,
        "retrieval_called": False if narrator_path_selected else "retrieve_context" in nodes or bool(retrieval),
        "validation_called": "validate_seam" in nodes or bool(validation),
        "commit_called": "commit_seam" in nodes or bool(committed),
        "render_visible_called": "render_visible" in nodes or isinstance(event.get("visible_output_bundle"), dict),
        "route_id": routing.get("route_id"),
        "route_family": routing.get("route_family"),
        "selected_provider": routing.get("selected_provider"),
        "selected_model": routing.get("selected_model"),
        "fallback_model": routing.get("fallback_model"),
        "fallback_chain": routing.get("fallback_chain"),
        "registered_adapter_providers": routing.get("registered_adapter_providers"),
        "generation_execution_mode": routing.get("generation_execution_mode"),
        "adapter": gen_meta.get("adapter"),
        "api_model": gen_meta.get("model"),
        "adapter_invocation_mode": gen_meta.get("adapter_invocation_mode"),
        # ADR-0033 §13.10 primary-vs-final clarity. ``adapter``/``api_model`` describe
        # the FINAL committed invocation (e.g. ldss_fallback after live opening failure).
        # The primary-attempt block surfaces what live route was tried first so
        # operators do not misread degraded fallback traces as healthy openai turns.
        "primary_attempt_adapter": gen_meta.get("primary_attempt_adapter"),
        "primary_attempt_model": gen_meta.get("primary_attempt_model"),
        "primary_attempt_provider": (
            gen_meta.get("primary_attempt_provider")
            or routing.get("selected_provider")
        ),
        "primary_attempt_selected_model": (
            gen_meta.get("primary_attempt_selected_model")
            or routing.get("selected_model")
        ),
        "primary_attempt_invocation_mode": gen_meta.get("primary_attempt_invocation_mode"),
        "final_adapter": gen_meta.get("final_adapter") or gen_meta.get("adapter"),
        "final_adapter_invocation_mode": (
            gen_meta.get("final_adapter_invocation_mode")
            or gen_meta.get("adapter_invocation_mode")
        ),
        "fallback_reason": gen_meta.get("fallback_reason") or routing.get("fallback_reason"),
        "ldss_fallback_after_live_opening_failure": bool(
            gen_meta.get("ldss_fallback_after_live_opening_failure")
        ),
        "generation_attempted": bool(generation.get("attempted")),
        "generation_success": generation.get("success"),
        "generation_error": _short_text(generation.get("error") or gen_meta.get("error")),
        "generation_fallback_used": bool(generation.get("fallback_used")),
        "parser_error": _short_text(gen_meta.get("langchain_parser_error") or generation.get("parser_error")),
        "structured_output_present": isinstance(structured, dict),
        "structured_output_keys": sorted(structured.keys()) if isinstance(structured, dict) else [],
        # PRIMARY-PARSER-EVIDENCE-01: primary attempt diagnosis fields.
        "primary_attempt_api_success": gen_meta.get("primary_attempt_api_success"),
        "primary_attempt_parser_error_present": gen_meta.get("primary_attempt_parser_error_present"),
        "primary_attempt_parser_error": gen_meta.get("primary_attempt_parser_error"),
        "primary_attempt_structured_output_present": gen_meta.get("primary_attempt_structured_output_present"),
        "primary_attempt_raw_output_sha256": gen_meta.get("primary_attempt_raw_output_sha256"),
        "primary_attempt_raw_output_excerpt": gen_meta.get("primary_attempt_raw_output_excerpt"),
        "self_correction_attempted": _sc_attempted,
        "self_correction_attempt_count": _sc_attempt_count,
        "self_correction_success": _sc_success,
        "self_correction_model": _sc_model,
        "self_correction_trigger_source": _sc_trigger_source,
        "runtime_aspect_failure_before_retry": _runtime_aspect_failure_before_retry,
        "capability_failure_before_retry": _capability_failure_before_retry,
        "self_correction_resolved_failure": _sc_resolved_failure,
        "usage_available": bool(gen_meta.get("usage_available")) or usage_total > 0,
        "usage_source": gen_meta.get("usage_source"),
        "usage_details": {
            "input": _u_in,
            "output": _u_out,
            "total": usage_total,
        },
        "langfuse_prompt_name": _langfuse_prompt_name,
        "provided_model_name": str(gen_meta.get("model") or "").strip() or None,
        "generation_latency_ms": round(_lat_ms, 3) if isinstance(_lat_ms, (int, float)) else None,
        "llm_invocation_streaming": _streaming,
        "time_to_first_token_ms": _ttft_ms,
        "time_to_first_token_note": (
            "non_streaming_latency_proxy" if _streaming is False and _ttft_ms is not None else None
        ),
        "tokens_per_second_output": _tps_out,
        "retrieval_status": retrieval.get("status"),
        "retrieval_route": retrieval.get("retrieval_route"),
        "retrieval_hit_count": retrieval.get("hit_count"),
        "retrieval_profile": retrieval.get("profile"),
        "retrieval_domain": retrieval.get("domain"),
        "retrieval_context_attached": bool(graph_state.get("context_text") or generation.get("retrieval_context_attached")),
        "retrieval_top_hit_score": retrieval.get("top_hit_score"),
        "retrieval_documents_used": retrieval.get("documents_used"),
        "retrieval_provenance": retrieval.get("provenance"),
        "retrieval_authority_level": retrieval.get("authority_level")
        or retrieval.get("governance_authority_level"),
        "retrieval_corpus_fingerprint": retrieval.get("corpus_fingerprint"),
        "retrieval_index_version": retrieval.get("index_version"),
        "retrieval_degradation_mode": retrieval.get("degradation_mode"),
        "retrieval_governance_summary": retrieval.get("retrieval_governance_summary"),
        "selected_capabilities": (
            _capability_projection.get("selected_capabilities")
            or _capability_selection_projection.get("selected_capabilities")
            or (
                (graph_state.get("realization_plan") or {}).get("capabilities_selected")
                if isinstance(graph_state.get("realization_plan"), dict)
                else None
            )
            or []
        ),
        "realization_plan": graph_state.get("realization_plan")
        if isinstance(graph_state.get("realization_plan"), dict)
        else None,
        "realize_via_capabilities_used_capability": graph_state.get(
            "realize_via_capabilities_used_capability"
        ),
        "realize_via_capabilities_outcome": graph_state.get("realize_via_capabilities_outcome"),
        "kanon_break": bool(graph_state.get("kanon_break")),
        "kanon_break_reason": graph_state.get("kanon_break_reason"),
        # PR-B: live effect propagation fields. The hold-effect dict is
        # ``None`` for action classes that must not hold (unknown / criminal
        # / high-risk / non-commit). The realization contract is always
        # emitted; ``visible_block_emitted`` and ``non_realization_reason``
        # carry the explicit status. See
        # ``docs/implementation_logs/pr_b_live_effect_propagation_piv.md``.
        "canonical_path_hold_effect": (
            graph_state.get("canonical_path_hold_effect")
            if isinstance(graph_state.get("canonical_path_hold_effect"), dict)
            else None
        ),
        "free_player_action_resolution": (
            graph_state.get("free_player_action_resolution")
            if isinstance(graph_state.get("free_player_action_resolution"), dict)
            else None
        ),
        "narrator_consequence_realization": (
            graph_state.get("narrator_consequence_realization")
            if isinstance(graph_state.get("narrator_consequence_realization"), dict)
            else None
        ),
        "director_gathering_state": (
            graph_state.get("director_gathering_state")
            if isinstance(graph_state.get("director_gathering_state"), dict)
            else None
        ),
        "gathering_paused_beat_suppression": graph_state.get(
            "gathering_paused_beat_suppression"
        ),
        "director_pause_transition_reaction": (
            graph_state.get("director_pause_transition_reaction")
            if isinstance(graph_state.get("director_pause_transition_reaction"), dict)
            else None
        ),
        "visible_block_emitted": bool(
            (
                graph_state.get("narrator_consequence_realization")
                if isinstance(graph_state.get("narrator_consequence_realization"), dict)
                else {}
            ).get("visible_block_emitted")
        ),
        "director_path_mode": graph_state.get("director_path_mode")
        or (
            "director_realization_composer"
            if isinstance(graph_state.get("realization_plan"), dict)
            else None
        ),
'''
