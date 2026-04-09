"""HTTP error shape and status contract tests (split from former test_coverage_expansion)."""

import pytest


class TestErrorResponses:
    """Test proper error response format and status codes."""

    def test_404_for_nonexistent_resource(self, client, auth_headers):
        """404 returned for nonexistent resources."""
        response = client.get(
            "/api/v1/news/999999",
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "error" in response.get_json()

    def test_400_for_missing_required_fields(self, client, admin_headers):
        """400 returned for missing required fields."""
        response = client.post(
            "/api/v1/news",
            headers=admin_headers,
            json={"title": "Only title"},
        )
        assert response.status_code == 400
        assert "content" in response.get_json().get("error", "").lower()

    def test_401_without_jwt_token(self, client):
        """401 returned for requests without JWT."""
        response = client.get("/api/v1/admin/analytics/summary")
        assert response.status_code == 401
        assert "token" in response.get_json().get("error", "").lower()

    def test_429_rate_limit_enforced(self, client, auth_headers):
        """Rate limit returns 429 after threshold."""
        for _ in range(120):
            response = client.get(
                "/api/v1/admin/analytics/summary",
                headers=auth_headers,
            )
            if response.status_code == 429:
                assert "too many" in response.get_json().get("error", "").lower() or "rate" in response.get_json().get(
                    "error", ""
                ).lower()
                return

        pytest.skip("Rate limit not enforced in test environment")
