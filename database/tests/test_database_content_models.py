from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    NewsArticle,
    NewsArticleForumThread,
    NewsArticleTranslation,
    WikiPage,
    WikiPageForumThread,
    WikiPageTranslation,
)


class TestNewsModels:
    def test_news_article_translation_unique_constraints_are_enforced(self, db, user_factory):
        author = user_factory(role_name="moderator")
        article = NewsArticle(author_id=author.id, status="draft", default_language="en", category="updates")
        db.session.add(article)
        db.session.commit()

        db.session.add(
            NewsArticleTranslation(
                article_id=article.id,
                language_code="en",
                title="Launch",
                slug="launch",
                summary="Summary",
                content="Content",
            )
        )
        db.session.commit()

        db.session.add(
            NewsArticleTranslation(
                article_id=article.id,
                language_code="en",
                title="Launch 2",
                slug="launch-2",
                content="Content 2",
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        second_article = NewsArticle(author_id=author.id, status="draft", default_language="en")
        db.session.add(second_article)
        db.session.commit()

        db.session.add(
            NewsArticleTranslation(
                article_id=second_article.id,
                language_code="en",
                title="Launch 3",
                slug="launch",
                content="Content 3",
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_news_article_delete_cascades_translations_and_related_threads(self, db, thread_factory, user_factory):
        author = user_factory(role_name="moderator")
        article = NewsArticle(author_id=author.id, status="published", default_language="en")
        db.session.add(article)
        db.session.commit()

        translation = NewsArticleTranslation(article_id=article.id, language_code="en", title="Hello", slug="hello-news", content="Body")
        relation = NewsArticleForumThread(article_id=article.id, thread_id=thread_factory().id, relation_type="discussion")
        db.session.add_all([translation, relation])
        db.session.commit()

        db.session.delete(article)
        db.session.commit()

        assert NewsArticleTranslation.query.count() == 0
        assert NewsArticleForumThread.query.count() == 0

    def test_news_article_forum_thread_link_is_unique_per_pair(self, db, thread_factory, user_factory):
        author = user_factory(role_name="moderator")
        article = NewsArticle(author_id=author.id, status="draft", default_language="en")
        thread = thread_factory()
        db.session.add(article)
        db.session.commit()

        db.session.add(NewsArticleForumThread(article_id=article.id, thread_id=thread.id))
        db.session.commit()

        db.session.add(NewsArticleForumThread(article_id=article.id, thread_id=thread.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_deleting_discussion_thread_sets_news_article_discussion_thread_to_null(self, db, thread_factory, user_factory):
        author = user_factory(role_name="moderator")
        thread = thread_factory()
        article = NewsArticle(
            author_id=author.id,
            status="draft",
            default_language="en",
            discussion_thread_id=thread.id,
            published_at=datetime.now(timezone.utc),
        )
        db.session.add(article)
        db.session.commit()

        db.session.delete(thread)
        db.session.commit()
        db.session.refresh(article)

        assert article.discussion_thread_id is None


class TestWikiModels:
    def test_wiki_page_translation_unique_constraints_are_enforced(self, db):
        page = WikiPage(key="intro", sort_order=0, is_published=True)
        db.session.add(page)
        db.session.commit()

        db.session.add(
            WikiPageTranslation(
                page_id=page.id,
                language_code="en",
                title="Intro",
                slug="intro",
                content_markdown="# Intro",
            )
        )
        db.session.commit()

        db.session.add(
            WikiPageTranslation(
                page_id=page.id,
                language_code="en",
                title="Intro 2",
                slug="intro-2",
                content_markdown="# Intro 2",
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        second_page = WikiPage(key="another", sort_order=1, is_published=True)
        db.session.add(second_page)
        db.session.commit()

        db.session.add(
            WikiPageTranslation(
                page_id=second_page.id,
                language_code="en",
                title="Another",
                slug="intro",
                content_markdown="# Another",
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_wiki_page_delete_cascades_translations_and_related_threads(self, db, thread_factory):
        page = WikiPage(key="lore", sort_order=0, is_published=True)
        db.session.add(page)
        db.session.commit()

        translation = WikiPageTranslation(page_id=page.id, language_code="en", title="Lore", slug="lore", content_markdown="Lore body")
        relation = WikiPageForumThread(page_id=page.id, thread_id=thread_factory().id)
        db.session.add_all([translation, relation])
        db.session.commit()

        db.session.delete(page)
        db.session.commit()

        assert WikiPageTranslation.query.count() == 0
        assert WikiPageForumThread.query.count() == 0

    def test_wiki_page_forum_thread_link_is_unique_per_pair(self, db, thread_factory):
        page = WikiPage(key="faq", sort_order=0, is_published=True)
        db.session.add(page)
        db.session.commit()
        thread = thread_factory()

        db.session.add(WikiPageForumThread(page_id=page.id, thread_id=thread.id))
        db.session.commit()

        db.session.add(WikiPageForumThread(page_id=page.id, thread_id=thread.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_deleting_discussion_thread_sets_wiki_page_discussion_thread_to_null(self, db, thread_factory):
        thread = thread_factory()
        page = WikiPage(key="thread-linked", sort_order=0, is_published=True, discussion_thread_id=thread.id)
        db.session.add(page)
        db.session.commit()

        db.session.delete(thread)
        db.session.commit()
        db.session.refresh(page)

        assert page.discussion_thread_id is None
