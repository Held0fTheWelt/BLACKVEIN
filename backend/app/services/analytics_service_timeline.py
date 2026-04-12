"""Daily timeline queries for analytics_service (DS-007)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import and_, func

from app.extensions import db
from app.models import ActivityLog, ForumPost, ForumReport, ForumThread
from app.utils.time_utils import utc_now as _utc_now
from app.services._analytics_utils import _parse_date, _date_to_end_of_day


def timeline_range_and_dates(
    date_from: Optional[str],
    date_to: Optional[str],
) -> tuple[datetime, datetime, list[datetime]]:
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
    current = dt_from.replace(hour=0, minute=0, second=0, microsecond=0)
    dates: list[datetime] = []
    while current < dt_to:
        dates.append(current)
        current += timedelta(days=1)
    return dt_from, dt_to, dates


def _counts_by_date(
    *,
    model,
    created_attr,
    dt_from: datetime,
    dt_to: datetime,
    extra_filters: tuple[Any, ...] = (),
) -> dict[str | None, int]:
    q = (
        db.session.query(func.date(created_attr).label("date"), func.count(model.id).label("count"))
        .filter(
            and_(
                created_attr >= dt_from,
                created_attr < dt_to,
                *extra_filters,
            )
        )
        .group_by(func.date(created_attr))
    )
    rows = q.all()
    out: dict[str | None, int] = {}
    for d in rows:
        if d[0]:
            date_str = d[0].isoformat() if hasattr(d[0], "isoformat") else str(d[0])
            out[date_str] = d[1]
        else:
            out[None] = d[1]
    return out


def threads_per_day(dt_from: datetime, dt_to: datetime, dates: list[datetime]) -> list[int]:
    dct = _counts_by_date(
        model=ForumThread,
        created_attr=ForumThread.created_at,
        dt_from=dt_from,
        dt_to=dt_to,
        extra_filters=(ForumThread.deleted_at.is_(None),),
    )
    return [dct.get(d.isoformat(), 0) for d in dates]


def posts_per_day(dt_from: datetime, dt_to: datetime, dates: list[datetime]) -> list[int]:
    dct = _counts_by_date(
        model=ForumPost,
        created_attr=ForumPost.created_at,
        dt_from=dt_from,
        dt_to=dt_to,
        extra_filters=(ForumPost.deleted_at.is_(None),),
    )
    return [dct.get(d.isoformat(), 0) for d in dates]


def reports_per_day(dt_from: datetime, dt_to: datetime, dates: list[datetime]) -> list[int]:
    dct = _counts_by_date(
        model=ForumReport,
        created_attr=ForumReport.created_at,
        dt_from=dt_from,
        dt_to=dt_to,
    )
    return [dct.get(d.isoformat(), 0) for d in dates]


def moderation_actions_per_day(dt_from: datetime, dt_to: datetime, dates: list[datetime]) -> list[int]:
    dct = _counts_by_date(
        model=ActivityLog,
        created_attr=ActivityLog.created_at,
        dt_from=dt_from,
        dt_to=dt_to,
        extra_filters=(ActivityLog.category == "moderation",),
    )
    return [dct.get(d.isoformat(), 0) for d in dates]


def build_analytics_timeline_payload(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    metric: Optional[str] = None,
) -> dict[str, Any]:
    now = _utc_now()
    dt_from, dt_to, dates = timeline_range_and_dates(date_from, date_to)
    result: dict[str, Any] = {
        "timeline": {},
        "query_date": now.isoformat(),
        "date_range": {
            "from": dt_from.isoformat(),
            "to": dt_to.isoformat(),
        },
    }
    if not metric or metric == "threads":
        result["timeline"]["threads"] = threads_per_day(dt_from, dt_to, dates)
    if not metric or metric == "posts":
        result["timeline"]["posts"] = posts_per_day(dt_from, dt_to, dates)
    if not metric or metric == "reports":
        result["timeline"]["reports"] = reports_per_day(dt_from, dt_to, dates)
    if not metric or metric == "actions":
        result["timeline"]["actions"] = moderation_actions_per_day(dt_from, dt_to, dates)
    result["timeline"]["dates"] = [d.isoformat() for d in dates]
    return result
