"""Game routes implementation concern: ticket routes.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
@api_v1_bp.route("/game/tickets", methods=["POST"])
@limiter.limit("30 per minute")
def game_create_ticket():
    try:
        user = _require_game_user()
        data = request.get_json(silent=True) or {}
        run_id = (data.get("run_id") or "").strip()
        if not run_id:
            return jsonify({"error": "run_id is required."}), route_status_codes.bad_request

        identity = _resolve_identity_context(user, data)
        preferred_role_id = (data.get("preferred_role_id") or None)

        join = resolve_join_context(
            run_id=run_id,
            account_id=str(user.id),
            character_id=identity["character_id"],
            display_name=identity["display_name"],
            preferred_role_id=preferred_role_id,
        )
        ticket = issue_play_ticket(
            {
                "run_id": join.run_id,
                "participant_id": join.participant_id,
                "account_id": str(user.id),
                "character_id": identity["character_id"],
                "display_name": join.display_name,
                "role_id": join.role_id,
            }
        )
        if identity["character_id"]:
            touch_character_last_used(user.id, int(identity["character_id"]))
        return jsonify(
            {
                "ticket": ticket,
                "run_id": join.run_id,
                "participant_id": join.participant_id,
                "role_id": join.role_id,
                "display_name": join.display_name,
                "character_id": identity["character_id"],
                "ws_base_url": get_play_service_websocket_url(),
            }
        ), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)

'''
