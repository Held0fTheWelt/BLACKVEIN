"""Tests for admin logs API, roles, and activity logging."""
import pytest

from app.extensions import db
from app.models import ActivityLog, User
from app.services import log_activity


def test_registered_user_has_role_user(client, app):
    """After API registration, the user has role=user."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "roleuser", "email": "roleuser@example.com", "password": "Rolepass1"},
        content_type="application/json",
    )
    assert response.status_code == 201
    with app.app_context():
        user = User.query.filter_by(username="roleuser").first()
        assert user is not None
        assert user.role == "user"


def test_user_role_helpers(test_user, moderator_user, admin_user):
    """User has_role, is_admin, is_moderator_or_admin behave correctly."""
    u, _ = test_user
    m, _ = moderator_user
    a, _ = admin_user
    assert u.has_role("user") is True
    assert u.has_role("admin") is False
    assert u.is_admin is False
    assert u.is_moderator_or_admin is False
    assert m.has_role("moderator") is True
    assert m.is_admin is False
    assert a.has_role("admin") is True
    assert a.is_admin is True
    assert a.is_moderator_or_admin is True


def test_admin_logs_api_without_token_returns_401(client):
    """GET /api/v1/admin/logs without JWT returns 401."""
    response = client.get("/api/v1/admin/logs")
    assert response.status_code == 401


def test_admin_logs_api_non_admin_returns_403(client, auth_headers):
    """GET /api/v1/admin/logs with non-admin JWT returns 403."""
    response = client.get("/api/v1/admin/logs", headers=auth_headers)
    assert response.status_code == 403
    data = response.get_json()
    assert data.get("error") == "Forbidden"


def test_admin_logs_api_admin_returns_200_and_structure(client, admin_headers):
    """GET /api/v1/admin/logs with admin JWT returns 200 and items/total/page/limit."""
    response = client.get("/api/v1/admin/logs", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert isinstance(data["items"], list)


def test_admin_logs_api_filters(client, admin_headers, app):
    """Admin logs API accepts category and returns filtered results."""
    with app.app_context():
        log_activity(category="auth", action="login", status="success", message="Test")
        log_activity(category="news", action="news_created", status="success", message="Test")
    response = client.get("/api/v1/admin/logs?category=auth", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    for item in data["items"]:
        assert item["category"] == "auth"


def test_activity_log_created_on_login(client, app, test_user):
    """After successful API login, an activity log entry exists."""
    user, password = test_user
    with app.app_context():
        initial = ActivityLog.query.count()
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    with app.app_context():
        assert ActivityLog.query.count() >= initial + 1
        logs = ActivityLog.query.filter_by(category="auth", action="login", status="success").all()
        assert len(logs) >= 1


def test_dashboard_api_logs_non_admin_redirected(client, auth_headers):
    """Legacy /dashboard/api/logs removed; non-admin JWT on /api/v1/admin/logs returns 403."""
    response = client.get("/api/v1/admin/logs", headers=auth_headers)
    assert response.status_code == 403


def test_dashboard_api_logs_admin_returns_json(client, admin_headers):
    """GET /api/v1/admin/logs with admin JWT returns 200 and JSON with items."""
    response = client.get("/api/v1/admin/logs", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert "total" in data


def test_dashboard_api_logs_invalid_page_limit_use_defaults_and_cap(client, admin_headers):
    """Invalid page/limit query args hit _parse_int except/max branches in routes."""
    response = client.get(
        "/api/v1/admin/logs?page=abc&limit=9999",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["page"] == 1
    assert data["limit"] == 100


def test_dashboard_api_logs_export_invalid_limit_uses_default(client, admin_headers):
    response = client.get(
        "/api/v1/admin/logs/export?limit=not-a-number",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "text/csv" in (response.content_type or "")


def test_csv_export_admin_returns_csv(client, admin_headers):
    """GET /api/v1/admin/logs/export as admin returns CSV."""
    response = client.get("/api/v1/admin/logs/export", headers=admin_headers)
    assert response.status_code == 200
    assert "text/csv" in response.content_type
    assert "id,created_at" in response.get_data(as_text=True) or ""


def test_csv_export_non_admin_returns_403(client, auth_headers):
    """GET /api/v1/admin/logs/export as non-admin returns 403."""
    response = client.get("/api/v1/admin/logs/export", headers=auth_headers)
    assert response.status_code == 403
