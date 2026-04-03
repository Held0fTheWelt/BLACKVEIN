"""Service-level coverage for app.services.news_service helpers and branches."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.i18n import (
    TRANSLATION_STATUS_APPROVED,
    TRANSLATION_STATUS_OUTDATED,
    TRANSLATION_STATUS_PUBLISHED,
    TRANSLATION_STATUS_REVIEW_REQUIRED,
    get_default_language,
)
from app.models import (
    ForumCategory,
    ForumThread,
    NewsArticle,
    NewsArticleForumThread,
    NewsArticleTranslation,
)
from app.services import news_service as ns


def test_normalize_slug_edge_cases():
    assert ns._normalize_slug(None) is None
    assert ns._normalize_slug("") is None
    assert ns._normalize_slug("   ") is None
    assert ns._normalize_slug("Hello World!") == "hello-world"
    assert ns._normalize_slug("  Foo--Bar  ") == "foo-bar"


def test_effective_language_and_get_effective_translation(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        article = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            created_at=now,
            updated_at=now,
        )
        db.session.add(article)
        db.session.flush()
        t_de = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="DE",
            slug="de-slug",
            content="c",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        t_en = NewsArticleTranslation(
            article_id=article.id,
            language_code="en",
            title="EN",
            slug="en-slug",
            content="c2",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add_all([t_de, t_en])
        db.session.commit()

        assert ns._effective_language(article, "en") == "en"
        assert ns._effective_language(article, "xx") == "de"

        got = ns._get_effective_translation(article, "en")
        assert got and got.language_code == "en"

        # Fallback to default when requested lang missing
        db.session.delete(t_en)
        db.session.commit()
        got2 = ns._get_effective_translation(article, "en")
        assert got2 and got2.language_code == "de"


def test_article_to_public_dict_discussion_thread_variants(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        cat = ForumCategory(slug="news-cat", title="NC", is_active=True, is_private=False)
        db.session.add(cat)
        db.session.flush()
        thread_ok = ForumThread(
            category_id=cat.id,
            slug="disc-slug",
            title="Discussion",
            status="open",
            author_id=user.id,
        )
        thread_del = ForumThread(
            category_id=cat.id,
            slug="gone",
            title="Gone",
            status="open",
            author_id=user.id,
            deleted_at=now,
        )
        db.session.add_all([thread_ok, thread_del])
        db.session.flush()

        article = NewsArticle(
            author_id=user.id,
            status="published",
            default_language="de",
            discussion_thread_id=thread_ok.id,
            created_at=now,
            updated_at=now,
            published_at=now,
        )
        db.session.add(article)
        db.session.flush()
        trans = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="T",
            slug="t-slug",
            content="body",
            translation_status=TRANSLATION_STATUS_PUBLISHED,
            source_language="de",
            translated_at=now,
        )
        db.session.add(trans)
        db.session.commit()

        d = ns._article_to_public_dict(article, trans)
        assert d["discussion_thread_id"] == thread_ok.id
        assert d["discussion_thread_slug"] == thread_ok.slug

        article.discussion_thread_id = thread_del.id
        db.session.commit()
        d2 = ns._article_to_public_dict(article, trans)
        assert d2["discussion_thread_id"] is None
        assert d2["discussion_thread_slug"] is None

        article.discussion_thread_id = None
        db.session.commit()
        d3 = ns._article_to_public_dict(article, trans)
        assert d3["discussion_thread_id"] is None


def test_list_related_threads_for_article(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        assert ns.list_related_threads_for_article(0) == []
        assert ns.list_related_threads_for_article(None) == []

        cat = ForumCategory(
            slug="rel-cat",
            title="Rel",
            is_active=True,
            is_private=False,
            required_role=None,
        )
        db.session.add(cat)
        db.session.flush()
        thread = ForumThread(
            category_id=cat.id,
            slug="related-thread",
            title="Related",
            status="open",
            author_id=user.id,
        )
        db.session.add(thread)
        db.session.flush()
        article = NewsArticle(
            author_id=user.id,
            status="published",
            default_language="de",
            created_at=now,
            updated_at=now,
            published_at=now,
        )
        db.session.add(article)
        db.session.flush()
        link = NewsArticleForumThread(article_id=article.id, thread_id=thread.id)
        db.session.add(link)
        db.session.commit()

        items = ns.list_related_threads_for_article(article.id, limit=10)
        assert len(items) >= 1
        assert items[0]["slug"] == "related-thread"


def test_list_news_sort_title_and_editorial_statuses(app, sample_news):
    pub1, pub2, draft = sample_news
    with app.app_context():
        items, total = ns.list_news(published_only=True, sort="title", order="asc", lang="de")
        assert total >= 2
        assert all("title" in x for x in items)

        items2, _ = ns.list_news(published_only=False, sort="not_a_field", order="desc", lang="de")
        assert any("translation_statuses" in x for x in items2)


def test_create_and_update_news_validation(app, test_user):
    with app.app_context():
        _, err = ns.create_news("", "x", "body")
        assert err

        _, err2 = ns.create_news("T", "###", "body")
        assert err2

        a, err_ok = ns.create_news("T1", "t1-slug", "body", is_published=False)
        assert err_ok is None and a

        _, err_dup = ns.create_news("T2", "t1-slug", "body")
        assert "Slug already" in (err_dup or "")

        _, err_up = ns.update_news(a.id, title="   ")
        assert "empty" in (err_up or "").lower()

        _, err_slug = ns.update_news(a.id, slug="@@@")
        assert err_slug


def test_upsert_article_translation_paths(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        article = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            created_at=now,
            updated_at=now,
        )
        db.session.add(article)
        db.session.flush()
        t0 = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="Base",
            slug="base-slug",
            content="base",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add(t0)
        db.session.commit()

        _, err_lang = ns.upsert_article_translation(article.id, "xx", title="X", content="Y")
        assert err_lang

        _, err_new = ns.upsert_article_translation(article.id, "en", title=None, content=None)
        assert "required" in (err_new or "").lower()

        tr, err_ok = ns.upsert_article_translation(
            article.id, "en", title="English", slug="en-news", content="Hello"
        )
        assert err_ok is None and tr.language_code == "en"

        tr2, err_up = ns.upsert_article_translation(
            article.id, "en", summary="S" * 600
        )
        assert tr2 is None and "Summary" in (err_up or "")


def test_translation_workflow_helpers(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        article = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            created_at=now,
            updated_at=now,
        )
        db.session.add(article)
        db.session.flush()
        t_de = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="T",
            slug="wf-slug",
            content="c",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add(t_de)
        db.session.commit()

        assert ns.get_article_translation(article.id, "") is None

        ns.submit_review_article_translation(article.id, "de")
        db.session.refresh(t_de)
        assert t_de.translation_status == TRANSLATION_STATUS_REVIEW_REQUIRED

        ns.approve_article_translation(article.id, "de", reviewer_id=user.id)
        db.session.refresh(t_de)
        assert t_de.translation_status == TRANSLATION_STATUS_APPROVED

        ns.publish_article_translation(article.id, "de")
        db.session.refresh(t_de)
        assert t_de.translation_status == TRANSLATION_STATUS_PUBLISHED


def test_mark_article_translations_outdated(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        article = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            created_at=now,
            updated_at=now,
        )
        db.session.add(article)
        db.session.flush()
        t_de = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="T",
            slug="o-slug",
            content="c",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        t_en = NewsArticleTranslation(
            article_id=article.id,
            language_code="en",
            title="T2",
            slug="o-slug-en",
            content="c2",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add_all([t_de, t_en])
        db.session.commit()

        ns.mark_article_translations_outdated(article.id, exclude_language="de")
        db.session.refresh(t_de)
        db.session.refresh(t_en)
        assert t_en.translation_status == TRANSLATION_STATUS_OUTDATED
        assert t_de.translation_status == TRANSLATION_STATUS_APPROVED


def test_list_article_translations_and_delete_news(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        article = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language=get_default_language(),
            created_at=now,
            updated_at=now,
        )
        db.session.add(article)
        db.session.flush()
        t = NewsArticleTranslation(
            article_id=article.id,
            language_code=article.default_language,
            title="T",
            slug="del-slug",
            content="c",
            translation_status="approved",
            source_language=article.default_language,
            translated_at=now,
        )
        db.session.add(t)
        db.session.commit()

        rows, err = ns.list_article_translations(article.id)
        assert err is None and len(rows) >= 1

        ok, err_d = ns.delete_news(article.id)
        assert ok and err_d is None


def test_get_suggested_threads_missing_article(app):
    with app.app_context():
        assert ns.get_suggested_threads_for_article(999_999) == []


def test_article_to_public_dict_without_translation():
    assert ns._article_to_public_dict(
        NewsArticle(author_id=1, status="draft", default_language="de"),
        None,
    ) is None


def test_get_news_by_id_and_article_helpers(app):
    with app.app_context():
        assert ns.get_news_by_id(None) is None  # type: ignore[arg-type]
        assert ns.get_news_by_id(999_999_999) is None
        assert ns.get_news_article_by_id(None) is None  # type: ignore[arg-type]


def test_get_news_by_slug_bad_input_and_unpublished(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        assert ns.get_news_by_slug(None) is None  # type: ignore[arg-type]
        assert ns.get_news_by_slug(123) is None  # type: ignore[arg-type]

        article = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            created_at=now,
            updated_at=now,
        )
        db.session.add(article)
        db.session.flush()
        t = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="Draft only",
            slug="draft-only-slug",
            content="x",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add(t)
        db.session.commit()
        assert ns.get_news_by_slug("draft-only-slug") is None


def test_effective_language_fallback_to_app_default(app, test_user):
    with app.app_context():
        user, _ = test_user
        article = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="xx-invalid",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(article)
        db.session.commit()
        assert ns._effective_language(article, "also-bad") == get_default_language()


def test_list_news_category_search_and_future_publish(app, test_user, sample_news):
    _pub1, _pub2, _draft = sample_news
    with app.app_context():
        items, total = ns.list_news(published_only=True, category="Updates", lang="de")
        assert total >= 2
        assert all(x.get("category") == "Updates" for x in items)

        items_s, _ = ns.list_news(published_only=False, search="searchable", lang="de")
        assert any(
            "searchable" in (x.get("title") or "").lower()
            or "searchable" in (x.get("content") or "").lower()
            for x in items_s
        )

        user, _ = test_user
        now = datetime.now(timezone.utc)
        future_article = NewsArticle(
            author_id=user.id,
            status="published",
            default_language="de",
            created_at=now,
            updated_at=now,
            published_at=now + timedelta(days=7),
        )
        db.session.add(future_article)
        db.session.flush()
        ft = NewsArticleTranslation(
            article_id=future_article.id,
            language_code="de",
            title="Future",
            slug="future-scheduled",
            content="body",
            translation_status=TRANSLATION_STATUS_PUBLISHED,
            source_language="de",
            translated_at=now,
        )
        db.session.add(ft)
        db.session.commit()

        pub_only, tot = ns.list_news(published_only=True, lang="de")
        ids = {x["id"] for x in pub_only}
        assert future_article.id not in ids


def test_publish_and_unpublish_news_service(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        article = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            created_at=now,
            updated_at=now,
        )
        db.session.add(article)
        db.session.flush()
        t = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="Pub cycle",
            slug="pub-cycle-slug",
            content="c",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add(t)
        db.session.commit()

        a1, err = ns.publish_news(article.id)
        assert err is None and a1.status == "published"

        a2, err2 = ns.unpublish_news(article.id)
        assert err2 is None and a2.status == "draft"


def test_list_news_sort_published_order_asc(app, sample_news):
    with app.app_context():
        items, _ = ns.list_news(published_only=True, sort="created_at", order="asc", lang="de")
        assert len(items) >= 2
        times = [x["created_at"] for x in items if x.get("created_at")]
        assert times == sorted(times)
