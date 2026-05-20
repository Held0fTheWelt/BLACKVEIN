"""Analytics content aggregation (popular tags, trending threads, freshness) — DS-024 split."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import and_, func

from app.extensions import db
from app.models import ForumTag, ForumThread, ForumThreadTag, User


def _query_popular_tags(limit: int) -> List[Dict[str, Any]]:
    rows = (
        db.session.query(
            ForumTag.id,
            ForumTag.label,
            ForumTag.slug,
            func.count(ForumThreadTag.thread_id).label("thread_count"),
        )
        .outerjoin(ForumThreadTag, ForumThreadTag.tag_id == ForumTag.id)
        .group_by(ForumTag.id)
        .order_by(func.count(ForumThreadTag.thread_id).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "tag_id": t[0],
            "label": t[1],
            "slug": t[2],
            "thread_count": t[3] or 0,
        }
        for t in rows
    ]


def _query_trending_threads(
    dt_from: datetime,
    dt_to: datetime,
    limit: int,
) -> List[Dict[str, Any]]:
    rows = (
        db.session.query(
            ForumThread.id,
            ForumThread.title,
            ForumThread.slug,
            ForumThread.reply_count,
            ForumThread.view_count,
            ForumThread.created_at,
            ForumThread.last_post_at,
            User.username,
        )
        .join(User, ForumThread.author_id == User.id, isouter=True)
        .filter(
            and_(
                ForumThread.created_at >= dt_from,
                ForumThread.created_at < dt_to,
                ForumThread.deleted_at.is_(None),
            )
        )
        .order_by(ForumThread.last_post_at.desc().nulls_last())
        .limit(limit)
        .all()
    )
    return [
        {
            "thread_id": t[0],
            "title": t[1],
            "slug": t[2],
            "replies": t[3],
            "views": t[4],
            "created_at": t[5].isoformat() if t[5] else None,
            "last_activity": t[6].isoformat() if t[6] else None,
            "author": t[7],
        }
        for t in rows
    ]


def _query_content_freshness(now: datetime) -> Dict[str, Dict[str, Any]]:
    cutoff_new = now - timedelta(days=7)
    cutoff_recent = now - timedelta(days=30)

    new_count = (
        db.session.query(func.count(ForumThread.id))
        .filter(
            and_(
                ForumThread.created_at >= cutoff_new,
                ForumThread.deleted_at.is_(None),
            )
        )
        .scalar()
        or 0
    )

    recent_count = (
        db.session.query(func.count(ForumThread.id))
        .filter(
            and_(
                ForumThread.created_at >= cutoff_recent,
                ForumThread.created_at < cutoff_new,
                ForumThread.deleted_at.is_(None),
            )
        )
        .scalar()
        or 0
    )

    old_count = (
        db.session.query(func.count(ForumThread.id))
        .filter(
            and_(
                ForumThread.created_at < cutoff_recent,
                ForumThread.deleted_at.is_(None),
            )
        )
        .scalar()
        or 0
    )

    return {
        "new": {"label": "< 7 days", "count": new_count},
        "recent": {"label": "7-30 days", "count": recent_count},
        "old": {"label": "> 30 days", "count": old_count},
    }


def build_analytics_content_payload(
    *,
    dt_from: datetime,
    dt_to: datetime,
    now: datetime,
    limit: int,
) -> Dict[str, Any]:
    """Assemble popular_tags, trending_threads, and content_freshness for the given window."""
    lim = max(1, min(limit, 100))
    return {
        "popular_tags": _query_popular_tags(lim),
        "trending_threads": _query_trending_threads(dt_from, dt_to, lim),
        "content_freshness": _query_content_freshness(now),
        "query_date": now.isoformat(),
        "date_range": {
            "from": dt_from.isoformat(),
            "to": dt_to.isoformat(),
        },
    }
