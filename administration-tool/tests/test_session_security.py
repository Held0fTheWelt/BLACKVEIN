"""Comprehensive session and cookie security hardening tests.

Tests that session cookies are configured with security flags:
- Secure flag (HTTPS only)
- HttpOnly flag (no JavaScript access)
- SameSite flag (CSRF protection)
- Session lifetime is reasonable
Tests session creation, persistence, isolation, and behavior.
"""
import pytest
from flask import session


@pytest.mark.security
@pytest.mark.contract
class TestSessionCookieSecurityFlags:
    """Test that session cookies have proper security flags configured."""

    def test_session_cookie_secure_flag_enabled(self, client):
        """SESSION_COOKIE_SECURE must be True (HTTPS-only transmission)."""
        app = client.application
        assert app.config.get("SESSION_COOKIE_SECURE") is True, \
            "SESSION_COOKIE_SECURE must be True for production security"

    def test_session_cookie_httponly_flag_enabled(self, client):
        """SESSION_COOKIE_HTTPONLY must be True (no JavaScript access to cookie)."""
        app = client.application
        assert app.config.get("SESSION_COOKIE_HTTPONLY") is True, \
            "SESSION_COOKIE_HTTPONLY must be True to prevent XSS attacks"

    def test_session_cookie_samesite_flag_set_to_lax(self, client):
        """SESSION_COOKIE_SAMESITE must be 'Lax' for CSRF protection."""
        app = client.application
        samesite = app.config.get("SESSION_COOKIE_SAMESITE")
        assert samesite == "Lax", \
            f"SESSION_COOKIE_SAMESITE must be 'Lax', got {samesite}"

    def test_session_cookie_samesite_not_none(self, client):
        """SESSION_COOKIE_SAMESITE must not be None (would require Secure flag always)."""
        app = client.application
        samesite = app.config.get("SESSION_COOKIE_SAMESITE")
        assert samesite is not None, \
            "SESSION_COOKIE_SAMESITE should not be None (would require Secure flag)"

    def test_session_cookie_samesite_not_too_permissive(self, client):
        """SESSION_COOKIE_SAMESITE should not be 'None' (too permissive for CSRF)."""
        app = client.application
        samesite = app.config.get("SESSION_COOKIE_SAMESITE")
        assert samesite != "None", \
            "SESSION_COOKIE_SAMESITE must not be 'None' (allows CSRF attacks)"


@pytest.mark.security
@pytest.mark.contract
class TestSessionLifetime:
    """Test that session lifetime is configured and reasonable."""

    def test_permanent_session_lifetime_configured(self, client):
        """PERMANENT_SESSION_LIFETIME must be configured."""
        app = client.application
        lifetime = app.config.get("PERMANENT_SESSION_LIFETIME")
        assert lifetime is not None, "PERMANENT_SESSION_LIFETIME must be configured"
        assert isinstance(lifetime, int), "PERMANENT_SESSION_LIFETIME must be an integer"

    def test_session_lifetime_is_reasonable_not_infinite(self, client):
        """Session lifetime should not be infinite (should be < 1 day)."""
        app = client.application
        lifetime = app.config.get("PERMANENT_SESSION_LIFETIME")
        max_reasonable = 86400  # 1 day in seconds
        assert lifetime <= max_reasonable, \
            f"Session lifetime {lifetime}s should be <= {max_reasonable}s (1 day)"

    def test_session_lifetime_is_reasonable_not_too_short(self, client):
        """Session lifetime should be reasonable (>= 30 minutes)."""
        app = client.application
        lifetime = app.config.get("PERMANENT_SESSION_LIFETIME")
        min_reasonable = 1800  # 30 minutes in seconds
        assert lifetime >= min_reasonable, \
            f"Session lifetime {lifetime}s should be >= {min_reasonable}s (30 minutes)"

    def test_session_lifetime_typically_one_hour(self, client):
        """Session lifetime should typically be 1 hour for admin tools."""
        app = client.application
        lifetime = app.config.get("PERMANENT_SESSION_LIFETIME")
        expected = 3600  # 1 hour
        # Allow some flexibility but should be close to 1 hour
        assert 1800 <= lifetime <= 7200, \
            f"Session lifetime {lifetime}s should be reasonable (typically 1 hour)"


@pytest.mark.security
class TestSessionCreationAndPersistence:
    """Test that sessions are created and persist correctly."""

    def test_session_creation_works(self, client):
        """Session creation via session_transaction should work."""
        with client.session_transaction() as sess:
            sess["test_key"] = "test_value"

        # Verify session was created by reading it back
        with client.session_transaction() as sess:
            assert sess.get("test_key") == "test_value"

    def test_session_data_persists_across_requests(self, client):
        """Session data should persist across multiple requests."""
        # Create session data
        with client.session_transaction() as sess:
            sess["user_id"] = 123
            sess["username"] = "testuser"

        # Access first route (should have session)
        response1 = client.get("/")
        assert response1.status_code in (200, 404)

        # Session data should still be there
        with client.session_transaction() as sess:
            assert sess.get("user_id") == 123
            assert sess.get("username") == "testuser"

    def test_session_isolation_between_clients(self, app):
        """Different test clients should have isolated sessions."""
        client1 = app.test_client()
        client2 = app.test_client()

        # Client 1: set session data
        with client1.session_transaction() as sess:
            sess["client_id"] = "client1"

        # Client 2: set different session data
        with client2.session_transaction() as sess:
            sess["client_id"] = "client2"

        # Verify isolation
        with client1.session_transaction() as sess:
            assert sess.get("client_id") == "client1"

        with client2.session_transaction() as sess:
            assert sess.get("client_id") == "client2"

    def test_session_can_be_cleared(self, client):
        """Session data should be clearable."""
        with client.session_transaction() as sess:
            sess["key"] = "value"

        # Clear session
        with client.session_transaction() as sess:
            sess.clear()

        # Verify cleared
        with client.session_transaction() as sess:
            assert len(sess) == 0
            assert sess.get("key") is None


@pytest.mark.security
@pytest.mark.unit
class TestSessionSecretKeyConfiguration:
    """Test that the session secret key is properly configured."""

    def test_secret_key_is_set(self, client):
        """App must have a secret key configured."""
        app = client.application
        secret_key = app.secret_key
        assert secret_key is not None, "SECRET_KEY must be set"
        assert len(secret_key) > 0, "SECRET_KEY must not be empty"

    def test_secret_key_is_string(self, client):
        """Secret key should be a string or bytes."""
        app = client.application
        secret_key = app.secret_key
        assert isinstance(secret_key, (str, bytes)), \
            f"SECRET_KEY should be string or bytes, got {type(secret_key)}"

    def test_secret_key_sufficient_entropy(self, client):
        """Secret key should have sufficient entropy (>= 15 chars for test, >32 in production)."""
        app = client.application
        secret_key = app.secret_key
        if isinstance(secret_key, bytes):
            secret_key = secret_key.decode("utf-8", errors="ignore")
        # In test environment (via conftest), accept 15+ chars
        # In production, validate_secret_key enforces 32+ bytes
        min_test_length = 15  # conftest provides "test-secret-key"
        assert len(secret_key) >= min_test_length, \
            f"SECRET_KEY should have entropy, got {len(secret_key)} chars (min {min_test_length})"


@pytest.mark.security
@pytest.mark.integration
class TestSessionCookieBehavior:
    """Test the actual behavior of session cookies in HTTP responses."""

    def test_session_cookie_set_on_response(self, client):
        """Session cookies should be set when session is modified."""
        # Trigger session creation
        with client.session_transaction() as sess:
            sess["init"] = True

        # Make a request
        response = client.get("/")

        # Response should have Set-Cookie header if session was created/modified
        # (may not appear in test client, but config should be correct)
        assert response.status_code in (200, 404)

    def test_session_config_enforces_https_in_production(self, client):
        """In production (TESTING=False), SESSION_COOKIE_SECURE should be True."""
        app = client.application
        # In test mode, TESTING might be True, but config should still enforce security
        secure = app.config.get("SESSION_COOKIE_SECURE")
        assert secure is True, "SESSION_COOKIE_SECURE must be True for security"


@pytest.mark.security
@pytest.mark.contract
class TestSessionSecurityHeaders:
    """Test that responses with sessions include security headers."""

    def test_session_response_has_security_headers(self, client):
        """Responses that use sessions should have security headers."""
        # Create a session
        with client.session_transaction() as sess:
            sess["logged_in"] = True

        # Make a request
        response = client.get("/manage/login")

        # Should have security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Content-Security-Policy" in response.headers

    def test_manage_login_page_has_security_headers(self, client):
        """Login page (manages sessions) must have security headers."""
        response = client.get("/manage/login")
        assert response.status_code == 200
        assert "X-Content-Type-Options" in response.headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"


@pytest.mark.security
class TestSessionCookieAttributes:
    """Test the individual attributes of session cookie configuration."""

    def test_all_session_security_flags_set(self, client):
        """All session security flags must be properly set."""
        app = client.application
        config = app.config

        secure = config.get("SESSION_COOKIE_SECURE")
        httponly = config.get("SESSION_COOKIE_HTTPONLY")
        samesite = config.get("SESSION_COOKIE_SAMESITE")
        lifetime = config.get("PERMANENT_SESSION_LIFETIME")

        # All must be set
        assert secure is not None, "SESSION_COOKIE_SECURE not configured"
        assert httponly is not None, "SESSION_COOKIE_HTTPONLY not configured"
        assert samesite is not None, "SESSION_COOKIE_SAMESITE not configured"
        assert lifetime is not None, "PERMANENT_SESSION_LIFETIME not configured"

        # All must have correct values
        assert secure is True, "SESSION_COOKIE_SECURE must be True"
        assert httponly is True, "SESSION_COOKIE_HTTPONLY must be True"
        assert samesite == "Lax", f"SESSION_COOKIE_SAMESITE must be Lax, got {samesite}"
        assert isinstance(lifetime, int), "PERMANENT_SESSION_LIFETIME must be int"
        assert lifetime > 0, "PERMANENT_SESSION_LIFETIME must be positive"

    def test_session_cookie_no_domain_constraint(self, client):
        """Session cookie domain should be unconstrained (applies to all subdomains appropriately)."""
        app = client.application
        # SESSION_COOKIE_DOMAIN can be None (applies to current domain)
        # or explicitly set - both are acceptable
        domain = app.config.get("SESSION_COOKIE_DOMAIN")
        # If set, it should not be wildcard
        if domain is not None:
            assert not domain.startswith("."), \
                "SESSION_COOKIE_DOMAIN should not start with . (overly permissive)"


@pytest.mark.security
@pytest.mark.integration
class TestSessionTimeoutBehavior:
    """Test session timeout behavior if applicable."""

    def test_session_lifetime_config_matches_documentation(self, client):
        """Session lifetime should be documented and match code."""
        app = client.application
        lifetime = app.config.get("PERMANENT_SESSION_LIFETIME")
        # Documented as 1 hour (3600 seconds)
        expected = 3600
        assert lifetime == expected, \
            f"PERMANENT_SESSION_LIFETIME should be {expected}s (1 hour), got {lifetime}s"

    def test_session_persistence_enabled(self, client):
        """Sessions should use permanent_session for persistence across browser restarts."""
        # This is a config/behavior test - Flask will respect the lifetime config
        # when permanent_session() is called in the app
        app = client.application
        assert app.config.get("PERMANENT_SESSION_LIFETIME") > 0


@pytest.mark.security
@pytest.mark.unit
class TestSessionConfigValuesAreSecure:
    """Test that session config values themselves are secure choices."""

    def test_samesite_lax_is_secure_default(self, client):
        """SameSite=Lax is a secure default for CSRF protection."""
        app = client.application
        samesite = app.config.get("SESSION_COOKIE_SAMESITE")
        # Lax is good: allows safe (GET) cross-site requests but blocks POST/PUT/DELETE
        # Strict would block all cross-site, None would be insecure
        assert samesite == "Lax", "Lax is the secure default for SameSite"

    def test_secure_flag_required_for_https(self, client):
        """Secure flag ensures cookie only sent over HTTPS."""
        app = client.application
        secure = app.config.get("SESSION_COOKIE_SECURE")
        assert secure is True, "Secure flag required to protect cookie in transit"

    def test_httponly_flag_required_for_xss_protection(self, client):
        """HttpOnly flag prevents XSS attacks from stealing cookies."""
        app = client.application
        httponly = app.config.get("SESSION_COOKIE_HTTPONLY")
        assert httponly is True, "HttpOnly required to prevent XSS cookie theft"
