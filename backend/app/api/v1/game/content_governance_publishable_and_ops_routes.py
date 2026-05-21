"""Game routes implementation concern: content governance publishable and ops routes.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
@api_v1_bp.route("/game/content/experiences/<int:experience_id>/governance/mark-publishable", methods=["POST"])
@require_jwt_moderator_or_admin
def game_content_governance_mark_publishable(experience_id: int):
    try:
        user = _current_user()
        data = request.get_json(silent=True) or {}
        note = data.get("note") if isinstance(data.get("note"), str) else None
        experience = mark_experience_publishable(
            experience_id,
            actor_user_id=user.id if user else None,
            note=note,
        )
        return jsonify({"experience": experience}), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/ops/runs", methods=["GET"])
@require_jwt_moderator_or_admin
def game_ops_runs():
    try:
        return jsonify({"runs": list_play_runs()})
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/ops/runs/<run_id>", methods=["GET"])
@require_jwt_moderator_or_admin
def game_ops_run_detail(run_id: str):
    try:
        return jsonify(get_play_run_details(run_id))
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/ops/runs/<run_id>/transcript", methods=["GET"])
@require_jwt_moderator_or_admin
def game_ops_run_transcript(run_id: str):
    try:
        return jsonify(get_play_run_transcript(run_id))
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/ops/runs/<run_id>/terminate", methods=["POST"])
@require_jwt_moderator_or_admin
def game_ops_run_terminate(run_id: str):
    try:
        actor = _current_user()
        actor_name = (actor.username if actor else "moderator").strip() or "moderator"
        return jsonify(
            terminate_play_run(run_id, actor_display_name=actor_name, reason="game_ops_terminate"),
        )
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)
'''
