from __future__ import annotations

import pytest

import app.main as main_module


def _login(client, auth_backend_success):
    client.post(
        "/login",
        content="username=operator&password=pw",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )


@pytest.mark.parametrize(
    "path",
    [
        "/dashboard",
        "/runs-sessions",
        "/live-runtime",
        "/validation-authority",
        "/runtime-ledger",
        "/narrative-systems",
        "/traces",
        "/history",
        "/health",
        "/runtime-status",
        "/engine",
    ],
)
def test_authenticated_runtime_pages_render(client, auth_backend_success, path):
    _login(client, auth_backend_success)
    response = client.get(path)
    assert response.status_code == 200
    assert "Runtime Diagnostic Tier" in response.text


@pytest.mark.parametrize(
    "path",
    [
        "/dashboard",
        "/runs-sessions",
        "/ui-api/admin/world-engine/health",
    ],
)
def test_unauthenticated_runtime_pages_redirect_or_401(client, path):
    if path.startswith("/ui-api/"):
        response = client.get(path)
        assert response.status_code == 401
        return
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_diagnostics_redirects_to_health(client, auth_backend_success):
    _login(client, auth_backend_success)
    response = client.get("/diagnostics", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/health"


def test_ops_requires_auth(client):
    response = client.get("/ops", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_favicon_is_linked_and_served(client):
    login_response = client.get("/login")
    assert login_response.status_code == 200
    assert "/static/favicon.ico" in login_response.text

    favicon_response = client.get("/favicon.ico")
    assert favicon_response.status_code == 200
    assert favicon_response.headers["content-type"].startswith("image/vnd.microsoft.icon")
    assert favicon_response.content.startswith(b"\x00\x00\x01\x00")
