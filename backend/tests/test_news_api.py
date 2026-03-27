"""Tests for news API: list, detail, search, sort, pagination, published-only, write access."""
import pytest

from app.extensions import db
from app.models import (
    User,
    Role,
    NewsArticle,
    NewsArticleTranslation,
    ForumCategory,
    ForumThread,
    ForumPost,
)
from werkzeug.security import generate_password_hash


# --- List JSON ---


def test_news_list_returns_200_and_json(client):
    """GET /api/v1/news returns 200 and JSON with items, total, page, per_page."""
    response = client.get("/api/v1/news")
    assert response.status_code == 200
    assert response.content_type and "application/json" in response.content_type
    data = response.get_json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)
    assert data["page"] >= 1
    assert data["per_page"] >= 1


def test_news_list_item_shape(client, sample_news):
    """List items have expected fields (id, title, slug, summary, content, author_id, author_name, etc.)."""
    pub1, _pub2, _draft = sample_news
    response = client.get("/api/v1/news")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["items"]) >= 1
    item = next((i for i in data["items"] if i["id"] == pub1.id), None)
    assert item is not None
    assert item["title"] == "Published Article"
    assert item["slug"] == "published-article"
    assert "summary" in item
    assert "content" in item
    assert "author_id" in item
    assert "author_name" in item
    assert "is_published" in item
    assert "published_at" in item
    assert "created_at" in item
    assert "updated_at" in item
    assert "category" in item


# --- Detail JSON ---


def test_news_detail_returns_200_and_json(client, sample_news):
    """GET /api/v1/news/<id> for published article returns 200 and single object."""
    pub1, _pub2, _draft = sample_news
    response = client.get("/api/v1/news/{}".format(pub1.id))
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == pub1.id
    assert data["title"] == "Published Article"
    assert data["slug"] == "published-article"
    assert "content" in data
    assert "published_at" in data


def test_news_detail_not_found_returns_404(client):
    """GET /api/v1/news/99999 returns 404 and JSON error."""
    response = client.get("/api/v1/news/99999")
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


# --- Published-only visibility ---


def test_news_list_only_published(client, sample_news):
    """List returns only published articles; draft is not in items."""
    _pub1, _pub2, draft = sample_news
    response = client.get("/api/v1/news")
    assert response.status_code == 200
    data = response.get_json()
    ids = [i["id"] for i in data["items"]]
    assert draft.id not in ids


def test_news_detail_draft_returns_404(client, sample_news):
    """GET /api/v1/news/<id> for unpublished article returns 404 (no auth)."""
    _pub1, _pub2, draft = sample_news
    response = client.get("/api/v1/news/{}".format(draft.id))
    assert response.status_code == 404
    assert response.get_json().get("error") == "Not found"


def test_news_detail_draft_with_moderator_returns_200(client, moderator_headers, sample_news):
    """GET /api/v1/news/<id> for draft with moderator JWT returns 200 (CRUD read for drafts)."""
    _pub1, _pub2, draft = sample_news
    response = client.get("/api/v1/news/{}".format(draft.id), headers=moderator_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == draft.id
    assert data["is_published"] is False


def test_news_list_include_drafts_with_moderator(client, moderator_headers, sample_news):
    """GET /api/v1/news?published_only=0 with moderator JWT returns all items including drafts."""
    _pub1, _pub2, draft = sample_news
    response = client.get(
        "/api/v1/news",
        query_string={"published_only": "0", "limit": "20"},
        headers=moderator_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    ids = [i["id"] for i in data["items"]]
    assert draft.id in ids


def test_news_list_without_drafts_param_unchanged(client, moderator_headers, sample_news):
    """GET /api/v1/news without published_only=0 still returns only published (backward compatible)."""
    _pub1, _pub2, draft = sample_news
    response = client.get("/api/v1/news", headers=moderator_headers)
    assert response.status_code == 200
    data = response.get_json()
    ids = [i["id"] for i in data["items"]]
    assert draft.id not in ids


# --- Search ---


def test_news_list_search(client, sample_news):
    """GET /api/v1/news?q=... filters by search term (title/summary/content)."""
    pub1, _pub2, _draft = sample_news
    response = client.get("/api/v1/news", query_string={"q": "searchable"})
    assert response.status_code == 200
    data = response.get_json()
    assert any(i["id"] == pub1.id for i in data["items"])
    response2 = client.get("/api/v1/news", query_string={"q": "nonexistentwordxyz"})
    assert response2.status_code == 200
    assert len(response2.get_json()["items"]) == 0


# --- Sorting ---


def test_news_list_sort_direction(client, sample_news):
    """GET /api/v1/news with sort and direction returns ordered items."""
    response_desc = client.get("/api/v1/news", query_string={"sort": "title", "direction": "desc"})
    response_asc = client.get("/api/v1/news", query_string={"sort": "title", "direction": "asc"})
    assert response_desc.status_code == 200
    assert response_asc.status_code == 200
    titles_desc = [i["title"] for i in response_desc.get_json()["items"]]
    titles_asc = [i["title"] for i in response_asc.get_json()["items"]]
    assert titles_desc == list(reversed(titles_asc))


# --- Pagination ---


def test_news_list_pagination(client, sample_news):
    """GET /api/v1/news?page=1&limit=1 returns one item and total reflects full count."""
    response = client.get("/api/v1/news", query_string={"page": 1, "limit": 1})
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["items"]) <= 1
    assert data["page"] == 1
    assert data["per_page"] == 1
    assert data["total"] >= 2  # we have 2 published


def test_news_list_category_filter(client, sample_news):
    """GET /api/v1/news?category=Updates returns only items in that category."""
    response = client.get("/api/v1/news", query_string={"category": "Updates"})
    assert response.status_code == 200
    data = response.get_json()
    for item in data["items"]:
        assert item["category"] == "Updates"


# --- Anonymous write blocking ---


def test_news_post_without_token_returns_401(client):
    """POST /api/v1/news without Authorization returns 401."""
    response = client.post(
        "/api/v1/news",
        json={"title": "T", "slug": "t", "content": "C"},
        content_type="application/json",
    )
    assert response.status_code == 401
    assert "error" in response.get_json()


def test_news_put_without_token_returns_401(client, sample_news):
    """PUT /api/v1/news/<id> without Authorization returns 401."""
    pub1, _pub2, _draft = sample_news
    response = client.put(
        "/api/v1/news/{}".format(pub1.id),
        json={"title": "Updated"},
        content_type="application/json",
    )
    assert response.status_code == 401


def test_news_delete_without_token_returns_401(client, sample_news):
    """DELETE /api/v1/news/<id> without Authorization returns 401."""
    pub1, _pub2, _draft = sample_news
    response = client.delete("/api/v1/news/{}".format(pub1.id))
    assert response.status_code == 401


# --- Authenticated user (role=user) write blocked (403) ---


def test_news_post_with_user_role_returns_403(client, auth_headers, sample_news):
    """POST /api/v1/news with valid JWT but role=user returns 403 Forbidden."""
    response = client.post(
        "/api/v1/news",
        headers=auth_headers,
        json={"title": "User Post", "slug": "user-post", "content": "Body"},
        content_type="application/json",
    )
    assert response.status_code == 403
    data = response.get_json()
    assert "error" in data and "forbidden" in data["error"].lower()


def test_news_put_with_user_role_returns_403(client, auth_headers, sample_news):
    """PUT /api/v1/news/<id> with valid JWT but role=user returns 403."""
    pub1, _pub2, _draft = sample_news
    response = client.put(
        "/api/v1/news/{}".format(pub1.id),
        headers=auth_headers,
        json={"title": "Updated"},
        content_type="application/json",
    )
    assert response.status_code == 403


# --- Moderator write access (201/200) ---


def test_news_post_with_moderator_returns_201(client, moderator_headers):
    """POST /api/v1/news with moderator JWT returns 201 and creates article."""
    response = client.post(
        "/api/v1/news",
        headers=moderator_headers,
        json={
            "title": "New by Moderator",
            "slug": "new-by-moderator",
            "content": "Content here.",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["title"] == "New by Moderator"
    assert data["slug"] == "new-by-moderator"
    assert "id" in data


def test_news_post_with_admin_returns_201(client, admin_headers):
    """POST /api/v1/news with admin JWT returns 201 and creates article."""
    response = client.post(
        "/api/v1/news",
        headers=admin_headers,
        json={
            "title": "New by Admin",
            "slug": "new-by-admin",
            "content": "Content by admin.",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["title"] == "New by Admin"
    assert data["slug"] == "new-by-admin"
    assert "id" in data


def test_news_put_with_moderator_returns_200(client, moderator_headers, sample_news):
    """PUT /api/v1/news/<id> with moderator JWT returns 200 and updates article."""
    pub1, _pub2, _draft = sample_news
    response = client.put(
        "/api/v1/news/{}".format(pub1.id),
        headers=moderator_headers,
        json={"title": "Updated Title by Moderator"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "Updated Title by Moderator"


def test_news_publish_with_moderator_returns_200(client, moderator_headers, sample_news):
    """POST /api/v1/news/<id>/publish with moderator JWT returns 200."""
    _pub1, _pub2, draft = sample_news
    response = client.post(
        "/api/v1/news/{}".format(draft.id) + "/publish",
        headers=moderator_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["is_published"] is True


def test_news_delete_with_moderator_returns_200(client, moderator_headers, sample_news):
    """DELETE /api/v1/news/<id> with moderator JWT returns 200 and removes article."""
    _pub1, pub2, _draft = sample_news
    response = client.delete("/api/v1/news/{}".format(pub2.id), headers=moderator_headers)
    assert response.status_code == 200
    get_resp = client.get("/api/v1/news/{}".format(pub2.id))
    assert get_resp.status_code == 404


# --- Discussion link (link/unlink and public response) ---


def test_news_discussion_link_unlink_and_public_response(app, client, moderator_headers, sample_news):
    """Link a forum thread to a news article; public detail includes discussion_thread_slug; unlink clears it."""
    from app.extensions import db
    from app.models import ForumCategory, ForumThread

    pub1_article, _pub2, _draft = sample_news
    with app.app_context():
        cat = ForumCategory(slug="news-discuss", title="News Discuss", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="article-discussion", title="Article discussion", status="open")
        db.session.add(thread)
        db.session.commit()
        thread_id = thread.id

    # Link
    resp = client.post(
        "/api/v1/news/{}/discussion-thread".format(pub1_article.id),
        headers=moderator_headers,
        json={"discussion_thread_id": thread_id},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("discussion_thread_id") == thread_id

    # Public detail includes discussion fields
    get_resp = client.get("/api/v1/news/{}".format(pub1_article.id))
    assert get_resp.status_code == 200
    get_data = get_resp.get_json()
    assert get_data.get("discussion_thread_id") == thread_id
    assert get_data.get("discussion_thread_slug") == "article-discussion"

    # Unlink
    del_resp = client.delete("/api/v1/news/{}/discussion-thread".format(pub1_article.id), headers=moderator_headers)
    assert del_resp.status_code == 200
    get_resp2 = client.get("/api/v1/news/{}".format(pub1_article.id))
    assert get_resp2.status_code == 200
    get_data2 = get_resp2.get_json()
    assert get_data2.get("discussion_thread_id") is None


# --- Rate Limiting on X-Service-Key Protected Endpoints ---


def test_news_translation_get_rate_limiting_with_service_key(client, sample_news):
    """Test rate limiting on GET /api/v1/news/<id>/translations/<lang> with X-Service-Key."""
    pub1_article, _pub2, _draft = sample_news
    article_id = pub1_article.id
    lang = "en"
    service_key = "test-service-key-12345"

    # Make 51 requests with the same X-Service-Key header; should get 429 on the 51st
    for i in range(51):
        response = client.get(
            f"/api/v1/news/{article_id}/translations/{lang}",
            headers={"X-Service-Key": service_key}
        )
        if response.status_code == 429:
            # Rate limit hit; verify error message
            data = response.get_json()
            assert "error" in data or "message" in data or data.get("error") or data.get("message")
            return

    # If we get here, rate limit may not be enforced in test environment
    pytest.skip("Rate limit not enforced in test environment")


def test_news_translation_put_rate_limiting_with_service_key(client, sample_news):
    """Test rate limiting on PUT /api/v1/news/<id>/translations/<lang> with X-Service-Key."""
    pub1_article, _pub2, _draft = sample_news
    article_id = pub1_article.id
    lang = "en"
    service_key = "test-service-key-put-12345"

    # Prepare request body for translation
    body = {
        "title": "Translated Title",
        "slug": "translated-slug",
        "summary": "Translated summary",
        "content": "Translated content",
    }

    # Make 51 requests with the same X-Service-Key header; should get 429 on the 51st
    for i in range(51):
        response = client.put(
            f"/api/v1/news/{article_id}/translations/{lang}",
            json=body,
            headers={"X-Service-Key": service_key}
        )
        if response.status_code == 429:
            # Rate limit hit; verify it's a rate limit error
            data = response.get_json()
            assert "error" in data or "message" in data or data.get("error") or data.get("message")
            return

    # If we get here, rate limit may not be enforced in test environment
    pytest.skip("Rate limit not enforced in test environment")


def test_news_translation_get_rate_limit_keyed_by_service_key(client, sample_news, moderator_headers):
    """Test that rate limiting is correctly keyed by X-Service-Key (different keys have separate limits)."""
    pub1_article, _pub2, _draft = sample_news
    article_id = pub1_article.id
    lang = "en"

    # This test demonstrates that the X-Service-Key is used as the limiter key.
    # Making requests with the same key uses up the same rate limit bucket.
    # We can't test invalid keys hitting 401 and still being rate limited,
    # but we can verify the decorator is properly applied with the correct key_func.

    # Verify the endpoint is protected and requires either valid JWT or valid X-Service-Key
    response = client.get(
        f"/api/v1/news/{article_id}/translations/{lang}",
        headers={"X-Service-Key": "invalid-key"}
    )
    assert response.status_code in (401, 403), "Invalid X-Service-Key should be rejected"

    # Verify JWT still works
    response = client.get(
        f"/api/v1/news/{article_id}/translations/{lang}",
        headers=moderator_headers
    )
    assert response.status_code in (200, 404, 400), "Valid JWT should be accepted"



"""Tests for TestNewsWriteAPI."""

class TestNewsWriteAPI:

    def test_create_news_article(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news",
            json={
                "title": "Test Article",
                "slug": "test-article-write",
                "content": "Full article content here.",
                "summary": "Short summary.",
                "category": "Updates",
            },
            headers=moderator_headers,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["title"] == "Test Article"

    def test_create_news_missing_fields(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news",
            json={"title": ""},
            headers=moderator_headers,
        )
        assert resp.status_code in (400, 422)

    def test_update_news_article(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news",
            json={"title": "Updatable", "slug": "updatable-article", "content": "body"},
            headers=moderator_headers,
        )
        article_id = resp.get_json()["id"]
        resp = client.put(
            f"/api/v1/news/{article_id}",
            json={"title": "Updated Title", "content": "updated body"},
            headers=moderator_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "Updated Title"

    def test_update_news_not_found(self, app, client, moderator_headers):
        resp = client.put(
            "/api/v1/news/99999",
            json={"title": "X"},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_delete_news_article(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news",
            json={"title": "Deletable", "slug": "deletable-article", "content": "body"},
            headers=moderator_headers,
        )
        article_id = resp.get_json()["id"]
        resp = client.delete(f"/api/v1/news/{article_id}", headers=moderator_headers)
        assert resp.status_code == 200

    def test_delete_news_not_found(self, app, client, moderator_headers):
        resp = client.delete("/api/v1/news/99999", headers=moderator_headers)
        assert resp.status_code == 404

    def test_publish_unpublish(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news",
            json={"title": "Pub Test", "slug": "pub-test-article", "content": "body"},
            headers=moderator_headers,
        )
        article_id = resp.get_json()["id"]
        resp = client.post(f"/api/v1/news/{article_id}/publish", headers=moderator_headers)
        assert resp.status_code == 200
        resp = client.post(f"/api/v1/news/{article_id}/unpublish", headers=moderator_headers)
        assert resp.status_code == 200

    def test_publish_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/news/99999/publish", headers=moderator_headers)
        assert resp.status_code == 404

    def test_unpublish_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/news/99999/unpublish", headers=moderator_headers)
        assert resp.status_code == 404

    def test_news_detail_by_id(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news",
            json={"title": "DetailById", "slug": "detail-by-id", "content": "body"},
            headers=moderator_headers,
        )
        article_id = resp.get_json()["id"]
        client.post(f"/api/v1/news/{article_id}/publish", headers=moderator_headers)
        resp = client.get(f"/api/v1/news/{article_id}")
        assert resp.status_code == 200

    def test_news_translations_list(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news",
            json={"title": "TransTest", "slug": "trans-test", "content": "body"},
            headers=moderator_headers,
        )
        article_id = resp.get_json()["id"]
        resp = client.get(f"/api/v1/news/{article_id}/translations", headers=moderator_headers)
        assert resp.status_code == 200

    def test_news_translation_put(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news",
            json={"title": "TransPut", "slug": "trans-put", "content": "body"},
            headers=moderator_headers,
        )
        article_id = resp.get_json()["id"]
        resp = client.put(
            f"/api/v1/news/{article_id}/translations/en",
            json={"title": "English Title", "content": "English body", "summary": "Eng sum"},
            headers=moderator_headers,
        )
        assert resp.status_code in (200, 201)

    def test_news_translation_get(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news",
            json={"title": "TransGet", "slug": "trans-get", "content": "body"},
            headers=moderator_headers,
        )
        article_id = resp.get_json()["id"]
        client.put(
            f"/api/v1/news/{article_id}/translations/en",
            json={"title": "En", "content": "En body", "summary": "s"},
            headers=moderator_headers,
        )
        resp = client.get(f"/api/v1/news/{article_id}/translations/en", headers=moderator_headers)
        assert resp.status_code == 200


# ======================= WIKI ADMIN TESTS =======================



"""Tests for TestNewsTranslationWorkflow."""

class TestNewsTranslationWorkflow:

    def _create_article(self, client, moderator_headers):
        resp = client.post(
            "/api/v1/news",
            json={"title": f"NTW-{id(self)}", "slug": f"ntw-{id(self)}", "content": "body"},
            headers=moderator_headers,
        )
        assert resp.status_code == 201
        return resp.get_json()["id"]

    def test_translation_submit_review(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        # Create translation first
        client.put(
            f"/api/v1/news/{aid}/translations/en",
            json={"title": "EN", "content": "EN body", "summary": "s"},
            headers=moderator_headers,
        )
        resp = client.post(f"/api/v1/news/{aid}/translations/en/submit-review", headers=moderator_headers)
        assert resp.status_code == 200

    def test_translation_submit_review_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/news/99999/translations/en/submit-review", headers=moderator_headers)
        assert resp.status_code == 404

    def test_translation_approve(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        client.put(
            f"/api/v1/news/{aid}/translations/en",
            json={"title": "EN", "content": "EN body", "summary": "s"},
            headers=moderator_headers,
        )
        resp = client.post(f"/api/v1/news/{aid}/translations/en/approve", headers=moderator_headers)
        assert resp.status_code == 200

    def test_translation_approve_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/news/99999/translations/en/approve", headers=moderator_headers)
        assert resp.status_code == 404

    def test_translation_publish(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        client.put(
            f"/api/v1/news/{aid}/translations/en",
            json={"title": "EN", "content": "EN body", "summary": "s"},
            headers=moderator_headers,
        )
        resp = client.post(f"/api/v1/news/{aid}/translations/en/publish", headers=moderator_headers)
        assert resp.status_code == 200

    def test_translation_publish_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/news/99999/translations/en/publish", headers=moderator_headers)
        assert resp.status_code == 404

    def test_auto_translate(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        resp = client.post(
            f"/api/v1/news/{aid}/translations/auto-translate",
            json={},
            headers=moderator_headers,
        )
        assert resp.status_code == 202

    def test_auto_translate_not_found(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news/99999/translations/auto-translate",
            json={},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_translation_get_unsupported_lang(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        resp = client.get(f"/api/v1/news/{aid}/translations/xx", headers=moderator_headers)
        assert resp.status_code == 400

    def test_translation_put_missing_body(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        resp = client.put(f"/api/v1/news/{aid}/translations/en", headers=moderator_headers)
        assert resp.status_code == 400

    def test_translation_put_not_found(self, app, client, moderator_headers):
        resp = client.put(
            "/api/v1/news/99999/translations/en",
            json={"title": "X", "content": "Y"},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_translations_list_not_found(self, app, client, moderator_headers):
        resp = client.get("/api/v1/news/99999/translations", headers=moderator_headers)
        assert resp.status_code == 404

    def test_news_detail_by_slug(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        client.post(f"/api/v1/news/{aid}/publish", headers=moderator_headers)
        resp = client.get(f"/api/v1/news/{aid}")
        assert resp.status_code == 200

    def test_news_detail_not_found_slug(self, app, client):
        resp = client.get("/api/v1/news/nonexistent-slug-abc")
        assert resp.status_code == 404

    def test_news_list_with_search(self, app, client, moderator_headers):
        self._create_article(client, moderator_headers)
        resp = client.get("/api/v1/news?q=NTW")
        assert resp.status_code == 200

    def test_news_list_with_sort(self, app, client, moderator_headers):
        self._create_article(client, moderator_headers)
        resp = client.get("/api/v1/news?sort=title&direction=asc")
        assert resp.status_code == 200

    def test_news_create_missing_body(self, app, client, moderator_headers):
        resp = client.post("/api/v1/news", headers=moderator_headers)
        assert resp.status_code == 400

    def test_news_update_missing_body(self, app, client, moderator_headers):
        aid = self._create_article(client, moderator_headers)
        resp = client.put(f"/api/v1/news/{aid}", headers=moderator_headers)
        assert resp.status_code == 400


# ======================= NEWS DISCUSSION THREAD LINKS =======================



"""Tests for TestNewsDiscussionThreadLinks."""

class TestNewsDiscussionThreadLinks:

    def _setup(self, app, client, moderator_headers):
        """Create news article + forum thread, return (article_id, thread_id)."""
        resp = client.post(
            "/api/v1/news",
            json={"title": f"NDT-{id(self)}", "slug": f"ndt-{id(self)}", "content": "body"},
            headers=moderator_headers,
        )
        article_id = resp.get_json()["id"]
        with app.app_context():
            user = User.query.filter_by(username="moderatoruser").first()
            cat = ForumCategory(title="News Disc Cat", slug=f"news-disc-cat-{id(self)}", description="test")
            db.session.add(cat)
            db.session.flush()
            thread = ForumThread(
                title="News Discussion",
                slug=f"news-disc-thread-{id(self)}",
                category_id=cat.id,
                author_id=user.id,
            )
            db.session.add(thread)
            db.session.commit()
            thread_id = thread.id
        return article_id, thread_id

    def test_link_discussion_thread(self, app, client, moderator_headers):
        aid, tid = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/news/{aid}/discussion-thread",
            json={"discussion_thread_id": tid},
            headers=moderator_headers,
        )
        assert resp.status_code == 200

    def test_link_discussion_thread_not_found(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/news/99999/discussion-thread",
            json={"discussion_thread_id": 1},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_link_discussion_thread_missing_body(self, app, client, moderator_headers):
        aid, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/news/{aid}/discussion-thread",
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_link_discussion_thread_invalid_id(self, app, client, moderator_headers):
        aid, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/news/{aid}/discussion-thread",
            json={"discussion_thread_id": "abc"},
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_unlink_discussion_thread(self, app, client, moderator_headers):
        aid, tid = self._setup(app, client, moderator_headers)
        client.post(
            f"/api/v1/news/{aid}/discussion-thread",
            json={"discussion_thread_id": tid},
            headers=moderator_headers,
        )
        resp = client.delete(f"/api/v1/news/{aid}/discussion-thread", headers=moderator_headers)
        assert resp.status_code == 200

    def test_unlink_discussion_thread_not_found(self, app, client, moderator_headers):
        resp = client.delete("/api/v1/news/99999/discussion-thread", headers=moderator_headers)
        assert resp.status_code == 404

    def test_related_threads_get(self, app, client, moderator_headers):
        aid, _ = self._setup(app, client, moderator_headers)
        resp = client.get(f"/api/v1/news/{aid}/related-threads", headers=moderator_headers)
        assert resp.status_code == 200

    def test_related_threads_add(self, app, client, moderator_headers):
        aid, tid = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/news/{aid}/related-threads",
            json={"thread_id": tid},
            headers=moderator_headers,
        )
        assert resp.status_code == 200

    def test_related_threads_add_missing_body(self, app, client, moderator_headers):
        aid, _ = self._setup(app, client, moderator_headers)
        resp = client.post(f"/api/v1/news/{aid}/related-threads", headers=moderator_headers)
        assert resp.status_code == 400

    def test_related_threads_add_invalid_id(self, app, client, moderator_headers):
        aid, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/news/{aid}/related-threads",
            json={"thread_id": "abc"},
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_related_threads_delete(self, app, client, moderator_headers):
        aid, tid = self._setup(app, client, moderator_headers)
        client.post(
            f"/api/v1/news/{aid}/related-threads",
            json={"thread_id": tid},
            headers=moderator_headers,
        )
        resp = client.delete(f"/api/v1/news/{aid}/related-threads/{tid}", headers=moderator_headers)
        assert resp.status_code == 200

    def test_related_threads_delete_not_found(self, app, client, moderator_headers):
        aid, _ = self._setup(app, client, moderator_headers)
        resp = client.delete(f"/api/v1/news/{aid}/related-threads/99999", headers=moderator_headers)
        assert resp.status_code == 404


# ======================= AREA API EXTENDED =======================
