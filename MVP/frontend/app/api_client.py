"""Backend API client for frontend service."""
from __future__ import annotations

from typing import Any

import requests
from flask import current_app, session


class BackendApiError(Exception):
    def __init__(self, message: str, *, status_code: int = 500, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


def _api_url(path: str) -> str:
    base = current_app.config["BACKEND_API_URL"].rstrip("/")
    return f"{base}{path if path.startswith('/') else '/' + path}"


def _auth_headers() -> dict[str, str]:
    token = session.get("access_token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _refresh_tokens() -> bool:
    refresh_token = session.get("refresh_token")
    if not refresh_token:
        return False
    response = requests.post(
        _api_url("/api/v1/auth/refresh"),
        headers={"Authorization": f"Bearer {refresh_token}"},
        timeout=15,
    )
    if response.status_code != 200:
        return False
    data = response.json()
    access_token = data.get("access_token")
    new_refresh = data.get("refresh_token")
    if not access_token or not new_refresh:
        return False
    session["access_token"] = access_token
    session["refresh_token"] = new_refresh
    session.modified = True
    return True


def request_backend(
    method: str,
    path: str,
    *,
    json_data: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    allow_refresh: bool = True,
) -> requests.Response:
    response = requests.request(
        method=method.upper(),
        url=_api_url(path),
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json=json_data,
        params=params,
        timeout=20,
    )
    if response.status_code == 401 and allow_refresh and _refresh_tokens():
        response = requests.request(
            method=method.upper(),
            url=_api_url(path),
            headers={**_auth_headers(), "Content-Type": "application/json"},
            json=json_data,
            params=params,
            timeout=20,
        )
    return response


def require_success(response: requests.Response, default_message: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if response.ok:
        return payload
    message = payload.get("error") or payload.get("message") or default_message
    raise BackendApiError(message, status_code=response.status_code, payload=payload)
