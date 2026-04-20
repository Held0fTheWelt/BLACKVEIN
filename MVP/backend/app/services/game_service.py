from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from flask import current_app


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


def list_templates() -> list[dict]:
    payload = _request("GET", "/api/templates")
    return payload if isinstance(payload, list) else []


def list_runs() -> list[dict]:
    payload = _request("GET", "/api/runs")
    return payload if isinstance(payload, list) else []


def create_run(*, template_id: str, account_id: str, display_name: str, character_id: str | None = None) -> dict:
    if not current_app.config.get("PLAY_SERVICE_ALLOW_NEW_SESSIONS", True):
        raise GameServiceError(
            "New play runs are disabled by operator control (Play-Service allow_new_sessions=false).",
            status_code=502,
        )
    payload = _request(
        "POST",
        "/api/runs",
        json_payload={
            "template_id": template_id,
            "account_id": str(account_id),
            "character_id": character_id,
            "display_name": display_name,
        },
    )
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
    payload = _request("GET", f"/api/runs/{run_id}")
    return _parse_run_details_v1(payload, requested_run_id=run_id)


def get_run_transcript(run_id: str) -> dict:
    payload = _request("GET", f"/api/runs/{run_id}/transcript")
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


def create_story_session(*, module_id: str, runtime_projection: dict, trace_id: str | None = None) -> dict:
    if not current_app.config.get("PLAY_SERVICE_ALLOW_NEW_SESSIONS", True):
        raise GameServiceError(
            "New story sessions are disabled by operator control (Play-Service allow_new_sessions=false).",
            status_code=502,
        )
    payload = _request(
        "POST",
        "/api/story/sessions",
        json_payload={"module_id": module_id, "runtime_projection": runtime_projection},
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
