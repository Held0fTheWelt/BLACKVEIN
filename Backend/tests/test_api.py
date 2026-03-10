"""Tests for API v1 routes (REST, JWT)."""
import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db


def test_api_health_returns_ok(client):
    """GET /api/v1/health returns 200 and status ok."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_register_success(client):
    """POST /api/v1/auth/register creates user and returns 201."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "newuser", "email": "newuser@example.com", "password": "Secret123"},
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["username"] == "newuser"
    assert "id" in data


def test_register_missing_json_returns_400(client):
    """POST /api/v1/auth/register without JSON returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        data="not json",
        content_type="text/plain",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_register_validation_returns_400(client):
    """POST /api/v1/auth/register with short username returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "a", "email": "a@b.co", "password": "Longenough1"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_register_missing_email_returns_400(client):
    """POST /api/v1/auth/register without email returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "noman", "password": "Secret123"},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.get_json().get("error") == "Email is required"
def test_register_duplicate_username_returns_409(client, test_user):
    """POST /api/v1/auth/register with existing username returns 409."""
    user, password = test_user
    response = client.post(
        "/api/v1/auth/register",
        json={"username": user.username, "email": "other@example.com", "password": "Otherpass1"},
        content_type="application/json",
    )
    assert response.status_code == 409
    assert "error" in response.get_json()


def test_login_success_returns_token(client, test_user):
    """POST /api/v1/auth/login with valid credentials returns access_token and user."""
    user, password = test_user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "access_token" in data
    assert data["user"]["username"] == user.username
    assert data["user"]["id"] == user.id


def test_login_invalid_returns_401(client):
    """POST /api/v1/auth/login with wrong credentials returns 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "wrong"},
        content_type="application/json",
    )
    assert response.status_code == 401
    assert "error" in response.get_json()


def test_login_missing_body_returns_400(client):
    """POST /api/v1/auth/login without JSON returns 400."""
    response = client.post(
        "/api/v1/auth/login",
        data="x",
        content_type="text/plain",
    )
    assert response.status_code == 400


def test_me_without_token_returns_401(client):
    """GET /api/v1/auth/me without Authorization returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "error" in response.get_json()


def test_me_with_token_returns_user(client, auth_headers, test_user):
    """GET /api/v1/auth/me with valid JWT returns current user."""
    user, _ = test_user
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["username"] == user.username
    assert data["id"] == user.id


def test_protected_without_token_returns_401(client):
    """GET /api/v1/test/protected without token returns 401."""
    response = client.get("/api/v1/test/protected")
    assert response.status_code == 401


def test_protected_with_token_returns_ok(client, auth_headers, test_user):
    """GET /api/v1/test/protected with valid JWT returns message and user info."""
    user, _ = test_user
    response = client.get("/api/v1/test/protected", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "ok"
    assert data["user_id"] == user.id
    assert data["username"] == user.username


def test_api_404_returns_json(client):
    """GET /api/v1/nonexistent returns 404 with JSON error, not HTML."""
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    assert response.content_type and "application/json" in response.content_type
    data = response.get_json()
    assert "error" in data
    assert "not found" in data["error"].lower() or data["error"] == "Not found"


def test_cors_no_allow_origin_when_origins_not_configured(client):
    """When CORS_ORIGINS is not set, API responses do not include Access-Control-Allow-Origin."""
    response = client.get("/api/v1/health", headers={"Origin": "http://other.example"})
    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") is None


def test_cors_allow_origin_when_configured():
    """When CORS_ORIGINS is set, API responds with correct Access-Control-Allow-Origin."""
    class ConfigWithCORS(TestingConfig):
        CORS_ORIGINS = ["http://test.example"]

    application = create_app(ConfigWithCORS)
    with application.app_context():
        db.create_all()
        try:
            client = application.test_client()
            response = client.get(
                "/api/v1/health",
                headers={"Origin": "http://test.example"}
            )
            assert response.status_code == 200
            assert response.headers.get("Access-Control-Allow-Origin") == "http://test.example"
        finally:
            db.drop_all()
