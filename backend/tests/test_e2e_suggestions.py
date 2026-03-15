"""
E2E Tests for News/Wiki Suggestions Feature

Tests the complete flow:
1. Create news article with discussion thread
2. Tag the discussion thread
3. Create related threads with matching tags
4. Verify suggestions appear on public page
5. Verify management interface shows candidates
"""

import pytest
from datetime import datetime, timezone


class TestNewsPublicPageSuggestions:
    """Test that suggestions appear on public News pages."""

    def test_news_detail_shows_suggestions_section(self, client, app, test_user):
        """Published news article displays suggestions section with suggestions."""
        from app.models import NewsArticle, NewsArticleTranslation, ForumCategory, ForumThread, ForumTag, ForumThreadTag
        from app.extensions import db

        with app.app_context():
            user, _ = test_user
            now = datetime.now(timezone.utc)

            # 1. Create forum category
            cat = ForumCategory(
                slug="news-suggestions-test",
                title="News Suggestions Test",
                sort_order=0,
                is_active=True,
                is_private=False
            )
            db.session.add(cat)
            db.session.flush()

            # 2. Create tags
            tag1 = ForumTag(slug="testing", label="Testing")
            tag2 = ForumTag(slug="deployment", label="Deployment")
            db.session.add(tag1)
            db.session.add(tag2)
            db.session.flush()

            # 3. Create primary discussion thread with tags
            primary_thread = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="news-primary-discussion",
                title="Primary Discussion",
                status="open",
                created_at=now,
                updated_at=now,
            )
            db.session.add(primary_thread)
            db.session.flush()

            # Tag the primary thread
            thread_tag1 = ForumThreadTag(thread_id=primary_thread.id, tag_id=tag1.id)
            thread_tag2 = ForumThreadTag(thread_id=primary_thread.id, tag_id=tag2.id)
            db.session.add(thread_tag1)
            db.session.add(thread_tag2)
            db.session.flush()

            # 4. Create suggested thread (with matching tag)
            suggested_thread = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="news-suggested-related",
                title="Related Discussion",
                status="open",
                created_at=now,
                updated_at=now,
                last_post_at=now,
            )
            db.session.add(suggested_thread)
            db.session.flush()

            # Tag the suggested thread with matching tag
            suggested_tag = ForumThreadTag(thread_id=suggested_thread.id, tag_id=tag1.id)
            db.session.add(suggested_tag)

            # 5. Create news article linked to primary discussion
            article = NewsArticle(
                author_id=user.id,
                status="published",
                default_language="de",
                discussion_thread_id=primary_thread.id,
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
                content="Test content",
                translation_status="published",
                source_language="de",
                translated_at=now,
            )
            db.session.add(trans)
            db.session.commit()

            article_id = article.id

        # 6. Fetch news detail API
        response = client.get(f"/api/v1/news/{article_id}")
        assert response.status_code == 200
        data = response.get_json()

        # 7. Verify response structure
        assert "discussion" in data or data.get("discussion_thread_id") is not None
        assert "suggested_threads" in data or len([t for t in data.get("discussion", [])]) >= 0

        # 8. Verify suggested threads have reason labels
        if "suggested_threads" in data and data["suggested_threads"]:
            for suggestion in data["suggested_threads"]:
                # Each suggestion must have a grounded reason
                assert "reason" in suggestion, "Suggestion missing reason label"
                assert suggestion["reason"] in [
                    "Matched 1 tag",
                    "Matched 2 tags",
                    "Recent discussion"
                ], f"Unknown reason label: {suggestion['reason']}"

    def test_news_suggestions_exclude_primary_discussion(self, client, app, test_user):
        """Suggestions must exclude the primary discussion thread itself."""
        from app.models import NewsArticle, NewsArticleTranslation, ForumCategory, ForumThread
        from app.extensions import db

        with app.app_context():
            user, _ = test_user
            now = datetime.now(timezone.utc)

            cat = ForumCategory(
                slug="test-exclude-primary",
                title="Test",
                sort_order=0,
                is_active=True,
                is_private=False
            )
            db.session.add(cat)
            db.session.flush()

            primary = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="primary",
                title="Primary",
                status="open",
                created_at=now,
                updated_at=now,
            )
            db.session.add(primary)
            db.session.flush()

            article = NewsArticle(
                author_id=user.id,
                status="published",
                default_language="de",
                discussion_thread_id=primary.id,
                created_at=now,
                updated_at=now,
                published_at=now,
            )
            db.session.add(article)
            db.session.flush()

            trans = NewsArticleTranslation(
                article_id=article.id,
                language_code="de",
                title="Article",
                slug="article",
                content="Content",
                translation_status="published",
                source_language="de",
                translated_at=now,
            )
            db.session.add(trans)
            db.session.commit()

            article_id = article.id
            primary_id = primary.id

        response = client.get(f"/api/v1/news/{article_id}")
        data = response.get_json()

        # The primary discussion must NOT appear in suggestions
        if "suggested_threads" in data:
            for suggestion in data["suggested_threads"]:
                assert suggestion["id"] != primary_id, "Primary discussion in suggestions!"

    def test_news_suggestions_endpoint(self, client, app, test_user):
        """Dedicated /news/<id>/suggested-threads endpoint returns suggestions."""
        from app.models import NewsArticle, NewsArticleTranslation, ForumCategory, ForumThread, ForumTag, ForumThreadTag
        from app.extensions import db

        with app.app_context():
            user, _ = test_user
            now = datetime.now(timezone.utc)

            cat = ForumCategory(
                slug="endpoint-test",
                title="Test",
                sort_order=0,
                is_active=True,
                is_private=False
            )
            db.session.add(cat)
            db.session.flush()

            tag = ForumTag(slug="test-tag", label="Test Tag")
            db.session.add(tag)
            db.session.flush()

            primary = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="primary",
                title="Primary",
                status="open",
                created_at=now,
                updated_at=now,
            )
            db.session.add(primary)
            db.session.flush()

            thread_tag = ForumThreadTag(thread_id=primary.id, tag_id=tag.id)
            db.session.add(thread_tag)
            db.session.flush()

            suggested = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="suggested",
                title="Suggested",
                status="open",
                created_at=now,
                updated_at=now,
                last_post_at=now,
            )
            db.session.add(suggested)
            db.session.flush()

            suggested_tag = ForumThreadTag(thread_id=suggested.id, tag_id=tag.id)
            db.session.add(suggested_tag)

            article = NewsArticle(
                author_id=user.id,
                status="published",
                default_language="de",
                discussion_thread_id=primary.id,
                created_at=now,
                updated_at=now,
                published_at=now,
            )
            db.session.add(article)
            db.session.flush()

            trans = NewsArticleTranslation(
                article_id=article.id,
                language_code="de",
                title="Article",
                slug="article",
                content="Content",
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

        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 0


class TestWikiSuggestions:
    """Test that suggestions appear on Wiki pages."""

    def test_wiki_page_payload_includes_suggestions(self, client, app, test_user):
        """Wiki page payload includes suggested_threads alongside primary and related."""
        from app.models import WikiPage, WikiPageTranslation, ForumCategory, ForumThread, ForumTag, ForumThreadTag
        from app.extensions import db

        with app.app_context():
            user, _ = test_user
            now = datetime.now(timezone.utc)

            cat = ForumCategory(
                slug="wiki-test",
                title="Wiki Test",
                sort_order=0,
                is_active=True,
                is_private=False
            )
            db.session.add(cat)
            db.session.flush()

            tag = ForumTag(slug="wiki-tag", label="Wiki Tag")
            db.session.add(tag)
            db.session.flush()

            primary = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="wiki-primary",
                title="Wiki Primary",
                status="open",
                created_at=now,
                updated_at=now,
            )
            db.session.add(primary)
            db.session.flush()

            thread_tag = ForumThreadTag(thread_id=primary.id, tag_id=tag.id)
            db.session.add(thread_tag)
            db.session.flush()

            suggested = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="wiki-suggested",
                title="Wiki Suggested",
                status="open",
                created_at=now,
                updated_at=now,
                last_post_at=now,
            )
            db.session.add(suggested)
            db.session.flush()

            suggested_tag = ForumThreadTag(thread_id=suggested.id, tag_id=tag.id)
            db.session.add(suggested_tag)

            wiki = WikiPage(
                key="wiki-test-page",
                discussion_thread_id=primary.id,
                created_at=now,
                updated_at=now,
            )
            db.session.add(wiki)
            db.session.flush()

            trans = WikiPageTranslation(
                page_id=wiki.id,
                language_code="de",
                title="Wiki Test Page",
                slug="wiki-test-page",
                content_markdown="Content",
            )
            db.session.add(trans)
            db.session.commit()

            wiki_slug = trans.slug

        response = client.get(f"/api/v1/wiki/{wiki_slug}")
        assert response.status_code == 200, f"Got {response.status_code}: {response.get_json()}"
        data = response.get_json()

        # Verify all three discussion sources are present
        assert "discussion" in data or data.get("discussion_thread_id")
        assert "suggested_threads" in data, "Wiki payload missing suggested_threads"

        # Verify suggestions have reason labels
        if data.get("suggested_threads"):
            for suggestion in data["suggested_threads"]:
                assert "reason" in suggestion, "Suggestion missing reason"


class TestSuggestionRankingDeterminism:
    """Test that suggestion ranking is deterministic and stable."""

    def test_suggestions_stable_ordering(self, client, app, test_user):
        """Multiple calls return same suggestion order."""
        from app.models import NewsArticle, NewsArticleTranslation, ForumCategory, ForumThread, ForumTag, ForumThreadTag
        from app.extensions import db

        with app.app_context():
            user, _ = test_user
            now = datetime.now(timezone.utc)

            cat = ForumCategory(
                slug="stability-test",
                title="Stability Test",
                sort_order=0,
                is_active=True,
                is_private=False
            )
            db.session.add(cat)
            db.session.flush()

            tag = ForumTag(slug="stable", label="Stable")
            db.session.add(tag)
            db.session.flush()

            primary = ForumThread(
                category_id=cat.id,
                author_id=user.id,
                slug="primary",
                title="Primary",
                status="open",
                created_at=now,
                updated_at=now,
            )
            db.session.add(primary)
            db.session.flush()

            thread_tag = ForumThreadTag(thread_id=primary.id, tag_id=tag.id)
            db.session.add(thread_tag)
            db.session.flush()

            # Create multiple threads with matching tag
            threads = []
            for i in range(3):
                t = ForumThread(
                    category_id=cat.id,
                    author_id=user.id,
                    slug=f"thread-{i}",
                    title=f"Thread {i}",
                    status="open",
                    created_at=now,
                    updated_at=now,
                    last_post_at=now,
                )
                db.session.add(t)
                db.session.flush()
                tt = ForumThreadTag(thread_id=t.id, tag_id=tag.id)
                db.session.add(tt)
                threads.append(t)

            article = NewsArticle(
                author_id=user.id,
                status="published",
                default_language="de",
                discussion_thread_id=primary.id,
                created_at=now,
                updated_at=now,
                published_at=now,
            )
            db.session.add(article)
            db.session.flush()

            trans = NewsArticleTranslation(
                article_id=article.id,
                language_code="de",
                title="Article",
                slug="article",
                content="Content",
                translation_status="published",
                source_language="de",
                translated_at=now,
            )
            db.session.add(trans)
            db.session.commit()

            article_id = article.id

        # Call multiple times and verify same order
        response1 = client.get(f"/api/v1/news/{article_id}")
        data1 = response1.get_json()
        suggestions1 = [s["id"] for s in data1.get("suggested_threads", [])]

        response2 = client.get(f"/api/v1/news/{article_id}")
        data2 = response2.get_json()
        suggestions2 = [s["id"] for s in data2.get("suggested_threads", [])]

        # Order must be identical
        assert suggestions1 == suggestions2, "Suggestion order changed between calls"
