"""Authenticated proxy from World-Engine UI to Backend admin/runtime APIs."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, Response

from app.config import BACKEND_RUNTIME_CONFIG_URL

UI_SESSION_ACCESS_TOKEN_KEY = "world_engine_access_token"


def backend_base_url() -> str:
    return (BACKEND_RUNTIME_CONFIG_URL or "").strip().rstrip("/")


async def backend_proxy_response(
    request: Request,
    backend_path: str,
    *,
    method: str | None = None,
    access_token_key: str = UI_SESSION_ACCESS_TOKEN_KEY,
) -> Response:
    """Forward a request to ``{BACKEND}/api/v1/{backend_path}`` using the UI session JWT."""
    access_token = request.session.get(access_token_key)
    if not access_token:
        raise HTTPException(status_code=401, detail="Authentication required.")

    base_url = backend_base_url()
    if not base_url:
        raise HTTPException(status_code=503, detail="Backend API is not configured.")

    http_method = (method or request.method).upper()
    path = backend_path.lstrip("/")
    url = f"{base_url}/api/v1/{path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    content_type = (request.headers.get("content-type") or "").strip()
    body: bytes | None = None
    if http_method in {"POST", "PUT", "PATCH", "DELETE"}:
        body = await request.body()
        if content_type:
            headers["Content-Type"] = content_type

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream = await client.request(http_method, url, headers=headers, content=body)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Backend API unavailable.") from exc

    media_type = upstream.headers.get("content-type", "application/json")
    if "application/json" in media_type:
        try:
            payload = upstream.json()
        except ValueError:
            payload = {"error": upstream.text or "Invalid JSON from backend."}
        return JSONResponse(content=payload, status_code=upstream.status_code)

    return Response(content=upstream.content, status_code=upstream.status_code, media_type=media_type)


def user_capabilities(current_user: dict[str, Any] | None) -> dict[str, bool]:
    """Derive World-Engine UI capability flags from ``allowed_features`` on /auth/me."""
    allowed: list[str] = []
    if isinstance(current_user, dict):
        raw = current_user.get("allowed_features")
        if isinstance(raw, list):
            allowed = [str(item) for item in raw]

    def _has(feature_id: str) -> bool:
        return feature_id in allowed

    author = _has("manage.world_engine_author")
    operate = author or _has("manage.world_engine_operate")
    observe = operate or _has("manage.world_engine_observe")
    ai_governance = _has("manage.ai_runtime_governance")
    return {
        "observe": observe,
        "operate": operate,
        "author": author,
        "ai_governance": ai_governance,
        "any_runtime": observe or ai_governance,
    }
