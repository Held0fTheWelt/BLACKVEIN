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


@dataclass(slots=True)
class PlayJoinContext:
    run_id: str
    participant_id: str
    role_id: str
    display_name: str
    account_id: str | None = None
    character_id: str | None = None




def has_complete_play_service_config() -> bool:
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


def _request(method: str, path: str, *, json_payload: dict | None = None, internal: bool = False) -> dict | list:
    base_url = _require_configured_url("internal" if internal else "public")
    try:
        with httpx.Client(base_url=base_url, timeout=10.0) as client:
            response = client.request(method, path, json=json_payload, headers=_internal_headers() if internal else None)
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
    if not isinstance(payload, dict):
        raise GameServiceError("Play service returned an unexpected create_run payload.")
    return payload


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
    return PlayJoinContext(
        run_id=payload["run_id"],
        participant_id=payload["participant_id"],
        role_id=payload["role_id"],
        display_name=payload["display_name"],
        account_id=payload.get("account_id"),
        character_id=payload.get("character_id"),
    )


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
