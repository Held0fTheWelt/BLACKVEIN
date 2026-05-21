"""Game routes implementation concern: player session resume and opening routes.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/player-sessions/<run_id>", methods=["GET"])
@limiter.limit("60 per minute")
def game_player_session_resume(run_id: str):
    """Resume the canonical player story session by run id."""
    try:
        user = _require_game_user()
        bundle = _ensure_player_session(user, run_id=run_id)
        return jsonify(bundle), route_status_codes.ok

    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/player-sessions/<run_id>/opening", methods=["POST"])
@limiter.limit("20 per minute")
def game_player_session_opening(run_id: str):
    """Generate the delayed opening for a fast-created player story session."""
    try:
        user = _require_game_user()
        bundle = _ensure_player_session(user, run_id=run_id)
        if bundle.get("opening_present"):
            return jsonify(bundle), route_status_codes.ok

        runtime_session_id = str(bundle.get("runtime_session_id") or "").strip()
        if not runtime_session_id:
            raise GameServiceError("Canonical player session is not ready.", status_code=502)

        trace_id = g.get("trace_id")
        langfuse_trace_id = g.get("langfuse_trace_id") or get_langfuse_trace_id()
        trace_meta = _trace_classification(canonical_player_flow=True, runtime_mode="solo_story")
        opening_payload = execute_story_opening(
            session_id=runtime_session_id,
            trace_id=trace_id,
            langfuse_trace_id=langfuse_trace_id,
            trace_origin=str(trace_meta.get("trace_origin")),
            execution_tier=str(trace_meta.get("execution_tier")),
            canonical_player_flow=bool(trace_meta.get("canonical_player_flow")),
            test_case_id=trace_meta.get("test_case_id"),
            runtime_mode=str(trace_meta.get("runtime_mode")),
        )
        opening_turn = opening_payload.get("turn") if isinstance(opening_payload.get("turn"), dict) else None
        state = get_story_state(runtime_session_id, trace_id=trace_id)
        refreshed = _player_session_bundle(
            run_id=run_id,
            template_id=str(bundle.get("template_id") or ""),
            module_id=str(bundle.get("module_id") or ""),
            runtime_session_id=runtime_session_id,
            state=state,
            turn=opening_turn,
            created={
                "opening_turn": opening_turn,
                "session_loop": bundle.get("session_loop"),
            },
        )
        return jsonify(refreshed), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


'''
