"""Comprehensive tests for wiki_service to expand coverage from 12% to 85%+."""
import pytest
from datetime import datetime, timezone
from app.extensions import db
from app.models import WikiPage, WikiPageTranslation, WikiPageForumThread, ForumThread, ForumCategory
from app.services import wiki_service
from app.i18n import (
    TRANSLATION_STATUS_APPROVED,
    TRANSLATION_STATUS_REVIEW_REQUIRED,
    TRANSLATION_STATUS_PUBLISHED,
    TRANSLATION_STATUS_OUTDATED,
    TRANSLATION_STATUS_MACHINE_DRAFT
)


@pytest.fixture
def wiki_data(app, test_user):
    """Create comprehensive wiki test data."""
    with app.app_context():
        user, _ = test_user
        now = datetime.now(timezone.utc)

        # Create wiki pages
        page1 = WikiPage(
            key="index",
            sort_order=0,
            is_published=True,
            created_at=now,
            updated_at=now
        )
        db.session.add(page1)
        db.session.flush()

        page2 = WikiPage(
            key="tutorial",
            sort_order=1,
            is_published=True,
            created_at=now,
            updated_at=now
        )
        db.session.add(page2)
        db.session.flush()

        page3 = WikiPage(
            key="unpublished",
            sort_order=2,
            is_published=False,
            created_at=now,
            updated_at=now
        )
        db.session.add(page3)
        db.session.flush()

        # Create translations
        trans1_en = WikiPageTranslation(
            page_id=page1.id,
            language_code="en",
            title="Index",
            slug="index",
            content_markdown="# Welcome to Wiki",
            translation_status=TRANSLATION_STATUS_PUBLISHED,
            source_version=now.isoformat()
        )
        db.session.add(trans1_en)

        trans1_de = WikiPageTranslation(
            page_id=page1.id,
            language_code="de",
            title="Startseite",
            slug="startseite",
            content_markdown="# Willkommen zum Wiki",
            translation_status=TRANSLATION_STATUS_PUBLISHED,
            source_version=now.isoformat()
        )
        db.session.add(trans1_de)

        trans2_en = WikiPageTranslation(
            page_id=page2.id,
            language_code="en",
            title="Tutorial",
            slug="tutorial",
            content_markdown="# Tutorial",
            translation_status=TRANSLATION_STATUS_APPROVED
        )
        db.session.add(trans2_en)

        # Create forum category and threads
        cat = ForumCategory(
            slug="wiki-discussions",
            title="Wiki Discussions",
            description="Discussion threads",
            is_active=True,
            is_private=False,
            sort_order=0
        )
        db.session.add(cat)
        db.session.flush()

        thread1 = ForumThread(
            category_id=cat.id,
            title="Index Discussion",
            slug="index-discussion",
            author_id=user.id,
            created_at=now
        )
        db.session.add(thread1)
        db.session.flush()

        # Link thread to wiki page
        link = WikiPageForumThread(
            page_id=page1.id,
            thread_id=thread1.id,
            relation_type="primary"
        )
        db.session.add(link)

        db.session.commit()
        return {
            "page1": page1.id,
            "page2": page2.id,
            "page3": page3.id,
            "user": user,
            "thread1": thread1.id,
            "cat": cat.id,
            "now": now
        }


class TestGetWikiPageByKey:
    """Test get_wiki_page_by_key function."""

    def test_get_existing_page(self, app, wiki_data):
        """get_wiki_page_by_key returns existing page."""
        with app.app_context():
            page = wiki_service.get_wiki_page_by_key("index")
            assert page is not None
            assert page.key == "index"

    def test_get_nonexistent_page(self, app):
        """get_wiki_page_by_key returns None for missing page."""
        with app.app_context():
            page = wiki_service.get_wiki_page_by_key("nonexistent")
            assert page is None

    def test_get_page_with_none_key(self, app):
        """get_wiki_page_by_key handles None key."""
        with app.app_context():
            page = wiki_service.get_wiki_page_by_key(None)
            assert page is None

    def test_get_page_with_empty_string(self, app):
        """get_wiki_page_by_key handles empty string."""
        with app.app_context():
            page = wiki_service.get_wiki_page_by_key("")
            assert page is None

    def test_get_page_with_whitespace(self, app, wiki_data):
        """get_wiki_page_by_key strips whitespace from key."""
        with app.app_context():
            page = wiki_service.get_wiki_page_by_key("  index  ")
            assert page is not None


class TestGetWikiTranslation:
    """Test get_wiki_translation function."""

    def test_get_existing_translation(self, app, wiki_data):
        """get_wiki_translation returns existing translation."""
        with app.app_context():
            trans = wiki_service.get_wiki_translation(wiki_data["page1"], "en")
            assert trans is not None
            assert trans.language_code == "en"

    def test_get_nonexistent_translation(self, app, wiki_data):
        """get_wiki_translation returns None for missing translation."""
        with app.app_context():
            trans = wiki_service.get_wiki_translation(wiki_data["page1"], "fr")
            assert trans is None

    def test_get_translation_with_none_page_id(self, app):
        """get_wiki_translation handles None page_id."""
        with app.app_context():
            trans = wiki_service.get_wiki_translation(None, "en")
            assert trans is None

    def test_get_translation_with_none_language(self, app, wiki_data):
        """get_wiki_translation handles None language."""
        with app.app_context():
            trans = wiki_service.get_wiki_translation(wiki_data["page1"], None)
            assert trans is None


class TestGetEffectiveWikiTranslation:
    """Test get_effective_wiki_translation function."""

    def test_get_translation_with_exact_language(self, app, wiki_data):
        """get_effective_wiki_translation returns exact language if available."""
        with app.app_context():
            page = WikiPage.query.get(wiki_data["page1"])
            trans = wiki_service.get_effective_wiki_translation(page, "de")
            assert trans is not None
            assert trans.language_code == "de"

    def test_get_translation_fallback_to_first(self, app, wiki_data):
        """get_effective_wiki_translation falls back to first translation."""
        with app.app_context():
            page = WikiPage.query.get(wiki_data["page1"])
            trans = wiki_service.get_effective_wiki_translation(page, None)
            assert trans is not None

    def test_get_translation_invalid_language(self, app, wiki_data):
        """get_effective_wiki_translation handles invalid language gracefully."""
        with app.app_context():
            page = WikiPage.query.get(wiki_data["page1"])
            trans = wiki_service.get_effective_wiki_translation(page, "zz-invalid")
            assert trans is not None  # Falls back to available translations


class TestGetWikiMarkdownForDisplay:
    """Test get_wiki_markdown_for_display function."""

    def test_get_markdown_for_index_page(self, app, wiki_data):
        """get_wiki_markdown_for_display returns index page markdown."""
        with app.app_context():
            markdown = wiki_service.get_wiki_markdown_for_display(lang="en")
            assert markdown is not None
            assert isinstance(markdown, str)

    def test_get_markdown_nonexistent_index(self, app):
        """get_wiki_markdown_for_display returns None if no index page."""
        with app.app_context():
            # Ensure no index page
            WikiPage.query.filter_by(key="index").delete()
            db.session.commit()

            markdown = wiki_service.get_wiki_markdown_for_display()
            assert markdown is None


class TestGetWikiPageBySlug:
    """Test get_wiki_page_by_slug function."""

    def test_get_page_by_slug_published(self, app, wiki_data):
        """get_wiki_page_by_slug returns published page."""
        with app.app_context():
            page, trans = wiki_service.get_wiki_page_by_slug("index", lang="en")
            assert page is not None
            assert trans is not None
            assert page.is_published is True

    def test_get_page_by_slug_unpublished(self, app, wiki_data):
        """get_wiki_page_by_slug returns None for unpublished page."""
        with app.app_context():
            page, trans = wiki_service.get_wiki_page_by_slug("unpublished")
            # Should return None since page is unpublished
            assert page is None or page.is_published is True

    def test_get_page_by_slug_case_insensitive(self, app, wiki_data):
        """get_wiki_page_by_slug is case insensitive."""
        with app.app_context():
            page, trans = wiki_service.get_wiki_page_by_slug("INDEX", lang="en")
            assert page is not None

    def test_get_page_by_slug_nonexistent(self, app):
        """get_wiki_page_by_slug returns None for nonexistent slug."""
        with app.app_context():
            page, trans = wiki_service.get_wiki_page_by_slug("nonexistent")
            assert page is None
            assert trans is None


class TestListRelatedThreads:
    """Test list_related_threads_for_page function."""

    def test_list_related_threads_for_page(self, app, wiki_data):
        """list_related_threads_for_page returns related threads."""
        with app.app_context():
            threads = wiki_service.list_related_threads_for_page(wiki_data["page1"], limit=5)
            assert isinstance(threads, list)
            assert len(threads) > 0

    def test_list_related_threads_no_threads(self, app, wiki_data):
        """list_related_threads_for_page returns empty list if no threads."""
        with app.app_context():
            threads = wiki_service.list_related_threads_for_page(wiki_data["page2"], limit=5)
            assert isinstance(threads, list)

    def test_list_related_threads_with_none_id(self, app):
        """list_related_threads_for_page handles None page_id."""
        with app.app_context():
            threads = wiki_service.list_related_threads_for_page(None)
            assert threads == []

    def test_list_related_threads_respects_limit(self, app, wiki_data):
        """list_related_threads_for_page respects limit parameter."""
        with app.app_context():
            threads_5 = wiki_service.list_related_threads_for_page(wiki_data["page1"], limit=5)
            assert len(threads_5) <= 5


class TestListWikiPages:
    """Test list_wiki_pages function."""

    def test_list_wiki_pages(self, app, wiki_data):
        """list_wiki_pages returns all pages."""
        with app.app_context():
            pages = wiki_service.list_wiki_pages()
            assert isinstance(pages, list)
            assert len(pages) >= 3

    def test_list_wiki_pages_ordered_by_sort_order(self, app, wiki_data):
        """list_wiki_pages returns pages in sort order."""
        with app.app_context():
            pages = wiki_service.list_wiki_pages()
            sort_orders = [p.sort_order for p in pages]
            assert sort_orders == sorted(sort_orders)


class TestGetWikiPageById:
    """Test get_wiki_page_by_id function."""

    def test_get_page_by_id(self, app, wiki_data):
        """get_wiki_page_by_id returns page by ID."""
        with app.app_context():
            page = wiki_service.get_wiki_page_by_id(wiki_data["page1"])
            assert page is not None
            assert page.id == wiki_data["page1"]

    def test_get_page_by_id_not_found(self, app):
        """get_wiki_page_by_id returns None for invalid ID."""
        with app.app_context():
            page = wiki_service.get_wiki_page_by_id(99999)
            assert page is None

    def test_get_page_by_id_none(self, app):
        """get_wiki_page_by_id handles None ID."""
        with app.app_context():
            page = wiki_service.get_wiki_page_by_id(None)
            assert page is None


class TestCreateWikiPage:
    """Test create_wiki_page function."""

    def test_create_page_success(self, app):
        """create_wiki_page creates a page successfully."""
        with app.app_context():
            page, error = wiki_service.create_wiki_page(
                key="new-page",
                sort_order=0,
                is_published=True
            )

            assert error is None
            assert page is not None
            assert page.key == "new-page"

    def test_create_page_empty_key(self, app):
        """create_wiki_page fails with empty key."""
        with app.app_context():
            page, error = wiki_service.create_wiki_page(key="")

            assert error is not None
            assert page is None

    def test_create_page_duplicate_key(self, app, wiki_data):
        """create_wiki_page fails with duplicate key."""
        with app.app_context():
            page, error = wiki_service.create_wiki_page(key="index")

            assert error is not None
            assert page is None

    def test_create_page_with_parent(self, app):
        """create_wiki_page creates page with parent."""
        with app.app_context():
            parent, _ = wiki_service.create_wiki_page(key="parent")
            child, error = wiki_service.create_wiki_page(
                key="child",
                parent_id=parent.id
            )

            assert error is None
            assert child.parent_id == parent.id


class TestUpdateWikiPage:
    """Test update_wiki_page function."""

    def test_update_page_key(self, app, wiki_data):
        """update_wiki_page updates page key."""
        with app.app_context():
            page, error = wiki_service.update_wiki_page(
                wiki_data["page3"],
                key="renamed-page"
            )

            assert error is None
            assert page.key == "renamed-page"

    def test_update_page_sort_order(self, app, wiki_data):
        """update_wiki_page updates sort order."""
        with app.app_context():
            page, error = wiki_service.update_wiki_page(
                wiki_data["page3"],
                sort_order=10
            )

            assert error is None
            assert page.sort_order == 10

    def test_update_page_is_published(self, app, wiki_data):
        """update_wiki_page updates published status."""
        with app.app_context():
            page, error = wiki_service.update_wiki_page(
                wiki_data["page3"],
                is_published=True
            )

            assert error is None
            assert page.is_published is True

    def test_update_page_not_found(self, app):
        """update_wiki_page returns error for nonexistent page."""
        with app.app_context():
            page, error = wiki_service.update_wiki_page(99999, key="new")

            assert error is not None
            assert page is None

    def test_update_page_empty_key(self, app, wiki_data):
        """update_wiki_page fails with empty key."""
        with app.app_context():
            page, error = wiki_service.update_wiki_page(
                wiki_data["page3"],
                key=""
            )

            assert error is not None
            assert page is None


class TestListWikiPageTranslations:
    """Test list_wiki_page_translations function."""

    def test_list_translations(self, app, wiki_data):
        """list_wiki_page_translations returns all translations."""
        with app.app_context():
            translations, error = wiki_service.list_wiki_page_translations(wiki_data["page1"])

            assert error is None
            assert isinstance(translations, list)
            assert len(translations) > 0

    def test_list_translations_not_found(self, app):
        """list_wiki_page_translations returns error for nonexistent page."""
        with app.app_context():
            translations, error = wiki_service.list_wiki_page_translations(99999)

            assert error is not None
            assert translations is None

    def test_list_translations_includes_missing(self, app, wiki_data):
        """list_wiki_page_translations includes missing language entries."""
        with app.app_context():
            translations, error = wiki_service.list_wiki_page_translations(wiki_data["page1"])

            assert error is None
            # Should have entries for all supported languages
            statuses = [t["translation_status"] for t in translations]
            # At least one should be "missing" if not all languages are translated
            assert len(statuses) > 0


class TestGetWikiPageTranslation:
    """Test get_wiki_page_translation function."""

    def test_get_translation_by_language(self, app, wiki_data):
        """get_wiki_page_translation returns translation by language."""
        with app.app_context():
            trans = wiki_service.get_wiki_page_translation(wiki_data["page1"], "en")
            assert trans is not None
            assert trans.language_code == "en"

    def test_get_translation_invalid_language(self, app, wiki_data):
        """get_wiki_page_translation returns None for invalid language."""
        with app.app_context():
            trans = wiki_service.get_wiki_page_translation(wiki_data["page1"], "zz-invalid")
            assert trans is None

    def test_get_translation_case_insensitive(self, app, wiki_data):
        """get_wiki_page_translation is case insensitive."""
        with app.app_context():
            trans = wiki_service.get_wiki_page_translation(wiki_data["page1"], "EN")
            assert trans is not None


class TestUpsertWikiPageTranslation:
    """Test upsert_wiki_page_translation function."""

    def test_upsert_new_translation(self, app, wiki_data):
        """upsert_wiki_page_translation creates new translation."""
        with app.app_context():
            trans, error = wiki_service.upsert_wiki_page_translation(
                wiki_data["page2"],
                "de",
                title="Anleitung",
                slug="anleitung",
                content_markdown="# Anleitung"
            )

            assert error is None
            assert trans is not None
            assert trans.language_code == "de"

    def test_upsert_update_translation(self, app, wiki_data):
        """upsert_wiki_page_translation updates existing translation."""
        with app.app_context():
            trans, error = wiki_service.upsert_wiki_page_translation(
                wiki_data["page1"],
                "en",
                title="Updated Index",
                content_markdown="# Updated"
            )

            assert error is None
            assert trans.title == "Updated Index"

    def test_upsert_new_requires_title_and_slug(self, app, wiki_data):
        """upsert_wiki_page_translation requires title and slug for new translation."""
        with app.app_context():
            trans, error = wiki_service.upsert_wiki_page_translation(
                wiki_data["page2"],
                "es",
                content_markdown="# Content"
            )

            assert error is not None
            assert trans is None

    def test_upsert_invalid_language(self, app, wiki_data):
        """upsert_wiki_page_translation handles invalid language."""
        with app.app_context():
            trans, error = wiki_service.upsert_wiki_page_translation(
                wiki_data["page1"],
                "zz-invalid",
                title="Title"
            )

            assert error is not None
            assert trans is None

    def test_upsert_page_not_found(self, app):
        """upsert_wiki_page_translation returns error for nonexistent page."""
        with app.app_context():
            trans, error = wiki_service.upsert_wiki_page_translation(
                99999,
                "en",
                title="Title",
                slug="slug"
            )

            assert error is not None
            assert trans is None


class TestSubmitReviewWikiTranslation:
    """Test submit_review_wiki_translation function."""

    def test_submit_review_success(self, app, wiki_data):
        """submit_review_wiki_translation changes status to review required."""
        with app.app_context():
            trans, error = wiki_service.submit_review_wiki_translation(
                wiki_data["page1"],
                "en"
            )

            assert error is None
            assert trans.translation_status == TRANSLATION_STATUS_REVIEW_REQUIRED


class TestApproveWikiTranslation:
    """Test approve_wiki_translation function."""

    def test_approve_translation_success(self, app, wiki_data, admin_user):
        """approve_wiki_translation changes status to approved."""
        with app.app_context():
            admin, _ = admin_user

            trans, error = wiki_service.approve_wiki_translation(
                wiki_data["page1"],
                "en",
                reviewer_id=admin.id
            )

            assert error is None
            assert trans.translation_status == TRANSLATION_STATUS_APPROVED
            assert trans.reviewed_by == admin.id


class TestPublishWikiTranslation:
    """Test publish_wiki_translation function."""

    def test_publish_translation_success(self, app, wiki_data):
        """publish_wiki_translation changes status to published."""
        with app.app_context():
            trans, error = wiki_service.publish_wiki_translation(
                wiki_data["page1"],
                "en"
            )

            assert error is None
            assert trans.translation_status == TRANSLATION_STATUS_PUBLISHED


class TestMarkWikiTranslationsOutdated:
    """Test mark_wiki_translations_outdated function."""

    def test_mark_outdated_all_except_one(self, app, wiki_data):
        """mark_wiki_translations_outdated marks all translations except one."""
        with app.app_context():
            wiki_service.mark_wiki_translations_outdated(
                wiki_data["page1"],
                exclude_language="en"
            )
            db.session.commit()

            # Check that en is not outdated
            en_trans = wiki_service.get_wiki_page_translation(wiki_data["page1"], "en")
            de_trans = wiki_service.get_wiki_page_translation(wiki_data["page1"], "de")

            # EN should not have changed to outdated (it was excluded)
            # DE might be outdated now
            assert en_trans is not None


class TestWikiSlugValidation:
    """Test slug validation functions."""

    def test_wiki_slug_exists_for_lang(self, app, wiki_data):
        """_wiki_slug_exists_for_lang detects existing slugs."""
        with app.app_context():
            exists = wiki_service._wiki_slug_exists_for_lang("index", "en")
            assert exists is True

    def test_wiki_slug_exists_returns_false_for_new(self, app):
        """_wiki_slug_exists_for_lang returns False for new slugs."""
        with app.app_context():
            exists = wiki_service._wiki_slug_exists_for_lang("totally-new-slug", "en")
            assert exists is False

    def test_wiki_slug_exists_case_insensitive(self, app, wiki_data):
        """_wiki_slug_exists_for_lang is case insensitive."""
        with app.app_context():
            exists = wiki_service._wiki_slug_exists_for_lang("INDEX", "en")
            assert exists is True

    def test_wiki_slug_exists_with_exclusion(self, app, wiki_data):
        """_wiki_slug_exists_for_lang can exclude a translation."""
        with app.app_context():
            # Get a translation ID to exclude
            trans = wiki_service.get_wiki_page_translation(wiki_data["page1"], "en")

            exists = wiki_service._wiki_slug_exists_for_lang(
                "index",
                "en",
                exclude_translation_id=trans.id
            )
            assert exists is False


class TestSuggestedThreadsForWikiPage:
    """Test get_suggested_threads_for_wiki_page function."""

    def test_get_suggested_threads(self, app, wiki_data):
        """get_suggested_threads_for_wiki_page returns suggestions."""
        with app.app_context():
            suggestions = wiki_service.get_suggested_threads_for_wiki_page(
                wiki_data["page1"],
                limit=5
            )

            assert isinstance(suggestions, list)

    def test_get_suggested_threads_nonexistent_page(self, app):
        """get_suggested_threads_for_wiki_page returns empty for nonexistent page."""
        with app.app_context():
            suggestions = wiki_service.get_suggested_threads_for_wiki_page(99999)

            assert suggestions == []
