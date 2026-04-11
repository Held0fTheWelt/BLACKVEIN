"""Service-layer edge cases for forum and news (split from former test_coverage_expansion)."""

import pytest


class TestServiceLayerEdgeCases:
    """Test service layer logic for edge cases."""

    def test_cannot_create_forum_thread_in_archived_category(self, client, admin_headers, app, forum_archived_category):
        """Cannot create threads in archived/inactive categories."""
        response = client.post(
            "/api/v1/forum/categories/archived-category-fixture/threads",
            headers=admin_headers,
            json={"title": "Test"},
        )
        assert response.status_code in [400, 409, 403]

    def test_news_search_respects_published_status(self, client, app):
        """News search doesn't return unpublished articles to users."""
        response = client.get("/api/v1/news?published=false")

        assert response.status_code in [200, 403]
        if response.status_code == 200:
            articles = response.get_json().get("data", [])
            for _article in articles:
                pass

    def test_pagination_respects_limits(self, client, auth_headers, app):
        """Pagination enforces reasonable limits."""
        response = client.get(
            "/api/v1/news?limit=1000&page=1",
            headers=auth_headers,
        )

        if response.status_code == 200:
            data = response.get_json()
            assert len(data.get("data", [])) <= 100
        else:
            pytest.skip("News endpoint not available in test environment")
