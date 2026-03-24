"""Centralized activity logging for admin dashboard. Do not spread raw ActivityLog inserts elsewhere."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import or_

from app.extensions import db
from app.models import ActivityLog, User


def log_activity(
    *,
    actor: User | None = None,
    category: str,
    action: str,
    status: str = "info",
    message: str | None = None,
    route: str | None = None,
    method: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    target_type: str | None = None,
    target_id: str | int | None = None,
    actor_username_snapshot: str | None = None,
) -> ActivityLog:
    """
    Create a structured activity log entry. Use this from routes and services;
    do not write to ActivityLog directly elsewhere.
    """
    actor_user_id = None
    actor_username_snapshot_final = actor_username_snapshot
    actor_role_snapshot = None
    if actor is not None:
        actor_user_id = actor.id
        if actor_username_snapshot_final is None:
            actor_username_snapshot_final = actor.username
        actor_role_snapshot = getattr(actor, "role", None)
        if actor_role_snapshot is None and hasattr(actor, "role_rel") and actor.role_rel:
            actor_role_snapshot = actor.role_rel.name

    tags = list(tags) if tags else []
    meta = dict(metadata) if metadata else {}
    target_id_str = str(target_id) if target_id is not None else None

    entry = ActivityLog(
        actor_user_id=actor_user_id,
        actor_username_snapshot=actor_username_snapshot_final,
        actor_role_snapshot=actor_role_snapshot,
        category=(category or "system").strip()[:32],
        action=(action or "unknown").strip()[:64],
        status=(status or "info").strip()[:20],
        message=(message or "")[:512] if message else None,
        route=(route or "")[:256] if route else None,
        method=(method or "")[:10] if method else None,
        tags=tags if tags else None,
        meta=meta if meta else None,
        target_type=(target_type or "")[:64] if target_type else None,
        target_id=target_id_str,
    )
    db.session.add(entry)
    db.session.commit()
    db.session.refresh(entry)
    return entry


def list_activity_logs(
    page: int = 1,
    limit: int = 50,
    q: str | None = None,
    category: str | None = None,
    action: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """
    Return (list of ActivityLog, total count) for admin logs API.
    Newest first. Filters: q (search message, action, actor_username_snapshot), category, action, status, date_from, date_to.
    """
    query = ActivityLog.query
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                ActivityLog.message.ilike(term),
                ActivityLog.action.ilike(term),
                ActivityLog.actor_username_snapshot.ilike(term),
            )
        )
    if category and category.strip():
        query = query.filter(ActivityLog.category == category.strip())
    if action and action.strip():
        query = query.filter(ActivityLog.action == action.strip())
    if status and status.strip():
        query = query.filter(ActivityLog.status == status.strip())
    if date_from and date_from.strip():
        try:
            # YYYY-MM-DD -> start of day UTC
            dt = datetime.strptime(date_from.strip()[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.filter(ActivityLog.created_at >= dt)
        except ValueError:
            pass
    if date_to and date_to.strip():
        try:
            # YYYY-MM-DD -> end of day UTC
            dt = datetime.strptime(date_to.strip()[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            dt = dt + timedelta(days=1)
            query = query.filter(ActivityLog.created_at < dt)
        except ValueError:
            pass
    total = query.count()
    query = query.order_by(ActivityLog.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    return query.all(), total
