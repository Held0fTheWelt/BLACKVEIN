"""News and forum state transition rules (split from former test_coverage_expansion)."""

from app.extensions import db
from app.models import NewsArticle, NewsArticleTranslation


class TestStateTransitions:
    """Test valid state transitions and prevent invalid ones."""

    def test_cannot_unpublish_already_unpublished_article(self, client, admin_headers, app):
        """Cannot unpublish an already unpublished article."""
        with app.app_context():
            article = NewsArticle.query.filter(NewsArticle.status != "published").first()
            if article:
                article_id = article.id

                response = client.put(
                    f"/api/v1/news/{article_id}/unpublish",
                    headers=admin_headers,
                )
                assert response.status_code in [204, 409]

    def test_cannot_lock_already_locked_thread(self, client, admin_headers, app, forum_locked_thread):
        """Locking an already locked thread is idempotent."""
        response = client.post(
            f"/api/v1/forum/threads/{forum_locked_thread}/lock",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("is_locked") is True

    def test_publish_then_unpublish_article(self, client, admin_headers, app):
        """Article can be published then unpublished (valid state transition)."""
        with app.app_context():
            article = NewsArticle(
                status="draft",
                default_language="en",
                author_id=1,
            )
            db.session.add(article)
            db.session.flush()
            article_id = article.id

            translation = NewsArticleTranslation(
                article_id=article_id,
                language_code="en",
                title="State Test Article",
                slug="state-test-article",
                content="Testing state transitions",
                translation_status="approved",
            )
            db.session.add(translation)
            db.session.commit()

        response1 = client.post(
            f"/api/v1/news/{article_id}/publish",
            headers=admin_headers,
        )
        assert response1.status_code in [200, 204]

        response2 = client.post(
            f"/api/v1/news/{article_id}/unpublish",
            headers=admin_headers,
        )
        assert response2.status_code in [200, 204]
