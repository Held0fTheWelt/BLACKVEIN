from __future__ import annotations

from typing import Any

import pytest

import app.main as main_module


def _login_form_data(username: str, password: str) -> str:
    return f"username={username}&password={password}"


def test_ui_login_page_renders(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "World-Engine Login" in response.text


def test_unauthenticated_dashboard_redirects_to_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_unauthenticated_embedded_page_redirects_to_login(client):
    response = client.get("/engine/app", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_successful_login_grants_access_and_renders_shell(client, auth_backend_success):
    response = client.post(
        "/login",
        content=_login_form_data("operator", "pw"),
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"
    assert auth_backend_success["login"][0]["username"] == "operator"
    assert len(auth_backend_success["me"]) == 1

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert "Runtime Dashboard" in dashboard.text
    assert "Runs / Sessions" in dashboard.text
    assert "Health" in dashboard.text
    assert "Runtime Simulator" in dashboard.text


def test_login_backend_calls_do_not_run_on_event_loop(client, monkeypatch):
    calls: list[str] = []

    def _login(username: str, password: str):
        return (
            True,
            {
                "access_token": "token-ok",
                "refresh_token": "refresh-ok",
                "user": {"username": username, "role": "admin"},
            },
            200,
        )

    def _me(token: str):
        return True, {"username": "operator", "role": "admin"}, 200

    async def _threadpool_probe(func, *args, **kwargs):
        calls.append(func.__name__)
        return func(*args, **kwargs)

    monkeypatch.setattr(main_module, "_backend_login", _login)
    monkeypatch.setattr(main_module, "_backend_fetch_user", _me)
    monkeypatch.setattr(main_module, "run_in_threadpool", _threadpool_probe)

    response = client.post(
        "/login",
        content=_login_form_data("operator", "pw"),
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert calls == ["_login", "_me"]


def test_failed_login_does_not_grant_access(client, monkeypatch):
    monkeypatch.setattr(main_module, "_backend_login", lambda *_args, **_kwargs: (False, {"error": "invalid"}, 401))
    monkeypatch.setattr(main_module, "_backend_fetch_user", lambda *_args, **_kwargs: (False, {"error": "invalid"}, 401))

    response = client.post(
        "/login",
        content=_login_form_data("operator", "bad"),
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401
    assert "Invalid username or password." in response.text

    protected = client.get("/dashboard", follow_redirects=False)
    assert protected.status_code == 303
    assert protected.headers["location"].startswith("/login")


def test_logout_clears_session_and_revokes_access(client, auth_backend_success):
    login = client.post(
        "/login",
        content=_login_form_data("operator", "pw"),
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    assert login.status_code == 303

    before_logout = client.get("/dashboard")
    assert before_logout.status_code == 200

    logout = client.post("/logout", follow_redirects=False)
    assert logout.status_code == 303
    assert logout.headers["location"] == "/login"

    after_logout = client.get("/dashboard", follow_redirects=False)
    assert after_logout.status_code == 303
    assert after_logout.headers["location"].startswith("/login")


def test_existing_engine_page_is_embedded_after_login(client, auth_backend_success):
    client.post(
        "/login",
        content=_login_form_data("operator", "pw"),
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    response = client.get("/engine")
    assert response.status_code == 200
    assert 'src="/engine/app"' in response.text


def test_no_frontend_only_auth_bypass(client):
    response = client.get("/dashboard?admin=true", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
