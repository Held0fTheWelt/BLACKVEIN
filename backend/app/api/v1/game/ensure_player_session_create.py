"""Game routes implementation concern: ensure player session create.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''

    if not isinstance(run_payload, dict):
        run_payload = get_play_run_details(clean_run_id)
    resolved_template_id = (template_id or _run_template_id(run_payload)).strip()
    template = run_payload.get("template") if isinstance(run_payload.get("template"), dict) else {}
    template_title = str(template.get("title") or resolved_template_id)
    runtime_profile_handoff = _runtime_profile_handoff_from_run_payload(run_payload)
    if resolved_template_id == "god_of_carnage_solo" and not runtime_profile_handoff:
        raise GameServiceError(
            "Play run did not include runtime profile actor ownership required for god_of_carnage_solo.",
            status_code=502,
        )
    if selected_player_role and runtime_profile_handoff:
        handoff_role = str(runtime_profile_handoff.get("selected_player_role") or "").strip()
        if handoff_role and handoff_role != selected_player_role:
            raise GameServiceError(
                "Selected player role does not match the play run runtime profile handoff.",
                status_code=409,
            )
    module_id, runtime_projection, provenance = _compile_player_module(
        resolved_template_id,
        runtime_profile_handoff=runtime_profile_handoff,

    )
    provenance["run_id"] = clean_run_id
    trace_meta = _trace_classification(canonical_player_flow=True, runtime_mode="solo_story")
    effective_input_language = (session_input_language or session_output_language or _DEFAULT_OUTPUT_LANGUAGE).strip().lower()
    created = create_story_session(
        module_id=module_id,
        runtime_projection=runtime_projection,
        session_input_language=effective_input_language,
        session_output_language=session_output_language,
        user_id=str(user.id),
        trace_id=trace_id or g.get("trace_id"),
        langfuse_trace_id=langfuse_trace_id or g.get("langfuse_trace_id") or get_langfuse_trace_id(),
        trace_origin=str(trace_meta.get("trace_origin")),
        execution_tier=str(trace_meta.get("execution_tier")),
        canonical_player_flow=bool(trace_meta.get("canonical_player_flow")),
        test_case_id=trace_meta.get("test_case_id"),
        runtime_mode=str(trace_meta.get("runtime_mode")),
        content_provenance=provenance,
        skip_graph_opening_on_create=skip_graph_opening_on_create,
    )
    runtime_session_id = str(created.get("session_id") or "").strip()
    if not runtime_session_id:
        raise GameServiceError("World-Engine did not return a story session id.", status_code=502)
    _persist_player_session_binding(
        user,
        run_id=clean_run_id,
        template_id=resolved_template_id,
        template_title=template_title,
        module_id=module_id,
        runtime_session_id=runtime_session_id,
        session_input_language=effective_input_language,
        session_output_language=session_output_language,
    )
    state = get_story_state(runtime_session_id, trace_id=g.get("trace_id"))
    return _player_session_bundle(
        run_id=clean_run_id,
        template_id=resolved_template_id,
        module_id=module_id,
        runtime_session_id=runtime_session_id,
        state=state,
        created=created,
    )


'''
