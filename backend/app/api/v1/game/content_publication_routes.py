"""Game routes implementation concern: content publication routes.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''

@api_v1_bp.route("/game/content/experiences/<int:experience_id>", methods=["PATCH"])
@require_jwt_moderator_or_admin
def game_content_update(experience_id: int):
    try:
        user = _current_user()
        data = request.get_json(silent=True) or {}
        payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
        experience = update_experience(experience_id, payload=payload, actor_user_id=user.id if user else None)
        return jsonify({"experience": experience}), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/content/experiences/<int:experience_id>/publish", methods=["POST"])
@require_jwt_moderator_or_admin
def game_content_publish(experience_id: int):
    try:
        user = _current_user()
        experience = publish_experience(experience_id, actor_user_id=user.id if user else None)
        return jsonify({"experience": experience}), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/content/experiences/<int:experience_id>/unpublish", methods=["POST"])
@require_jwt_moderator_or_admin
def game_content_unpublish(experience_id: int):
    try:
        user = _current_user()
        data = request.get_json(silent=True) or {}
        note = data.get("note") if isinstance(data.get("note"), str) else None
        experience = unpublish_experience(
            experience_id,
            actor_user_id=user.id if user else None,
            note=note,
        )
        return jsonify({"experience": experience}), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)

'''
