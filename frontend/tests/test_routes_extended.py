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
    assert "/news" in r.headers["Location"]


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
    assert b'data-typewriter-shell="true"' in r.data
    assert b'id="matrix-layer"' in r.data
    assert b'id="fr-side"' in r.data
    assert b'id="fr-side-toggle"' in r.data
    assert b"Play Session" in r.data
    assert b'id="runtime-selected-responder"' not in r.data
    assert b'id="runtime-validation-status"' not in r.data
    assert b"Story" in r.data
    assert b"Your Turn" in r.data
    assert b"The room is already tense." in r.data
    assert b"play-turn-card" not in r.data
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


def test_play_execute_html_missing_readiness_flags_fails_closed(client, monkeypatch):
    def fake_request(method, path, **kwargs):
        if path == "/api/v1/game/player-sessions/sid/turns":
            return FakeResponse(
                payload={
                    "runtime_session_id": "story-1",
                    "story_entries": [],
                    "visible_scene_output": {"blocks": []},
                    "turn": {"interpreted_input": {"kind": "speech"}},
                }
            )
        raise AssertionError(f"unexpected backend call: {method} {path}")

    monkeypatch.setattr("app.player_backend.request_backend", fake_request)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"

    response = client.post(
        "/play/sid/execute",
        data={"player_input": "I wait."},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"Typewriter-Test: Die UI-Shell lebt." not in response.data
    assert b"runtime_shell_without_player_visible_story_output" in response.data
    assert b'id="execute-turn-btn" disabled' in response.data


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


def test_routes_play_normalizes_story_entries():
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
    assert "display_passivity_line" in normalized[0]
    assert "display_vitality_line" in normalized[0]


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


def test_evict_legacy_large_session_keys_clears_stale_cookie_data(client):
    with client.application.test_request_context("/"):
        for k in routes_play._LEGACY_LARGE_SESSION_KEYS:
            routes_play.session[k] = {"run-1": "x" * 10_000}
        routes_play._evict_legacy_large_session_keys()
        for k in routes_play._LEGACY_LARGE_SESSION_KEYS:
            assert k not in routes_play.session
        # idempotent on clean session
        routes_play._evict_legacy_large_session_keys()


def test_display_helpers_uncovered_branches():
    # _build_display_passivity_line: empty
    assert routes_play._build_display_passivity_line([]) == ""
    assert routes_play._build_display_passivity_line(["", "  "]) == ""

    # _build_display_vitality_line: branched bits
    vit = {"initiative_present": True, "multi_actor_realized": True, "sparse_input_recovery_applied": True}
    line = routes_play._build_display_vitality_line(vit)
    assert "initiative" in line and "multi-actor" in line and "sparse-recovery" in line

    # _build_display_actor_turn_line: with outcome and initiative
    entry = {"actor_turn_summary": {"last_actor_outcome_summary": "ok", "initiative_summary": {"event_count": 2}}}
    line = routes_play._build_display_actor_turn_line(entry)
    assert "ok" in line and "initiative_events=2" in line

    # _format_reaction_order_divergence: various paths
    assert routes_play._format_reaction_order_divergence(None) == ""
    assert routes_play._format_reaction_order_divergence("raw") == "raw"
    assert "Divergence" in routes_play._format_reaction_order_divergence({"justification": "timing"})
    assert "Order divergence" in routes_play._format_reaction_order_divergence({"reason": "delay_reason"})
    assert routes_play._format_reaction_order_divergence({}) == "Order divergence detected"

    # _build_display_render_support_warning: floor + div paths
    e = {"render_support": {"vitality_floor_warning": "floor!", "reaction_order_divergence": {"reason": "r"}}}
    w = routes_play._build_display_render_support_warning(e, {})
    assert "floor!" in w


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
    assert b"Typewriter-Test: Die UI-Shell lebt." in response.data
    assert b"Keine Runtime-Session und kein Story-Output verfuegbar." in response.data
    assert b"No authored opening was returned" not in response.data


def test_routes_play_normalized_rows_include_vitality_fields():
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


# ---------------------------------------------------------------------------
# stream_narrator_proxy — SSE same-origin proxy
# ---------------------------------------------------------------------------

def test_stream_narrator_proxy_forwards_event_stream(client, monkeypatch):
    """Proxy returns text/event-stream forwarded from play service via internal URL."""
    captured_urls = []

    class FakeUpstream:
        status_code = 200
        def iter_content(self, chunk_size=None):
            yield b"data: {\"event_kind\": \"narrator_block\"}\n\n"
        def close(self):
            pass

    def fake_get(url, **kw):
        captured_urls.append(url)
        return FakeUpstream()

    monkeypatch.setattr("app.routes_play._requests.get", fake_get)
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.get("/api/story/sessions/test-sess/stream-narrator")
    assert r.status_code == 200
    assert "text/event-stream" in r.content_type
    assert b"narrator_block" in r.data
    # Must use internal URL, not public URL
    assert len(captured_urls) == 1
    assert "play-internal.example.test" in captured_urls[0]
    assert "play.example.test" not in captured_urls[0]


def test_stream_narrator_proxy_503_when_play_service_not_configured(client, monkeypatch):
    """Returns 503 when PLAY_SERVICE_INTERNAL_URL is not set."""
    monkeypatch.setitem(client.application.config, "PLAY_SERVICE_INTERNAL_URL", "")
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.get("/api/story/sessions/test-sess/stream-narrator")
    assert r.status_code == 503


def test_stream_narrator_proxy_502_when_play_service_unreachable(client, monkeypatch):
    """Returns 502 when internal play service connection fails."""
    import requests as _req

    monkeypatch.setattr(
        "app.routes_play._requests.get",
        lambda url, **kw: (_ for _ in ()).throw(_req.RequestException("refused")),
    )
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
    r = client.get("/api/story/sessions/test-sess/stream-narrator")
    assert r.status_code == 502


# ---------------------------------------------------------------------------
# FRONTEND-SESSION-COOKIE-SIZE-ROUTE-COVERAGE
# Verify eviction and no-large-session invariant at route level.
# ---------------------------------------------------------------------------

def _play_session_backend_stub(session_id="s1"):
    """Minimal play-session API response used by cookie-size tests."""
    return FakeResponse(payload={
        "contract": "game_player_session_v1",
        "runtime_session_id": "story-1",
        "runtime_session_ready": True,
        "can_execute": True,
        "story_entries": [],
        "shell_state_view": {"module_id": "goc", "current_scene_id": "s1_scene", "turn_counter": 0},
    })


def test_play_shell_evicts_legacy_large_keys_on_request(client, monkeypatch):
    """GET /play/<id> must remove all three legacy large-payload keys from the session."""
    monkeypatch.setattr("app.player_backend.request_backend",
                        lambda *a, **k: _play_session_backend_stub())
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        for k in routes_play._LEGACY_LARGE_SESSION_KEYS:
            sess[k] = {"run-1": "x" * 2000}

    r = client.get("/play/s1")
    assert r.status_code == 200

    with client.session_transaction() as sess:
        for k in routes_play._LEGACY_LARGE_SESSION_KEYS:
            assert k not in sess, f"Legacy key {k!r} was not evicted from session"


def test_play_shell_cookie_value_below_browser_limit_after_eviction(client, monkeypatch):
    """Set-Cookie emitted after eviction must have a session value under 4093 bytes."""
    import re

    monkeypatch.setattr("app.player_backend.request_backend",
                        lambda *a, **k: _play_session_backend_stub())
    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        for k in routes_play._LEGACY_LARGE_SESSION_KEYS:
            sess[k] = {"run-1": "x" * 2000}

    r = client.get("/play/s1")
    # Flask may emit multiple Set-Cookie headers (session + per-run cookies); find the session one
    all_set_cookie = r.headers.getlist("Set-Cookie")
    session_cookie_header = next((h for h in all_set_cookie if h.startswith("session=")), None)
    assert session_cookie_header, (
        f"Expected a session= Set-Cookie after eviction. Got: {all_set_cookie}"
    )
    m = re.search(r"session=([^;]+)", session_cookie_header)
    assert m, "Could not parse session value from Set-Cookie"
    cookie_value = m.group(1)
    assert len(cookie_value) < 4093, (
        f"Session cookie value too large: {len(cookie_value)} bytes (browser limit is 4093)"
    )
    # Ideally well under 1500 bytes (only small identifiers remain)
    assert len(cookie_value) < 1500, (
        f"Session cookie value exceeds ideal limit: {len(cookie_value)} bytes (target < 1500)"
    )


def test_play_shell_fresh_session_holds_only_small_identifiers(client, monkeypatch):
    """A fresh session on GET /play/<id> must not grow large: no legacy keys, access_token present."""
    monkeypatch.setattr("app.player_backend.request_backend",
                        lambda *a, **k: _play_session_backend_stub())
    with client.session_transaction() as sess:
        sess["access_token"] = "t"

    r = client.get("/play/s1")
    assert r.status_code == 200

    with client.session_transaction() as sess:
        assert "access_token" in sess
        for k in routes_play._LEGACY_LARGE_SESSION_KEYS:
            assert k not in sess, f"Fresh session must not contain {k!r}"
        # Only small-identifier keys permitted; backend_session_id now lives in per-run cookie only
        allowed = {"access_token", "current_user", "_flashes"}
        unexpected = set(sess.keys()) - allowed
        assert not unexpected, f"Unexpected session keys after /play/<id>: {unexpected}"


def test_stream_narrator_proxy_does_not_mutate_session(client, monkeypatch):
    """SSE proxy must not add keys to or enlarge the Flask session."""
    import re

    class _FakeUpstream:
        status_code = 200
        def iter_content(self, chunk_size=None):
            yield b"data: {}\n\n"
        def close(self):
            pass

    monkeypatch.setattr("app.routes_play._requests.get", lambda *a, **k: _FakeUpstream())

    with client.session_transaction() as sess:
        sess["access_token"] = "t"
        initial_keys = set(sess.keys())

    r = client.get("/api/story/sessions/s1/stream-narrator")
    assert r.status_code == 200

    with client.session_transaction() as sess:
        added = set(sess.keys()) - initial_keys
        assert not added, f"SSE proxy must not add session keys: {added}"

    all_set_cookie = r.headers.getlist("Set-Cookie")
    session_cookie_header = next((h for h in all_set_cookie if h.startswith("session=")), None)
    if session_cookie_header:
        m = re.search(r"session=([^;]+)", session_cookie_header)
        if m:
            assert len(m.group(1)) < 1500, "SSE route must not set a large session cookie"
