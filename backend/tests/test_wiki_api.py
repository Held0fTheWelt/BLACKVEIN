"""Tests for wiki API: GET and PUT /api/v1/wiki (moderator/admin only)."""
import pytest

from app.extensions import db
from app.models import (
    User,
    Role,
    WikiPage,
    WikiPageTranslation,
    ForumCategory,
    ForumThread,
)


def test_wiki_get_without_auth_returns_401(client):
    """GET /api/v1/wiki without Authorization returns 401."""
    response = client.get("/api/v1/wiki")
    assert response.status_code == 401


def test_wiki_get_with_user_role_returns_403(client, auth_headers):
    """GET /api/v1/wiki with JWT for plain user returns 403."""
    response = client.get("/api/v1/wiki", headers=auth_headers)
    assert response.status_code == 403


def test_wiki_get_with_moderator_returns_200(client, moderator_headers, tmp_path, monkeypatch):
    """GET /api/v1/wiki with moderator JWT returns 200 and content/html."""
    wiki_file = tmp_path / "wiki.md"
    wiki_file.write_text("# Hello\n\nWiki content.", encoding="utf-8")

    from app.api.v1 import wiki_routes
    def fake_path():
        return wiki_file
    monkeypatch.setattr(wiki_routes, "_wiki_path", fake_path)

    response = client.get("/api/v1/wiki", headers=moderator_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "content" in data
    assert data["content"] == "# Hello\n\nWiki content."
    assert "html" in data
    assert "Hello" in (data["html"] or "")


def test_wiki_get_missing_file_returns_empty_content(client, moderator_headers, tmp_path, monkeypatch):
    """GET /api/v1/wiki when file does not exist returns 200 with empty content."""
    wiki_file = tmp_path / "wiki.md"
    assert not wiki_file.exists()

    from app.api.v1 import wiki_routes
    def fake_path():
        return wiki_file
    monkeypatch.setattr(wiki_routes, "_wiki_path", fake_path)

    response = client.get("/api/v1/wiki", headers=moderator_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("content") == ""
    assert data.get("html") is None


def test_wiki_put_without_auth_returns_401(client):
    """PUT /api/v1/wiki without Authorization returns 401."""
    response = client.put(
        "/api/v1/wiki",
        json={"content": "# Updated"},
        content_type="application/json",
    )
    assert response.status_code == 401


def test_wiki_put_with_moderator_writes_file(client, moderator_headers, tmp_path, monkeypatch):
    """PUT /api/v1/wiki with moderator JWT writes content and returns 200."""
    wiki_file = tmp_path / "wiki.md"
    wiki_file.parent.mkdir(parents=True, exist_ok=True)
    wiki_file.write_text("old", encoding="utf-8")

    from app.api.v1 import wiki_routes
    def fake_path():
        return wiki_file
    monkeypatch.setattr(wiki_routes, "_wiki_path", fake_path)

    response = client.put(
        "/api/v1/wiki",
        json={"content": "# New content\n\nUpdated."},
        content_type="application/json",
        headers=moderator_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("message") == "Updated"
    assert data.get("content") == "# New content\n\nUpdated."
    assert wiki_file.read_text(encoding="utf-8") == "# New content\n\nUpdated."


def test_wiki_put_without_body_returns_400(client, moderator_headers, tmp_path, monkeypatch):
    """PUT /api/v1/wiki without JSON body returns 400."""
    wiki_file = tmp_path / "wiki.md"
    from app.api.v1 import wiki_routes
    monkeypatch.setattr(wiki_routes, "_wiki_path", lambda: wiki_file)

    response = client.put("/api/v1/wiki", headers=moderator_headers)
    assert response.status_code == 400
    assert response.get_json().get("error")


def test_wiki_put_without_content_key_returns_400(client, moderator_headers, tmp_path, monkeypatch):
    """PUT /api/v1/wiki with body missing 'content' returns 400."""
    wiki_file = tmp_path / "wiki.md"
    from app.api.v1 import wiki_routes
    monkeypatch.setattr(wiki_routes, "_wiki_path", lambda: wiki_file)

    response = client.put(
        "/api/v1/wiki",
        json={},
        content_type="application/json",
        headers=moderator_headers,
    )
    assert response.status_code == 400
    assert "content" in (response.get_json().get("error") or "").lower()


def test_wiki_public_slug_not_found_returns_404(client):
    assert client.get("/api/v1/wiki/does-not-exist-slug-xyz").status_code == 404


def test_wiki_suggested_threads_unknown_page_returns_404(client):
    assert client.get("/api/v1/wiki/999999/suggested-threads").status_code == 404


def test_wiki_suggested_threads_existing_page_returns_200(client, app):
    """GET /api/v1/wiki/<page_id>/suggested-threads returns items and total when page exists."""
    with app.app_context():
        page = WikiPage(key="sug-api-page", is_published=True, discussion_thread_id=None)
        db.session.add(page)
        db.session.commit()
        page_id = page.id

    resp = client.get(f"/api/v1/wiki/{page_id}/suggested-threads")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data.get("total") == len(data["items"])


def test_wiki_public_markdown_failure_sets_html_none(client, app, monkeypatch):
    """Exception during markdown render yields html=None (wiki_page_get)."""
    from app.api.v1 import wiki_routes
    from app.models import WikiPage, WikiPageTranslation

    with app.app_context():
        page = WikiPage(key="md_fail_page", discussion_thread_id=None)
        db.session.add(page)
        db.session.flush()
        tr = WikiPageTranslation(
            page_id=page.id,
            language_code="de",
            title="T",
            slug="md-fail-page",
            content_markdown="# x",
        )
        db.session.add(tr)
        db.session.commit()
        slug = tr.slug

    def boom(*_a, **_kw):
        raise RuntimeError("markdown boom")

    monkeypatch.setattr(wiki_routes.markdown, "markdown", boom)
    resp = client.get(f"/api/v1/wiki/{slug}?lang=de")
    assert resp.status_code == 200
    assert resp.get_json().get("html") is None


def test_wiki_put_content_must_be_string(client, moderator_headers, tmp_path, monkeypatch):
    wiki_file = tmp_path / "wiki.md"
    from app.api.v1 import wiki_routes

    monkeypatch.setattr(wiki_routes, "_wiki_path", lambda: wiki_file)
    resp = client.put(
        "/api/v1/wiki",
        json={"content": 123},
        headers=moderator_headers,
    )
    assert resp.status_code == 400


def test_wiki_get_read_oserror_returns_500(client, moderator_headers, tmp_path, monkeypatch):
    """OSError when reading wiki file returns 500 (wiki_get)."""
    from app.api.v1 import wiki_routes

    class UnreadablePath:
        def is_file(self):
            return True

        def read_text(self, encoding="utf-8"):
            raise OSError("simulated read failure")

    monkeypatch.setattr(wiki_routes, "_wiki_path", UnreadablePath)

    resp = client.get("/api/v1/wiki", headers=moderator_headers)
    assert resp.status_code == 500
    assert "read" in (resp.get_json().get("error") or "").lower()


def test_wiki_get_markdown_failure_sets_html_none(client, moderator_headers, tmp_path, monkeypatch):
    """Exception during markdown in legacy wiki_get leaves html None."""
    from app.api.v1 import wiki_routes

    wiki_file = tmp_path / "wiki.md"
    wiki_file.write_text("# Body", encoding="utf-8")
    monkeypatch.setattr(wiki_routes, "_wiki_path", lambda: wiki_file)

    def boom(*_a, **_kw):
        raise RuntimeError("markdown boom")

    monkeypatch.setattr(wiki_routes.markdown, "markdown", boom)

    resp = client.get("/api/v1/wiki", headers=moderator_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("content") == "# Body"
    assert data.get("html") is None


def test_wiki_put_write_oserror_returns_500(client, moderator_headers, tmp_path, monkeypatch):
    """OSError when writing wiki file returns 500 (wiki_put)."""
    from app.api.v1 import wiki_routes

    wiki_file = tmp_path / "wiki.md"

    class UnwritablePath:
        parent = wiki_file.parent

        def write_text(self, content, encoding="utf-8"):
            raise OSError("simulated write failure")

    monkeypatch.setattr(wiki_routes, "_wiki_path", UnwritablePath)

    resp = client.put(
        "/api/v1/wiki",
        json={"content": "# new"},
        content_type="application/json",
        headers=moderator_headers,
    )
    assert resp.status_code == 500
    assert "write" in (resp.get_json().get("error") or "").lower()


"""Tests for TestWikiAdminAPI."""

class TestWikiAdminAPI:

    def test_wiki_page_list(self, app, client, moderator_headers):
        resp = client.get("/api/v1/wiki-admin/pages", headers=moderator_headers)
        assert resp.status_code == 200

    def test_wiki_page_create(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            json={"key": "test-wiki-page"},
            headers=moderator_headers,
        )
        assert resp.status_code in (200, 201)

    def test_wiki_page_create_missing_key(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            json={"key": ""},
            headers=moderator_headers,
        )
        assert resp.status_code in (400, 422)

    def test_wiki_page_update(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            json={"key": "wiki-upd-test"},
            headers=moderator_headers,
        )
        if resp.status_code in (200, 201):
            page_id = resp.get_json().get("id")
            if page_id:
                resp = client.put(
                    f"/api/v1/wiki-admin/pages/{page_id}",
                    json={"key": "wiki-upd-test-2"},
                    headers=moderator_headers,
                )
                assert resp.status_code == 200

    def test_wiki_admin_requires_mod(self, app, client, auth_headers):
        resp = client.get("/api/v1/wiki-admin/pages", headers=auth_headers)
        assert resp.status_code == 403

    def test_wiki_page_translations(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            json={"key": "wiki-trans-test"},
            headers=moderator_headers,
        )
        if resp.status_code in (200, 201):
            page_id = resp.get_json().get("id")
            if page_id:
                resp = client.get(f"/api/v1/wiki-admin/pages/{page_id}/translations", headers=moderator_headers)
                assert resp.status_code == 200

    def test_wiki_page_put_translation(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            json={"key": "wiki-trans-put"},
            headers=moderator_headers,
        )
        if resp.status_code in (200, 201):
            page_id = resp.get_json().get("id")
            if page_id:
                resp = client.put(
                    f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
                    json={"title": "German Title", "slug": "german-title", "content_markdown": "German body"},
                    headers=moderator_headers,
                )
                assert resp.status_code in (200, 201)


# ======================= PUBLIC WIKI TESTS =======================



"""Tests for TestWikiPublicAPI."""

class TestWikiPublicAPI:

    def test_wiki_get_requires_mod(self, app, client, moderator_headers):
        resp = client.get("/api/v1/wiki", headers=moderator_headers)
        assert resp.status_code == 200

    def test_wiki_get_forbidden_for_user(self, app, client, auth_headers):
        resp = client.get("/api/v1/wiki", headers=auth_headers)
        assert resp.status_code == 403

    def test_wiki_public_page_not_found(self, app, client):
        resp = client.get("/api/v1/wiki/nonexistent")
        assert resp.status_code == 404


# ======================= WEB ROUTES TESTS =======================



"""Tests for TestWikiAdminTranslationWorkflow."""

class TestWikiAdminTranslationWorkflow:

    def _create_page_with_translation(self, client, moderator_headers):
        """Helper: create wiki page + de translation, return (page_id, trans_response)."""
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            json={"key": f"wiki-wf-{id(self)}"},
            headers=moderator_headers,
        )
        assert resp.status_code in (200, 201)
        page_id = resp.get_json()["id"]
        resp = client.put(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
            json={"title": "DE Title", "slug": f"de-slug-{id(self)}", "content_markdown": "DE Content"},
            headers=moderator_headers,
        )
        assert resp.status_code in (200, 201)
        return page_id

    def test_translation_get(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.get(f"/api/v1/wiki-admin/pages/{page_id}/translations/de", headers=moderator_headers)
        assert resp.status_code == 200
        assert resp.get_json()["title"] == "DE Title"

    def test_translation_get_not_found(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.get(f"/api/v1/wiki-admin/pages/{page_id}/translations/en", headers=moderator_headers)
        assert resp.status_code == 404

    def test_translation_get_unsupported_lang(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.get(f"/api/v1/wiki-admin/pages/{page_id}/translations/xx", headers=moderator_headers)
        assert resp.status_code == 400

    def test_submit_review(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.post(f"/api/v1/wiki-admin/pages/{page_id}/translations/de/submit-review", headers=moderator_headers)
        assert resp.status_code == 200
        assert resp.get_json()["translation_status"] == "review_required"

    def test_submit_review_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/wiki-admin/pages/99999/translations/de/submit-review", headers=moderator_headers)
        assert resp.status_code == 404

    def test_approve(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.post(f"/api/v1/wiki-admin/pages/{page_id}/translations/de/approve", headers=moderator_headers)
        assert resp.status_code == 200
        assert resp.get_json()["translation_status"] == "approved"

    def test_approve_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/wiki-admin/pages/99999/translations/de/approve", headers=moderator_headers)
        assert resp.status_code == 404

    def test_publish(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.post(f"/api/v1/wiki-admin/pages/{page_id}/translations/de/publish", headers=moderator_headers)
        assert resp.status_code == 200
        assert resp.get_json()["translation_status"] == "published"

    def test_publish_not_found(self, app, client, moderator_headers):
        resp = client.post("/api/v1/wiki-admin/pages/99999/translations/de/publish", headers=moderator_headers)
        assert resp.status_code == 404

    def test_auto_translate(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/auto-translate",
            json={},
            headers=moderator_headers,
        )
        assert resp.status_code == 202

    def test_auto_translate_page_not_found(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki-admin/pages/99999/translations/auto-translate",
            json={},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_page_update_not_found(self, app, client, moderator_headers):
        resp = client.put(
            "/api/v1/wiki-admin/pages/99999",
            json={"key": "x"},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_page_translations_list_not_found(self, app, client, moderator_headers):
        resp = client.get("/api/v1/wiki-admin/pages/99999/translations", headers=moderator_headers)
        assert resp.status_code == 404

    def test_translation_put_missing_body(self, app, client, moderator_headers):
        page_id = self._create_page_with_translation(client, moderator_headers)
        resp = client.put(
            f"/api/v1/wiki-admin/pages/{page_id}/translations/de",
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_page_create_missing_body(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_page_update_missing_body(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            json={"key": "wiki-update-body-test"},
            headers=moderator_headers,
        )
        page_id = resp.get_json()["id"]
        resp = client.put(
            f"/api/v1/wiki-admin/pages/{page_id}",
            headers=moderator_headers,
        )
        assert resp.status_code == 400


# ======================= WIKI DISCUSSION THREAD LINKS =======================



"""Tests for TestWikiDiscussionThreadLinks."""

class TestWikiDiscussionThreadLinks:

    def _setup(self, app, client, moderator_headers):
        """Create a wiki page and a forum thread."""
        resp = client.post(
            "/api/v1/wiki-admin/pages",
            json={"key": f"wiki-disc-{id(self)}"},
            headers=moderator_headers,
        )
        page_id = resp.get_json()["id"]
        with app.app_context():
            user = User.query.filter_by(username="moderatoruser").first()
            cat = ForumCategory(title="Wiki Disc Cat", slug=f"wiki-disc-cat-{id(self)}", description="test")
            db.session.add(cat)
            db.session.flush()
            thread = ForumThread(
                title="Wiki Discussion",
                slug=f"wiki-disc-thread-{id(self)}",
                category_id=cat.id,
                author_id=user.id,
            )
            db.session.add(thread)
            db.session.commit()
            thread_id = thread.id
        return page_id, thread_id

    def test_link_discussion_thread(self, app, client, moderator_headers):
        page_id, thread_id = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki/{page_id}/discussion-thread",
            json={"discussion_thread_id": thread_id},
            headers=moderator_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["discussion_thread_id"] == thread_id

    def test_link_discussion_thread_page_not_found(self, app, client, moderator_headers):
        resp = client.post(
            "/api/v1/wiki/99999/discussion-thread",
            json={"discussion_thread_id": 1},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_link_discussion_thread_invalid_id(self, app, client, moderator_headers):
        page_id, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki/{page_id}/discussion-thread",
            json={"discussion_thread_id": "abc"},
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_link_discussion_thread_not_found(self, app, client, moderator_headers):
        page_id, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki/{page_id}/discussion-thread",
            json={"discussion_thread_id": 99999},
            headers=moderator_headers,
        )
        assert resp.status_code == 404

    def test_unlink_discussion_thread(self, app, client, moderator_headers):
        page_id, thread_id = self._setup(app, client, moderator_headers)
        client.post(
            f"/api/v1/wiki/{page_id}/discussion-thread",
            json={"discussion_thread_id": thread_id},
            headers=moderator_headers,
        )
        resp = client.delete(f"/api/v1/wiki/{page_id}/discussion-thread", headers=moderator_headers)
        assert resp.status_code == 200

    def test_unlink_discussion_thread_page_not_found(self, app, client, moderator_headers):
        resp = client.delete("/api/v1/wiki/99999/discussion-thread", headers=moderator_headers)
        assert resp.status_code == 404

    def test_related_threads_get(self, app, client, moderator_headers):
        page_id, _ = self._setup(app, client, moderator_headers)
        resp = client.get(f"/api/v1/wiki/{page_id}/related-threads", headers=moderator_headers)
        assert resp.status_code == 200

    def test_related_threads_add(self, app, client, moderator_headers):
        page_id, thread_id = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki/{page_id}/related-threads",
            json={"thread_id": thread_id},
            headers=moderator_headers,
        )
        assert resp.status_code == 200

    def test_related_threads_add_missing_body(self, app, client, moderator_headers):
        page_id, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki/{page_id}/related-threads",
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_related_threads_add_invalid_id(self, app, client, moderator_headers):
        page_id, _ = self._setup(app, client, moderator_headers)
        resp = client.post(
            f"/api/v1/wiki/{page_id}/related-threads",
            json={"thread_id": "abc"},
            headers=moderator_headers,
        )
        assert resp.status_code == 400

    def test_related_threads_delete(self, app, client, moderator_headers):
        page_id, thread_id = self._setup(app, client, moderator_headers)
        client.post(
            f"/api/v1/wiki/{page_id}/related-threads",
            json={"thread_id": thread_id},
            headers=moderator_headers,
        )
        resp = client.delete(
            f"/api/v1/wiki/{page_id}/related-threads/{thread_id}",
            headers=moderator_headers,
        )
        assert resp.status_code == 200

    def test_related_threads_delete_not_found(self, app, client, moderator_headers):
        page_id, _ = self._setup(app, client, moderator_headers)
        resp = client.delete(
            f"/api/v1/wiki/{page_id}/related-threads/99999",
            headers=moderator_headers,
        )
        assert resp.status_code == 404


# ======================= NEWS TRANSLATION WORKFLOW =======================
