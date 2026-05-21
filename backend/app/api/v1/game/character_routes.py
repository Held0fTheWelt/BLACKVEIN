"""Game routes implementation concern: character routes.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''

@api_v1_bp.route("/game/characters", methods=["GET"])
@limiter.limit("60 per minute")
def game_characters_list():
    try:
        user = _require_game_user()
        return jsonify({"characters": [c.to_dict() for c in list_characters_for_user(user.id)]})
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/characters", methods=["POST"])
@limiter.limit("20 per minute")

def game_characters_create():
    try:
        user = _require_game_user()
        data = request.get_json(silent=True) or {}
        character = create_character_for_user(
            user,
            name=data.get("name") or "",
            display_name=data.get("display_name"),
            bio=data.get("bio"),
            is_default=bool(data.get("is_default")),
        )
        return jsonify({"character": character.to_dict()}), route_status_codes.created
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/characters/<int:character_id>", methods=["PATCH"])
@limiter.limit("20 per minute")
def game_characters_update(character_id: int):
    try:
        user = _require_game_user()
        data = request.get_json(silent=True) or {}
        character = update_character_for_user(
            user.id,
            character_id,
            name=data.get("name"),
            display_name=data.get("display_name"),
            bio=data.get("bio"),
            is_default=data.get("is_default"),
            is_archived=data.get("is_archived"),
        )
        return jsonify({"character": character.to_dict()}), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/characters/<int:character_id>", methods=["DELETE"])
@limiter.limit("20 per minute")
def game_characters_delete(character_id: int):
    try:
        user = _require_game_user()
        character = update_character_for_user(user.id, character_id, is_archived=True)
        return jsonify({"character": character.to_dict(), "archived": True}), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)

'''
