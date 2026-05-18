from __future__ import annotations

import pytest
import httpx
from fastapi.responses import JSONResponse

import app.main as main_module
import app.ui_backend_proxy as proxy_module
from app.ui_backend_proxy import user_capabilities


@pytest.mark.parametrize(
    ("user", "expected"),
    [
        (None, {"observe": False, "operate": False, "author": False, "ai_governance": False, "any_runtime": False}),
        (
            {"allowed_features": ["manage.world_engine_observe"]},
            {"observe": True, "operate": False, "author": False, "ai_governance": False, "any_runtime": True},
        ),
        (
            {"allowed_features": ["manage.world_engine_operate"]},
            {"observe": True, "operate": True, "author": False, "ai_governance": False, "any_runtime": True},
        ),
        (
            {"allowed_features": ["manage.world_engine_author"]},
            {"observe": True, "operate": True, "author": True, "ai_governance": False, "any_runtime": True},
        ),
        (
            {"allowed_features": ["manage.ai_runtime_governance"]},
            {"observe": False, "operate": False, "author": False, "ai_governance": True, "any_runtime": True},
        ),
    ],
)
def test_user_capabilities_from_allowed_features(user, expected):
    assert user_capabilities(user) == expected


def test_ui_api_proxy_forwards_when_authenticated(client, auth_backend_success, monkeypatch):
    async def _fake_proxy(request, backend_path: str):
        return JSONResponse({"proxied": backend_path})

    monkeypatch.setattr(main_module, "backend_proxy_response", _fake_proxy)
    client.post(
        "/login",
        content="username=operator&password=pw",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    response = client.get("/ui-api/admin/world-engine/health")
    assert response.status_code == 200
    assert response.json() == {"proxied": "admin/world-engine/health"}


@pytest.mark.asyncio
async def test_backend_proxy_response_uses_async_client(monkeypatch):
    captured = {}

    class FakeUrl:
        query = "limit=2"

    class FakeRequest:
        method = "POST"
        url = FakeUrl()
        headers = {"content-type": "application/json"}
        session = {proxy_module.UI_SESSION_ACCESS_TOKEN_KEY: "token-ok"}

        async def body(self):
            return b'{"probe": true}'

    class FakeAsyncClient:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method, url, *, headers, content):
            captured.update(
                {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "content": content,
                }
            )
            return httpx.Response(200, json={"data": {"ok": True}})

    def _sync_client_should_not_be_used(*_args, **_kwargs):
        raise AssertionError("ui backend proxy must not block the event loop with httpx.Client")

    monkeypatch.setattr(proxy_module, "BACKEND_RUNTIME_CONFIG_URL", "http://backend.example")
    monkeypatch.setattr(proxy_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(proxy_module.httpx, "Client", _sync_client_should_not_be_used)

    response = await proxy_module.backend_proxy_response(FakeRequest(), "admin/world-engine/health")

    assert response.status_code == 200
    assert captured["timeout"] == 30.0
    assert captured["method"] == "POST"
    assert captured["url"] == "http://backend.example/api/v1/admin/world-engine/health?limit=2"
    assert captured["headers"]["Authorization"] == "Bearer token-ok"
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["content"] == b'{"probe": true}'
