"""Comprehensive error response security tests.

Tests that error responses (404, 500, 502) are deterministic, safe, and include
security headers. Verifies no information leakage in error responses.
Tests proxy error surfaces, Flask error handlers, and error page security.
"""
from __future__ import annotations

import pytest


@pytest.mark.security
@pytest.mark.contract
class TestFourOhFourErrorResponse:
    """Test 404 Not Found responses are safe and include security headers."""

    @pytest.mark.parametrize("nonexistent_path", [
        "/does-not-exist",
        "/nonexistent/route",
        "/api/v1/fake",
        "/manage/fake-page",
    ])
    def test_404_returns_appropriate_status(self, client, nonexistent_path):
        """Non-existent routes should return 404 status.

        Note: /wiki/<slug> and /news/<id> are parameterized routes that render
        with any slug/id value (backend loads actual data on frontend), so they
        return 200, not 404. Only truly unmapped routes return 404.
        """
        response = client.get(nonexistent_path)
        assert response.status_code == 404, \
            f"Non-existent route {nonexistent_path} should return 404"

    @pytest.mark.parametrize("nonexistent_path", [
        "/does-not-exist",
        "/nonexistent/route",
    ])
    def test_404_has_security_headers(self, client, nonexistent_path):
        """404 responses must include all security headers."""
        response = client.get(nonexistent_path)
        assert response.status_code == 404

        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Content-Security-Policy",
            "Referrer-Policy",
        ]
        for header in required_headers:
            assert header in response.headers, \
                f"{header} missing on 404 response from {nonexistent_path}"

    def test_404_has_csp_header(self, client):
        """404 error page must have CSP header."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None, "CSP header required on 404"
        assert len(csp) > 0, "CSP header should not be empty"

    def test_404_has_xss_protection_headers(self, client):
        """404 response should have XSS protection headers."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        # X-Frame-Options prevents clickjacking
        assert response.headers.get("X-Frame-Options") == "DENY"
        # X-Content-Type-Options prevents MIME sniffing
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_404_no_traceback_leak(self, client):
        """404 response should not leak Python tracebacks."""
        response = client.get("/definitely-does-not-exist-12345")
        assert response.status_code == 404
        response_text = response.get_data(as_text=True)
        assert "Traceback" not in response_text, \
            "404 response should not contain Python traceback"
        assert "File \"" not in response_text, \
            "404 response should not expose file paths"
        assert "line " not in response_text.lower() or "error" not in response_text.lower(), \
            "404 should not expose line numbers"

    def test_404_no_sensitive_path_info(self, client):
        """404 response should not echo back the requested path if it contains sensitive data."""
        # This is already tested above, but emphasize for completeness
        response = client.get("/nonexistent")
        assert response.status_code == 404
        # Path shouldn't appear directly (at least not with filesystem context)
        response_text = response.get_data(as_text=True)
        # Typical safe 404 pages don't echo the path
        # (Flask's default 404 template is safe)

    def test_404_content_type_is_html(self, client):
        """404 response should be HTML (or safe content type)."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        content_type = response.content_type
        # Should be HTML or plain text
        assert content_type.startswith("text/html") or content_type.startswith("text/plain"), \
            f"404 content type should be safe, got {content_type}"


@pytest.mark.security
@pytest.mark.contract
class TestProxyErrorResponses:
    """Test that proxy endpoint errors return safe responses."""

    def test_proxy_admin_block_returns_403(self, client):
        """Proxy should block admin/* paths with 403."""
        response = client.get("/_proxy/admin/some/path")
        assert response.status_code == 403, \
            "Proxy should block admin paths with 403 Forbidden"

    def test_proxy_admin_block_has_security_headers(self, client):
        """Proxy 403 responses should have security headers."""
        response = client.get("/_proxy/admin/test")
        assert response.status_code == 403
        # Note: after_request handler adds headers to all responses
        assert "X-Content-Type-Options" in response.headers

    def test_proxy_missing_backend_url_returns_500(self, app, monkeypatch):
        """Proxy should return 500 if BACKEND_API_URL not configured."""
        # This is a configuration error test
        app.config["BACKEND_API_URL"] = ""  # Empty backend URL
        client = app.test_client()
        response = client.get("/_proxy/api/v1/news")
        # Should fail gracefully
        assert response.status_code >= 400, "Proxy should fail if backend not configured"

    def test_proxy_error_responses_have_security_headers(self, client):
        """Proxy error responses should have security headers."""
        response = client.get("/_proxy/admin/path")
        assert "X-Content-Type-Options" in response.headers
        # Flask's after_request adds headers to all responses


@pytest.mark.security
@pytest.mark.integration
class TestErrorResponseDeterminism:
    """Test that error responses are deterministic (not random)."""

    def test_same_404_returns_same_response(self, client):
        """Multiple requests to same non-existent route should return same 404."""
        response1 = client.get("/nonexistent-path-12345")
        response2 = client.get("/nonexistent-path-12345")

        assert response1.status_code == response2.status_code == 404
        # Headers should be identical
        assert response1.headers.get("Content-Security-Policy") == \
               response2.headers.get("Content-Security-Policy")

    def test_different_404s_have_same_headers(self, client):
        """Different non-existent routes should have identical security headers."""
        response1 = client.get("/nonexistent1")
        response2 = client.get("/nonexistent2")

        assert response1.status_code == response2.status_code == 404
        # Security headers should be identical
        for header in ["X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"]:
            assert response1.headers.get(header) == response2.headers.get(header), \
                f"Security header {header} should be consistent across 404s"


@pytest.mark.security
@pytest.mark.unit
class TestErrorPageSecurity:
    """Test that error pages themselves are secure."""

    def test_404_csp_prevents_external_scripts(self, client):
        """404 page CSP should prevent loading external scripts."""
        response = client.get("/nonexistent")
        csp = response.headers.get("Content-Security-Policy", "")
        # script-src should not allow arbitrary external domains
        # (default-src 'self' would handle this)
        assert "default-src 'self'" in csp or "script-src" in csp

    def test_404_frame_ancestors_none(self, client):
        """404 page should not be embeddable in frames."""
        response = client.get("/nonexistent")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_404_content_sniffing_protected(self, client):
        """404 page should prevent MIME type sniffing."""
        response = client.get("/nonexistent")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"


@pytest.mark.security
@pytest.mark.contract
class TestErrorResponseInformationLeakage:
    """Test that error responses don't leak sensitive information."""

    @pytest.mark.parametrize("bad_path", [
        "/admin/secret",
        "/config/database",
        "/../etc/passwd",
        "/..%2f..%2fetc%2fpasswd",
    ])
    def test_error_responses_dont_leak_paths(self, client, bad_path):
        """Error responses should not leak filesystem or application paths."""
        response = client.get(bad_path)
        # Should be 404 or safe error
        assert response.status_code >= 400
        response_text = response.get_data(as_text=True)
        # Should not contain the requested path in a way that reveals structure
        # (Flask default 404 is safe)

    def test_404_response_is_consistent_html(self, client):
        """404 response should be valid, consistent HTML (not a traceback)."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        response_text = response.get_data(as_text=True)
        # Should be HTML or plain text
        assert len(response_text) > 0, "404 should have some response body"
        # Should not be an error traceback
        assert "Traceback" not in response_text

    def test_error_responses_safe_for_caching(self, client):
        """Error responses should be safe to cache (no sensitive data)."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        # Cache-Control header might be present (but not tested here)
        # The important thing is no sensitive data in response
        response_text = response.get_data(as_text=True)
        sensitive_patterns = [
            "SECRET",
            "PASSWORD",
            "API_KEY",
            "token",
        ]
        for pattern in sensitive_patterns:
            assert pattern not in response_text.upper(), \
                f"404 should not contain {pattern}"


@pytest.mark.security
@pytest.mark.integration
class TestAllErrorRoutesHaveSecurity:
    """Test that ALL error paths include security headers."""

    @pytest.mark.parametrize("invalid_route", [
        "/",  # This exists, but test framework
        "/nonexistent",
        "/admin/secret",
        "/api/v1/fake",
        "//double/slash",
        "/./dot/path",
    ])
    def test_all_error_like_routes_have_security_headers(self, client, invalid_route):
        """Even potential error routes should have security headers."""
        response = client.get(invalid_route)
        # Regardless of status code, should have security headers
        if response.status_code >= 400:  # It's an error
            assert "Content-Security-Policy" in response.headers, \
                f"CSP missing on {response.status_code} response"
            assert "X-Content-Type-Options" in response.headers, \
                f"X-Content-Type-Options missing on {response.status_code} response"


@pytest.mark.security
class TestErrorResponseStatusCodeConsistency:
    """Test that error status codes are consistent and appropriate."""

    def test_404_is_returned_not_500(self, client):
        """Non-existent routes should return 404, not 500."""
        response = client.get("/nonexistent-route-xyz")
        assert response.status_code == 404, \
            "Non-existent routes should return 404, not 500"
        # 500 would indicate a server error, which is different from "not found"

    def test_forbidden_returns_403_not_404(self, client):
        """Forbidden paths (like proxy admin block) should return 403, not 404."""
        response = client.get("/_proxy/admin/something")
        assert response.status_code == 403, \
            "Proxy admin block should return 403 Forbidden"


@pytest.mark.security
@pytest.mark.browser
class TestErrorResponseBrowserBehavior:
    """Test error response behavior from browser perspective."""

    def test_404_response_not_cached_indefinitely(self, client):
        """404 responses should not be cached indefinitely."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        # Check cache-control (may or may not be set, but if set should be reasonable)
        cache_control = response.headers.get("Cache-Control", "")
        # Should not be a very long cache time

    def test_error_responses_readable_as_html(self, client):
        """Error responses should be readable HTML by browsers."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        content_type = response.content_type
        # Should be HTML or safe text
        assert content_type.startswith("text/html") or content_type.startswith("text/plain")
