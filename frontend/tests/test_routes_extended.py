"""Extended route coverage for player/public frontend."""
from __future__ import annotations

import json

from app import routes_play

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
    assert b'id="play-runtime-status"' in r.data
    assert b'id="runtime-selected-responder"' in r.data
    assert b'id="runtime-validation-status"' in r.data
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
                    "narrator_streaming": {"status": "streaming", "session_id": "story-1"},
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
    assert data["narrator_streaming"] == {"status": "streaming", "session_id": "story-1"}
    assert data["runtime_status_view"]["contract"] == "play_shell_runtime_status.v1"


def test_play_shell_renders_action_lines_and_degraded_runtime_banner(client, monkeypatch):
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
                            "spoken_lines": [{"speaker_id": "annette_reille", "text": "Enough."}],
                            "action_lines": [{"actor_id": "annette_reille", "text": "She leans forward."}],
                            "dramatic_context_summary": {"responder_id": "annette_reille"},
                            "authority_summary": {"validation_status": "approved"},
                            "runtime_governance_surface": {
                                "fallback_stage_reached": "graph_fallback_executed",
                                "mock_output_flag": True,
                            },
                        }
                    ],
                    "shell_state_view": {
                        "module_id": "god_of_carnage",
                        "current_scene_id": "scene_1",
                        "turn_counter": 0,
                        "player_shell_context": {"responder_id": "annette_reille"},
                    },
                }
            )
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.player_backend.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
    response = client.get("/play/s1")
    assert response.status_code == 200
    assert b"Action" in response.data
    assert b"She leans forward." in response.data
    assert b"Degraded runtime path" in response.data
    assert b"annette_reille" in response.data


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


def test_routes_play_template_mapping_helpers(monkeypatch):
    monkeypatch.setattr(routes_play, "HAS_YAML", False)
    assert routes_play._load_template_mapping() == {"god_of_carnage_solo": "god_of_carnage"}
    monkeypatch.setattr(routes_play, "_PLAY_TEMPLATE_TO_CONTENT_MODULE_ID", {"tpl": "module"})
    assert routes_play.play_template_to_content_module_id(" tpl ") == "module"
    assert routes_play.play_template_to_content_module_id("unknown") == "unknown"


def test_routes_play_normalizes_story_entries_and_runtime_status_view():
    normalized = routes_play._normalize_story_entries_for_shell(
        [
            {
                "entry_id": "r1",
                "role": "runtime",
                "turn_number": 3,
                "text": "A hard answer lands.",
                "spoken_lines": [{"speaker_id": "annette_reille", "text": "Enough.", "tone": "cutting"}],
                "action_lines": [{"actor_id": "annette_reille", "text": "She leans in."}],
                "authority_summary": {"validation_status": "approved"},
                "runtime_governance_surface": {"fallback_stage_reached": "graph_fallback_executed"},
            }
        ],
        shell_state_view={"player_shell_context": {"responder_id": "annette_reille"}},
    )
    assert normalized[0]["spoken_lines"] == ["annette_reille: Enough. (cutting)"]
    assert normalized[0]["action_lines"] == ["annette_reille: She leans in."]
    assert normalized[0]["degraded"] is True
    assert normalized[0]["quality_class"] == "degraded"
    assert "fallback_used" in normalized[0]["degraded_reasons"]
    assert "fallback_used" in normalized[0]["degradation_signals"]

    status = routes_play._runtime_status_view_from_story_entries(
        normalized,
        shell_state_view={"player_shell_context": {"responder_id": "annette_reille"}},
    )
    assert status["contract"] == "play_shell_runtime_status.v1"
    assert status["selected_responder_id"] == "annette_reille"
    assert status["validation_status"] == "approved"
    assert status["quality_class"] == "degraded"
    assert status["degradation_signals"] == ["fallback_used"]
    assert status["aggregated_degradation_signals"] == ["fallback_used"]
    assert status["rising_degraded_posture"] is False
    assert status["degraded"] is True
    assert status["degraded_reasons"] == ["fallback_used"]
    assert status["latest_turn_number"] == 3
    assert isinstance(status["latest_vitality_summary"], dict)
    assert isinstance(status["latest_why_turn_felt_passive"], list)
    assert "display_passivity_line" in normalized[0]
    assert "display_vitality_line" in normalized[0]
    assert status["degradation_summary"] == "fallback_used"
    assert status["latest_display_passivity_line"]


def test_routes_play_weak_but_legal_is_not_marked_degraded():
    normalized = routes_play._normalize_story_entries_for_shell(
        [
            {
                "entry_id": "r2",
                "role": "runtime",
                "turn_number": 4,
                "text": "The answer lands, but softly.",
                "authority_summary": {"validation_status": "approved"},
                "runtime_governance_surface": {
                    "quality_class": "weak_but_legal",
                    "degradation_signals": ["weak_signal_accepted"],
                },
            }
        ]
    )
    assert normalized[0]["quality_class"] == "weak_but_legal"
    assert normalized[0]["degradation_signals"] == ["weak_signal_accepted"]
    assert normalized[0]["degraded"] is False
    assert normalized[0]["degraded_reasons"] == ["weak_signal_accepted"]


def test_routes_play_runtime_view_and_opening_projection(capsys):
    payload = {
        "trace_id": "trace-1",
        "turn": {
            "turn_number": 2,
            "raw_input": "I look at the table.",
            "interpreted_input": {"kind": "action"},
            "visible_output_bundle": {
                "gm_narration": [" The room tightens. ", ""],
                "spoken_lines": ["Annette: Enough.", ""],
            },
            "validation_outcome": {"status": "approved"},
            "narrative_commit": {"committed_scene_id": "scene_1"},
            "graph": {"errors": []},
        },
        "state": {
            "committed_state": {
                "last_narrative_commit_summary": {"committed_scene_id": "scene_1"},
                "last_narrative_commit": {"committed_scene_id": "scene_1"},
                "last_committed_consequences": ["tension_escalates"],
            }
        },
    }
    view = routes_play._build_play_shell_runtime_view(payload)
    assert view == {
        "turn_number": 2,
        "player_line": "I look at the table.",
        "narration_text": "The room tightens.",
        "spoken_lines": ["Annette: Enough."],
        "committed_consequences": ["tension_escalates"],
        "interpreted_input_kind": "action",
    }

    opening = routes_play._build_play_shell_opening_view(
        {
            "turn_number": 0,
            "turn_kind": "opening",
            "raw_input": "hidden prompt",
            "trace_id": "opening-trace",
            "narrative_commit": {"committed_consequences": ["opened"]},
            "visible_output_bundle": {"gm_narration": ["Opening narration."]},
            "validation_outcome": {"status": "approved"},
        },
        opening_meta={"current_scene_id": "scene_1", "turn_counter": 0},
    )
    assert opening["turn_number"] == 0
    assert opening["player_line"] == ""
    assert opening["narration_text"] == "Opening narration."
    assert opening["committed_consequences"] == ["opened"]

    missing_view = routes_play._build_play_shell_runtime_view({"turn": {"turn_number": 3}, "state": {}})
    assert missing_view["turn_number"] == 3
    assert "missing critical fields" in capsys.readouterr().err


def test_routes_play_operator_payload_truncation(monkeypatch):
    rows = [{"i": i} for i in range(routes_play.DIAGNOSTICS_MAX_ROWS + 3)]
    payload = {
        "session_id": "backend-1",
        "trace_id": "trace-1",
        "world_engine_story_session_id": "story-1",
        "turn": {"turn_number": 1},
        "state": {"current_scene_id": "scene_1"},
        "diagnostics": {"diagnostics": rows},
        "backend_interpretation_preview": {"kind": "speech"},
        "warnings": ["w"],
    }
    truncated = routes_play._truncate_operator_payload(payload)
    assert len(truncated["diagnostics"]["diagnostics"]) == routes_play.DIAGNOSTICS_MAX_ROWS
    assert truncated["diagnostics"]["_truncated_row_count"] == routes_play.DIAGNOSTICS_MAX_ROWS + 3

    monkeypatch.setattr(routes_play, "OPERATOR_SESSION_JSON_MAX", 20)
    tiny = routes_play._truncate_operator_payload(payload)
    assert tiny["diagnostics"]["_truncated"] is True
    assert tiny["state"]["_truncated"] is True


def test_routes_play_legacy_turn_log_helpers(client):
    with client.application.test_request_context("/"):
        routes_play.session[routes_play.PLAY_SHELL_TURN_LOG_KEY] = "bad"
        routes_play._append_turn_log("run-1", {"turn_number": 1})
        existing = routes_play._ensure_turn_log_from_legacy("run-1", None)
        assert existing == [{"turn_number": 1}]
        assert routes_play._ensure_turn_log_from_legacy("run-2", {"turn_number": 2}) == [{"turn_number": 2}]
        assert routes_play._ensure_turn_log_from_legacy("run-3", None) == []


def test_routes_play_persist_turn_success_stores_legacy_projection(client):
    payload = {
        "trace_id": "trace-1",
        "opening_turn": {
            "turn_number": 0,
            "turn_kind": "opening",
            "narrative_commit": {"committed_consequences": ["opening_done"]},
            "visible_output_bundle": {"gm_narration": ["Opening text."]},
            "validation_outcome": {"status": "approved"},
        },
        "world_engine_opening_meta": {"current_scene_id": "scene_1", "turn_counter": 0},
        "turn": {
            "turn_number": 1,
            "raw_input": "Hello.",
            "interpreted_input": {"kind": "speech"},
            "visible_output_bundle": {"gm_narration": ["Reply text."]},
            "validation_outcome": {"status": "approved"},
            "narrative_commit": {},
        },
        "state": {"committed_state": {"last_committed_consequences": ["reply_done"]}},
        "diagnostics": {"diagnostics": []},
    }
    with client.application.test_request_context("/"):
        result = routes_play._persist_turn_success("run-1", payload)
        assert result["runtime_view"]["narration_text"] == "Reply text."
        assert result["operator_bundle"]["trace_id"] == "trace-1"
        logs = routes_play.session.get(routes_play.PLAY_SHELL_TURN_LOG_KEY)["run-1"]
        assert [entry["narration_text"] for entry in logs] == ["Opening text.", "Reply text."]


def test_play_input_json_non_object_returns_empty(client):
    with client.application.test_request_context(
        "/play/sid/execute",
        method="POST",
        data="[]",
        content_type="application/json",
    ):
        assert routes_play._player_input_from_request() == ""


def test_play_execute_json_backend_error_and_invalid_payload(client, monkeypatch):
    def backend_error(method, path, **kwargs):
        return FakeResponse(status_code=502, payload={"error": "bridge down"})

    monkeypatch.setattr("app.player_backend.request_backend", backend_error)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    response = client.post(
        "/play/sid/execute",
        data=json.dumps({"player_input": "Hello"}),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    assert response.status_code == 400
    assert "bridge down" in response.get_json()["error"]

    monkeypatch.setattr("app.player_backend.require_success", lambda *a, **k: ["bad"])
    monkeypatch.setattr("app.player_backend.request_backend", lambda *a, **k: FakeResponse(payload=["bad"]))
    response = client.post(
        "/play/sid/execute",
        data=json.dumps({"player_input": "Hello"}),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Runtime turn execution returned an invalid response."


def test_play_shell_backend_error_flashes_and_renders_empty_shell(client, monkeypatch):
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(status_code=503, payload={"error": "resume failed"}),
    )
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    response = client.get("/play/sid")
    assert response.status_code == 200
    assert b"resume failed" in response.data
    assert b"No authored opening was returned" in response.data


def test_routes_play_runtime_status_reports_rising_degraded_posture_and_row_vitality():
    entries = []
    for idx in range(1, 11):
        degraded = idx > 5
        entries.append(
            {
                "entry_id": f"r-{idx}",
                "role": "runtime",
                "turn_number": idx,
                "text": f"turn {idx}",
                "spoken_lines": [{"speaker_id": "annette_reille", "text": "Enough."}] if degraded else [],
                "runtime_governance_surface": {
                    "quality_class": "degraded" if degraded else "healthy",
                    "degradation_signals": ["fallback_used"] if degraded else [],
                },
                "actor_survival_telemetry": {
                    "vitality_telemetry_v1": {
                        "schema_version": "vitality_telemetry_v1",
                        "response_present": degraded,
                        "initiative_present": False,
                        "multi_actor_realized": False,
                        "sparse_input_recovery_applied": False,
                        "selected_primary_responder_id": "annette_reille",
                        "realized_actor_ids": ["annette_reille"] if degraded else [],
                        "realized_secondary_responder_ids": [],
                        "rendered_actor_ids": ["annette_reille"] if degraded else [],
                        "generated_spoken_line_count": 1 if degraded else 0,
                        "validated_spoken_line_count": 1 if degraded else 0,
                        "rendered_spoken_line_count": 1 if degraded else 0,
                        "generated_action_line_count": 0,
                        "validated_action_line_count": 0,
                        "rendered_action_line_count": 0,
                        "fallback_used": degraded,
                        "degraded_commit": False,
                        "retry_exhausted": False,
                        "quality_class": "degraded" if degraded else "healthy",
                        "degradation_signals": ["fallback_used"] if degraded else [],
                    }
                },
            }
        )

    normalized = routes_play._normalize_story_entries_for_shell(entries)
    assert all("vitality_summary" in row for row in normalized)
    assert all("why_turn_felt_passive" in row for row in normalized)

    status = routes_play._runtime_status_view_from_story_entries(normalized)
    assert status["rising_degraded_posture"] is True
    assert "fallback_used" in status["aggregated_degradation_signals"]
    assert isinstance(status["latest_vitality_summary"], dict)


def test_routes_play_dramatic_whitelist_ignores_non_whitelisted_keys():
    normalized = routes_play._normalize_story_entries_for_shell(
        [
            {
                "entry_id": "r1",
                "role": "runtime",
                "turn_number": 1,
                "text": "Narration.",
                "authority_summary": {
                    "validation_status": "approved",
                    "social_continuity_status": "tension_escalates",
                },
                "dramatic_context_summary": {
                    "selected_scene_function": "escalate_conflict",
                    "pacing_mode": "compressed",
                    "thread_pressure_level": 2,
                    "continuity_classes": ["blame_pressure"],
                    "secret_debug_blob": {"nested": "must_not_surface"},
                    "raw_retrieval_internals": ["ranking", "notes"],
                },
            }
        ],
        diagnostics_deep=True,
    )
    row = normalized[0]
    keys = {item["key"] for item in row["display_dramatic_context_items"]}
    assert "secret_debug_blob" not in keys
    assert "raw_retrieval_internals" not in keys
    assert "scene_function" in keys
    assert "pacing_mode" in keys
    compact = row["display_dramatic_context_compact"]
    assert "escalate_conflict" in compact or "Scene" in compact
    assert "must_not_surface" not in compact


def test_routes_play_diagnostics_deep_toggle_controls_context_items():
    shallow = routes_play._normalize_story_entries_for_shell(
        [
            {
                "role": "runtime",
                "text": "x",
                "dramatic_context_summary": {"pacing_mode": "thin_edge"},
                "authority_summary": {"validation_status": "approved"},
            }
        ],
        diagnostics_deep=False,
    )
    deep = routes_play._normalize_story_entries_for_shell(
        [
            {
                "role": "runtime",
                "text": "x",
                "dramatic_context_summary": {"pacing_mode": "thin_edge"},
                "authority_summary": {"validation_status": "approved"},
            }
        ],
        diagnostics_deep=True,
    )
    assert shallow[0]["display_dramatic_context_items"] == []
    assert len(deep[0]["display_dramatic_context_items"]) >= 1


def test_play_shell_diagnostics_query_sets_session_and_surfaces_details(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/player-sessions/sdiag":
            return FakeResponse(
                payload={
                    "contract": "game_player_session_v1",
                    "runtime_session_id": "story-1",
                    "runtime_session_ready": True,
                    "can_execute": True,
                    "story_entries": [
                        {
                            "entry_id": "o1",
                            "role": "runtime",
                            "turn_number": 0,
                            "text": "Open.",
                            "authority_summary": {"validation_status": "approved"},
                            "dramatic_context_summary": {
                                "selected_scene_function": "probe_motive",
                                "pacing_mode": "standard",
                            },
                        }
                    ],
                    "shell_state_view": {"module_id": "god_of_carnage", "current_scene_id": "scene_1", "turn_counter": 0},
                }
            )
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.player_backend.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess["current_user"] = {"username": "u1"}
    page = client.get("/play/sdiag?diagnostics=1")
    assert page.status_code == 200
    assert b"Dramatic context (diagnostics)" in page.data
    with client.session_transaction() as sess:
        assert sess.get(routes_play.PLAY_SHELL_DIAGNOSTICS_SESSION_KEY) is True


def test_play_execute_json_includes_show_play_diagnostics_flag(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/player-sessions/sdiag2/turns" and method == "POST":
            return FakeResponse(
                payload={
                    "contract": "game_player_session_v1",
                    "story_entries": [
                        {
                            "role": "runtime",
                            "turn_number": 0,
                            "text": "Hello.",
                            "authority_summary": {"validation_status": "approved"},
                        }
                    ],
                    "shell_state_view": {},
                    "turn": {"interpreted_input": {"kind": "speech"}},
                }
            )
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.player_backend.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        sess[routes_play.PLAY_SHELL_DIAGNOSTICS_SESSION_KEY] = True
    r = client.post(
        "/play/sdiag2/execute",
        data=json.dumps({"player_input": "hi"}),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["show_play_diagnostics"] is True
    assert "runtime_status_view" in body
    assert body["runtime_status_view"]["quality_class"] in {"healthy", "weak_but_legal", "degraded", "failed"}
