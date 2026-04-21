"""Extended route coverage for player/public frontend."""
from __future__ import annotations

import json

from app.api_client import BackendApiError


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None, content=None, headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.ok = 200 <= status_code < 300
        self.content = content if content is not None else b"{}"
        self.headers = headers or {"Content-Type": "application/json"}

    def json(self):
        return self._payload


def test_login_get_redirects_when_already_logged_in(client):
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.get("/login", follow_redirects=False)
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


def test_login_get_shows_form(client):
    r = client.get("/login")
    assert r.status_code == 200


def test_login_post_empty_fields(client):
    r = client.post("/login", data={"username": "", "password": ""})
    assert r.status_code == 400


def test_login_post_backend_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(status_code=401, payload={"error": "bad creds"}),
    )
    r = client.post("/login", data={"username": "a", "password": "b"})
    assert r.status_code == 401


def test_logout_post_with_token_calls_backend(client, monkeypatch):
    calls = []

    def rec(method, path, **kwargs):
        calls.append((method, path))
        return FakeResponse()

    monkeypatch.setattr("app.player_backend.request_backend", rec)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.post("/logout", follow_redirects=False)
    assert r.status_code == 302
    assert ("POST", "/api/v1/auth/logout") in calls


def test_logout_post_without_token(client, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("should not call backend")

    monkeypatch.setattr("app.player_backend.request_backend", boom)
    r = client.post("/logout", follow_redirects=False)
    assert r.status_code == 302


def test_register_get(client):
    r = client.get("/register")
    assert r.status_code == 200


def test_register_post_validation(client):
    r = client.post("/register", data={"username": "", "password": ""})
    assert r.status_code == 400


def test_register_post_password_mismatch(client):
    r = client.post(
        "/register",
        data={"username": "u", "email": "u@e.com", "password": "a", "password_confirm": "b"},
    )
    assert r.status_code == 400


def test_register_post_success(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(payload={}),
    )
    r = client.post(
        "/register",
        data={
            "username": "nu",
            "email": "nu@e.com",
            "password": "secret",
            "password_confirm": "secret",
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "/register/pending" in r.headers["Location"]


def test_register_post_api_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(status_code=409, payload={"error": "taken"}),
    )
    r = client.post(
        "/register",
        data={
            "username": "nu",
            "email": "nu@e.com",
            "password": "secret",
            "password_confirm": "secret",
        },
    )
    assert r.status_code == 409


def test_register_pending_get(client):
    r = client.get("/register/pending")
    assert r.status_code == 200


def test_resend_verification_get(client):
    r = client.get("/resend-verification")
    assert r.status_code == 200


def test_resend_verification_post_success(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(payload={"message": "sent"}),
    )
    r = client.post("/resend-verification", data={"email": "a@b.com"}, follow_redirects=False)
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_resend_verification_post_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(status_code=400, payload={"error": "no"}),
    )
    r = client.post("/resend-verification", data={"email": "a@b.com"})
    assert r.status_code == 400


def test_forgot_password_get(client):
    r = client.get("/forgot-password")
    assert r.status_code == 200


def test_forgot_password_post_success(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(payload={"message": "check mail"}),
    )
    r = client.post("/forgot-password", data={"email": "a@b.com"}, follow_redirects=False)
    assert r.status_code == 302


def test_forgot_password_post_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(status_code=503, payload={"error": "fail"}),
    )
    r = client.post("/forgot-password", data={"email": "a@b.com"})
    assert r.status_code == 503


def test_reset_password_get(client):
    r = client.get("/reset-password/tok123")
    assert r.status_code == 200


def test_reset_password_post_mismatch(client):
    r = client.post(
        "/reset-password/tok123",
        data={"password": "a", "password_confirm": "b"},
    )
    assert r.status_code == 400


def test_reset_password_post_success(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(payload={"message": "ok"}),
    )
    r = client.post(
        "/reset-password/tok123",
        data={"password": "secret", "password_confirm": "secret"},
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_reset_password_post_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(status_code=400, payload={"error": "bad token"}),
    )
    r = client.post(
        "/reset-password/tok123",
        data={"password": "secret", "password_confirm": "secret"},
    )
    assert r.status_code == 400


def test_dashboard_unauthorized_clears_session(client, monkeypatch):
    def fail(*a, **k):
        raise BackendApiError("nope", status_code=401)

    monkeypatch.setattr("app.player_backend.request_backend", fail)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"id": 1}
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]
    with client.session_transaction() as sess:
        assert sess.get("access_token") is None


def test_dashboard_backend_error_non_401_shows_flash_and_fallback_user(client, monkeypatch):
    def fail(*a, **k):
        raise BackendApiError("offline", status_code=503)

    monkeypatch.setattr("app.player_backend.request_backend", fail)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "bob"}
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert b"bob" in r.data


def test_news_ok_and_empty(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(payload={"items": [{"title": "N1"}]}),
    )
    r = client.get("/news")
    assert r.status_code == 200
    assert b"N1" in r.data

    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(status_code=500, payload={}),
    )
    r2 = client.get("/news")
    assert r2.status_code == 200


def test_wiki_index_and_slug_and_status_codes(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda m, p, **k: FakeResponse(payload={"title": "Idx"}) if p.endswith("index") else FakeResponse(),
    )
    r = client.get("/wiki")
    assert r.status_code == 200

    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda m, p, **k: FakeResponse(status_code=404, payload={}),
    )
    r404 = client.get("/wiki/missing")
    assert r404.status_code == 404

    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda m, p, **k: FakeResponse(status_code=502, payload={}),
    )
    r502 = client.get("/wiki/broken")
    assert r502.status_code == 200


def test_community_ok_and_fail(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(payload={"items": [{"title": "Cat", "description": "d"}]}),
    )
    r = client.get("/community")
    assert b"Cat" in r.data

    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(status_code=503),
    )
    r2 = client.get("/community")
    assert r2.status_code == 200


def test_game_menu_requires_login(client):
    r = client.get("/game-menu", follow_redirects=False)
    assert r.status_code == 302


def test_game_menu_renders(client):
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "pam"}
    r = client.get("/game-menu")
    assert r.status_code == 200
    assert b"Game Menu" in r.data
    assert b"Open play launcher" in r.data


def test_play_create_missing_template(client):
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.post("/play/start", data={}, follow_redirects=False)
    assert r.status_code == 302
    assert "/play" in r.headers["Location"]


def test_play_create_api_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(status_code=400, payload={"error": "no"}),
    )
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.post("/play/start", data={"template_id": "t1"}, follow_redirects=False)
    assert r.status_code == 302
    assert "/play" in r.headers["Location"]


def test_play_create_no_run_id(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(payload={"run": {}}),
    )
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.post("/play/start", data={"template_id": "t1"}, follow_redirects=False)
    assert r.status_code == 302
    assert "/play" in r.headers["Location"]


def test_play_create_success(client, monkeypatch):
    calls = []

    def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return FakeResponse(payload={"run_id": "run-99"})

    monkeypatch.setattr("app.player_backend.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.post("/play/start", data={"template_id": "t1"}, follow_redirects=False)
    assert r.status_code == 302
    assert "/play/run-99" in r.headers["Location"]
    assert calls[-1][1] == "/api/v1/game/player-sessions"
    assert calls[-1][2]["json_data"]["template_id"] == "t1"


def test_play_shell_renders_canonical_story_entries_without_ticket_or_backend_session(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/player-sessions/s1":
            return FakeResponse(
                payload={
                    "contract": "game_player_session_v1",
                    "runtime_session_id": "story-1",
                    "runtime_session_ready": True,
                    "can_execute": True,
                    "story_entries": [
                        {
                            "entry_id": "opening",
                            "role": "runtime",
                            "speaker": "World of Shadows",
                            "turn_number": 0,
                            "text": "The room is already tense.",
                        }
                    ],
                    "shell_state_view": {
                        "module_id": "god_of_carnage",
                        "current_scene_id": "scene_1",
                        "turn_counter": 0,
                    },
                }
            )
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.player_backend.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
    r = client.get("/play/s1")
    assert r.status_code == 200
    assert b'id="play-story-window"' in r.data
    assert b'id="play-input-dock"' in r.data
    assert b'name="player_input"' in r.data
    assert b"Story" in r.data
    assert b"Your Turn" in r.data
    assert b"The room is already tense." in r.data
    assert b"Connect WebSocket" not in r.data
    assert b"data-backend-session-id" not in r.data


def test_play_execute_empty_and_runtime_dispatch(client, monkeypatch):
    calls = []

    def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if path == "/api/v1/game/player-sessions/sid/turns":
            return FakeResponse(
                payload={
                    "story_entries": [
                        {"role": "player", "text": kwargs["json_data"]["player_input"], "turn_number": 1},
                        {"role": "runtime", "text": "The story answers.", "turn_number": 1},
                    ],
                    "turn": {
                        "turn_number": 1,
                        "raw_input": kwargs["json_data"]["player_input"],
                        "interpreted_input": {"kind": "speech"},
                    }
                }
            )
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.player_backend.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.post("/play/sid/execute", data={"player_input": ""}, follow_redirects=False)
    assert r.status_code == 302

    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    client.post("/play/sid/execute", data={"player_input": "I look around and wait."}, follow_redirects=False)
    assert calls
    method, path, kwargs = calls[-1]
    assert method == "POST"
    assert path == "/api/v1/game/player-sessions/sid/turns"
    assert kwargs["json_data"]["player_input"] == "I look around and wait."


def test_play_execute_json_returns_story_entries(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/player-sessions/sid/turns":
            return FakeResponse(
                payload={
                    "story_entries": [
                        {"role": "runtime", "text": "Opening pressure.", "turn_number": 0},
                        {"role": "player", "text": "wave", "turn_number": 1},
                        {"role": "runtime", "text": "The room responds.", "turn_number": 1},
                    ],
                    "story_window": {"contract": "authoritative_story_window_v1"},
                    "shell_state_view": {"current_scene_id": "scene_1"},
                    "turn": {
                        "turn_number": 1,
                        "raw_input": kwargs["json_data"]["player_input"],
                        "interpreted_input": {"kind": "ooc"},
                    },
                    "state": {"current_scene_id": "a"},
                    "diagnostics": {"diagnostics": [{"x": 1}]},
                }
            )
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.player_backend.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.post(
        "/play/sid/execute",
        data=json.dumps({"player_input": "wave"}),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is True
    assert [entry["text"] for entry in data["story_entries"]] == [
        "Opening pressure.",
        "wave",
        "The room responds.",
    ]


def test_play_shell_transcript_includes_opening_and_returned_turns(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/player-sessions/sid":
            return FakeResponse(
                payload={
                    "runtime_session_id": "story-1",
                    "runtime_session_ready": True,
                    "can_execute": True,
                    "story_entries": [
                        {"role": "runtime", "speaker": "World of Shadows", "turn_number": 0, "text": "Welcome to the table."},
                        {"role": "player", "speaker": "You", "turn_number": 1, "text": "Hello."},
                        {"role": "runtime", "speaker": "World of Shadows", "turn_number": 1, "text": "You speak; tension rises."},
                    ],
                    "shell_state_view": {"module_id": "god_of_carnage", "current_scene_id": "scene_1", "turn_counter": 1},
                }
            )
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.player_backend.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
    page = client.get("/play/sid")
    assert page.status_code == 200
    assert b"Welcome to the table." in page.data
    assert b"Hello." in page.data
    assert b"You speak; tension rises." in page.data
    assert b"internal opening prompt" not in page.data


def test_api_proxy_get_and_post(client, monkeypatch):
    class Resp:
        status_code = 201
        content = b'{"ok":true}'
        headers = {"Content-Type": "application/json"}

    def fake_request(method, url, **kwargs):
        assert "query" in kwargs.get("params", {}) or method == "POST"
        return Resp()

    monkeypatch.setattr("app.api_client.requests.request", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.get("/api/v1/news/items?query=x")
    assert r.status_code == 201
    assert r.get_json() == {"ok": True}

    r2 = client.post(
        "/api/v1/game/runs",
        json={"template_id": "x"},
        headers={"Content-Type": "application/json"},
    )
    assert r2.status_code == 201

