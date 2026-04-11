"""Technical backend information surface (/backend/*) and root redirect behavior."""

import pytest


_INFO_PATHS = (
    "/backend",
    "/backend/",
    "/backend/api",
    "/backend/engine",
    "/backend/ai",
    "/backend/auth",
    "/backend/ops",
)


@pytest.mark.parametrize("path", _INFO_PATHS)
def test_backend_info_pages_return_200(client, path):
    response = client.get(path, follow_redirects=True)
    assert response.status_code == 200
    assert b"System / backend service" in response.data or b"backend service" in response.data


def test_backend_info_home_has_navigation(client):
    r = client.get("/backend/")
    assert r.status_code == 200
    assert b"/backend/api" in r.data
    assert b"/backend/engine" in r.data


def test_root_redirects_to_backend_info(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers.get("Location", "")
    assert loc.endswith("/backend/") or loc.endswith("/backend")


def test_create_app_registers_info_blueprint(app):
    assert "info.backend_home" in app.view_functions
    assert "info.api_overview" in app.view_functions
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert any(str(r).startswith("/backend") for r in rules)


def test_legacy_player_routes_still_redirect_or_410_not_html_shell(client, app):
    """Legacy paths must not become canonical HTML hosts; they redirect or 410."""
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    for path in ("/login", "/dashboard", "/play", "/game-menu"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["Location"].startswith("https://frontend.example.com")
    app.config["FRONTEND_URL"] = None
    r = client.get("/login", follow_redirects=False)
    assert r.status_code == 410
    assert r.is_json


def test_api_health_unaffected_next_to_backend_namespace(client):
    """Backend info URLs must not shadow /api/v1/* JSON routes."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.is_json
    assert r.get_json().get("status") == "ok"
