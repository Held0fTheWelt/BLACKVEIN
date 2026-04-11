from __future__ import annotations

from typing import Any

from flask import current_app, jsonify, request, session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from app.api.v1 import api_v1_bp
from app.auth.permissions import require_jwt_moderator_or_admin
from app.extensions import db, limiter
from app.models import User
from app.services.game_content_service import (
    GameContentConflictError,
    GameContentLifecycleError,
    GameContentNotFoundError,
    GameContentValidationError,
    apply_editorial_decision,
    create_experience,
    get_experience,
    list_experiences,
    list_published_experience_payloads,
    mark_experience_publishable,
    publish_experience,
    submit_experience_for_review,
    unpublish_experience,
    update_experience,
)
from app.services.game_profile_service import (
    NotFoundError,
    OwnershipError,
    ValidationError,
    create_character_for_user,
    get_character_for_user,
    list_characters_for_user,
    list_save_slots_for_user,
    touch_character_last_used,
    update_character_for_user,
    upsert_save_slot_for_user,
    delete_save_slot_for_user,
)
from app.services.game_service import (
    GameServiceConfigError,
    GameServiceError,
    create_run as create_play_run,
    get_run_details as get_play_run_details,
    get_run_transcript as get_play_run_transcript,
    terminate_run as terminate_play_run,
    get_play_service_websocket_url,
    has_complete_play_service_config,
    issue_play_ticket,
    list_runs as list_play_runs,
    list_templates as list_play_templates,
    resolve_join_context,
)


class GameIdentityContext(dict):
    display_name: str
    character_id: str | None
    character_name: str | None



def _current_user() -> User | None:
    uid = session.get("user_id")
    if uid is not None:
        return db.session.get(User, int(uid))
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        return None
    uid = get_jwt_identity()
    if uid is None:
        return None
    return db.session.get(User, int(uid))



def _require_game_user() -> User:
    user = _current_user()
    if user is None:
        raise PermissionError("Authentication required.")
    if getattr(user, "is_banned", False):
        raise PermissionError("Account is restricted.")
    return user



def _error_response(exc: Exception):
    if isinstance(exc, PermissionError):
        return jsonify({"error": str(exc)}), 401 if "Authentication" in str(exc) else 403
    if isinstance(exc, NotFoundError):
        return jsonify({"error": str(exc)}), 404
    if isinstance(exc, (OwnershipError, ValidationError, GameContentValidationError)):
        return jsonify({"error": str(exc)}), 400
    if isinstance(exc, GameContentNotFoundError):
        return jsonify({"error": str(exc)}), 404
    if isinstance(exc, GameContentConflictError):
        return jsonify({"error": str(exc)}), 409
    if isinstance(exc, GameContentLifecycleError):
        body: dict[str, Any] = {"error": str(exc)}
        if exc.code:
            body["code"] = exc.code
        if exc.content_lifecycle is not None:
            body["content_lifecycle"] = exc.content_lifecycle
        return jsonify(body), 409
    if isinstance(exc, GameServiceConfigError):
        return jsonify({"error": str(exc)}), exc.status_code
    if isinstance(exc, GameServiceError):
        return jsonify({"error": str(exc)}), exc.status_code
    return jsonify({"error": "Unexpected game launcher error."}), 500



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



def _parse_optional_int(raw_value: Any, *, field_name: str) -> int | None:
    if raw_value in (None, "", "null"):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a valid integer.") from exc


def _serialize_template_catalog(templates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: list[dict[str, Any]] = []
    for template in templates:
        kind = template.get("kind") or "unknown"
        grouped.append(
            {
                "id": template.get("id"),
                "title": template.get("title") or template.get("id") or "Untitled",
                "kind": kind,
                "kind_label": {
                    "solo_story": "Solo Story",
                    "group_story": "Group Story",
                    "open_world": "Open World",
                }.get(kind, kind.replace("_", " ").title()),
            }
        )
    return grouped


def _builtin_play_template_dicts() -> list[dict[str, Any]]:
    """Fallback catalog for the play launcher when the world-engine list is empty or play is not configured."""
    from app.content.builtins import load_builtin_templates

    out: list[dict[str, Any]] = []
    for tmpl in load_builtin_templates().values():
        d = tmpl.model_dump(mode="json")
        out.append({"id": d["id"], "title": d["title"], "kind": d["kind"]})
    return out


@api_v1_bp.route("/game/bootstrap", methods=["GET"])
@limiter.limit("60 per minute")
def game_bootstrap():
    try:
        user = _require_game_user()
        play_service = _play_service_bootstrap()
        templates: list[dict[str, Any]] = []
        runs: list[dict[str, Any]] = []
        if play_service["configured"]:
            try:
                templates = list_play_templates()
            except GameServiceError:
                templates = []
            try:
                runs = list_play_runs()
            except GameServiceError:
                runs = []
        if not templates:
            templates = _builtin_play_template_dicts()
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
        try:
            raw = list_play_templates()
        except GameServiceError:
            raw = []
        if not raw:
            raw = _builtin_play_template_dicts()
        return jsonify({"templates": _serialize_template_catalog(raw)})
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


@api_v1_bp.route("/game/runs", methods=["POST"])
@limiter.limit("20 per minute")
def game_create_run():
    try:
        user = _require_game_user()
        data = request.get_json(silent=True) or {}
        template_id = (data.get("template_id") or "").strip()
        if not template_id:
            return jsonify({"error": "template_id is required."}), 400
        identity = _resolve_identity_context(user, data)
        result = create_play_run(
            template_id=template_id,
            account_id=str(user.id),
            character_id=identity["character_id"],
            display_name=identity["display_name"],
        )
        if identity["character_id"]:
            touch_character_last_used(user.id, int(identity["character_id"]))
        return jsonify(result), 200
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/tickets", methods=["POST"])
@limiter.limit("30 per minute")
def game_create_ticket():
    try:
        user = _require_game_user()
        data = request.get_json(silent=True) or {}
        run_id = (data.get("run_id") or "").strip()
        if not run_id:
            return jsonify({"error": "run_id is required."}), 400

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
        ), 200
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


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
        return jsonify({"character": character.to_dict()}), 201
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
        return jsonify({"character": character.to_dict()}), 200
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/characters/<int:character_id>", methods=["DELETE"])
@limiter.limit("20 per minute")
def game_characters_delete(character_id: int):
    try:
        user = _require_game_user()
        character = update_character_for_user(user.id, character_id, is_archived=True)
        return jsonify({"character": character.to_dict(), "archived": True}), 200
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


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
        return jsonify({"save_slot": slot.to_dict()}), 200
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/save-slots/<int:slot_id>", methods=["DELETE"])
@limiter.limit("20 per minute")
def game_save_slots_delete(slot_id: int):
    try:
        user = _require_game_user()
        delete_save_slot_for_user(user.id, slot_id)
        return jsonify({"deleted": True, "slot_id": slot_id}), 200
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/content/published", methods=["GET"])
@limiter.limit("60 per minute")
def game_published_content_feed():
    try:
        return jsonify({"templates": list_published_experience_payloads()})
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/content/experiences", methods=["GET"])
@require_jwt_moderator_or_admin
def game_content_list():
    try:
        lifecycle = (request.args.get("lifecycle") or "").strip() or None
        return jsonify(
            {"experiences": list_experiences(include_payload=True, lifecycle=lifecycle)}
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
        return jsonify({"experience": experience}), 201
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/content/experiences/<int:experience_id>", methods=["GET"])
@require_jwt_moderator_or_admin
def game_content_get(experience_id: int):
    try:
        return jsonify({"experience": get_experience(experience_id, include_payload=True)})
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/content/experiences/<int:experience_id>", methods=["PATCH"])
@require_jwt_moderator_or_admin
def game_content_update(experience_id: int):
    try:
        user = _current_user()
        data = request.get_json(silent=True) or {}
        payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
        experience = update_experience(experience_id, payload=payload, actor_user_id=user.id if user else None)
        return jsonify({"experience": experience}), 200
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/content/experiences/<int:experience_id>/publish", methods=["POST"])
@require_jwt_moderator_or_admin
def game_content_publish(experience_id: int):
    try:
        user = _current_user()
        experience = publish_experience(experience_id, actor_user_id=user.id if user else None)
        return jsonify({"experience": experience}), 200
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
        return jsonify({"experience": experience}), 200
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


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
        return jsonify({"experience": experience}), 200
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
            return jsonify({"error": "decision is required"}), 400
        note = data.get("note") if isinstance(data.get("note"), str) else None
        experience = apply_editorial_decision(
            experience_id,
            decision=decision.strip(),
            actor_user_id=user.id if user else None,
            note=note,
        )
        return jsonify({"experience": experience}), 200
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


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
        return jsonify({"experience": experience}), 200
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
