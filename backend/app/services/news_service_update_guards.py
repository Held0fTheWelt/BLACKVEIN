"""Partial-update validation for ``news_service.update_news`` (DS-005 — control-flow extraction)."""

from __future__ import annotations

from typing import Any, Callable

from app.i18n import normalize_language

from app.services.news_service_create_guards import (
    CATEGORY_MAX_LENGTH,
    COVER_IMAGE_MAX_LENGTH,
    SLUG_MAX_LENGTH,
    SUMMARY_MAX_LENGTH,
    TITLE_MAX_LENGTH,
    normalize_news_slug,
)

SlugExistsExcluding = Callable[[str, str, int], bool]


def validate_news_update_patch(
    *,
    title: str | None = None,
    slug: str | None = None,
    summary: str | None = None,
    content: str | None = None,
    cover_image: str | None = None,
    category: str | None = None,
    default_language: str | None = None,
    article_id: int,
    default_lang: str,
    slug_exists_for_lang_excluding: SlugExistsExcluding,
) -> tuple[dict[str, Any] | None, str | None]:
    """
    Build a validated patch for fields that are not ``None`` (caller passes only intended updates).

    Returns ``(patch, None)`` or ``(None, error_message)``. Keys in ``patch`` match attributes to set
    on translation vs article (see ``news_service.update_news``).
    """
    patch: dict[str, Any] = {}

    if title is not None:
        t = title.strip()
        if not t:
            return None, "Title cannot be empty"
        if len(t) > TITLE_MAX_LENGTH:
            return None, f"Title must be at most {TITLE_MAX_LENGTH} characters"
        patch["title"] = t

    if slug is not None:
        slug_norm = normalize_news_slug(slug)
        if not slug_norm:
            return None, "Slug must be alphanumeric with hyphens"
        if len(slug_norm) > SLUG_MAX_LENGTH:
            return None, f"Slug must be at most {SLUG_MAX_LENGTH} characters"
        if slug_exists_for_lang_excluding(slug_norm, default_lang, article_id):
            return None, "Slug already in use"
        patch["slug"] = slug_norm

    if summary is not None:
        s = (summary or "").strip() or None
        if s and len(s) > SUMMARY_MAX_LENGTH:
            return None, f"Summary must be at most {SUMMARY_MAX_LENGTH} characters"
        patch["summary"] = s

    if content is not None:
        c = content.strip()
        if not c:
            return None, "Content cannot be empty"
        patch["content"] = c

    if cover_image is not None:
        cv = (cover_image or "").strip() or None
        if cv and len(cv) > COVER_IMAGE_MAX_LENGTH:
            return None, f"Cover image URL must be at most {COVER_IMAGE_MAX_LENGTH} characters"
        patch["cover_image"] = cv

    if category is not None:
        cat = (category or "").strip() or None
        if cat and len(cat) > CATEGORY_MAX_LENGTH:
            return None, f"Category must be at most {CATEGORY_MAX_LENGTH} characters"
        patch["category"] = cat

    if default_language is not None:
        lang_norm = normalize_language(default_language)
        if lang_norm:
            patch["default_language"] = lang_norm

    return patch, None
