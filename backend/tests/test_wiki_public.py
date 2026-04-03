"""Tests for public wiki API: GET /api/v1/wiki/<slug> and discussion link in response."""
from datetime import datetime, timezone

import pytest

from app.extensions import db
from app.models import ForumCategory, ForumThread, WikiPage, WikiPageForumThread, WikiPageTranslation


@pytest.fixture
def wiki_page_with_discussion(app):
    """Create a published wiki page with a linked forum thread."""
    with app.app_context():
        cat = ForumCategory(slug="wiki-cat", title="Wiki Cat", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(category_id=cat.id, slug="wiki-discuss", title="Wiki discussion", status="open")
        db.session.add(thread)
        db.session.flush()
        page = WikiPage(key="testpage", is_published=True, discussion_thread_id=thread.id)
        db.session.add(page)
        db.session.flush()
        trans = WikiPageTranslation(
            page_id=page.id,
            language_code="de",
            title="Test Page",
            slug="test-page",
            content_markdown="Content here.",
        )
        db.session.add(trans)
        db.session.commit()
        thread_id = thread.id
        return page, thread_id


def test_wiki_page_get_returns_discussion_link_when_linked(client, wiki_page_with_discussion):
    """GET /api/v1/wiki/<slug> includes discussion object when page has linked thread."""
    page, thread_id = wiki_page_with_discussion
    resp = client.get("/api/v1/wiki/test-page?lang=de")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("title") == "Test Page"
    assert data.get("discussion") is not None
    assert data["discussion"].get("thread_id") == thread_id
    assert data["discussion"].get("thread_slug") == "wiki-discuss"
    assert data["discussion"].get("type") == "primary"


def test_wiki_page_get_no_discussion_link_when_not_linked(app, client):
    """GET /api/v1/wiki/<slug> returns discussion null when not linked."""
    with app.app_context():
        page = WikiPage(key="nolink", is_published=True, discussion_thread_id=None)
        db.session.add(page)
        db.session.flush()
        trans = WikiPageTranslation(
            page_id=page.id,
            language_code="de",
            title="No Link Page",
            slug="no-link-page",
            content_markdown="Content.",
        )
        db.session.add(trans)
        db.session.commit()

    resp = client.get("/api/v1/wiki/no-link-page?lang=de")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("discussion") is None


def test_wiki_page_get_discussion_null_when_primary_thread_soft_deleted(app, client):
    """Linked discussion thread with deleted_at set yields discussion null (wiki_routes line 57)."""
    with app.app_context():
        cat = ForumCategory(
            slug="wiki-cat-del",
            title="Wiki Cat Del",
            is_active=True,
            is_private=False,
        )
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(
            category_id=cat.id,
            slug="wiki-deleted-thread",
            title="Deleted discussion",
            status="open",
            deleted_at=datetime.now(timezone.utc),
        )
        db.session.add(thread)
        db.session.flush()
        page = WikiPage(
            key="deldiscpage",
            is_published=True,
            discussion_thread_id=thread.id,
        )
        db.session.add(page)
        db.session.flush()
        trans = WikiPageTranslation(
            page_id=page.id,
            language_code="de",
            title="Del Disc Page",
            slug="del-disc-page",
            content_markdown="Body.",
        )
        db.session.add(trans)
        db.session.commit()

    resp = client.get("/api/v1/wiki/del-disc-page?lang=de")
    assert resp.status_code == 200
    assert resp.get_json().get("discussion") is None


def test_wiki_page_get_includes_related_threads(app, client):
    """Manually linked forum threads appear as related_threads with type related."""
    with app.app_context():
        cat = ForumCategory(
            slug="wiki-rel-cat",
            title="Wiki Rel Cat",
            is_active=True,
            is_private=False,
            required_role=None,
        )
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(
            category_id=cat.id,
            slug="wiki-related-thr",
            title="Related thread",
            status="open",
        )
        db.session.add(thread)
        db.session.flush()
        page = WikiPage(key="relwiki", is_published=True, discussion_thread_id=None)
        db.session.add(page)
        db.session.flush()
        db.session.add(WikiPageForumThread(page_id=page.id, thread_id=thread.id))
        trans = WikiPageTranslation(
            page_id=page.id,
            language_code="de",
            title="Rel Wiki",
            slug="rel-wiki-page",
            content_markdown="Text.",
        )
        db.session.add(trans)
        db.session.commit()

    resp = client.get("/api/v1/wiki/rel-wiki-page?lang=de")
    assert resp.status_code == 200
    data = resp.get_json()
    rel = data.get("related_threads")
    assert rel and len(rel) == 1
    assert rel[0].get("type") == "related"
    assert rel[0].get("slug") == "wiki-related-thr"


def test_wiki_page_get_includes_suggested_threads(monkeypatch, app, client):
    """Suggested threads branch when service returns items not filtered as manual or primary."""
    with app.app_context():
        page = WikiPage(key="sugwiki", is_published=True, discussion_thread_id=None)
        db.session.add(page)
        db.session.flush()
        trans = WikiPageTranslation(
            page_id=page.id,
            language_code="de",
            title="Sug Wiki",
            slug="sug-wiki-page",
            content_markdown="X.",
        )
        db.session.add(trans)
        db.session.commit()

    from app.api.v1 import wiki_routes

    def fake_suggested(_page_id, limit=5):
        return [
            {
                "id": 91001,
                "slug": "suggested-slug",
                "title": "Suggested",
                "reason": "test",
            }
        ]

    monkeypatch.setattr(wiki_routes, "get_suggested_threads_for_wiki_page", fake_suggested)

    resp = client.get("/api/v1/wiki/sug-wiki-page?lang=de")
    assert resp.status_code == 200
    sug = resp.get_json().get("suggested_threads")
    assert sug and len(sug) == 1
    assert sug[0].get("type") == "suggested"
    assert sug[0].get("id") == 91001
