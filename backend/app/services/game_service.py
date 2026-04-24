from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from flask import current_app


# Keep module identity stable across ``app.services...`` and
# ``backend.app.services...`` import paths so exception classes are shared.
if __name__ == "app.services.game_service":
    sys.modules.setdefault("backend.app.services.game_service", sys.modules[__name__])
elif __name__ == "backend.app.services.game_service":
    sys.modules.setdefault("app.services.game_service", sys.modules[__name__])


class GameServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class GameServiceConfigError(GameServiceError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500)


def _unexpected(kind: str) -> GameServiceError:
    return GameServiceError(f"Play service returned an unexpected {kind} payload.")


def _parse_create_run_v1(payload: object) -> dict:
    """Validate nested-run V1 create response; reject contradictory flat run_id."""
    if not isinstance(payload, dict):
        raise _unexpected("create_run")
    run = payload.get("run")
    if not isinstance(run, dict):
        raise _unexpected("create_run")
    run_inner_id = run.get("id")
    if not isinstance(run_inner_id, str) or not run_inner_id.strip():
        raise _unexpected("create_run")
    top_run_id = payload.get("run_id")
    if top_run_id is not None and top_run_id != run_inner_id:
        raise GameServiceError("Play service create_run payload has contradictory run_id vs run.id.")
    if not isinstance(payload.get("store"), dict):
        raise _unexpected("create_run")
    if not isinstance(payload.get("hint"), str):
        raise _unexpected("create_run")
    return payload


def _parse_run_details_v1(payload: object, *, requested_run_id: str) -> dict:
    """Validate nested-run V1 details; reject flat-only or contradictory identity."""
    if not isinstance(payload, dict):
        raise _unexpected("run detail")
    run = payload.get("run")
    if not isinstance(run, dict):
        raise _unexpected("run detail")
    inner_id = run.get("id")
    if not isinstance(inner_id, str) or not inner_id.strip():
        raise _unexpected("run detail")
    if inner_id != requested_run_id:
        raise GameServiceError("Play service run detail run.id does not match requested run_id.")
    top_run_id = payload.get("run_id")
    if top_run_id is not None and top_run_id != inner_id:
        raise GameServiceError("Play service run detail payload has contradictory run_id vs run.id.")
    if not isinstance(payload.get("template_source"), str):
        raise _unexpected("run detail")
    template = payload.get("template")
    if not isinstance(template, dict):
        raise _unexpected("run detail")
    for key in ("id", "title", "kind", "join_policy", "min_humans_to_start"):
        if key not in template:
            raise _unexpected("run detail")
    if not isinstance(payload.get("store"), dict):
        raise _unexpected("run detail")
    lobby = payload.get("lobby")
    if lobby is not None and not isinstance(lobby, dict):
        raise _unexpected("run detail")
    return payload


def _parse_terminate_v1(payload: object, *, requested_run_id: str) -> dict:
    """Validate terminate envelope V1 (no legacy status-only success)."""
    if not isinstance(payload, dict):
        raise _unexpected("terminate")
    if payload.get("terminated") is not True:
        raise _unexpected("terminate")
    rid = payload.get("run_id")
    tid = payload.get("template_id")
    if not isinstance(rid, str) or not rid.strip():
        raise _unexpected("terminate")
    if not isinstance(tid, str) or not tid.strip():
        raise _unexpected("terminate")
    if rid != requested_run_id:
        raise GameServiceError("Play service terminate payload run_id does not match requested run_id.")
    if not isinstance(payload.get("actor_display_name"), str):
        raise _unexpected("terminate")
    if not isinstance(payload.get("reason"), str):
        raise _unexpected("terminate")
    return payload


@dataclass(slots=True)
class PlayJoinContext:
    run_id: str
    participant_id: str
    role_id: str
    display_name: str
    account_id: str | None = None
    character_id: str | None = None




def has_complete_play_service_config() -> bool:
    if current_app.config.get("PLAY_SERVICE_CONTROL_DISABLED"):
        return False
    public_url = (current_app.config.get("PLAY_SERVICE_PUBLIC_URL") or "").strip()
    internal_url = (current_app.config.get("PLAY_SERVICE_INTERNAL_URL") or "").strip()
    shared_secret = (current_app.config.get("PLAY_SERVICE_SHARED_SECRET") or "").strip()
    return bool(public_url and internal_url and shared_secret)

def _require_configured_url(kind: str) -> str:
    key = "PLAY_SERVICE_INTERNAL_URL" if kind == "internal" else "PLAY_SERVICE_PUBLIC_URL"
    value = (current_app.config.get(key) or "").strip()
    if not value:
        raise GameServiceConfigError(f"{key} is not configured.")
    return value.rstrip("/")


def get_play_service_public_url() -> str:
    return _require_configured_url("public")


def get_play_service_websocket_url() -> str:
    public_url = get_play_service_public_url()
    parsed = urlparse(public_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.netloc}".rstrip("/")


def _internal_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    api_key = (current_app.config.get("PLAY_SERVICE_INTERNAL_API_KEY") or "").strip()
    if api_key:
        headers["X-Play-Service-Key"] = api_key
    return headers


def _request(
    method: str,
    path: str,
    *,
    json_payload: dict | None = None,
    internal: bool = False,
    trace_id: str | None = None,
) -> dict | list:
    if current_app.config.get("PLAY_SERVICE_CONTROL_DISABLED"):
        raise GameServiceError(
            "Play service integration is disabled by operator control (Play-Service control surface).",
            status_code=502,
        )
    base_url = _require_configured_url("internal" if internal else "public")
    timeout = current_app.config.get("PLAY_SERVICE_REQUEST_TIMEOUT", 30)  # Use config timeout (default 30s)
    headers: dict[str, str] | None = None
    if internal:
        headers = dict(_internal_headers())
        if trace_id:
            headers["X-WoS-Trace-Id"] = trace_id
    try:
        with httpx.Client(base_url=base_url, timeout=float(timeout)) as client:
            response = client.request(method, path, json=json_payload, headers=headers)
    except httpx.RequestError as exc:
        raise GameServiceError(f"Play service unavailable: {exc}", status_code=502) from exc

    try:
        payload = response.json() if response.content else None
    except Exception:
        payload = None

    if response.status_code >= 400:
        detail = None
        if isinstance(payload, dict):
            detail = payload.get("detail") or payload.get("error")
        raise GameServiceError(detail or f"Play service request failed with {response.status_code}.", status_code=response.status_code)
    return payload


def get_play_service_ready(*, trace_id: str | None = None) -> dict:
    payload = _request("GET", "/api/health/ready", internal=True, trace_id=trace_id)
    if not isinstance(payload, dict):
        raise GameServiceError("Play service returned an unexpected ready payload.")
    return payload


def _coerce_json_object_list(payload: object, wrapped_keys: tuple[str, ...]) -> list[dict]:
    """Normalize list endpoints: raw JSON array or common ``{key: [...]}`` wrapper shapes."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in wrapped_keys:
            inner = payload.get(key)
            if isinstance(inner, list):
                return [x for x in inner if isinstance(x, dict)]
    return []


def list_templates() -> list[dict]:
    # Always use internal base URL: these calls run inside the backend process (Docker network, etc.).
    payload = _request("GET", "/api/templates", internal=True)
    return _coerce_json_object_list(payload, ("templates", "items"))


def list_runs() -> list[dict]:
    payload = _request("GET", "/api/runs", internal=True)
    return _coerce_json_object_list(payload, ("runs", "items"))


def create_run(
    *,
    template_id: str | None = None,
    account_id: str,
    display_name: str,
    character_id: str | None = None,
    runtime_profile_id: str | None = None,
    selected_player_role: str | None = None,
) -> dict:
    if not current_app.config.get("PLAY_SERVICE_ALLOW_NEW_SESSIONS", True):
        raise GameServiceError(
            "New play runs are disabled by operator control (Play-Service allow_new_sessions=false).",
            status_code=502,
        )
    json_payload: dict = {
        "account_id": str(account_id),
        "character_id": character_id,
        "display_name": display_name,
    }
    if runtime_profile_id:
        json_payload["runtime_profile_id"] = runtime_profile_id
        if selected_player_role:
            json_payload["selected_player_role"] = selected_player_role
    else:
        json_payload["template_id"] = template_id
    payload = _request("POST", "/api/runs", json_payload=json_payload, internal=True)
    return _parse_create_run_v1(payload)


def resolve_join_context(
    *,
    run_id: str,
    account_id: str,
    display_name: str,
    character_id: str | None = None,
    preferred_role_id: str | None = None,
) -> PlayJoinContext:
    payload = _request(
        "POST",
        "/api/internal/join-context",
        json_payload={
            "run_id": run_id,
            "account_id": str(account_id),
            "character_id": character_id,
            "display_name": display_name,
            "preferred_role_id": preferred_role_id,
        },
        internal=True,
    )
    if not isinstance(payload, dict):
        raise GameServiceError("Play service returned an unexpected join-context payload.")
    try:
        return PlayJoinContext(
            run_id=payload["run_id"],
            participant_id=payload["participant_id"],
            role_id=payload["role_id"],
            display_name=payload["display_name"],
            account_id=payload.get("account_id"),
            character_id=payload.get("character_id"),
        )
    except (KeyError, TypeError):
        raise GameServiceError("Play service returned an unexpected join-context payload.")


def issue_play_ticket(payload: dict, ttl_seconds: int | None = None) -> str:
    secret = (current_app.config.get("PLAY_SERVICE_SHARED_SECRET") or "").strip()
    if not secret:
        raise GameServiceConfigError("PLAY_SERVICE_SHARED_SECRET is not configured.")
    ttl = ttl_seconds or int(current_app.config.get("GAME_TICKET_TTL_SECONDS", 300))
    body = {
        **payload,
        "iat": int(time.time()),
        "exp": int(time.time()) + ttl,
    }
    raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest().encode("ascii")
    return base64.urlsafe_b64encode(raw + b"." + sig).decode("ascii")


def get_run_details(run_id: str) -> dict:
    payload = _request("GET", f"/api/runs/{run_id}", internal=True)
    return _parse_run_details_v1(payload, requested_run_id=run_id)


def get_run_transcript(run_id: str) -> dict:
    payload = _request("GET", f"/api/runs/{run_id}/transcript", internal=True)
    if not isinstance(payload, dict) or "entries" not in payload:
        raise GameServiceError("Play service returned an unexpected transcript payload.")
    return payload


def terminate_run(
    run_id: str,
    *,
    actor_display_name: str | None = None,
    reason: str | None = None,
) -> dict:
    payload = _request(
        "POST",
        f"/api/internal/runs/{run_id}/terminate",
        json_payload={
            "actor_display_name": (actor_display_name or "").strip(),
            "reason": (reason or "").strip(),
        },
        internal=True,
    )
    return _parse_terminate_v1(payload, requested_run_id=run_id)


def create_story_session(
    *,
    module_id: str,
    runtime_projection: dict,
    trace_id: str | None = None,
    content_provenance: dict | None = None,
) -> dict:
    if not current_app.config.get("PLAY_SERVICE_ALLOW_NEW_SESSIONS", True):
        raise GameServiceError(
            "New story sessions are disabled by operator control (Play-Service allow_new_sessions=false).",
            status_code=502,
        )
    payload = _request(
        "POST",
        "/api/story/sessions",
        json_payload={
            "module_id": module_id,
            "runtime_projection": runtime_projection,
            "content_provenance": content_provenance or {},
        },
        internal=True,
        trace_id=trace_id,
    )
    if not isinstance(payload, dict) or "session_id" not in payload:
        raise GameServiceError("Play service returned an unexpected story-session payload.")
    return payload


def execute_story_turn(*, session_id: str, player_input: str, trace_id: str | None = None) -> dict:
    payload = _request(
        "POST",
        f"/api/story/sessions/{session_id}/turns",
        json_payload={"player_input": player_input},
        internal=True,
        trace_id=trace_id,
    )
    if not isinstance(payload, dict) or "turn" not in payload:
        raise GameServiceError("Play service returned an unexpected story-turn payload.")
    return payload


def get_story_state(session_id: str, *, trace_id: str | None = None) -> dict:
    payload = _request("GET", f"/api/story/sessions/{session_id}/state", internal=True, trace_id=trace_id)
    if not isinstance(payload, dict):
        raise GameServiceError("Play service returned an unexpected story-state payload.")
    return payload


def get_story_diagnostics(session_id: str, *, trace_id: str | None = None) -> dict:
    payload = _request("GET", f"/api/story/sessions/{session_id}/diagnostics", internal=True, trace_id=trace_id)
    if not isinstance(payload, dict):
        raise GameServiceError("Play service returned an unexpected story-diagnostics payload.")
    return payload


def list_story_sessions(*, trace_id: str | None = None) -> dict:
    payload = _request("GET", "/api/story/sessions", internal=True, trace_id=trace_id)
    if not isinstance(payload, dict) or "items" not in payload:
        raise GameServiceError("Play service returned an unexpected story-session list payload.")
    return payload


def get_play_story_runtime_config_status(*, trace_id: str | None = None) -> dict[str, Any]:
    """Fetch governed-runtime posture from the play service (world-engine)."""
    payload = _request("GET", "/api/internal/story/runtime/config-status", internal=True, trace_id=trace_id)
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise GameServiceError("Play service returned an unexpected story runtime config-status payload.")
    return payload


def reload_play_story_runtime_governed_config(*, trace_id: str | None = None) -> dict[str, Any]:
    """Push a fresh resolved runtime config into the play service in-process story runtime."""
    payload = _request("POST", "/api/internal/story/runtime/reload-config", internal=True, trace_id=trace_id)
    if not isinstance(payload, dict):
        raise GameServiceError("Play service returned an unexpected story runtime reload-config payload.")
    return payload


def _parse_narrative_ok_data(payload: object, *, kind: str) -> dict:
    """Validate world-engine narrative governance envelope and return ``data`` object."""
    if not isinstance(payload, dict):
        raise GameServiceError(f"Play service returned an unexpected {kind} payload.")
    if payload.get("ok") is not True:
        raise GameServiceError(f"Play service returned a non-ok {kind} payload.")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise GameServiceError(f"Play service returned an unexpected {kind} data payload.")
    return data


def reload_active_narrative_package(*, module_id: str, expected_active_version: str, trace_id: str | None = None) -> dict:
    """Request world-engine active package reload for one narrative module."""
    payload = _request(
        "POST",
        "/api/internal/narrative/packages/reload-active",
        json_payload={"module_id": module_id, "expected_active_version": expected_active_version},
        internal=True,
        trace_id=trace_id,
    )
    return _parse_narrative_ok_data(payload, kind="narrative_reload_active")


def load_narrative_preview_package(
    *,
    module_id: str,
    preview_id: str,
    isolation_mode: str = "session_namespace",
    trace_id: str | None = None,
) -> dict:
    """Load one preview package into world-engine isolated preview runtime."""
    payload = _request(
        "POST",
        "/api/internal/narrative/packages/load-preview",
        json_payload={"module_id": module_id, "preview_id": preview_id, "isolation_mode": isolation_mode},
        internal=True,
        trace_id=trace_id,
    )
    return _parse_narrative_ok_data(payload, kind="narrative_load_preview")


def unload_narrative_preview_package(*, module_id: str, preview_id: str, trace_id: str | None = None) -> dict:
    """Unload one preview package from world-engine isolated preview runtime."""
    payload = _request(
        "POST",
        "/api/internal/narrative/packages/unload-preview",
        json_payload={"module_id": module_id, "preview_id": preview_id},
        internal=True,
        trace_id=trace_id,
    )
    return _parse_narrative_ok_data(payload, kind="narrative_unload_preview")


def start_narrative_preview_session(
    *,
    module_id: str,
    preview_id: str,
    session_seed: str,
    isolation_mode: str = "session_namespace",
    trace_id: str | None = None,
) -> dict:
    """Start one world-engine isolated preview session."""
    payload = _request(
        "POST",
        "/api/internal/narrative/preview/start-session",
        json_payload={
            "module_id": module_id,
            "preview_id": preview_id,
            "session_seed": session_seed,
            "isolation_mode": isolation_mode,
        },
        internal=True,
        trace_id=trace_id,
    )
    return _parse_narrative_ok_data(payload, kind="narrative_preview_start_session")


def end_narrative_preview_session(*, preview_session_id: str, trace_id: str | None = None) -> dict:
    """End one world-engine isolated preview session."""
    payload = _request(
        "POST",
        "/api/internal/narrative/preview/end-session",
        json_payload={"preview_session_id": preview_session_id},
        internal=True,
        trace_id=trace_id,
    )
    return _parse_narrative_ok_data(payload, kind="narrative_preview_end_session")


def get_narrative_runtime_state(*, module_id: str, trace_id: str | None = None) -> dict:
    """Fetch world-engine narrative runtime state for one module."""
    payload = _request(
        "GET",
        f"/api/internal/narrative/runtime/state?module_id={module_id}",
        internal=True,
        trace_id=trace_id,
    )
    return _parse_narrative_ok_data(payload, kind="narrative_runtime_state")


def get_narrative_runtime_validator_config(*, trace_id: str | None = None) -> dict:
    """Fetch world-engine narrative validator runtime configuration."""
    payload = _request(
        "GET",
        "/api/internal/narrative/runtime/validator-config",
        internal=True,
        trace_id=trace_id,
    )
    return _parse_narrative_ok_data(payload, kind="narrative_runtime_validator_config")


def get_narrative_runtime_health(*, trace_id: str | None = None) -> dict:
    """Fetch world-engine narrative runtime health summary and recent events."""
    payload = _request(
        "GET",
        "/api/internal/narrative/runtime/health",
        internal=True,
        trace_id=trace_id,
    )
    return _parse_narrative_ok_data(payload, kind="narrative_runtime_health")
