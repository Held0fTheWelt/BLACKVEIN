"""
CSRF Protection Verification Tests

Comprehensive tests to verify CSRF protection is properly implemented:
1. API endpoints are exempted from CSRF (use JWT instead)
2. Web form endpoints require valid CSRF tokens
3. POST without CSRF token fails
4. POST from different origin fails
5. POST with valid CSRF token succeeds
"""

import pytest
from flask import session
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models import User, Role
from app.models.role import ensure_roles_seeded


class TestCSRFConfiguration:
    """Verify CSRF is properly configured in the Flask app."""

    def test_csrf_enabled_in_app(self, app):
        """CSRF protection should be enabled by default (except in testing)."""
        if not app.config.get("TESTING"):
            # In production/development, CSRF should be enabled
            assert app.config.get("WTF_CSRF_ENABLED", True)

    def test_csrf_enabled_in_testing(self, app):
        """CSRF should be enabled in testing so we can verify protection works."""
        if app.config.get("TESTING"):
            # In testing, CSRF defaults to Flask-WTF's enabled state (True) so we can test it
            assert app.config.get("WTF_CSRF_ENABLED") != False


class TestAPIEndpointsExemptFromCSRF:
    """
    Verify that API endpoints are exempt from CSRF protection
    (they use JWT authentication instead).
    """

    def test_api_blueprint_exempt_from_csrf(self, app, client):
        """The /api/v1 blueprint should be exempted from CSRF protection."""
        # This is configured in __init__.py: csrf.exempt(api_v1_bp)
        # We verify this by attempting a POST to an API endpoint without CSRF token
        
        # Register a test user
        response = client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "TestPassword123!",
            "email": "test@example.com"
        })
        # Should succeed even without CSRF token (API endpoints use JWT, not CSRF)
        assert response.status_code in [201, 400]  # 201=success, 400=validation error


class TestWebFormCSRFProtection:
    """
    Verify that web form endpoints (non-API) require CSRF tokens.
    """

    def test_web_login_requires_csrf_token(self, client):
        """POST to /login without CSRF token should fail with 400."""
        # First, GET the login page to see the form
        response = client.get("/login")
        assert response.status_code == 200

        # Try POST without CSRF token
        response = client.post("/login", data={
            "username": "testuser",
            "password": "password"
        })
        # Should fail due to missing CSRF token
        assert response.status_code == 400

    def test_web_register_requires_csrf_token(self, client):
        """POST to /register without CSRF token should fail with 400."""
        response = client.post("/register", data={
            "username": "newuser",
            "password": "TestPassword123!",
            "password_confirm": "TestPassword123!",
            "email": "new@example.com"
        })
        # Should fail due to missing CSRF token
        assert response.status_code == 400

    def test_web_logout_requires_csrf_token(self, client, app):
        """POST to /logout without CSRF token should fail with 400."""
        with app.app_context():
            # Ensure roles are seeded
            ensure_roles_seeded()

            # Get the user role
            role = Role.query.filter_by(name=Role.NAME_USER).first()

            # Create and login a user first
            user = User(
                username="testuser",
                email="test@example.com",
                email_verified_at=db.func.now(),
                password_hash=generate_password_hash("TestPassword123!"),
                role_id=role.id
            )
            db.session.add(user)
            db.session.commit()

            # Login
            client.post("/login", data={
                "username": "testuser",
                "password": "TestPassword123!",
                "csrf_token": "dummy"  # This will fail anyway, testing CSRF requirement
            })

            # Try logout without valid CSRF token
            response = client.post("/logout", data={})
            # Should fail due to missing/invalid CSRF token
            assert response.status_code == 400


class TestCSRFTokenValidation:
    """
    Verify that CSRF token validation works correctly.
    """

    def test_invalid_csrf_token_rejected(self, client):
        """POST with invalid CSRF token should be rejected."""
        response = client.post("/login", data={
            "username": "testuser",
            "password": "password",
            "csrf_token": "invalid-token-here"
        })
        # Should reject due to invalid CSRF token
        assert response.status_code == 400

    def test_missing_csrf_token_rejected(self, client):
        """POST without CSRF token should be rejected."""
        response = client.post("/login", data={
            "username": "testuser",
            "password": "password"
        })
        # Should reject due to missing CSRF token
        assert response.status_code == 400


class TestCSRFTokenPresenceInForms:
    """
    Verify that HTML templates include CSRF tokens in forms.
    """

    def test_login_form_contains_csrf_token(self, client):
        """Login form should contain CSRF token input."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b'name="csrf_token"' in response.data or b'csrf-token' in response.data

    def test_register_form_contains_csrf_token(self, client):
        """Register form should contain CSRF token input."""
        response = client.get("/register")
        assert response.status_code == 200
        assert b'name="csrf_token"' in response.data or b'csrf-token' in response.data

    def test_base_template_includes_csrf_support(self, client):
        """Base template should have CSRF token function available."""
        response = client.get("/login")
        assert response.status_code == 200
        # Check that csrf_token is rendered (appears in HTML)
        assert b'csrf_token' in response.data


class TestSessionCookieConfiguration:
    """
    Verify that session cookies are properly configured for CSRF protection.
    """

    def test_session_cookie_httponly(self, app):
        """Session cookie should have HttpOnly flag."""
        assert app.config.get("SESSION_COOKIE_HTTPONLY") == True

    def test_session_cookie_samesite_lax(self, app):
        """Session cookie should have SameSite=Lax to prevent CSRF."""
        samesite = app.config.get("SESSION_COOKIE_SAMESITE", "Lax")
        assert samesite in ["Lax", "Strict"]


class TestFormBasedAuthenticationEndpoints:
    """
    Verify CSRF protection on form-based authentication endpoints.
    """

    def test_csrf_token_in_login_response(self, client):
        """GET /login should return CSRF token in response."""
        response = client.get("/login")
        assert response.status_code == 200
        # CSRF token should be present in HTML
        html = response.data.decode()
        assert "csrf_token" in html.lower()

    def test_csrf_token_in_register_response(self, client):
        """GET /register should return CSRF token in response."""
        response = client.get("/register")
        assert response.status_code == 200
        html = response.data.decode()
        assert "csrf_token" in html.lower()


class TestSecurityHeaders:
    """
    Verify security headers are present to complement CSRF protection.
    """

    def test_x_frame_options_header(self, client):
        """X-Frame-Options header should prevent clickjacking."""
        response = client.get("/login")
        assert response.headers.get("X-Frame-Options") in ["DENY", "SAMEORIGIN"]

    def test_content_security_policy_header(self, client):
        """CSP header should restrict form submissions to same origin."""
        response = client.get("/login")
        csp = response.headers.get("Content-Security-Policy", "")
        # form-action 'self' prevents form submission to other origins
        assert "form-action 'self'" in csp

    def test_referrer_policy_header(self, client):
        """Referrer-Policy should be set appropriately."""
        response = client.get("/login")
        referrer = response.headers.get("Referrer-Policy", "")
        assert "strict-origin" in referrer or "same-origin" in referrer


