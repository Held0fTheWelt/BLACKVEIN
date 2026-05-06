"""Client helper to fetch resolved runtime config from backend."""

from __future__ import annotations

from typing import Any

import httpx


def fetch_resolved_runtime_config(*, base_url: str, token: str, timeout_seconds: float = 2.0) -> dict[str, Any] | None:
    """Fetch resolved runtime config from backend internal endpoint."""
    if not base_url.strip() or not token.strip():
        return None
    endpoint = f"{base_url.rstrip('/')}/api/v1/internal/runtime-config"
    try:
        response = httpx.get(
            endpoint,
            headers={"X-Internal-Config-Token": token, "Accept": "application/json"},
            timeout=timeout_seconds,
        )
    except Exception:
        return None
    if response.status_code != 200:
        return None
    payload = response.json()
    if not isinstance(payload, dict):
        return None
    if payload.get("ok") is True and isinstance(payload.get("data"), dict):
        return payload["data"]
    return None


def fetch_hf_hub_token_from_backend(*, base_url: str, token: str, timeout_seconds: float = 2.0) -> str | None:
    """Fetch decrypted HF Hub token from backend internal governance API."""
    if not base_url.strip() or not token.strip():
        return None
    endpoint = f"{base_url.rstrip('/')}/api/v1/internal/hf-hub/token"
    try:
        response = httpx.get(
            endpoint,
            headers={"X-Internal-Config-Token": token, "Accept": "application/json"},
            timeout=timeout_seconds,
        )
    except Exception:
        return None
    if response.status_code != 200:
        return None
    payload = response.json()
    if not isinstance(payload, dict):
        return None
    if payload.get("ok") is not True or not isinstance(payload.get("data"), dict):
        return None
    raw = payload["data"].get("token")
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None
