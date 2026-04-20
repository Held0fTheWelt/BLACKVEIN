"""Test language_code validation on translation endpoints.

Validates that:
1. Only whitelisted languages are accepted (en, fr, de, es, it, pt, ru, zh, ja, ko)
2. Invalid language codes return 400 Bad Request
3. Injection attempts via language_code field are prevented
4. Valid languages pass through successfully
"""
import pytest
from app.extensions import db
from app.models import NewsArticle, WikiPage, WikiPageTranslation, NewsArticleTranslation


class TestSiteTranslationEndpoints:
    """Integration tests for site endpoints with language validation."""

    def test_site_slogans_valid_language(self, client):
        """GET site slogans with valid language should succeed."""
        response = client.get("/api/v1/site/slogans?placement=test&lang=en")
        assert response.status_code == 200

    def test_site_slogans_invalid_language(self, client):
        """GET site slogans with invalid language should return 400."""
        response = client.get("/api/v1/site/slogans?placement=test&lang=invalid")
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_site_slogan_valid_language(self, client):
        """GET site slogan with valid language should succeed."""
        response = client.get("/api/v1/site/slogan?placement=test&lang=de")
        assert response.status_code == 200

    def test_site_slogan_invalid_language(self, client):
        """GET site slogan with invalid language should return 400."""
        response = client.get("/api/v1/site/slogan?placement=test&lang=bad")
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_site_slogan_injection_attempt(self, client):
        """GET site slogan with injection should return 400."""
        payloads = [
            "en' OR '1'='1",
            "../../etc/passwd",
        ]

        for payload in payloads:
            response = client.get(f"/api/v1/site/slogan?placement=test&lang={payload}")
            assert response.status_code == 400, f"Payload '{payload}' should return 400"

    def test_site_slogan_all_supported_languages(self, client):
        """All whitelisted languages should be accepted."""
        supported = ["en", "fr", "de", "es", "it", "pt", "ru", "zh", "ja", "ko"]
        for lang in supported:
            response = client.get(f"/api/v1/site/slogan?placement=test&lang={lang}")
            assert response.status_code == 200, f"Language {lang} should be supported"


class TestWikiTranslationEndpoints:
    """Integration tests for wiki translation endpoints with language validation."""

    def test_wiki_translation_get_valid_language(self, client, app, admin_headers):
        """GET wiki translation with valid language should succeed."""
        with app.app_context():
            page = WikiPage(key="test-page")
            db.session.add(page)
            db.session.flush()

            trans = WikiPageTranslation(
                page_id=page.id,
                language_code="en",
                title="Test",
                slug="test",
                content_markdown="# Test"
            )
            db.session.add(trans)
            db.session.commit()
            page_id = page.id

        response = client.get(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/en",
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_wiki_translation_get_invalid_language(self, client, app, admin_headers):
        """GET wiki translation with invalid language should return 400."""
        with app.app_context():
            page = WikiPage(key="test-page")
            db.session.add(page)
            db.session.commit()
            page_id = page.id

        response = client.get(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/xx",
            headers=admin_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_wiki_translation_get_injection_attempt(self, client, app, admin_headers):
        """GET wiki translation with injection should return 400."""
        with app.app_context():
            page = WikiPage(key="test-page")
            db.session.add(page)
            db.session.commit()
            page_id = page.id

        # SQL injection payloads that make it to the handler
        sql_payloads = [
            "en' OR '1'='1",
            "en\"; DROP TABLE",
        ]

        for payload in sql_payloads:
            response = client.get(
                f"/api/v1/wiki-admin/pages/{page_id}/translations/{payload}",
                headers=admin_headers
            )
            assert response.status_code == 400, f"Payload '{payload}' should return 400"

        # Path traversal payloads that don't match the route (Flask rejects at routing level)
        path_payload = "../../etc/passwd"
        response = client.get(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/{path_payload}",
            headers=admin_headers
        )
        assert response.status_code == 404, f"Path traversal '{path_payload}' should return 404 (rejected at routing level)"

    def test_wiki_translation_put_valid_language(self, client, app, admin_headers):
        """PUT wiki translation with valid language should succeed."""
        with app.app_context():
            page = WikiPage(key="test-page")
            db.session.add(page)
            db.session.commit()
            page_id = page.id

        response = client.put(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/en",
            json={
                "title": "Test",
                "slug": "test",
                "content_markdown": "# Test"
            },
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_wiki_translation_put_invalid_language(self, client, app, admin_headers):
        """PUT wiki translation with invalid language should return 400."""
        with app.app_context():
            page = WikiPage(key="test-page")
            db.session.add(page)
            db.session.commit()
            page_id = page.id

        response = client.put(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/invalid",
            json={
                "title": "Test",
                "slug": "test",
                "content_markdown": "# Test"
            },
            headers=admin_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_wiki_translation_post_submit_review_invalid_lang(self, client, app, admin_headers):
        """POST wiki translation submit-review with invalid language should return 400."""
        with app.app_context():
            page = WikiPage(key="test-page")
            db.session.add(page)
            db.session.commit()
            page_id = page.id

        response = client.post(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/bad/submit-review",
            headers=admin_headers
        )
        assert response.status_code == 400

    def test_wiki_translation_post_approve_invalid_lang(self, client, app, admin_headers):
        """POST wiki translation approve with invalid language should return 400."""
        with app.app_context():
            page = WikiPage(key="test-page")
            db.session.add(page)
            db.session.commit()
            page_id = page.id

        response = client.post(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/zz/approve",
            headers=admin_headers
        )
        assert response.status_code == 400

    def test_wiki_translation_post_publish_invalid_lang(self, client, app, admin_headers):
        """POST wiki translation publish with invalid language should return 400."""
        with app.app_context():
            page = WikiPage(key="test-page")
            db.session.add(page)
            db.session.commit()
            page_id = page.id

        response = client.post(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/xyz/publish",
            headers=admin_headers
        )
        assert response.status_code == 400


class TestNewsTranslationEndpoints:
    """Integration tests for news translation endpoints with language validation."""

    def test_news_translation_get_valid_language(self, client, app, admin_headers):
        """GET news translation with valid language should succeed."""
        with app.app_context():
            article = NewsArticle(
                default_language="en",
                status="published",
                author_id=1
            )
            db.session.add(article)
            db.session.flush()

            trans = NewsArticleTranslation(
                article_id=article.id,
                language_code="en",
                title="Test",
                slug="test",
                content="# Test"
            )
            db.session.add(trans)
            db.session.commit()
            article_id = article.id

        response = client.get(
            f"/api/v1/news/{article_id}/translations/en",
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_news_translation_get_invalid_language(self, client, app, admin_headers):
        """GET news translation with invalid language should return 400."""
        with app.app_context():
            article = NewsArticle(
                default_language="en",
                status="published",
                author_id=1
            )
            db.session.add(article)
            db.session.commit()
            article_id = article.id

        response = client.get(
            f"/api/v1/news/{article_id}/translations/xxxx",
            headers=admin_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_news_translation_put_valid_language(self, client, app, admin_headers):
        """PUT news translation with valid language should succeed."""
        with app.app_context():
            article = NewsArticle(
                default_language="en",
                status="published",
                author_id=1
            )
            db.session.add(article)
            db.session.commit()
            article_id = article.id

        response = client.put(
            f"/api/v1/news/{article_id}/translations/fr",
            json={
                "title": "Test",
                "slug": "test-fr",
                "content": "# Test"
            },
            headers=admin_headers
        )
        assert response.status_code == 200

    def test_news_translation_put_invalid_language(self, client, app, admin_headers):
        """PUT news translation with invalid language should return 400."""
        with app.app_context():
            article = NewsArticle(
                default_language="en",
                status="published",
                author_id=1
            )
            db.session.add(article)
            db.session.commit()
            article_id = article.id

        response = client.put(
            f"/api/v1/news/{article_id}/translations/zz",
            json={
                "title": "Test",
                "slug": "test-zz",
                "content": "# Test"
            },
            headers=admin_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_news_translation_post_submit_review_invalid_lang(self, client, app, admin_headers):
        """POST news translation submit-review with invalid language should return 400."""
        with app.app_context():
            article = NewsArticle(
                default_language="en",
                status="published",
                author_id=1
            )
            db.session.add(article)
            db.session.commit()
            article_id = article.id

        response = client.post(
            f"/api/v1/news/{article_id}/translations/bad/submit-review",
            headers=admin_headers
        )
        assert response.status_code == 400

    def test_news_translation_post_approve_invalid_lang(self, client, app, admin_headers):
        """POST news translation approve with invalid language should return 400."""
        with app.app_context():
            article = NewsArticle(
                default_language="en",
                status="published",
                author_id=1
            )
            db.session.add(article)
            db.session.commit()
            article_id = article.id

        response = client.post(
            f"/api/v1/news/{article_id}/translations/zz/approve",
            headers=admin_headers
        )
        assert response.status_code == 400

    def test_news_translation_post_publish_invalid_lang(self, client, app, admin_headers):
        """POST news translation publish with invalid language should return 400."""
        with app.app_context():
            article = NewsArticle(
                default_language="en",
                status="published",
                author_id=1
            )
            db.session.add(article)
            db.session.commit()
            article_id = article.id

        response = client.post(
            f"/api/v1/news/{article_id}/translations/xyz/publish",
            headers=admin_headers
        )
        assert response.status_code == 400
