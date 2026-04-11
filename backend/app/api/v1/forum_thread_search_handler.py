"""Forum thread search — validation, query build, response (DS-050)."""

from __future__ import annotations

from flask import jsonify, request

from app.api.v1.forum_routes_helpers import _current_user_optional, _parse_int
from app.extensions import db
from app.services.forum_service import user_is_moderator
from app.services.search_utils import _escape_sql_like_wildcards


def run_forum_thread_search():
    """
    Search over thread titles and optionally post content with filters.
    Same contract as ``forum_routes.forum_search`` (OpenAPI / status codes).
    """
    from app.models import ForumThread, ForumPost, ForumCategory, ForumThreadTag

    user = _current_user_optional()

    q_raw = (request.args.get("q") or "").strip()
    page = _parse_int(request.args.get("page"), 1, min_val=1, max_val=10000)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    category_slug = (request.args.get("category") or "").strip() or None
    status_filter = (request.args.get("status") or "").strip() or None
    tag_slug = (request.args.get("tag") or "").strip().lower() or None
    include_content = request.args.get("include_content", "").strip().lower() in ("1", "true", "yes")

    if not q_raw and not category_slug and not status_filter and not tag_slug:
        return jsonify(
            {
                "items": [],
                "total": 0,
                "page": page,
                "per_page": limit,
            }
        ), 200

    if q_raw and len(q_raw) < 3:
        return jsonify(
            {
                "error": "Search query must be at least 3 characters",
                "items": [],
                "total": 0,
                "page": page,
                "per_page": limit,
            }
        ), 400

    if len(q_raw) > 500:
        q_raw = q_raw[:500]

    q_escaped = _escape_sql_like_wildcards(q_raw)
    like_pattern = f"%{q_escaped}%" if q_escaped else None

    is_mod = user_is_moderator(user) if user else False

    q = ForumThread.query
    if not is_mod:
        q = q.filter(ForumThread.status.notin_(("deleted", "hidden")))
    else:
        q = q.filter(ForumThread.status != "deleted")

    if like_pattern:
        q = q.filter(ForumThread.title.ilike(like_pattern, escape="\\"))

    q = q.join(ForumCategory, ForumCategory.id == ForumThread.category_id)
    if not is_mod:
        q = q.filter(ForumCategory.is_active.is_(True))
        q = q.filter(ForumCategory.is_private.is_(False))
    if category_slug:
        q = q.filter(ForumCategory.slug == category_slug)

    if status_filter:
        if status_filter not in ("open", "locked", "archived", "hidden"):
            return jsonify(
                {
                    "error": (
                        f"Invalid status filter: {status_filter}. "
                        "Must be one of: open, locked, archived, hidden"
                    ),
                    "items": [],
                    "total": 0,
                    "page": page,
                    "per_page": limit,
                }
            ), 400
        q = q.filter(ForumThread.status == status_filter)

    if tag_slug:
        from app.models import ForumTag as ForumTagModel

        q = (
            q.join(ForumThreadTag, ForumThreadTag.thread_id == ForumThread.id)
            .join(ForumTagModel, ForumTagModel.id == ForumThreadTag.tag_id)
            .filter(ForumTagModel.slug == tag_slug)
        )

    if include_content and like_pattern and len(q_raw) >= 3:
        from sqlalchemy import select

        sub = select(ForumPost.thread_id).where(ForumPost.content.ilike(like_pattern, escape="\\"))
        q = q.filter(
            db.or_(
                ForumThread.title.ilike(like_pattern, escape="\\"),
                ForumThread.id.in_(sub),
            )
        )

    q = q.order_by(
        ForumThread.is_pinned.desc(),
        ForumThread.last_post_at.desc().nullslast(),
        ForumThread.id.asc(),
    )
    total = q.count()
    page = max(1, page)
    limit = max(1, min(limit, 100))
    offset = (page - 1) * limit
    items = q.offset(offset).limit(limit).all()

    items_data = []
    for t in items:
        d = t.to_dict()
        d["author_username"] = t.author.username if t.author else None
        items_data.append(d)

    return jsonify(
        {
            "items": items_data,
            "total": total,
            "page": page,
            "per_page": limit,
        }
    ), 200
