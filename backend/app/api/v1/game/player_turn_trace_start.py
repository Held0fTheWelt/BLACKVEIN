"""Game routes implementation concern: player turn trace start.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
@api_v1_bp.route("/game/player-sessions/<run_id>/turns", methods=["POST"])
@limiter.limit("30 per minute")
def game_player_session_turn(run_id: str):
    """Execute a player turn through the authoritative World-Engine story runtime."""
    try:
        user = _require_game_user()
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "JSON body must be an object."}), route_status_codes.bad_request
        player_input = str(data.get("player_input") or data.get("input") or "").strip()
        if not player_input:
            return jsonify({"error": "player_input is required."}), route_status_codes.bad_request
        bundle = _ensure_player_session(user, run_id=run_id)
        runtime_session_id = str(bundle.get("runtime_session_id") or "").strip()
        if not runtime_session_id:
            raise GameServiceError("Canonical player session is not ready.", status_code=502)

        trace_id = g.get("trace_id")
        langfuse_trace_id = g.get("langfuse_trace_id") or get_langfuse_trace_id()
        trace_meta = _trace_classification(canonical_player_flow=True, runtime_mode="solo_story")
        adapter = LangfuseAdapter.get_instance()
        root_span = None

        player_input_sha256 = hashlib.sha256(player_input.encode("utf-8")).hexdigest()

        try:
            # Langfuse sessionId must match world-engine story session id so opening + turns
            # group under the same session view; keep play run id as run_id for correlation.
            root_span = adapter.start_trace(
                name="backend.turn.execute",
                session_id=runtime_session_id,
                run_id=run_id,
                module_id=str(bundle.get("module_id") or ""),
                metadata={
                    "wos_trace_id": trace_id,
                    "langfuse_trace_id": langfuse_trace_id,
                    "play_run_id": run_id,
                    "world_engine_story_session_id": runtime_session_id,
                    "player_input_length": len(player_input),
                    "player_input_sha256": player_input_sha256,
                    "stage": "turn_execution",
                    "route": "/game/player-sessions/<run_id>/turns",
                    **trace_meta,
                },
                trace_id=langfuse_trace_id,
                user_id=str(user.id),
            )

'''
