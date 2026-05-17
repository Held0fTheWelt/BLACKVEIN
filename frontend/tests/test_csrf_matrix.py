"""Regression tests for the documented CSRF matrix."""
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CSRF_MATRIX = REPO_ROOT / "docs" / "security" / "csrf-matrix.md"


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None, content=None, headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.ok = 200 <= status_code < 300
        self.content = content if content is not None else b"{}"
        self.headers = headers or {"Content-Type": "application/json"}

    def json(self):
        return self._payload


def _rule_methods(app) -> dict[str, set[str]]:
    ignored = {"HEAD", "OPTIONS"}
    return {
        rule.rule: set(rule.methods or set()) - ignored
        for rule in app.url_map.iter_rules()
    }


def test_csrf_matrix_documents_frontend_cookie_flows():
    matrix = CSRF_MATRIX.read_text(encoding="utf-8")

    assert "Frontend player forms" in matrix
    assert "Frontend same-origin API proxy `/api/v1/<path>`" in matrix
    assert "`/login`, `/logout`, `/register`" in matrix
    assert "`/play/start`, `/play/<session_id>/execute`" in matrix
    assert "`wos_backend_session_<run_id>`" in matrix


def test_frontend_session_cookie_flags_match_csrf_matrix(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_frontend_mutating_cookie_routes_match_csrf_matrix(app):
    rules = _rule_methods(app)

    assert rules["/login"] == {"GET", "POST"}
    assert rules["/logout"] == {"POST"}
    assert rules["/register"] == {"GET", "POST"}
    assert rules["/resend-verification"] == {"GET", "POST"}
    assert rules["/forgot-password"] == {"GET", "POST"}
    assert rules["/reset-password/<token>"] == {"GET", "POST"}
    assert rules["/play/start"] == {"POST"}
    assert rules["/play/<session_id>/execute"] == {"POST"}
    assert rules["/api/v1/<path:subpath>"] == {"GET", "POST", "PUT", "PATCH", "DELETE"}


def test_play_shell_backend_session_cookie_is_strict_and_httponly(client, monkeypatch):
    def fake_request_backend(method, path, **kwargs):
        assert method == "GET"
        assert path == "/api/v1/game/player-sessions/run-1"
        return FakeResponse(
            payload={
                "contract": "game_player_session_v1",
                "runtime_session_id": "story-1",
                "runtime_session_ready": True,
                "can_execute": True,
                "story_entries": [],
                "shell_state_view": {},
            }
        )

    monkeypatch.setattr("app.player_backend.request_backend", fake_request_backend)
    with client.session_transaction() as sess:
        sess["access_token"] = "token-a"

    response = client.get("/play/run-1")
    cookies = response.headers.getlist("Set-Cookie")
    backend_cookie = next(
        cookie for cookie in cookies if cookie.startswith("wos_backend_session_run-1=")
    )

    assert "Secure" in backend_cookie
    assert "HttpOnly" in backend_cookie
    assert "SameSite=Strict" in backend_cookie
