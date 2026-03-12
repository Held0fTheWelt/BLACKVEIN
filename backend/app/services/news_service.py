"""News service: list, get, create, update, delete, publish. Uses NewsArticle + NewsArticleTranslation with language fallback."""
import logging
import re
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy import or_

from app.extensions import db
from app.i18n import (
    get_default_language,
    get_supported_languages,
    is_supported_language,
    normalize_language,
    TRANSLATION_STATUS_APPROVED,
    TRANSLATION_STATUS_MACHINE_DRAFT,
    TRANSLATION_STATUS_OUTDATED,
    TRANSLATION_STATUS_PUBLISHED,
    TRANSLATION_STATUS_REVIEW_REQUIRED,
    TRANSLATION_STATUSES,
)
from app.models import NewsArticle, NewsArticleTranslation

logger = logging.getLogger(__name__)

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TITLE_MAX_LENGTH = 255
SLUG_MAX_LENGTH = 255
SUMMARY_MAX_LENGTH = 500
CATEGORY_MAX_LENGTH = 64
COVER_IMAGE_MAX_LENGTH = 512

SORT_FIELDS = {"created_at", "updated_at", "published_at", "title"}
SORT_ORDERS = {"asc", "desc"}


def _utc_now():
    return datetime.now(timezone.utc)


def _normalize_slug(slug: str) -> str | None:
    if not slug or not isinstance(slug, str):
        return None
    s = slug.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s if s else None


def _slug_exists_for_lang(slug: str, language_code: str, exclude_article_id: int | None = None) -> bool:
    q = NewsArticleTranslation.query.filter(
        db.func.lower(NewsArticleTranslation.slug) == slug.lower(),
        NewsArticleTranslation.language_code == language_code,
    )
    if exclude_article_id is not None:
        q = q.filter(NewsArticleTranslation.article_id != exclude_article_id)
    return q.first() is not None


def _effective_language(article: NewsArticle, requested_lang: str | None) -> str:
    """Return the language code to use for this article: requested -> article default -> config default."""
    default = get_default_language()
    if requested_lang and is_supported_language(requested_lang):
        return requested_lang.strip().lower()
    if article.default_language and is_supported_language(article.default_language):
        return article.default_language.strip().lower()
    return default


def _get_translation_for_lang(article_id: int, language_code: str) -> NewsArticleTranslation | None:
    return NewsArticleTranslation.query.filter_by(
        article_id=article_id,
        language_code=language_code,
    ).first()


def _get_effective_translation(article: NewsArticle, lang: str | None) -> NewsArticleTranslation | None:
    """Return translation for article using fallback: lang -> article.default_language -> default."""
    lang = lang and normalize_language(lang) or article.default_language or get_default_language()
    t = _get_translation_for_lang(article.id, lang)
    if t:
        return t
    default_lang = article.default_language or get_default_language()
    if default_lang != lang:
        t = _get_translation_for_lang(article.id, default_lang)
        if t:
            return t
    fallback = get_default_language()
    if fallback != lang and fallback != default_lang:
        return _get_translation_for_lang(article.id, fallback)
    return NewsArticleTranslation.query.filter_by(article_id=article.id).first()


def _article_to_public_dict(article: NewsArticle, translation: NewsArticleTranslation | None) -> dict | None:
    """Build public API dict from article + effective translation. Returns None if no translation."""
    if not translation:
        return None
    out = {
        "id": article.id,
        "title": translation.title,
        "slug": translation.slug,
        "summary": translation.summary,
        "content": translation.content,
        "is_published": article.status == "published",
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "created_at": article.created_at.isoformat() if article.created_at else None,
        "updated_at": article.updated_at.isoformat() if article.updated_at else None,
        "cover_image": article.cover_image,
        "category": article.category,
        "language_code": translation.language_code,
    }
    if article.author_id is not None:
        out["author_id"] = article.author_id
        out["author_name"] = article.author.username if article.author else None
    else:
        out["author_id"] = None
        out["author_name"] = None
    return out


def list_news(
    *,
    published_only: bool = False,
    search: str | None = None,
    sort: str = "created_at",
    order: str = "desc",
    page: int = 1,
    per_page: int = 20,
    category: str | None = None,
    lang: str | None = None,
):
    """List news articles. Returns (list of dicts for API, total_count). Each dict is article + effective translation for lang."""
    q = NewsArticle.query
    if published_only:
        q = q.filter(NewsArticle.status == "published")
        q = q.filter(
            (NewsArticle.published_at == None) | (NewsArticle.published_at <= _utc_now())
        )
    if category and category.strip():
        q = q.filter(db.func.lower(NewsArticle.category) == category.strip().lower())

    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.join(NewsArticleTranslation).filter(
            or_(
                NewsArticleTranslation.title.ilike(term),
                NewsArticleTranslation.summary.ilike(term),
                NewsArticleTranslation.content.ilike(term),
            )
        ).distinct()

    if sort == "title":
        q = q.outerjoin(
            NewsArticleTranslation,
            (NewsArticle.id == NewsArticleTranslation.article_id)
            & (NewsArticleTranslation.language_code == NewsArticle.default_language),
        ).distinct()
        sort_col = NewsArticleTranslation.title
    else:
        sort_col = getattr(NewsArticle, sort, None) if sort in SORT_FIELDS else NewsArticle.created_at
    if sort_col is None:
        sort_col = NewsArticle.created_at
    if order == "asc":
        q = q.order_by(sort_col.asc())
    else:
        q = q.order_by(sort_col.desc())

    total = q.count()
    offset = max(0, (page - 1) * per_page)
    per_page = max(1, min(per_page, 100))
    articles = q.offset(offset).limit(per_page).all()

    default_lang = get_default_language()
    items = []
    for article in articles:
        trans = _get_effective_translation(article, lang)
        if not trans:
            continue
        if published_only and (article.status != "published" or trans.translation_status != TRANSLATION_STATUS_PUBLISHED):
            continue
        d = _article_to_public_dict(article, trans)
        if d and published_only:
            items.append(d)
            continue
        if d and not published_only:
            # Editorial: add translation status per language for list UI
            status_map = {}
            for code in get_supported_languages():
                t = _get_translation_for_lang(article.id, code)
                status_map[code] = t.translation_status if t else "missing"
            d["translation_statuses"] = status_map
            d["default_language"] = article.default_language
            items.append(d)

    return items, total


def get_news_by_id(news_id: int, lang: str | None = None):
    """Return public dict for article by id or None. For published-only callers, only published articles."""
    if news_id is None:
        return None
    article = db.session.get(NewsArticle, news_id)
    if not article:
        return None
    trans = _get_effective_translation(article, lang)
    if not trans:
        return None
    return _article_to_public_dict(article, trans)


def get_news_article_by_id(article_id: int):
    """Return NewsArticle by id or None (for editorial use)."""
    if article_id is None:
        return None
    return db.session.get(NewsArticle, article_id)


def get_news_by_slug(slug: str, lang: str | None = None):
    """Return public dict for article by slug in given language (with fallback) or None."""
    if not slug or not isinstance(slug, str):
        return None
    slug_norm = slug.strip().lower()
    default_lang = get_default_language()
    for try_lang in [normalize_language(lang) or default_lang, default_lang]:
        if not try_lang:
            continue
        trans = NewsArticleTranslation.query.filter(
            db.func.lower(NewsArticleTranslation.slug) == slug_norm,
            NewsArticleTranslation.language_code == try_lang,
            NewsArticleTranslation.translation_status == TRANSLATION_STATUS_PUBLISHED,
        ).first()
        if trans:
            article = db.session.get(NewsArticle, trans.article_id)
            if article and article.status == "published":
                return _article_to_public_dict(article, trans)
    return None


def create_news(
    title: str,
    slug: str,
    content: str,
    *,
    summary: str | None = None,
    author_id: int | None = None,
    is_published: bool = False,
    cover_image: str | None = None,
    category: str | None = None,
    default_language: str | None = None,
):
    """Create a news article with one translation in default_language. Returns (NewsArticle, None) or (None, error_message)."""
    default_lang = normalize_language(default_language) or get_default_language()
    title = (title or "").strip()
    if not title:
        return None, "Title is required"
    if len(title) > TITLE_MAX_LENGTH:
        return None, f"Title must be at most {TITLE_MAX_LENGTH} characters"
    content = (content or "").strip()
    if not content:
        return None, "Content is required"
    slug_norm = _normalize_slug(slug) if slug else None
    if not slug_norm:
        return None, "Slug is required and must be alphanumeric with hyphens"
    if len(slug_norm) > SLUG_MAX_LENGTH:
        return None, f"Slug must be at most {SLUG_MAX_LENGTH} characters"
    if _slug_exists_for_lang(slug_norm, default_lang):
        return None, "Slug already in use"
    if summary is not None and len((summary or "")) > SUMMARY_MAX_LENGTH:
        return None, f"Summary must be at most {SUMMARY_MAX_LENGTH} characters"
    if category and len(category) > CATEGORY_MAX_LENGTH:
        return None, f"Category must be at most {CATEGORY_MAX_LENGTH} characters"
    if cover_image and len(cover_image) > COVER_IMAGE_MAX_LENGTH:
        return None, f"Cover image URL must be at most {COVER_IMAGE_MAX_LENGTH} characters"

    now = _utc_now()
    status = "published" if is_published else "draft"
    article = NewsArticle(
        author_id=author_id,
        status=status,
        default_language=default_lang,
        category=(category or "").strip() or None,
        cover_image=(cover_image or "").strip() or None,
        created_at=now,
        updated_at=now,
        published_at=now if is_published else None,
    )
    db.session.add(article)
    db.session.flush()

    trans_status = TRANSLATION_STATUS_PUBLISHED if is_published else "approved"
    trans = NewsArticleTranslation(
        article_id=article.id,
        language_code=default_lang,
        title=title,
        slug=slug_norm,
        summary=(summary or "").strip() or None,
        content=content,
        translation_status=trans_status,
        source_language=default_lang,
        translated_at=now,
    )
    db.session.add(trans)
    db.session.commit()
    logger.info("News article created: id=%s slug=%r", article.id, slug_norm)
    return article, None


def update_news(
    news_or_id,
    *,
    title: str | None = None,
    slug: str | None = None,
    summary: str | None = None,
    content: str | None = None,
    cover_image: str | None = None,
    category: str | None = None,
    default_language: str | None = None,
):
    """Update base article and its default-language translation. Returns (NewsArticle, None) or (None, error_message)."""
    article = get_news_article_by_id(news_or_id) if isinstance(news_or_id, int) else news_or_id
    if not article:
        return None, "News not found"

    default_lang = article.default_language or get_default_language()
    trans = _get_translation_for_lang(article.id, default_lang)
    if not trans:
        return None, "Default translation not found"

    if title is not None:
        t = title.strip()
        if not t:
            return None, "Title cannot be empty"
        if len(t) > TITLE_MAX_LENGTH:
            return None, f"Title must be at most {TITLE_MAX_LENGTH} characters"
        trans.title = t
    if slug is not None:
        slug_norm = _normalize_slug(slug)
        if not slug_norm:
            return None, "Slug must be alphanumeric with hyphens"
        if len(slug_norm) > SLUG_MAX_LENGTH:
            return None, f"Slug must be at most {SLUG_MAX_LENGTH} characters"
        if _slug_exists_for_lang(slug_norm, default_lang, exclude_article_id=article.id):
            return None, "Slug already in use"
        trans.slug = slug_norm
    if summary is not None:
        s = (summary or "").strip() or None
        if s and len(s) > SUMMARY_MAX_LENGTH:
            return None, f"Summary must be at most {SUMMARY_MAX_LENGTH} characters"
        trans.summary = s
    if content is not None:
        c = content.strip()
        if not c:
            return None, "Content cannot be empty"
        trans.content = c
    if cover_image is not None:
        article.cover_image = (cover_image or "").strip() or None
        if article.cover_image and len(article.cover_image) > COVER_IMAGE_MAX_LENGTH:
            return None, f"Cover image URL must be at most {COVER_IMAGE_MAX_LENGTH} characters"
    if category is not None:
        article.category = (category or "").strip() or None
        if article.category and len(article.category) > CATEGORY_MAX_LENGTH:
            return None, f"Category must be at most {CATEGORY_MAX_LENGTH} characters"
    if default_language is not None:
        lang_norm = normalize_language(default_language)
        if lang_norm:
            article.default_language = lang_norm

    article.updated_at = _utc_now()
    # Mark non-source translations outdated when source content changes
    if any(x is not None for x in (title, slug, summary, content)):
        source_version = _utc_now().isoformat()
        trans.source_version = source_version
        mark_article_translations_outdated(article.id, exclude_language=default_lang)
    db.session.commit()
    logger.info("News article updated: id=%s", article.id)
    return article, None


def delete_news(news_or_id):
    """Delete a news article (and its translations). Returns (True, None) or (False, error_message)."""
    article = get_news_article_by_id(news_or_id) if isinstance(news_or_id, int) else news_or_id
    if not article:
        return False, "News not found"
    db.session.delete(article)
    db.session.commit()
    logger.info("News article deleted: id=%s", article.id)
    return True, None


def publish_news(news_or_id):
    """Set article status to published and published_at=now. Returns (NewsArticle, None) or (None, error_message)."""
    article = get_news_article_by_id(news_or_id) if isinstance(news_or_id, int) else news_or_id
    if not article:
        return None, "News not found"
    article.status = "published"
    if not article.published_at:
        article.published_at = _utc_now()
    db.session.commit()
    logger.info("News article published: id=%s", article.id)
    return article, None


def unpublish_news(news_or_id):
    """Set article status to draft. Returns (NewsArticle, None) or (None, error_message)."""
    article = get_news_article_by_id(news_or_id) if isinstance(news_or_id, int) else news_or_id
    if not article:
        return None, "News not found"
    article.status = "draft"
    db.session.commit()
    logger.info("News article unpublished: id=%s", article.id)
    return article, None


# --- Article translations (editorial) ---


def list_article_translations(article_id: int):
    """Return list of translation summaries for article (language_code, status, title, slug, etc.)."""
    article = get_news_article_by_id(article_id)
    if not article:
        return None, "News not found"
    trans_list = NewsArticleTranslation.query.filter_by(article_id=article_id).all()
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
                "translated_at": t.translated_at.isoformat() if t.translated_at else None,
                "reviewed_at": t.reviewed_at.isoformat() if t.reviewed_at else None,
            })
        else:
            out.append({
                "language_code": lang,
                "translation_status": "missing",
                "title": None,
                "slug": None,
                "translated_at": None,
                "reviewed_at": None,
            })
    return out, None


def get_article_translation(article_id: int, language_code: str):
    """Return full NewsArticleTranslation for article+lang or None."""
    if not normalize_language(language_code):
        return None
    return NewsArticleTranslation.query.filter_by(
        article_id=article_id,
        language_code=normalize_language(language_code),
    ).first()


def _translation_to_dict(t: NewsArticleTranslation):
    return {
        "id": t.id,
        "article_id": t.article_id,
        "language_code": t.language_code,
        "title": t.title,
        "slug": t.slug,
        "summary": t.summary,
        "content": t.content,
        "seo_title": t.seo_title,
        "seo_description": t.seo_description,
        "translation_status": t.translation_status,
        "source_language": t.source_language,
        "source_version": t.source_version,
        "translated_at": t.translated_at.isoformat() if t.translated_at else None,
        "reviewed_by": t.reviewed_by,
        "reviewed_at": t.reviewed_at.isoformat() if t.reviewed_at else None,
    }


def upsert_article_translation(
    article_id: int,
    language_code: str,
    *,
    title: str | None = None,
    slug: str | None = None,
    summary: str | None = None,
    content: str | None = None,
    seo_title: str | None = None,
    seo_description: str | None = None,
    translation_status: str | None = None,
):
    """Create or update a news article translation. Returns (translation, None) or (None, error_message)."""
    article = get_news_article_by_id(article_id)
    if not article:
        return None, "News not found"
    lang = normalize_language(language_code)
    if not lang:
        return None, "Unsupported language"
    trans = get_article_translation(article_id, lang)
    if trans:
        if title is not None:
            trans.title = (title or "").strip() or trans.title
            if len(trans.title) > TITLE_MAX_LENGTH:
                return None, f"Title must be at most {TITLE_MAX_LENGTH} characters"
        if slug is not None:
            slug_norm = _normalize_slug(slug)
            if not slug_norm:
                return None, "Slug must be alphanumeric with hyphens"
            if _slug_exists_for_lang(slug_norm, lang, exclude_article_id=article_id):
                return None, "Slug already in use for this language"
            trans.slug = slug_norm
        if summary is not None:
            trans.summary = (summary or "").strip() or None
            if trans.summary and len(trans.summary) > SUMMARY_MAX_LENGTH:
                return None, f"Summary must be at most {SUMMARY_MAX_LENGTH} characters"
        if content is not None:
            trans.content = (content or "").strip() or trans.content
        if seo_title is not None:
            trans.seo_title = (seo_title or "").strip() or None
        if seo_description is not None:
            trans.seo_description = (seo_description or "").strip() or None
        if translation_status is not None and translation_status in TRANSLATION_STATUSES:
            trans.translation_status = translation_status
        # When updating the source (default-language) translation content, mark others outdated
        if content is not None or title is not None or summary is not None or slug is not None:
            if article.default_language == lang:
                trans.source_version = _utc_now().isoformat()
                mark_article_translations_outdated(article_id, exclude_language=lang)
        db.session.commit()
        db.session.refresh(trans)
        return trans, None
    # Create new translation
    if not title or not content:
        return None, "title and content are required for new translation"
    slug_norm = _normalize_slug(slug) if slug else _normalize_slug(title)
    if not slug_norm:
        return None, "Slug is required"
    if _slug_exists_for_lang(slug_norm, lang):
        return None, "Slug already in use for this language"
    now = _utc_now()
    status = translation_status if translation_status in TRANSLATION_STATUSES else TRANSLATION_STATUS_MACHINE_DRAFT
    trans = NewsArticleTranslation(
        article_id=article_id,
        language_code=lang,
        title=(title or "").strip(),
        slug=slug_norm,
        summary=(summary or "").strip() or None,
        content=(content or "").strip(),
        seo_title=(seo_title or "").strip() or None,
        seo_description=(seo_description or "").strip() or None,
        translation_status=status,
        source_language=article.default_language,
        translated_at=now,
    )
    db.session.add(trans)
    db.session.commit()
    logger.info("News translation created: article_id=%s lang=%s", article_id, lang)
    return trans, None


def submit_review_article_translation(article_id: int, language_code: str):
    """Set translation status to review_required. Returns (translation, None) or (None, error_message)."""
    trans = get_article_translation(article_id, normalize_language(language_code) or "")
    if not trans:
        return None, "Translation not found"
    trans.translation_status = TRANSLATION_STATUS_REVIEW_REQUIRED
    db.session.commit()
    return trans, None


def approve_article_translation(article_id: int, language_code: str, reviewer_id: int | None = None):
    """Set translation status to approved and set reviewed_by/reviewed_at. Returns (translation, None) or (None, error_message)."""
    trans = get_article_translation(article_id, normalize_language(language_code) or "")
    if not trans:
        return None, "Translation not found"
    trans.translation_status = TRANSLATION_STATUS_APPROVED
    trans.reviewed_by = reviewer_id
    trans.reviewed_at = _utc_now()
    db.session.commit()
    return trans, None


def publish_article_translation(article_id: int, language_code: str):
    """Set translation status to published. Returns (translation, None) or (None, error_message)."""
    trans = get_article_translation(article_id, normalize_language(language_code) or "")
    if not trans:
        return None, "Translation not found"
    trans.translation_status = TRANSLATION_STATUS_PUBLISHED
    db.session.commit()
    return trans, None


def mark_article_translations_outdated(article_id: int, exclude_language: str | None = None):
    """Mark all translations except exclude_language as outdated (e.g. after source change)."""
    q = NewsArticleTranslation.query.filter_by(article_id=article_id)
    if exclude_language:
        q = q.filter(NewsArticleTranslation.language_code != exclude_language)
    q.update({"translation_status": TRANSLATION_STATUS_OUTDATED}, synchronize_session=False)
    db.session.commit()
