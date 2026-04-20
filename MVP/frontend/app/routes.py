"""Player/public frontend routes."""
from __future__ import annotations

from typing import Any

import requests
from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .api_client import BackendApiError, request_backend, require_success
from .auth import require_login

frontend_bp = Blueprint("frontend", __name__)


def _clear_auth_state() -> None:
    session.pop("access_token", None)
    session.pop("refresh_token", None)
    session.pop("current_user", None)
    session.modified = True


def _current_user() -> dict[str, Any] | None:
    return session.get("current_user")


def _user_is_admin(user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    return user.get("role") == "admin"


def _request_wants_json() -> bool:
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    if request.is_json:
        return True
    return False


def _compose_authoritative_shell_bundle(*, run_id: str, run_detail: dict[str, Any] | None, transcript: dict[str, Any] | None, runtime_shell_readout: dict[str, Any] | None = None) -> dict[str, Any]:
    entries = []
    if isinstance(transcript, dict):
        raw_entries = transcript.get("entries")
        if isinstance(raw_entries, list):
            entries = raw_entries

    latest_entry = entries[-1] if entries else None
    latest_text = None
    if isinstance(latest_entry, dict):
        latest_text = latest_entry.get("text") or latest_entry.get("content") or latest_entry.get("message")
    latest_text = _build_response_framed_line(text=latest_text, runtime_shell_readout=runtime_shell_readout)

    run_obj = run_detail.get("run") if isinstance(run_detail, dict) else {}
    template_obj = run_detail.get("template") if isinstance(run_detail, dict) else {}
    lobby_obj = run_detail.get("lobby") if isinstance(run_detail, dict) else {}

    transcript_preview = [
        (entry.get("text") or entry.get("content") or entry.get("message") or str(entry))
        for entry in entries[-5:]
    ]
    transcript_preview = _build_response_framed_preview(preview=transcript_preview, runtime_shell_readout=runtime_shell_readout)
    transcript_entry_count = len(entries)
    run_status = (run_obj or {}).get("status") if isinstance(run_obj, dict) else None
    lobby_status = (lobby_obj or {}).get("status") if isinstance(lobby_obj, dict) else None
    status_parts = []
    if run_status:
        status_parts.append(f"Run status: {run_status}")
    if lobby_status:
        status_parts.append(f"Lobby: {lobby_status}")
    status_parts.append(f"Transcript entries: {transcript_entry_count}")
    if latest_text:
        status_parts.append(f"Latest line: {latest_text}")

    shell_state_view = {
        "run_title": (template_obj or {}).get("title") or (run_obj or {}).get("template_title"),
        "template_source": run_detail.get("template_source") if isinstance(run_detail, dict) else None,
        "lobby_status": lobby_status,
        "run_status": run_status,
        "transcript_entry_count": transcript_entry_count,
        "latest_entry_text": latest_text,
        "transcript_preview": transcript_preview,
        "authoritative_status_summary": " · ".join(status_parts),
    }

    return {
        "run_id": run_id,
        "run_detail": run_detail,
        "transcript": transcript,
        "transcript_entry_count": transcript_entry_count,
        "latest_entry_text": latest_text,
        "template_title": shell_state_view.get("run_title"),
        "template_source": shell_state_view.get("template_source"),
        "lobby_status": shell_state_view.get("lobby_status"),
        "run_status": shell_state_view.get("run_status"),
        "shell_state_view": shell_state_view,
    }




def _build_response_framed_line(*, text: str | None, runtime_shell_readout: dict[str, Any] | None) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    raw = text.strip()
    if not isinstance(runtime_shell_readout, dict):
        return raw
    prefix = runtime_shell_readout.get("response_line_prefix_now")
    if not (isinstance(prefix, str) and prefix.strip()):
        prefix = runtime_shell_readout.get("response_address_source_now")
    if not (isinstance(prefix, str) and prefix.strip()):
        prefix = runtime_shell_readout.get("who_answers_now")
    if not (isinstance(prefix, str) and prefix.strip()):
        return raw
    prefix = prefix.strip().rstrip('.')
    return f"{prefix} — {raw}"


def _build_response_framed_preview(*, preview: list[str], runtime_shell_readout: dict[str, Any] | None) -> list[str]:
    if not isinstance(preview, list) or not preview:
        return preview
    framed = list(preview)
    last = _build_response_framed_line(text=framed[-1], runtime_shell_readout=runtime_shell_readout)
    if isinstance(last, str) and last.strip():
        framed[-1] = last
    return framed

def _build_shell_state_view(*, run_id: str, run_detail: dict[str, Any] | None, transcript: dict[str, Any] | None, authoritative_observation: dict[str, Any] | None) -> dict[str, Any]:
    runtime_shell_readout = _get_play_shell_runtime_readout(run_id)
    if isinstance(authoritative_observation, dict):
        shell_state_view = authoritative_observation.get("shell_state_view")
        if isinstance(shell_state_view, dict):
            merged = _merge_runtime_shell_readout(base=shell_state_view, runtime_shell_readout=runtime_shell_readout)
            merged["latest_entry_text"] = _build_response_framed_line(text=merged.get("latest_entry_text"), runtime_shell_readout=runtime_shell_readout)
            preview = merged.get("transcript_preview")
            if isinstance(preview, list):
                merged["transcript_preview"] = _build_response_framed_preview(preview=preview, runtime_shell_readout=runtime_shell_readout)
            return merged
    base = _compose_authoritative_shell_bundle(run_id="unknown", run_detail=run_detail, transcript=transcript, runtime_shell_readout=runtime_shell_readout).get("shell_state_view", {})
    merged = _merge_runtime_shell_readout(base=base, runtime_shell_readout=runtime_shell_readout)
    merged["latest_entry_text"] = _build_response_framed_line(text=merged.get("latest_entry_text"), runtime_shell_readout=runtime_shell_readout)
    preview = merged.get("transcript_preview")
    if isinstance(preview, list):
        merged["transcript_preview"] = _build_response_framed_preview(preview=preview, runtime_shell_readout=runtime_shell_readout)
    return merged


def _fetch_authoritative_shell_observation(run_id: str) -> dict[str, Any]:
    detail_response = request_backend("GET", f"/api/v1/game/runs/{run_id}")
    transcript_response = request_backend("GET", f"/api/v1/game/runs/{run_id}/transcript")

    detail_payload = require_success(detail_response, "Could not load authoritative run details.")
    transcript_payload = require_success(transcript_response, "Could not load authoritative transcript.")
    return _compose_authoritative_shell_bundle(run_id=run_id, run_detail=detail_payload, transcript=transcript_payload)


def _resolve_authoritative_observation(run_id: str, *, allow_cached_fallback: bool = True) -> tuple[dict[str, Any] | None, str, str | None]:
    cached = _get_play_shell_observations().get(run_id)
    try:
        observation = _fetch_authoritative_shell_observation(run_id)
        _store_play_shell_observation(run_id, observation)
        return observation, "fresh", None
    except BackendApiError as exc:
        if allow_cached_fallback and isinstance(cached, dict):
            return cached, "cached_fallback", str(exc)
        return None, "unavailable", str(exc)


def _get_play_shell_observations() -> dict[str, Any]:
    observations = session.get("play_shell_authoritative_observations", {})
    return observations if isinstance(observations, dict) else {}


def _store_play_shell_observation(run_id: str, observation: dict[str, Any]) -> None:
    observations = _get_play_shell_observations()
    observations[run_id] = observation
    session["play_shell_authoritative_observations"] = observations
    session.modified = True


def _get_play_shell_runtime_readouts() -> dict[str, Any]:
    payload = session.get("play_shell_runtime_readouts", {})
    return payload if isinstance(payload, dict) else {}



def _get_play_shell_runtime_readout(run_id: str) -> dict[str, Any] | None:
    payload = _get_play_shell_runtime_readouts().get(run_id)
    return payload if isinstance(payload, dict) else None



def _store_play_shell_runtime_readout(run_id: str, readout: dict[str, Any]) -> None:
    payload = _get_play_shell_runtime_readouts()
    payload[run_id] = readout
    session["play_shell_runtime_readouts"] = payload
    session.modified = True



def _extract_runtime_shell_readout(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    turn = payload.get("turn")
    if isinstance(turn, dict):
        direct_turn = turn.get("shell_readout_projection")
        if isinstance(direct_turn, dict):
            return direct_turn
    state = payload.get("state")
    if not isinstance(state, dict):
        return None
    direct = state.get("shell_readout_projection")
    if isinstance(direct, dict):
        return direct
    committed_state = state.get("committed_state")
    if isinstance(committed_state, dict):
        nested = committed_state.get("shell_readout_projection")
        if isinstance(nested, dict):
            return nested
    return None


def _extract_turn_level_addressed_line(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    turn = payload.get("turn")
    if not isinstance(turn, dict):
        return None
    bundle = turn.get("visible_output_bundle_addressed")
    if not isinstance(bundle, dict):
        return None
    for key in ("gm_narration", "spoken_lines"):
        raw = bundle.get(key)
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, str) and item.strip():
                    return item.strip()
    return None


def _merge_turn_level_addressed_output(*, shell_response: dict[str, Any], payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(shell_response, dict):
        return shell_response
    addressed_line = _extract_turn_level_addressed_line(payload)
    if not addressed_line:
        return shell_response
    merged = dict(shell_response)
    shell_state = dict(merged.get("shell_state_view") or {})
    shell_state["latest_entry_text"] = addressed_line
    preview = shell_state.get("transcript_preview")
    if isinstance(preview, list):
        preview_lines = [str(x) for x in preview if str(x).strip()]
        if not preview_lines or preview_lines[-1] != addressed_line:
            preview_lines = (preview_lines + [addressed_line])[-5:]
        shell_state["transcript_preview"] = preview_lines
    else:
        shell_state["transcript_preview"] = [addressed_line]
    status = shell_state.get("authoritative_status_summary")
    if isinstance(status, str) and status.strip():
        parts = [p.strip() for p in status.split(" · ") if p.strip() and not p.strip().startswith("Latest line:")]
        parts.append(f"Latest line: {addressed_line}")
        shell_state["authoritative_status_summary"] = " · ".join(parts)
    merged["shell_state_view"] = shell_state
    merged["latest_entry_text"] = addressed_line
    if isinstance(merged.get("transcript_preview"), list):
        preview_lines = [str(x) for x in merged.get("transcript_preview") if str(x).strip()]
        if not preview_lines or preview_lines[-1] != addressed_line:
            preview_lines = (preview_lines + [addressed_line])[-5:]
        merged["transcript_preview"] = preview_lines
    return merged



def _merge_runtime_shell_readout(*, base: dict[str, Any], runtime_shell_readout: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(base, dict):
        base = {}
    merged = dict(base)
    if isinstance(runtime_shell_readout, dict):
        for field in (
            "social_weather_now",
            "live_surface_now",
            "carryover_now",
            "social_geometry_now",
            "situational_freedom_now",
            "address_pressure_now",
            "social_moment_now",
            "response_pressure_now",
            "response_address_source_now",
            "response_exchange_now",
            "response_exchange_label_now",
            "response_carryover_now",
            "response_line_prefix_now",
            "who_answers_now",
            "why_this_reply_now",
            "observation_foothold_now",
            "room_pressure_now",
            "zone_sensitivity_now",
            "salient_object_now",
            "object_sensitivity_now",
            "continued_wound_now",
            "role_pressure_now",
            "dominant_social_reading_now",
            "social_axis_now",
            "host_guest_pressure_now",
            "spouse_axis_now",
            "cross_couple_now",
            "pressure_redistribution_now",
            "callback_pressure_now",
            "callback_role_frame_now",
            "active_pressure_now",
            "recent_act_social_meaning",
            "object_social_reading_now",
            "situational_affordance_now",
            "reaction_delta_now",
            "carryover_delta_now",
            "pressure_shift_delta_now",
            "hot_surface_delta_now",
        ):
            value = runtime_shell_readout.get(field)
            if isinstance(value, str) and value.strip():
                merged[field] = value.strip()
    return merged


def _get_play_shell_run_module_bindings() -> dict[str, Any]:
    bindings = session.get("play_shell_run_modules", {})
    return bindings if isinstance(bindings, dict) else {}


def _get_play_shell_run_module_binding(run_id: str) -> str | None:
    value = _get_play_shell_run_module_bindings().get(run_id)
    return value if isinstance(value, str) and value else None


def _store_play_shell_run_module_binding(run_id: str, module_id: str) -> None:
    bindings = _get_play_shell_run_module_bindings()
    bindings[run_id] = module_id
    session["play_shell_run_modules"] = bindings
    session.modified = True


def _get_backend_session_bindings() -> dict[str, Any]:
    backend_sessions = session.get("play_shell_backend_sessions", {})
    return backend_sessions if isinstance(backend_sessions, dict) else {}


def _get_backend_session_binding(run_id: str) -> str | None:
    value = _get_backend_session_bindings().get(run_id)
    return value if isinstance(value, str) and value else None


def _store_backend_session_binding(run_id: str, backend_session_id: str) -> None:
    backend_sessions = _get_backend_session_bindings()
    backend_sessions[run_id] = backend_session_id
    session["play_shell_backend_sessions"] = backend_sessions
    session.modified = True


def _extract_runtime_bootstrap_module_binding(*, observation: dict[str, Any] | None, observation_source: str) -> tuple[str | None, str | None]:
    if not isinstance(observation, dict):
        return None, None
    run_detail = observation.get("run_detail")
    template = run_detail.get("template") if isinstance(run_detail, dict) else None
    template_id = template.get("id") if isinstance(template, dict) else None
    if not isinstance(template_id, str) or not template_id.strip():
        return None, None
    binding_source = "authoritative_run_detail" if observation_source == "fresh" else "cached_authoritative_observation"
    return template_id.strip(), binding_source


def _create_backend_session_binding(*, run_id: str, module_id: str) -> tuple[str | None, str | None]:
    response = request_backend(
        "POST",
        "/api/v1/sessions",
        json_data={"module_id": module_id},
    )
    try:
        payload = require_success(response, "Could not create runtime session.")
    except BackendApiError as exc:
        return None, str(exc)
    backend_session_id = payload.get("session_id")
    if not isinstance(backend_session_id, str) or not backend_session_id.strip():
        return None, "Runtime session creation returned no session id."
    _store_backend_session_binding(run_id, backend_session_id)
    return backend_session_id, None


def _build_runtime_recovery_payload(
    *,
    status: str,
    message: str,
    recoverable: bool,
    recovered: bool,
    backend_session_source: str | None = None,
    module_binding_source: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "recoverable": recoverable,
        "recovered": recovered,
        "backend_session_source": backend_session_source,
        "module_binding_source": module_binding_source,
        "error": error,
    }


def _resolve_runtime_recovery(
    *,
    run_id: str,
    observation: dict[str, Any] | None,
    observation_source: str,
    backend_session_id: str | None,
    recover_backend_session: bool,
) -> tuple[str | None, dict[str, Any]]:
    module_id = _get_play_shell_run_module_binding(run_id)
    module_binding_source = "session_mapping" if module_id else None
    if not module_id:
        module_id, module_binding_source = _extract_runtime_bootstrap_module_binding(
            observation=observation,
            observation_source=observation_source,
        )
        if module_id:
            _store_play_shell_run_module_binding(run_id, module_id)

    if backend_session_id:
        return backend_session_id, _build_runtime_recovery_payload(
            status="bound",
            message="Existing runtime session binding preserved.",
            recoverable=True,
            recovered=False,
            backend_session_source="session_binding",
            module_binding_source=module_binding_source,
        )

    if not recover_backend_session:
        if module_id:
            return None, _build_runtime_recovery_payload(
                status="not_ready",
                message="Runtime session is not ready yet, but the shell has enough binding context to recover it on re-entry.",
                recoverable=True,
                recovered=False,
                module_binding_source=module_binding_source,
            )
        return None, _build_runtime_recovery_payload(
            status="not_ready",
            message="Runtime session is not ready. Recovery requires a stored template binding or an authoritative run detail payload that still exposes one.",
            recoverable=False,
            recovered=False,
        )

    if not module_id:
        return None, _build_runtime_recovery_payload(
            status="not_ready",
            message="Runtime session recovery is not possible from current shell state. Re-open the run from Play Start or reload while authoritative run detail is available.",
            recoverable=False,
            recovered=False,
        )

    recovered_backend_session_id, recovery_error = _create_backend_session_binding(run_id=run_id, module_id=module_id)
    if recovered_backend_session_id:
        return recovered_backend_session_id, _build_runtime_recovery_payload(
            status="recovered",
            message="Runtime session binding recovered from existing shell-visible run context.",
            recoverable=True,
            recovered=True,
            backend_session_source="recovered_backend_session",
            module_binding_source=module_binding_source,
        )

    return None, _build_runtime_recovery_payload(
        status="not_ready",
        message="Runtime session recovery failed while creating a backend compatibility session.",
        recoverable=True,
        recovered=False,
        backend_session_source="recovery_failed",
        module_binding_source=module_binding_source,
        error=recovery_error,
    )


def _authoritative_observation_response(*, run_id: str, observation: dict[str, Any] | None, observation_source: str, observation_error: str | None = None, backend_session_id: str | None = None, runtime_recovery: dict[str, Any] | None = None) -> dict[str, Any]:
    shell_state_view = _build_shell_state_view(
        run_id=run_id,
        run_detail=observation.get("run_detail") if isinstance(observation, dict) else None,
        transcript=observation.get("transcript") if isinstance(observation, dict) else None,
        authoritative_observation=observation,
    ) if isinstance(observation, dict) else _merge_runtime_shell_readout(base={}, runtime_shell_readout=_get_play_shell_runtime_readout(run_id))
    observation_meta = {
        "source": observation_source,
        "error": observation_error,
        "is_fresh": observation_source == "fresh",
        "is_cached_fallback": observation_source == "cached_fallback",
        "is_unavailable": observation is None,
    }
    runtime_recovery_payload = runtime_recovery if isinstance(runtime_recovery, dict) else _build_runtime_recovery_payload(
        status="bound" if backend_session_id else "not_ready",
        message="Existing runtime session binding preserved." if backend_session_id else "Runtime session is not ready.",
        recoverable=bool(backend_session_id),
        recovered=False,
        backend_session_source="session_binding" if backend_session_id else None,
    )
    return {
        "ok": observation is not None,
        "session_id": run_id,
        "backend_session_id": backend_session_id,
        "runtime_session_ready": bool(backend_session_id),
        "can_execute": bool(backend_session_id),
        "can_refresh": True,
        "observation_source": observation_source,
        "observation_error": observation_error,
        "observation_meta": observation_meta,
        "authoritative_observation": observation,
        "shell_state_view": shell_state_view,
        "runtime_recovery": runtime_recovery_payload,
        "runtime_recovery_status": runtime_recovery_payload.get("status"),
        "runtime_recovery_message": runtime_recovery_payload.get("message"),
        "runtime_recovery_error": runtime_recovery_payload.get("error"),
    }


def _build_play_shell_response(*, run_id: str, backend_session_id: str | None, allow_cached_fallback: bool = True, recover_backend_session: bool = False) -> dict[str, Any]:
    observation, observation_source, observation_error = _resolve_authoritative_observation(run_id, allow_cached_fallback=allow_cached_fallback)
    resolved_backend_session_id, runtime_recovery = _resolve_runtime_recovery(
        run_id=run_id,
        observation=observation,
        observation_source=observation_source,
        backend_session_id=backend_session_id,
        recover_backend_session=recover_backend_session,
    )
    return _authoritative_observation_response(
        run_id=run_id,
        observation=observation,
        observation_source=observation_source,
        observation_error=observation_error,
        backend_session_id=resolved_backend_session_id,
        runtime_recovery=runtime_recovery,
    )

def _fetch_me() -> dict[str, Any]:
    response = request_backend("GET", "/api/v1/auth/me")
    payload = require_success(response, "Could not fetch user profile.")
    session["current_user"] = payload
    session.modified = True
    return payload


@frontend_bp.route("/")
def home():
    return render_template("home.html")


@frontend_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("access_token"):
            return redirect(url_for("frontend.dashboard"))
        return render_template("login.html")

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not username or not password:
        flash("Username and password are required.", "error")
        return render_template("login.html"), 400

    response = request_backend(
        "POST",
        "/api/v1/auth/login",
        json_data={"username": username, "password": password},
        allow_refresh=False,
    )
    try:
        payload = require_success(response, "Login failed.")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return render_template("login.html"), exc.status_code

    session["access_token"] = payload["access_token"]
    session["refresh_token"] = payload["refresh_token"]
    session["current_user"] = payload.get("user")
    session.modified = True
    flash("Logged in successfully.", "success")
    return redirect(url_for("frontend.dashboard"))


@frontend_bp.route("/logout", methods=["POST"])
def logout():
    if session.get("access_token"):
        request_backend("POST", "/api/v1/auth/logout")
    _clear_auth_state()
    flash("You have been logged out.", "info")
    return redirect(url_for("frontend.home"))


@frontend_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = (request.form.get("username") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    if not username or not password:
        flash("Username and password are required.", "error")
        return render_template("register.html"), 400
    if password != password_confirm:
        flash("Passwords do not match.", "error")
        return render_template("register.html"), 400

    response = request_backend(
        "POST",
        "/api/v1/auth/register",
        json_data={"username": username, "email": email, "password": password},
        allow_refresh=False,
    )
    try:
        require_success(response, "Registration failed.")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return render_template("register.html"), exc.status_code

    flash("Registration complete. You can now log in.", "success")
    return redirect(url_for("frontend.register_pending"))


@frontend_bp.route("/register/pending")
def register_pending():
    return render_template("register_pending.html")


@frontend_bp.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
    if request.method == "GET":
        return render_template("resend_verification.html")
    email = (request.form.get("email") or "").strip().lower()
    response = request_backend(
        "POST",
        "/api/v1/auth/resend-verification",
        json_data={"email": email},
        allow_refresh=False,
    )
    try:
        payload = require_success(response, "Could not resend verification email.")
        flash(payload.get("message", "Verification mail request accepted."), "info")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return render_template("resend_verification.html"), exc.status_code
    return redirect(url_for("frontend.login"))


@frontend_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html")
    email = (request.form.get("email") or "").strip().lower()
    response = request_backend(
        "POST",
        "/api/v1/auth/forgot-password",
        json_data={"email": email},
        allow_refresh=False,
    )
    try:
        payload = require_success(response, "Could not request a reset link.")
        flash(payload.get("message", "If the email exists, a reset link has been sent."), "info")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return render_template("forgot_password.html"), exc.status_code
    return redirect(url_for("frontend.login"))


@frontend_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    if request.method == "GET":
        return render_template("reset_password.html", token=token)
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""
    if password != password_confirm:
        flash("Passwords do not match.", "error")
        return render_template("reset_password.html", token=token), 400
    response = request_backend(
        "POST",
        "/api/v1/auth/reset-password",
        json_data={"token": token, "new_password": password},
        allow_refresh=False,
    )
    try:
        payload = require_success(response, "Password reset failed.")
        flash(payload.get("message", "Password reset successful."), "success")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return render_template("reset_password.html", token=token), exc.status_code
    return redirect(url_for("frontend.login"))


@frontend_bp.route("/dashboard")
@require_login
def dashboard():
    try:
        user = _fetch_me()
    except BackendApiError as exc:
        if exc.status_code == 401:
            _clear_auth_state()
            return redirect(url_for("frontend.login"))
        flash(str(exc), "error")
        user = _current_user()
    return render_template(
        "dashboard.html",
        current_user=user,
        is_admin=_user_is_admin(user),
    )


@frontend_bp.route("/news")
def news():
    response = request_backend("GET", "/api/v1/news", params={"page": 1, "limit": 20}, allow_refresh=False)
    items: list[dict[str, Any]] = []
    if response.ok:
        payload = response.json()
        items = payload.get("items", []) if isinstance(payload, dict) else []
    return render_template("news.html", items=items)


@frontend_bp.route("/wiki")
@frontend_bp.route("/wiki/<path:slug>")
def wiki(slug: str | None = None):
    api_path = f"/api/v1/wiki/{slug}" if slug else "/api/v1/wiki/index"
    response = request_backend("GET", api_path, allow_refresh=False)
    page = response.json() if response.ok else None
    return render_template("wiki.html", page=page, slug=slug), response.status_code if response.status_code in (200, 404) else 200


@frontend_bp.route("/community")
def community():
    response = request_backend("GET", "/api/v1/forum/categories", allow_refresh=False)
    categories = []
    if response.ok:
        payload = response.json()
        categories = payload.get("items", []) if isinstance(payload, dict) else []
    return render_template("community.html", categories=categories)


@frontend_bp.route("/game-menu")
@require_login
def game_menu():
    user = _current_user()
    return render_template(
        "game_menu.html",
        current_user=user,
        api_base="/api/v1/game",
        play_service_public_url=current_app.config["PLAY_SERVICE_PUBLIC_URL"],
    )


@frontend_bp.route("/play")
@require_login
def play_start():
    response = request_backend("GET", "/api/v1/game/bootstrap")
    bootstrap = response.json() if response.ok else {}
    return render_template("session_start.html", bootstrap=bootstrap)


@frontend_bp.route("/play/start", methods=["POST"])
@require_login
def play_create():
    template_id = (request.form.get("template_id") or "").strip()
    if not template_id:
        flash("Please select a template.", "error")
        return redirect(url_for("frontend.play_start"))
    response = request_backend("POST", "/api/v1/game/runs", json_data={"template_id": template_id})
    try:
        payload = require_success(response, "Could not create play run.")
    except BackendApiError as exc:
        flash(str(exc), "error")
        return redirect(url_for("frontend.play_start"))
    run_id = payload.get("run", {}).get("id")
    if not run_id:
        flash("Run creation returned no run id.", "error")
        return redirect(url_for("frontend.play_start"))
    _store_play_shell_run_module_binding(run_id, template_id)
    return redirect(url_for("frontend.play_shell", session_id=run_id))


@frontend_bp.route("/play/<session_id>")
@require_login
def play_shell(session_id: str):
    user = _current_user() or {}
    response = request_backend(
        "POST",
        "/api/v1/game/tickets",
        json_data={"run_id": session_id, "display_name": user.get("username", "Player")},
    )
    ticket_payload = response.json() if response.ok else {}
    if not response.ok:
        flash(ticket_payload.get("error", "Could not create play ticket."), "error")

    shell_response = _build_play_shell_response(
        run_id=session_id,
        backend_session_id=_get_backend_session_binding(session_id),
        recover_backend_session=True,
    )
    observation = shell_response.get("authoritative_observation") if isinstance(shell_response, dict) else None
    if observation is None:
        flash(shell_response.get("observation_error") or "Could not load authoritative run details.", "error")

    runtime_recovery = shell_response.get("runtime_recovery") or {}
    if not shell_response.get("runtime_session_ready") and runtime_recovery.get("error"):
        flash(runtime_recovery.get("error") or runtime_recovery.get("message") or "Runtime session recovery failed.", "error")

    run_detail = observation.get("run_detail") if isinstance(observation, dict) else None
    transcript = observation.get("transcript") if isinstance(observation, dict) else None
    return render_template(
        "session_shell.html",
        session_id=session_id,
        ticket=ticket_payload,
        backend_session_id=shell_response.get("backend_session_id"),
        run_detail=run_detail,
        transcript=transcript,
        authoritative_observation=observation,
        shell_state_view=shell_response.get("shell_state_view") or {},
        observation_source=shell_response.get("observation_source"),
        observation_error=shell_response.get("observation_error"),
        observation_meta=shell_response.get("observation_meta") or {},
        runtime_session_ready=shell_response.get("runtime_session_ready"),
        can_execute=shell_response.get("can_execute"),
        runtime_recovery=runtime_recovery,
        runtime_recovery_status=shell_response.get("runtime_recovery_status"),
        runtime_recovery_message=shell_response.get("runtime_recovery_message"),
        runtime_recovery_error=shell_response.get("runtime_recovery_error"),
        initial_shell_state=shell_response,
    )



@frontend_bp.route("/play/<session_id>/observe", methods=["GET"])
@require_login
def play_observe(session_id: str):
    shell_response = _build_play_shell_response(
        run_id=session_id,
        backend_session_id=_get_backend_session_binding(session_id),
        recover_backend_session=True,
    )
    if shell_response.get("authoritative_observation") is None:
        return jsonify({"error": shell_response.get("observation_error") or "Could not refresh authoritative observation.", **shell_response}), 502
    return jsonify(shell_response), 200


@frontend_bp.route("/play/<session_id>/execute", methods=["POST"])
@require_login
def play_execute(session_id: str):
    request_payload = request.get_json(silent=True) or {}
    player_input = ((request.form.get("player_input") if request.form else None) or request_payload.get("player_input") or "").strip()
    wants_json = _request_wants_json()
    if not player_input:
        message = "Please describe your turn in natural language (or use an explicit command)."
        if wants_json:
            return jsonify({"error": message}), 400
        flash(message, "error")
        return redirect(url_for("frontend.play_shell", session_id=session_id))
    shell_response = _build_play_shell_response(
        run_id=session_id,
        backend_session_id=_get_backend_session_binding(session_id),
        recover_backend_session=True,
    )
    backend_session_id = shell_response.get("backend_session_id") if isinstance(shell_response, dict) else None
    if not backend_session_id:
        message = shell_response.get("runtime_recovery_error") or shell_response.get("runtime_recovery_message") or "Runtime session is not ready."
        if wants_json:
            return jsonify({"error": message, **shell_response}), 409
        flash(message, "error")
        return redirect(url_for("frontend.play_shell", session_id=session_id))
    response = request_backend(
        "POST",
        f"/api/v1/sessions/{backend_session_id}/turns",
        json_data={"player_input": player_input},
    )
    try:
        payload = require_success(response, "Runtime turn execution failed.")
    except BackendApiError as exc:
        if wants_json:
            return jsonify({"error": str(exc)}), exc.status_code
        flash(str(exc), "error")
        return redirect(url_for("frontend.play_shell", session_id=session_id))
    interpreted = (((payload.get("turn") or {}).get("interpreted_input") or {}).get("kind") or "unknown").strip()
    runtime_shell_readout = _extract_runtime_shell_readout(payload)
    if isinstance(runtime_shell_readout, dict):
        _store_play_shell_runtime_readout(session_id, runtime_shell_readout)
    try:
        shell_response = _build_play_shell_response(run_id=session_id, backend_session_id=backend_session_id)
        shell_state_view = shell_response.get("shell_state_view") or {}
        success_message = f"Turn executed in runtime (input kind: {interpreted}). {shell_state_view.get('authoritative_status_summary') or 'Authoritative refresh completed.'}"
        if wants_json:
            response_payload = dict(shell_response)
            response_payload = _merge_turn_level_addressed_output(shell_response=response_payload, payload=payload)
            response_payload.update({
                "turn": payload.get("turn"),
                "interpreted_input_kind": interpreted,
                "message": success_message,
            })
            return jsonify(response_payload), 200
        flash(success_message, "success")
    except BackendApiError as exc:
        warning_message = f"Turn executed in runtime (input kind: {interpreted}), but authoritative refresh failed: {exc}"
        if wants_json:
            return jsonify({
                "ok": True,
                "session_id": session_id,
                "backend_session_id": backend_session_id,
                "runtime_session_ready": True,
                "can_execute": True,
                "can_refresh": True,
                "turn": payload.get("turn"),
                "interpreted_input_kind": interpreted,
                "observation_source": "unavailable",
                "observation_error": str(exc),
                "observation_meta": {"source": "unavailable", "error": str(exc), "is_fresh": False, "is_cached_fallback": False, "is_unavailable": True},
                "authoritative_refresh_error": str(exc),
                "message": warning_message,
            }), 200
        flash(warning_message, "warning")
    return redirect(url_for("frontend.play_shell", session_id=session_id))


@frontend_bp.route("/api/v1/<path:subpath>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def api_proxy(subpath: str):
    """Compatibility proxy so frontend static assets can call /api/v1/* on same origin."""
    path = f"/api/v1/{subpath}"
    payload = request.get_json(silent=True)
    response = request_backend(
        request.method,
        path,
        json_data=payload if request.method in ("POST", "PUT", "PATCH", "DELETE") else None,
        params=request.args.to_dict(flat=True),
    )
    content_type = response.headers.get("Content-Type", "application/json")
    return Response(response.content, status=response.status_code, content_type=content_type)


@frontend_bp.errorhandler(BackendApiError)
def handle_backend_error(exc: BackendApiError):
    if request.path.startswith("/api/"):
        return jsonify({"error": str(exc), **exc.payload}), exc.status_code
    flash(str(exc), "error")
    return redirect(url_for("frontend.home"))


@frontend_bp.errorhandler(requests.RequestException)
def handle_request_exception(_exc: requests.RequestException):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Backend API unavailable."}), 503
    flash("Backend API unavailable.", "error")
    return redirect(url_for("frontend.home"))
