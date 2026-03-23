"""
Real dashboard metrics from persisted user data only.
No fake revenue, sessions, or conversion. Definitions:
- Active now: users with last_seen_at within the last 15 minutes.
- Active users over time: distinct users with last_seen_at in each time bucket.
- User growth: cumulative count of users with created_at <= end of each bucket.
"""
from datetime import datetime, timezone, timedelta

from sqlalchemy import and_, distinct, func, or_

from app.extensions import db
from app.models import User

ACTIVE_NOW_WINDOW_MINUTES = 15
VALID_RANGES = ("24h", "7d", "30d", "12m")


def _utc_now():
    return datetime.now(timezone.utc)


def _range_end_and_buckets(range_key: str):
    """Return (range_end_utc, list of (bucket_start, bucket_end) in UTC)."""
    now = _utc_now()
    if range_key == "24h":
        end = now
        start = end - timedelta(hours=24)
        buckets = []
        for i in range(24):
            b_end = start + timedelta(hours=i + 1)
            b_start = start + timedelta(hours=i)
            buckets.append((b_start, b_end))
        return end, buckets
    if range_key == "7d":
        end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        start = end - timedelta(days=7)
        buckets = []
        for i in range(7):
            b_start = start + timedelta(days=i)
            b_end = b_start + timedelta(days=1)
            buckets.append((b_start, b_end))
        return end, buckets
    if range_key == "30d":
        end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        start = end - timedelta(days=30)
        buckets = []
        for i in range(30):
            b_start = start + timedelta(days=i)
            b_end = b_start + timedelta(days=1)
            buckets.append((b_start, b_end))
        return end, buckets
    if range_key == "12m":
        end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=365)
        buckets = []
        for i in range(12):
            b_start = start + timedelta(days=30 * i)
            b_end = start + timedelta(days=30 * (i + 1))
            buckets.append((b_start, b_end))
        return end, buckets
    return now, []


def get_metrics(range_key: str):
    """
    Return dict: active_now, registered_total, verified_total, banned_total,
    active_users_over_time, user_growth_over_time, selected_range, bucket_info.
    All values from real user data. range_key must be 24h|7d|30d|12m.
    """
    if range_key not in VALID_RANGES:
        range_key = "24h"

    now = _utc_now()
    active_cutoff = now - timedelta(minutes=ACTIVE_NOW_WINDOW_MINUTES)

    active_now = db.session.query(func.count(User.id)).filter(
        User.last_seen_at >= active_cutoff
    ).scalar() or 0

    registered_total = db.session.query(func.count(User.id)).scalar() or 0
    verified_total = db.session.query(func.count(User.id)).filter(
        User.email_verified_at.isnot(None)
    ).scalar() or 0
    banned_total = db.session.query(func.count(User.id)).filter(User.is_banned.is_(True)).scalar() or 0

    range_end, buckets = _range_end_and_buckets(range_key)
    bucket_labels = []
    active_users_over_time = []
    user_growth_over_time = []

    for b_start, b_end in buckets:
        if range_key == "24h":
            bucket_labels.append(b_start.strftime("%H:%M"))
        elif range_key in ("7d", "30d"):
            bucket_labels.append(b_start.strftime("%Y-%m-%d"))
        else:
            bucket_labels.append(b_start.strftime("%Y-%m"))

        active_in_bucket = db.session.query(func.count(distinct(User.id))).filter(
            and_(
                User.last_seen_at >= b_start,
                User.last_seen_at < b_end,
            )
        ).scalar() or 0
        active_users_over_time.append(active_in_bucket)

        growth_at_end = db.session.query(func.count(User.id)).filter(
            or_(User.created_at <= b_end, User.created_at.is_(None))
        ).scalar() or 0
        user_growth_over_time.append(growth_at_end)

    return {
        "active_now": active_now,
        "registered_total": registered_total,
        "verified_total": verified_total,
        "banned_total": banned_total,
        "active_users_over_time": active_users_over_time,
        "user_growth_over_time": user_growth_over_time,
        "selected_range": range_key,
        "bucket_labels": bucket_labels,
        "bucket_info": {
            "range": range_key,
            "bucket_count": len(buckets),
        },
    }
