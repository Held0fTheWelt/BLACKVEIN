"""Extended route coverage for player/public frontend."""
from __future__ import annotations

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
        "app.routes.request_backend",
        lambda *a, **k: FakeResponse(status_code=401, payload={"error": "bad creds"}),
    )
    r = client.post("/login", data={"username": "a", "password": "b"})
    assert r.status_code == 401


def test_logout_post_with_token_calls_backend(client, monkeypatch):
    calls = []

    def rec(method, path, **kwargs):
        calls.append((method, path))
        return FakeResponse()

    monkeypatch.setattr("app.routes.request_backend", rec)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.post("/logout", follow_redirects=False)
    assert r.status_code == 302
    assert ("POST", "/api/v1/auth/logout") in calls


def test_logout_post_without_token(client, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("should not call backend")

    monkeypatch.setattr("app.routes.request_backend", boom)
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
        "app.routes.request_backend",
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
        "app.routes.request_backend",
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
        "app.routes.request_backend",
        lambda *a, **k: FakeResponse(payload={"message": "sent"}),
    )
    r = client.post("/resend-verification", data={"email": "a@b.com"}, follow_redirects=False)
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_resend_verification_post_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.request_backend",
        lambda *a, **k: FakeResponse(status_code=400, payload={"error": "no"}),
    )
    r = client.post("/resend-verification", data={"email": "a@b.com"})
    assert r.status_code == 400


def test_forgot_password_get(client):
    r = client.get("/forgot-password")
    assert r.status_code == 200


def test_forgot_password_post_success(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.request_backend",
        lambda *a, **k: FakeResponse(payload={"message": "check mail"}),
    )
    r = client.post("/forgot-password", data={"email": "a@b.com"}, follow_redirects=False)
    assert r.status_code == 302


def test_forgot_password_post_error(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.request_backend",
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
        "app.routes.request_backend",
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
        "app.routes.request_backend",
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

    monkeypatch.setattr("app.routes.request_backend", fail)
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

    monkeypatch.setattr("app.routes.request_backend", fail)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "bob"}
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert b"bob" in r.data


def test_news_ok_and_empty(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.request_backend",
        lambda *a, **k: FakeResponse(payload={"items": [{"title": "N1"}]}),
    )
    r = client.get("/news")
    assert r.status_code == 200
    assert b"N1" in r.data

    monkeypatch.setattr(
        "app.routes.request_backend",
        lambda *a, **k: FakeResponse(status_code=500, payload={}),
    )
    r2 = client.get("/news")
    assert r2.status_code == 200


def test_wiki_index_and_slug_and_status_codes(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.request_backend",
        lambda m, p, **k: FakeResponse(payload={"title": "Idx"}) if p.endswith("index") else FakeResponse(),
    )
    r = client.get("/wiki")
    assert r.status_code == 200

    monkeypatch.setattr(
        "app.routes.request_backend",
        lambda m, p, **k: FakeResponse(status_code=404, payload={}),
    )
    r404 = client.get("/wiki/missing")
    assert r404.status_code == 404

    monkeypatch.setattr(
        "app.routes.request_backend",
        lambda m, p, **k: FakeResponse(status_code=502, payload={}),
    )
    r502 = client.get("/wiki/broken")
    assert r502.status_code == 200


def test_community_ok_and_fail(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.request_backend",
        lambda *a, **k: FakeResponse(payload={"items": [{"title": "Cat", "description": "d"}]}),
    )
    r = client.get("/community")
    assert b"Cat" in r.data

    monkeypatch.setattr(
        "app.routes.request_backend",
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
        "app.routes.request_backend",
        lambda *a, **k: FakeResponse(status_code=400, payload={"error": "no"}),
    )
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.post("/play/start", data={"template_id": "t1"}, follow_redirects=False)
    assert r.status_code == 302
    assert "/play" in r.headers["Location"]


def test_play_create_no_run_id(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.request_backend",
        lambda *a, **k: FakeResponse(payload={"run": {}}),
    )
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.post("/play/start", data={"template_id": "t1"}, follow_redirects=False)
    assert r.status_code == 302
    assert "/play" in r.headers["Location"]


def test_play_create_success(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.request_backend",
        lambda *a, **k: FakeResponse(payload={"run": {"id": "run-99"}}),
    )
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.post("/play/start", data={"template_id": "t1"}, follow_redirects=False)
    assert r.status_code == 302
    assert "/play/run-99" in r.headers["Location"]
    with client.session_transaction() as sess:
        assert sess.get("play_shell_run_modules", {}).get("run-99") == "t1"


def test_play_shell_ticket_ok_and_error(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc", "participant_id": "p1", "role_id": "host", "ws_base_url": "wss://play.example.com"})
        if path == "/api/v1/game/runs/s1":
            return FakeResponse(payload={"run": {"id": "s1"}, "template_source": "backend_published", "template": {"title": "God of Carnage"}, "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/s1/transcript":
            return FakeResponse(payload={"run_id": "s1", "entries": [{"text": "A sharp opening line."}]})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-1"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"s1": "god_of_carnage"}
    r = client.get("/play/s1")
    assert r.status_code == 200
    assert b"Natural language is the primary input path" in r.data
    assert b"name=\"player_input\"" in r.data
    with client.session_transaction() as sess:
        assert sess.get("play_shell_backend_sessions", {}).get("s1") == "backend-session-1"

    monkeypatch.setattr(
        "app.routes.request_backend",
        lambda *a, **k: FakeResponse(status_code=400, payload={"error": "nope"}),
    )
    r2 = client.get("/play/s2")
    assert r2.status_code == 200


def test_play_execute_empty_and_runtime_dispatch(client, monkeypatch):
    calls = []

    def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if path == "/api/v1/sessions/backend-session-1/turns":
            return FakeResponse(
                payload={
                    "turn": {
                        "turn_number": 1,
                        "raw_input": kwargs["json_data"]["player_input"],
                        "interpreted_input": {"kind": "speech"},
                    }
                }
            )
        if path == "/api/v1/game/runs/sid":
            return FakeResponse(payload={"run": {"id": "sid", "status": "active"}, "template_source": "backend_published", "template": {"title": "God of Carnage"}, "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/sid/transcript":
            return FakeResponse(payload={"run_id": "sid", "entries": [{"text": "A sharp reply."}]})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.post("/play/sid/execute", data={"player_input": ""}, follow_redirects=False)
    assert r.status_code == 302

    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"sid": "backend-session-1"}
    client.post("/play/sid/execute", data={"player_input": "I look around and wait."}, follow_redirects=False)
    assert calls
    turn_calls = [call for call in calls if call[1] == "/api/v1/sessions/backend-session-1/turns"]
    assert turn_calls
    assert turn_calls[0][2]["json_data"]["player_input"] == "I look around and wait."
    assert any(path == "/api/v1/game/runs/sid" for _, path, _ in calls)
    assert any(path == "/api/v1/game/runs/sid/transcript" for _, path, _ in calls)
    with client.session_transaction() as sess:
        observation = sess.get("play_shell_authoritative_observations", {}).get("sid")
        assert observation["latest_entry_text"] == "A sharp reply."
        assert observation["transcript_entry_count"] == 1
        assert "shell_state_view" in observation
        assert observation["shell_state_view"]["authoritative_status_summary"].startswith("Run status: active")


def test_play_execute_rejects_missing_backend_session_binding(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/runs/sid":
            return FakeResponse(status_code=503, payload={"error": "detail down"})
        if path == "/api/v1/game/runs/sid/transcript":
            return FakeResponse(status_code=503, payload={"error": "transcript down"})
        if path == "/api/v1/sessions":
            raise AssertionError("runtime recovery should not attempt session creation without recoverable binding")
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    response = client.post("/play/sid/execute", data={"player_input": "I stay silent."}, follow_redirects=False)
    assert response.status_code == 302
    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
    assert any("Runtime session recovery is not possible from current shell state." in message for _, message in flashes)


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




def test_play_shell_gracefully_handles_missing_run_detail_and_transcript(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/s3":
            return FakeResponse(status_code=404, payload={"error": "missing detail"})
        if path == "/api/v1/game/runs/s3/transcript":
            return FakeResponse(status_code=404, payload={"error": "missing transcript"})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-3"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"s3": "god_of_carnage"}
    r = client.get("/play/s3")
    assert r.status_code == 200
    assert b"Run details are currently unavailable." in r.data
    assert b"No transcript entries available yet." in r.data


def test_play_execute_warns_when_authoritative_refresh_fails(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/sessions/backend-session-1/turns":
            return FakeResponse(payload={"turn": {"interpreted_input": {"kind": "speech"}}})
        if path == "/api/v1/game/runs/sid":
            return FakeResponse(status_code=503, payload={"error": "run detail down"})
        if path == "/api/v1/game/runs/sid/transcript":
            return FakeResponse(status_code=503, payload={"error": "run transcript down"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"sid": "backend-session-1"}
    response = client.post("/play/sid/execute", data={"player_input": "I hesitate."}, follow_redirects=False)
    assert response.status_code == 302


def test_play_shell_renders_cached_authoritative_observation_as_fallback(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/s4":
            return FakeResponse(status_code=404, payload={"error": "missing detail"})
        if path == "/api/v1/game/runs/s4/transcript":
            return FakeResponse(status_code=404, payload={"error": "missing transcript"})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-4"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"s4": "god_of_carnage"}
        sess["play_shell_authoritative_observations"] = {
            "s4": {
                "template_title": "God of Carnage",
                "template_source": "backend_published",
                "lobby_status": "active",
                "transcript_entry_count": 2,
                "latest_entry_text": "Cached authoritative line.",
                "run_detail": {"run": {"id": "s4"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}},
                "transcript": {"entries": [{"text": "Cached authoritative line."}]},
            }
        }
    r = client.get("/play/s4")
    assert r.status_code == 200
    assert b"Latest authoritative observation" in r.data
    assert b"Cached authoritative line." in r.data


def test_play_execute_json_returns_authoritative_shell_state_bundle(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/sessions/backend-session-1/turns":
            return FakeResponse(payload={"turn": {"interpreted_input": {"kind": "speech"}}})
        if path == "/api/v1/game/runs/sid":
            return FakeResponse(payload={"run": {"id": "sid", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/sid/transcript":
            return FakeResponse(payload={"run_id": "sid", "entries": [{"text": "A sharp reply."}, {"text": "Another line."}]})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"sid": "backend-session-1"}
    response = client.post("/play/sid/execute", json={"player_input": "I look around and wait."}, headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["interpreted_input_kind"] == "speech"
    assert data["shell_state_view"]["run_title"] == "God of Carnage"
    assert data["shell_state_view"]["transcript_entry_count"] == 2
    assert data["shell_state_view"]["latest_entry_text"] == "Another line."
    assert data["shell_state_view"]["transcript_preview"] == ["A sharp reply.", "Another line."]
    assert data["shell_state_view"]["authoritative_status_summary"] == "Run status: active · Lobby: active · Transcript entries: 2 · Latest line: Another line."
    assert "Run status: active" in data["message"]


def test_play_execute_json_returns_error_for_missing_backend_session_binding(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/runs/sid":
            return FakeResponse(status_code=503, payload={"error": "detail down"})
        if path == "/api/v1/game/runs/sid/transcript":
            return FakeResponse(status_code=503, payload={"error": "transcript down"})
        if path == "/api/v1/sessions":
            raise AssertionError("runtime recovery should not attempt session creation without recoverable binding")
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    response = client.post("/play/sid/execute", json={"player_input": "I stay silent."}, headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 409
    data = response.get_json()
    assert data["runtime_recovery_status"] == "not_ready"
    assert data["error"].startswith("Runtime session recovery is not possible from current shell state.")


def test_play_shell_renders_no_reload_coherence_hooks(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/s5":
            return FakeResponse(payload={"run": {"id": "s5", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/s5/transcript":
            return FakeResponse(payload={"run_id": "s5", "entries": [{"text": "Observed line."}]})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-5"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

        
    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"s5": "god_of_carnage"}
    r = client.get("/play/s5")
    assert r.status_code == 200
    assert b'id="execute-form"' in r.data
    assert b'id="shell-execute-status"' in r.data
    assert b'id="transcript-preview-list"' in r.data


def test_play_shell_prefers_fresh_authoritative_bundle_over_stale_cached_observation(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/s6":
            return FakeResponse(payload={"run": {"id": "s6", "status": "paused", "template_title": "Fresh Title"}, "template": {"title": "Fresh Title"}, "template_source": "backend_published", "lobby": {"status": "paused"}})
        if path == "/api/v1/game/runs/s6/transcript":
            return FakeResponse(payload={"run_id": "s6", "entries": [{"text": "Fresh authoritative line."}]})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-6"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"s6": "god_of_carnage"}
        sess["play_shell_authoritative_observations"] = {
            "s6": {
                "template_title": "Stale Title",
                "template_source": "stale_source",
                "lobby_status": "active",
                "transcript_entry_count": 9,
                "latest_entry_text": "Stale line.",
                "shell_state_view": {"run_title": "Stale Title", "authoritative_status_summary": "stale"},
                "run_detail": {"run": {"id": "s6", "status": "active"}},
                "transcript": {"entries": [{"text": "Stale line."}]},
            }
        }
    r = client.get("/play/s6")
    assert r.status_code == 200
    assert b"Fresh Title" in r.data
    assert b"Fresh authoritative line." in r.data
    assert b"Run status: paused" in r.data
    with client.session_transaction() as sess:
        observation = sess.get("play_shell_authoritative_observations", {}).get("s6")
        assert observation["template_title"] == "Fresh Title"
        assert observation["latest_entry_text"] == "Fresh authoritative line."


def test_play_shell_renders_authoritative_status_summary(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/s7":
            return FakeResponse(payload={"run": {"id": "s7", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/s7/transcript":
            return FakeResponse(payload={"run_id": "s7", "entries": [{"text": "Observed line."}]})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-7"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"s7": "god_of_carnage"}
    r = client.get("/play/s7")
    assert r.status_code == 200
    assert b"Run status: active" in r.data
    assert b"Transcript entries: 1" in r.data


def test_play_observe_returns_authoritative_shell_state_bundle(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/runs/s8":
            return FakeResponse(payload={"run": {"id": "s8", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/s8/transcript":
            return FakeResponse(payload={"run_id": "s8", "entries": [{"text": "Observed line."}, {"text": "Newest observed line."}]})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    response = client.get("/play/s8/observe", headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["shell_state_view"]["run_status"] == "active"
    assert data["shell_state_view"]["latest_entry_text"] == "Newest observed line."


def test_play_shell_renders_refresh_observation_button(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/s9":
            return FakeResponse(payload={"run": {"id": "s9", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/s9/transcript":
            return FakeResponse(payload={"run_id": "s9", "entries": [{"text": "Observed line."}]})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-9"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"s9": "god_of_carnage"}
    r = client.get("/play/s9")
    assert r.status_code == 200
    assert b'id="refresh-observation-btn"' in r.data
    assert b'/play/s9/observe' in r.data


def test_play_execute_json_and_followup_observe_share_coherent_bundle_shape(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/sessions/backend-session-1/turns":
            return FakeResponse(payload={"turn": {"interpreted_input": {"kind": "speech"}}})
        if path == "/api/v1/game/runs/sid":
            return FakeResponse(payload={"run": {"id": "sid", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/sid/transcript":
            return FakeResponse(payload={"run_id": "sid", "entries": [{"text": "A sharp reply."}, {"text": "Another line."}]})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"sid": "backend-session-1"}

    execute_response = client.post("/play/sid/execute", json={"player_input": "I look around and wait."}, headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    observe_response = client.get("/play/sid/observe", headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    execute_data = execute_response.get_json()
    observe_data = observe_response.get_json()
    assert execute_response.status_code == 200
    assert observe_response.status_code == 200
    assert execute_data["shell_state_view"]["authoritative_status_summary"] == observe_data["shell_state_view"]["authoritative_status_summary"]
    assert execute_data["shell_state_view"]["latest_entry_text"] == observe_data["shell_state_view"]["latest_entry_text"]



def test_play_shell_renders_observation_source_and_runtime_session_ready(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/s10":
            return FakeResponse(payload={"run": {"id": "s10", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/s10/transcript":
            return FakeResponse(payload={"run_id": "s10", "entries": [{"text": "Observed line."}]})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-10"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"s10": "god_of_carnage"}
    r = client.get("/play/s10")
    assert r.status_code == 200
    assert b'Observation source:' in r.data
    assert b'>fresh<' in r.data
    assert b'Runtime session ready:' in r.data
    assert b'>yes<' in r.data


def test_play_shell_uses_cached_fallback_source_when_authoritative_fetch_fails(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/s11":
            return FakeResponse(status_code=503, payload={"error": "detail down"})
        if path == "/api/v1/game/runs/s11/transcript":
            return FakeResponse(status_code=503, payload={"error": "transcript down"})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-11"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"s11": "god_of_carnage"}
        sess["play_shell_authoritative_observations"] = {
            "s11": {
                "run_detail": {"run": {"id": "s11", "status": "paused"}, "template": {"title": "Cached Title"}, "template_source": "backend_published", "lobby": {"status": "paused"}},
                "transcript": {"entries": [{"text": "Cached line."}]},
                "shell_state_view": {"run_title": "Cached Title", "run_status": "paused", "transcript_entry_count": 1, "latest_entry_text": "Cached line.", "transcript_preview": ["Cached line."], "authoritative_status_summary": "Run status: paused · Lobby: paused · Transcript entries: 1 · Latest line: Cached line."},
                "template_title": "Cached Title",
                "template_source": "backend_published",
                "lobby_status": "paused",
                "transcript_entry_count": 1,
                "latest_entry_text": "Cached line.",
            }
        }
    r = client.get("/play/s11")
    assert r.status_code == 200
    assert b'>cached_fallback<' in r.data
    assert b'detail down' in r.data or b'transcript down' in r.data


def test_play_observe_returns_observation_source_and_runtime_session_flags(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/runs/s12":
            return FakeResponse(payload={"run": {"id": "s12", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/s12/transcript":
            return FakeResponse(payload={"run_id": "s12", "entries": [{"text": "Observed line."}]})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"s12": "backend-session-12"}
    response = client.get("/play/s12/observe", headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["observation_source"] == "fresh"
    assert data["runtime_session_ready"] is True
    assert data["backend_session_id"] == "backend-session-12"
    assert data["can_refresh"] is True


def test_play_execute_json_returns_runtime_ready_and_observation_source(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/sessions/backend-session-1/turns":
            return FakeResponse(payload={"turn": {"interpreted_input": {"kind": "speech"}}})
        if path == "/api/v1/game/runs/sid":
            return FakeResponse(payload={"run": {"id": "sid", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/sid/transcript":
            return FakeResponse(payload={"run_id": "sid", "entries": [{"text": "A sharp reply."}]})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"sid": "backend-session-1"}
    response = client.post("/play/sid/execute", json={"player_input": "I wait."}, headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["runtime_session_ready"] is True
    assert data["can_execute"] is True
    assert data["observation_source"] == "fresh"



def test_play_shell_embeds_initial_authoritative_shell_state_json(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/s7":
            return FakeResponse(payload={"run": {"id": "s7", "status": "active", "template_title": "GoC"}, "template": {"title": "GoC"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/s7/transcript":
            return FakeResponse(payload={"run_id": "s7", "entries": [{"text": "Fresh line."}]})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-7"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"s7": "god_of_carnage"}
    r = client.get("/play/s7")
    assert r.status_code == 200
    assert b'id="initial-shell-state"' in r.data
    assert b'"observation_meta": {"error": null, "is_cached_fallback": false, "is_fresh": true, "is_unavailable": false, "source": "fresh"}' in r.data


def test_play_observe_returns_observation_meta(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/runs/s8":
            return FakeResponse(payload={"run": {"id": "s8", "status": "active", "template_title": "GoC"}, "template": {"title": "GoC"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/s8/transcript":
            return FakeResponse(payload={"run_id": "s8", "entries": [{"text": "Observe line."}]})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"s8": "backend-session-8"}
    r = client.get("/play/s8/observe", headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["observation_meta"]["is_fresh"] is True
    assert data["runtime_session_ready"] is True
    assert data["shell_state_view"]["run_status"] == "active"


def test_play_observe_falls_back_to_cached_authoritative_observation(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/runs/s9":
            return FakeResponse(status_code=503, payload={"error": "detail down"})
        if path == "/api/v1/game/runs/s9/transcript":
            return FakeResponse(status_code=503, payload={"error": "transcript down"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"s9": "backend-session-9"}
        sess["play_shell_authoritative_observations"] = {"s9": {"run_id": "s9", "run_detail": {"run": {"id": "s9", "status": "paused", "template_title": "Cached GoC"}, "template": {"title": "Cached GoC"}, "template_source": "backend_published", "lobby": {"status": "paused"}}, "transcript": {"entries": [{"text": "Cached line."}]}, "transcript_entry_count": 1, "latest_entry_text": "Cached line.", "template_title": "Cached GoC", "template_source": "backend_published", "lobby_status": "paused", "run_status": "paused", "shell_state_view": {"run_title": "Cached GoC", "template_source": "backend_published", "lobby_status": "paused", "run_status": "paused", "transcript_entry_count": 1, "latest_entry_text": "Cached line.", "transcript_preview": ["Cached line."], "authoritative_status_summary": "Run status: paused · Lobby: paused · Transcript entries: 1 · Latest line: Cached line."}}}
    r = client.get("/play/s9/observe", headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["observation_meta"]["is_cached_fallback"] is True
    assert data["shell_state_view"]["latest_entry_text"] == "Cached line."


def test_play_shell_recovers_backend_session_from_authoritative_run_detail_when_mapping_missing(client, monkeypatch):
    calls = []

    def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs.get("json_data")))
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/recover-shell":
            return FakeResponse(payload={
                "run": {"id": "recover-shell", "status": "active", "template_title": "Recovered GoC"},
                "template_source": "backend_published",
                "template": {"id": "god_of_carnage_solo", "title": "Recovered GoC", "kind": "solo_story", "join_policy": "solo", "min_humans_to_start": 1},
                "lobby": {"status": "active"},
            })
        if path == "/api/v1/game/runs/recover-shell/transcript":
            return FakeResponse(payload={"run_id": "recover-shell", "entries": [{"text": "Recovered observation line."}]})
        if path == "/api/v1/sessions":
            assert kwargs.get("json_data") == {"module_id": "god_of_carnage_solo"}
            return FakeResponse(payload={"session_id": "backend-session-recover-shell"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
    response = client.get("/play/recover-shell")
    assert response.status_code == 200
    assert b'id="runtime-session-id">backend-session-recover-shell<' in response.data
    assert b'id="runtime-recovery-status">recovered<' in response.data
    with client.session_transaction() as sess:
        assert sess.get("play_shell_backend_sessions", {}).get("recover-shell") == "backend-session-recover-shell"
        assert sess.get("play_shell_run_modules", {}).get("recover-shell") == "god_of_carnage_solo"
    assert ("POST", "/api/v1/sessions", {"module_id": "god_of_carnage_solo"}) in calls



def test_play_observe_recovers_backend_session_from_cached_authoritative_observation(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/runs/recover-cache":
            return FakeResponse(status_code=503, payload={"error": "detail down"})
        if path == "/api/v1/game/runs/recover-cache/transcript":
            return FakeResponse(status_code=503, payload={"error": "transcript down"})
        if path == "/api/v1/sessions":
            assert kwargs.get("json_data") == {"module_id": "god_of_carnage_solo"}
            return FakeResponse(payload={"session_id": "backend-session-recover-cache"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_authoritative_observations"] = {
            "recover-cache": {
                "run_id": "recover-cache",
                "run_detail": {
                    "run": {"id": "recover-cache", "status": "paused", "template_title": "Cached GoC"},
                    "template": {"id": "god_of_carnage_solo", "title": "Cached GoC", "kind": "solo_story", "join_policy": "solo", "min_humans_to_start": 1},
                    "template_source": "backend_published",
                    "lobby": {"status": "paused"},
                },
                "transcript": {"entries": [{"text": "Cached line."}]},
                "shell_state_view": {"run_title": "Cached GoC", "template_source": "backend_published", "lobby_status": "paused", "run_status": "paused", "transcript_entry_count": 1, "latest_entry_text": "Cached line.", "transcript_preview": ["Cached line."], "authoritative_status_summary": "Run status: paused · Lobby: paused · Transcript entries: 1 · Latest line: Cached line."},
                "template_title": "Cached GoC",
                "template_source": "backend_published",
                "lobby_status": "paused",
                "run_status": "paused",
                "transcript_entry_count": 1,
                "latest_entry_text": "Cached line.",
            }
        }
    response = client.get("/play/recover-cache/observe", headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["observation_source"] == "cached_fallback"
    assert data["runtime_session_ready"] is True
    assert data["backend_session_id"] == "backend-session-recover-cache"
    assert data["runtime_recovery_status"] == "recovered"
    assert data["runtime_recovery"]["module_binding_source"] == "cached_authoritative_observation"
    with client.session_transaction() as sess:
        assert sess.get("play_shell_backend_sessions", {}).get("recover-cache") == "backend-session-recover-cache"
        assert sess.get("play_shell_run_modules", {}).get("recover-cache") == "god_of_carnage_solo"



def test_play_execute_json_recovers_backend_session_before_turn_dispatch(client, monkeypatch):
    calls = []

    def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs.get("json_data")))
        if path == "/api/v1/game/runs/recover-execute":
            return FakeResponse(payload={
                "run": {"id": "recover-execute", "status": "active", "template_title": "Recovered GoC"},
                "template_source": "backend_published",
                "template": {"id": "god_of_carnage_solo", "title": "Recovered GoC", "kind": "solo_story", "join_policy": "solo", "min_humans_to_start": 1},
                "lobby": {"status": "active"},
            })
        if path == "/api/v1/game/runs/recover-execute/transcript":
            return FakeResponse(payload={"run_id": "recover-execute", "entries": [{"text": "Fresh line after recovery."}]})
        if path == "/api/v1/sessions":
            assert kwargs.get("json_data") == {"module_id": "god_of_carnage_solo"}
            return FakeResponse(payload={"session_id": "backend-session-recover-execute"})
        if path == "/api/v1/sessions/backend-session-recover-execute/turns":
            return FakeResponse(payload={"turn": {"interpreted_input": {"kind": "speech"}}})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    response = client.post(
        "/play/recover-execute/execute",
        json={"player_input": "I recover and continue."},
        headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["runtime_session_ready"] is True
    assert data["backend_session_id"] == "backend-session-recover-execute"
    assert any(path == "/api/v1/sessions" for _, path, _ in calls)
    assert any(path == "/api/v1/sessions/backend-session-recover-execute/turns" for _, path, _ in calls)
    with client.session_transaction() as sess:
        assert sess.get("play_shell_backend_sessions", {}).get("recover-execute") == "backend-session-recover-execute"
        assert sess.get("play_shell_run_modules", {}).get("recover-execute") == "god_of_carnage_solo"



def test_play_shell_renders_explicit_bounded_failure_when_runtime_recovery_is_impossible(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/unrecoverable":
            return FakeResponse(status_code=503, payload={"error": "detail down"})
        if path == "/api/v1/game/runs/unrecoverable/transcript":
            return FakeResponse(status_code=503, payload={"error": "transcript down"})
        if path == "/api/v1/sessions":
            raise AssertionError("runtime recovery should not attempt session creation without recoverable binding")
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
    response = client.get("/play/unrecoverable")
    assert response.status_code == 200
    assert b'id="runtime-session-ready">no<' in response.data
    assert b'id="runtime-recovery-status">not_ready<' in response.data
    assert b'Runtime session recovery is not possible from current shell state.' in response.data



def test_play_execute_json_merges_runtime_shell_readout_projection(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/sessions/backend-session-1/turns":
            return FakeResponse(payload={
                "turn": {"interpreted_input": {"kind": "speech"}},
                "state": {
                    "committed_state": {
                        "shell_readout_projection": {
                            "social_weather_now": "Exit pressure is dominating the room; even practical movement is reading as failed repair.",
                            "live_surface_now": "The doorway is the hot surface right now; hovering there reads as departure pressure, not neutral movement.",
                            "carryover_now": "Departure shame is still active; the room has not spent the earlier failed-exit pressure.",
                            "social_geometry_now": "Pressure is sitting with the host side and spouse axis rather than the guests.",
                            "situational_freedom_now": "Distance shifts, hovering, and trying not to leave cleanly will all be socially legible here.",
                            "address_pressure_now": "Veronique is effectively pressing you through failed departure pressure; the doorway is acting like an accusation, not a neutral exit.",
                            "social_moment_now": "This is a failed-exit moment under brittle civility.",
                            "response_pressure_now": "The room is pressing for repair, explanation, or a refusal to leave cleanly.",
                "response_address_source_now": "Veronique answers from the host side through the spouse axis in failed repair, with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction.",
                "response_exchange_now": "Your act drew a failed repair answer because your move turned departure into repair pressure.",
                "response_exchange_label_now": "failed repair",
                "response_line_prefix_now": "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway",
                            "who_answers_now": "Veronique is the one answering now; the host side is speaking through spouse embarrassment, with civility hardening into correction.",
                            "why_this_reply_now": "The room read the act as failed repair, so the host side answered through spouse embarrassment at the doorway and let the reply pull the moment back under principle instead of letting the exit close it, in a principle-first rebuke that uses civility as correction.",
                            "observation_foothold_now": "You are inside a failed-exit exchange now; the host side is answering through departure pressure and restraint still reads as part of the exchange.",
                            "room_pressure_now": "The room feels exit-loaded; the doorway still reads as a social trap.",
                            "zone_sensitivity_now": "The doorway zone is socially charged; hovering there will read as pressure, not neutral movement.",
                "reaction_delta_now": "Your last move tightened departure pressure; the room turned practical movement into failed repair.",
                "carryover_delta_now": "An earlier failed-exit wound was reactivated now; departure shame is not merely lingering.",
                "pressure_shift_delta_now": "Pressure shifted onto the spouse axis and host-side embarrassment rather than staying with movement itself.",
                "hot_surface_delta_now": "The doorway became newly hot because the last move made departure pressure live again.",
                            "salient_object_now": "The threshold itself is acting like a pressure object.",
                            "object_sensitivity_now": "The threshold itself is carrying object-like pressure; hovering there will read as failed departure, not idle movement.",
                            "continued_wound_now": "Departure shame is still active; the room has not released the wish to leave.",
                            "role_pressure_now": "Veronique is carrying host-side pressure; the room is reading this as a boundary problem, not a neutral act.",
                            "callback_pressure_now": "This is still behaving like a callback; the room is reusing an earlier wound rather than reacting from scratch.",
                            "active_pressure_now": "Still live: departure pressure, reading dispute",
                            "recent_act_social_meaning": "The last act tightened the social trap instead of creating a clean way out.",
                            "dominant_social_reading_now": "It is landing as failed repair and renewed departure pressure rather than a clean practical move.",
                            "social_axis_now": "The host side and spouse axis are carrying the weight; Veronique is taking the room's boundary reading.",
                            "host_guest_pressure_now": "Host-side pressure is carrying more of the room; the guests have more room to watch than absorb.",
                            "spouse_axis_now": "One partner is carrying social cost for the other's act; the spouse axis is not settled.",
                            "cross_couple_now": "Cross-couple strain is live, though it is not fully taking over the room.",
                            "pressure_redistribution_now": "Pressure has shifted from practical movement into spouse embarrassment and departure shame.",
                            "object_social_reading_now": "Right now the threshold reads as a failed-departure surface more than a neutral edge.",
                            "callback_role_frame_now": "The callback is reviving departure shame and failed repair rather than opening a new issue.",
                            "situational_affordance_now": "Threshold movement, staying back, or edging toward the door are all socially legible right now.",
                            "reaction_delta_now": "Your last move tightened departure pressure; the room turned practical movement into failed repair.",
                            "carryover_delta_now": "An earlier failed-exit wound was reactivated now; departure shame is not merely lingering.",
                            "pressure_shift_delta_now": "Pressure shifted onto the spouse axis and host-side embarrassment rather than staying with movement itself.",
                            "hot_surface_delta_now": "The doorway became newly hot because the last move made departure pressure live again.",
                        }
                    }
                },
            })
        if path == "/api/v1/game/runs/sid":
            return FakeResponse(payload={"run": {"id": "sid", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/sid/transcript":
            return FakeResponse(payload={"run_id": "sid", "entries": [{"text": "A sharp reply."}]})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"sid": "backend-session-1"}
    response = client.post("/play/sid/execute", json={"player_input": "I hover at the door."}, headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 200
    data = response.get_json()
    shell = data["shell_state_view"]
    assert shell["social_weather_now"].startswith("Exit pressure is dominating the room")
    assert shell["live_surface_now"].startswith("The doorway is the hot surface right now")
    assert shell["carryover_now"].startswith("Departure shame is still active")
    assert shell["social_geometry_now"].startswith("Pressure is sitting with the host side and spouse axis")
    assert shell["situational_freedom_now"].startswith("Distance shifts, hovering")
    assert shell["room_pressure_now"].startswith("The room feels exit-loaded")
    assert shell["zone_sensitivity_now"].startswith("The doorway zone is socially charged")
    assert shell["salient_object_now"].startswith("The threshold")
    assert shell["object_sensitivity_now"].startswith("The threshold itself is carrying object-like pressure")
    assert shell["continued_wound_now"].startswith("Departure shame")
    assert shell["callback_pressure_now"].startswith("This is still behaving like a callback")
    assert shell["dominant_social_reading_now"].startswith("It is landing as failed repair")
    assert shell["social_axis_now"].startswith("The host side and spouse axis")
    assert shell["host_guest_pressure_now"].startswith("Host-side pressure is carrying more of the room")
    assert shell["spouse_axis_now"].startswith("One partner is carrying social cost")
    assert shell["cross_couple_now"].startswith("Cross-couple strain is live")
    assert shell["pressure_redistribution_now"].startswith("Pressure has shifted from practical movement")
    assert shell["callback_role_frame_now"].startswith("The callback is reviving departure shame")
    assert shell["object_social_reading_now"].startswith("Right now the threshold reads as a failed-departure surface")
    assert shell["recent_act_social_meaning"].startswith("The last act tightened the social trap")
    assert shell["situational_affordance_now"].startswith("Threshold movement")
    assert shell["reaction_delta_now"].startswith("Your last move tightened departure pressure")
    assert shell["carryover_delta_now"].startswith("An earlier failed-exit wound was reactivated now")
    assert shell["pressure_shift_delta_now"].startswith("Pressure shifted onto the spouse axis")
    assert shell["response_address_source_now"] == "Veronique answers from the host side through the spouse axis in failed repair, with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction."
    assert shell["response_exchange_now"].startswith("Your act drew a failed repair answer")
    assert shell["response_exchange_label_now"] == "failed repair"
    assert shell["response_line_prefix_now"] == "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway"
    assert shell["latest_entry_text"] == "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway — A sharp reply."
    assert shell["transcript_preview"] == ["Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway — A sharp reply."]


def test_play_shell_frames_latest_transcript_with_runtime_response_address(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/sx":
            return FakeResponse(payload={"run": {"id": "sx", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/sx/transcript":
            return FakeResponse(payload={"run_id": "sx", "entries": [{"text": "A sharp reply."}]})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-sx"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"sx": "god_of_carnage"}
        sess["play_shell_runtime_readouts"] = {
            "sx": {
                "response_address_source_now": "Veronique answers from the host side through the spouse axis in failed repair, with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction.",
                "response_exchange_now": "Your act drew a failed repair answer because your move turned departure into repair pressure.",
                "response_exchange_label_now": "failed repair",
                "response_line_prefix_now": "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway",
            }
        }
    r = client.get("/play/sx")
    assert r.status_code == 200
    assert "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway — A sharp reply." in r.get_data(as_text=True)


def test_play_shell_renders_cached_runtime_shell_readout_fields(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/s13":
            return FakeResponse(payload={"run": {"id": "s13", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/s13/transcript":
            return FakeResponse(payload={"run_id": "s13", "entries": [{"text": "Observed line."}]})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-13"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"s13": "god_of_carnage"}
        sess["play_shell_runtime_readouts"] = {
            "s13": {
                "social_weather_now": "Judgment is dominating the room; taste and household status are doing more work than repair.",
                "live_surface_now": "The books are the hot surface right now; touching them reads as taste and status judgment.",
                "carryover_now": "The earlier books/taste wound is still live enough to be reused as judgment.",
                "social_geometry_now": "Pressure is sitting with the host side and spouse axis rather than the guests.",
                "situational_freedom_now": "Touching, not touching, helping around, or standing off from the loaded household surface will all mean something here.",
                "address_pressure_now": "Annette is effectively pressing you through taste and household judgment, not just object attention.",
                "social_moment_now": "This is a judgment-and-status moment rather than neutral room talk.",
                "response_pressure_now": "The room is pressing for restraint or explanation around taste, manners, and status.",
                "response_address_source_now": "Annette answers from the guest side across the couples in accusation, with cross-couple strain on the books, in a cutting contradiction that treats principle as performance.",
                "response_exchange_now": "Your act drew an accusation answer because your move made taste and status the live wound.",
                "response_exchange_label_now": "accusation",
                "response_line_prefix_now": "Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, the earlier taste-and-status wound still sitting on the books",
                "who_answers_now": "Annette is the one answering now; the guest side is speaking through cross-couple strain, with wit exposing morality as pose.",
                "why_this_reply_now": "The room read the act as taste and household judgment, so cross-couple strain answered through the books and let the reply pull the room back to exposed contradiction instead of letting manners cover it, in a cutting contradiction that treats principle as performance.",
                "observation_foothold_now": "You are inside a judgment exchange now; the guest side is answering through taste, manners, and status.",
                "reaction_delta_now": "Your last move turned object handling into taste and status judgment.",
                "carryover_delta_now": "An earlier taste-and-status wound was pulled back into active judgment now.",
                "pressure_shift_delta_now": "Pressure shifted into cross-couple strain; the room is temporarily reading across the pairs.",
                "hot_surface_delta_now": "The books are hot because the last move turned them into a fresh taste-and-status wound.",
                "room_pressure_now": "The room feels judgment-heavy; blame is carrying more weight than repair.",
                "zone_sensitivity_now": "The object-rich center of the room is socially hot; touching things there will not read as incidental.",
                "salient_object_now": "The books are carrying taste, status, and household judgment.",
                "object_sensitivity_now": "The books are a taste-and-status surface; handling them will read as judgment, manners, or intrusion.",
                "continued_wound_now": "An earlier slight is still live beneath a thin attempt to smooth it over.",
                "role_pressure_now": "Veronique is carrying host-side pressure; the room is reading this as a boundary problem, not a neutral act.",
                "callback_pressure_now": "This is still behaving like a callback; the room is reusing an earlier wound rather than reacting from scratch.",
                "active_pressure_now": "Still live: blame pressure, fragile repair",
                "recent_act_social_meaning": "The room is treating the last act as meaningful, not incidental.",
                "dominant_social_reading_now": "It is landing as judgment around taste and household status rather than neutral handling.",
                "social_axis_now": "The host side and spouse axis are carrying the weight; Veronique is taking the room's boundary reading.",
                "host_guest_pressure_now": "Host-side pressure is more visible than guest-side ease right now.",
                "spouse_axis_now": "One partner is carrying social cost for the other's act; the spouse axis is not settled.",
                "cross_couple_now": "Cross-couple strain is live, though it is not fully taking over the room.",
                "pressure_redistribution_now": "Pressure has shifted from object handling into taste judgment and household status strain.",
                "object_social_reading_now": "Right now the books read as a taste-and-status wound more than background decor.",
                "callback_role_frame_now": "The callback is reusing taste and status as judgment.",
                "situational_affordance_now": "Approaching, handling, helping, or deliberately not touching the loaded household surfaces will all read socially.",
            }
        }
    r = client.get("/play/s13")
    assert r.status_code == 200
    assert b"Judgment is dominating the room; taste and household status are doing more work than repair." in r.data
    assert b"The books are the hot surface right now; touching them reads as taste and status judgment." in r.data
    assert b"The earlier books/taste wound is still live enough to be reused as judgment." in r.data
    assert b"Pressure is sitting with the host side and spouse axis rather than the guests." in r.data
    assert b"Touching, not touching, helping around, or standing off from the loaded household surface will all mean something here." in r.data
    assert b"Annette is effectively pressing you through taste and household judgment, not just object attention." in r.data
    assert b"This is a judgment-and-status moment rather than neutral room talk." in r.data
    assert b"The room is pressing for restraint or explanation around taste, manners, and status." in r.data
    assert b"Annette is the one answering now; the guest side is speaking through cross-couple strain, with wit exposing morality as pose." in r.data
    assert b"The room read the act as taste and household judgment, so cross-couple strain answered through the books and let the reply pull the room back to exposed contradiction instead of letting manners cover it, in a cutting contradiction that treats principle as performance." in r.data
    assert b"You are inside a judgment exchange now; the guest side is answering through taste, manners, and status." in r.data
    assert b"Your last move turned object handling into taste and status judgment." in r.data
    assert b"An earlier taste-and-status wound was pulled back into active judgment now." in r.data


def test_play_shell_prefers_compressed_contextual_readout_fields(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/tickets":
            return FakeResponse(payload={"ticket": "abc"})
        if path == "/api/v1/game/runs/s14":
            return FakeResponse(payload={"run": {"id": "s14", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/s14/transcript":
            return FakeResponse(payload={"run_id": "s14", "entries": [{"text": "Observed line."}]})
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-14"})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
        sess["play_shell_run_modules"] = {"s14": "god_of_carnage"}
        sess["play_shell_runtime_readouts"] = {
            "s14": {
                "social_weather_now": "Exit pressure is dominating the room; even practical movement is reading as failed repair.",
                "live_surface_now": "The doorway is the hot surface right now; hovering there reads as departure pressure, not neutral movement.",
                "carryover_now": "Departure shame is still active; the room has not spent the earlier failed-exit pressure.",
                "social_geometry_now": "Pressure is sitting with the host side and spouse axis rather than the guests.",
                "situational_freedom_now": "Distance shifts, hovering, and trying not to leave cleanly will all be socially legible here.",
                "address_pressure_now": "Veronique is effectively pressing you through failed departure pressure; the doorway is acting like an accusation, not a neutral exit.",
                "social_moment_now": "This is a failed-exit moment under brittle civility.",
                "response_pressure_now": "The room is pressing for repair, explanation, or a refusal to leave cleanly.",
                "response_address_source_now": "Veronique answers from the host side through the spouse axis in failed repair, with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction.",
                "response_exchange_now": "Your act drew a failed repair answer because your move turned departure into repair pressure.",
                "response_exchange_label_now": "failed repair",
                "response_line_prefix_now": "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway",
                "who_answers_now": "Veronique is the one answering now; the host side is speaking through spouse embarrassment, with civility hardening into correction.",
                "why_this_reply_now": "The room read the act as failed repair, so the host side answered through spouse embarrassment at the doorway and let the reply pull the moment back under principle instead of letting the exit close it, in a principle-first rebuke that uses civility as correction.",
                "observation_foothold_now": "You are inside a failed-exit exchange now; the host side is answering through departure pressure and restraint still reads as part of the exchange.",
                "room_pressure_now": "The room feels exit-loaded; the doorway still reads as a social trap.",
                "zone_sensitivity_now": "The doorway zone is socially charged; hovering there will read as pressure, not neutral movement.",
                "reaction_delta_now": "Your last move tightened departure pressure; the room turned practical movement into failed repair.",
                "carryover_delta_now": "An earlier failed-exit wound was reactivated now; departure shame is not merely lingering.",
                "pressure_shift_delta_now": "Pressure shifted onto the spouse axis and host-side embarrassment rather than staying with movement itself.",
                "hot_surface_delta_now": "The doorway became newly hot because the last move made departure pressure live again.",
            }
        }
    r = client.get("/play/s14")
    assert r.status_code == 200
    assert b'id="social-weather-now"' in r.data
    assert b'id="live-surface-now"' in r.data
    assert b'id="carryover-now"' in r.data
    assert b'id="social-geometry-now"' in r.data
    assert b'id="situational-freedom-now"' in r.data
    assert b'id="who-answers-now"' in r.data
    assert b'id="why-this-reply-now"' in r.data
    assert b'id="observation-foothold-now"' in r.data
    assert b'id="address-pressure-now"' in r.data
    assert b'id="social-moment-now"' in r.data
    assert b'id="response-pressure-now"' in r.data
    assert b'id="reaction-delta-now"' in r.data
    assert b'id="carryover-delta-now"' in r.data
    assert b'id="pressure-shift-delta-now"' in r.data
    assert b'id="hot-surface-delta-now"' in r.data
    assert b'id="room-pressure-now"' not in r.data
    assert b'id="zone-sensitivity-now"' not in r.data





def test_play_execute_json_prefers_turn_level_addressed_visible_output_bundle(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-addressed"})
        if path == "/api/v1/sessions/backend-session-addressed/turns":
            return FakeResponse(payload={
                "turn": {
                    "turn_number": 1,
                    "interpreted_input": {"kind": "action"},
                    "shell_readout_projection": {
                        "response_address_source_now": "Annette answers from the guest side across the couples in accusation, with cross-couple strain on the books, in a cutting contradiction that treats principle as performance.",
                        "response_exchange_label_now": "accusation",
                        "response_line_prefix_now": "Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, the earlier taste-and-status wound still sitting on the books",
                    },
                    "visible_output_bundle_addressed": {
                        "gm_narration": ["Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, the earlier taste-and-status wound still sitting on the books — She cuts in with a sharper accusation."]
                    },
                },
                "state": {"turn_counter": 1, "current_scene_id": "living_room_main"},
                "diagnostics": {"diagnostics": []},
            })
        if path == "/api/v1/game/runs/saddr":
            return FakeResponse(payload={"run": {"id": "saddr", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/saddr/transcript":
            return FakeResponse(payload={"run_id": "saddr", "entries": [{"text": "A weaker generic line."}]})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"saddr": "backend-session-addressed"}
    response = client.post("/play/saddr/execute", json={"player_input": "I touch the books."}, headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["shell_state_view"]["latest_entry_text"] == "Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, the earlier taste-and-status wound still sitting on the books — She cuts in with a sharper accusation."
    assert data["shell_state_view"]["transcript_preview"][-1] == "Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, the earlier taste-and-status wound still sitting on the books — She cuts in with a sharper accusation."


def test_play_execute_json_uses_turn_level_runtime_shell_readout_when_state_missing(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-direct"})
        if path == "/api/v1/sessions/backend-session-direct/turns":
            return FakeResponse(payload={
                "turn": {
                    "turn_number": 1,
                    "interpreted_input": {"kind": "action"},
                    "shell_readout_projection": {
                        "response_address_source_now": "Veronique answers from the host side through the spouse axis in failed repair, with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction.",
                        "response_exchange_label_now": "failed repair",
                        "response_line_prefix_now": "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway",
                    },
                },
                "state": {"turn_counter": 1, "current_scene_id": "hallway_threshold"},
                "diagnostics": {"diagnostics": []},
            })
        if path == "/api/v1/game/runs/sdirect":
            return FakeResponse(payload={"run": {"id": "sdirect", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/sdirect/transcript":
            return FakeResponse(payload={"run_id": "sdirect", "entries": [{"text": "A sharp reply."}]})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"sdirect": "backend-session-direct"}
    response = client.post("/play/sdirect/execute", json={"player_input": "I hover at the door."}, headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["shell_state_view"]["latest_entry_text"] == "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway — A sharp reply."


def test_play_execute_json_prefers_turn_level_addressed_visible_output_bundle_carries_prior_wound(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-carry"})
        if path == "/api/v1/sessions/backend-session-carry/turns":
            return FakeResponse(payload={
                "turn": {
                    "turn_number": 1,
                    "interpreted_input": {"kind": "action"},
                    "shell_readout_projection": {
                        "response_address_source_now": "Veronique answers from the host side through the spouse axis in failed repair, with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction.",
                        "response_exchange_label_now": "failed repair",
                        "response_line_prefix_now": "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway",
                    },
                    "visible_output_bundle_addressed": {
                        "gm_narration": ["Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway — She answers as if the failed exit is still sitting between you."]
                    },
                },
                "state": {"turn_counter": 1, "current_scene_id": "hallway_threshold"},
                "diagnostics": {"diagnostics": []},
            })
        if path == "/api/v1/game/runs/scarry":
            return FakeResponse(payload={"run": {"id": "scarry", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/scarry/transcript":
            return FakeResponse(payload={"run_id": "scarry", "entries": [{"text": "A weaker generic line."}]})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"scarry": "backend-session-carry"}
    response = client.post("/play/scarry/execute", json={"player_input": "I hover at the door again."}, headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 200
    data = response.get_json()
    assert "the earlier failed exit still sitting at the doorway" in data["shell_state_view"]["latest_entry_text"]


def test_play_execute_json_prefers_turn_level_addressed_visible_output_bundle_over_hosting_surface(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/sessions":
            return FakeResponse(payload={"session_id": "backend-session-hosting"})
        if path == "/api/v1/sessions/backend-session-hosting/turns":
            return FakeResponse(payload={
                "turn": {
                    "turn_number": 1,
                    "interpreted_input": {"kind": "action"},
                    "shell_readout_projection": {
                        "response_address_source_now": "Michel answers from the host side in brittle repair, with host-side hospitality strain over the hosting surface, in a smoothing deflection that offers hospitality instead of alignment.",
                        "response_exchange_label_now": "brittle repair",
                        "response_line_prefix_now": "Michel, from the host side, answers in brittle repair with host-side hospitality strain over the hosting surface, in a smoothing deflection that offers hospitality instead of alignment, the earlier hospitality-and-hosting line still sitting over the hosting surface",
                    },
                    "visible_output_bundle_addressed": {
                        "gm_narration": ["Michel, from the host side, answers in brittle repair with host-side hospitality strain over the hosting surface, in a smoothing deflection that offers hospitality instead of alignment, the earlier hospitality-and-hosting line still sitting over the hosting surface — He makes the drinks themselves feel like part of the reproach."]
                    },
                },
                "state": {"turn_counter": 1, "current_scene_id": "living_room_main"},
                "diagnostics": {"diagnostics": []},
            })
        if path == "/api/v1/game/runs/shost":
            return FakeResponse(payload={"run": {"id": "shost", "status": "active", "template_title": "God of Carnage"}, "template": {"title": "God of Carnage"}, "template_source": "backend_published", "lobby": {"status": "active"}})
        if path == "/api/v1/game/runs/shost/transcript":
            return FakeResponse(payload={"run_id": "shost", "entries": [{"text": "A weaker generic line."}]})
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.routes.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["play_shell_backend_sessions"] = {"shost": "backend-session-hosting"}
    response = client.post("/play/shost/execute", json={"player_input": "I pour a drink."}, headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["shell_state_view"]["latest_entry_text"] == "Michel, from the host side, answers in brittle repair with host-side hospitality strain over the hosting surface, in a smoothing deflection that offers hospitality instead of alignment, the earlier hospitality-and-hosting line still sitting over the hosting surface — He makes the drinks themselves feel like part of the reproach."
