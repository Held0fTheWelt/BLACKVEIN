from __future__ import annotations

import pytest
from fastapi.responses import JSONResponse

import app.main as main_module
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
