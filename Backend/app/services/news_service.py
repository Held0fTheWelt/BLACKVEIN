"""News service: list, get, create, update, delete, publish. Filtering/sorting/pagination here."""
import logging
import re
from datetime import datetime, timezone

from app.extensions import db
from app.models import News

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
    """Normalize slug: lowercase, strip, collapse spaces to single hyphen. None if invalid."""
    if not slug or not isinstance(slug, str):
        return None
    s = slug.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s if s else None


def _slug_exists(slug: str, exclude_id: int | None = None) -> bool:
    q = News.query.filter(db.func.lower(News.slug) == slug.lower())
    if exclude_id is not None:
        q = q.filter(News.id != exclude_id)
    return q.first() is not None


def list_news(
    *,
    published_only: bool = False,
    search: str | None = None,
    sort: str = "created_at",
    order: str = "desc",
    page: int = 1,
    per_page: int = 20,
    category: str | None = None,
):
    """
    List news with optional filtering, search, sort, and pagination.
    Returns (query_result_list, total_count).
    """
    q = News.query
    if published_only:
        q = q.filter(News.is_published == True)
        q = q.filter(
            (News.published_at == None) | (News.published_at <= _utc_now())
        )
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(
            db.or_(
                News.title.ilike(term),
                News.summary.ilike(term),
                News.content.ilike(term),
            )
        )
    if category and category.strip():
        q = q.filter(db.func.lower(News.category) == category.strip().lower())

    sort_col = getattr(News, sort, None) if sort in SORT_FIELDS else News.created_at
    if order == "asc":
        q = q.order_by(sort_col.asc())
    else:
        q = q.order_by(sort_col.desc())

    total = q.count()
    offset = max(0, (page - 1) * per_page)
    per_page = max(1, min(per_page, 100))
    items = q.offset(offset).limit(per_page).all()
    return items, total


def get_news_by_id(news_id: int):
    """Return News by id or None."""
    if news_id is None:
        return None
    return db.session.get(News, news_id)


def get_news_by_slug(slug: str):
    """Return News by slug (case-insensitive) or None."""
    if not slug or not isinstance(slug, str):
        return None
    return News.query.filter(db.func.lower(News.slug) == slug.strip().lower()).first()


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
):
    """
    Create a news article. Returns (News, None) or (None, error_message).
    Slug is normalized and must be unique.
    """
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
    if _slug_exists(slug_norm):
        return None, "Slug already in use"

    if summary is not None and len((summary or "")) > SUMMARY_MAX_LENGTH:
        return None, f"Summary must be at most {SUMMARY_MAX_LENGTH} characters"
    if category and len(category) > CATEGORY_MAX_LENGTH:
        return None, f"Category must be at most {CATEGORY_MAX_LENGTH} characters"
    if cover_image and len(cover_image) > COVER_IMAGE_MAX_LENGTH:
        return None, f"Cover image URL must be at most {COVER_IMAGE_MAX_LENGTH} characters"

    now = _utc_now()
    news = News(
        title=title,
        slug=slug_norm,
        summary=(summary or "").strip() or None,
        content=content,
        author_id=author_id,
        is_published=bool(is_published),
        published_at=now if is_published else None,
        created_at=now,
        updated_at=now,
        cover_image=(cover_image or "").strip() or None,
        category=(category or "").strip() or None,
    )
    db.session.add(news)
    db.session.commit()
    logger.info("News created: id=%s slug=%r", news.id, news.slug)
    return news, None


def update_news(
    news_or_id,
    *,
    title: str | None = None,
    slug: str | None = None,
    summary: str | None = None,
    content: str | None = None,
    cover_image: str | None = None,
    category: str | None = None,
):
    """
    Update a news article. Returns (News, None) or (None, error_message).
    Only provided fields are updated.
    """
    news = get_news_by_id(news_or_id) if isinstance(news_or_id, int) else news_or_id
    if not news:
        return None, "News not found"

    if title is not None:
        t = title.strip()
        if not t:
            return None, "Title cannot be empty"
        if len(t) > TITLE_MAX_LENGTH:
            return None, f"Title must be at most {TITLE_MAX_LENGTH} characters"
        news.title = t
    if slug is not None:
        slug_norm = _normalize_slug(slug)
        if not slug_norm:
            return None, "Slug must be alphanumeric with hyphens"
        if len(slug_norm) > SLUG_MAX_LENGTH:
            return None, f"Slug must be at most {SLUG_MAX_LENGTH} characters"
        if _slug_exists(slug_norm, exclude_id=news.id):
            return None, "Slug already in use"
        news.slug = slug_norm
    if summary is not None:
        s = (summary or "").strip() or None
        if s and len(s) > SUMMARY_MAX_LENGTH:
            return None, f"Summary must be at most {SUMMARY_MAX_LENGTH} characters"
        news.summary = s
    if content is not None:
        c = content.strip()
        if not c:
            return None, "Content cannot be empty"
        news.content = c
    if cover_image is not None:
        news.cover_image = (cover_image or "").strip() or None
        if news.cover_image and len(news.cover_image) > COVER_IMAGE_MAX_LENGTH:
            return None, f"Cover image URL must be at most {COVER_IMAGE_MAX_LENGTH} characters"
    if category is not None:
        news.category = (category or "").strip() or None
        if news.category and len(news.category) > CATEGORY_MAX_LENGTH:
            return None, f"Category must be at most {CATEGORY_MAX_LENGTH} characters"

    db.session.commit()
    logger.info("News updated: id=%s", news.id)
    return news, None


def delete_news(news_or_id):
    """Delete a news article. Returns (True, None) or (False, error_message)."""
    news = get_news_by_id(news_or_id) if isinstance(news_or_id, int) else news_or_id
    if not news:
        return False, "News not found"
    db.session.delete(news)
    db.session.commit()
    logger.info("News deleted: id=%s slug=%r", news.id, news.slug)
    return True, None


def publish_news(news_or_id):
    """Set is_published=True and published_at=now. Returns (News, None) or (None, error_message)."""
    news = get_news_by_id(news_or_id) if isinstance(news_or_id, int) else news_or_id
    if not news:
        return None, "News not found"
    news.is_published = True
    if not news.published_at:
        news.published_at = _utc_now()
    db.session.commit()
    logger.info("News published: id=%s", news.id)
    return news, None


def unpublish_news(news_or_id):
    """Set is_published=False. published_at is left as-is. Returns (News, None) or (None, error_message)."""
    news = get_news_by_id(news_or_id) if isinstance(news_or_id, int) else news_or_id
    if not news:
        return None, "News not found"
    news.is_published = False
    db.session.commit()
    logger.info("News unpublished: id=%s", news.id)
    return news, None
