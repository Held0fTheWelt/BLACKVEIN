"""Forum thread search — parse, query build, pagination + JSON (DS-021)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from flask import jsonify, request

from app.api.v1.forum_routes_helpers import _current_user_optional, _parse_int
from app.extensions import db
from app.services.content.forum_service import user_is_moderator
from app.services.common.search_utils import _escape_sql_like_wildcards


@dataclass
class ForumThreadSearchInput:
    """Validated request inputs for thread search (after arg parse + trimming)."""

    user: Any
    q_raw: str
    page: int
    limit: int
    category_slug: Optional[str]
    status_filter: Optional[str]
    tag_slug: Optional[str]
    include_content: bool
    q_escaped: str
    like_pattern: Optional[str]


def _thread_search_parse_input() -> ForumThreadSearchInput:
    user = _current_user_optional()
    q_raw = (request.args.get("q") or "").strip()
    page = _parse_int(request.args.get("page"), 1, min_val=1, max_val=10000)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    category_slug = (request.args.get("category") or "").strip() or None
    status_filter = (request.args.get("status") or "").strip() or None
    tag_slug = (request.args.get("tag") or "").strip().lower() or None
    include_content = request.args.get("include_content", "").strip().lower() in ("1", "true", "yes")

    if len(q_raw) > 500:
        q_raw = q_raw[:500]

    q_escaped = _escape_sql_like_wildcards(q_raw)
    like_pattern = f"%{q_escaped}%" if q_escaped else None

    return ForumThreadSearchInput(
        user=user,
        q_raw=q_raw,
        page=page,
        limit=limit,
        category_slug=category_slug,
        status_filter=status_filter,
        tag_slug=tag_slug,
        include_content=include_content,
        q_escaped=q_escaped,
        like_pattern=like_pattern,
    )


def _thread_search_early_listing_or_bad_query(
    inp: ForumThreadSearchInput,
) -> Optional[Tuple[Any, int]]:
    """Empty filter shortcut, or 400 when text query is too short."""
    if not inp.q_raw and not inp.category_slug and not inp.status_filter and not inp.tag_slug:
        return (
            jsonify(
                {
                    "items": [],
                    "total": 0,
                    "page": inp.page,
                    "per_page": inp.limit,
                }
            ),
            200,
        )
    if inp.q_raw and len(inp.q_raw) < 3:
        return (
            jsonify(
                {
                    "error": "Search query must be at least 3 characters",
                    "items": [],
                    "total": 0,
                    "page": inp.page,
                    "per_page": inp.limit,
                }
            ),
            400,
        )
    return None


def _thread_search_build_query(inp: ForumThreadSearchInput) -> Tuple[Any, Optional[Tuple[Any, int]]]:
    """Return ``(query, error_response)``; ``error_response`` set on invalid status filter."""
    from app.models import ForumThread, ForumPost, ForumCategory, ForumThreadTag

    is_mod = user_is_moderator(inp.user) if inp.user else False

    q = ForumThread.query
    if not is_mod:
        q = q.filter(ForumThread.status.notin_(("deleted", "hidden")))
    else:
        q = q.filter(ForumThread.status != "deleted")

    if inp.like_pattern:
        q = q.filter(ForumThread.title.ilike(inp.like_pattern, escape="\\"))

    q = q.join(ForumCategory, ForumCategory.id == ForumThread.category_id)
    if not is_mod:
        q = q.filter(ForumCategory.is_active.is_(True))
        q = q.filter(ForumCategory.is_private.is_(False))
    if inp.category_slug:
        q = q.filter(ForumCategory.slug == inp.category_slug)

    if inp.status_filter:
        if inp.status_filter not in ("open", "locked", "archived", "hidden"):
            err = (
                jsonify(
                    {
                        "error": (
                            f"Invalid status filter: {inp.status_filter}. "
                            "Must be one of: open, locked, archived, hidden"
                        ),
                        "items": [],
                        "total": 0,
                        "page": inp.page,
                        "per_page": inp.limit,
                    }
                ),
                400,
            )
            return q, err
        q = q.filter(ForumThread.status == inp.status_filter)

    if inp.tag_slug:
        from app.models import ForumTag as ForumTagModel

        q = (
            q.join(ForumThreadTag, ForumThreadTag.thread_id == ForumThread.id)
            .join(ForumTagModel, ForumTagModel.id == ForumThreadTag.tag_id)
            .filter(ForumTagModel.slug == inp.tag_slug)
        )

    if inp.include_content and inp.like_pattern and len(inp.q_raw) >= 3:
        from sqlalchemy import select

        sub = select(ForumPost.thread_id).where(ForumPost.content.ilike(inp.like_pattern, escape="\\"))
        q = q.filter(
            db.or_(
                ForumThread.title.ilike(inp.like_pattern, escape="\\"),
                ForumThread.id.in_(sub),
            )
        )

    q = q.order_by(
        ForumThread.is_pinned.desc(),
        ForumThread.last_post_at.desc().nullslast(),
        ForumThread.id.asc(),
    )
    return q, None


def _thread_search_paginate_and_jsonify(q: Any, inp: ForumThreadSearchInput) -> Tuple[Any, int]:
    total = q.count()
    page = max(1, inp.page)
    limit = max(1, min(inp.limit, 100))
    offset = (page - 1) * limit
    items = q.offset(offset).limit(limit).all()

    items_data = []
    for t in items:
        d = t.to_dict()
        d["author_username"] = t.author.username if t.author else None
        items_data.append(d)

    return (
        jsonify(
            {
                "items": items_data,
                "total": total,
                "page": page,
                "per_page": limit,
            }
        ),
        200,
    )


def execute_forum_thread_search() -> Tuple[Any, int]:
    """Same contract as ``forum_thread_search_handler.run_forum_thread_search``."""
    inp = _thread_search_parse_input()
    early = _thread_search_early_listing_or_bad_query(inp)
    if early is not None:
        return early

    q, err = _thread_search_build_query(inp)
    if err is not None:
        return err

    return _thread_search_paginate_and_jsonify(q, inp)
