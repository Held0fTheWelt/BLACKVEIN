"""Tests for suggested forum threads linked to news/wiki discussions.

Replaces a legacy module that imported removed models (Forum, Thread, etc.) and
specified non-existent routes. These tests exercise real service behavior:
`get_suggested_threads_for_article` and exclusion of the primary discussion thread.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.extensions import db
from app.models import (
    ForumCategory,
    ForumTag,
    ForumThread,
    ForumThreadTag,
    NewsArticle,
    NewsArticleTranslation,
)


@pytest.fixture
def discussion_suggestion_setup(app, test_user):
    """Category, primary thread (tagged), second thread (same tag), published article with discussion_thread_id."""
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)

        cat = ForumCategory(
            slug="sugg-disc-cat",
            title="Suggestion Disc",
            sort_order=0,
            is_active=True,
            is_private=False,
        )
        db.session.add(cat)
        db.session.flush()

        tag = ForumTag(slug="sugg-disc-python", label="python")
        db.session.add(tag)
        db.session.flush()

        primary = ForumThread(
            category_id=cat.id,
            author_id=user.id,
            slug="sugg-disc-primary",
            title="Primary discussion",
            status="open",
            created_at=now,
            updated_at=now,
        )
        other = ForumThread(
            category_id=cat.id,
            author_id=user.id,
            slug="sugg-disc-related",
            title="Related by tag",
            status="open",
            created_at=now,
            updated_at=now,
        )
        db.session.add_all([primary, other])
        db.session.flush()

        db.session.add_all(
            [
                ForumThreadTag(thread_id=primary.id, tag_id=tag.id),
                ForumThreadTag(thread_id=other.id, tag_id=tag.id),
            ]
        )

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
            title="Article with discussion",
            slug="sugg-disc-article",
            content="Body",
            translation_status="published",
            source_language="de",
            translated_at=now,
        )
        db.session.add(trans)
        db.session.commit()

        return {
            "article_id": article.id,
            "primary_thread_id": primary.id,
            "other_thread_id": other.id,
        }


def test_get_suggested_threads_excludes_primary_discussion(
    app, discussion_suggestion_setup
):
    """Primary discussion thread is not included in suggestions."""
    from app.services.news_service import get_suggested_threads_for_article

    ids = discussion_suggestion_setup
    with app.app_context():
        items = get_suggested_threads_for_article(ids["article_id"], limit=10)
        thread_ids = {x["id"] for x in items}

    assert ids["primary_thread_id"] not in thread_ids
    assert ids["other_thread_id"] in thread_ids


def test_get_suggested_threads_reason_labels_tag_matches(
    app, discussion_suggestion_setup
):
    """When tags overlap, the reason label includes 'Matched' and 'tag(s)'."""
    from app.services.news_service import get_suggested_threads_for_article

    with app.app_context():
        items = get_suggested_threads_for_article(
            discussion_suggestion_setup["article_id"], limit=10
        )

    other = next(
        x
        for x in items
        if x["id"] == discussion_suggestion_setup["other_thread_id"]
    )
    assert "reason" in other
    assert "Matched" in other["reason"]
    assert "tag" in other["reason"].lower()
