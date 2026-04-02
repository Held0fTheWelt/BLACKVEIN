"""Extra forum_routes coverage (404/400 branches and _current_user_optional)."""


def test_forum_categories_survives_get_current_user_exception(client, monkeypatch):
    from app.api.v1 import forum_routes

    def _boom():
        raise RuntimeError("jwt")

    monkeypatch.setattr(forum_routes, "get_current_user", _boom)
    r = client.get("/api/v1/forum/categories")
    assert r.status_code == 200
    assert "items" in r.get_json()


def test_forum_category_unknown_slug_returns_404(client):
    r = client.get("/api/v1/forum/categories/does-not-exist-slug-99999")
    assert r.status_code == 404


def test_forum_category_threads_unknown_returns_404(client):
    r = client.get("/api/v1/forum/categories/missing-cat/threads")
    assert r.status_code == 404


def test_forum_thread_detail_unknown_slug_returns_404(client):
    r = client.get("/api/v1/forum/threads/no-such-thread-slug-ever-12345")
    assert r.status_code == 404


def test_forum_thread_posts_unknown_id_returns_404(client):
    r = client.get("/api/v1/forum/threads/999999999/posts")
    assert r.status_code == 404


def test_forum_search_no_filters_returns_empty(client):
    r = client.get("/api/v1/forum/search")
    assert r.status_code == 200
    body = r.get_json()
    assert body["items"] == []
    assert body["total"] == 0


def test_forum_search_short_query_returns_400(client):
    r = client.get("/api/v1/forum/search?q=ab")
    assert r.status_code == 400


def test_forum_search_invalid_status_returns_400(client):
    r = client.get("/api/v1/forum/search?q=hello&status=not_a_status")
    assert r.status_code == 400
