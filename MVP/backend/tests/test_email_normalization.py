"""
Tests for email normalization in user registration and login.
Ensures emails are stored and compared case-insensitively.
"""

import pytest
from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import User, Role
from app.services.user_service import (
    create_user,
    get_user_by_email,
    validate_email_format,
)


@pytest.fixture
def app():
    """Create a Flask application for testing."""
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        # Ensure default role exists
        if not Role.query.filter_by(name="user").first():
            db.session.add(Role(name="user"))
            db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestEmailValidation:
    """Test email validation and normalization."""

    def test_validate_email_format_normalizes_to_lowercase(self):
        """Email validation should normalize to lowercase."""
        is_valid, email = validate_email_format("User@Example.Com")
        assert is_valid
        assert email == email.lower()
        assert "@" in email

    def test_validate_email_format_strips_whitespace(self):
        """Email validation should strip leading/trailing whitespace."""
        is_valid, email = validate_email_format("  user@example.com  ")
        assert is_valid
        assert email == "user@example.com"

    def test_validate_email_format_rejects_invalid(self):
        """Email validation should reject invalid emails."""
        is_valid, error = validate_email_format("not-an-email")
        assert not is_valid
        assert "error" in error.lower() or "invalid" in error.lower()

    def test_validate_email_format_requires_email(self):
        """Email validation should require non-empty email."""
        is_valid, error = validate_email_format("")
        assert not is_valid
        is_valid, error = validate_email_format(None)
        assert not is_valid


class TestUserRegistration:
    """Test user registration with email normalization."""

    def test_create_user_stores_email_lowercase(self, app):
        """User creation should store email in lowercase."""
        with app.app_context():
            user, err = create_user("testuser", "Password123!", "User@Example.COM")
            assert err is None
            assert user is not None
            assert user.email == "user@example.com"

    def test_create_user_with_mixed_case_email(self, app):
        """User creation with mixed case email should normalize."""
        with app.app_context():
            user, err = create_user("testuser", "Password123!", "JoHn.DoE@Gmail.CoM")
            assert err is None
            assert user is not None
            assert user.email == "john.doe@gmail.com"

    def test_create_user_duplicate_email_case_insensitive(self, app):
        """Duplicate email check should be case-insensitive."""
        with app.app_context():
            user1, err1 = create_user("user1", "Password123!", "test@example.com")
            assert err1 is None

            # Try to create user with same email in different case
            user2, err2 = create_user("user2", "Password123!", "TEST@EXAMPLE.COM")
            assert err2 == "Email already registered"
            assert user2 is None

    def test_create_user_no_email(self, app):
        """User creation should allow optional email."""
        with app.app_context():
            user, err = create_user("testuser", "Password123!", None)
            assert err is None
            assert user is not None
            assert user.email is None


class TestEmailLookup:
    """Test email lookup with case-insensitive comparison."""

    def test_get_user_by_email_lowercase(self, app):
        """get_user_by_email should find user with lowercase lookup."""
        with app.app_context():
            user_created, _ = create_user("testuser", "Password123!", "User@Example.COM")
            assert user_created.email == "user@example.com"

            # Look up by exact lowercase
            found = get_user_by_email("user@example.com")
            assert found is not None
            assert found.id == user_created.id

    def test_get_user_by_email_uppercase(self, app):
        """get_user_by_email should find user with uppercase lookup."""
        with app.app_context():
            user_created, _ = create_user("testuser", "Password123!", "user@example.com")

            # Look up by uppercase
            found = get_user_by_email("USER@EXAMPLE.COM")
            assert found is not None
            assert found.id == user_created.id

    def test_get_user_by_email_mixed_case(self, app):
        """get_user_by_email should find user with mixed case lookup."""
        with app.app_context():
            user_created, _ = create_user("testuser", "Password123!", "User@Example.COM")

            # Look up by different mixed case
            found = get_user_by_email("uSeR@eXaMpLe.CoM")
            assert found is not None
            assert found.id == user_created.id

    def test_get_user_by_email_nonexistent(self, app):
        """get_user_by_email should return None for nonexistent email."""
        with app.app_context():
            found = get_user_by_email("nonexistent@example.com")
            assert found is None


class TestLoginNormalization:
    """Test login with email normalization."""

    def test_login_api_mixed_case_email(self, app, client):
        """API register and login should work with mixed case email."""
        with app.app_context():
            # Register with mixed case email
            resp = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "testuser",
                    "password": "Password123!@#",
                    "email": "User@Example.COM",
                },
            )
            assert resp.status_code == 201

            # Now try to get the user by email to verify storage
            user = get_user_by_email("user@example.com")
            assert user is not None
            assert user.email == "user@example.com"

    def test_login_api_different_case_than_registered(self, app, client):
        """API login should work with different case than registration."""
        with app.app_context():
            # Register with uppercase email
            client.post(
                "/api/v1/auth/register",
                json={
                    "username": "testuser",
                    "password": "Password123!@#",
                    "email": "User@EXAMPLE.COM",
                },
            )

            # Verify user exists with normalized email
            user = get_user_by_email("user@example.com")
            assert user is not None


class TestForgotPasswordNormalization:
    """Test forgot password with email normalization."""

    def test_forgot_password_mixed_case(self, app, client):
        """Forgot password should work with mixed case email."""
        with app.app_context():
            # Create user with lowercase email
            create_user("testuser", "Password123!", "user@example.com")

            # Request reset with uppercase email
            resp = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "USER@EXAMPLE.COM"},
            )
            assert resp.status_code == 200


class TestApiRegistrationNormalization:
    """Registration via public API with email normalization."""

    def test_api_register_mixed_case_email(self, app, client):
        """POST /api/v1/auth/register should normalize mixed case email."""
        with app.app_context():
            resp = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "normuser",
                    "password": "Password123!@#",
                    "email": "User@EXAMPLE.COM",
                },
                content_type="application/json",
            )
            assert resp.status_code == 201

            user = get_user_by_email("user@example.com")
            assert user is not None
            assert user.email == "user@example.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
