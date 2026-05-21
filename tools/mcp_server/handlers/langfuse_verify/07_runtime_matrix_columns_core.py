"""Langfuse verify source segment: runtime_matrix_columns_core.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        ps = nested_ps or direct_ps
        if ps:
            path_summary_source = "trace.output"
            _apply(ps, _PS_FIELDS)
        # Classification fields may be present even without a full path_summary
        _apply(trace_output, _CLASSIFICATION_FIELDS)

    # --- Source 2: story.graph.path_summary observation ---
    ps_obs = _find_observation_by_name(obs_list, "story.graph.path_summary")
    if ps_obs:
        for block_key in ("output", "input", "metadata"):
            block = _coerce_dict_or_json(ps_obs.get(block_key))
            if block:
                if path_summary_source == "missing":
                    path_summary_source = f"observation.{block_key}"
                _apply(block, _PS_FIELDS)

    # --- Source 3: score metadata (score_metadata_base carries WoS-specific fields) ---
    score_meta = _first_score_metadata(raw_trace)
    if score_meta:
        score_source = "trace.scores"
        _apply(score_meta, {
            "session_id", "selected_player_role", "human_actor_id",
            "final_adapter", "quality_class", "fallback_reason",
            "first_actor_block_index",
            "narrator_block_count",
            "structured_narration_summary_kind",
            "opening_narration_normalized",
            "opening_narration_source",
            "opening_narration_beat_count",
            "narration_summary_input_kind",
            "opening_shape_subgates",
            "opening_shape_failure_reasons",
            "scene_block_summary",
        })

    # --- Source 4: turn span metadata ---
    for span_name in ("backend.turn.execute", "world-engine.turn.execute"):
        span_obs = _find_observation_by_name(obs_list, span_name)
        if span_obs:
            for block_key in ("metadata", "output", "input"):
                block = _coerce_dict_or_json(span_obs.get(block_key))
                _apply(block, _CLASSIFICATION_FIELDS | {"session_id"})

    # --- Source 5: trace.metadata (top-level) ---
    trace_meta = _extract_metadata(raw_trace)
    _apply(trace_meta, _PS_FIELDS)

    # --- Source 6: world-engine.session.create statusMessage (key=value fallback) ---
    we_create = _find_observation_by_name(obs_list, "world-engine.session.create")
    if we_create:
        sm = str(
            we_create.get("statusMessage")
            or we_create.get("status_message")
            or ""
        )
        if sm:
            tokens = _parse_status_tokens(sm)
            if tokens:
                status_message_fallback_used = True
                if not ev.get("final_adapter") and tokens.get("adapter"):
                    ev["final_adapter"] = tokens["adapter"]
                if not ev.get("quality_class") and tokens.get("quality"):
                    ev["quality_class"] = tokens["quality"]

    # --- Gate scores ---
    det_scores, _ = _extract_scores_split(raw_trace)
    if det_scores:
        score_source = "trace.scores"
    for gate in (
        "opening_shape_contract_pass",
        "opening_contract_pass",
'''
