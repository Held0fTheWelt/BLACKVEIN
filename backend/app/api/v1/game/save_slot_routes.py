"""Game routes implementation concern: save slot routes.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''

@api_v1_bp.route("/game/save-slots", methods=["GET"])
@limiter.limit("60 per minute")
def game_save_slots_list():
    try:
        user = _require_game_user()
        return jsonify({"save_slots": [slot.to_dict() for slot in list_save_slots_for_user(user.id)]})
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/save-slots", methods=["POST"])
@limiter.limit("20 per minute")
def game_save_slots_upsert():
    try:
        user = _require_game_user()
        data = request.get_json(silent=True) or {}
        slot = upsert_save_slot_for_user(
            user.id,
            slot_key=data.get("slot_key") or "",
            title=data.get("title") or "",
            template_id=data.get("template_id") or "",
            template_title=data.get("template_title"),
            run_id=data.get("run_id"),
            kind=data.get("kind"),
            status=data.get("status"),

            character_id=_parse_optional_int(data.get("character_id"), field_name="character_id"),
            metadata=data.get("metadata") if isinstance(data.get("metadata"), dict) else None,
        )
        return jsonify({"save_slot": slot.to_dict()}), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/save-slots/<int:slot_id>", methods=["DELETE"])
@limiter.limit("20 per minute")
def game_save_slots_delete(slot_id: int):
    try:
        user = _require_game_user()
        delete_save_slot_for_user(user.id, slot_id)
        return jsonify({"deleted": True, "slot_id": slot_id}), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/content/published", methods=["GET"])
@limiter.limit("60 per minute")
def game_published_content_feed():
    try:
        return jsonify({"templates": list_published_experience_payloads()})
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)
'''
