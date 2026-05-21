"""Game routes implementation concern: content governance review routes.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''

@api_v1_bp.route("/game/content/experiences/<int:experience_id>/governance/submit-review", methods=["POST"])
@require_jwt_moderator_or_admin
def game_content_governance_submit_review(experience_id: int):
    try:
        user = _current_user()
        data = request.get_json(silent=True) or {}
        note = data.get("note") if isinstance(data.get("note"), str) else None
        experience = submit_experience_for_review(
            experience_id,
            actor_user_id=user.id if user else None,
            note=note,
        )
        return jsonify({"experience": experience}), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/content/experiences/<int:experience_id>/governance/decision", methods=["POST"])
@require_jwt_moderator_or_admin
def game_content_governance_decision(experience_id: int):
    try:
        user = _current_user()
        data = request.get_json(silent=True) or {}
        decision = data.get("decision")
        if not isinstance(decision, str) or not decision.strip():
            return jsonify({"error": "decision is required"}), route_status_codes.bad_request
        note = data.get("note") if isinstance(data.get("note"), str) else None
        experience = apply_editorial_decision(
            experience_id,
            decision=decision.strip(),
            actor_user_id=user.id if user else None,

            note=note,
        )
        return jsonify({"experience": experience}), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


'''
