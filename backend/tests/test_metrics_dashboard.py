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
