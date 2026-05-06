"""MVP1 frontend play launcher tests — FIX-005 and FIX-008.

Tests prove:
- session_start.html role selector is rendered for god_of_carnage_solo
- play_create rejects missing selected_role for god_of_carnage_solo
- play_create submits runtime_profile_id + selected_player_role (not template_id)
- play_create works for both Annette and Alain
- play_create rejects visitor role
"""

from __future__ import annotations

from unittest.mock import patch


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._payload


def _logged_in(client):
    with client.session_transaction() as sess:
        sess["access_token"] = "test-token"
        sess["user_id"] = "1"


# ---------------------------------------------------------------------------
# Play launcher route tests
# ---------------------------------------------------------------------------

def test_play_start_renders_role_selector_in_html(client, monkeypatch):
    """GET /play must render the Annette/Alain role selector (FIX-005)."""
    _logged_in(client)
    monkeypatch.setattr(
        "app.player_backend.request_backend",
        lambda *a, **k: FakeResponse(payload={
            "templates": [{"id": "god_of_carnage_solo", "title": "God of Carnage", "kind": "solo_story", "kind_label": "Solo Story"}],
            "runs": [],
            "characters": [],
            "save_slots": [],
        }),
    )
    r = client.get("/play")
    assert r.status_code == 200
    body = r.data.decode("utf-8")
    assert "selected_player_role" in body, "Role selector input must appear in session_start.html"
    assert "Annette" in body
    assert "Alain" in body


def test_play_launcher_requires_annette_or_alain(client):
    """POST /play/start with god_of_carnage_solo and no role must redirect with error (FIX-005)."""
    _logged_in(client)
    r = client.post(
        "/play/start",
        data={"template_id": "god_of_carnage_solo"},
        follow_redirects=False,
    )
    # Should redirect back to play_start with an error flash
    assert r.status_code in (302, 303)


def test_play_create_rejects_missing_selected_role(client):
    """POST /play/start for GoC Solo without selected_player_role must not call backend (FIX-005)."""
    _logged_in(client)
    called = []

    def record_backend(*a, **k):
        called.append(True)
        return FakeResponse()

    with patch("app.player_backend.request_backend", side_effect=record_backend):
        r = client.post(
            "/play/start",
            data={"template_id": "god_of_carnage_solo"},
            follow_redirects=False,
        )
    assert r.status_code in (302, 303)
    assert not called, "Backend must not be called when selected_player_role is missing for GoC Solo"


def test_play_create_submits_selected_player_role_annette(client):
    """POST /play/start with annette must submit runtime_profile_id to backend (FIX-005, FIX-008)."""
    _logged_in(client)
    submitted = {}

    def capture_backend(method, path, *, json_data=None, **kwargs):
        submitted["method"] = method
        submitted["path"] = path
        submitted["json_data"] = json_data
        return FakeResponse(payload={"run": {"id": "r1"}, "run_id": "r1"})

    with patch("app.player_backend.request_backend", side_effect=capture_backend):
        r = client.post(
            "/play/start",
            data={"template_id": "god_of_carnage_solo", "selected_player_role": "annette"},
            follow_redirects=False,
        )

    assert r.status_code in (302, 303)
    assert submitted.get("method") == "POST"
    json_data = submitted.get("json_data") or {}
    assert json_data.get("runtime_profile_id") == "god_of_carnage_solo", (
        f"Frontend must submit runtime_profile_id, not template_id. Got: {json_data}"
    )
    assert json_data.get("selected_player_role") == "annette"
    assert "template_id" not in json_data, (
        f"Frontend must not submit template_id for GoC Solo. Got: {json_data}"
    )


def test_play_create_submits_selected_player_role_alain(client):
    """POST /play/start with alain must submit runtime_profile_id to backend (FIX-005, FIX-008)."""
    _logged_in(client)
    submitted = {}

    def capture_backend(method, path, *, json_data=None, **kwargs):
        submitted["method"] = method
        submitted["path"] = path
        submitted["json_data"] = json_data
        return FakeResponse(payload={"run": {"id": "r2"}, "run_id": "r2"})

    with patch("app.player_backend.request_backend", side_effect=capture_backend):
        r = client.post(
            "/play/start",
            data={"template_id": "god_of_carnage_solo", "selected_player_role": "alain"},
            follow_redirects=False,
        )

    json_data = submitted.get("json_data") or {}
    assert json_data.get("runtime_profile_id") == "god_of_carnage_solo"
    assert json_data.get("selected_player_role") == "alain"


def test_frontend_launcher_annette_and_alain_start_payloads(client):
    """Both Annette and Alain start payloads must use runtime_profile_id (FIX-008)."""
    _logged_in(client)

    for role in ("annette", "alain"):
        submitted = {}

        def capture_backend(method, path, *, json_data=None, **kwargs):
            submitted["json_data"] = json_data
            return FakeResponse(payload={"run": {"id": f"run_{role}"}, "run_id": f"run_{role}"})

        with patch("app.player_backend.request_backend", side_effect=capture_backend):
            client.post(
                "/play/start",
                data={"template_id": "god_of_carnage_solo", "selected_player_role": role},
                follow_redirects=False,
            )
        jd = submitted.get("json_data") or {}
        assert jd.get("runtime_profile_id") == "god_of_carnage_solo", f"Role {role}: missing runtime_profile_id"
        assert jd.get("selected_player_role") == role, f"Role {role}: wrong selected_player_role"
        assert "template_id" not in jd, f"Role {role}: must not send template_id"


def test_play_create_rejects_visitor_role(client):
    """POST /play/start with visitor as selected_player_role must be rejected (FIX-005)."""
    _logged_in(client)
    called = []

    def record_backend(*a, **k):
        called.append(True)
        return FakeResponse()

    with patch("app.player_backend.request_backend", side_effect=record_backend):
        r = client.post(
            "/play/start",
            data={"template_id": "god_of_carnage_solo", "selected_player_role": "visitor"},
            follow_redirects=False,
        )
    assert r.status_code in (302, 303)
    assert not called, "Backend must not be called when visitor is submitted as selected_player_role"


# ---------------------------------------------------------------------------
# ADR-0036: session_output_language forwarded in frontend POST payload
# ---------------------------------------------------------------------------

def test_play_create_forwards_session_output_language_de(client):
    """POST /play/start must include session_output_language=de in backend payload (ADR-0036)."""
    _logged_in(client)
    submitted = {}

    def capture_backend(method, path, *, json_data=None, **kwargs):
        submitted["json_data"] = json_data
        return FakeResponse(payload={"run": {"id": "r_lang_de"}, "run_id": "r_lang_de"})

    with patch("app.player_backend.request_backend", side_effect=capture_backend):
        client.post(
            "/play/start",
            data={
                "template_id": "god_of_carnage_solo",
                "selected_player_role": "annette",
                "session_output_language": "de",
            },
            follow_redirects=False,
        )

    json_data = submitted.get("json_data") or {}
    assert json_data.get("session_output_language") == "de"


def test_play_create_forwards_session_output_language_en(client):
    """POST /play/start must include session_output_language=en in backend payload (ADR-0036)."""
    _logged_in(client)
    submitted = {}

    def capture_backend(method, path, *, json_data=None, **kwargs):
        submitted["json_data"] = json_data
        return FakeResponse(payload={"run": {"id": "r_lang_en"}, "run_id": "r_lang_en"})

    with patch("app.player_backend.request_backend", side_effect=capture_backend):
        client.post(
            "/play/start",
            data={
                "template_id": "god_of_carnage_solo",
                "selected_player_role": "annette",
                "session_output_language": "en",
            },
            follow_redirects=False,
        )

    json_data = submitted.get("json_data") or {}
    assert json_data.get("session_output_language") == "en"


def test_play_create_defaults_session_output_language_to_de(client):
    """POST /play/start without session_output_language must default to de (ADR-0036)."""
    _logged_in(client)
    submitted = {}

    def capture_backend(method, path, *, json_data=None, **kwargs):
        submitted["json_data"] = json_data
        return FakeResponse(payload={"run": {"id": "r_lang_default"}, "run_id": "r_lang_default"})

    with patch("app.player_backend.request_backend", side_effect=capture_backend):
        client.post(
            "/play/start",
            data={
                "template_id": "god_of_carnage_solo",
                "selected_player_role": "annette",
            },
            follow_redirects=False,
        )

    json_data = submitted.get("json_data") or {}
    assert json_data.get("session_output_language") == "de"
