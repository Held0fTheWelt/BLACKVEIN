"""Game routes implementation concern: error response and bootstrap helpers.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''



def _error_response(exc: Exception):
    if isinstance(exc, PermissionError):
        return jsonify({"error": str(exc)}), route_status_codes.unauthorized if "Authentication" in str(exc) else 403
    if isinstance(exc, NotFoundError):
        return jsonify({"error": str(exc)}), route_status_codes.not_found
    if isinstance(exc, (OwnershipError, ValidationError, GameContentValidationError)):
        return jsonify({"error": str(exc)}), route_status_codes.bad_request
    if isinstance(exc, GameContentNotFoundError):
        return jsonify({"error": str(exc)}), route_status_codes.not_found
    if isinstance(exc, GameContentConflictError):
        return jsonify({"error": str(exc)}), route_status_codes.conflict
    if isinstance(exc, GameContentLifecycleError):
        body: dict[str, Any] = {"error": str(exc)}
        if exc.code:
            body["code"] = exc.code
        if exc.content_lifecycle is not None:
            body["content_lifecycle"] = exc.content_lifecycle
        return jsonify(body), route_status_codes.conflict
    if isinstance(exc, GameServiceConfigError):
        return jsonify({"error": str(exc)}), exc.status_code
    if isinstance(exc, GameServiceError):
        body: dict[str, Any] = {"error": str(exc)}
        code = getattr(exc, "code", None)
        payload = getattr(exc, "payload", None)
        if code:
            body["code"] = code
        if isinstance(payload, dict):
            body.update(payload)
        return jsonify(body), exc.status_code
    return jsonify({"error": "Unexpected game launcher error."}), route_status_codes.internal_error



def _play_service_bootstrap() -> dict[str, Any]:
    play_public_url = (current_app.config.get("PLAY_SERVICE_PUBLIC_URL") or "").strip() or None
    configured = has_complete_play_service_config()
    ws_base_url = None
    if configured:
        try:
            ws_base_url = get_play_service_websocket_url()
        except GameServiceConfigError:
            configured = False
    return {
        "configured": configured,
        "public_url": play_public_url,
        "ws_base_url": ws_base_url,
    }



def _resolve_identity_context(user: User, payload: dict[str, Any]) -> GameIdentityContext:

    raw_character_id = payload.get("character_id")
    display_name = (payload.get("character_name") or payload.get("display_name") or user.username or "Player").strip()
    character_name = (payload.get("character_name") or None)
    character_id: str | None = None
    if raw_character_id not in (None, "", "null"):
        try:
            parsed_character_id = int(raw_character_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError("character_id must be a valid integer.") from exc
        character = get_character_for_user(user.id, parsed_character_id)
        display_name = character.display_name.strip() or character.name.strip() or display_name
        character_name = character.name.strip()
        character_id = str(character.id)
    return GameIdentityContext(
        display_name=display_name,
        character_id=character_id,
        character_name=character_name,
    )
'''
