"""Public read-only news API. Only published news is exposed.

List:  GET /api/v1/news?q=&sort=published_at&direction=desc&page=1&limit=20&category=
  Response: { "items": [ { "id", "title", "slug", "summary", "content", "author_id", "author_name",
    "is_published", "published_at", "created_at", "updated_at", "cover_image", "category" } ], "total", "page", "per_page" }

Detail: GET /api/v1/news/<id>
  Response: single object same shape as list item, or { "error": "Not found" } 404.

Write (all require Authorization: Bearer <JWT> and editor/admin role; 401 if missing/invalid token, 403 if forbidden):
  POST   /api/v1/news             -> create (body: title, slug, content; optional summary, is_published, cover_image, category)
  PUT    /api/v1/news/<id>        -> update (body: optional title, slug, summary, content, cover_image, category)
  DELETE /api/v1/news/<id>        -> delete
  POST   /api/v1/news/<id>/publish   -> set published
  POST   /api/v1/news/<id>/unpublish -> set unpublished
"""
from datetime import datetime, timezone

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.auth import current_user_can_write_news
from app.extensions import limiter
from app.services.news_service import (
    SORT_FIELDS,
    SORT_ORDERS,
    create_news,
    delete_news,
    get_news_by_id,
    list_news,
    publish_news,
    unpublish_news,
    update_news,
)


def _parse_int(value, default, min_val=None, max_val=None):
    """Parse query param as int; return default if missing/invalid."""
    if value is None:
        return default
    try:
        n = int(value)
        if min_val is not None and n < min_val:
            return default
        if max_val is not None and n > max_val:
            return max_val
        return n
    except (TypeError, ValueError):
        return default


@api_v1_bp.route("/news", methods=["GET"])
@limiter.limit("60 per minute")
def news_list():
    """
    List published news. Query params: q (search), sort, direction, page, limit, category.
    Response: { "items": [...], "total": N, "page": P, "per_page": L }.
    """
    q = request.args.get("q", "").strip() or None
    sort = request.args.get("sort", "published_at").strip() or "published_at"
    if sort not in SORT_FIELDS:
        sort = "published_at"
    direction = request.args.get("direction", "desc").strip().lower() or "desc"
    if direction not in SORT_ORDERS:
        direction = "desc"
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    category = request.args.get("category", "").strip() or None

    items, total = list_news(
        published_only=True,
        search=q,
        sort=sort,
        order=direction,
        page=page,
        per_page=limit,
        category=category,
    )
    return jsonify({
        "items": [n.to_dict() for n in items],
        "total": total,
        "page": page,
        "per_page": limit,
    }), 200


@api_v1_bp.route("/news/<int:news_id>", methods=["GET"])
@limiter.limit("60 per minute")
def news_detail(news_id):
    """
    Get a single published news article by id. 404 if not found or not published.
    Response: single news object (id, title, slug, summary, content, author_id, author_name, ...).
    """
    news = get_news_by_id(news_id)
    if not news or not news.is_published:
        return jsonify({"error": "Not found"}), 404
    now = datetime.now(timezone.utc)
    if news.published_at is not None:
        pub_at = news.published_at
        if pub_at.tzinfo is None:
            pub_at = pub_at.replace(tzinfo=timezone.utc)
        if pub_at > now:
            return jsonify({"error": "Not found"}), 404
    return jsonify(news.to_dict()), 200


# --- Protected write endpoints (JWT required) ---


@api_v1_bp.route("/news", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def news_create():
    """
    Create a news article. Requires JWT and editor/admin role. Body: title, slug, content; optional summary, is_published, cover_image, category.
    author_id is set from JWT identity.
    """
    if not current_user_can_write_news():
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    title = (data.get("title") or "").strip()
    slug = (data.get("slug") or "").strip()
    content = (data.get("content") or "").strip()
    if not title or not slug or not content:
        return jsonify({"error": "title, slug, and content are required"}), 400
    try:
        author_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid token"}), 401
    summary = data.get("summary")
    if summary is not None:
        summary = (summary or "").strip() or None
    is_published = bool(data.get("is_published", False))
    cover_image = data.get("cover_image")
    if cover_image is not None:
        cover_image = (cover_image or "").strip() or None
    category = data.get("category")
    if category is not None:
        category = (category or "").strip() or None

    news, err = create_news(
        title=title,
        slug=slug,
        content=content,
        summary=summary,
        author_id=author_id,
        is_published=is_published,
        cover_image=cover_image,
        category=category,
    )
    if err:
        status = 409 if err == "Slug already in use" else 400
        return jsonify({"error": err}), status
    return jsonify(news.to_dict()), 201


@api_v1_bp.route("/news/<int:news_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def news_update(news_id):
    """
    Update a news article. Requires JWT and editor/admin role. Body: optional title, slug, summary, content, cover_image, category.
    """
    if not current_user_can_write_news():
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    kwargs = {}
    if "title" in data:
        kwargs["title"] = (data.get("title") or "").strip() or None
    if "slug" in data:
        kwargs["slug"] = (data.get("slug") or "").strip() or None
    if "summary" in data:
        kwargs["summary"] = (data.get("summary") or "").strip() or None
    if "content" in data:
        kwargs["content"] = (data.get("content") or "").strip() or None
    if "cover_image" in data:
        kwargs["cover_image"] = (data.get("cover_image") or "").strip() or None
    if "category" in data:
        kwargs["category"] = (data.get("category") or "").strip() or None

    news, err = update_news(news_id, **kwargs)
    if err:
        status = 409 if err == "Slug already in use" else (404 if err == "News not found" else 400)
        return jsonify({"error": err}), status
    return jsonify(news.to_dict()), 200


@api_v1_bp.route("/news/<int:news_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@jwt_required()
def news_delete(news_id):
    """Delete a news article. Requires JWT and editor/admin role."""
    if not current_user_can_write_news():
        return jsonify({"error": "Forbidden"}), 403
    ok, err = delete_news(news_id)
    if err:
        return jsonify({"error": err}), 404
    return jsonify({"message": "Deleted"}), 200


@api_v1_bp.route("/news/<int:news_id>/publish", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def news_publish(news_id):
    """Set article as published. Requires JWT and editor/admin role."""
    if not current_user_can_write_news():
        return jsonify({"error": "Forbidden"}), 403
    news, err = publish_news(news_id)
    if err:
        return jsonify({"error": err}), 404
    return jsonify(news.to_dict()), 200


@api_v1_bp.route("/news/<int:news_id>/unpublish", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def news_unpublish(news_id):
    """Set article as unpublished. Requires JWT and editor/admin role."""
    if not current_user_can_write_news():
        return jsonify({"error": "Forbidden"}), 403
    news, err = unpublish_news(news_id)
    if err:
        return jsonify({"error": err}), 404
    return jsonify(news.to_dict()), 200
