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
)
from app.models import NewsArticle, NewsArticleTranslation, ForumThread, NewsArticleForumThread
from app.services.news_service_create_guards import validate_news_create_payload
from app.services.news_service_translation_upsert_guards import (
    validate_upsert_translation_create_fields,
    validate_upsert_translation_update_patch,
)
from app.services.news_service_update_guards import validate_news_update_patch

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
    if article.discussion_thread_id is not None:
        thread = db.session.get(ForumThread, article.discussion_thread_id)
        if thread and thread.deleted_at is None:
            out["discussion_thread_id"] = thread.id
            out["discussion_thread_slug"] = thread.slug
        else:
            out["discussion_thread_id"] = None
            out["discussion_thread_slug"] = None
    else:
        out["discussion_thread_id"] = None
        out["discussion_thread_slug"] = None
    return out


def list_related_threads_for_article(article_id: int, *, limit: int = 5) -> list[dict]:
    """Return safe related forum threads for a news article."""
    if not article_id:
        return []
    from app.models import ForumCategory  # local import to avoid cycles

    q = (
        db.session.query(ForumThread)
        .join(NewsArticleForumThread, NewsArticleForumThread.thread_id == ForumThread.id)
        .filter(NewsArticleForumThread.article_id == article_id)
        .filter(ForumThread.deleted_at.is_(None))
    )
    # Restrict to public categories (no required_role, not private, active)
    q = q.join(ForumCategory, ForumCategory.id == ForumThread.category_id).filter(
        ForumCategory.is_active.is_(True),
        ForumCategory.is_private.is_(False),
        ForumCategory.required_role.is_(None),
    )
    q = q.order_by(ForumThread.is_pinned.desc(), ForumThread.last_post_at.desc().nullslast())
    threads = q.limit(max(1, min(limit, 20))).all()
    items: list[dict] = []
    for t in threads:
        d = {
            "id": t.id,
            "slug": t.slug,
            "title": t.title,
            "status": t.status,
            "reply_count": t.reply_count,
            "last_post_at": t.last_post_at.isoformat() if t.last_post_at else None,
        }
        if t.category:
            d["category"] = {"id": t.category.id, "slug": t.category.slug, "title": t.category.title}
        items.append(d)
    return items


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
    fields, err = validate_news_create_payload(
        title,
        slug,
        content,
        summary=summary,
        category=category,
        cover_image=cover_image,
        default_language=default_language,
        slug_exists_for_lang=lambda s, lang: _slug_exists_for_lang(s, lang),
    )
    if err:
        return None, err
    default_lang = fields["default_lang"]
    title = fields["title"]
    content = fields["content"]
    slug_norm = fields["slug_norm"]
    summary = fields["summary"]
    category = fields["category"]
    cover_image = fields["cover_image"]

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

    patch, err = validate_news_update_patch(
        title=title,
        slug=slug,
        summary=summary,
        content=content,
        cover_image=cover_image,
        category=category,
        default_language=default_language,
        article_id=article.id,
        default_lang=default_lang,
        slug_exists_for_lang_excluding=lambda s, lang, aid: _slug_exists_for_lang(
            s, lang, exclude_article_id=aid
        ),
    )
    if err:
        return None, err

    if "title" in patch:
        trans.title = patch["title"]
    if "slug" in patch:
        trans.slug = patch["slug"]
    if "summary" in patch:
        trans.summary = patch["summary"]
    if "content" in patch:
        trans.content = patch["content"]
    if "cover_image" in patch:
        article.cover_image = patch["cover_image"]
    if "category" in patch:
        article.category = patch["category"]
    if "default_language" in patch:
        article.default_language = patch["default_language"]

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
        patch, err = validate_upsert_translation_update_patch(
            title=title,
            slug=slug,
            summary=summary,
            content=content,
            seo_title=seo_title,
            seo_description=seo_description,
            translation_status=translation_status,
            existing_title=trans.title or "",
            existing_content=trans.content or "",
            article_id=article_id,
            lang=lang,
            slug_exists_excluding_article=lambda s, l, aid: _slug_exists_for_lang(
                s, l, exclude_article_id=aid
            ),
        )
        if err:
            return None, err
        if "title" in patch:
            trans.title = patch["title"]
        if "slug" in patch:
            trans.slug = patch["slug"]
        if "summary" in patch:
            trans.summary = patch["summary"]
        if "content" in patch:
            trans.content = patch["content"]
        if "seo_title" in patch:
            trans.seo_title = patch["seo_title"]
        if "seo_description" in patch:
            trans.seo_description = patch["seo_description"]
        if "translation_status" in patch:
            trans.translation_status = patch["translation_status"]
        # When updating the source (default-language) translation content, mark others outdated
        if content is not None or title is not None or summary is not None or slug is not None:
            if article.default_language == lang:
                trans.source_version = _utc_now().isoformat()
                mark_article_translations_outdated(article_id, exclude_language=lang)
        db.session.commit()
        db.session.refresh(trans)
        return trans, None
    # Create new translation
    fields, err = validate_upsert_translation_create_fields(
        title=title,
        content=content,
        slug=slug,
        summary=summary,
        seo_title=seo_title,
        seo_description=seo_description,
        translation_status=translation_status,
        lang=lang,
        slug_exists_global=lambda s, l: _slug_exists_for_lang(s, l),
    )
    if err:
        return None, err
    now = _utc_now()
    trans = NewsArticleTranslation(
        article_id=article_id,
        language_code=lang,
        title=fields["title"],
        slug=fields["slug"],
        summary=fields["summary"],
        content=fields["content"],
        seo_title=fields["seo_title"],
        seo_description=fields["seo_description"],
        translation_status=fields["translation_status"],
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


def get_suggested_threads_for_article(article_id: int, *, limit: int = 5) -> list[dict]:
    """Get auto-suggested related forum threads for a news article (in addition to explicit links).

    Uses deterministic ranking based on:
    - Tag matches from discussion thread (if exists)
    - Recent activity (tie-breaker)
    - Excludes: primary discussion, manually related threads, hidden/deleted threads
    """
    article = NewsArticle.query.get(article_id)
    if not article:
        return []

    from app.models import ForumThread, ForumCategory, ForumThreadTag, ForumTag
    from app.services.forum_service import suggest_related_threads_for_query

    # Collect tags from the primary discussion thread (if linked)
    query_tags = []
    exclude_ids = set()

    if article.discussion_thread_id:
        exclude_ids.add(article.discussion_thread_id)
        # Get tags from the primary discussion thread
        primary_thread = ForumThread.query.get(article.discussion_thread_id)
        if primary_thread:
            thread_tags = db.session.query(ForumTag.label).join(
                ForumThreadTag, ForumThreadTag.tag_id == ForumTag.id
            ).filter(
                ForumThreadTag.thread_id == article.discussion_thread_id
            ).all()
            query_tags = [t[0] for t in thread_tags]

    # Collect manually linked thread IDs to exclude
    manually_linked = list_related_threads_for_article(article_id, limit=100)
    for thread_dict in manually_linked:
        exclude_ids.add(thread_dict["id"])

    # Use deterministic ranking function
    suggestions = suggest_related_threads_for_query(
        query_tags=query_tags if query_tags else None,
        exclude_thread_ids=exclude_ids if exclude_ids else None,
        exclude_primary_id=article.discussion_thread_id,
        limit=limit,
    )

    return suggestions
