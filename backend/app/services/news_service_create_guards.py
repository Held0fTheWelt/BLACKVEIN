"""Pure validation for ``news_service.create_news`` (DS-005 — control-flow extraction).

Length / slug rules mirror ``news_service`` (keep in sync if constants move).
"""

from __future__ import annotations

import re
from typing import Any, Callable

from app.i18n import get_default_language, normalize_language

TITLE_MAX_LENGTH = 255
SLUG_MAX_LENGTH = 255
SUMMARY_MAX_LENGTH = 500
CATEGORY_MAX_LENGTH = 64
COVER_IMAGE_MAX_LENGTH = 512


def _normalize_slug(slug: str) -> str | None:
    if not slug or not isinstance(slug, str):
        return None
    s = slug.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s if s else None


def normalize_news_slug(slug: str) -> str | None:
    """Normalize a user slug string; shared with ``news_service`` update validation."""
    return _normalize_slug(slug)


def validate_news_create_payload(
    title: str,
    slug: str,
    content: str,
    *,
    summary: str | None,
    category: str | None,
    cover_image: str | None,
    default_language: str | None,
    slug_exists_for_lang: Callable[[str, str], bool],
) -> tuple[dict[str, Any] | None, str | None]:
    """Return ``(normalized_fields, None)`` or ``(None, error_message)``."""
    default_lang = normalize_language(default_language) or get_default_language()
    title_stripped = (title or "").strip()
    if not title_stripped:
        return None, "Title is required"
    if len(title_stripped) > TITLE_MAX_LENGTH:
        return None, f"Title must be at most {TITLE_MAX_LENGTH} characters"
    content_stripped = (content or "").strip()
    if not content_stripped:
        return None, "Content is required"
    slug_norm = _normalize_slug(slug) if slug else None
    if not slug_norm:
        return None, "Slug is required and must be alphanumeric with hyphens"
    if len(slug_norm) > SLUG_MAX_LENGTH:
        return None, f"Slug must be at most {SLUG_MAX_LENGTH} characters"
    if slug_exists_for_lang(slug_norm, default_lang):
        return None, "Slug already in use"
    if summary is not None and len((summary or "")) > SUMMARY_MAX_LENGTH:
        return None, f"Summary must be at most {SUMMARY_MAX_LENGTH} characters"
    if category and len(category) > CATEGORY_MAX_LENGTH:
        return None, f"Category must be at most {CATEGORY_MAX_LENGTH} characters"
    if cover_image and len(cover_image) > COVER_IMAGE_MAX_LENGTH:
        return None, f"Cover image URL must be at most {COVER_IMAGE_MAX_LENGTH} characters"

    return {
        "default_lang": default_lang,
        "title": title_stripped,
        "content": content_stripped,
        "slug_norm": slug_norm,
        "summary": (summary or "").strip() or None,
        "category": (category or "").strip() or None,
        "cover_image": (cover_image or "").strip() or None,
    }, None
