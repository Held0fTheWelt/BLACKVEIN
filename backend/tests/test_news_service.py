"""Service-level coverage for app.services.news_service helpers and branches."""

from __future__ import annotations

import builtins
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.extensions import db
from app.i18n import (
    TRANSLATION_STATUS_APPROVED,
    TRANSLATION_STATUS_MACHINE_DRAFT,
    TRANSLATION_STATUS_OUTDATED,
    TRANSLATION_STATUS_PUBLISHED,
    TRANSLATION_STATUS_REVIEW_REQUIRED,
    get_default_language,
)
from app.models import (
    ForumCategory,
    ForumTag,
    ForumThread,
    ForumThreadTag,
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
        assert "category" in items[0]
        assert items[0]["category"]["slug"] == "rel-cat"
        assert items[0]["category"]["title"] == "Rel"


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


def test_get_effective_translation_fallback_app_default_and_first_any(app, test_user):
    """Covers third-tier fallback (line 90) and .first() (line 91)."""
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        # App default "de", article default "en", only DE translation -> line 90
        a1 = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="en",
            created_at=now,
            updated_at=now,
        )
        db.session.add(a1)
        db.session.flush()
        t_de = NewsArticleTranslation(
            article_id=a1.id,
            language_code="de",
            title="Only DE",
            slug="only-de",
            content="c",
            translation_status="approved",
            source_language="en",
            translated_at=now,
        )
        db.session.add(t_de)
        # App default == article default == "de", only EN translation -> line 91
        a2 = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            created_at=now,
            updated_at=now,
        )
        db.session.add(a2)
        db.session.flush()
        t_en = NewsArticleTranslation(
            article_id=a2.id,
            language_code="en",
            title="Only EN",
            slug="only-en",
            content="c",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add(t_en)
        db.session.commit()

        got1 = ns._get_effective_translation(a1, None)
        assert got1 and got1.language_code == "de"

        got2 = ns._get_effective_translation(a2, None)
        assert got2 and got2.language_code == "en"


def test_article_to_public_dict_no_author(app, test_user):
    with app.app_context():
        now = datetime.now(timezone.utc)
        article = NewsArticle(
            author_id=None,
            status="published",
            default_language="de",
            created_at=now,
            updated_at=now,
            published_at=now,
        )
        db.session.add(article)
        db.session.flush()
        trans = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="Anon",
            slug="anon-slug",
            content="x",
            translation_status=TRANSLATION_STATUS_PUBLISHED,
            source_language="de",
            translated_at=now,
        )
        db.session.add(trans)
        db.session.commit()

        d = ns._article_to_public_dict(article, trans)
        assert d["author_id"] is None
        assert d["author_name"] is None


def test_get_news_by_id_no_translation(app, test_user):
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
        db.session.commit()
        assert ns.get_news_by_id(article.id) is None


def test_get_news_by_slug_draft_article_published_translation(app, test_user):
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
            title="Inconsistent",
            slug="inconsistent-slug",
            content="x",
            translation_status=TRANSLATION_STATUS_PUBLISHED,
            source_language="de",
            translated_at=now,
        )
        db.session.add(t)
        db.session.commit()
        assert ns.get_news_by_slug("inconsistent-slug") is None


def test_get_news_by_slug_skips_empty_try_lang(app):
    with app.app_context():
        with patch.object(ns, "get_default_language", return_value=""):
            assert ns.get_news_by_slug("any-slug") is None


def test_list_news_published_skips_non_published_translation(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
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
        t = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="Approved only",
            slug="approved-only-pub",
            content="body",
            translation_status=TRANSLATION_STATUS_APPROVED,
            source_language="de",
            translated_at=now,
        )
        db.session.add(t)
        db.session.commit()

        items, _ = ns.list_news(published_only=True, lang="de")
        assert article.id not in {x["id"] for x in items}


def test_list_news_editorial_item_has_status_map_and_default_lang(app, sample_news):
    _pub1, _pub2, draft_article = sample_news
    with app.app_context():
        items, _ = ns.list_news(published_only=False, lang="de")
        draft_rows = [x for x in items if x["id"] == draft_article.id]
        assert len(draft_rows) == 1
        row = draft_rows[0]
        assert "translation_statuses" in row
        assert "default_language" in row
        assert row["default_language"] == "de"
        assert isinstance(row["translation_statuses"], dict)


def test_list_news_sort_col_none_fallback_uses_created_at(app, sample_news):
    def _getattr(obj, name, default=None):
        from app.models import NewsArticle

        if obj is NewsArticle and name == "published_at":
            return None
        return builtins.getattr(obj, name, default)

    with app.app_context():
        with patch("app.services.news_service.getattr", side_effect=_getattr):
            items, total = ns.list_news(published_only=True, sort="published_at", lang="de")
        assert total >= 1
        assert all("id" in x for x in items)


def test_create_news_validation_errors(app, test_user):
    with app.app_context():
        assert "Title" in (ns.create_news("  ", "a-slug", "body")[1] or "")
        long_title = "T" * (ns.TITLE_MAX_LENGTH + 1)
        assert "Title" in (ns.create_news(long_title, "a-slug", "body")[1] or "")
        assert "Content" in (ns.create_news("Ok", "ok-slug", "  ")[1] or "")
        assert "Slug" in (ns.create_news("Ok", "", "body")[1] or "")
        long_slug = "a-" * 200
        assert "Slug" in (ns.create_news("Ok", long_slug, "body")[1] or "")
        assert "Summary" in (
            ns.create_news("Ok", "ok-slug-2", "body", summary="S" * (ns.SUMMARY_MAX_LENGTH + 1))[1] or ""
        )
        assert "Category" in (
            ns.create_news("Ok", "ok-slug-3", "body", category="C" * (ns.CATEGORY_MAX_LENGTH + 1))[1] or ""
        )
        assert "Cover image" in (
            ns.create_news("Ok", "ok-slug-4", "body", cover_image="U" * (ns.COVER_IMAGE_MAX_LENGTH + 1))[1]
            or ""
        )


def test_update_news_errors_and_outdated_and_object_arg(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        empty = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            created_at=now,
            updated_at=now,
        )
        db.session.add(empty)
        db.session.flush()
        db.session.commit()
        _, err_missing = ns.update_news(empty.id, title="X")
        assert "Default translation not found" in (err_missing or "")

        base, _ = ns.create_news("B1", "b1-slug", "body", is_published=False)
        long_title = "L" * (ns.TITLE_MAX_LENGTH + 1)
        _, err_tl = ns.update_news(base.id, title=long_title)
        assert "Title" in (err_tl or "")

        other, _ = ns.create_news("B2", "b2-slug", "body", is_published=False)
        _, err_dup = ns.update_news(base.id, slug="b2-slug")
        assert "Slug already" in (err_dup or "")

        _, err_sum = ns.update_news(base.id, summary="S" * (ns.SUMMARY_MAX_LENGTH + 1))
        assert "Summary" in (err_sum or "")

        _, err_co = ns.update_news(base.id, content="   ")
        assert "empty" in (err_co or "").lower()

        long_url = "https://x.com/" + "u" * ns.COVER_IMAGE_MAX_LENGTH
        _, err_cv = ns.update_news(base.id, cover_image=long_url)
        assert "Cover image" in (err_cv or "")

        _, err_cat = ns.update_news(base.id, category="Z" * (ns.CATEGORY_MAX_LENGTH + 1))
        assert "Category" in (err_cat or "")

        ns.upsert_article_translation(base.id, "en", title="En", slug="b1-en", content="en body")
        db.session.refresh(base)
        art, err_ok = ns.update_news(base, title="Updated base")
        assert err_ok is None and art
        t_en = ns.get_article_translation(base.id, "en")
        assert t_en and t_en.translation_status == TRANSLATION_STATUS_OUTDATED

        _, err_slug_long = ns.update_news(base.id, slug="a-" * 200)
        assert "Slug" in (err_slug_long or "")

        a3, _ = ns.create_news("B3", "b3-slug", "body", is_published=False, default_language="de")
        ok3, _ = ns.update_news(a3.id, default_language="en")
        db.session.refresh(ok3)
        assert ok3.default_language == "en"


def test_publish_news_keeps_existing_published_at(app, test_user):
    with app.app_context():
        user, _ = test_user
        # ORM/SQLite may round-trip as naive datetime
        fixed = datetime(2020, 1, 15, 0, 0, 0)
        now = datetime.now(timezone.utc)
        article = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            created_at=now,
            updated_at=now,
            published_at=fixed,
        )
        db.session.add(article)
        db.session.flush()
        t = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="P",
            slug="pub-at-slug",
            content="c",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add(t)
        db.session.commit()

        ns.publish_news(article.id)
        db.session.refresh(article)
        assert article.published_at == fixed


def test_mark_article_translations_outdated_no_exclude(app, test_user):
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
            slug="all-out-1",
            content="c",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        t_en = NewsArticleTranslation(
            article_id=article.id,
            language_code="en",
            title="T2",
            slug="all-out-2",
            content="c2",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add_all([t_de, t_en])
        db.session.commit()

        ns.mark_article_translations_outdated(article.id)
        db.session.refresh(t_de)
        db.session.refresh(t_en)
        assert t_de.translation_status == TRANSLATION_STATUS_OUTDATED
        assert t_en.translation_status == TRANSLATION_STATUS_OUTDATED


def test_upsert_article_translation_update_errors_and_create_edges(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        a1 = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            created_at=now,
            updated_at=now,
        )
        a2 = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            created_at=now,
            updated_at=now,
        )
        db.session.add_all([a1, a2])
        db.session.flush()
        t1 = NewsArticleTranslation(
            article_id=a1.id,
            language_code="de",
            title="A1",
            slug="a1-de",
            content="c",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        t2 = NewsArticleTranslation(
            article_id=a2.id,
            language_code="en",
            title="A2",
            slug="shared-en-slug",
            content="c2",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add_all([t1, t2])
        db.session.commit()

        _, err_title = ns.upsert_article_translation(
            a1.id, "de", title="X" * (ns.TITLE_MAX_LENGTH + 1)
        )
        assert "Title" in (err_title or "")

        _, err_slug_bad = ns.upsert_article_translation(a1.id, "de", slug="@@@")
        assert "Slug" in (err_slug_bad or "")

        ns.upsert_article_translation(a1.id, "en", title="E1", slug="e1-only", content="e")
        _, err_slug_dup = ns.upsert_article_translation(
            a1.id, "en", slug="shared-en-slug"
        )
        assert "Slug already" in (err_slug_dup or "")

        _, err_sum = ns.upsert_article_translation(
            a1.id, "en", summary="S" * (ns.SUMMARY_MAX_LENGTH + 1)
        )
        assert "Summary" in (err_sum or "")

        a3 = NewsArticle(
            author_id=user.id,
            status="draft",
            default_language="de",
            created_at=now,
            updated_at=now,
        )
        db.session.add(a3)
        db.session.flush()
        t3 = NewsArticleTranslation(
            article_id=a3.id,
            language_code="de",
            title="A3",
            slug="a3-de",
            content="c",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add(t3)
        db.session.commit()

        _, err_slug_req = ns.upsert_article_translation(
            a3.id, "en", title="@@@", content="has content", slug=None
        )
        assert "Slug is required" in (err_slug_req or "")

        tr_draft, _ = ns.upsert_article_translation(
            a3.id,
            "en",
            title="Fr",
            slug="fr-new-en",
            content="fr body",
            translation_status="not-a-real-status",
        )
        assert tr_draft.translation_status == TRANSLATION_STATUS_MACHINE_DRAFT


def test_upsert_default_language_marks_other_translations_outdated(app, test_user):
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
            slug="de-src",
            content="de body",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        t_en = NewsArticleTranslation(
            article_id=article.id,
            language_code="en",
            title="EN",
            slug="en-other",
            content="en body",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add_all([t_de, t_en])
        db.session.commit()

        ns.upsert_article_translation(article.id, "de", content="changed default")
        db.session.refresh(t_de)
        db.session.refresh(t_en)
        assert t_en.translation_status == TRANSLATION_STATUS_OUTDATED
        assert t_de.translation_status == "approved"


def test_get_suggested_threads_for_article_with_tags_and_mock(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        cat = ForumCategory(
            slug="sug-cat",
            title="Sug",
            is_active=True,
            is_private=False,
            required_role=None,
        )
        db.session.add(cat)
        db.session.flush()
        primary = ForumThread(
            category_id=cat.id,
            slug="primary-sug-thread",
            title="Primary",
            status="open",
            author_id=user.id,
        )
        linked = ForumThread(
            category_id=cat.id,
            slug="linked-sug-thread",
            title="Linked",
            status="open",
            author_id=user.id,
        )
        db.session.add_all([primary, linked])
        db.session.flush()
        tag = ForumTag(slug="news-tag", label="NewsTag", created_at=now)
        db.session.add(tag)
        db.session.flush()
        db.session.add(ForumThreadTag(thread_id=primary.id, tag_id=tag.id))

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
        db.session.add(NewsArticleForumThread(article_id=article.id, thread_id=linked.id))
        trans = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="Sug news",
            slug="sug-news-article",
            content="x",
            translation_status=TRANSLATION_STATUS_PUBLISHED,
            source_language="de",
            translated_at=now,
        )
        db.session.add(trans)
        db.session.commit()

        fake = [{"id": 999, "slug": "mock"}]
        with patch(
            "app.services.forum_service.suggest_related_threads_for_query",
            return_value=fake,
        ) as m:
            out = ns.get_suggested_threads_for_article(article.id, limit=3)
        assert out == fake
        call_kw = m.call_args.kwargs
        assert call_kw["query_tags"] == ["NewsTag"]
        assert primary.id in call_kw["exclude_thread_ids"]
        assert linked.id in call_kw["exclude_thread_ids"]


def test_translation_to_dict_shape(app, test_user):
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
            title="Dict",
            slug="dict-slug",
            content="c",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add(t)
        db.session.commit()
        d = ns._translation_to_dict(t)
        assert d["slug"] == "dict-slug"
        assert d["translation_status"] == "approved"


def test_get_effective_translation_default_lang_lookup_misses(app, test_user):
    """Covers 84–88 when default_lang != lang but second lookup returns None."""
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
        db.session.commit()
        assert ns._get_effective_translation(article, "en") is None


def test_list_news_skips_article_without_translation(app, test_user):
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
        db.session.commit()
        items, _ = ns.list_news(published_only=False, lang="de")
        assert article.id not in {x["id"] for x in items}


def test_get_news_by_id_returns_public_dict(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
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
        db.session.add(
            NewsArticleTranslation(
                article_id=article.id,
                language_code="de",
                title="By id",
                slug="by-id-slug",
                content="x",
                translation_status=TRANSLATION_STATUS_PUBLISHED,
                source_language="de",
                translated_at=now,
            )
        )
        db.session.commit()
        d = ns.get_news_by_id(article.id, lang="de")
        assert d and d["id"] == article.id and d["slug"] == "by-id-slug"


def test_get_news_by_slug_returns_dict_when_published(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
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
        t = NewsArticleTranslation(
            article_id=article.id,
            language_code="de",
            title="Live",
            slug="live-pub-slug",
            content="x",
            translation_status=TRANSLATION_STATUS_PUBLISHED,
            source_language="de",
            translated_at=now,
        )
        db.session.add(t)
        db.session.commit()
        d = ns.get_news_by_slug("live-pub-slug")
        assert d and d["slug"] == "live-pub-slug"


def test_update_news_not_found_and_clear_optional_fields(app, test_user):
    with app.app_context():
        _, err = ns.update_news(999_999_999, title="Nope")
        assert "not found" in (err or "").lower()

        a, _ = ns.create_news("Clr", "clr-slug", "body", is_published=False, cover_image="https://x.com/i.png")
        ok, err2 = ns.update_news(a.id, cover_image="", category="")
        assert err2 is None and ok
        db.session.refresh(ok)
        assert ok.cover_image is None
        assert ok.category is None


def test_update_news_slug_success_and_default_language_invalid_normalized(app, test_user):
    with app.app_context():
        a, _ = ns.create_news("S1", "s1-slug", "body", is_published=False, summary="keep")
        ok, err = ns.update_news(a.id, slug="s1-new-slug")
        assert err is None
        db.session.refresh(ok)
        trans = ns._get_translation_for_lang(a.id, "de")
        assert trans and trans.slug == "s1-new-slug"

        _, err2 = ns.update_news(a.id, default_language="not-a-lang")
        assert err2 is None

        ok3, err3 = ns.update_news(a.id, summary="", content="replaced-body")
        assert err3 is None
        db.session.refresh(trans)
        assert trans.summary is None
        assert trans.content == "replaced-body"


def test_delete_publish_unpublish_errors(app):
    with app.app_context():
        ok, err = ns.delete_news(999_999_999)
        assert not ok and "not found" in (err or "").lower()
        _, errp = ns.publish_news(999_999_999)
        assert "not found" in (errp or "").lower()
        _, erru = ns.unpublish_news(999_999_999)
        assert "not found" in (erru or "").lower()


def test_list_article_translations_not_found(app):
    with app.app_context():
        rows, err = ns.list_article_translations(999_999_999)
        assert rows is None and "not found" in (err or "").lower()


def test_upsert_article_not_found(app):
    with app.app_context():
        _, err = ns.upsert_article_translation(999_999_999, "de", title="X", content="Y")
        assert "not found" in (err or "").lower()


def test_upsert_update_title_strip_fallback_and_seo_and_status(app, test_user):
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
            title="KeepMe",
            slug="seo-slug",
            content="c",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add(t)
        db.session.commit()

        tr, err = ns.upsert_article_translation(article.id, "de", title="   ", seo_title=" ST ", seo_description=" SD ")
        assert err is None and tr.title == "KeepMe"
        assert tr.seo_title == "ST"
        assert tr.seo_description == "SD"

        tr2, err2 = ns.upsert_article_translation(
            article.id, "de", translation_status=TRANSLATION_STATUS_PUBLISHED
        )
        assert err2 is None and tr2.translation_status == TRANSLATION_STATUS_PUBLISHED

        tr3, err3 = ns.upsert_article_translation(article.id, "de", slug="seo-slug-renamed")
        assert err3 is None and tr3.slug == "seo-slug-renamed"


def test_upsert_update_non_default_language_no_outdated_mark(app, test_user):
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
            slug="nde-de",
            content="de",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        t_en = NewsArticleTranslation(
            article_id=article.id,
            language_code="en",
            title="EN",
            slug="nde-en",
            content="en",
            translation_status="approved",
            source_language="de",
            translated_at=now,
        )
        db.session.add_all([t_de, t_en])
        db.session.commit()

        ns.upsert_article_translation(article.id, "en", content="en changed")
        db.session.refresh(t_de)
        db.session.refresh(t_en)
        assert t_de.translation_status == "approved"
        assert t_en.translation_status == "approved"


def test_upsert_create_duplicate_slug_cross_article(app, test_user):
    with app.app_context():
        a1, _ = ns.create_news("U1", "u1-slug-x", "b", is_published=False)
        a2, _ = ns.create_news("U2", "u2-slug-x", "b", is_published=False)
        ns.upsert_article_translation(a1.id, "en", title="E1", slug="dup-en-slug", content="e1")
        _, err = ns.upsert_article_translation(
            a2.id, "en", title="E2", slug="dup-en-slug", content="e2"
        )
        assert "Slug already" in (err or "")


def test_translation_workflow_not_found(app):
    with app.app_context():
        _, e1 = ns.submit_review_article_translation(999_999_999, "de")
        assert "not found" in (e1 or "").lower()
        _, e2 = ns.approve_article_translation(999_999_999, "de")
        assert "not found" in (e2 or "").lower()
        _, e3 = ns.publish_article_translation(999_999_999, "de")
        assert "not found" in (e3 or "").lower()


def test_get_suggested_threads_no_discussion_thread(app, test_user):
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)
        article = NewsArticle(
            author_id=user.id,
            status="published",
            default_language="de",
            discussion_thread_id=None,
            created_at=now,
            updated_at=now,
            published_at=now,
        )
        db.session.add(article)
        db.session.flush()
        db.session.add(
            NewsArticleTranslation(
                article_id=article.id,
                language_code="de",
                title="No disc",
                slug="no-disc-sug",
                content="x",
                translation_status=TRANSLATION_STATUS_PUBLISHED,
                source_language="de",
                translated_at=now,
            )
        )
        db.session.commit()
        with patch("app.services.forum_service.suggest_related_threads_for_query", return_value=[]):
            assert ns.get_suggested_threads_for_article(article.id) == []
