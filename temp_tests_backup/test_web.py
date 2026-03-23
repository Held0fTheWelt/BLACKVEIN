"""Tests for web (server-rendered) routes."""
import pytest


def test_home_returns_200(client):
    """GET / returns 200 and renders home."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"World of Shadows" in response.data or b"Welcome" in response.data


def test_web_health_returns_ok(client):
    """GET /health returns JSON status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_login_get_returns_200(client):
    """GET /login shows login form."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"login" in response.data.lower() or b"username" in response.data.lower()


def test_login_post_invalid_credentials(client):
    """POST /login with wrong credentials shows error and does not redirect."""
    response = client.post(
        "/login",
        data={"username": "nobody", "password": "wrong"},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert b"Invalid" in response.data or b"error" in response.data.lower()


def test_login_post_success_redirects_to_dashboard(client, test_user):
    """POST /login with valid credentials redirects to dashboard and sets session."""
    user, password = test_user
    response = client.post(
        "/login",
        data={"username": user.username, "password": password},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome" in response.data or b"Dashboard" in response.data


def test_login_get_when_logged_in_redirects_to_dashboard(client, test_user):
    """GET /login when already logged in redirects to dashboard."""
    user, password = test_user
    client.post("/login", data={"username": user.username, "password": password})
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 302
    assert "dashboard" in response.location or response.headers.get("Location", "").endswith("/dashboard")


def test_get_logout_rejected(client):
    """GET /logout is not allowed; route is POST only."""
    response = client.get("/logout")
    assert response.status_code == 405


def test_logout_post_without_session_redirects_to_home(client):
    """POST /logout without active session redirects to home (no 400/403)."""
    response = client.post("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Log in" in response.data or b"login" in response.data.lower()


def test_logout_post_redirects_and_clears_session(client, test_user):
    """POST /logout redirects to home and clears session (logout is POST only)."""
    user, password = test_user
    client.post("/login", data={"username": user.username, "password": password})
    response = client.post("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Log in" in response.data or b"login" in response.data.lower()


def test_dashboard_anonymous_redirects_to_login(client):
    """GET /dashboard without session redirects to login."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "login" in response.location or "/login" in (response.headers.get("Location") or "")


def test_dashboard_logged_in_returns_200(client, test_user):
    """GET /dashboard with valid session returns 200 and dashboard content."""
    user, password = test_user
    client.post("/login", data={"username": user.username, "password": password})
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.data or user.username.encode() in response.data


def test_login_post_without_csrf_rejected(client_csrf):
    """POST /login without valid CSRF token is rejected when CSRF is enabled."""
    from app.extensions import db
    from app.models import User
    from werkzeug.security import generate_password_hash
    with client_csrf.application.app_context():
        db.create_all()
        u = User(username="csrftest", password_hash=generate_password_hash("Csrfpass1"))
        db.session.add(u)
        db.session.commit()
    response = client_csrf.post(
        "/login",
        data={"username": "csrftest", "password": "Csrfpass1"},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_404_returns_custom_page(client):
    """Unknown route returns 404 and custom template."""
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert b"not found" in response.data.lower() or b"404" in response.data
