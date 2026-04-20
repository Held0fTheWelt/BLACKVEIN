"""Test HTTPS enforcement for production deployments.

Coverage:
- HTTP to HTTPS redirect (301) in production
- HSTS header enforcement (max-age=31536000; includeSubDomains)
- SESSION_COOKIE_SECURE=True in production config
- SESSION_COOKIE_HTTPONLY=True enforcement
- No redirect in development/testing mode
- Secure headers verification
"""

import pytest
from app import create_app
from app.config import Config, TestingConfig
from app.extensions import db


class ProductionHTTPSConfig(Config):
    """Production config with HTTPS enforcement enabled."""
    TESTING = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key-for-https-tests"
    JWT_SECRET_KEY = "test-jwt-secret-key-at-least-32-bytes-long"
    ENFORCE_HTTPS = True
    PREFER_HTTPS = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True


class DevelopmentHTTPSConfig(Config):
    """Development config with HTTPS disabled."""
    TESTING = False
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key-for-https-tests"
    JWT_SECRET_KEY = "test-jwt-secret-key-at-least-32-bytes-long"
    ENFORCE_HTTPS = False
    PREFER_HTTPS = False


@pytest.fixture
def app_production_https():
    """Production app with HTTPS enforcement enabled."""
    application = create_app(ProductionHTTPSConfig)
    with application.app_context():
        db.create_all()
        yield application


@pytest.fixture
def client_production_https(app_production_https):
    """Test client for production app with HTTPS."""
    return app_production_https.test_client()


@pytest.fixture
def app_development():
    """Development app with debug mode (HTTPS disabled)."""
    application = create_app(DevelopmentHTTPSConfig)
    with application.app_context():
        db.create_all()
        yield application


@pytest.fixture
def client_development(app_development):
    """Test client for development app."""
    return app_development.test_client()


@pytest.fixture
def app_testing():
    """Testing app (HTTPS enforcement should be disabled)."""
    application = create_app(TestingConfig)
    with application.app_context():
        db.create_all()
        yield application


@pytest.fixture
def client_testing(app_testing):
    """Test client for testing app."""
    return app_testing.test_client()


class TestHTTPToHTTPSRedirect:
    """Test HTTP to HTTPS redirect functionality."""

    def test_http_request_redirects_to_https_in_production(self, client_production_https):
        """HTTP request should redirect to HTTPS in production (301)."""
        response = client_production_https.get(
            "/",
            base_url="http://localhost",
        )
        # Should be a 301 redirect
        assert response.status_code == 301
        # Location header should point to HTTPS
        assert response.location.startswith("https://")
        assert "localhost" in response.location

    def test_https_request_not_redirected_in_production(self, client_production_https):
        """HTTPS request should not be redirected in production."""
        response = client_production_https.get(
            "/",
            base_url="https://localhost",
        )
        # Not the HTTP→HTTPS 301; root redirects to /backend info (302) when already HTTPS
        assert response.status_code != 301
        assert response.status_code in [200, 302, 404, 410]
        if response.status_code == 302:
            assert "/backend" in (response.headers.get("Location") or "")

    def test_no_redirect_in_development(self, client_development):
        """HTTP request should NOT be redirected in development (debug=True)."""
        response = client_development.get(
            "/",
            base_url="http://localhost",
        )
        assert response.status_code != 301
        assert response.status_code in [200, 302, 404, 410]
        if response.status_code == 302:
            assert "/backend" in (response.headers.get("Location") or "")

    def test_no_redirect_in_testing(self, client_testing):
        """HTTP request should NOT be redirected in testing mode."""
        response = client_testing.get(
            "/",
            base_url="http://localhost",
        )
        assert response.status_code != 301
        assert response.status_code in [200, 302, 404, 410]
        if response.status_code == 302:
            assert "/backend" in (response.headers.get("Location") or "")

    def test_api_endpoint_redirects_to_https(self, client_production_https):
        """API endpoint should also redirect from HTTP to HTTPS."""
        response = client_production_https.get(
            "/api/v1/auth/me",
            base_url="http://localhost",
        )
        # Should be a 301 redirect
        assert response.status_code == 301
        assert response.location.startswith("https://")

    def test_redirect_preserves_path_and_query_params(self, client_production_https):
        """Redirect should preserve path and query parameters."""
        response = client_production_https.get(
            "/api/v1/news?category=updates&page=2",
            base_url="http://localhost",
        )
        assert response.status_code == 301
        assert "https://localhost/api/v1/news" in response.location
        assert "category=updates" in response.location
        assert "page=2" in response.location


class TestHSTS:
    """Test HTTP Strict-Transport-Security header enforcement."""

    def test_hsts_header_present_in_production(self, client_production_https):
        """HSTS header should be present in production responses."""
        response = client_production_https.get(
            "/",
            base_url="https://localhost",
        )
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

    def test_hsts_header_not_present_in_testing(self, client_testing):
        """HSTS header should NOT be present in testing mode."""
        response = client_testing.get("/")
        assert "Strict-Transport-Security" not in response.headers

    def test_hsts_header_has_correct_max_age(self, client_production_https):
        """HSTS header should have 1-year max-age (31536000 seconds)."""
        response = client_production_https.get(
            "/",
            base_url="https://localhost",
        )
        hsts = response.headers.get("Strict-Transport-Security")
        assert "max-age=31536000" in hsts
        assert "includeSubDomains" in hsts


class TestSessionCookieSecure:
    """Test SESSION_COOKIE_SECURE flag enforcement."""

    def test_production_config_has_secure_cookie_flag(self):
        """Production config should have SESSION_COOKIE_SECURE=True."""
        app = create_app(ProductionHTTPSConfig)
        assert app.config.get("SESSION_COOKIE_SECURE") is True

    def test_production_config_has_httponly_cookie_flag(self):
        """Production config should have SESSION_COOKIE_HTTPONLY=True."""
        app = create_app(ProductionHTTPSConfig)
        assert app.config.get("SESSION_COOKIE_HTTPONLY") is True

    def test_development_config_has_httponly_cookie_flag(self):
        """Development config should have SESSION_COOKIE_HTTPONLY=True."""
        app = create_app(DevelopmentHTTPSConfig)
        assert app.config.get("SESSION_COOKIE_HTTPONLY") is True

    def test_testing_config_has_httponly_cookie_flag(self):
        """Testing config should have SESSION_COOKIE_HTTPONLY=True."""
        app = create_app(TestingConfig)
        assert app.config.get("SESSION_COOKIE_HTTPONLY") is True


class TestSecurityHeaders:
    """Test other security headers are present."""

    def test_x_content_type_options_header(self, client_production_https):
        """X-Content-Type-Options header should be present."""
        response = client_production_https.get(
            "/",
            base_url="https://localhost",
        )
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options_header(self, client_production_https):
        """X-Frame-Options header should be present."""
        response = client_production_https.get(
            "/",
            base_url="https://localhost",
        )
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_referrer_policy_header(self, client_production_https):
        """Referrer-Policy header should be present."""
        response = client_production_https.get(
            "/",
            base_url="https://localhost",
        )
        assert "Referrer-Policy" in response.headers
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_permissions_policy_header(self, client_production_https):
        """Permissions-Policy header should be present."""
        response = client_production_https.get(
            "/",
            base_url="https://localhost",
        )
        assert "Permissions-Policy" in response.headers
        assert "geolocation=()" in response.headers["Permissions-Policy"]
        assert "microphone=()" in response.headers["Permissions-Policy"]
        assert "camera=()" in response.headers["Permissions-Policy"]

    def test_content_security_policy_header(self, client_production_https):
        """Content-Security-Policy header should be present."""
        response = client_production_https.get(
            "/",
            base_url="https://localhost",
        )
        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src" in csp
        assert "style-src" in csp


class TestEnforceHTTPSConfig:
    """Test ENFORCE_HTTPS configuration."""

    def test_enforce_https_flag_in_production(self):
        """ENFORCE_HTTPS should be True in production config."""
        app = create_app(ProductionHTTPSConfig)
        assert app.config.get("ENFORCE_HTTPS") is True

    def test_enforce_https_flag_in_development(self):
        """ENFORCE_HTTPS should be False in development config."""
        app = create_app(DevelopmentHTTPSConfig)
        assert app.config.get("ENFORCE_HTTPS") is False

    def test_prefer_https_flag_in_production(self):
        """PREFER_HTTPS should be True in production config."""
        app = create_app(ProductionHTTPSConfig)
        assert app.config.get("PREFER_HTTPS") is True

    def test_prefer_https_flag_in_development(self):
        """PREFER_HTTPS should be False in development config."""
        app = create_app(DevelopmentHTTPSConfig)
        assert app.config.get("PREFER_HTTPS") is False


class TestHTTPSRedirectWithDifferentMethods:
    """Test HTTP to HTTPS redirect works with various HTTP methods."""

    def test_post_request_redirects_to_https(self, client_production_https):
        """POST request should redirect to HTTPS in production."""
        response = client_production_https.post(
            "/api/v1/auth/login",
            base_url="http://localhost",
            json={"username": "test", "password": "test"},
        )
        # POST requests should also redirect
        assert response.status_code == 301
        assert response.location.startswith("https://")

    def test_put_request_redirects_to_https(self, client_production_https):
        """PUT request should redirect to HTTPS in production."""
        response = client_production_https.put(
            "/api/v1/user/profile",
            base_url="http://localhost",
            json={"username": "newname"},
        )
        assert response.status_code == 301
        assert response.location.startswith("https://")

    def test_delete_request_redirects_to_https(self, client_production_https):
        """DELETE request should redirect to HTTPS in production."""
        response = client_production_https.delete(
            "/api/v1/user/account",
            base_url="http://localhost",
        )
        assert response.status_code == 301
        assert response.location.startswith("https://")
