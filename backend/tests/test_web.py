"""Compatibility tests for legacy web redirects."""


def test_web_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_legacy_ui_route_returns_410_without_frontend_url(client, app):
    app.config["FRONTEND_URL"] = None
    response = client.get("/login")
    assert response.status_code == 410
    payload = response.get_json()
    assert payload["error"] == "Legacy UI route disabled."


def test_home_redirects_to_frontend_url(client, app):
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "https://frontend.example.com/"


def test_play_route_redirects_to_frontend(client, app):
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    response = client.get("/play/demo-session", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "https://frontend.example.com/play/demo-session"
