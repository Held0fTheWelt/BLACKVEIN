import pytest
from flask import session


class TestSessionSecurity:
    """Test suite for session and cookie security hardening."""

    @pytest.mark.security
    def test_session_cookie_httponly_flag(self, client):
        """Test that session cookies have HttpOnly flag set."""
        # Trigger session creation
        with client.session_transaction() as sess:
            sess['test_key'] = 'test_value'

        # Verify HttpOnly flag is set in config
        assert client.application.config['SESSION_COOKIE_HTTPONLY'] is True

    @pytest.mark.security
    def test_session_cookie_secure_flag(self, client):
        """Test that session cookies have Secure flag set."""
        assert client.application.config['SESSION_COOKIE_SECURE'] is True

    @pytest.mark.security
    def test_session_cookie_samesite_flag(self, client):
        """Test that session cookies have SameSite flag set."""
        assert client.application.config['SESSION_COOKIE_SAMESITE'] == 'Lax'

    @pytest.mark.security
    def test_session_lifetime_reasonable(self, client):
        """Test that session lifetime is set to a reasonable duration."""
        lifetime = client.application.config['PERMANENT_SESSION_LIFETIME']
        # Should be less than 1 day (86400 seconds)
        assert lifetime < 86400
        # Should be at least 30 minutes (1800 seconds)
        assert lifetime >= 1800

    @pytest.mark.security
    def test_security_header_x_content_type_options(self, client):
        """Test that X-Content-Type-Options header is present."""
        response = client.get('/')
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'

    @pytest.mark.security
    def test_security_header_x_frame_options(self, client):
        """Test that X-Frame-Options header is set to DENY."""
        response = client.get('/')
        assert response.headers.get('X-Frame-Options') == 'DENY'

    @pytest.mark.security
    def test_security_header_referrer_policy(self, client):
        """Test that Referrer-Policy header is present."""
        response = client.get('/')
        assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'

    @pytest.mark.security
    def test_security_header_permissions_policy(self, client):
        """Test that Permissions-Policy header restricts sensitive features."""
        response = client.get('/')
        policy = response.headers.get('Permissions-Policy', '')
        assert 'geolocation=()' in policy
        assert 'microphone=()' in policy
        assert 'camera=()' in policy

    @pytest.mark.security
    def test_csp_header_present(self, client):
        """Test that Content-Security-Policy header is present."""
        response = client.get('/')
        assert 'Content-Security-Policy' in response.headers

    @pytest.mark.security
    def test_csp_default_src_self(self, client):
        """Test that CSP default-src restricts to self."""
        response = client.get('/')
        csp = response.headers.get('Content-Security-Policy', '')
        assert "default-src 'self'" in csp

    @pytest.mark.security
    def test_csp_object_src_none(self, client):
        """Test that CSP blocks object/embed elements."""
        response = client.get('/')
        csp = response.headers.get('Content-Security-Policy', '')
        assert "object-src 'none'" in csp

    @pytest.mark.security
    def test_csp_frame_ancestors_none(self, client):
        """Test that CSP blocks frame embedding."""
        response = client.get('/')
        csp = response.headers.get('Content-Security-Policy', '')
        assert "frame-ancestors 'none'" in csp

    @pytest.mark.security
    def test_csp_form_action_self(self, client):
        """Test that CSP restricts form submissions to self."""
        response = client.get('/')
        csp = response.headers.get('Content-Security-Policy', '')
        assert "form-action 'self'" in csp

    @pytest.mark.security
    def test_csp_base_uri_self(self, client):
        """Test that CSP restricts base URI to self."""
        response = client.get('/')
        csp = response.headers.get('Content-Security-Policy', '')
        assert "base-uri 'self'" in csp

    @pytest.mark.security
    def test_secret_key_is_secure(self, client):
        """Test that SECRET_KEY is properly set."""
        app = client.application
        secret_key = app.secret_key
        # Secret key should be set and not empty
        assert secret_key is not None
        assert len(secret_key) > 0

    @pytest.mark.security
    def test_secret_key_length_sufficient_for_generated_keys(self, client):
        """Test that generated SECRET_KEY has sufficient length.

        In test environment, conftest provides a short key which is acceptable.
        In production, validate_secret_key enforces 32+ bytes.
        """
        from app import validate_secret_key

        # Verify the validation function enforces 32 bytes in production
        with pytest.raises(ValueError, match="secret_key"):
            validate_secret_key("short_key", is_production=True)

        # Verify 32+ bytes is accepted
        long_key = "a" * 32
        assert validate_secret_key(long_key, is_production=True) is True
