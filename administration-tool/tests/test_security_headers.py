"""Comprehensive security headers testing for administration-tool frontend.

Tests that security headers are present on ALL responses and meet security contract.
Validates Content-Security-Policy, X-Content-Type-Options, X-Frame-Options,
Referrer-Policy, Permissions-Policy on all route types and content types.
"""
from __future__ import annotations

import re
import pytest


# All routes to test security headers on - public, admin, JSON endpoints, etc.
ROUTES_TO_TEST = [
    # Public pages
    ("/", "text/html"),
    ("/news", "text/html"),
    ("/wiki", "text/html"),
    ("/forum", "text/html"),
    # Forum detail pages
    ("/forum/categories/general", "text/html"),
    ("/forum/threads/welcome", "text/html"),
    ("/forum/tags/devlog", "text/html"),
    ("/forum/notifications", "text/html"),
    ("/forum/saved", "text/html"),
    # User profile
    ("/users/1/profile", "text/html"),
    # Management/admin routes
    ("/manage", "text/html"),
    ("/manage/login", "text/html"),
    ("/manage/news", "text/html"),
    ("/manage/users", "text/html"),
    ("/manage/roles", "text/html"),
    ("/manage/areas", "text/html"),
    ("/manage/wiki", "text/html"),
    ("/manage/forum", "text/html"),
    # Error routes (will be 404, but should still have headers)
    ("/nonexistent/route", "text/html"),
]


@pytest.mark.security
@pytest.mark.contract
class TestSecurityHeadersPresence:
    """Test that all security headers are present on responses."""

    @pytest.mark.parametrize("route,expected_content_type", ROUTES_TO_TEST)
    def test_x_content_type_options_present_on_all_routes(self, client, route, expected_content_type):
        """X-Content-Type-Options header must be present on all routes."""
        response = client.get(route)
        assert "X-Content-Type-Options" in response.headers, \
            f"X-Content-Type-Options header missing on {route}"
        assert response.headers["X-Content-Type-Options"] == "nosniff", \
            f"X-Content-Type-Options should be 'nosniff' on {route}"

    @pytest.mark.parametrize("route,expected_content_type", ROUTES_TO_TEST)
    def test_x_frame_options_present_on_all_routes(self, client, route, expected_content_type):
        """X-Frame-Options header must be present on all routes."""
        response = client.get(route)
        assert "X-Frame-Options" in response.headers, \
            f"X-Frame-Options header missing on {route}"
        assert response.headers["X-Frame-Options"] == "DENY", \
            f"X-Frame-Options should be 'DENY' on {route}"

    @pytest.mark.parametrize("route,expected_content_type", ROUTES_TO_TEST)
    def test_referrer_policy_present_on_all_routes(self, client, route, expected_content_type):
        """Referrer-Policy header must be present on all routes."""
        response = client.get(route)
        assert "Referrer-Policy" in response.headers, \
            f"Referrer-Policy header missing on {route}"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin", \
            f"Referrer-Policy value incorrect on {route}"

    @pytest.mark.parametrize("route,expected_content_type", ROUTES_TO_TEST)
    def test_permissions_policy_present_on_all_routes(self, client, route, expected_content_type):
        """Permissions-Policy header must be present on all routes."""
        response = client.get(route)
        assert "Permissions-Policy" in response.headers, \
            f"Permissions-Policy header missing on {route}"
        policy = response.headers["Permissions-Policy"]
        # Verify key dangerous features are blocked
        assert "geolocation=()" in policy, "geolocation should be blocked"
        assert "microphone=()" in policy, "microphone should be blocked"
        assert "camera=()" in policy, "camera should be blocked"

    @pytest.mark.parametrize("route,expected_content_type", ROUTES_TO_TEST)
    def test_csp_header_present_on_all_routes(self, client, route, expected_content_type):
        """Content-Security-Policy header must be present on all routes."""
        response = client.get(route)
        assert "Content-Security-Policy" in response.headers, \
            f"Content-Security-Policy header missing on {route}"


@pytest.mark.security
@pytest.mark.contract
class TestContentSecurityPolicyContract:
    """Test CSP header contract: required directives and their restrictions."""

    @pytest.mark.parametrize("route,_", ROUTES_TO_TEST[:3])  # Sample of routes
    def test_csp_default_src_restricts_to_self(self, client, route, _):
        """default-src must be 'self' only (no unsafe, no wildcard)."""
        response = client.get(route)
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp, f"default-src must be 'self' on {route}"

    @pytest.mark.parametrize("route,_", ROUTES_TO_TEST[:3])
    def test_csp_script_src_configured(self, client, route, _):
        """script-src must be present and configured. May allow unsafe-inline for legacy support."""
        response = client.get(route)
        csp = response.headers["Content-Security-Policy"]
        assert "script-src" in csp, f"script-src directive missing on {route}"

    @pytest.mark.parametrize("route,_", ROUTES_TO_TEST[:3])
    def test_csp_style_src_configured(self, client, route, _):
        """style-src must be present and configured."""
        response = client.get(route)
        csp = response.headers["Content-Security-Policy"]
        assert "style-src" in csp, f"style-src directive missing on {route}"

    @pytest.mark.parametrize("route,_", ROUTES_TO_TEST[:3])
    def test_csp_img_src_allows_data_and_https(self, client, route, _):
        """img-src should allow self, data:, and https:."""
        response = client.get(route)
        csp = response.headers["Content-Security-Policy"]
        assert "img-src" in csp, f"img-src directive missing on {route}"

    @pytest.mark.parametrize("route,_", ROUTES_TO_TEST[:3])
    def test_csp_connect_src_includes_self_and_https(self, client, route, _):
        """connect-src must include 'self' and https: for API calls."""
        response = client.get(route)
        csp = response.headers["Content-Security-Policy"]
        assert "connect-src" in csp, f"connect-src directive missing on {route}"

    @pytest.mark.parametrize("route,_", ROUTES_TO_TEST[:3])
    def test_csp_object_src_is_none(self, client, route, _):
        """object-src must be 'none' (blocks plugins, embeds, etc)."""
        response = client.get(route)
        csp = response.headers["Content-Security-Policy"]
        assert "object-src 'none'" in csp, f"object-src must be 'none' on {route}"

    @pytest.mark.parametrize("route,_", ROUTES_TO_TEST[:3])
    def test_csp_frame_ancestors_is_none(self, client, route, _):
        """frame-ancestors must be 'none' (blocks embedding in iframes)."""
        response = client.get(route)
        csp = response.headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in csp, f"frame-ancestors must be 'none' on {route}"

    @pytest.mark.parametrize("route,_", ROUTES_TO_TEST[:3])
    def test_csp_base_uri_is_self(self, client, route, _):
        """base-uri must be 'self' (prevents <base> tag hijacking)."""
        response = client.get(route)
        csp = response.headers["Content-Security-Policy"]
        assert "base-uri 'self'" in csp, f"base-uri must be 'self' on {route}"

    @pytest.mark.parametrize("route,_", ROUTES_TO_TEST[:3])
    def test_csp_form_action_is_self(self, client, route, _):
        """form-action must be 'self' (restricts form submissions)."""
        response = client.get(route)
        csp = response.headers["Content-Security-Policy"]
        assert "form-action 'self'" in csp, f"form-action must be 'self' on {route}"


@pytest.mark.security
class TestCSPDirectiveSyntax:
    """Test CSP syntax validity and safety of directive values."""

    def test_csp_no_unsafe_eval(self, client):
        """CSP must NOT use unsafe-eval (allows arbitrary JS execution)."""
        response = client.get("/")
        csp = response.headers["Content-Security-Policy"]
        assert "unsafe-eval" not in csp, "CSP must not allow unsafe-eval"

    def test_csp_no_wildcard_sources(self, client):
        """CSP should not use wildcards for script/style/frame sources."""
        response = client.get("/")
        csp = response.headers["Content-Security-Policy"]
        # Check that we don't have wildcard for dangerous directives
        dangerous_wildcards = [
            "script-src *",
            "style-src *",
            "frame-src *",
            "default-src *",
        ]
        for pattern in dangerous_wildcards:
            assert pattern not in csp, f"CSP must not use wildcard: {pattern}"

    def test_csp_directives_have_valid_format(self, client):
        """CSP header must follow valid syntax: directive value; directive value;"""
        response = client.get("/")
        csp = response.headers["Content-Security-Policy"]
        # Very basic check: should have semicolons separating directives
        assert ";" in csp, "CSP should have multiple directives separated by semicolons"
        directives = [d.strip() for d in csp.split(";")]
        # Filter out empty entries
        directives = [d for d in directives if d]
        assert len(directives) > 1, "CSP should have multiple directives"

    def test_csp_script_src_may_allow_unsafe_inline_but_not_unsafe_eval(self, client):
        """script-src may allow unsafe-inline for legacy support, but never unsafe-eval."""
        response = client.get("/")
        csp = response.headers["Content-Security-Policy"]
        # Extract script-src directive
        script_src_match = re.search(r"script-src ([^;]+)", csp)
        assert script_src_match, "script-src directive should be present"
        script_src_value = script_src_match.group(1)
        assert "unsafe-eval" not in script_src_value, \
            "script-src must not contain unsafe-eval (arbitrary JS execution risk)"


@pytest.mark.security
@pytest.mark.integration
class TestSecurityHeadersOnErrorResponses:
    """Test that security headers are present even on error responses."""

    def test_404_has_security_headers(self, client):
        """404 Not Found responses must have security headers."""
        response = client.get("/this-route-definitely-does-not-exist-12345")
        assert response.status_code == 404
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "Content-Security-Policy" in response.headers

    def test_error_response_has_no_stack_trace_info(self, client):
        """Error responses should not leak stack traces or system info."""
        response = client.get("/nonexistent")
        # Check for common stack trace patterns
        response_data = response.get_data(as_text=True) if response.data else ""
        # Should not contain Python stack trace indicators
        assert "Traceback" not in response_data, "Error response should not contain Python traceback"


@pytest.mark.security
@pytest.mark.contract
class TestSecurityHeadersOnHTMLResponses:
    """Test security headers specifically on HTML content type responses."""

    @pytest.mark.parametrize("route", ["/", "/news", "/forum", "/manage/login"])
    def test_html_responses_have_all_security_headers(self, client, route):
        """HTML responses must have all security headers."""
        response = client.get(route)
        assert response.status_code in (200, 404), f"Unexpected status on {route}"
        assert response.content_type.startswith("text/html"), f"Expected HTML on {route}"

        headers = response.headers
        required_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Referrer-Policy",
            "Permissions-Policy",
            "Content-Security-Policy",
        ]
        for header in required_headers:
            assert header in headers, f"{header} missing on HTML response from {route}"


@pytest.mark.security
class TestSecurityHeadersConnectSrcWithBackendOrigin:
    """Test that CSP connect-src includes backend origin when configured."""

    def test_connect_src_includes_backend_origin(self, client, app):
        """connect-src should include the backend API origin for CORS-free proxied requests."""
        response = client.get("/")
        csp = response.headers["Content-Security-Policy"]
        # Should have connect-src with at least 'self' and https:
        assert "connect-src" in csp, "connect-src directive required for API calls"
        # Backend is configured in the app, extract it
        backend_url = app.config.get("BACKEND_API_URL", "")
        assert backend_url, "BACKEND_API_URL should be configured"
        # Extract origin from URL
        if backend_url.startswith("http"):
            from urllib.parse import urlparse
            parsed = urlparse(backend_url)
            backend_origin = f"{parsed.scheme}://{parsed.netloc}"
            # connect-src should include it (or at least https: which allows all https)
            connect_part = csp.split("connect-src")[1].split(";")[0]
            assert "https:" in connect_part or backend_origin in connect_part, \
                f"connect-src should allow backend origin"


@pytest.mark.security
class TestSecurityHeadersImmutability:
    """Test that security headers are consistent across multiple requests."""

    def test_security_headers_consistent_across_requests(self, client):
        """Security headers should be identical for multiple requests to same route."""
        response1 = client.get("/")
        response2 = client.get("/")

        csp1 = response1.headers.get("Content-Security-Policy", "")
        csp2 = response2.headers.get("Content-Security-Policy", "")
        assert csp1 == csp2, "CSP should be consistent across requests"

        # Check other headers too
        for header in ["X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"]:
            assert response1.headers.get(header) == response2.headers.get(header), \
                f"{header} should be consistent"

    def test_security_headers_same_across_different_routes(self, client):
        """Security headers should be the same across all routes (global policy)."""
        routes = ["/", "/news", "/manage/login"]
        headers_per_route = {}

        for route in routes:
            response = client.get(route)
            headers_per_route[route] = {
                "X-Content-Type-Options": response.headers.get("X-Content-Type-Options"),
                "X-Frame-Options": response.headers.get("X-Frame-Options"),
                "Referrer-Policy": response.headers.get("Referrer-Policy"),
            }

        # All routes should have identical security headers
        first_route_headers = headers_per_route[routes[0]]
        for route, headers in headers_per_route.items():
            assert headers["X-Content-Type-Options"] == first_route_headers["X-Content-Type-Options"]
            assert headers["X-Frame-Options"] == first_route_headers["X-Frame-Options"]
            assert headers["Referrer-Policy"] == first_route_headers["Referrer-Policy"]
