from __future__ import annotations

import hashlib
from typing import Any

from flask import current_app, g, jsonify, request, session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from sqlalchemy import select

from app.api.v1 import api_v1_bp
from app.auth.permissions import require_jwt_moderator_or_admin
from app.content.compiler import compile_module
from app.content.module_exceptions import ModuleLoadError
from app.extensions import db, limiter
from app.models import GameSaveSlot, User
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
    resolve_canonical_module_id_for_template,
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
    create_story_session,
    execute_story_turn as execute_story_turn_in_engine,
    get_run_details as get_play_run_details,
    get_run_transcript as get_play_run_transcript,
    get_story_state,
    terminate_run as terminate_play_run,
    get_play_service_websocket_url,
    has_complete_play_service_config,
    issue_play_ticket,
    list_runs as list_play_runs,
    list_templates as list_play_templates,
    resolve_join_context,
)
from app.observability.langfuse_adapter import LangfuseAdapter
from app.observability.trace import get_langfuse_trace_id
from app.config.route_constants import route_status_codes, route_pagination_config


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
        return jsonify({"error": str(exc)}), exc.status_code
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



def _player_session_slot_key(run_id: str) -> str:
    digest = hashlib.sha1(run_id.encode("utf-8")).hexdigest()[:24]
    return f"player-{digest}"


def _find_player_session_slot(user_id: int, run_id: str) -> GameSaveSlot | None:
    return db.session.scalar(
        select(GameSaveSlot).where(
            GameSaveSlot.user_id == user_id,
            GameSaveSlot.slot_key == _player_session_slot_key(run_id),
        )
    )


def _run_template_id(payload: dict[str, Any]) -> str:
    run = payload.get("run") if isinstance(payload.get("run"), dict) else {}
    template = payload.get("template") if isinstance(payload.get("template"), dict) else {}
    template_id = str(run.get("template_id") or template.get("id") or payload.get("template_id") or "").strip()
    if not template_id:
        raise GameServiceError("Play run did not include a template id.", status_code=502)
    return template_id


def _run_id(payload: dict[str, Any]) -> str:
    run = payload.get("run") if isinstance(payload.get("run"), dict) else {}
    run_id = str(run.get("id") or payload.get("run_id") or "").strip()
    if not run_id:
        raise GameServiceError("Play run did not include a run id.", status_code=502)
    return run_id


def _story_window_from_state(state: dict[str, Any]) -> dict[str, Any]:
    story_window = state.get("story_window") if isinstance(state.get("story_window"), dict) else {}
    entries = story_window.get("entries") if isinstance(story_window.get("entries"), list) else []
    return {
        "contract": story_window.get("contract") or "authoritative_story_window_v1",
        "source": story_window.get("source") or "world_engine_story_runtime",
        "entries": entries,
        "entry_count": len(entries),
        "latest_entry": entries[-1] if entries else None,
    }


def _player_shell_state_view(
    *,
    state: dict[str, Any],
    run_id: str,
    template_id: str,
    module_id: str,
    runtime_session_id: str,
) -> dict[str, Any]:
    committed = state.get("committed_state") if isinstance(state.get("committed_state"), dict) else {}
    player_shell_context = committed.get("player_shell_context")
    if not isinstance(player_shell_context, dict):
        player_shell_context = state.get("player_shell_context") if isinstance(state.get("player_shell_context"), dict) else {}
    module_scope_truth = committed.get("module_scope_truth")
    if not isinstance(module_scope_truth, dict):
        module_scope_truth = state.get("module_scope_truth") if isinstance(state.get("module_scope_truth"), dict) else {}
    return {
        "run_id": run_id,
        "template_id": template_id,
        "module_id": module_id,
        "runtime_session_id": runtime_session_id,
        "turn_counter": state.get("turn_counter"),
        "current_scene_id": state.get("current_scene_id"),
        "history_count": state.get("history_count"),
        "last_narrative_commit_summary": committed.get("last_narrative_commit_summary"),
        "last_committed_consequences": committed.get("last_committed_consequences") or [],
        "last_open_pressures": committed.get("last_open_pressures") or [],
        "player_shell_context": player_shell_context,
        "module_scope_truth": module_scope_truth,
    }


def _player_session_bundle(
    *,
    run_id: str,
    template_id: str,
    module_id: str,
    runtime_session_id: str,
    state: dict[str, Any],
    created: dict[str, Any] | None = None,
    turn: dict[str, Any] | None = None,
) -> dict[str, Any]:
    story_window = _story_window_from_state(state)
    latest_turn = turn if isinstance(turn, dict) else None
    opening_turn = created.get("opening_turn") if isinstance(created, dict) and isinstance(created.get("opening_turn"), dict) else None
    if latest_turn is None:
        latest_turn = state.get("last_committed_turn") if isinstance(state.get("last_committed_turn"), dict) else None
    latest_governance = (
        latest_turn.get("runtime_governance_surface")
        if isinstance(latest_turn, dict) and isinstance(latest_turn.get("runtime_governance_surface"), dict)
        else None
    )
    narrator_streaming = None
    if isinstance(latest_turn, dict) and isinstance(latest_turn.get("narrator_streaming"), dict):
        narrator_streaming = latest_turn.get("narrator_streaming")
    elif isinstance(opening_turn, dict) and isinstance(opening_turn.get("narrator_streaming"), dict):
        narrator_streaming = opening_turn.get("narrator_streaming")
    # Contract 3: can_execute must match story_window.entry_count
    # Opening turn exists when entry_count > 0
    can_execute = story_window.get("entry_count", 0) > 0
    return {
        "contract": "game_player_session_v1",
        "run_id": run_id,
        "template_id": template_id,
        "module_id": module_id,
        "ticket_id": None,
        "backend_session_id": None,
        "runtime_session_id": runtime_session_id,
        "world_engine_story_session_id": runtime_session_id,
        "runtime_session_ready": True,
        "can_execute": can_execute,
        "story_window": story_window,
        "story_entries": story_window["entries"],
        "narrator_streaming": narrator_streaming,
        "shell_state_view": _player_shell_state_view(
            state=state,
            run_id=run_id,
            template_id=template_id,
            module_id=module_id,
            runtime_session_id=runtime_session_id,
        ),
        "authoritative_state": state,
        "turn": latest_turn,
        "opening_turn": opening_turn,
        "governance": {
            "runtime_governance_surface": latest_governance,
            "runtime_config_status": created.get("runtime_config_status") if isinstance(created, dict) else None,
            "content_publication_gate": "published_game_content_required_for_template_module_binding",
            "player_path_governed_by": [
                "game content publication lifecycle",
                "world-engine governed runtime config",
                "runtime validation and guardrails",
            ],
        },
        "identifier_model": {
            "template_id": "launcher/content template selection",
            "module_id": "compiled runtime module for story execution",
            "run_id": "player launch and continuity handle",
            "ticket_id": "not used by canonical HTTP story player path",
            "backend_session_id": "not used by canonical player path",
            "runtime_session_id": "world-engine story session id",
        },
    }


def _persist_player_session_binding(
    user: User,
    *,
    run_id: str,
    template_id: str,
    template_title: str | None,
    module_id: str,
    runtime_session_id: str,
) -> GameSaveSlot:
    return upsert_save_slot_for_user(
        user.id,
        slot_key=_player_session_slot_key(run_id),
        title=template_title or f"Play session {run_id}",
        template_id=template_id,
        template_title=template_title,
        run_id=run_id,
        kind="canonical_player_session",
        status="active",
        metadata={
            "contract": "game_player_session_v1",
            "module_id": module_id,
            "runtime_session_id": runtime_session_id,
            "world_engine_story_session_id": runtime_session_id,
            "continuity_owner": "backend_game_player_session_bridge",
        },
    )


_RUNTIME_HANDOFF_FIELDS = (
    "content_module_id",
    "runtime_profile_id",
    "runtime_module_id",
    "runtime_mode",
    "selected_player_role",
    "human_actor_id",
    "npc_actor_ids",
    "actor_lanes",
    "visitor_present",
    "content_hash",
)


def _runtime_profile_handoff_from_run_payload(run_payload: dict[str, Any]) -> dict[str, Any]:
    handoff = {key: run_payload.get(key) for key in _RUNTIME_HANDOFF_FIELDS if key in run_payload}
    if not handoff:
        return {}

    required = (
        "content_module_id",
        "runtime_profile_id",
        "runtime_module_id",
        "selected_player_role",
        "human_actor_id",
        "npc_actor_ids",
        "actor_lanes",
    )
    missing = [key for key in required if handoff.get(key) in (None, "", [], {})]
    if missing:
        raise GameServiceError(
            f"Play run is missing runtime profile handoff fields: {', '.join(missing)}",
            status_code=502,
        )

    npc_actor_ids = handoff.get("npc_actor_ids")
    actor_lanes = handoff.get("actor_lanes")
    if not isinstance(npc_actor_ids, list) or not all(isinstance(actor_id, str) and actor_id.strip() for actor_id in npc_actor_ids):
        raise GameServiceError("Play run runtime profile handoff has invalid npc_actor_ids.", status_code=502)
    if not isinstance(actor_lanes, dict):
        raise GameServiceError("Play run runtime profile handoff has invalid actor_lanes.", status_code=502)

    human_actor_id = str(handoff["human_actor_id"]).strip()
    if actor_lanes.get(human_actor_id) != "human":
        raise GameServiceError("Play run runtime profile handoff does not mark human_actor_id as human.", status_code=502)
    invalid_npcs = [actor_id for actor_id in npc_actor_ids if actor_lanes.get(actor_id) != "npc"]
    if invalid_npcs:
        raise GameServiceError(
            f"Play run runtime profile handoff does not mark NPC actors correctly: {', '.join(invalid_npcs)}",
            status_code=502,
        )
    if "visitor" in actor_lanes or "visitor" in npc_actor_ids or human_actor_id == "visitor":
        raise GameServiceError("Play run runtime profile handoff must not include visitor as a story actor.", status_code=502)
    return handoff


def _merge_runtime_profile_handoff(
    runtime_projection: dict[str, Any],
    *,
    module_id: str,
    handoff: dict[str, Any],
) -> dict[str, Any]:
    if not handoff:
        return runtime_projection

    content_module_id = str(handoff.get("content_module_id") or "").strip()
    if content_module_id != module_id:
        raise GameServiceError(
            f"Runtime profile content_module_id {content_module_id!r} does not match compiled module {module_id!r}.",
            status_code=502,
        )

    enriched = dict(runtime_projection)
    for key in _RUNTIME_HANDOFF_FIELDS:
        if key in handoff:
            enriched[key] = handoff[key]
    return enriched


def _compile_player_module(
    template_id: str,
    *,
    runtime_profile_handoff: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    module_id = resolve_canonical_module_id_for_template(template_id)
    try:
        compiled = compile_module(module_id)
    except ModuleLoadError as exc:
        raise GameContentValidationError(f"canonical module not found for template_id {template_id!r}") from exc
    runtime_projection = compiled.runtime_projection.model_dump(mode="json")
    runtime_projection = _merge_runtime_profile_handoff(
        runtime_projection,
        module_id=module_id,
        handoff=runtime_profile_handoff or {},
    )

    provenance = {
        "template_id": template_id,
        "module_id": module_id,
        "canonical_content_authority": f"content/modules/{module_id}/",
        "runtime_projection_module_id": runtime_projection.get("module_id"),
        "runtime_projection_module_version": runtime_projection.get("module_version"),
        "publication_gate": "game_content_published",
    }
    if runtime_profile_handoff:
        provenance["runtime_profile_handoff"] = {
            key: runtime_profile_handoff[key]
            for key in _RUNTIME_HANDOFF_FIELDS
            if key in runtime_profile_handoff
        }
    return module_id, runtime_projection, provenance


def _ensure_player_session(
    user: User,
    *,
    run_id: str | None = None,
    template_id: str | None = None,
    run_payload: dict[str, Any] | None = None,
    trace_id: str | None = None,
    selected_player_role: str | None = None,
) -> dict[str, Any]:
    clean_run_id = (run_id or "").strip()
    created: dict[str, Any] | None = None

    if not clean_run_id:
        if not isinstance(run_payload, dict):
            raise ValidationError("run_id is required.")
        clean_run_id = _run_id(run_payload)

    slot = _find_player_session_slot(user.id, clean_run_id)
    if slot is not None:
        metadata = slot.metadata_json if isinstance(slot.metadata_json, dict) else {}
        runtime_session_id = str(
            metadata.get("runtime_session_id") or metadata.get("world_engine_story_session_id") or ""
        ).strip()
        module_id = str(metadata.get("module_id") or "").strip()
        slot_template_id = str(slot.template_id or template_id or "").strip()
        if runtime_session_id and module_id and slot_template_id:
            try:
                state = get_story_state(runtime_session_id, trace_id=g.get("trace_id"))
                return _player_session_bundle(
                    run_id=clean_run_id,
                    template_id=slot_template_id,
                    module_id=module_id,
                    runtime_session_id=runtime_session_id,
                    state=state,
                )
            except GameServiceError as exc:
                if exc.status_code != route_status_codes.not_found:
                    raise

    if not isinstance(run_payload, dict):
        run_payload = get_play_run_details(clean_run_id)
    resolved_template_id = (template_id or _run_template_id(run_payload)).strip()
    template = run_payload.get("template") if isinstance(run_payload.get("template"), dict) else {}
    template_title = str(template.get("title") or resolved_template_id)
    runtime_profile_handoff = _runtime_profile_handoff_from_run_payload(run_payload)
    if resolved_template_id == "god_of_carnage_solo" and not runtime_profile_handoff:
        raise GameServiceError(
            "Play run did not include runtime profile actor ownership required for god_of_carnage_solo.",
            status_code=502,
        )
    if selected_player_role and runtime_profile_handoff:
        handoff_role = str(runtime_profile_handoff.get("selected_player_role") or "").strip()
        if handoff_role and handoff_role != selected_player_role:
            raise GameServiceError(
                "Selected player role does not match the play run runtime profile handoff.",
                status_code=409,
            )
    module_id, runtime_projection, provenance = _compile_player_module(
        resolved_template_id,
        runtime_profile_handoff=runtime_profile_handoff,
    )
    provenance["run_id"] = clean_run_id
    created = create_story_session(
        module_id=module_id,
        runtime_projection=runtime_projection,
        trace_id=trace_id or g.get("trace_id"),
        content_provenance=provenance,
    )
    runtime_session_id = str(created.get("session_id") or "").strip()
    if not runtime_session_id:
        raise GameServiceError("World-Engine did not return a story session id.", status_code=502)
    _persist_player_session_binding(
        user,
        run_id=clean_run_id,
        template_id=resolved_template_id,
        template_title=template_title,
        module_id=module_id,
        runtime_session_id=runtime_session_id,
    )
    state = get_story_state(runtime_session_id, trace_id=g.get("trace_id"))
    return _player_session_bundle(
        run_id=clean_run_id,
        template_id=resolved_template_id,
        module_id=module_id,
        runtime_session_id=runtime_session_id,
        state=state,
        created=created,
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
        template_id = (data.get("template_id") or "").strip() or None
        runtime_profile_id = (data.get("runtime_profile_id") or "").strip() or None
        selected_player_role = (data.get("selected_player_role") or "").strip() or None
        if not template_id and not runtime_profile_id:
            return jsonify({"error": "template_id or runtime_profile_id is required."}), route_status_codes.bad_request
        _PROFILE_ONLY_TEMPLATES = {"god_of_carnage_solo"}
        if template_id in _PROFILE_ONLY_TEMPLATES and not runtime_profile_id:
            return jsonify({
                "error": f"{template_id!r} must be started via runtime_profile_id with selected_player_role.",
                "code": "runtime_profile_required",
                "hint": f"Set runtime_profile_id={template_id!r} and selected_player_role=annette|alain.",
            }), route_status_codes.bad_request
        identity = _resolve_identity_context(user, data)
        result = create_play_run(
            template_id=template_id,
            account_id=str(user.id),
            character_id=identity["character_id"],
            display_name=identity["display_name"],
            runtime_profile_id=runtime_profile_id,
            selected_player_role=selected_player_role,
        )
        if identity["character_id"]:
            touch_character_last_used(user.id, int(identity["character_id"]))
        return jsonify(result), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/player-sessions", methods=["POST"])
@limiter.limit("20 per minute")
def game_player_session_create():
    """Create or resume the canonical player story session for a play run."""
    try:
        user = _require_game_user()
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "JSON body must be an object."}), route_status_codes.bad_request
        run_id = (data.get("run_id") or "").strip()
        template_id = (data.get("template_id") or "").strip()
        trace_id = (data.get("trace_id") or "").strip() or g.get("trace_id")
        run_payload: dict[str, Any] | None = None
        runtime_profile_id = (data.get("runtime_profile_id") or "").strip() or None
        selected_player_role = (data.get("selected_player_role") or "").strip() or None
        if not run_id:
            if not template_id and not runtime_profile_id:
                return jsonify({"error": "template_id, runtime_profile_id, or run_id is required."}), route_status_codes.bad_request
            identity = _resolve_identity_context(user, data)
            run_payload = create_play_run(
                template_id=template_id or None,
                account_id=str(user.id),
                character_id=identity["character_id"],
                display_name=identity["display_name"],
                runtime_profile_id=runtime_profile_id,
                selected_player_role=selected_player_role,
            )
            run_id = _run_id(run_payload)
            if identity["character_id"]:
                touch_character_last_used(user.id, int(identity["character_id"]))
        bundle = _ensure_player_session(
            user,
            run_id=run_id,
            template_id=template_id or None,
            run_payload=run_payload,
            trace_id=trace_id,
            selected_player_role=selected_player_role,
        )
        return jsonify(bundle), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/player-sessions/<run_id>", methods=["GET"])
@limiter.limit("60 per minute")
def game_player_session_resume(run_id: str):
    """Resume the canonical player story session by run id."""
    try:
        user = _require_game_user()
        bundle = _ensure_player_session(user, run_id=run_id)
        return jsonify(bundle), route_status_codes.ok
    except Exception as exc:  # pragma: no cover - centralized mapper
        return _error_response(exc)


@api_v1_bp.route("/game/player-sessions/<run_id>/turns", methods=["POST"])
@limiter.limit("30 per minute")
def game_player_session_turn(run_id: str):
    """Execute a player turn through the authoritative World-Engine story runtime."""
    try:
        user = _require_game_user()
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "JSON body must be an object."}), route_status_codes.bad_request
        player_input = str(data.get("player_input") or data.get("input") or "").strip()
        if not player_input:
            return jsonify({"error": "player_input is required."}), route_status_codes.bad_request
        bundle = _ensure_player_session(user, run_id=run_id)
        runtime_session_id = str(bundle.get("runtime_session_id") or "").strip()
        if not runtime_session_id:
            raise GameServiceError("Canonical player session is not ready.", status_code=502)

        trace_id = g.get("trace_id")
        langfuse_trace_id = g.get("langfuse_trace_id") or get_langfuse_trace_id()
        adapter = LangfuseAdapter.get_instance()
        root_span = None

        try:
            # Create root span for this turn execution
            root_span = adapter.start_trace(
                name="backend.turn.execute",
                session_id=run_id,
                module_id=str(bundle.get("module_id") or ""),
                metadata={
                    "wos_trace_id": trace_id,
                    "langfuse_trace_id": langfuse_trace_id,
                    "player_input_length": len(player_input),
                    "stage": "turn_execution",
                    "route": "/game/player-sessions/<run_id>/turns",
                },
                trace_id=langfuse_trace_id,
            )

            turn_payload = execute_story_turn_in_engine(
                session_id=runtime_session_id,
                player_input=player_input,
                trace_id=trace_id,
                langfuse_trace_id=langfuse_trace_id,
            )
            turn = turn_payload.get("turn") if isinstance(turn_payload.get("turn"), dict) else {}
            state = get_story_state(runtime_session_id, trace_id=trace_id)

            # Update root span with results
            if root_span:
                root_span.update(output={
                    "status": "completed",
                })

            refreshed = _player_session_bundle(
                run_id=run_id,
                template_id=str(bundle.get("template_id") or ""),
                module_id=str(bundle.get("module_id") or ""),
                runtime_session_id=runtime_session_id,
                state=state,
                turn=turn,
            )
            return jsonify(refreshed), route_status_codes.ok
        except GameServiceError as exc:
            # Update root span with error
            if root_span:
                root_span.update(output={
                    "status": "error",
                    "failure_class": "world_engine_unreachable",
                    "status_code": exc.status_code,
                })
            raise
        finally:
            # End root span and flush
            if root_span:
                adapter.end_trace(root_span)
            adapter.flush()
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
