"""Analytics service: deterministic community health metrics and queries."""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import func, and_, or_

from app.extensions import db
from app.models import (
    User, ForumThread, ForumPost, ForumCategory, ForumTag, ForumThreadTag,
    ForumReport, ActivityLog, Role
)


def _utc_now():
    return datetime.now(timezone.utc)


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse YYYY-MM-DD string to UTC datetime at start of day."""
    if not date_str or not date_str.strip():
        return None
    try:
        dt = datetime.strptime(date_str.strip()[:10], "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _date_to_end_of_day(date_dt: datetime) -> datetime:
    """Convert date to end of day (start of next day, exclusive)."""
    return (date_dt + timedelta(days=1)).replace(tzinfo=timezone.utc)


def get_analytics_summary(date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
    """
    Return community summary: user counts, thread/post counts, report queue status.
    Query params: date_from (YYYY-MM-DD), date_to (YYYY-MM-DD) for filtering recent activity.
    If not provided, defaults to last 30 days.
    """
    now = _utc_now()
    default_from = now - timedelta(days=30)

    dt_from = _parse_date(date_from) or default_from
    dt_to = _parse_date(date_to)
    if dt_to:
        dt_to = _date_to_end_of_day(dt_to)
    else:
        dt_to = now

    # Ensure valid range
    if dt_from > dt_to:
        dt_from = dt_to - timedelta(days=30)

    # User counts (lifetime, not time-filtered)
    total_users = db.session.query(func.count(User.id)).scalar() or 0
    verified_users = db.session.query(func.count(User.id)).filter(
        User.email_verified_at.isnot(None)
    ).scalar() or 0
    banned_users = db.session.query(func.count(User.id)).filter(
        User.is_banned.is_(True)
    ).scalar() or 0

    # Active now (last 15 minutes)
    active_cutoff = now - timedelta(minutes=15)
    active_now = db.session.query(func.count(User.id)).filter(
        User.last_seen_at >= active_cutoff
    ).scalar() or 0

    # Thread/post counts (time-filtered)
    threads_created = db.session.query(func.count(ForumThread.id)).filter(
        and_(
            ForumThread.created_at >= dt_from,
            ForumThread.created_at < dt_to,
            ForumThread.deleted_at.is_(None)
        )
    ).scalar() or 0

    posts_created = db.session.query(func.count(ForumPost.id)).filter(
        and_(
            ForumPost.created_at >= dt_from,
            ForumPost.created_at < dt_to,
            ForumPost.deleted_at.is_(None)
        )
    ).scalar() or 0

    # Report queue status
    reports_open = db.session.query(func.count(ForumReport.id)).filter(
        ForumReport.status == "open"
    ).scalar() or 0
    reports_in_review = db.session.query(func.count(ForumReport.id)).filter(
        ForumReport.status == "in_review"
    ).scalar() or 0
    reports_resolved = db.session.query(func.count(ForumReport.id)).filter(
        ForumReport.status == "resolved"
    ).scalar() or 0

    return {
        "summary": {
            "users": {
                "total": total_users,
                "verified": verified_users,
                "banned": banned_users,
                "active_now": active_now,
            },
            "content": {
                "threads_created": threads_created,
                "posts_created": posts_created,
            },
            "reports": {
                "open": reports_open,
                "in_review": reports_in_review,
                "resolved": reports_resolved,
            },
        },
        "query_date": now.isoformat(),
        "date_range": {
            "from": dt_from.isoformat(),
            "to": dt_to.isoformat(),
        },
    }


def get_analytics_timeline(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    metric: Optional[str] = None
) -> Dict[str, Any]:
    """
    Return daily activity counts: threads, posts, reports, moderation actions.
    metric filter: 'threads', 'posts', 'reports', 'actions' or None (all).
    """
    now = _utc_now()
    default_from = now - timedelta(days=30)

    dt_from = _parse_date(date_from) or default_from
    dt_to = _parse_date(date_to)
    if dt_to:
        dt_to = _date_to_end_of_day(dt_to)
    else:
        dt_to = now

    if dt_from > dt_to:
        dt_from = dt_to - timedelta(days=30)

    # Generate date labels for the range
    current = dt_from.replace(hour=0, minute=0, second=0, microsecond=0)
    dates = []
    while current < dt_to:
        dates.append(current)
        current += timedelta(days=1)

    result = {
        "timeline": {},
        "query_date": now.isoformat(),
        "date_range": {
            "from": dt_from.isoformat(),
            "to": dt_to.isoformat(),
        },
    }

    # Threads per day
    if not metric or metric == "threads":
        thread_counts = db.session.query(
            func.date(ForumThread.created_at).label("date"),
            func.count(ForumThread.id).label("count")
        ).filter(
            and_(
                ForumThread.created_at >= dt_from,
                ForumThread.created_at < dt_to,
                ForumThread.deleted_at.is_(None)
            )
        ).group_by(func.date(ForumThread.created_at)).all()

        thread_dict = {}
        for d in thread_counts:
            if d[0]:
                date_str = d[0].isoformat() if hasattr(d[0], 'isoformat') else str(d[0])
                thread_dict[date_str] = d[1]
            else:
                thread_dict[None] = d[1]
        result["timeline"]["threads"] = [
            thread_dict.get(d.isoformat(), 0) for d in dates
        ]

    # Posts per day
    if not metric or metric == "posts":
        post_counts = db.session.query(
            func.date(ForumPost.created_at).label("date"),
            func.count(ForumPost.id).label("count")
        ).filter(
            and_(
                ForumPost.created_at >= dt_from,
                ForumPost.created_at < dt_to,
                ForumPost.deleted_at.is_(None)
            )
        ).group_by(func.date(ForumPost.created_at)).all()

        post_dict = {}
        for d in post_counts:
            if d[0]:
                date_str = d[0].isoformat() if hasattr(d[0], 'isoformat') else str(d[0])
                post_dict[date_str] = d[1]
            else:
                post_dict[None] = d[1]
        result["timeline"]["posts"] = [
            post_dict.get(d.isoformat(), 0) for d in dates
        ]

    # Reports per day
    if not metric or metric == "reports":
        report_counts = db.session.query(
            func.date(ForumReport.created_at).label("date"),
            func.count(ForumReport.id).label("count")
        ).filter(
            and_(
                ForumReport.created_at >= dt_from,
                ForumReport.created_at < dt_to
            )
        ).group_by(func.date(ForumReport.created_at)).all()

        report_dict = {}
        for d in report_counts:
            if d[0]:
                date_str = d[0].isoformat() if hasattr(d[0], 'isoformat') else str(d[0])
                report_dict[date_str] = d[1]
            else:
                report_dict[None] = d[1]
        result["timeline"]["reports"] = [
            report_dict.get(d.isoformat(), 0) for d in dates
        ]

    # Moderation actions per day
    if not metric or metric == "actions":
        action_counts = db.session.query(
            func.date(ActivityLog.created_at).label("date"),
            func.count(ActivityLog.id).label("count")
        ).filter(
            and_(
                ActivityLog.category == "moderation",
                ActivityLog.created_at >= dt_from,
                ActivityLog.created_at < dt_to
            )
        ).group_by(func.date(ActivityLog.created_at)).all()

        action_dict = {}
        for d in action_counts:
            if d[0]:
                date_str = d[0].isoformat() if hasattr(d[0], 'isoformat') else str(d[0])
                action_dict[date_str] = d[1]
            else:
                action_dict[None] = d[1]
        result["timeline"]["actions"] = [
            action_dict.get(d.isoformat(), 0) for d in dates
        ]

    # Include date labels
    result["timeline"]["dates"] = [d.isoformat() for d in dates]

    return result


def get_analytics_users(limit: int = 10, sort_by: Optional[str] = None) -> Dict[str, Any]:
    """
    Return top contributors and user distribution by role.
    sort_by: 'contributions' (default), 'activity', 'joined'
    """
    now = _utc_now()
    limit = max(1, min(limit, 100))

    # Top contributors (by threads + posts created)
    contributors = db.session.query(
        User.id,
        User.username,
        func.count(ForumThread.id).label("threads"),
        func.count(ForumPost.id).label("posts"),
        User.created_at
    ).outerjoin(
        ForumThread, ForumThread.author_id == User.id
    ).outerjoin(
        ForumPost, ForumPost.author_id == User.id
    ).group_by(User.id).all()

    # Calculate totals and sort
    contributor_list = []
    for user_id, username, threads, posts in [(c[0], c[1], c[2], c[3]) for c in contributors]:
        total = (threads or 0) + (posts or 0)
        if total > 0:  # Only include active contributors
            contributor_list.append({
                "user_id": user_id,
                "username": username,
                "threads": threads or 0,
                "posts": posts or 0,
                "total_contributions": total,
            })

    contributor_list.sort(key=lambda x: x["total_contributions"], reverse=True)
    top_contributors = contributor_list[:limit]

    # User distribution by role
    role_dist = db.session.query(
        Role.name,
        func.count(User.id).label("count")
    ).join(
        User, User.role_id == Role.id
    ).group_by(Role.name).all()

    role_distribution = {r[0]: r[1] for r in role_dist}

    return {
        "top_contributors": top_contributors,
        "role_distribution": role_distribution,
        "query_date": now.isoformat(),
        "total_results": len(top_contributors),
    }


def get_analytics_content(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Return popular tags, trending threads, and content freshness distribution.
    """
    now = _utc_now()
    default_from = now - timedelta(days=30)

    dt_from = _parse_date(date_from) or default_from
    dt_to = _parse_date(date_to)
    if dt_to:
        dt_to = _date_to_end_of_day(dt_to)
    else:
        dt_to = now

    limit = max(1, min(limit, 100))

    # Popular tags (by thread count)
    popular_tags = db.session.query(
        ForumTag.id,
        ForumTag.label,
        ForumTag.slug,
        func.count(ForumThreadTag.thread_id).label("thread_count")
    ).outerjoin(
        ForumThreadTag, ForumThreadTag.tag_id == ForumTag.id
    ).group_by(ForumTag.id).order_by(
        func.count(ForumThreadTag.thread_id).desc()
    ).limit(limit).all()

    tags_result = [
        {
            "tag_id": t[0],
            "label": t[1],
            "slug": t[2],
            "thread_count": t[3] or 0,
        }
        for t in popular_tags
    ]

    # Trending threads (recent, high engagement)
    trending_threads = db.session.query(
        ForumThread.id,
        ForumThread.title,
        ForumThread.slug,
        ForumThread.reply_count,
        ForumThread.view_count,
        ForumThread.created_at,
        ForumThread.last_post_at,
        User.username
    ).join(
        User, ForumThread.author_id == User.id, isouter=True
    ).filter(
        and_(
            ForumThread.created_at >= dt_from,
            ForumThread.created_at < dt_to,
            ForumThread.deleted_at.is_(None)
        )
    ).order_by(
        ForumThread.last_post_at.desc().nulls_last()
    ).limit(limit).all()

    threads_result = [
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
        for t in trending_threads
    ]

    # Content freshness distribution
    now_dt = _utc_now()
    cutoff_new = now_dt - timedelta(days=7)
    cutoff_recent = now_dt - timedelta(days=30)

    new_count = db.session.query(func.count(ForumThread.id)).filter(
        and_(
            ForumThread.created_at >= cutoff_new,
            ForumThread.deleted_at.is_(None)
        )
    ).scalar() or 0

    recent_count = db.session.query(func.count(ForumThread.id)).filter(
        and_(
            ForumThread.created_at >= cutoff_recent,
            ForumThread.created_at < cutoff_new,
            ForumThread.deleted_at.is_(None)
        )
    ).scalar() or 0

    old_count = db.session.query(func.count(ForumThread.id)).filter(
        and_(
            ForumThread.created_at < cutoff_recent,
            ForumThread.deleted_at.is_(None)
        )
    ).scalar() or 0

    freshness = {
        "new": {"label": "< 7 days", "count": new_count},
        "recent": {"label": "7-30 days", "count": recent_count},
        "old": {"label": "> 30 days", "count": old_count},
    }

    return {
        "popular_tags": tags_result,
        "trending_threads": threads_result,
        "content_freshness": freshness,
        "query_date": now.isoformat(),
        "date_range": {
            "from": dt_from.isoformat(),
            "to": dt_to.isoformat(),
        },
    }


def get_analytics_moderation(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    priority_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Return report queue status, resolution trends, and moderator activity.
    """
    now = _utc_now()
    default_from = now - timedelta(days=30)

    dt_from = _parse_date(date_from) or default_from
    dt_to = _parse_date(date_to)
    if dt_to:
        dt_to = _date_to_end_of_day(dt_to)
    else:
        dt_to = now

    # Report queue status (overall)
    queue_status = db.session.query(
        ForumReport.status,
        func.count(ForumReport.id).label("count")
    ).group_by(ForumReport.status).all()

    queue_dict = {r[0]: r[1] for r in queue_status}

    # Recent reports (for timeline)
    recent_reports = db.session.query(
        func.date(ForumReport.created_at).label("date"),
        func.count(ForumReport.id).label("count")
    ).filter(
        and_(
            ForumReport.created_at >= dt_from,
            ForumReport.created_at < dt_to
        )
    ).group_by(func.date(ForumReport.created_at)).all()

    reports_by_date = {}
    for r in recent_reports:
        if r[0]:
            date_str = r[0].isoformat() if hasattr(r[0], 'isoformat') else str(r[0])
            reports_by_date[date_str] = r[1]
        else:
            reports_by_date[None] = r[1]

    # Moderation actions (who did what)
    mod_actions = db.session.query(
        ActivityLog.action,
        func.count(ActivityLog.id).label("count")
    ).filter(
        and_(
            ActivityLog.category == "moderation",
            ActivityLog.created_at >= dt_from,
            ActivityLog.created_at < dt_to
        )
    ).group_by(ActivityLog.action).all()

    actions_dict = {m[0]: m[1] for m in mod_actions}

    # Average resolution time (for resolved reports)
    resolved_reports = db.session.query(
        ForumReport.created_at,
        ForumReport.handled_at
    ).filter(
        and_(
            ForumReport.status == "resolved",
            ForumReport.handled_at.isnot(None),
            ForumReport.handled_at >= dt_from,
            ForumReport.handled_at < dt_to
        )
    ).all()

    resolution_times = []
    for created, handled in resolved_reports:
        if created and handled:
            delta = (handled - created).total_seconds() / 86400  # Convert to days
            resolution_times.append(delta)

    avg_resolution_days = sum(resolution_times) / len(resolution_times) if resolution_times else 0.0

    return {
        "queue_status": queue_dict,
        "reports_by_date": reports_by_date,
        "moderation_actions": actions_dict,
        "average_resolution_days": round(avg_resolution_days, 2),
        "total_resolved_in_period": len(resolution_times),
        "query_date": now.isoformat(),
        "date_range": {
            "from": dt_from.isoformat(),
            "to": dt_to.isoformat(),
        },
    }
