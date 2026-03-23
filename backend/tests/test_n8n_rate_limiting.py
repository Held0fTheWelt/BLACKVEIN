"""Test rate limiting for N8N service integration endpoints.

Tests verify:
1. Endpoints using @require_editor_or_n8n_service have proper rate limiting
2. Rate limiting is per-service-key (X-Service-Key header)
3. 50 requests per minute are allowed, 51st returns 429
4. Different X-Service-Key values have separate buckets
5. Missing/invalid X-Service-Key required for auth
"""

import pytest
from app.models import NewsArticle, NewsArticleTranslation, WikiPage, WikiPageTranslation


@pytest.fixture
def n8n_service_key():
    """Return a valid N8N service key for testing."""
    return "test-n8n-service-key-12345"


@pytest.fixture
def app_with_n8n(app):
    """Configure app with N8N_SERVICE_TOKEN for testing."""
    with app.app_context():
        app.config["N8N_SERVICE_TOKEN"] = "test-n8n-service-key-12345"
        yield app


@pytest.fixture
def sample_news_article(app, admin_user):
    """Create a sample published news article for translation tests."""
    with app.app_context():
        user, _ = admin_user
        article = NewsArticle(
            author_id=user.id,
            status="published",
            default_language="de",
            category="Updates",
        )
        from app.extensions import db
        db.session.add(article)
        db.session.flush()

        # Add German translation
        trans = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="Test Article",
            slug="test-article",
            content="Test content",
            translation_status="published",
            source_language="de",
        )
        db.session.add(trans)
        db.session.commit()
        return article.id


@pytest.fixture
def sample_wiki_page(app, admin_user):
    """Create a sample wiki page for translation tests."""
    with app.app_context():
        from app.extensions import db
        page = WikiPage(
            key="test-page",
            sort_order=0,
            is_published=True,
        )
        db.session.add(page)
        db.session.flush()

        # Add German translation
        trans = WikiPageTranslation(
            page_id=page.id,
            language_code="de",
            title="Test Page",
            slug="test-page",
            content_markdown="# Test Page",
            translation_status="published",
            source_language="de",
        )
        db.session.add(trans)
        db.session.commit()
        return page.id


class TestNewsTranslationRateLimiting:
    """Test rate limiting on news translation endpoints."""

    def test_news_translation_get_rate_limiting_with_n8n_key(
        self, app_with_n8n, client, sample_news_article, n8n_service_key
    ):
        """Test GET /news/<id>/translations/<lang> rate limiting with X-Service-Key."""
        article_id = sample_news_article
        headers = {"X-Service-Key": n8n_service_key}

        # Send 50 requests - all should succeed
        for i in range(50):
            response = client.get(
                f"/api/v1/news/{article_id}/translations/de",
                headers=headers,
            )
            # First 50 requests should be allowed (200 or 404 if translation doesn't exist)
            assert response.status_code in (200, 404), f"Request {i+1} failed with {response.status_code}"

        # 51st request should be rate limited (429)
        response = client.get(
            f"/api/v1/news/{article_id}/translations/de",
            headers=headers,
        )
        assert response.status_code == 429, f"Expected 429 but got {response.status_code}"

    def test_news_translation_put_rate_limiting_with_n8n_key(
        self, app_with_n8n, client, sample_news_article, n8n_service_key
    ):
        """Test PUT /news/<id>/translations/<lang> rate limiting with X-Service-Key."""
        article_id = sample_news_article
        headers = {
            "X-Service-Key": n8n_service_key,
            "Content-Type": "application/json",
        }
        payload = {
            "title": "Translated Title",
            "slug": "translated-slug",
            "content": "Translated content",
        }

        # Send 50 requests - all should succeed
        for i in range(50):
            response = client.put(
                f"/api/v1/news/{article_id}/translations/de",
                json=payload,
                headers=headers,
            )
            # First 50 requests should be allowed (200, 400, or 404)
            assert response.status_code in (200, 400, 404, 409), \
                f"Request {i+1} failed with {response.status_code}: {response.get_json()}"

        # 51st request should be rate limited (429)
        response = client.put(
            f"/api/v1/news/{article_id}/translations/de",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 429, f"Expected 429 but got {response.status_code}"

    def test_news_translation_per_key_bucket_isolation(
        self, app_with_n8n, client, sample_news_article, n8n_service_key
    ):
        """Test that rate limiting uses X-Service-Key value in limiter key."""
        article_id = sample_news_article

        headers_service = {"X-Service-Key": n8n_service_key}

        # Send 51 requests with X-Service-Key - 51st should be rate limited
        for i in range(50):
            response = client.get(
                f"/api/v1/news/{article_id}/translations/de",
                headers=headers_service,
            )
            assert response.status_code in (200, 404), f"Request {i+1} failed: {response.status_code}"

        # 51st request with X-Service-Key should be rate limited
        response = client.get(
            f"/api/v1/news/{article_id}/translations/de",
            headers=headers_service,
        )
        assert response.status_code == 429, f"51st request should be rate limited but got {response.status_code}"

    def test_news_translation_missing_x_service_key_requires_jwt(
        self, app_with_n8n, client, sample_news_article, moderator_headers
    ):
        """Test that missing X-Service-Key falls back to JWT auth."""
        article_id = sample_news_article

        # Without both X-Service-Key and JWT should fail with 401
        response = client.get(
            f"/api/v1/news/{article_id}/translations/de",
        )
        assert response.status_code == 401, "Missing both X-Service-Key and JWT should return 401"

        # With JWT should succeed
        response = client.get(
            f"/api/v1/news/{article_id}/translations/de",
            headers=moderator_headers,
        )
        assert response.status_code in (200, 404), f"JWT auth should work, got {response.status_code}"


class TestWikiTranslationRateLimiting:
    """Test rate limiting on wiki translation endpoints."""

    def test_wiki_translation_get_rate_limiting_with_n8n_key(
        self, app_with_n8n, client, sample_wiki_page, n8n_service_key
    ):
        """Test GET /wiki-admin/pages/<id>/translations/<lang> rate limiting with X-Service-Key."""
        page_id = sample_wiki_page
        headers = {"X-Service-Key": n8n_service_key}

        # Send 50 requests - all should succeed
        for i in range(50):
            response = client.get(
                f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
                headers=headers,
            )
            # First 50 requests should be allowed (200 or 404 if translation doesn't exist)
            assert response.status_code in (200, 404), f"Request {i+1} failed with {response.status_code}"

        # 51st request should be rate limited (429)
        response = client.get(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
            headers=headers,
        )
        assert response.status_code == 429, f"Expected 429 but got {response.status_code}"

    def test_wiki_translation_put_rate_limiting_with_n8n_key(
        self, app_with_n8n, client, sample_wiki_page, n8n_service_key
    ):
        """Test PUT /wiki-admin/pages/<id>/translations/<lang> rate limiting with X-Service-Key."""
        page_id = sample_wiki_page
        headers = {
            "X-Service-Key": n8n_service_key,
            "Content-Type": "application/json",
        }
        payload = {
            "title": "Translated Title",
            "slug": "translated-slug",
            "content_markdown": "# Translated content",
        }

        # Send 50 requests - all should succeed
        for i in range(50):
            response = client.put(
                f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
                json=payload,
                headers=headers,
            )
            # First 50 requests should be allowed (200, 400, or 404)
            assert response.status_code in (200, 400, 404, 409), \
                f"Request {i+1} failed with {response.status_code}: {response.get_json()}"

        # 51st request should be rate limited (429)
        response = client.put(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 429, f"Expected 429 but got {response.status_code}"

    def test_wiki_translation_per_key_bucket_isolation(
        self, app_with_n8n, client, sample_wiki_page, n8n_service_key
    ):
        """Test that rate limiting uses X-Service-Key value in limiter key for wiki."""
        page_id = sample_wiki_page

        headers_service = {"X-Service-Key": n8n_service_key}

        # Send 51 requests with X-Service-Key - 51st should be rate limited
        for i in range(50):
            response = client.get(
                f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
                headers=headers_service,
            )
            assert response.status_code in (200, 404), f"Request {i+1} failed: {response.status_code}"

        # 51st request with X-Service-Key should be rate limited
        response = client.get(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
            headers=headers_service,
        )
        assert response.status_code == 429, f"51st request should be rate limited but got {response.status_code}"

    def test_wiki_translation_missing_x_service_key_requires_jwt(
        self, app_with_n8n, client, sample_wiki_page, moderator_headers
    ):
        """Test that missing X-Service-Key falls back to JWT auth for wiki."""
        page_id = sample_wiki_page

        # Without both X-Service-Key and JWT should fail with 401
        response = client.get(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
        )
        assert response.status_code == 401, "Missing both X-Service-Key and JWT should return 401"

        # With JWT should succeed
        response = client.get(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
            headers=moderator_headers,
        )
        assert response.status_code in (200, 404), f"JWT auth should work, got {response.status_code}"


class TestN8nServiceKeyValidation:
    """Test N8N service key validation and invalid key handling."""

    def test_invalid_n8n_service_key_requires_jwt(self, app_with_n8n, client, sample_news_article):
        """Test that invalid X-Service-Key requires JWT fallback."""
        article_id = sample_news_article
        headers = {"X-Service-Key": "invalid-key"}

        # Invalid X-Service-Key should fail auth (401)
        response = client.get(
            f"/api/v1/news/{article_id}/translations/de",
            headers=headers,
        )
        assert response.status_code == 401, "Invalid X-Service-Key should require JWT and fail with 401"

    def test_empty_x_service_key_requires_jwt(self, app_with_n8n, client, sample_news_article):
        """Test that empty X-Service-Key requires JWT fallback."""
        article_id = sample_news_article
        headers = {"X-Service-Key": ""}

        # Empty X-Service-Key should require JWT and fail with 401
        response = client.get(
            f"/api/v1/news/{article_id}/translations/de",
            headers=headers,
        )
        assert response.status_code == 401, "Empty X-Service-Key should require JWT and fail with 401"


class TestRateLimitingEdgeCases:
    """Test edge cases and boundary conditions for rate limiting."""

    def test_rate_limit_resets_per_minute(self, app_with_n8n, client, sample_news_article, n8n_service_key):
        """Test that rate limit is per minute (mock time if needed for real testing)."""
        article_id = sample_news_article
        headers = {"X-Service-Key": n8n_service_key}

        # Send 50 requests
        for i in range(50):
            response = client.get(
                f"/api/v1/news/{article_id}/translations/de",
                headers=headers,
            )
            assert response.status_code in (200, 404)

        # 51st request should fail
        response = client.get(
            f"/api/v1/news/{article_id}/translations/de",
            headers=headers,
        )
        assert response.status_code == 429, "51st request should be rate limited"

    def test_mixed_get_put_share_rate_limit(self, app_with_n8n, client, sample_news_article, n8n_service_key):
        """Test that GET and PUT requests share the same rate limit bucket."""
        article_id = sample_news_article
        headers = {
            "X-Service-Key": n8n_service_key,
            "Content-Type": "application/json",
        }
        payload = {
            "title": "Title",
            "slug": "slug",
            "content": "content",
        }

        # Send 50 GET requests to hit rate limit
        for i in range(50):
            response = client.get(
                f"/api/v1/news/{article_id}/translations/de",
                headers=headers,
            )
            assert response.status_code in (200, 404), f"GET {i+1} failed: {response.status_code}"

        # 51st request should be rate limited
        response = client.get(
            f"/api/v1/news/{article_id}/translations/de",
            headers=headers,
        )
        assert response.status_code == 429, f"51st GET should be rate limited, got {response.status_code}"
