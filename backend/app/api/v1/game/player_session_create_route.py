"""Game routes implementation concern: player session create route.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
@api_v1_bp.route("/game/player-sessions", methods=["POST"])
@limiter.limit("20 per minute")
def game_player_session_create():
    """Create or resume the canonical player story session for a play run."""
    try:
        user = _require_game_user()
        data = request.get_json(silent=True) or {}

        if not isinstance(data, dict):
            return jsonify({"error": "JSON body must be an object."}), route_status_codes.bad_request
        run_id = (data.get("run_id") or "").strip()
        template_id = (data.get("template_id") or "").strip()
        trace_id = (data.get("trace_id") or "").strip() or g.get("trace_id")
        langfuse_trace_id = g.get("langfuse_trace_id") or get_langfuse_trace_id()
        run_payload: dict[str, Any] | None = None
        runtime_profile_id = (data.get("runtime_profile_id") or "").strip() or None
        selected_player_role = (data.get("selected_player_role") or "").strip() or None
        skip_graph_opening_on_create = bool(data.get("skip_graph_opening_on_create"))
        raw_language = data.get("session_output_language")
        if raw_language is not None and not isinstance(raw_language, str):
            return jsonify({"error": "session_output_language must be a string.", "code": "invalid_output_language"}), route_status_codes.bad_request
        session_output_language = (raw_language or "").strip().lower() or _DEFAULT_OUTPUT_LANGUAGE
        if session_output_language not in _ALLOWED_OUTPUT_LANGUAGES:
            return jsonify({
                "error": f"session_output_language {raw_language!r} is not supported.",
                "code": "unsupported_language",
                "allowed": sorted(_ALLOWED_OUTPUT_LANGUAGES),
            }), route_status_codes.bad_request
        raw_input_language = data.get("session_input_language")
        if raw_input_language is not None and not isinstance(raw_input_language, str):
            return jsonify({"error": "session_input_language must be a string.", "code": "invalid_input_language"}), route_status_codes.bad_request
        session_input_language = (raw_input_language or "").strip().lower() or session_output_language
        if session_input_language not in _ALLOWED_OUTPUT_LANGUAGES:
            return jsonify({
                "error": f"session_input_language {raw_input_language!r} is not supported.",
                "code": "unsupported_input_language",
                "allowed": sorted(_ALLOWED_OUTPUT_LANGUAGES),
            }), route_status_codes.bad_request
        if not run_id:
            if not template_id and not runtime_profile_id:
                return jsonify({"error": "template_id, runtime_profile_id, or run_id is required."}), route_status_codes.bad_request
            identity = _resolve_identity_context(user, data)
            run_payload = create_play_run(
                template_id=template_id or None,
                account_id=str(user.id),
                character_id=identity["character_id"],
                display_name=identity["display_name"],
                runtime_profile_id=runtime_profile_id,
                selected_player_role=selected_player_role,
                trace_id=trace_id,
                langfuse_trace_id=langfuse_trace_id,
            )
            run_id = _run_id(run_payload)
            if identity["character_id"]:
                touch_character_last_used(user.id, int(identity["character_id"]))
        bundle = _ensure_player_session(
            user,
            run_id=run_id,
            template_id=template_id or None,
            run_payload=run_payload,
            trace_id=trace_id,
            langfuse_trace_id=langfuse_trace_id,
            selected_player_role=selected_player_role,
            session_input_language=session_input_language,
            session_output_language=session_output_language,
            skip_graph_opening_on_create=skip_graph_opening_on_create,
        )
        return jsonify(bundle), route_status_codes.ok
'''
