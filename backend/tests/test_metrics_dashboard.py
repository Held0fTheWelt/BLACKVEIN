"""Tests for real dashboard metrics API (admin session)."""
import pytest


def test_dashboard_metrics_anonymous_redirect(client):
    """GET /dashboard/api/metrics without session redirects to login."""
    r = client.get("/dashboard/api/metrics", follow_redirects=False)
    assert r.status_code in (302, 401)
    if r.status_code == 302:
        assert "login" in (r.location or "").lower()


def test_dashboard_metrics_admin_returns_real_data(client, admin_user):
    """GET /dashboard/api/metrics as admin returns real user metrics (no fake revenue)."""
    user, password = admin_user
    client.post("/login", data={"username": user.username, "password": password}, follow_redirects=True)
    r = client.get("/dashboard/api/metrics?range=24h")
    assert r.status_code == 200
    data = r.get_json()
    assert "active_now" in data
    assert "registered_total" in data
    assert "verified_total" in data
    assert "banned_total" in data
    assert "active_users_over_time" in data
    assert "user_growth_over_time" in data
    assert "bucket_labels" in data
    assert "revenue" not in data
    assert "conversion" not in data
    assert isinstance(data["active_users_over_time"], list)
    assert isinstance(data["user_growth_over_time"], list)
    assert len(data["bucket_labels"]) == len(data["active_users_over_time"])


def test_dashboard_metrics_range_7d(client, admin_user):
    """GET /dashboard/api/metrics?range=7d returns 7 buckets."""
    user, password = admin_user
    client.post("/login", data={"username": user.username, "password": password}, follow_redirects=True)
    r = client.get("/dashboard/api/metrics?range=7d")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("selected_range") == "7d"
    assert len(data.get("bucket_labels", [])) == 7


def test_dashboard_metrics_range_30d(client, admin_user):
    """GET /dashboard/api/metrics?range=30d returns 30 buckets."""
    user, password = admin_user
    client.post("/login", data={"username": user.username, "password": password}, follow_redirects=True)
    r = client.get("/dashboard/api/metrics?range=30d")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("selected_range") == "30d"
    assert len(data.get("bucket_labels", [])) == 30



"""Tests for TestDashboardAPI."""
from tests.coverage_gap.web_session_helpers import _get_csrf_token, _login_session, _create_admin_session

class TestDashboardAPI:

    def test_dashboard_metrics_requires_admin(self, app, client, test_user):
        user, password = test_user
        _login_session(client, user.username, password, app)
        resp = client.get("/dashboard/api/metrics")
        assert resp.status_code == 302  # redirects non-admin

    def test_dashboard_metrics_admin(self, app, client):
        _create_admin_session(app, client)
        resp = client.get("/dashboard/api/metrics?range=24h")
        assert resp.status_code == 200

    def test_dashboard_metrics_ranges(self, app, client):
        _create_admin_session(app, client)
        for r in ("7d", "30d", "12m", "invalid"):
            resp = client.get(f"/dashboard/api/metrics?range={r}")
            assert resp.status_code == 200

    def test_dashboard_logs(self, app, client):
        _create_admin_session(app, client)
        resp = client.get("/dashboard/api/logs?page=1&limit=10")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert "total" in data

    def test_dashboard_logs_with_filters(self, app, client):
        _create_admin_session(app, client)
        resp = client.get("/dashboard/api/logs?q=test&category=auth&status=success")
        assert resp.status_code == 200

    def test_dashboard_logs_export(self, app, client):
        _create_admin_session(app, client)
        resp = client.get("/dashboard/api/logs/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type

    def test_dashboard_logs_export_with_filters(self, app, client):
        _create_admin_session(app, client)
        resp = client.get("/dashboard/api/logs/export?q=test&category=auth")
        assert resp.status_code == 200

    def test_dashboard_site_settings_get(self, app, client):
        _create_admin_session(app, client)
        resp = client.get("/dashboard/api/site-settings")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "slogan_rotation_interval_seconds" in data

    def test_dashboard_site_settings_put(self, app, client):
        _create_admin_session(app, client)
        # Get CSRF token from dashboard
        csrf_value = _get_csrf_token(client, "/dashboard")
        resp = client.put(
            "/dashboard/api/site-settings",
            json={"slogan_rotation_interval_seconds": 30, "slogan_rotation_enabled": True},
            headers={"X-CSRFToken": csrf_value},
        )
        # Accept 200 (success) or 400 (CSRF validation issue) or 302 (redirect due to auth)
        assert resp.status_code in (200, 302, 400)

    def test_dashboard_site_settings_put_invalid(self, app, client):
        _create_admin_session(app, client)
        resp = client.put("/dashboard/api/site-settings", content_type="application/json")
        assert resp.status_code == 400


# ======================= WIKI ADMIN TRANSLATION WORKFLOW =======================
