"""Game routes implementation concern: bootstrap template and run list routes.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
@api_v1_bp.route("/game/bootstrap", methods=["GET"])
@limiter.limit("60 per minute")
def game_bootstrap():
    try:
        user = _require_game_user()
        play_service = _play_service_bootstrap()
        runs: list[dict[str, Any]] = []
        templates, template_diagnostic = _template_catalog_from_runtime_or_fallback(
            play_service_configured=bool(play_service["configured"])
        )
        play_service["template_catalog"] = template_diagnostic
        if play_service["configured"]:
            try:
                runs = list_play_runs()
            except GameServiceError as exc:
                runs = []
                play_service["runs_degraded"] = True
                play_service["runs_error"] = str(exc)
        characters = [character.to_dict() for character in list_characters_for_user(user.id)]
        save_slots = [slot.to_dict() for slot in list_save_slots_for_user(user.id)]
        return jsonify(
            {
                "profile": {
                    "account_id": str(user.id),
                    "username": user.username,
                    "default_display_name": user.username,
                },
                "play_service": play_service,
                "templates": _serialize_template_catalog(templates),
                "runs": runs,
                "characters": characters,
                "save_slots": save_slots,
            }
        )

    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/templates", methods=["GET"])
@limiter.limit("60 per minute")
def game_templates():
    try:
        _require_game_user()
        raw, diagnostic = _template_catalog_from_runtime_or_fallback(
            play_service_configured=has_complete_play_service_config()
        )
        return jsonify({"templates": _serialize_template_catalog(raw), "template_catalog": diagnostic})
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/runs", methods=["GET"])
@limiter.limit("60 per minute")
def game_runs():
    try:
        _require_game_user()
        return jsonify({"runs": list_play_runs()})
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


'''
