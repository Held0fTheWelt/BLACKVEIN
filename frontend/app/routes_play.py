"""Play / session shell routes (registered on ``frontend_bp``)."""

from __future__ import annotations

import json
from typing import Any

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from . import player_backend
from .player_backend import BackendApiError
from .auth import require_login
from .frontend_blueprint import frontend_bp

PLAY_SHELL_RUNTIME_VIEWS_KEY = "play_shell_runtime_views"
PLAY_SHELL_TURN_LOG_KEY = "play_shell_turn_logs"
PLAY_SHELL_OPERATOR_KEY = "play_shell_operator_payloads"

TURN_LOG_MAX = 50
DIAGNOSTICS_MAX_ROWS = 40
OPERATOR_SESSION_JSON_MAX = 120_000

# World-Engine template_id (play catalog) → YAML module id for POST /api/v1/sessions
_PLAY_TEMPLATE_TO_CONTENT_MODULE_ID = {
    "god_of_carnage_solo": "god_of_carnage",
}


def play_template_to_content_module_id(template_id: str) -> str:
    """Map play launcher template id to backend content module directory id."""
    tid = (template_id or "").strip()
    return _PLAY_TEMPLATE_TO_CONTENT_MODULE_ID.get(tid, tid)


def _build_play_shell_runtime_view(api_payload: dict[str, Any]) -> dict[str, Any]:
    """Project world-engine bridge JSON into a compact, player-facing last-turn view."""
    turn = api_payload.get("turn") if isinstance(api_payload.get("turn"), dict) else {}
    st = api_payload.get("state") if isinstance(api_payload.get("state"), dict) else {}
    bundle = turn.get("visible_output_bundle") if isinstance(turn.get("visible_output_bundle"), dict) else {}
    gm = bundle.get("gm_narration")
    lines: list[str] = []
    if isinstance(gm, list):
        lines = [str(x).strip() for x in gm if str(x).strip()]
    narration_text = "\n\n".join(lines)
    spoken = bundle.get("spoken_lines")
    spoken_lines: list[str] = []
    if isinstance(spoken, list):
        spoken_lines = [str(x).strip() for x in spoken if str(x).strip()]

    committed = st.get("committed_state") if isinstance(st.get("committed_state"), dict) else {}
    summary = (
        committed.get("last_narrative_commit_summary")
        if isinstance(committed.get("last_narrative_commit_summary"), dict)
        else {}
    )
    consequences = committed.get("last_committed_consequences")
    cons_list: list[str] = []
    if isinstance(consequences, list):
        cons_list = [str(x) for x in consequences[:12]]

    val = turn.get("validation_outcome") if isinstance(turn.get("validation_outcome"), dict) else {}
    val_status = str(val.get("status") or "").strip() or None

    graph = turn.get("graph") if isinstance(turn.get("graph"), dict) else {}
    errs = graph.get("errors")
    err_count = len(errs) if isinstance(errs, list) else 0

    interp = turn.get("interpreted_input") if isinstance(turn.get("interpreted_input"), dict) else {}
    input_kind = str(interp.get("kind") or "").strip() or "unknown"

    nc = committed.get("last_narrative_commit") if isinstance(committed.get("last_narrative_commit"), dict) else {}
    if not nc:
        nc = turn.get("narrative_commit") if isinstance(turn.get("narrative_commit"), dict) else {}

    return {
        "trace_id": str(api_payload.get("trace_id") or "").strip() or None,
        "world_engine_story_session_id": str(api_payload.get("world_engine_story_session_id") or "").strip() or None,
        "turn_number": turn.get("turn_number"),
        "player_line": str(turn.get("raw_input") or "").strip(),
        "interpreted_input_kind": input_kind,
        "narration_text": narration_text,
        "spoken_lines": spoken_lines,
        "committed_scene_id": summary.get("committed_scene_id") or nc.get("committed_scene_id"),
        "commit_reason_code": summary.get("commit_reason_code") or nc.get("commit_reason_code"),
        "situation_status": summary.get("situation_status"),
        "validation_status": val_status,
        "graph_error_count": err_count,
        "committed_consequences": cons_list,
        "current_scene_id": st.get("current_scene_id"),
        "turn_counter": st.get("turn_counter"),
    }


def _truncate_operator_payload(payload: dict[str, Any]) -> dict[str, Any]:
    turn = payload.get("turn") if isinstance(payload.get("turn"), dict) else {}
    st = payload.get("state") if isinstance(payload.get("state"), dict) else {}
    diag = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    out: dict[str, Any] = {
        "session_id": payload.get("session_id"),
        "trace_id": payload.get("trace_id"),
        "world_engine_story_session_id": payload.get("world_engine_story_session_id"),
        "turn": turn,
        "state": st,
        "diagnostics": dict(diag),
        "backend_interpretation_preview": payload.get("backend_interpretation_preview"),
        "warnings": payload.get("warnings"),
    }
    d_inner = out["diagnostics"]
    rows = d_inner.get("diagnostics")
    if isinstance(rows, list) and len(rows) > DIAGNOSTICS_MAX_ROWS:
        d_inner = {
            **d_inner,
            "diagnostics": rows[-DIAGNOSTICS_MAX_ROWS:],
            "_truncated_row_count": len(rows),
        }
        out["diagnostics"] = d_inner
    raw = json.dumps(out, default=str)
    if len(raw) > OPERATOR_SESSION_JSON_MAX:
        out["diagnostics"] = {"_truncated": True, "note": "Full payload too large for play session storage"}
        out["state"] = {"_truncated": True}
    return out


def _append_turn_log(run_id: str, view: dict[str, Any]) -> None:
    logs = session.get(PLAY_SHELL_TURN_LOG_KEY)
    if not isinstance(logs, dict):
        logs = {}
    lst = list(logs.get(run_id) or [])
    lst.append(view)
    if len(lst) > TURN_LOG_MAX:
        lst = lst[-TURN_LOG_MAX:]
    logs[run_id] = lst
    session[PLAY_SHELL_TURN_LOG_KEY] = logs


def _persist_turn_success(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    view = _build_play_shell_runtime_view(payload)
    views = session.get(PLAY_SHELL_RUNTIME_VIEWS_KEY)
    if not isinstance(views, dict):
        views = {}
    views[run_id] = view
    session[PLAY_SHELL_RUNTIME_VIEWS_KEY] = views
    _append_turn_log(run_id, view)
    op = session.get(PLAY_SHELL_OPERATOR_KEY)
    if not isinstance(op, dict):
        op = {}
    truncated = _truncate_operator_payload(payload)
    op[run_id] = truncated
    session[PLAY_SHELL_OPERATOR_KEY] = op
    session.modified = True
    return {"runtime_view": view, "operator_bundle": truncated}


def _ensure_turn_log_from_legacy(run_id: str, runtime_view: dict[str, Any] | None) -> list[dict[str, Any]]:
    logs = session.get(PLAY_SHELL_TURN_LOG_KEY)
    if not isinstance(logs, dict):
        logs = {}
    lst = logs.get(run_id)
    if isinstance(lst, list) and lst:
        return lst
    if runtime_view:
        logs[run_id] = [runtime_view]
        session[PLAY_SHELL_TURN_LOG_KEY] = logs
        session.modified = True
        return [runtime_view]
    return []


def _wants_json_response() -> bool:
    if request.is_json:
        return True
    return request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json"


def _player_input_from_request() -> str:
    if request.is_json:
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            return (data.get("player_input") or "").strip()
        return ""
    return (request.form.get("player_input") or "").strip()


def _run_backend_turn(run_id: str, player_input: str) -> tuple[dict[str, Any] | None, str | None]:
    backend_sessions = session.get("play_shell_backend_sessions", {})
    if not isinstance(backend_sessions, dict):
        backend_sessions = {}
    backend_session_id = backend_sessions.get(run_id)
    if not backend_session_id:
        return None, "Runtime session is not ready. Re-open the play shell from Play Start."
    text = player_input.strip()
    if not text:
        return None, "Please describe your turn in natural language (or use an explicit command)."
    response = player_backend.request_backend(
        "POST",
        f"/api/v1/sessions/{backend_session_id}/turns",
        json_data={"player_input": text},
    )
    try:
        pl = player_backend.require_success(response, "Runtime turn execution failed.")
    except BackendApiError as exc:
        return None, str(exc)
    if isinstance(pl, dict):
        return pl, None
    return None, "Runtime turn execution returned an invalid response."


@frontend_bp.route("/play")
@require_login
def play_start():
    response = player_backend.request_backend("GET", "/api/v1/game/bootstrap")
    bootstrap = response.json() if response.ok else {}
    return render_template("session_start.html", bootstrap=bootstrap)


@frontend_bp.route("/play/start", methods=["POST"])
@require_login
def play_create():
    template_id = (request.form.get("template_id") or "").strip()
    if not template_id:
        flash("Please select a template.", "error")
        return redirect(url_for("frontend.play_start"))
    response = player_backend.request_backend("POST", "/api/v1/game/runs", json_data={"template_id": template_id})
    try:
        payload = player_backend.require_success(response, "Could not create play run.")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return redirect(url_for("frontend.play_start"))
    run_id = payload.get("run", {}).get("id")
    if not run_id:
        flash("Run creation returned no run id.", "error")
        return redirect(url_for("frontend.play_start"))
    run_modules = session.get("play_shell_run_modules", {})
    if not isinstance(run_modules, dict):
        run_modules = {}
    run_modules[run_id] = play_template_to_content_module_id(template_id)
    session["play_shell_run_modules"] = run_modules
    session.modified = True
    return redirect(url_for("frontend.play_shell", session_id=run_id))


@frontend_bp.route("/play/<session_id>")
@require_login
def play_shell(session_id: str):
    user = session.get("current_user") or {}
    response = player_backend.request_backend(
        "POST",
        "/api/v1/game/tickets",
        json_data={"run_id": session_id, "display_name": user.get("username", "Player")},
    )
    ticket_payload = response.json() if response.ok else {}
    if not response.ok:
        flash(ticket_payload.get("error", "Could not create play ticket."), "error")
    backend_sessions = session.get("play_shell_backend_sessions", {})
    if not isinstance(backend_sessions, dict):
        backend_sessions = {}
    backend_session_id = backend_sessions.get(session_id)
    if not backend_session_id:
        run_modules = session.get("play_shell_run_modules", {})
        module_id = run_modules.get(session_id) if isinstance(run_modules, dict) else None
        if module_id:
            backend_response = player_backend.request_backend(
                "POST",
                "/api/v1/sessions",
                json_data={"module_id": module_id},
            )
            if backend_response.ok:
                backend_payload = backend_response.json()
                backend_session_id = backend_payload.get("session_id")
                if backend_session_id:
                    backend_sessions[session_id] = backend_session_id
                    session["play_shell_backend_sessions"] = backend_sessions
                    session.modified = True
                else:
                    flash("Runtime session creation returned no session id.", "error")
            else:
                backend_payload = backend_response.json() if backend_response.content else {}
                flash(backend_payload.get("error", "Could not create runtime session."), "error")
        else:
            flash("No module mapping found for this run. Start a new run from Play Start.", "error")
    runtime_views = session.get(PLAY_SHELL_RUNTIME_VIEWS_KEY)
    if not isinstance(runtime_views, dict):
        runtime_views = {}
    runtime_view = runtime_views.get(session_id)
    turn_log = _ensure_turn_log_from_legacy(session_id, runtime_view)
    op_map = session.get(PLAY_SHELL_OPERATOR_KEY)
    operator_bundle = op_map.get(session_id) if isinstance(op_map, dict) else None
    play_bootstrap_json = json.dumps({"operator_bundle": operator_bundle or {}})

    return render_template(
        "session_shell.html",
        session_id=session_id,
        ticket=ticket_payload,
        backend_session_id=backend_session_id,
        runtime_view=runtime_view,
        turn_log=turn_log,
        operator_bundle=operator_bundle,
        play_bootstrap_json=play_bootstrap_json,
    )


@frontend_bp.route("/play/<session_id>/execute", methods=["POST"])
@require_login
def play_execute(session_id: str):
    wants_json = _wants_json_response()
    player_input = _player_input_from_request()
    payload, err = _run_backend_turn(session_id, player_input)
    if err:
        if wants_json:
            return jsonify({"ok": False, "error": err}), 400
        flash(err, "error")
        return redirect(url_for("frontend.play_shell", session_id=session_id))
    assert payload is not None
    extras = _persist_turn_success(session_id, payload)
    interpreted = (((payload.get("turn") or {}).get("interpreted_input") or {}).get("kind") or "unknown").strip()
    if wants_json:
        return jsonify(
            {
                "ok": True,
                "interpreted_input_kind": interpreted,
                **extras,
            }
        ), 200
    flash(
        f"Turn executed (interpreted as {interpreted}). Scene and narration below update from the world-engine response.",
        "success",
    )
    return redirect(url_for("frontend.play_shell", session_id=session_id))
