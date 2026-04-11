"""Forum tag discovery under /forum/tags/* (register on api_v1_bp)."""

from __future__ import annotations

from flask import jsonify, request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.api.v1.forum_routes_helpers import _parse_int
from app.extensions import db, limiter


@api_v1_bp.route("/forum/tags/popular", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def forum_tags_popular():
    """
    Get popular tags across all threads.
    Query: limit (default 20, max 100).
    Returns list of tags with label, slug, thread_count.
    """
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)

    from app.models import ForumTag, ForumThreadTag, ForumThread

    tags_data = db.session.query(
        ForumTag.id,
        ForumTag.label,
        ForumTag.slug,
        db.func.count(ForumThreadTag.thread_id).label("thread_count"),
    ).outerjoin(ForumThreadTag, ForumTag.id == ForumThreadTag.tag_id).outerjoin(
        ForumThread, ForumThreadTag.thread_id == ForumThread.id
    ).filter(ForumThread.status.notin_(("deleted",))).group_by(
        ForumTag.id, ForumTag.label, ForumTag.slug
    ).order_by(db.func.count(ForumThreadTag.thread_id).desc()).limit(limit).all()

    tags = [
        {
            "id": tag[0],
            "label": tag[1],
            "slug": tag[2],
            "thread_count": tag[3] or 0,
        }
        for tag in tags_data
    ]

    return jsonify({"items": tags}), 200


@api_v1_bp.route("/forum/tags/<slug>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def forum_tag_detail(slug):
    """
    Get tag details with threads using this tag.
    Query: page, limit.
    Returns tag info and paginated list of threads.
    """
    from app.models import ForumTag, ForumThreadTag, ForumThread

    tag = ForumTag.query.filter_by(slug=slug).first()
    if not tag:
        return jsonify({"error": "Tag not found"}), 404

    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)

    threads_query = (
        ForumThread.query.join(ForumThreadTag, ForumThread.id == ForumThreadTag.thread_id)
        .filter(
            ForumThreadTag.tag_id == tag.id,
            ForumThread.status.notin_(("deleted",)),
        )
        .order_by(ForumThread.created_at.desc())
    )

    total = threads_query.count()
    threads = threads_query.offset((page - 1) * limit).limit(limit).all()

    return jsonify({
        "tag": {
            "id": tag.id,
            "label": tag.label,
            "slug": tag.slug,
        },
        "threads": [
            {
                "id": t.id,
                "title": t.title,
                "slug": t.slug,
                "author_id": t.author_id,
                "author_username": t.author.username if t.author else None,
                "post_count": t.reply_count,
                "view_count": t.view_count,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in threads
        ],
        "total": total,
        "page": page,
        "per_page": limit,
    }), 200
