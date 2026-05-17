from types import SimpleNamespace


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.ok = 200 <= status_code < 300
        self.content = b"{}"
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        return self._payload


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"<title>Better Tomorrow" in response.data
    assert b"BETTER TOMORROW" in response.data
    assert b"Sign in" in response.data
    assert b"Create your account" in response.data
    assert b"matrix-layer" in response.data
    assert b'/static/favicon.ico' in response.data


def test_home_page_ctas_switch_for_authenticated_user(client):
    with client.session_transaction() as sess:
        sess["access_token"] = "token-a"
        sess["current_user"] = {"username": "alice"}

    response = client.get("/")
    assert response.status_code == 200
    assert b"Sign in" not in response.data
    assert b"Create your account" not in response.data
    assert b"Get Started" in response.data
    assert b'href="/news"' in response.data
    assert b'href="/register"' not in response.data


def test_sidebar_uses_brand_as_home_link_without_home_nav_item(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b'class="fr-brand"' in response.data
    assert b'href="/"' in response.data
    assert b"World of Shadows" in response.data
    assert b"World of Shadows \xc2\xb7 Player" not in response.data
    assert b">Home</a>" not in response.data


def test_favicon_is_served(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert response.mimetype == "image/vnd.microsoft.icon"
    assert response.data.startswith(b"\x00\x00\x01\x00")


def test_login_success_sets_session(client, monkeypatch):
    def fake_request_backend(method, path, **kwargs):
        assert method == "POST"
        assert path == "/api/v1/auth/login"
        return FakeResponse(
            payload={
                "access_token": "token-a",
                "refresh_token": "token-r",
                "user": {"id": 1, "username": "alice"},
            }
        )

    monkeypatch.setattr("app.player_backend.request_backend", fake_request_backend)
    response = client.post("/login", data={"username": "alice", "password": "secret"})
    assert response.status_code == 302
    assert "/news" in response.headers["Location"]


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_dashboard_with_session_renders_user(client, monkeypatch):
    def fake_request_backend(method, path, **kwargs):
        assert method == "GET"
        assert path == "/api/v1/auth/me"
        return FakeResponse(payload={"id": 1, "username": "alice"})

    monkeypatch.setattr("app.player_backend.request_backend", fake_request_backend)
    with client.session_transaction() as sess:
        sess["access_token"] = "token-a"
        sess["refresh_token"] = "token-r"

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"alice" in response.data
    assert b'class="fr-side"' in response.data
    assert b'href="/dashboard"' in response.data
    assert b"Dashboard menu" not in response.data
    assert b"// USER SETTINGS" in response.data


def test_play_start_lists_templates(client, monkeypatch):
    def fake_request_backend(method, path, **kwargs):
        assert method == "GET"
        assert path == "/api/v1/game/bootstrap"
        return FakeResponse(payload={"templates": [{"id": "god_of_carnage", "title": "God of Carnage"}]})

    monkeypatch.setattr("app.player_backend.request_backend", fake_request_backend)
    with client.session_transaction() as sess:
        sess["access_token"] = "token-a"
    response = client.get("/play")
    assert response.status_code == 200
    assert b"God of Carnage" in response.data
