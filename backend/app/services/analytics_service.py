"""Analytics service: deterministic community health metrics and queries."""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import func, and_, or_

from app.extensions import db
from app.models import (
    User, ForumThread, ForumPost,
    ForumReport, ActivityLog, Role
)
from app.services.analytics_service_content import build_analytics_content_payload
from app.services.analytics_service_timeline import build_analytics_timeline_payload
from app.utils.time_utils import utc_now as _utc_now
from app.services._analytics_utils import _parse_date, _date_to_end_of_day


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
    return build_analytics_timeline_payload(date_from=date_from, date_to=date_to, metric=metric)


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

    return build_analytics_content_payload(dt_from=dt_from, dt_to=dt_to, now=now, limit=limit)


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
