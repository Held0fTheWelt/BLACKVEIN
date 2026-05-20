"""Tests for backend web infrastructure routes."""


def test_web_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_old_ui_route_is_removed_without_frontend_url(client, app):
    app.config["FRONTEND_URL"] = None
    response = client.get("/login")
    assert response.status_code == 404


def test_home_redirects_to_backend_info_not_player_frontend(client, app):
    """Root is the backend entry point."""
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    loc = response.headers["Location"]
    assert loc.endswith("/backend/") or loc.endswith("/backend")


def test_old_play_route_is_removed(client, app):
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    response = client.get("/play/demo-session", follow_redirects=False)
    assert response.status_code == 404
