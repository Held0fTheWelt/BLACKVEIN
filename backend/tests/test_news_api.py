"""Tests for news API: list, detail, search, sort, pagination, published-only, write access."""
import pytest


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
