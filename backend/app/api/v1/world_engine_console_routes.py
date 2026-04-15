"""Admin API: proxy read/write World Engine play service for the management console (JWT + feature flags)."""

from __future__ import annotations

from flask import current_app, g, jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.permissions import require_jwt_moderator_or_admin, require_world_engine_capability
from app.extensions import limiter
from app.services.game_service import (
    GameServiceError,
    create_story_session,
    execute_story_turn,
    get_play_service_ready,
    get_run_details,
    get_run_transcript,
    get_story_diagnostics,
    get_story_state,
    list_runs,
    list_story_sessions,
    list_templates,
    terminate_run,
)
from app.services.world_engine_control_center_service import build_world_engine_control_center_snapshot
from app.config.route_constants import route_status_codes, route_pagination_config


def _trace() -> str | None:
    tid = getattr(g, "trace_id", None)
    return tid if isinstance(tid, str) else None


def _gs_err(exc: GameServiceError):
    return jsonify({"error": str(exc)}), min(exc.status_code, 599)


@api_v1_bp.route("/admin/world-engine/health", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_world_engine_capability("observe")
def world_engine_console_health():
    """Observed play-service readiness (GET /api/health/ready on world-engine)."""
    try:
        out = get_play_service_ready(trace_id=_trace())
    except GameServiceError as exc:
        return _gs_err(exc)
    return jsonify(out), route_status_codes.ok


@api_v1_bp.route("/admin/world-engine/control-center", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_world_engine_capability("observe")
def world_engine_control_center_snapshot():
    app = current_app._get_current_object()
    return jsonify(build_world_engine_control_center_snapshot(app, trace_id=_trace())), route_status_codes.ok


@api_v1_bp.route("/admin/world-engine/templates", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_world_engine_capability("observe")
def world_engine_console_templates():
    try:
        items = list_templates()
    except GameServiceError as exc:
        return _gs_err(exc)
    return jsonify({"items": items}), route_status_codes.ok


@api_v1_bp.route("/admin/world-engine/runs", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_world_engine_capability("observe")
def world_engine_console_runs():
    try:
        items = list_runs()
    except GameServiceError as exc:
        return _gs_err(exc)
    return jsonify({"items": items}), route_status_codes.ok


@api_v1_bp.route("/admin/world-engine/runs/<run_id>", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_world_engine_capability("observe")
def world_engine_console_run_detail(run_id: str):
    try:
        detail = get_run_details(run_id)
    except GameServiceError as exc:
        return _gs_err(exc)
    return jsonify(detail), route_status_codes.ok


@api_v1_bp.route("/admin/world-engine/runs/<run_id>/transcript", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_world_engine_capability("observe")
def world_engine_console_run_transcript(run_id: str):
    try:
        data = get_run_transcript(run_id)
    except GameServiceError as exc:
        return _gs_err(exc)
    return jsonify(data), route_status_codes.ok


@api_v1_bp.route("/admin/world-engine/runs/<run_id>/terminate", methods=["POST"])
@limiter.limit("20 per minute")
@require_jwt_moderator_or_admin
@require_world_engine_capability("operate")
def world_engine_console_run_terminate(run_id: str):
    body = request.get_json(silent=True) or {}
    actor = body.get("actor_display_name") if isinstance(body.get("actor_display_name"), str) else ""
    reason = body.get("reason") if isinstance(body.get("reason"), str) else ""
    try:
        out = terminate_run(run_id, actor_display_name=actor, reason=reason)
    except GameServiceError as exc:
        return _gs_err(exc)
    return jsonify(out), route_status_codes.ok


@api_v1_bp.route("/admin/world-engine/story/sessions", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_world_engine_capability("observe")
def world_engine_console_story_sessions_list():
    try:
        data = list_story_sessions(trace_id=_trace())
    except GameServiceError as exc:
        return _gs_err(exc)
    return jsonify(data), route_status_codes.ok


@api_v1_bp.route("/admin/world-engine/story/sessions", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
@require_world_engine_capability("author")
def world_engine_console_story_sessions_create():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object body required"}), route_status_codes.bad_request
    module_id = body.get("module_id")
    projection = body.get("runtime_projection")
    if not isinstance(module_id, str) or not module_id.strip():
        return jsonify({"error": "module_id is required"}), route_status_codes.bad_request
    if not isinstance(projection, dict):
        return jsonify({"error": "runtime_projection object is required"}), route_status_codes.bad_request
    try:
        out = create_story_session(
            module_id=module_id.strip(),
            runtime_projection=projection,
            trace_id=_trace(),
        )
    except GameServiceError as exc:
        return _gs_err(exc)
    return jsonify(out), route_status_codes.ok


@api_v1_bp.route("/admin/world-engine/story/sessions/<session_id>/state", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_world_engine_capability("observe")
def world_engine_console_story_state(session_id: str):
    try:
        data = get_story_state(session_id, trace_id=_trace())
    except GameServiceError as exc:
        return _gs_err(exc)
    return jsonify(data), route_status_codes.ok


@api_v1_bp.route("/admin/world-engine/story/sessions/<session_id>/diagnostics", methods=["GET"])
@limiter.limit("60 per minute")
@require_jwt_moderator_or_admin
@require_world_engine_capability("observe")
def world_engine_console_story_diagnostics(session_id: str):
    try:
        data = get_story_diagnostics(session_id, trace_id=_trace())
    except GameServiceError as exc:
        return _gs_err(exc)
    return jsonify(data), route_status_codes.ok


@api_v1_bp.route("/admin/world-engine/story/sessions/<session_id>/turns", methods=["POST"])
@limiter.limit("30 per minute")
@require_jwt_moderator_or_admin
@require_world_engine_capability("author")
def world_engine_console_story_turn(session_id: str):
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "JSON object body required"}), route_status_codes.bad_request
    player_input = body.get("player_input")
    if not isinstance(player_input, str) or not player_input.strip():
        return jsonify({"error": "player_input is required"}), route_status_codes.bad_request
    try:
        out = execute_story_turn(
            session_id=session_id,
            player_input=player_input.strip(),
            trace_id=_trace(),
        )
    except GameServiceError as exc:
        return _gs_err(exc)
    return jsonify(out), route_status_codes.ok
