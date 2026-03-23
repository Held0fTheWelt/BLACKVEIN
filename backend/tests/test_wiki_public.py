"""Tests for public wiki API: GET /api/v1/wiki/<slug> and discussion link in response."""
import pytest

from app.extensions import db
from app.models import ForumCategory, ForumThread, WikiPage, WikiPageTranslation


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
