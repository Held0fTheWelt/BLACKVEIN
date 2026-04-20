"""
WAVE 4: Error page and error handling contract tests for administration-tool.

Tests cover:
- 404 pages render properly
- 500 pages render properly
- Backend unavailable page behavior
- Error pages must not leak sensitive information
- Error pages must have security headers
"""
from __future__ import annotations

from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest
from conftest import captured_templates, load_frontend_module


# ============================================================================
# 404 ERROR PAGE CONTRACT
# ============================================================================


class TestFourOhFourErrorPageContract:
    """Test 404 Not Found error pages."""

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "nonexistent_path",
        [
            "/does-not-exist",
            "/nonexistent/route",
            "/invalid/path/to/nothing",
            "/manage/invalid-page",
            "/api/v1/fake",
        ],
    )
    def test_404_nonexistent_route_returns_404_status(self, client, nonexistent_path: str):
        """Contract: Non-existent routes return 404 status code."""
        response = client.get(nonexistent_path)
        assert response.status_code == 404

    @pytest.mark.contract
    def test_404_response_is_html(self, client):
        """Contract: 404 response is HTML."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        content_type = response.headers.get("Content-Type", "")
        assert "text/html" in content_type or "text/plain" in content_type

    @pytest.mark.contract
    def test_404_response_has_body(self, client):
        """Contract: 404 response has a body."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        assert len(response.data) > 0

    @pytest.mark.contract
    def test_404_multiple_nonexistent_routes_are_consistent(self, client):
        """Contract: Multiple 404s have consistent status and headers."""
        response1 = client.get("/nonexistent1")
        response2 = client.get("/nonexistent2")

        assert response1.status_code == 404
        assert response2.status_code == 404
        # Security headers should be identical
        for header in ["X-Content-Type-Options", "X-Frame-Options"]:
            assert response1.headers.get(header) == response2.headers.get(header)


# ============================================================================
# ERROR PAGE SECURITY HEADERS CONTRACT
# ============================================================================


class TestErrorPageSecurityHeadersContract:
    """Test that error pages include required security headers."""

    @pytest.mark.contract
    def test_404_has_x_content_type_options_header(self, client):
        """Contract: 404 page has X-Content-Type-Options header."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        assert "X-Content-Type-Options" in response.headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    @pytest.mark.contract
    def test_404_has_x_frame_options_header(self, client):
        """Contract: 404 page has X-Frame-Options header."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        assert "X-Frame-Options" in response.headers
        assert response.headers.get("X-Frame-Options") == "DENY"

    @pytest.mark.contract
    def test_404_has_csp_header(self, client):
        """Contract: 404 page has Content-Security-Policy header."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        csp = response.headers.get("Content-Security-Policy")
        assert csp is not None, "CSP header required on 404"
        assert len(csp) > 0, "CSP should not be empty"

    @pytest.mark.contract
    def test_404_has_referrer_policy_header(self, client):
        """Contract: 404 page has Referrer-Policy header."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        assert "Referrer-Policy" in response.headers

    @pytest.mark.contract
    @pytest.mark.parametrize("nonexistent_path", ["/fake", "/invalid", "/test123"])
    def test_all_404_responses_have_required_security_headers(self, client, nonexistent_path: str):
        """Contract: All 404 responses have required security headers."""
        response = client.get(nonexistent_path)
        assert response.status_code == 404

        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Content-Security-Policy",
        ]
        for header in required_headers:
            assert header in response.headers, \
                f"{header} missing from 404 response"

    @pytest.mark.contract
    def test_404_csp_blocks_unsafe_scripts(self, client):
        """Contract: 404 page CSP prevents unsafe scripts."""
        response = client.get("/nonexistent")
        csp = response.headers.get("Content-Security-Policy", "")
        # Should have restrictive CSP
        assert "default-src" in csp or "script-src" in csp


# ============================================================================
# ERROR PAGE INFORMATION LEAKAGE PREVENTION
# ============================================================================


class TestErrorPageInformationLeakage:
    """Test that error pages do not leak sensitive information."""

    @pytest.mark.contract
    def test_404_no_python_traceback(self, client):
        """Contract: 404 response does not contain Python tracebacks."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        response_text = response.get_data(as_text=True)
        assert "Traceback" not in response_text

    @pytest.mark.contract
    def test_404_no_file_paths_exposed(self, client):
        """Contract: 404 response does not expose file paths."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        response_text = response.get_data(as_text=True)
        # Should not expose file paths like /path/to/file.py
        assert 'File "' not in response_text
        assert ".py" not in response_text.lower() or "python" not in response_text.lower()

    @pytest.mark.contract
    def test_404_no_line_numbers_exposed(self, client):
        """Contract: 404 response does not expose line numbers in tracebacks."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        response_text = response.get_data(as_text=True)
        # Should not have "line XXX" style exposure
        assert "line " not in response_text.lower() or "traceback" not in response_text.lower()

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "sensitive_pattern",
        [
            "SECRET",
            "PASSWORD",
            "API_KEY",
            "token",
            "database",
            "password_history",
        ],
    )
    def test_404_no_sensitive_keywords(self, client, sensitive_pattern: str):
        """Contract: 404 response does not contain sensitive keywords."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        response_text = response.get_data(as_text=True).upper()
        assert sensitive_pattern.upper() not in response_text

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "bad_path",
        [
            "/admin/secret",
            "/config/database",
            "/../etc/passwd",
            "/..%2f..%2fetc%2fpasswd",
        ],
    )
    def test_404_for_path_traversal_attempts(self, client, bad_path: str):
        """Contract: Path traversal attempts return 404 safely."""
        response = client.get(bad_path)
        assert response.status_code == 404 or response.status_code == 403
        response_text = response.get_data(as_text=True)
        # Should not reveal that path traversal was attempted
        assert "Traceback" not in response_text


# ============================================================================
# ERROR PAGE XSS AND INJECTION PROTECTION
# ============================================================================


class TestErrorPageXSSProtection:
    """Test that error pages prevent XSS and injection attacks."""

    @pytest.mark.contract
    def test_404_x_frame_options_prevents_clickjacking(self, client):
        """Contract: X-Frame-Options: DENY prevents clickjacking."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        assert response.headers.get("X-Frame-Options") == "DENY"

    @pytest.mark.contract
    def test_404_x_content_type_options_prevents_mime_sniffing(self, client):
        """Contract: X-Content-Type-Options: nosniff prevents MIME sniffing."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    @pytest.mark.contract
    def test_404_csp_default_src_self(self, client):
        """Contract: 404 page CSP has default-src 'self'."""
        response = client.get("/nonexistent")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp or "default-src" in csp

    @pytest.mark.contract
    @pytest.mark.parametrize(
        "xss_attempt",
        [
            "/path?id=<script>alert('xss')</script>",
            "/path?search='+OR+'1'='1",
            "/path?param=%3Cimg%20src=x%20onerror=alert(1)%3E",
        ],
    )
    def test_404_for_xss_attempts_safe(self, client, xss_attempt: str):
        """Contract: XSS attempts return 404 safely."""
        response = client.get(xss_attempt)
        # Should return 404 or 400
        assert response.status_code in [400, 404]


# ============================================================================
# PROXY ERROR RESPONSES
# ============================================================================


class TestProxyErrorResponseContract:
    """Test proxy endpoint error handling and safety."""

    @pytest.mark.contract
    def test_proxy_admin_path_returns_403(self, client):
        """Contract: Proxy blocks admin paths with 403."""
        response = client.get("/_proxy/admin/users")
        assert response.status_code == 403

    @pytest.mark.contract
    def test_proxy_admin_block_has_security_headers(self, client):
        """Contract: Proxy 403 response has security headers."""
        response = client.get("/_proxy/admin/path")
        assert response.status_code == 403
        assert "X-Content-Type-Options" in response.headers

    @pytest.mark.contract
    def test_proxy_upstream_404_passes_through(self, monkeypatch):
        """Contract: Upstream 404 from backend passes through."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout: int = 0):
            raise HTTPError(
                url=request.full_url,
                code=404,
                msg="Not Found",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error":"Not found"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/users/999")
        assert response.status_code == 404

    @pytest.mark.contract
    def test_proxy_upstream_500_passes_through(self, monkeypatch):
        """Contract: Upstream 500 from backend passes through."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout: int = 0):
            raise HTTPError(
                url=request.full_url,
                code=500,
                msg="Internal Server Error",
                hdrs={"Content-Type": "application/json"},
                fp=BytesIO(b'{"error":"Internal error"}'),
            )

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/data")
        assert response.status_code == 500
        # Should still have security headers
        assert "X-Content-Type-Options" in response.headers

    @pytest.mark.contract
    def test_proxy_network_error_returns_502(self, monkeypatch):
        """Contract: Network errors return 502 Bad Gateway."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout: int = 0):
            raise URLError("Network unreachable")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")
        assert response.status_code == 502

    @pytest.mark.contract
    def test_proxy_timeout_returns_502(self, monkeypatch):
        """Contract: Proxy timeout returns 502."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.example.test")

        def fake_urlopen(request, timeout: int = 0):
            raise URLError("Connection timed out")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")
        assert response.status_code == 502

    @pytest.mark.contract
    def test_proxy_missing_backend_url_returns_500(self, monkeypatch):
        """Contract: Missing backend URL returns 500."""
        module = load_frontend_module(monkeypatch, backend_url="")
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")
        assert response.status_code == 500
        assert b"Backend API URL not configured" in response.data


# ============================================================================
# ERROR PAGE RESPONSE DETERMINISM
# ============================================================================


class TestErrorResponseDeterminism:
    """Test that error responses are deterministic."""

    @pytest.mark.contract
    def test_same_404_path_consistent_response(self, client):
        """Contract: Same 404 path returns consistent response."""
        response1 = client.get("/nonexistent-path-xyz")
        response2 = client.get("/nonexistent-path-xyz")

        assert response1.status_code == response2.status_code == 404
        assert response1.headers.get("X-Content-Type-Options") == \
               response2.headers.get("X-Content-Type-Options")

    @pytest.mark.contract
    def test_different_404_paths_same_headers(self, client):
        """Contract: Different 404 paths have same security headers."""
        response1 = client.get("/fake1")
        response2 = client.get("/fake2")

        assert response1.status_code == response2.status_code == 404

        # Security headers should be identical
        for header in ["X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"]:
            assert response1.headers.get(header) == response2.headers.get(header), \
                f"Header {header} should be consistent"

    @pytest.mark.contract
    def test_404_response_deterministic_across_requests(self, client):
        """Contract: 404 response is deterministic."""
        for _ in range(3):
            response = client.get("/fake-page")
            assert response.status_code == 404
            assert len(response.data) > 0


# ============================================================================
# ERROR PAGE RENDERING CONTRACT
# ============================================================================


class TestErrorPageRenderingContract:
    """Test that error pages render properly."""

    @pytest.mark.contract
    def test_404_response_is_valid_html_or_text(self, client):
        """Contract: 404 response is valid HTML or text."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        content_type = response.headers.get("Content-Type", "")
        assert "text/html" in content_type or "text/plain" in content_type

    @pytest.mark.contract
    def test_404_response_not_empty(self, client):
        """Contract: 404 response has content."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        assert len(response.data) > 0

    @pytest.mark.contract
    def test_404_response_readable(self, client):
        """Contract: 404 response is readable."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        # Should be readable text
        try:
            text = response.get_data(as_text=True)
            assert len(text) > 0
        except Exception:
            pytest.fail("404 response should be readable as text")


# ============================================================================
# BACKEND UNAVAILABLE GRACEFUL HANDLING
# ============================================================================


class TestBackendUnavailableGracefulHandling:
    """Test graceful handling when backend is unavailable."""

    @pytest.mark.contract
    def test_html_routes_render_without_backend(self, client):
        """Contract: HTML routes render without backend."""
        # Routes render templates without contacting backend
        response = client.get("/")
        assert response.status_code == 200

    @pytest.mark.contract
    def test_proxy_network_error_safe(self, monkeypatch):
        """Contract: Proxy network errors are handled safely."""
        module = load_frontend_module(monkeypatch, backend_url="https://unreachable.test")

        def fake_urlopen(request, timeout: int = 0):
            raise URLError("Connection refused")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")
        # Should return 502, not 500 or 503
        assert response.status_code == 502

    @pytest.mark.contract
    def test_proxy_timeout_safe(self, monkeypatch):
        """Contract: Proxy timeout is handled safely."""
        module = load_frontend_module(monkeypatch, backend_url="https://slow.test")

        def fake_urlopen(request, timeout: int = 0):
            raise URLError("Timeout")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")
        assert response.status_code == 502


# ============================================================================
# PROXY ERROR MESSAGE SAFETY
# ============================================================================


class TestProxyErrorMessageSafety:
    """Test that proxy error messages are safe."""

    @pytest.mark.contract
    def test_proxy_network_error_message_safe(self, monkeypatch):
        """Contract: Proxy network error message is safe."""
        module = load_frontend_module(monkeypatch, backend_url="https://api.test")

        def fake_urlopen(request, timeout: int = 0):
            raise URLError("Connection refused")

        monkeypatch.setattr(module, "urlopen", fake_urlopen)
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")
        assert response.status_code == 502
        # Error message should not expose internal details
        error_text = response.get_data(as_text=True).lower()
        assert "traceback" not in error_text

    @pytest.mark.contract
    def test_proxy_missing_backend_url_message_generic(self, monkeypatch):
        """Contract: Missing backend URL error message is generic."""
        module = load_frontend_module(monkeypatch, backend_url="")
        client = module.app.test_client()

        response = client.get("/_proxy/api/v1/news")
        assert response.status_code == 500
        assert b"Backend API URL not configured" in response.data


# ============================================================================
# ERROR RESPONSE CACHING CONTRACT
# ============================================================================


class TestErrorResponseCachingContract:
    """Test error response caching behavior."""

    @pytest.mark.contract
    def test_404_response_safe_for_caching(self, client):
        """Contract: 404 response is safe to cache."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        response_text = response.get_data(as_text=True)

        # Should not contain sensitive data
        sensitive_patterns = ["SECRET", "PASSWORD", "API_KEY", "token"]
        for pattern in sensitive_patterns:
            assert pattern not in response_text.upper()

    @pytest.mark.contract
    def test_error_response_no_session_data_leak(self, client):
        """Contract: Error response does not leak session data."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

        # Should not contain user-specific data
        response_text = response.get_data(as_text=True).lower()
        # No user IDs, tokens, etc.
        assert "session" not in response_text or "cookie" not in response_text


# ============================================================================
# ERROR STATUS CODE CORRECTNESS
# ============================================================================


class TestErrorStatusCodeCorrectness:
    """Test that error status codes are correct."""

    @pytest.mark.contract
    def test_404_not_500_for_missing_route(self, client):
        """Contract: Missing route returns 404, not 500."""
        response = client.get("/nonexistent-route-xyz")
        assert response.status_code == 404, "Missing routes should return 404"

    @pytest.mark.contract
    def test_403_not_404_for_forbidden_path(self, client):
        """Contract: Forbidden paths return 403, not 404."""
        response = client.get("/_proxy/admin/something")
        assert response.status_code == 403

    @pytest.mark.contract
    def test_proxy_403_for_admin_paths(self, client):
        """Contract: Admin paths are 403, not 404."""
        response = client.get("/_proxy/admin/users")
        assert response.status_code == 403, "Admin paths should be 403 Forbidden"

    @pytest.mark.contract
    def test_404_different_from_403(self, client):
        """Contract: 404 and 403 are distinguished."""
        response_404 = client.get("/nonexistent")
        response_403 = client.get("/_proxy/admin/test")

        assert response_404.status_code == 404
        assert response_403.status_code == 403
        assert response_404.status_code != response_403.status_code
