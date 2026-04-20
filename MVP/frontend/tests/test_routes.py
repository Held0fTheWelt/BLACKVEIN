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
    assert b"BETTER TOMORROW" in response.data
    assert b"matrix-layer" in response.data


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

    monkeypatch.setattr("app.routes.request_backend", fake_request_backend)
    response = client.post("/login", data={"username": "alice", "password": "secret"})
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_dashboard_with_session_renders_user(client, monkeypatch):
    def fake_request_backend(method, path, **kwargs):
        assert method == "GET"
        assert path == "/api/v1/auth/me"
        return FakeResponse(payload={"id": 1, "username": "alice"})

    monkeypatch.setattr("app.routes.request_backend", fake_request_backend)
    with client.session_transaction() as sess:
        sess["access_token"] = "token-a"
        sess["refresh_token"] = "token-r"

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"alice" in response.data


def test_play_start_lists_templates(client, monkeypatch):
    def fake_request_backend(method, path, **kwargs):
        assert method == "GET"
        assert path == "/api/v1/game/bootstrap"
        return FakeResponse(payload={"templates": [{"id": "god_of_carnage", "title": "God of Carnage"}]})

    monkeypatch.setattr("app.routes.request_backend", fake_request_backend)
    with client.session_transaction() as sess:
        sess["access_token"] = "token-a"
    response = client.get("/play")
    assert response.status_code == 200
    assert b"God of Carnage" in response.data
