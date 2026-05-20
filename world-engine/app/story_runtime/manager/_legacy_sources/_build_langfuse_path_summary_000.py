SOURCE = r'''\
def _build_langfuse_path_summary(
    *,
    session: "StorySession",
    graph_state: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    nodes = _str_list(graph_state.get("nodes_executed"))
    routing = graph_state.get("routing") if isinstance(graph_state.get("routing"), dict) else {}
    generation = graph_state.get("generation") if isinstance(graph_state.get("generation"), dict) else {}
    interpreted_input = (
        graph_state.get("interpreted_input")
        if isinstance(graph_state.get("interpreted_input"), dict)
        else {}
    )
    semantic_move_record = (
        graph_state.get("semantic_move_record")
        if isinstance(graph_state.get("semantic_move_record"), dict)
        else {}
    )
    scene_plan_record = (
        graph_state.get("scene_plan_record")
        if isinstance(graph_state.get("scene_plan_record"), dict)
        else {}
    )
    scene_assessment = (
        graph_state.get("scene_assessment")
        if isinstance(graph_state.get("scene_assessment"), dict)
        else {}
    )
    multi_pressure_resolution = (
        scene_assessment.get("multi_pressure_resolution")
        if isinstance(scene_assessment.get("multi_pressure_resolution"), dict)
        else {}
    )
    gen_meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    validation = (
        graph_state.get("validation_outcome")
        if isinstance(graph_state.get("validation_outcome"), dict)
        else {}
    )
    actor_lane_validation = (
        validation.get("actor_lane_validation")
        if isinstance(validation.get("actor_lane_validation"), dict)
        else {}
    )
    committed = (
        graph_state.get("committed_result")
        if isinstance(graph_state.get("committed_result"), dict)
        else {}
    )
    telemetry = (
        graph_state.get("actor_survival_telemetry")
        if isinstance(graph_state.get("actor_survival_telemetry"), dict)
        else {}
    )
    vitality = (
        telemetry.get("vitality_telemetry_v1")
        if isinstance(telemetry.get("vitality_telemetry_v1"), dict)
        else {}
    )
    passivity = (
        telemetry.get("passivity_diagnosis_v1")
        if isinstance(telemetry.get("passivity_diagnosis_v1"), dict)
        else {}
    )
    governance = (
        event.get("runtime_governance_surface")
        if isinstance(event.get("runtime_governance_surface"), dict)
        else {}
    )
    human_input_attribution = (
        event.get("human_input_attribution")
        if isinstance(event.get("human_input_attribution"), dict)
        else {}
    )
    retrieval = graph_state.get("retrieval") if isinstance(graph_state.get("retrieval"), dict) else {}
    structured = gen_meta.get("structured_output")
    if structured is None:
        structured = generation.get("structured_output")
    graph_errors = _str_list(graph_state.get("graph_errors"))
    _ledger_src = (
        graph_state.get("turn_aspect_ledger")
        if isinstance(graph_state.get("turn_aspect_ledger"), dict)
        else event.get("turn_aspect_ledger")
        if isinstance(event.get("turn_aspect_ledger"), dict)
        else None
    )
    turn_aspect_ledger = normalize_runtime_aspect_ledger(_ledger_src) if isinstance(_ledger_src, dict) else None
    usage_details = gen_meta.get("usage_details") if isinstance(gen_meta.get("usage_details"), dict) else {}
    _u_in = int(usage_details.get("input") or gen_meta.get("tokens_prompt") or 0)
    _u_out = int(usage_details.get("output") or gen_meta.get("tokens_completion") or 0)
    _u_tot = int(usage_details.get("total") or gen_meta.get("tokens_total") or 0)
    if _u_tot <= 0 and (_u_in > 0 or _u_out > 0):
        _u_tot = _u_in + _u_out
    usage_total = _u_tot
    _graph_pkg = event.get("graph") if isinstance(event.get("graph"), dict) else {}
    _graph_name = str(_graph_pkg.get("graph_name") or "").strip() or None
    _route_id = str(routing.get("route_id") or "").strip()
    _route_family = str(routing.get("route_family") or "").strip()
    _langfuse_prompt_parts = [p for p in (_route_id, _route_family, _graph_name) if p]
    _langfuse_prompt_name = "/".join(_langfuse_prompt_parts) if _langfuse_prompt_parts else None
    _lat_raw = gen_meta.get("generation_latency_ms")
    _lat_ms = float(_lat_raw) if isinstance(_lat_raw, (int, float)) else None
    _tps_out: float | None = None
    if _lat_ms is not None and _lat_ms > 0 and _u_out > 0:
        _tps_out = round(_u_out / (_lat_ms / 1000.0), 4)
    _streaming = gen_meta.get("llm_invocation_streaming")
    _ttft_ms: float | None = None
    if _lat_ms is not None and _lat_ms >= 0:
        # Non-streaming HTTP completions: no true first-token boundary; use full call latency.
        if _streaming is False:
            _ttft_ms = round(_lat_ms, 3)
    projection = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
    provenance = session.content_provenance if isinstance(session.content_provenance, dict) else {}
    trace_classification = (
        provenance.get("trace_classification")
        if isinstance(provenance.get("trace_classification"), dict)
        else {}
    )
    runtime_mode = str(
        trace_classification.get("runtime_mode")
        or projection.get("runtime_mode")
        or "solo_story"
    ).strip() or "solo_story"
    trace_origin = str(trace_classification.get("trace_origin") or "").strip() or "unknown"
    execution_tier = str(trace_classification.get("execution_tier") or "").strip()
    if not execution_tier:
        execution_tier = _infer_execution_tier_for_pytest() if trace_origin == "pytest" else "diagnostic"
    canonical_player_flow = bool(trace_classification.get("canonical_player_flow", False))
    test_case_id = trace_classification.get("test_case_id")
    environment = _observability_environment_for_session(session)
    local_evidence_meta = local_langfuse_evidence_metadata()
    if local_evidence_meta.get("environment"):
        environment = str(local_evidence_meta.get("environment") or "local")

    _spr = (
        str((session.runtime_projection or {}).get("selected_player_role") or "").strip()
        if isinstance(session.runtime_projection, dict)
        else ""
    )
    _player_input_kind = str(interpreted_input.get("player_input_kind") or "").strip().lower()
    _semantic_move_kind = str(semantic_move_record.get("move_type") or "").strip()
    _subtext_record = (
        semantic_move_record.get("subtext")
        if isinstance(semantic_move_record.get("subtext"), dict)
        else {}
    )
    _subtext_contract_pass = True
    if semantic_move_record:
        _subtext_contract_pass = (
            (not _semantic_move_kind or _semantic_move_kind in SEMANTIC_MOVE_TYPES)
            and bool(str(_subtext_record.get("surface_mode") or "").strip())
            and bool(str(_subtext_record.get("hidden_intent_hypothesis") or "").strip())
            and bool(str(_subtext_record.get("subtext_function") or "").strip())
            and bool(str(_subtext_record.get("sincerity_band") or "").strip())
        )
    _intent_surface_contract_pass = True
    if _player_input_kind:
        _intent_surface_contract_pass = (
            _player_input_kind in PLAYER_INPUT_KINDS
            and isinstance(interpreted_input.get("player_action_committed"), bool)
            and isinstance(interpreted_input.get("player_speech_committed"), bool)
            and isinstance(interpreted_input.get("narrator_response_expected"), bool)
            and isinstance(interpreted_input.get("npc_response_expected"), bool)
        )
    _player_input_attribution_pass = (
        bool(human_input_attribution.get("player_input_attribution_pass"))
        if "player_input_attribution_pass" in human_input_attribution
        else True
    )
    _semantic_move_alignment_pass = True
    if _semantic_move_kind:
        _semantic_move_alignment_pass = True
    if is_question_punctuation_probe_guarded(_player_input_kind) and _semantic_move_kind:
        _semantic_move_alignment_pass = (
            _semantic_move_alignment_pass
            and _semantic_move_kind not in FORBIDDEN_NON_SPEECH_ACTION_SEMANTIC_MOVES
        )
    _npc_action_narration_boundary_pass = not bool(
        (
            validation.get("intent_surface_diagnostics")
            if isinstance(validation.get("intent_surface_diagnostics"), dict)
            else {}
        ).get("npc_narrated_player_action_violation")
    )
    _runtime_profile_id = (
        _runtime_profile_id_from_projection(projection)
        or (
            turn_aspect_ledger.get("runtime_profile_id")
            if isinstance(turn_aspect_ledger, dict)
            else None
        )
    )
    if isinstance(turn_aspect_ledger, dict) and _runtime_profile_id and not turn_aspect_ledger.get("runtime_profile_id"):
        turn_aspect_ledger = dict(turn_aspect_ledger)
        turn_aspect_ledger["runtime_profile_id"] = _runtime_profile_id
        turn_aspect_ledger = normalize_runtime_aspect_ledger(turn_aspect_ledger)
    self_correction = (
        graph_state.get("self_correction")
        if isinstance(graph_state.get("self_correction"), dict)
        else {}
    )
    _sc_attempts_raw = (
        self_correction.get("attempts")
        if isinstance(self_correction.get("attempts"), list)
        else []
    )
    _sc_attempts = [item for item in _sc_attempts_raw if isinstance(item, dict)]
    _first_sc = _sc_attempts[0] if _sc_attempts else {}
    _last_sc = _sc_attempts[-1] if _sc_attempts else {}
    _sc_attempted = gen_meta.get("self_correction_attempted")
    if _sc_attempted is None and self_correction:
        _sc_attempted = bool(_sc_attempts)
    _sc_attempt_count = gen_meta.get("self_correction_attempt_count")
    if _sc_attempt_count is None and self_correction:
        _sc_attempt_count = self_correction.get("attempt_count")
        if _sc_attempt_count is None:
            _sc_attempt_count = len(_sc_attempts)
    _sc_success = gen_meta.get("self_correction_success")
    if _sc_success is None and self_correction:
        _sc_success = (
            bool(_last_sc.get("success")) and not _last_sc.get("parser_error")
            if _last_sc
            else False
        )
    _sc_model = gen_meta.get("self_correction_model")
    if _sc_model is None and _last_sc:
        _sc_model = _last_sc.get("candidate_model")
    _sc_trigger_source = gen_meta.get("self_correction_trigger_source")
    if _sc_trigger_source is None and _first_sc:
        _sc_trigger_source = _first_sc.get("trigger_source")
    _runtime_aspect_failure_before_retry = gen_meta.get("runtime_aspect_failure_before_retry")
    if _runtime_aspect_failure_before_retry is None and _first_sc:
        _runtime_aspect_failure_before_retry = _first_sc.get("runtime_aspect_failure_before_retry")
    _capability_failure_before_retry = gen_meta.get("capability_failure_before_retry")
    if _capability_failure_before_retry is None and _first_sc:
        _capability_failure_before_retry = _first_sc.get("capability_failure_before_retry")
    _sc_resolved_failure = gen_meta.get("self_correction_resolved_failure")
    if _sc_resolved_failure is None and self_correction:
        _sc_resolved_failure = any(bool(item.get("resolved_failure")) for item in _sc_attempts)
'''
