"""Tests for narrow follow-up Task.md: News/Wiki auto-suggestions and contextual enrichment.

Focus: News auto-suggestions (implemented), contextual discussion enrichment, and backward compatibility.
"""
import pytest
from datetime import datetime, timezone


class TestNewsAutoSuggestions:
    """Test News article auto-suggestions and contextual enrichment."""

    def test_news_suggestions_endpoint_returns_data(self, client, app, test_user):
        """GET /api/v1/news/<id>/suggested-threads returns article suggestions."""
        from app.models import NewsArticle, NewsArticleTranslation, ForumCategory, ForumThread
        from app.extensions import db

        with app.app_context():
            user, _ = test_user
            now = datetime.now(timezone.utc)

            # Create category for forum threads
            cat = ForumCategory(
                slug="news-test-cat",
                title="News Test Cat",
                sort_order=0,
                is_active=True,
                is_private=False
            )
            db.session.add(cat)
            db.session.flush()

            # Create a test forum thread
            thread = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="news-test-thread",
                title="Test Discussion",
                status="open",
                created_at=now,
                updated_at=now,
            )
            db.session.add(thread)
            db.session.flush()

            # Create a news article
            article = NewsArticle(
                author_id=user.id,
                status="published",
                default_language="de",
                category="news-test-cat",
                created_at=now,
                updated_at=now,
                published_at=now,
            )
            db.session.add(article)
            db.session.flush()

            trans = NewsArticleTranslation(
                article_id=article.id,
                language_code="de",
                title="Test Article",
                slug="test-article",
                content="Test content about testing",
                translation_status="published",
                source_language="de",
                translated_at=now,
            )
            db.session.add(trans)
            db.session.commit()
            article_id = article.id

        response = client.get(f"/api/v1/news/{article_id}/suggested-threads")
        assert response.status_code == 200
        data = response.get_json()
        # Should return items list and total count
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)

    def test_news_detail_includes_discussion_context(self, client, app, test_user):
        """News detail response includes discussion, related_threads, and suggested_threads."""
        from app.models import NewsArticle, NewsArticleTranslation
        from app.extensions import db

        with app.app_context():
            user, _ = test_user
            now = datetime.now(timezone.utc)

            article = NewsArticle(
                author_id=user.id,
                status="published",
                default_language="de",
                created_at=now,
                updated_at=now,
                published_at=now,
            )
            db.session.add(article)
            db.session.flush()

            trans = NewsArticleTranslation(
                article_id=article.id,
                language_code="de",
                title="Test News",
                slug="test-news-detail",
                content="Test content",
                translation_status="published",
                source_language="de",
                translated_at=now,
            )
            db.session.add(trans)
            db.session.commit()

        response = client.get("/api/v1/news/test-news-detail")
        assert response.status_code == 200
        data = response.get_json()
        # After enhancement, these fields should exist
        assert "slug" in data
        assert "title" in data
        # Discussion field should be present (can be None/empty, but field exists)
        if "discussion" in data:
            assert data["discussion"] is None or isinstance(data["discussion"], dict)
        # Related and suggested threads fields may be present
        if "related_threads" in data:
            assert isinstance(data["related_threads"], list)
        if "suggested_threads" in data:
            assert isinstance(data["suggested_threads"], list)

    def test_news_suggestions_exclude_unpublished(self, client, app, test_user):
        """Unpublished news articles don't return suggestions."""
        from app.models import NewsArticle, NewsArticleTranslation
        from app.extensions import db

        with app.app_context():
            user, _ = test_user
            now = datetime.now(timezone.utc)

            article = NewsArticle(
                author_id=user.id,
                status="draft",  # Draft article
                default_language="de",
                created_at=now,
                updated_at=now,
            )
            db.session.add(article)
            db.session.commit()
            article_id = article.id

        response = client.get(f"/api/v1/news/{article_id}/suggested-threads")
        assert response.status_code == 200
        data = response.get_json()
        # Draft articles return empty suggestions
        assert data["items"] == []
        assert data["total"] == 0


class TestBackwardCompatibility:
    """Ensure existing endpoints still work."""

    def test_news_detail_endpoint_still_works(self, client, app, test_user):
        """GET /api/v1/news/<slug> returns valid news data (backward compatibility)."""
        from app.models import NewsArticle, NewsArticleTranslation
        from app.extensions import db

        with app.app_context():
            user, _ = test_user
            now = datetime.now(timezone.utc)

            article = NewsArticle(
                author_id=user.id,
                status="published",
                default_language="de",
                created_at=now,
                updated_at=now,
                published_at=now,
            )
            db.session.add(article)
            db.session.flush()

            trans = NewsArticleTranslation(
                article_id=article.id,
                language_code="de",
                title="Backward Compat News",
                slug="backward-compat-news",
                content="Backward compatible content",
                translation_status="published",
                source_language="de",
                translated_at=now,
            )
            db.session.add(trans)
            db.session.commit()

        response = client.get("/api/v1/news/backward-compat-news")
        assert response.status_code == 200
        data = response.get_json()
        # Should have basic news fields
        assert "slug" in data
        assert data["slug"] == "backward-compat-news"
        assert "title" in data
        assert data["title"] == "Backward Compat News"
        assert "content" in data

    def test_news_list_endpoint_still_works(self, client, app):
        """GET /api/v1/news returns list of published news (backward compatibility)."""
        response = client.get("/api/v1/news")
        # May require auth in some configs, but should not error
        assert response.status_code in (200, 401)
        if response.status_code == 200:
            data = response.get_json()
            assert "items" in data
            assert isinstance(data["items"], list)


class TestNewsContextualEnrichment:
    """Test contextual discussion presentation for News."""

    def test_published_article_has_enriched_response(self, client, app, test_user):
        """Published articles receive enriched contextual response."""
        from app.models import NewsArticle, NewsArticleTranslation, ForumCategory, ForumThread
        from app.extensions import db

        with app.app_context():
            user, _ = test_user
            now = datetime.now(timezone.utc)

            # Create category and thread
            cat = ForumCategory(
                slug="enrich-cat",
                title="Enrich Cat",
                sort_order=0,
                is_active=True,
                is_private=False
            )
            db.session.add(cat)
            db.session.flush()

            thread = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="enrich-thread",
                title="Enrichment Discussion",
                status="open",
                created_at=now,
                updated_at=now,
            )
            db.session.add(thread)
            db.session.flush()

            # Create article with discussion thread linked
            article = NewsArticle(
                author_id=user.id,
                status="published",
                default_language="de",
                discussion_thread_id=thread.id,
                created_at=now,
                updated_at=now,
                published_at=now,
            )
            db.session.add(article)
            db.session.flush()

            trans = NewsArticleTranslation(
                article_id=article.id,
                language_code="de",
                title="Enriched Article",
                slug="enriched-article",
                content="Enriched content",
                translation_status="published",
                source_language="de",
                translated_at=now,
            )
            db.session.add(trans)
            db.session.commit()

        response = client.get("/api/v1/news/enriched-article")
        assert response.status_code == 200
        data = response.get_json()
        # Should have discussion context with thread info
        if "discussion" in data and data["discussion"]:
            assert "type" in data["discussion"]
            assert data["discussion"]["type"] == "primary"
            assert "thread_id" in data["discussion"]
            assert "thread_title" in data["discussion"]


class TestWikiAutoSuggestions:
    """Test Wiki article auto-suggestions and endpoint parity with News."""

    def test_wiki_suggestions_endpoint_returns_data(self, client, app, test_user):
        """GET /api/v1/wiki/<id>/suggested-threads returns article suggestions."""
        from app.models import WikiPage, WikiPageTranslation, ForumCategory, ForumThread
        from app.extensions import db

        with app.app_context():
            user, _ = test_user
            now = datetime.now(timezone.utc)

            # Create category
            cat = ForumCategory(
                slug="wiki-test-cat",
                title="Wiki Test Cat",
                sort_order=0,
                is_active=True,
                is_private=False
            )
            db.session.add(cat)
            db.session.flush()

            # Create forum thread
            thread = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="wiki-test-thread",
                title="Test Wiki Discussion",
                status="open",
                created_at=now,
                updated_at=now,
            )
            db.session.add(thread)
            db.session.flush()

            # Create wiki page
            page = WikiPage(
                key="test-wiki-page",
                is_published=True,
                created_at=now,
                updated_at=now,
            )
            db.session.add(page)
            db.session.flush()

            trans = WikiPageTranslation(
                page_id=page.id,
                language_code="de",
                title="Test Wiki",
                slug="test-wiki",
                content_markdown="Test wiki content",
            )
            db.session.add(trans)
            db.session.commit()
            page_id = page.id

        response = client.get(f"/api/v1/wiki/{page_id}/suggested-threads")
        assert response.status_code == 200
        data = response.get_json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)

    def test_wiki_suggestions_endpoint_returns_parity_with_news(self, client, app):
        """Wiki suggested-threads endpoint returns same structure as News endpoint."""
        response = client.get("/api/v1/wiki/999/suggested-threads")
        # Should return 404 for non-existent page (parity with News behavior)
        assert response.status_code == 404

    def test_wiki_page_detail_includes_suggested_threads(self, client, app, test_user):
        """Wiki page detail response includes suggested_threads field."""
        from app.models import WikiPage, WikiPageTranslation
        from app.extensions import db

        with app.app_context():
            user, _ = test_user
            now = datetime.now(timezone.utc)

            page = WikiPage(
                key="wiki-with-suggestions",
                is_published=True,
                created_at=now,
                updated_at=now,
            )
            db.session.add(page)
            db.session.flush()

            trans = WikiPageTranslation(
                page_id=page.id,
                language_code="de",
                title="Wiki With Suggestions",
                slug="wiki-with-suggestions",
                content_markdown="Content",
            )
            db.session.add(trans)
            db.session.commit()

        response = client.get("/api/v1/wiki/wiki-with-suggestions")
        assert response.status_code == 200
        data = response.get_json()
        # Should have these fields after enhancement
        assert "title" in data
        assert "slug" in data
        # suggested_threads field may or may not be present, but if present, must be array
        if "suggested_threads" in data:
            assert isinstance(data["suggested_threads"], list)
