"""Wiki: page and translation lookup. Supports DB-backed pages with fallback."""

from datetime import datetime, timezone

from flask import current_app

from app.extensions import db
from app.i18n import (
    TRANSLATION_STATUS_OUTDATED,
    get_default_language,
    normalize_language,
)
from app.models import WikiPage, WikiPageTranslation


def get_wiki_page_by_key(key: str):
    """Return WikiPage by key or None."""
    if not key or not isinstance(key, str):
        return None
    return WikiPage.query.filter_by(key=key.strip()).first()


def get_wiki_translation(page_id: int, language_code: str) -> WikiPageTranslation | None:
    """Return WikiPageTranslation for page and language, or None."""
    if not page_id or not language_code:
        return None
    return WikiPageTranslation.query.filter_by(
        page_id=page_id,
        language_code=language_code.strip().lower(),
    ).first()


def get_effective_wiki_translation(page: WikiPage, lang: str | None):
    """Return translation for page using fallback: lang -> first translation -> config default."""
    codes = []
    if lang and normalize_language(lang):
        codes.append(normalize_language(lang))
    # No explicit "default_language" on WikiPage; use first translation or config default
    first = WikiPageTranslation.query.filter_by(page_id=page.id).first()
    if first and first.language_code not in codes:
        codes.append(first.language_code)
    codes.append(get_default_language())
    for code in codes:
        t = get_wiki_translation(page.id, code)
        if t:
            return t
    return None


def get_wiki_markdown_for_display(lang: str | None = None) -> str | None:
    """
    Return markdown content for the default wiki page (key=index) in the given or default language.
    Used for backward-compatible wiki display. Returns None if no page in DB.
    """
    page = get_wiki_page_by_key("index")
    if not page:
        return None
    trans = get_effective_wiki_translation(page, lang)
    if not trans:
        return None
    return trans.content_markdown or ""


def get_wiki_page_by_slug(slug: str, lang: str | None = None):
    """Return (page, translation) for public display by slug and language, or (None, None)."""
    if not slug or not isinstance(slug, str):
        return None, None
    slug_norm = slug.strip().lower()
    default_lang = get_default_language()
    for try_lang in [normalize_language(lang) or default_lang, default_lang]:
        if not try_lang:
            continue
        trans = WikiPageTranslation.query.filter(
            db.func.lower(WikiPageTranslation.slug) == slug_norm,
            WikiPageTranslation.language_code == try_lang,
        ).first()
        if trans and trans.page and trans.page.is_published:
            return trans.page, trans
    return None, None


# --- Wiki admin (pages + translations) ---

def list_wiki_pages():
    """Return all wiki pages (id, key, sort_order, is_published, created_at, updated_at)."""
    return WikiPage.query.order_by(WikiPage.sort_order.asc(), WikiPage.id.asc()).all()


def get_wiki_page_by_id(page_id: int):
    """Return WikiPage by id or None."""
    if page_id is None:
        return None
    return db.session.get(WikiPage, page_id)


def create_wiki_page(key: str, parent_id: int | None = None, sort_order: int = 0, is_published: bool = True):
    """Create a wiki page. Returns (page, None) or (None, error_message)."""
    key = (key or "").strip()
    if not key:
        return None, "key is required"
    if WikiPage.query.filter_by(key=key).first():
        return None, "Key already in use"
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    page = WikiPage(key=key, parent_id=parent_id, sort_order=sort_order, is_published=is_published, created_at=now, updated_at=now)
    db.session.add(page)
    db.session.commit()
    return page, None


def update_wiki_page(page_id: int, *, key: str | None = None, sort_order: int | None = None, is_published: bool | None = None):
    """Update wiki page. Returns (page, None) or (None, error_message)."""
    page = get_wiki_page_by_id(page_id)
    if not page:
        return None, "Page not found"
    if key is not None:
        k = (key or "").strip()
        if not k:
            return None, "key cannot be empty"
        other = WikiPage.query.filter_by(key=k).first()
        if other and other.id != page_id:
            return None, "Key already in use"
        page.key = k
    if sort_order is not None:
        page.sort_order = sort_order
    if is_published is not None:
        page.is_published = bool(is_published)
    from datetime import datetime, timezone
    page.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return page, None


def list_wiki_page_translations(page_id: int):
    """Return list of translation summaries for page (per supported language)."""
    from app.i18n import get_supported_languages
    page = get_wiki_page_by_id(page_id)
    if not page:
        return None, "Page not found"
    trans_list = WikiPageTranslation.query.filter_by(page_id=page_id).all()
    supported = get_supported_languages()
    out = []
    for lang in supported:
        t = next((x for x in trans_list if x.language_code == lang), None)
        if t:
            out.append({
                "language_code": t.language_code,
                "translation_status": t.translation_status,
                "title": t.title,
                "slug": t.slug,
                "reviewed_at": t.reviewed_at.isoformat() if t.reviewed_at else None,
            })
        else:
            out.append({
                "language_code": lang,
                "translation_status": "missing",
                "title": None,
                "slug": None,
                "reviewed_at": None,
            })
    return out, None


def get_wiki_page_translation(page_id: int, language_code: str):
    """Return WikiPageTranslation for page+lang or None."""
    lang = normalize_language(language_code)
    if not lang:
        return None
    return WikiPageTranslation.query.filter_by(page_id=page_id, language_code=lang).first()


def _utc_now():
    return datetime.now(timezone.utc)


def mark_wiki_translations_outdated(page_id: int, exclude_language: str | None = None):
    """Mark all translations for the page as outdated except exclude_language. Caller must commit."""
    q = WikiPageTranslation.query.filter_by(page_id=page_id)
    if exclude_language:
        q = q.filter(WikiPageTranslation.language_code != exclude_language)
    q.update({"translation_status": TRANSLATION_STATUS_OUTDATED}, synchronize_session=False)


def _wiki_slug_exists_for_lang(slug: str, language_code: str, exclude_translation_id: int | None = None) -> bool:
    """True if another wiki translation already has this slug in this language."""
    q = WikiPageTranslation.query.filter(
        db.func.lower(WikiPageTranslation.slug) == slug.strip().lower(),
        WikiPageTranslation.language_code == language_code,
    )
    if exclude_translation_id is not None:
        q = q.filter(WikiPageTranslation.id != exclude_translation_id)
    return q.first() is not None


def upsert_wiki_page_translation(
    page_id: int,
    language_code: str,
    *,
    title: str | None = None,
    slug: str | None = None,
    content_markdown: str | None = None,
    translation_status: str | None = None,
):
    """Create or update wiki page translation. Returns (translation, None) or (None, error_message). Slug is unique per language."""
    from app.i18n import TRANSLATION_STATUSES
    page = get_wiki_page_by_id(page_id)
    if not page:
        return None, "Page not found"
    lang = normalize_language(language_code)
    if not lang:
        return None, "Unsupported language"
    trans = get_wiki_page_translation(page_id, lang)
    if trans:
        if title is not None:
            trans.title = (title or "").strip() or trans.title
        if slug is not None:
            new_slug = (slug or "").strip().lower() or trans.slug
            if _wiki_slug_exists_for_lang(new_slug, lang, exclude_translation_id=trans.id):
                return None, "Slug already in use for this language"
            trans.slug = new_slug
        if content_markdown is not None:
            trans.content_markdown = content_markdown
        # When this translation's content/title/slug changes, it becomes the new source; mark others outdated.
        if content_markdown is not None or title is not None or slug is not None:
            trans.source_version = _utc_now().isoformat()
            mark_wiki_translations_outdated(page_id, exclude_language=lang)
        db.session.commit()
        return trans, None
    if not title or not slug:
        return None, "title and slug required for new translation"
    new_slug = (slug or "").strip().lower()
    if _wiki_slug_exists_for_lang(new_slug, lang):
        return None, "Slug already in use for this language"
    from app.i18n import TRANSLATION_STATUS_MACHINE_DRAFT
    status = translation_status if translation_status in TRANSLATION_STATUSES else TRANSLATION_STATUS_MACHINE_DRAFT
    trans = WikiPageTranslation(
        page_id=page_id,
        language_code=lang,
        title=title.strip(),
        slug=new_slug,
        content_markdown=(content_markdown or "").strip(),
        translation_status=status,
    )
    db.session.add(trans)
    db.session.commit()
    return trans, None


def submit_review_wiki_translation(page_id: int, language_code: str):
    from app.i18n import TRANSLATION_STATUS_REVIEW_REQUIRED
    trans = get_wiki_page_translation(page_id, normalize_language(language_code) or "")
    if not trans:
        return None, "Translation not found"
    trans.translation_status = TRANSLATION_STATUS_REVIEW_REQUIRED
    db.session.commit()
    return trans, None


def approve_wiki_translation(page_id: int, language_code: str, reviewer_id: int | None = None):
    from app.i18n import TRANSLATION_STATUS_APPROVED
    from datetime import datetime, timezone
    trans = get_wiki_page_translation(page_id, normalize_language(language_code) or "")
    if not trans:
        return None, "Translation not found"
    trans.translation_status = TRANSLATION_STATUS_APPROVED
    trans.reviewed_by = reviewer_id
    trans.reviewed_at = datetime.now(timezone.utc)
    db.session.commit()
    return trans, None


def publish_wiki_translation(page_id: int, language_code: str):
    from app.i18n import TRANSLATION_STATUS_PUBLISHED
    trans = get_wiki_page_translation(page_id, normalize_language(language_code) or "")
    if not trans:
        return None, "Translation not found"
    trans.translation_status = TRANSLATION_STATUS_PUBLISHED
    db.session.commit()
    return trans, None
