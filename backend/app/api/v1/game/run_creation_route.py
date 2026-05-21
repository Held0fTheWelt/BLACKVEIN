"""Game routes implementation concern: run creation route.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
@api_v1_bp.route("/game/runs", methods=["POST"])
@limiter.limit("20 per minute")
def game_create_run():
    try:
        user = _require_game_user()
        data = request.get_json(silent=True) or {}
        template_id = (data.get("template_id") or "").strip() or None
        runtime_profile_id = (data.get("runtime_profile_id") or "").strip() or None
        selected_player_role = (data.get("selected_player_role") or "").strip() or None
        if not template_id and not runtime_profile_id:
            return jsonify({"error": "template_id or runtime_profile_id is required."}), route_status_codes.bad_request
        _PROFILE_ONLY_TEMPLATES = {"god_of_carnage_solo"}
        if template_id in _PROFILE_ONLY_TEMPLATES and not runtime_profile_id:
            return jsonify({
                "error": f"{template_id!r} must be started via runtime_profile_id with selected_player_role.",
                "code": "runtime_profile_required",
                "hint": f"Set runtime_profile_id={template_id!r} and selected_player_role=annette|alain.",
            }), route_status_codes.bad_request
        identity = _resolve_identity_context(user, data)
        trace_id = g.get("trace_id")
        langfuse_trace_id = g.get("langfuse_trace_id") or get_langfuse_trace_id()
        result = create_play_run(
            template_id=template_id,
            account_id=str(user.id),
            character_id=identity["character_id"],
            display_name=identity["display_name"],
            runtime_profile_id=runtime_profile_id,
            selected_player_role=selected_player_role,
            trace_id=trace_id,
            langfuse_trace_id=langfuse_trace_id,
        )
        if identity["character_id"]:
            touch_character_last_used(user.id, int(identity["character_id"]))
        return jsonify(result), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


'''
