SOURCE = r'''\
def _emit_langfuse_evidence_observations(
    *,
    path_summary: dict[str, Any],
    graph_state: dict[str, Any],
    event: dict[str, Any],
) -> None:
    try:
        adapter = LangfuseAdapter.get_instance()
    except Exception:
        logger.debug("Langfuse adapter unavailable for evidence observations", exc_info=True)
        return
    try:
        if not adapter or not adapter.is_enabled():
            return
    except Exception:
        return

    generation = (
        (event.get("model_route") or {}).get("generation")
        if isinstance(event.get("model_route"), dict)
        else {}
    )
    if not isinstance(generation, dict):
        generation = {}
    gen_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    adapter_name = str(gen_meta.get("adapter") or "").strip()
    primary_adapter_name = str(path_summary.get("primary_attempt_adapter") or "").strip()
    deterministic_adapters = {"mock", "ldss_fallback", "ldss_deterministic", NARRATOR_PATH_ADAPTER}
    primary_attempt_api_success = path_summary.get("primary_attempt_api_success") is True
    record_primary_attempt_generation = (
        primary_attempt_api_success
        and bool(primary_adapter_name)
        and primary_adapter_name not in deterministic_adapters
    )
    record_final_generation = bool(adapter_name) and adapter_name not in deterministic_adapters
    usage_details = path_summary.get("usage_details") if isinstance(path_summary.get("usage_details"), dict) else {}
    _ud_in = int(usage_details.get("input") or 0)
    _ud_out = int(usage_details.get("output") or 0)
    _ud_tot = int(usage_details.get("total") or 0)
    if _ud_tot <= 0 and (_ud_in > 0 or _ud_out > 0):
        _ud_tot = _ud_in + _ud_out
    usage_for_lf = (
        {"input": _ud_in, "output": _ud_out, "total": _ud_tot} if (_ud_in or _ud_out or _ud_tot) else None
    )
    model_name = str(
        (
            path_summary.get("primary_attempt_model")
            if record_primary_attempt_generation and not record_final_generation
            else None
        )
        or path_summary.get("api_model")
        or path_summary.get("selected_model")
        or gen_meta.get("model")
        or "unknown"
    ).strip()
    provider = str(
        (
            path_summary.get("primary_attempt_provider")
            if record_primary_attempt_generation and not record_final_generation
            else None
        )
        or path_summary.get("selected_provider")
        or primary_adapter_name
        or adapter_name
        or "unknown"
    ).strip()
    _lat_ev = path_summary.get("generation_latency_ms")
    _lat_ev_f = float(_lat_ev) if isinstance(_lat_ev, (int, float)) else None
    _tps_ev = path_summary.get("tokens_per_second_output")
    _tps_ev_f = float(_tps_ev) if isinstance(_tps_ev, (int, float)) else None
    _ttft_ev = path_summary.get("time_to_first_token_ms")
    _ttft_ev_f = float(_ttft_ev) if isinstance(_ttft_ev, (int, float)) else None
    _provided = str(
        path_summary.get("provided_model_name")
        or (
            path_summary.get("primary_attempt_model")
            if record_primary_attempt_generation and not record_final_generation
            else None
        )
        or gen_meta.get("model")
        or model_name
    ).strip()
    _prompt_name_ev = path_summary.get("langfuse_prompt_name")
    if record_final_generation or record_primary_attempt_generation:
        completion_text = (
            generation.get("model_raw_text")
            or generation.get("content")
            or path_summary.get("primary_attempt_raw_output_excerpt")
            or ""
        )
        try:
            adapter.record_generation(
                name="story.model.generation",
                model=model_name,
                provider=provider,
                prompt=str(graph_state.get("model_prompt") or "")[:20000],
                completion=str(completion_text)[:20000],
                usage_details=usage_for_lf,
                provided_model_name=_provided or None,
                prompt_name=str(_prompt_name_ev).strip() if _prompt_name_ev else None,
                latency_ms=_lat_ev_f,
                time_to_first_token_ms=_ttft_ev_f,
                tokens_per_second=_tps_ev_f,
                metadata={
                    "session_id": path_summary.get("session_id"),
                    "module_id": path_summary.get("module_id"),
                    "turn_number": path_summary.get("turn_number"),
                    "canonical_turn_id": path_summary.get("canonical_turn_id"),
                    "opening_turn": int(path_summary.get("turn_number") or 0) == 0,
                    "turn_kind": path_summary.get("turn_kind"),
                    "adapter": adapter_name,
                    "generation_observation_source": (
                        "primary_attempt" if record_primary_attempt_generation and not record_final_generation else "final"
                    ),
                    "primary_attempt_adapter": path_summary.get("primary_attempt_adapter"),
                    "primary_attempt_model": path_summary.get("primary_attempt_model"),
                    "primary_attempt_provider": path_summary.get("primary_attempt_provider"),
                    "primary_attempt_invocation_mode": path_summary.get("primary_attempt_invocation_mode"),
                    "primary_attempt_api_success": path_summary.get("primary_attempt_api_success"),
                    "primary_attempt_structured_output_present": path_summary.get(
                        "primary_attempt_structured_output_present"
                    ),
                    "primary_attempt_raw_output_sha256": path_summary.get("primary_attempt_raw_output_sha256"),
                    "adapter_invocation_mode": path_summary.get("adapter_invocation_mode"),
                    "final_adapter": path_summary.get("final_adapter"),
                    "final_adapter_invocation_mode": path_summary.get("final_adapter_invocation_mode"),
                    "route_id": path_summary.get("route_id"),
                    "route_family": path_summary.get("route_family"),
                    "selected_model": path_summary.get("selected_model"),
                    "fallback_model": path_summary.get("fallback_model"),
                    "fallback_used": path_summary.get("generation_fallback_used"),
                    "structured_output_present": path_summary.get("structured_output_present"),
                    "parser_error": path_summary.get("parser_error"),
                    "retrieval_context_attached": path_summary.get("retrieval_context_attached"),
                    "usage_available": path_summary.get("usage_available"),
                    "usage_source": path_summary.get("usage_source"),
                    "trace_origin": path_summary.get("trace_origin"),
                    "execution_tier": path_summary.get("execution_tier"),
                    "canonical_player_flow": path_summary.get("canonical_player_flow"),
                    "test_case_id": path_summary.get("test_case_id"),
                    "runtime_mode": path_summary.get("runtime_mode"),
                    "generation_mode": path_summary.get("generation_mode"),
                    "input_tokens": _ud_in,
                    "output_tokens": _ud_out,
                    "total_tokens": _ud_tot,
                    "time_to_first_token_note": path_summary.get("time_to_first_token_note"),
                },
            )
        except Exception:
            logger.debug("Langfuse generation observation failed", exc_info=True)

    retrieval = event.get("retrieval") if isinstance(event.get("retrieval"), dict) else {}
    sources = retrieval.get("sources") if isinstance(retrieval.get("sources"), list) else []
    documents: list[dict[str, Any]] = []
    for source in sources[:8]:
        if not isinstance(source, dict):
            continue
        documents.append(
            {
                "id": source.get("chunk_id") or source.get("source_path"),
                "content": source.get("snippet"),
                "score": source.get("score"),
                "metadata": {
                    "source_path": source.get("source_path"),
                    "content_class": source.get("content_class"),
                    "pack_role": source.get("pack_role"),
                    "source_evidence_lane": source.get("source_evidence_lane"),
                    "policy_note": source.get("policy_note"),
                },
            }
        )
    if retrieval:
        try:
            adapter.record_retrieval(
                name="story.rag.retrieval",
                query=str(retrieval.get("query") or event.get("raw_input") or "")[:4000],
                documents=documents,
                metadata={
                    "session_id": path_summary.get("session_id"),
                    "module_id": path_summary.get("module_id"),
                    "turn_number": path_summary.get("turn_number"),
                    "canonical_turn_id": path_summary.get("canonical_turn_id"),
                    "status": path_summary.get("retrieval_status"),
                    "retrieval_route": path_summary.get("retrieval_route"),
                    "hit_count": path_summary.get("retrieval_hit_count"),
                    "profile": path_summary.get("retrieval_profile"),
                    "domain": path_summary.get("retrieval_domain"),
                    "context_attached": path_summary.get("retrieval_context_attached"),
                    "top_hit_score": path_summary.get("retrieval_top_hit_score"),
                    "corpus_fingerprint": path_summary.get("retrieval_corpus_fingerprint"),
                    "index_version": path_summary.get("retrieval_index_version"),
                    "degradation_mode": path_summary.get("retrieval_degradation_mode"),
                    "governance_summary": path_summary.get("retrieval_governance_summary"),
                    "trace_origin": path_summary.get("trace_origin"),
                    "execution_tier": path_summary.get("execution_tier"),
                    "canonical_player_flow": path_summary.get("canonical_player_flow"),
                    "test_case_id": path_summary.get("test_case_id"),
                    "runtime_mode": path_summary.get("runtime_mode"),
                    "generation_mode": path_summary.get("generation_mode"),
                },
            )
        except Exception:
            logger.debug("Langfuse retrieval observation failed", exc_info=True)

    # Align with player-visible truth: opening turns often have gm_narration / generation text
    # before scene_blocks projection; counting only scene_blocks yields false 0 (see Langfuse traces).
    has_visible_surface = bool(_scene_blocks_from_turn_event(event)) or bool(
        _visible_lines_from_turn_event(event)
    )
    _authoritative_action_surface = adapter_name in {
        "action_resolution_authoritative",
        "action_resolution_synthetic",
    }
    deterministic_scores = {
        "non_mock_generation_pass": (
            1.0
            if _authoritative_action_surface
            or adapter_name not in {"", "mock", "ldss_fallback", "ldss_deterministic"}
            else 0.0
        ),
        "visible_output_present": 1.0 if has_visible_surface else 0.0,
        "actor_lane_safety_pass": 1.0 if path_summary.get("actor_lane_validation_status") in {"approved", None} else 0.0,
        "fallback_absent": 0.0 if path_summary.get("generation_fallback_used") else 1.0,
        "usage_present": 1.0 if int(usage_details.get("total") or 0) > 0 or _authoritative_action_surface else 0.0,
        "rag_context_attached": 1.0 if path_summary.get("retrieval_context_attached") else 0.0,
    }
    narrator_path_selected = bool(path_summary.get("narrator_path_selected")) or (
        str(path_summary.get("director_path_mode") or "").strip() == "narrator_path"
    )
    if narrator_path_selected:
        deterministic_scores["usage_present"] = 1.0
        deterministic_scores["rag_context_attached"] = 1.0
    intent_kind = str(path_summary.get("player_input_kind") or "").strip().lower()
    semantic_move_kind = str(path_summary.get("semantic_move_kind") or "").strip()
    semantic_alignment_pass = True
    if semantic_move_kind:
        semantic_alignment_pass = True
    if is_question_punctuation_probe_guarded(intent_kind) and semantic_move_kind:
        semantic_alignment_pass = (
            semantic_alignment_pass
'''
