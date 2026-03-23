"""Pytest fixtures for World of Shadows."""
import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    """Application with testing config and in-memory DB. Teardown: drop_all() after each test."""
    application = create_app(TestingConfig)
    with application.app_context():
        db.create_all()
        try:
            yield application
        finally:
            db.session.remove()
            db.drop_all()


@pytest.fixture
def db_session(app):
    """Run test in a clean session; rollback after test for isolation."""
    with app.app_context():
        yield db.session
        db.session.rollback()
        db.session.remove()


@pytest.fixture
def client(app):
    """Test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI runner for flask commands."""
    return app.test_cli_runner()


@pytest.fixture
def test_user(app):
    """Create a test user in the DB; returns (user, password)."""
    with app.app_context():
        user = User(
            username="testuser",
            password_hash=generate_password_hash("Testpass1"),
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user, "Testpass1"


@pytest.fixture
def auth_headers(test_user, client):
    """Return headers with valid JWT for test_user (for API requests)."""
    user, password = test_user
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    token = data["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestingConfigWithCSRF(TestingConfig):
    """Testing config with CSRF enabled for security tests."""
    WTF_CSRF_ENABLED = True


@pytest.fixture
def app_csrf():
    """Application with CSRF enabled (for testing CSRF protection). Teardown: drop_all()."""
    application = create_app(TestingConfigWithCSRF)
    with application.app_context():
        db.create_all()
        try:
            yield application
        finally:
            db.session.remove()
            db.drop_all()


@pytest.fixture
def client_csrf(app_csrf):
    """Test client for app with CSRF enabled."""
    return app_csrf.test_client()
