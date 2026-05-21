"""Game routes implementation concern: content feed and editor routes.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''


@api_v1_bp.route("/game/content/experiences", methods=["GET"])
@require_jwt_moderator_or_admin
def game_content_list():
    try:
        lifecycle = (request.args.get("lifecycle") or "").strip() or None
        status = (request.args.get("status") or "").strip() or None
        return jsonify(
            {
                "experiences": list_experiences(
                    include_payload=True, lifecycle=lifecycle, status=status
                )
            }
        )
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/content/experiences", methods=["POST"])
@require_jwt_moderator_or_admin
def game_content_create():
    try:
        user = _current_user()
        data = request.get_json(silent=True) or {}
        payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
        gov = data.get("governance_provenance") if isinstance(data.get("governance_provenance"), dict) else None
        experience = create_experience(
            payload=payload,
            actor_user_id=user.id if user else None,
            governance_provenance=gov,
        )
        return jsonify({"experience": experience}), route_status_codes.created
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/content/experiences/<int:experience_id>", methods=["GET"])
@require_jwt_moderator_or_admin
def game_content_get(experience_id: int):
    try:
        return jsonify({"experience": get_experience(experience_id, include_payload=True)})
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


'''
