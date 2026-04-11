"""Validation for ``news_service.upsert_article_translation`` (DS-005 — control-flow extraction)."""

from __future__ import annotations

from typing import Any, Callable

from app.i18n import TRANSLATION_STATUSES, TRANSLATION_STATUS_MACHINE_DRAFT

from app.services.news_service_create_guards import (
    SUMMARY_MAX_LENGTH,
    TITLE_MAX_LENGTH,
    normalize_news_slug,
)

SlugExistsExcludingArticle = Callable[[str, str, int], bool]
SlugExistsGlobal = Callable[[str, str], bool]


def validate_upsert_translation_update_patch(
    *,
    title: str | None,
    slug: str | None,
    summary: str | None,
    content: str | None,
    seo_title: str | None,
    seo_description: str | None,
    translation_status: str | None,
    existing_title: str,
    existing_content: str,
    article_id: int,
    lang: str,
    slug_exists_excluding_article: SlugExistsExcludingArticle,
) -> tuple[dict[str, Any] | None, str | None]:
    """Build validated field updates for an existing translation row."""
    patch: dict[str, Any] = {}

    if title is not None:
        new_title = (title or "").strip() or existing_title
        if len(new_title) > TITLE_MAX_LENGTH:
            return None, f"Title must be at most {TITLE_MAX_LENGTH} characters"
        patch["title"] = new_title

    if slug is not None:
        slug_norm = normalize_news_slug(slug)
        if not slug_norm:
            return None, "Slug must be alphanumeric with hyphens"
        if slug_exists_excluding_article(slug_norm, lang, article_id):
            return None, "Slug already in use for this language"
        patch["slug"] = slug_norm

    if summary is not None:
        new_summary = (summary or "").strip() or None
        if new_summary and len(new_summary) > SUMMARY_MAX_LENGTH:
            return None, f"Summary must be at most {SUMMARY_MAX_LENGTH} characters"
        patch["summary"] = new_summary

    if content is not None:
        patch["content"] = (content or "").strip() or existing_content

    if seo_title is not None:
        patch["seo_title"] = (seo_title or "").strip() or None
    if seo_description is not None:
        patch["seo_description"] = (seo_description or "").strip() or None

    if translation_status is not None and translation_status in TRANSLATION_STATUSES:
        patch["translation_status"] = translation_status

    return patch, None


def validate_upsert_translation_create_fields(
    *,
    title: Any,
    content: Any,
    slug: str | None,
    summary: str | None,
    seo_title: str | None,
    seo_description: str | None,
    translation_status: str | None,
    lang: str,
    slug_exists_global: SlugExistsGlobal,
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate payload for a new translation row (article has no row for ``lang`` yet)."""
    if not title or not content:
        return None, "title and content are required for new translation"

    slug_norm = normalize_news_slug(slug) if slug else normalize_news_slug(title)
    if not slug_norm:
        return None, "Slug is required"
    if slug_exists_global(slug_norm, lang):
        return None, "Slug already in use for this language"

    status = (
        translation_status
        if translation_status in TRANSLATION_STATUSES
        else TRANSLATION_STATUS_MACHINE_DRAFT
    )
    return {
        "title": (title or "").strip(),
        "slug": slug_norm,
        "summary": (summary or "").strip() or None,
        "content": (content or "").strip(),
        "seo_title": (seo_title or "").strip() or None,
        "seo_description": (seo_description or "").strip() or None,
        "translation_status": status,
    }, None
