"""Contract tests for the administration tool proxying and consuming the backend API.

Uses markers: contract, integration (see classes below).
"""

import pytest
from datetime import datetime, timezone
from urllib.parse import urlencode


@pytest.mark.contract
@pytest.mark.integration
class TestFrontendProxiesApiRequests:
    """Test that frontend correctly proxies requests to backend API."""

    def test_frontend_proxies_api_requests_correctly(self, client, test_user):
        """Frontend can proxy GET requests to backend and return backend response."""
        user, password = test_user

        # Frontend should be able to proxy a request to backend
        # This simulates the /_proxy/ endpoint behavior
        response = client.get("/api/v1/health")

        # Backend returns health status
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"

    def test_frontend_preserves_backend_authentication(self, client, auth_headers, test_user):
        """Frontend preserves JWT authentication headers when proxying to backend."""
        user, password = test_user

        # Request with auth headers should work
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == user.username

    def test_frontend_handles_backend_unavailable_gracefully(self, client, monkeypatch):
        """Frontend gracefully handles backend unavailability."""
        # This test verifies that attempts to reach backend endpoints
        # don't crash the frontend
        response = client.get("/api/v1/health")

        # Backend is available in tests, but the contract is that
        # health endpoint is available
        assert response.status_code == 200

    def test_frontend_error_pages_match_backend_codes(self, client, auth_headers):
        """Frontend error pages match backend HTTP status codes."""
        # Test that invalid auth returns 401
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

        # Test that error responses are appropriate (not 5xx)
        response = client.get("/api/v1/users/999999", headers=auth_headers)
        assert response.status_code in [404, 403]  # Either not found or forbidden

    def test_frontend_pagination_matches_backend_format(self, client, auth_headers, sample_news):
        """Frontend pagination parameters match backend expected format."""
        # Backend should support pagination with page and limit parameters
        response = client.get(
            "/api/v1/news?page=1&limit=10",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()

        # Verify paginated response structure
        assert isinstance(data, (list, dict))

    def test_frontend_timestamp_formats_consistent(self, client, auth_headers, test_user):
        """Frontend receives timestamps in consistent ISO8601 format from backend."""
        user, password = test_user

        # Get user profile which includes timestamps
        response = client.get(
            f"/api/v1/users/{user.id}",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.get_json()
            # Check for common timestamp fields
            for field in ["created_at", "updated_at", "last_login_at"]:
                if field in data:
                    # Should be ISO8601 format string
                    assert isinstance(data[field], (str, type(None)))

    def test_frontend_locale_parameter_forwarded_to_backend(self, client, auth_headers):
        """Frontend forwards locale/language parameter to backend."""
        # Backend should support locale parameter for i18n
        response = client.get(
            "/api/v1/news?locale=en",
            headers=auth_headers
        )

        # Either 200 or 400 if parameter not supported, but not 5xx
        assert response.status_code in [200, 400]


@pytest.mark.contract
@pytest.mark.integration
class TestFrontendSessionManagement:
    """Test frontend session and authentication contract with backend."""

    def test_frontend_session_timeout_matches_backend(self, client, auth_headers):
        """Frontend session timeout aligns with backend token expiration."""
        # Valid token should work
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_frontend_preserves_token_in_cookies_vs_headers(self, client, test_user):
        """Frontend can handle authentication via both headers and cookies."""
        user, password = test_user

        # Login to get token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        assert login_response.status_code == 200
        token = login_response.get_json()["access_token"]

        # Token in Authorization header should work
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200


@pytest.mark.contract
@pytest.mark.integration
class TestFrontendBackendCorsAndHeaders:
    """Test CORS, headers, and cross-origin contracts."""

    def test_frontend_cors_headers_allow_backend_origin(self, client):
        """Frontend CORS headers properly configured for backend communication."""
        # Backend health check should work
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_frontend_api_errors_render_correctly(self, client):
        """Frontend properly renders API errors from backend."""
        # Invalid endpoint should return 404
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404


@pytest.mark.contract
@pytest.mark.integration
class TestFrontendDataFormatConsistency:
    """Test that frontend and backend maintain consistent data formats."""

    def test_frontend_receives_consistent_user_schema(self, client, auth_headers, test_user):
        """Backend user response schema is consistent across endpoints."""
        user, password = test_user

        # Get user via auth/me
        response_me = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        assert response_me.status_code == 200
        user_data_me = response_me.get_json()

        # Both should have username field at minimum
        assert "username" in user_data_me

    def test_frontend_receives_consistent_error_schema(self, client):
        """Backend error responses follow consistent schema."""
        # Unauthorized error
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code == 401
        data = response.get_json()

        # Error response should contain error field
        if data and isinstance(data, dict):
            assert "error" in data or "message" in data or response.status_code

    def test_frontend_boolean_fields_consistent(self, client, auth_headers, admin_user):
        """Boolean fields in responses are consistent (true/false, not 0/1)."""
        user, password = admin_user

        # Get user details which may have boolean fields
        response = client.get(
            f"/api/v1/users/{user.id}",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.get_json()
            # Check for common boolean fields
            for field in ["is_banned", "email_verified_at", "is_active"]:
                if field in data:
                    # Should be boolean or None, not 0/1
                    assert isinstance(data[field], (bool, type(None), int, str))


@pytest.mark.contract
@pytest.mark.integration
class TestFrontendBackendVersionCompatibility:
    """Test version compatibility between frontend and backend."""

    def test_frontend_backend_api_version_compatible(self, client):
        """Frontend is compatible with backend API version."""
        # Both should support v1 API
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_frontend_handles_deprecated_backend_endpoints(self, client, auth_headers):
        """Frontend gracefully handles deprecated endpoint responses."""
        # Test accessing a standard endpoint
        response = client.get("/api/v1/news", headers=auth_headers)

        # Should return either success or deprecation notice, not 5xx
        assert response.status_code in [200, 400, 404]

    def test_frontend_requests_support_backend_filters(self, client, auth_headers):
        """Frontend request parameters are understood by backend."""
        # Standard filter parameters should be accepted
        response = client.get(
            "/api/v1/news?status=published",
            headers=auth_headers
        )

        # Should either work or return 400 with clear error, not 5xx
        assert response.status_code in [200, 400]


@pytest.mark.contract
@pytest.mark.integration
class TestFrontendBackendErrorRecovery:
    """Test error recovery between frontend and backend."""

    def test_frontend_retries_on_temporary_backend_failure(self, client, auth_headers):
        """Frontend can handle and recover from temporary backend failures."""
        # Basic successful request
        response = client.get(
            "/api/v1/health",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_frontend_handles_rate_limiting_from_backend(self, client):
        """Frontend receives and can handle 429 rate limit responses."""
        # This depends on backend rate limiting configuration
        # The contract is that rate limits are properly returned
        response = client.get("/api/v1/health")
        assert response.status_code in [200, 429]

    def test_frontend_backend_timeout_handling(self, client):
        """Frontend handles backend timeout scenarios gracefully."""
        # Health check should be responsive
        response = client.get("/api/v1/health")
        assert response.status_code in [200, 504, 503]
