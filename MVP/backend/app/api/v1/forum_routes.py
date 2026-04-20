"""Forum API: categories, threads, posts, likes, reports.

Public/community endpoints are read-only and allow anonymous access where safe.
Authenticated endpoints require JWT; moderation/admin flows are role-restricted.
"""
from datetime import datetime
from typing import Optional

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.utils.error_handler import log_full_error, ERROR_MESSAGES
from app.auth.permissions import (
    current_user_is_admin,
    current_user_is_moderator,
    current_user_is_moderator_or_admin,
    get_current_user,
)
from app.extensions import limiter, db
from app.models import (
    ForumCategory,
    ForumPostLike,
    ForumThread,
    ForumPost,
    ForumReport,
    ForumThreadSubscription,
    Notification,
    ForumTag,
)
from app.services import log_activity
from app.services.activity_log_service import list_activity_logs
from app.services.search_utils import _escape_sql_like_wildcards
from app.services.forum_service import (
    assign_report_to_moderator,
    bulk_update_report_status,
    create_category,
    create_notifications_for_thread_reply,
    create_post,
    create_report,
    create_thread,
    delete_category,
    delete_tag,
    get_category_by_slug_for_user,
    get_post_by_id,
    get_report_by_id,
    get_thread_by_id,
    get_thread_by_slug,
    hide_post,
    hide_thread,
    increment_thread_view,
    like_post,
    list_all_tags,
    list_categories_for_user,
    list_escalation_queue,
    list_handled_reports,
    list_moderator_assigned_reports,
    list_posts_for_thread,
    list_reports,
    list_reports_for_target,
    list_review_queue,
    list_threads_for_category,
    list_tags_for_threads,
    bookmarked_thread_ids_for_user,
    merge_threads,
    move_thread,
    recalc_thread_counters,
    set_thread_archived,
    set_thread_featured,
    set_thread_lock,
    set_thread_pinned,
    set_thread_unarchived,
    soft_delete_post,
    soft_delete_thread,
    split_thread_from_post,
    subscribe_thread,
    batch_tag_thread_counts,
    unsubscribe_thread,
    unhide_post,
    unlike_post,
    update_category,
    update_post,
    update_report_status,
    update_thread,
    user_can_create_thread,
    user_can_edit_post,
    user_can_like_post,
    user_can_manage_categories,
    user_can_moderate_category,
    user_can_post_in_thread,
    user_can_soft_delete_post,
    user_can_view_post,
    user_can_view_thread,
    user_is_moderator,
    _utc_now,
    bookmark_thread,
    unbookmark_thread,
    list_bookmarked_threads,
    set_thread_tags,
    list_tags_for_thread,
)


def _parse_int(value, default, min_val=None, max_val=None):
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


def _current_user_optional():
    """Return current user object or None (for optional JWT endpoints)."""
    try:
        return get_current_user()
    except Exception:
        return None


def _validate_content_length(content, min_len=2, max_len=50000):
    """
    Validate content length. Returns (is_valid, error_message).
    Enforces strict type checking to prevent bypass via non-string inputs.
    """
    # Type check first: must be a string
    if not isinstance(content, str):
        return False, "Content must be a string"

    # Strip and check length
    trimmed = content.strip()
    if len(trimmed) < min_len:
        return False, f"Content must be at least {min_len} characters"
    if len(trimmed) > max_len:
        return False, f"Content must not exceed {max_len} characters"
    return True, None


def _validate_title_length(title, min_len=5, max_len=500):
    """
    Validate title length. Returns (is_valid, error_message).
    Enforces strict type checking to prevent bypass via non-string inputs.
    """
    # Type check first: must be a string
    if not isinstance(title, str):
        return False, "Title must be a string"

    # Strip and check length
    trimmed = title.strip()
    if len(trimmed) < min_len:
        return False, f"Title must be at least {min_len} characters"
    if len(trimmed) > max_len:
        return False, f"Title must not exceed {max_len} characters"
    return True, None


def _validate_category_title_length(title, min_len=5, max_len=200):
    """
    Validate category title length. Returns (is_valid, error_message).
    Enforces strict type checking to prevent bypass via non-string inputs.
    """
    # Type check first: must be a string
    if not isinstance(title, str):
        return False, "Title must be a string"

    # Strip and check length
    trimmed = title.strip()
    if len(trimmed) < min_len:
        return False, f"Title must be at least {min_len} characters"
    if len(trimmed) > max_len:
        return False, f"Title must not exceed {max_len} characters"
    return True, None


# --- Public / community -------------------------------------------------------


@api_v1_bp.route("/forum/categories", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def forum_categories_list():
    """
    List visible forum categories for the current user (or anonymous).
    Response: { items: [ForumCategory], total } with to_dict() payloads.
    """
    user = _current_user_optional()
    cats = list_categories_for_user(user)
    return jsonify({"items": [c.to_dict() for c in cats], "total": len(cats)}), 200


@api_v1_bp.route("/forum/categories/<slug>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def forum_category_detail(slug):
    """
    Get one category by slug if the current user may access it.
    Response: category.to_dict() plus basic thread counts.
    """
    user = _current_user_optional()
    cat = get_category_by_slug_for_user(user, slug)
    if not cat:
        return jsonify({"error": "Category not found"}), 404
    # Basic stats: non-deleted threads count
    total_threads = (
        ForumThread.query.filter_by(category_id=cat.id)
        .filter(ForumThread.status != "deleted")
        .count()
    )
    data = cat.to_dict()
    data["thread_count"] = total_threads
    return jsonify(data), 200


@api_v1_bp.route("/forum/categories/<slug>/threads", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def forum_category_threads(slug):
    """
    List threads in a category (paginated). Anonymous users only see public
    categories; private/staff categories require appropriate role.

    Query: page, limit.
    """
    user = _current_user_optional()
    cat = get_category_by_slug_for_user(user, slug)
    if not cat:
        return jsonify({"error": "Category not found"}), 404

    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)

    # Moderators/admins see all statuses (hidden, archived); others get SQL-level filter.
    is_mod = user is not None and (current_user_is_moderator() or current_user_is_admin())
    page_items, total = list_threads_for_category(
        cat, page=page, per_page=limit, include_hidden=is_mod,
    )

    # Batch-load tags and bookmarks for the page items
    thread_ids = [t.id for t in page_items]
    tags_map = list_tags_for_threads(thread_ids)
    user_id = user.id if user else None
    bookmarked_ids = bookmarked_thread_ids_for_user(user_id, thread_ids)

    items_data = []
    for t in page_items:
        d = t.to_dict()
        d["author_username"] = t.author.username if t.author else None
        d["bookmarked_by_me"] = t.id in bookmarked_ids
        d["tags"] = tags_map.get(t.id, [])
        items_data.append(d)
    return jsonify(
        {
            "items": items_data,
            "total": total,
            "page": page,
            "per_page": limit,
        }
    ), 200


@api_v1_bp.route("/forum/threads/<slug>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def forum_thread_detail(slug):
    """
    Get one thread by slug if visible to current user.
    Response: thread.to_dict() plus category basic info.
    """
    user = _current_user_optional()
    thread = get_thread_by_slug(slug)
    if not thread or not user_can_view_thread(user, thread):
        return jsonify({"error": "Thread not found"}), 404
    user_id = user.id if user else None
    increment_thread_view(thread, user_id=user_id)
    data = thread.to_dict()
    data["author_username"] = thread.author.username if thread.author else None
    if thread.category:
        data["category"] = thread.category.to_dict()
    sub = None
    if user and user.id:
        sub = ForumThreadSubscription.query.filter_by(thread_id=thread.id, user_id=user.id).first()
        data["subscribed_by_me"] = sub is not None
    else:
        data["subscribed_by_me"] = False
    # Attach tags for community comfort layer
    tags = list_tags_for_thread(thread)
    if tags:
        data["tags"] = [{"slug": t.slug, "label": t.label} for t in tags]
    return jsonify(data), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/posts", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required(optional=True)
def forum_thread_posts(thread_id: int):
    """
    List posts in a thread (paginated).
    Anonymous users see only visible posts in visible threads.
    Moderators/admins may include hidden/deleted via query flags.

    Query: page, limit, include_hidden (moderator+), include_deleted (moderator+).
    """
    user = _current_user_optional()
    thread = get_thread_by_id(thread_id)
    if not thread or not user_can_view_thread(user, thread):
        return jsonify({"error": "Thread not found"}), 404

    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    include_hidden = False
    include_deleted = False
    if user and (current_user_is_moderator() or current_user_is_admin()):
        include_hidden = (request.args.get("include_hidden", "").lower() in ("1", "true", "yes"))
        include_deleted = (request.args.get("include_deleted", "").lower() in ("1", "true", "yes"))
    items, total = list_posts_for_thread(
        thread,
        page=page,
        per_page=limit,
        include_hidden=include_hidden,
        include_deleted=include_deleted,
    )
    current_user_id = user.id if user else None
    post_list = []
    for p in items:
        d = p.to_dict()
        d["author_username"] = p.author.username if p.author else None
        d["liked_by_me"] = (
            bool(ForumPostLike.query.filter_by(post_id=p.id, user_id=current_user_id).first())
            if current_user_id else False
        )
        post_list.append(d)
    return jsonify(
        {
            "items": post_list,
            "total": total,
            "page": page,
            "per_page": limit,
        }
    ), 200


@api_v1_bp.route("/forum/search", methods=["GET"])
@limiter.limit("30 per minute")
@jwt_required(optional=True)
def forum_search():
    """
    Search over thread titles and optionally post content with filters.

    Query parameters:
      - q: search query string (0-500 chars). Will be normalized and escaped.
      - page: page number (default 1, min 1, max 10000)
      - limit: results per page (default 20, min 1, max 100)
      - category: filter by category slug
      - status: filter by status (open, locked, archived, hidden)
      - tag: filter by tag slug
      - include_content: if 1/true/yes and q is 3+ chars, search post content too

    Validation:
      - Empty queries with no other filters return empty array (no unbounded scans)
      - Very short queries (1-2 chars) are rejected
      - Queries are truncated to 500 chars max
      - SQL LIKE wildcards are escaped for safety
      - Filter values are validated against known enums

    Ordering: pinned first, then by last_post_at desc, then by id asc

    Response: {items: [], total: int, page: int, per_page: int}
    """
    from app.models import ForumThread, ForumPost, ForumCategory, ForumThreadTag  # imported lazily to avoid cycles

    user = _current_user_optional()

    # Extract and normalize query
    q_raw = (request.args.get("q") or "").strip()
    page = _parse_int(request.args.get("page"), 1, min_val=1, max_val=10000)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    category_slug = (request.args.get("category") or "").strip() or None
    status_filter = (request.args.get("status") or "").strip() or None
    tag_slug = (request.args.get("tag") or "").strip().lower() or None
    include_content = (request.args.get("include_content", "").strip().lower() in ("1", "true", "yes"))

    # Input validation: empty query with no other filters
    if not q_raw and not category_slug and not status_filter and not tag_slug:
        return jsonify(
            {
                "items": [],
                "total": 0,
                "page": page,
                "per_page": limit,
            }
        ), 200

    # Input validation: very short queries (1-2 chars) are too broad
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

    # Input validation: truncate overly long search terms
    if len(q_raw) > 500:
        q_raw = q_raw[:500]

    # Escape SQL LIKE wildcards for safety, then build pattern
    q_escaped = _escape_sql_like_wildcards(q_raw)
    like_pattern = f"%{q_escaped}%" if q_escaped else None

    is_mod = user_is_moderator(user) if user else False

    # Base query with SQL-level visibility filtering
    q = ForumThread.query
    if not is_mod:
        # Regular users: exclude deleted and hidden threads at SQL level
        q = q.filter(ForumThread.status.notin_(("deleted", "hidden")))
    else:
        # Moderators see everything except deleted (keep consistency with list behavior)
        q = q.filter(ForumThread.status != "deleted")

    if like_pattern:
        q = q.filter(ForumThread.title.ilike(like_pattern, escape="\\"))

    # Join category for access filtering and optional category filter
    q = q.join(ForumCategory, ForumCategory.id == ForumThread.category_id)
    if not is_mod:
        # Only active, non-private categories for regular users (SQL-level)
        q = q.filter(ForumCategory.is_active.is_(True))
        q = q.filter(ForumCategory.is_private.is_(False))
    if category_slug:
        q = q.filter(ForumCategory.slug == category_slug)

    # Optional status filter: validate enum
    if status_filter:
        if status_filter not in ("open", "locked", "archived", "hidden"):
            return jsonify(
                {
                    "error": f"Invalid status filter: {status_filter}. Must be one of: open, locked, archived, hidden",
                    "items": [],
                    "total": 0,
                    "page": page,
                    "per_page": limit,
                }
            ), 400
        q = q.filter(ForumThread.status == status_filter)

    # Optional tag filter
    if tag_slug:
        from app.models import ForumTag as ForumTagModel  # local import
        q = q.join(ForumThreadTag, ForumThreadTag.thread_id == ForumThread.id).join(
            ForumTagModel, ForumTagModel.id == ForumThreadTag.tag_id
        ).filter(ForumTagModel.slug == tag_slug)

    # Optional post content search (requires 3+ chars for performance)
    if include_content and like_pattern and len(q_raw) >= 3:
        from sqlalchemy import select
        sub = select(ForumPost.thread_id).where(
            ForumPost.content.ilike(like_pattern, escape="\\")
        )
        q = q.filter(
            db.or_(
                ForumThread.title.ilike(like_pattern, escape="\\"),
                ForumThread.id.in_(sub),
            )
        )

    # SQL-level pagination (visibility already pushed into SQL)
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


# --- Authenticated community actions (threads, posts, likes, reports) ---------


def _require_user():
    """Require a logged-in, non-banned user."""
    user = get_current_user()
    if not user:
        return None, (jsonify({"error": "Authorization required"}), 401)
    if getattr(user, "is_banned", False):
        return None, (jsonify({"error": "Account is restricted."}), 403)
    return user, None


@api_v1_bp.route("/forum/categories/<slug>/threads", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_create(slug):
    """
    Create a new thread in a category.
    Body: title, content.
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    cat = ForumCategory.query.filter_by(slug=slug).first()
    if not cat:
        return jsonify({"error": "Category not found"}), 404
    if not user_can_create_thread(user, cat):
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    # Type check before stripping
    title_raw = data.get("title")
    content_raw = data.get("content")
    if title_raw is not None and not isinstance(title_raw, str):
        return jsonify({"error": "Title must be a string"}), 400
    if content_raw is not None and not isinstance(content_raw, str):
        return jsonify({"error": "Content must be a string"}), 400

    title = (title_raw or "").strip()
    content = (content_raw or "").strip()
    if not title or not content:
        return jsonify({"error": "title and content are required"}), 400

    # Validate title length (5-500 characters)
    is_valid, error_msg = _validate_title_length(title, min_len=5, max_len=500)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    # Validate content length (10-50000 characters)
    is_valid, error_msg = _validate_content_length(content, min_len=10, max_len=50000)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    thread, post, err = create_thread(
        category=cat,
        author_id=user.id,
        title=title,
        content=content,
    )
    if err:
        return jsonify({"error": err}), 400
    log_activity(
        actor=user,
        category="forum",
        action="thread_created",
        status="success",
        message=f"Thread created in category {cat.slug}: {thread.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(thread.id),
    )
    data = thread.to_dict()
    data["author_username"] = thread.author.username if thread.author else None
    if thread.category:
        data["category"] = thread.category.to_dict()
    return jsonify(data), 201


@api_v1_bp.route("/forum/threads/<int:thread_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_update(thread_id: int):
    """
    Update thread title. Author or category moderators/admins only.
    Moderators can only update threads in their assigned categories.
    Body: title (optional).
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    thread = get_thread_by_id(thread_id)
    if not thread:
        return jsonify({"error": "Thread not found"}), 404
    if not thread.category:
        return jsonify({"error": "Thread has no category"}), 400
    # Author can update their own thread
    if thread.author_id == user.id:
        pass
    # Moderators/admins must be assigned to the category
    elif not user_can_moderate_category(user, thread.category):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    title = data.get("title")
    if title is not None:
        # Type check before attempting to strip
        if not isinstance(title, str):
            return jsonify({"error": "Title must be a string"}), 400
        title = title.strip()
        # Validate title length (5-500 characters)
        is_valid, error_msg = _validate_title_length(title, min_len=5, max_len=500)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
    thread = update_thread(thread, title=title)
    log_activity(
        actor=user,
        category="forum",
        action="thread_updated",
        status="success",
        message=f"Thread updated: {thread.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(thread.id),
    )
    data = thread.to_dict()
    data["author_username"] = thread.author.username if thread.author else None
    if thread.category:
        data["category"] = thread.category.to_dict()
    return jsonify(data), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_delete(thread_id: int):
    """
    Soft-delete a thread. Author or category moderators/admins only.
    Moderators can only delete threads in their assigned categories.
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    thread = get_thread_by_id(thread_id)
    if not thread:
        return jsonify({"error": "Thread not found"}), 404
    if not thread.category:
        return jsonify({"error": "Thread has no category"}), 400
    # Author can delete their own thread
    if thread.author_id == user.id:
        pass
    # Moderators/admins must be assigned to the category
    elif not user_can_moderate_category(user, thread.category):
        return jsonify({"error": "Forbidden"}), 403
    thread = soft_delete_thread(thread)
    log_activity(
        actor=user,
        category="forum",
        action="thread_deleted",
        status="success",
        message=f"Thread soft-deleted: {thread.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(thread.id),
    )
    return jsonify({"message": "Deleted"}), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/posts", methods=["POST"])
@limiter.limit("10 per minute")
@jwt_required()
def forum_post_create(thread_id: int):
    """
    Create a post in a thread.
    Body: content, optional parent_post_id.
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    thread = get_thread_by_id(thread_id)
    if not thread:
        return jsonify({"error": "Thread not found"}), 404
    if not user_can_post_in_thread(user, thread):
        return jsonify({"error": "Forbidden. Thread is locked or not accessible."}), 403

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    # Type check before stripping
    content_raw = data.get("content")
    if content_raw is not None and not isinstance(content_raw, str):
        return jsonify({"error": "Content must be a string"}), 400

    content = (content_raw or "").strip()
    parent_post_id = data.get("parent_post_id")
    parent_id_int: Optional[int] = None
    if parent_post_id is not None:
        try:
            parent_id_int = int(parent_post_id)
        except (TypeError, ValueError):
            return jsonify({"error": "parent_post_id must be an integer"}), 400

    # Validate content length (10-50000 characters)
    is_valid, error_msg = _validate_content_length(content, min_len=10, max_len=50000)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    post, err = create_post(
        thread=thread,
        author_id=user.id,
        content=content,
        parent_post_id=parent_id_int,
    )
    if err:
        return jsonify({"error": err}), 400
    create_notifications_for_thread_reply(thread, post, user.id)
    log_activity(
        actor=user,
        category="forum",
        action="post_created",
        status="success",
        message=f"Post created in thread {thread.id}: {post.id}",
        route=request.path,
        method=request.method,
        target_type="forum_post",
        target_id=str(post.id),
    )
    return jsonify(post.to_dict()), 201


@api_v1_bp.route("/forum/threads/<int:thread_id>/bookmark", methods=["POST"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_thread_bookmark(thread_id: int):
    """
    Bookmark a thread for the current user.
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    thread = get_thread_by_id(thread_id)
    if not thread or not user_can_view_thread(user, thread):
        return jsonify({"error": "Thread not found"}), 404
    bookmark_thread(user, thread)
    return jsonify({"message": "Bookmarked"}), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/bookmark", methods=["DELETE"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_thread_unbookmark(thread_id: int):
    """
    Remove bookmark for a thread for the current user.
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    thread = get_thread_by_id(thread_id)
    if not thread:
        return jsonify({"error": "Thread not found"}), 404
    unbookmark_thread(user, thread)
    return jsonify({"message": "Unbookmarked"}), 200


@api_v1_bp.route("/forum/bookmarks", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_bookmarks_list():
    """
    List bookmarked threads for the current user.

    Query: page, limit.
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    threads, total = list_bookmarked_threads(user, page=page, per_page=limit)
    items = []
    for t in threads:
        d = t.to_dict()
        d["author_username"] = t.author.username if t.author else None
        if t.category:
            d["category"] = t.category.to_dict()
        tags = list_tags_for_thread(t)
        if tags:
            d["tags"] = [{"slug": tag.slug, "label": tag.label} for tag in tags]
        items.append(d)
    return jsonify({"items": items, "total": total, "page": page, "per_page": limit}), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/tags", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_set_tags(thread_id: int):
    """
    Set tags for a thread. Moderator/admin or thread author only.
    Body: { "tags": ["tag1", "tag2", ...] }
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    thread = get_thread_by_id(thread_id)
    if not thread:
        return jsonify({"error": "Thread not found"}), 404
    if not (thread.author_id == user.id or current_user_is_moderator() or current_user_is_admin()):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    raw_tags = data.get("tags") or []
    if not isinstance(raw_tags, list):
        return jsonify({"error": "tags must be a list of strings"}), 400
    tags = [str(t) for t in raw_tags if isinstance(t, (str, bytes))]
    tag_rows = set_thread_tags(thread, tags=tags)
    out = [{"slug": t.slug, "label": t.label} for t in tag_rows]
    return jsonify({"tags": out}), 200


@api_v1_bp.route("/forum/posts/<int:post_id>", methods=["PUT"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_post_update(post_id: int):
    """
    Update a post's content. Author or category moderators/admins only.
    Moderators can only edit posts in their assigned categories.
    Body: content.
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    post = get_post_by_id(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    if not user_can_edit_post(user, post):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    content = data.get("content")
    if content is None:
        return jsonify({"error": "content is required"}), 400

    # Type check before validation
    if not isinstance(content, str):
        return jsonify({"error": "Content must be a string"}), 400

    # Validate content length (10-50000 characters)
    is_valid, error_msg = _validate_content_length(content, min_len=10, max_len=50000)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    post = update_post(post, content=content, editor_id=user.id)
    log_activity(
        actor=user,
        category="forum",
        action="post_updated",
        status="success",
        message=f"Post updated: {post.id}",
        route=request.path,
        method=request.method,
        target_type="forum_post",
        target_id=str(post.id),
    )
    return jsonify(post.to_dict()), 200


@api_v1_bp.route("/forum/posts/<int:post_id>", methods=["DELETE"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_post_delete(post_id: int):
    """
    Soft-delete a post. Author or moderators/admins only.
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    post = get_post_by_id(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    if not user_can_soft_delete_post(user, post):
        return jsonify({"error": "Forbidden"}), 403
    post = soft_delete_post(post)
    log_activity(
        actor=user,
        category="forum",
        action="post_deleted",
        status="success",
        message=f"Post soft-deleted: {post.id}",
        route=request.path,
        method=request.method,
        target_type="forum_post",
        target_id=str(post.id),
    )
    return jsonify({"message": "Deleted"}), 200


@api_v1_bp.route("/forum/posts/<int:post_id>/like", methods=["POST"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_post_like(post_id: int):
    """
    Like a post. Duplicate likes are ignored (idempotent - returns 200 for already-liked posts).
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    post = get_post_by_id(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    if not user_can_like_post(user, post):
        return jsonify({"error": "Forbidden"}), 403
    like, err = like_post(user, post)
    if err:
        # Duplicate like - return 200 for idempotency (user already liked this post)
        return jsonify({"message": "Already liked", "like_count": post.like_count, "liked_by_me": True}), 200
    return jsonify({"message": "Liked", "like_count": post.like_count, "liked_by_me": True}), 200


@api_v1_bp.route("/forum/posts/<int:post_id>/like", methods=["DELETE"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_post_unlike(post_id: int):
    """
    Remove like from a post (idempotent).
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    post = get_post_by_id(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    unlike_post(user, post)
    return jsonify({"message": "Unliked", "like_count": post.like_count, "liked_by_me": False}), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/subscribe", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_subscribe(thread_id: int):
    """
    Subscribe to a thread (for future notifications).
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    thread = get_thread_by_id(thread_id)
    if not thread or not user_can_view_thread(user, thread):
        return jsonify({"error": "Thread not found"}), 404
    sub = subscribe_thread(user, thread)
    return jsonify({"message": "Subscribed", "subscription_id": sub.id}), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/subscribe", methods=["DELETE"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_unsubscribe(thread_id: int):
    """
    Unsubscribe from a thread.
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    thread = get_thread_by_id(thread_id)
    if not thread:
        return jsonify({"error": "Thread not found"}), 404
    unsubscribe_thread(user, thread)
    return jsonify({"message": "Unsubscribed"}), 200


@api_v1_bp.route("/forum/reports", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
def forum_report_create():
    """
    Create a report on a thread or post.
    Body: target_type ('thread' or 'post'), target_id, reason.
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    target_type = (data.get("target_type") or "").strip()
    try:
        target_id = int(data.get("target_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "target_id must be an integer"}), 400
    reason = data.get("reason")
    if target_type == "thread":
        target = get_thread_by_id(target_id)
        if not target or not user_can_view_thread(user, target):
            return jsonify({"error": "Thread not found"}), 404
    elif target_type == "post":
        target = get_post_by_id(target_id)
        if not target or not user_can_view_post(user, target):
            return jsonify({"error": "Post not found"}), 404
    else:
        return jsonify({"error": "Invalid target_type"}), 400

    report, err = create_report(
        target_type=target_type,
        target_id=target_id,
        reported_by=user.id,
        reason=reason,
    )
    if err:
        return jsonify({"error": err}), 400
    log_activity(
        actor=user,
        category="forum",
        action="report_created",
        status="success",
        message=f"Report created: {report.id}",
        route=request.path,
        method=request.method,
        target_type="forum_report",
        target_id=str(report.id),
    )
    return jsonify(report.to_dict()), 201


# --- Moderator/admin actions --------------------------------------------------


def _require_moderator_for_category(cat: ForumCategory):
    user = get_current_user()
    if not user:
        return None, (jsonify({"error": "Authorization required"}), 401)
    if not user_can_moderate_category(user, cat):
        return None, (jsonify({"error": "Forbidden"}), 403)
    return user, None


def _require_admin():
    user = get_current_user()
    if not user or not current_user_is_admin():
        return None, (jsonify({"error": "Forbidden"}), 403)
    return user, None


def _require_moderator_or_admin():
    user = get_current_user()
    if not user or not current_user_is_moderator_or_admin():
        return None, (jsonify({"error": "Forbidden"}), 403)
    return user, None


@api_v1_bp.route("/forum/threads/<int:thread_id>/lock", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_lock(thread_id: int):
    """Lock a thread (moderator/admin only)."""
    thread = get_thread_by_id(thread_id)
    if not thread or not thread.category:
        return jsonify({"error": "Thread not found"}), 404
    user, err_resp = _require_moderator_for_category(thread.category)
    if err_resp:
        return err_resp
    old_locked = thread.is_locked
    old_status = thread.status
    thread = set_thread_lock(thread, True)
    log_activity(
        actor=user,
        category="forum",
        action="thread_locked",
        status="success",
        message=f"Thread locked: {thread.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(thread.id),
        metadata={"before": {"is_locked": old_locked, "status": old_status}, "after": {"is_locked": True, "status": thread.status}},
    )
    return jsonify(thread.to_dict()), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/unlock", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_unlock(thread_id: int):
    """Unlock a thread (moderator/admin only)."""
    thread = get_thread_by_id(thread_id)
    if not thread or not thread.category:
        return jsonify({"error": "Thread not found"}), 404
    user, err_resp = _require_moderator_for_category(thread.category)
    if err_resp:
        return err_resp
    old_locked = thread.is_locked
    old_status = thread.status
    thread = set_thread_lock(thread, False)
    log_activity(
        actor=user,
        category="forum",
        action="thread_unlocked",
        status="success",
        message=f"Thread unlocked: {thread.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(thread.id),
        metadata={"before": {"is_locked": old_locked, "status": old_status}, "after": {"is_locked": False, "status": thread.status}},
    )
    return jsonify(thread.to_dict()), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/pin", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_pin(thread_id: int):
    """Pin a thread in its category (moderator/admin only)."""
    thread = get_thread_by_id(thread_id)
    if not thread or not thread.category:
        return jsonify({"error": "Thread not found"}), 404
    user, err_resp = _require_moderator_for_category(thread.category)
    if err_resp:
        return err_resp
    old_pinned = thread.is_pinned
    thread = set_thread_pinned(thread, True)
    log_activity(
        actor=user,
        category="forum",
        action="thread_pinned",
        status="success",
        message=f"Thread pinned: {thread.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(thread.id),
        metadata={"before": {"is_pinned": old_pinned}, "after": {"is_pinned": True}},
    )
    return jsonify(thread.to_dict()), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/unpin", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_unpin(thread_id: int):
    """Unpin a thread in its category (moderator/admin only)."""
    thread = get_thread_by_id(thread_id)
    if not thread or not thread.category:
        return jsonify({"error": "Thread not found"}), 404
    user, err_resp = _require_moderator_for_category(thread.category)
    if err_resp:
        return err_resp
    old_pinned = thread.is_pinned
    thread = set_thread_pinned(thread, False)
    log_activity(
        actor=user,
        category="forum",
        action="thread_unpinned",
        status="success",
        message=f"Thread unpinned: {thread.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(thread.id),
        metadata={"before": {"is_pinned": old_pinned}, "after": {"is_pinned": False}},
    )
    return jsonify(thread.to_dict()), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/feature", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_feature(thread_id: int):
    """Mark a thread as featured (moderator/admin only)."""
    thread = get_thread_by_id(thread_id)
    if not thread or not thread.category:
        return jsonify({"error": "Thread not found"}), 404
    user, err_resp = _require_moderator_for_category(thread.category)
    if err_resp:
        return err_resp
    old_featured = thread.is_featured
    thread = set_thread_featured(thread, True)
    log_activity(
        actor=user,
        category="forum",
        action="thread_featured",
        status="success",
        message=f"Thread featured: {thread.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(thread.id),
        metadata={"before": {"is_featured": old_featured}, "after": {"is_featured": True}},
    )
    return jsonify(thread.to_dict()), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/unfeature", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_unfeature(thread_id: int):
    """Remove featured flag from a thread (moderator/admin only)."""
    thread = get_thread_by_id(thread_id)
    if not thread or not thread.category:
        return jsonify({"error": "Thread not found"}), 404
    user, err_resp = _require_moderator_for_category(thread.category)
    if err_resp:
        return err_resp
    old_featured = thread.is_featured
    thread = set_thread_featured(thread, False)
    log_activity(
        actor=user,
        category="forum",
        action="thread_unfeatured",
        status="success",
        message=f"Thread unfeatured: {thread.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(thread.id),
        metadata={"before": {"is_featured": old_featured}, "after": {"is_featured": False}},
    )
    return jsonify(thread.to_dict()), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/move", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_move(thread_id: int):
    """Move a thread to another category (moderator/admin only). Body: category_id (int)."""
    thread = get_thread_by_id(thread_id)
    if not thread or not thread.category:
        return jsonify({"error": "Thread not found"}), 404
    user, err_resp = _require_moderator_for_category(thread.category)
    if err_resp:
        return err_resp
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    try:
        category_id = int(data.get("category_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "category_id must be an integer"}), 400
    new_cat = ForumCategory.query.get(category_id)
    if not new_cat:
        return jsonify({"error": "Category not found"}), 404
    if not user_can_moderate_category(user, new_cat):
        return jsonify({"error": "Forbidden"}), 403
    thread, err = move_thread(thread, new_cat)
    if err:
        return jsonify({"error": err}), 400
    log_activity(
        actor=user,
        category="forum",
        action="thread_moved",
        status="success",
        message=f"Thread {thread.id} moved to category {new_cat.slug}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(thread.id),
    )
    data = thread.to_dict()
    data["author_username"] = thread.author.username if thread.author else None
    if thread.category:
        data["category"] = thread.category.to_dict()
    return jsonify(data), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/archive", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_archive(thread_id: int):
    """Archive a thread (moderator/admin only)."""
    thread = get_thread_by_id(thread_id)
    if not thread or not thread.category:
        return jsonify({"error": "Thread not found"}), 404
    user, err_resp = _require_moderator_for_category(thread.category)
    if err_resp:
        return err_resp
    old_status = thread.status
    thread = set_thread_archived(thread)
    log_activity(
        actor=user,
        category="forum",
        action="thread_archived",
        status="success",
        message=f"Thread archived: {thread.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(thread.id),
        metadata={"before": {"status": old_status}, "after": {"status": "archived"}},
    )
    return jsonify(thread.to_dict()), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/unarchive", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_unarchive(thread_id: int):
    """Unarchive a thread (moderator/admin only)."""
    thread = get_thread_by_id(thread_id)
    if not thread or not thread.category:
        return jsonify({"error": "Thread not found"}), 404
    user, err_resp = _require_moderator_for_category(thread.category)
    if err_resp:
        return err_resp
    old_status = thread.status
    thread = set_thread_unarchived(thread)
    log_activity(
        actor=user,
        category="forum",
        action="thread_unarchived",
        status="success",
        message=f"Thread unarchived: {thread.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(thread.id),
        metadata={"before": {"status": old_status}, "after": {"status": thread.status}},
    )
    return jsonify(thread.to_dict()), 200


@api_v1_bp.route("/forum/threads/<int:source_thread_id>/merge", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_merge(source_thread_id: int):
    """
    Merge a source thread into a target thread (moderator/admin only).

    Body: { "target_thread_id": <int> }
    """
    source = get_thread_by_id(source_thread_id)
    if not source or not source.category:
        return jsonify({"error": "Source thread not found"}), 404
    user, err_resp = _require_moderator_for_category(source.category)
    if err_resp:
        return err_resp

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    try:
        target_thread_id = int(data.get("target_thread_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "target_thread_id must be an integer"}), 400

    target = get_thread_by_id(target_thread_id)
    if not target or not target.category:
        return jsonify({"error": "Target thread not found"}), 404

    # Ensure the user may moderate the target category as well.
    _, err_resp_target = _require_moderator_for_category(target.category)
    if err_resp_target:
        return err_resp_target

    err = merge_threads(source, target)
    if err:
        return jsonify({"error": err}), 400

    log_activity(
        actor=user,
        category="forum",
        action="thread_merged",
        status="success",
        message=f"Thread {source.id} merged into {target.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(target.id),
    )
    data = target.to_dict()
    data["author_username"] = target.author.username if target.author else None
    if target.category:
        data["category"] = target.category.to_dict()
    return jsonify(data), 200


@api_v1_bp.route("/forum/threads/<int:thread_id>/split", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_thread_split(thread_id: int):
    """
    Split a thread starting from a top-level post into a new thread (moderator/admin only).

    Safe, constrained behavior:
    - root_post_id must refer to a top-level post in the source thread (parent_post_id is null).
    - The root post and its direct replies (single-level replies) move into the new thread.
    - New thread title is required; category defaults to the source thread's category
      unless a target category_id is provided.
    """
    source_thread = get_thread_by_id(thread_id)
    if not source_thread or not source_thread.category:
        return jsonify({"error": "Thread not found"}), 404

    user, err_resp = _require_moderator_for_category(source_thread.category)
    if err_resp:
        return err_resp

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    try:
        root_post_id = int(data.get("root_post_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "root_post_id must be an integer"}), 400

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    category_id = data.get("category_id")
    target_category: Optional[ForumCategory] = None
    if category_id is not None:
        try:
            category_id_int = int(category_id)
        except (TypeError, ValueError):
            return jsonify({"error": "category_id must be an integer"}), 400
        target_category = ForumCategory.query.get(category_id_int)
        if not target_category:
            return jsonify({"error": "Category not found"}), 404
        if not user_can_moderate_category(user, target_category):
            return jsonify({"error": "Forbidden"}), 403

    root_post = get_post_by_id(root_post_id)
    if not root_post:
        return jsonify({"error": "Root post not found"}), 404

    new_thread, err = split_thread_from_post(
        source_thread=source_thread,
        root_post=root_post,
        new_title=title,
        new_category=target_category,
    )
    if err:
        return jsonify({"error": err}), 400

    log_activity(
        actor=user,
        category="forum",
        action="thread_split",
        status="success",
        message=f"Thread {source_thread.id} split into new thread {new_thread.id} from post {root_post.id}",
        route=request.path,
        method=request.method,
        target_type="forum_thread",
        target_id=str(new_thread.id),
    )
    resp_data = new_thread.to_dict()
    resp_data["author_username"] = new_thread.author.username if new_thread.author else None
    if new_thread.category:
        resp_data["category"] = new_thread.category.to_dict()
    return jsonify(resp_data), 201


@api_v1_bp.route("/forum/posts/<int:post_id>/hide", methods=["POST"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_post_hide(post_id: int):
    """Hide a post (moderator/admin only)."""
    post = get_post_by_id(post_id)
    if not post or not post.thread or not post.thread.category:
        return jsonify({"error": "Post not found"}), 404
    user, err_resp = _require_moderator_for_category(post.thread.category)
    if err_resp:
        return err_resp
    old_post_status = post.status
    post = hide_post(post)
    log_activity(
        actor=user,
        category="forum",
        action="post_hidden",
        status="success",
        message=f"Post hidden: {post.id}",
        route=request.path,
        method=request.method,
        target_type="forum_post",
        target_id=str(post.id),
        metadata={"before": {"status": old_post_status}, "after": {"status": "hidden"}},
    )
    return jsonify(post.to_dict()), 200


@api_v1_bp.route("/forum/posts/<int:post_id>/unhide", methods=["POST"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_post_unhide(post_id: int):
    """Unhide a post (moderator/admin only)."""
    post = get_post_by_id(post_id)
    if not post or not post.thread or not post.thread.category:
        return jsonify({"error": "Post not found"}), 404
    user, err_resp = _require_moderator_for_category(post.thread.category)
    if err_resp:
        return err_resp
    old_post_status = post.status
    post = unhide_post(post)
    log_activity(
        actor=user,
        category="forum",
        action="post_unhidden",
        status="success",
        message=f"Post unhidden: {post.id}",
        route=request.path,
        method=request.method,
        target_type="forum_post",
        target_id=str(post.id),
        metadata={"before": {"status": old_post_status}, "after": {"status": post.status}},
    )
    return jsonify(post.to_dict()), 200


@api_v1_bp.route("/forum/reports", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_reports_list():
    """
    List forum reports (moderator/admin only).
    Query: status, target_type, page, limit.
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp
    status = (request.args.get("status") or "").strip() or None
    target_type = (request.args.get("target_type") or "").strip() or None
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    items, total = list_reports(status=status, target_type=target_type, page=page, limit=limit)
    return jsonify({"items": [r.to_dict() for r in items], "total": total, "page": page, "limit": limit}), 200


@api_v1_bp.route("/forum/reports/<int:report_id>", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_report_get(report_id: int):
    """Get single report (moderator/admin only)."""
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp
    report = get_report_by_id(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report.to_dict()), 200


@api_v1_bp.route("/forum/reports/<int:report_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_report_update(report_id: int):
    """
    Update report status and metadata (moderator/admin only).
    Body: {
        "status": "open|reviewed|escalated|resolved|dismissed",
        "priority": "low|normal|high|critical" (optional),
        "escalation_reason": "str" (optional, for escalations),
        "resolution_note": "str" (optional)
    }
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp
    report = get_report_by_id(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    status = (data.get("status") or "").strip()
    old_status = report.status
    old_priority = report.priority

    priority = data.get("priority")
    if priority and priority not in ("low", "normal", "high", "critical"):
        return jsonify({"error": "Invalid priority"}), 400

    escalation_reason = data.get("escalation_reason")
    if escalation_reason is not None:
        escalation_reason = str(escalation_reason).strip() or None

    resolution_note = data.get("resolution_note")
    if resolution_note is not None:
        resolution_note = str(resolution_note).strip() or None

    try:
        report = update_report_status(
            report,
            status=status,
            handled_by=user.id,
            resolution_note=resolution_note,
            priority=priority,
            escalation_reason=escalation_reason,
        )
    except ValueError as e:
        log_full_error(e, "Report status update validation failed", user_id=user.id, route=request.path, method=request.method)
        return jsonify({"error": ERROR_MESSAGES["validation_error"]}), 400
    log_activity(
        actor=user,
        category="forum",
        action="report_status_updated",
        status="success",
        message=f"Report {report.id} status -> {report.status}",
        route=request.path,
        method=request.method,
        target_type="forum_report",
        target_id=str(report.id),
        metadata={
            "before": {"status": old_status, "priority": old_priority},
            "after": {"status": report.status, "priority": report.priority},
        },
    )
    return jsonify(report.to_dict()), 200


@api_v1_bp.route("/forum/reports/bulk-status", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
def forum_reports_bulk_status():
    """
    Bulk update report status with per-item feedback (moderator/admin only).
    Body: {
        "report_ids": [int, ...],
        "status": "reviewed|escalated|resolved|dismissed",
        "priority": "low|normal|high|critical" (optional),
        "resolution_note": "str" (optional)
    }
    Response: { "updated_ids": [...], "failed_items": [{"id": int, "reason": str}, ...] }
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    ids = data.get("report_ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "report_ids must be a non-empty list"}), 400
    try:
        id_list = [int(x) for x in ids]
    except (TypeError, ValueError):
        return jsonify({"error": "report_ids must contain integers"}), 400
    status = (data.get("status") or "").strip()
    if status not in ("reviewed", "escalated", "resolved", "dismissed"):
        return jsonify({"error": "Invalid status for bulk update"}), 400

    priority = data.get("priority")
    if priority and priority not in ("low", "normal", "high", "critical"):
        return jsonify({"error": "Invalid priority"}), 400

    resolution_note = data.get("resolution_note")
    if resolution_note is not None:
        resolution_note = str(resolution_note).strip() or None

    # Use service function for bulk update with per-item feedback
    success_ids, failed_items = bulk_update_report_status(
        id_list,
        status=status,
        handled_by=user.id,
        resolution_note=resolution_note,
        priority=priority,
    )

    if success_ids:
        log_activity(
            actor=user,
            category="forum",
            action="reports_bulk_status_updated",
            status="success",
            message=f"Reports {success_ids} status -> {status}",
            route=request.path,
            method=request.method,
            target_type="forum_report",
            target_id=",".join(str(x) for x in success_ids),
            metadata={
                "before": {"status": "mixed"},
                "after": {"status": status, "count": len(success_ids)},
            },
        )
    return jsonify({"updated_ids": success_ids, "failed_items": failed_items}), 200


@api_v1_bp.route("/forum/moderation/escalation-queue", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_escalation_queue():
    """
    Get escalated reports in priority order (moderator/admin only).
    Query params: page (default 1), limit (default 50, max 100), priority (filter: critical|high|normal|low)
    Response: { items: [ForumReport], total }
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp

    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 50, min_val=1, max_val=100)
    priority_filter = request.args.get("priority", "").strip() or None

    items, total = list_escalation_queue(
        page=page,
        per_page=limit,
        priority_filter=priority_filter,
    )

    return jsonify({
        "items": [r.to_dict() for r in items],
        "total": total,
        "page": page,
        "limit": limit,
    }), 200


@api_v1_bp.route("/forum/moderation/review-queue", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_review_queue():
    """
    Get open and reviewed reports pending action (moderator/admin only).
    Query params: page (default 1), limit (default 50, max 100)
    Response: { items: [ForumReport], total }
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp

    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 50, min_val=1, max_val=100)

    items, total = list_review_queue(page=page, per_page=limit)

    return jsonify({
        "items": [r.to_dict() for r in items],
        "total": total,
        "page": page,
        "limit": limit,
    }), 200


@api_v1_bp.route("/forum/moderation/moderator-assigned", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_moderator_assigned():
    """
    Get reports assigned to the current moderator (moderator/admin only).
    Query params: page (default 1), limit (default 50, max 100)
    Response: { items: [ForumReport], total }
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp

    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 50, min_val=1, max_val=100)

    items, total = list_moderator_assigned_reports(user.id, page=page, per_page=limit)

    return jsonify({
        "items": [r.to_dict() for r in items],
        "total": total,
        "page": page,
        "limit": limit,
    }), 200


@api_v1_bp.route("/forum/moderation/handled-reports", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_handled_reports():
    """
    Get resolved or dismissed reports (moderator/admin only).
    Query params: page (default 1), limit (default 50, max 100), status (filter: resolved|dismissed)
    Response: { items: [ForumReport], total }
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp

    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 50, min_val=1, max_val=100)
    status_filter = request.args.get("status", "").strip() or None

    items, total = list_handled_reports(page=page, per_page=limit, status_filter=status_filter)

    return jsonify({
        "items": [r.to_dict() for r in items],
        "total": total,
        "page": page,
        "limit": limit,
    }), 200


@api_v1_bp.route("/forum/moderation/reports/<int:report_id>/assign", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_report_assign(report_id: int):
    """
    Assign a report to a moderator (moderator/admin only).
    Body: { "moderator_id": int } or { "assign_to_me": true }
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp

    report = get_report_by_id(report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404

    data = request.get_json(silent=True) or {}
    assign_to_me = data.get("assign_to_me", False)

    if assign_to_me:
        moderator_id = user.id
    else:
        moderator_id = data.get("moderator_id")
        if not moderator_id:
            return jsonify({"error": "moderator_id or assign_to_me required"}), 400
        try:
            moderator_id = int(moderator_id)
        except (TypeError, ValueError):
            return jsonify({"error": "moderator_id must be integer"}), 400

    before_assigned = report.assigned_to
    report = assign_report_to_moderator(report, moderator_id)

    log_activity(
        actor=user,
        category="forum",
        action="report_assigned",
        status="success",
        message=f"Report {report_id} assigned to moderator {moderator_id}",
        route=request.path,
        method=request.method,
        target_type="forum_report",
        target_id=str(report_id),
        metadata={"before": {"assigned_to": before_assigned}, "after": {"assigned_to": moderator_id}},
    )

    return jsonify({"id": report.id, "assigned_to": report.assigned_to}), 200


# --- Category admin -----------------------------------------------------------


@api_v1_bp.route("/forum/admin/categories", methods=["POST"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_admin_category_create():
    """
    Create a forum category (admin only).
    Body: slug, title, optional description, parent_id, sort_order, is_active, is_private, required_role.
    """
    user, err_resp = _require_admin()
    if err_resp:
        return err_resp
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    # Type check title before stripping
    title_raw = data.get("title")
    if title_raw is not None and not isinstance(title_raw, str):
        return jsonify({"error": "Title must be a string"}), 400

    slug = (data.get("slug") or "").strip()
    title = (title_raw or "").strip()
    description = data.get("description")
    parent_id = data.get("parent_id")
    sort_order = data.get("sort_order", 0)
    is_active = bool(data.get("is_active", True))
    is_private = bool(data.get("is_private", False))
    required_role = data.get("required_role")
    parent_id_int: Optional[int] = None
    if parent_id is not None:
        try:
            parent_id_int = int(parent_id)
        except (TypeError, ValueError):
            return jsonify({"error": "parent_id must be an integer"}), 400
    try:
        sort_order_int = int(sort_order)
    except (TypeError, ValueError):
        sort_order_int = 0

    # Validate category title length (5-200 characters)
    is_valid, error_msg = _validate_category_title_length(title, min_len=5, max_len=200)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    cat, err = create_category(
        slug=slug,
        title=title,
        description=description,
        parent_id=parent_id_int,
        sort_order=sort_order_int,
        is_active=is_active,
        is_private=is_private,
        required_role=required_role,
    )
    if err:
        status = 409 if "already exists" in err.lower() else 400
        return jsonify({"error": err}), status
    log_activity(
        actor=user,
        category="forum",
        action="category_created",
        status="success",
        message=f"Forum category created: {cat.slug}",
        route=request.path,
        method=request.method,
        target_type="forum_category",
        target_id=str(cat.id),
    )
    return jsonify(cat.to_dict()), 201


@api_v1_bp.route("/forum/admin/categories/<int:category_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_admin_category_update(category_id: int):
    """
    Update a forum category (admin only).
    Body: optional title, description, sort_order, is_active, is_private, required_role.
    """
    user, err_resp = _require_admin()
    if err_resp:
        return err_resp
    cat = ForumCategory.query.get(category_id)
    if not cat:
        return jsonify({"error": "Category not found"}), 404
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    title = data.get("title")
    description = data.get("description")
    sort_order = data.get("sort_order")
    is_active = data.get("is_active")
    is_private = data.get("is_private")
    required_role = data.get("required_role")
    sort_order_int: Optional[int] = None
    if sort_order is not None:
        try:
            sort_order_int = int(sort_order)
        except (TypeError, ValueError):
            return jsonify({"error": "sort_order must be an integer"}), 400

    # Validate category title length if provided (5-200 characters)
    if title is not None:
        # Type check first
        if not isinstance(title, str):
            return jsonify({"error": "Title must be a string"}), 400
        title = title.strip()
        is_valid, error_msg = _validate_category_title_length(title, min_len=5, max_len=200)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

    cat = update_category(
        cat,
        title=title,
        description=description,
        sort_order=sort_order_int,
        is_active=bool(is_active) if is_active is not None else None,
        is_private=bool(is_private) if is_private is not None else None,
        required_role=required_role,
    )
    log_activity(
        actor=user,
        category="forum",
        action="category_updated",
        status="success",
        message=f"Forum category updated: {cat.slug}",
        route=request.path,
        method=request.method,
        target_type="forum_category",
        target_id=str(cat.id),
    )
    return jsonify(cat.to_dict()), 200


@api_v1_bp.route("/forum/admin/categories/<int:category_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_admin_category_delete(category_id: int):
    """
    Delete a forum category (admin only). This will cascade to threads/posts per
    the database schema (ondelete rules).
    """
    user, err_resp = _require_admin()
    if err_resp:
        return err_resp
    cat = ForumCategory.query.get(category_id)
    if not cat:
        return jsonify({"error": "Category not found"}), 404
    delete_category(cat)
    log_activity(
        actor=user,
        category="forum",
        action="category_deleted",
        status="success",
        message=f"Forum category deleted: {cat.slug}",
        route=request.path,
        method=request.method,
        target_type="forum_category",
        target_id=str(category_id),
    )
    return jsonify({"message": "Deleted"}), 200


# --- Tag admin ---------------------------------------------------------------


@api_v1_bp.route("/forum/tags", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_tags_list():
    """
    List all tags (moderator/admin only). Paginated with optional search.
    Query: q, page, limit.
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 50, min_val=1, max_val=100)
    q = (request.args.get("q") or "").strip() or None
    tags, total = list_all_tags(page=page, per_page=limit, q=q)
    counts = batch_tag_thread_counts([t.id for t in tags])
    items = []
    for t in tags:
        items.append({
            "id": t.id,
            "slug": t.slug,
            "label": t.label,
            "thread_count": counts.get(t.id, 0),
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return jsonify({"items": items, "total": total, "page": page, "per_page": limit}), 200


@api_v1_bp.route("/forum/tags/<int:tag_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@jwt_required()
def forum_tag_delete(tag_id: int):
    """
    Delete a tag if unused (admin only). Returns 409 if tag has thread associations.
    """
    user, err_resp = _require_admin()
    if err_resp:
        return err_resp
    tag = ForumTag.query.get(tag_id)
    if not tag:
        return jsonify({"error": "Tag not found"}), 404
    err = delete_tag(tag)
    if err:
        return jsonify({"error": err}), 409
    log_activity(
        actor=user,
        category="forum",
        action="tag_deleted",
        status="success",
        message=f"Forum tag deleted: {tag.slug}",
        route=request.path,
        method=request.method,
        target_type="forum_tag",
        target_id=str(tag_id),
    )
    return jsonify({"message": "Deleted"}), 200


# --- Subscriptions (thread subscribers list) --------------------------------


@api_v1_bp.route("/forum/threads/<int:thread_id>/subscribers", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_thread_subscribers(thread_id: int):
    """
    List subscribers for a thread (moderator/admin only).
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp
    thread = get_thread_by_id(thread_id)
    if not thread:
        return jsonify({"error": "Thread not found"}), 404

    subs = ForumThreadSubscription.query.filter_by(thread_id=thread_id).all()
    items = []
    for sub in subs:
        items.append({
            "id": sub.id,
            "thread_id": sub.thread_id,
            "user_id": sub.user_id,
            "username": sub.user.username if hasattr(sub, 'user') and sub.user else None,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
        })
    return jsonify({"items": items, "total": len(items)}), 200


# --- Moderation Dashboard ---------------------------------------------------


@api_v1_bp.route("/forum/moderation/metrics", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_moderation_metrics():
    """
    Get lightweight moderation metrics (moderator/admin only).
    Returns: open_reports count, hidden_posts count, locked_threads count.
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp

    open_reports = ForumReport.query.filter_by(status="open").count()
    hidden_posts = ForumPost.query.filter_by(status="hidden").count()
    locked_threads = ForumThread.query.filter_by(is_locked=True).count()
    pinned_threads = ForumThread.query.filter_by(is_pinned=True).filter(ForumThread.status != "deleted").count()

    return jsonify({
        "open_reports": open_reports,
        "hidden_posts": hidden_posts,
        "locked_threads": locked_threads,
        "pinned_threads": pinned_threads,
    }), 200


def _enrich_report_dict(r):
    """Add thread_slug and target_title for dashboard linking."""
    d = r.to_dict()
    if r.target_type == "thread":
        t = get_thread_by_id(r.target_id)
        d["thread_slug"] = t.slug if t and t.deleted_at is None else None
        d["target_title"] = t.title if t else None
    elif r.target_type == "post":
        p = get_post_by_id(r.target_id)
        if p and p.thread:
            d["thread_slug"] = p.thread.slug if p.thread.deleted_at is None else None
            d["target_title"] = (p.content or "")[:80] + ("..." if len(p.content or "") > 80 else "")
        else:
            d["thread_slug"] = None
            d["target_title"] = None
    else:
        d["thread_slug"] = None
        d["target_title"] = None
    return d


@api_v1_bp.route("/forum/moderation/recent-reports", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_moderation_recent_reports():
    """
    Get recent open reports for moderator action (moderator/admin only).
    Query: limit (default 10, max 50).
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp

    limit = _parse_int(request.args.get("limit"), 10, min_val=1, max_val=50)

    reports = ForumReport.query.filter_by(status="open").order_by(ForumReport.created_at.desc()).limit(limit).all()
    items = [_enrich_report_dict(r) for r in reports]
    return jsonify({"items": items, "total": len(items)}), 200


@api_v1_bp.route("/forum/moderation/recently-handled", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_moderation_recently_handled():
    """
    Get recently handled reports (moderator/admin only).
    Query: limit (default 10, max 50). Returns reports with status reviewed/resolved/dismissed, ordered by handled_at desc.
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp
    limit = _parse_int(request.args.get("limit"), 10, min_val=1, max_val=50)
    reports = (
        ForumReport.query.filter(ForumReport.status.in_(["reviewed", "escalated", "resolved", "dismissed"]))
        .filter(ForumReport.handled_at.isnot(None))
        .order_by(ForumReport.handled_at.desc())
        .limit(limit)
        .all()
    )
    items = [_enrich_report_dict(r) for r in reports]
    return jsonify({"items": items, "total": len(items)}), 200


@api_v1_bp.route("/forum/moderation/locked-threads", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_moderation_locked_threads():
    """List locked threads for dashboard (moderator/admin only). Query: limit (default 20, max 100)."""
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    threads = (
        ForumThread.query.filter_by(is_locked=True)
        .filter(ForumThread.status != "deleted")
        .order_by(ForumThread.updated_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    items = []
    for t in threads:
        items.append({
            "id": t.id,
            "slug": t.slug,
            "title": t.title,
            "category_slug": t.category.slug if t.category else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        })
    return jsonify({"items": items, "total": len(items)}), 200


@api_v1_bp.route("/forum/moderation/bulk-threads/status", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
def forum_moderation_bulk_threads_status():
    """
    Bulk lock/unlock/archive/unarchive threads.
    Body: { "thread_ids": [int, ...], "lock": true/false (optional), "archive": true/false (optional) }.
    Only moderators/admins with rights on the category may modify a thread.
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    ids = data.get("thread_ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "thread_ids must be a non-empty list"}), 400
    try:
        thread_ids = [int(x) for x in ids]
    except (TypeError, ValueError):
        return jsonify({"error": "thread_ids must contain integers"}), 400
    lock = data.get("lock")
    archive = data.get("archive")
    if lock is None and archive is None:
        return jsonify({"error": "At least one of lock or archive must be provided"}), 400

    before_states: dict[int, dict] = {}
    updated: list[int] = []
    for tid in thread_ids:
        thread = get_thread_by_id(tid)
        if not thread or not thread.category:
            continue
        # Ensure user can moderate this category
        if not user_can_moderate_category(user, thread.category):
            continue
        before_states[thread.id] = {"is_locked": thread.is_locked, "status": thread.status}
        if lock is not None:
            thread = set_thread_lock(thread, bool(lock))
        if archive is not None:
            if archive:
                thread = set_thread_archived(thread)
            else:
                thread = set_thread_unarchived(thread)
        updated.append(thread.id)

    if updated:
        actions = []
        after_state = {}
        if lock is not None:
            actions.append(f"lock={bool(lock)}")
            after_state["is_locked"] = bool(lock)
        if archive is not None:
            actions.append(f"archive={bool(archive)}")
            after_state["status"] = "archived" if archive else "open"
        log_activity(
            actor=user,
            category="forum",
            action="threads_bulk_status_updated",
            status="success",
            message=f"Threads {updated} updated ({', '.join(actions)})",
            route=request.path,
            method=request.method,
            target_type="forum_thread",
            target_id=",".join(str(x) for x in updated),
            metadata={"before": {str(tid): before_states.get(tid, {}) for tid in updated}, "after": after_state},
        )
    return jsonify({"updated_ids": updated}), 200


@api_v1_bp.route("/forum/moderation/bulk-posts/hide", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required()
def forum_moderation_bulk_posts_hide():
    """
    Bulk hide/unhide posts.
    Body: { "post_ids": [int, ...], "hidden": true/false }.
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    ids = data.get("post_ids") or []
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "post_ids must be a non-empty list"}), 400
    try:
        post_ids = [int(x) for x in ids]
    except (TypeError, ValueError):
        return jsonify({"error": "post_ids must contain integers"}), 400
    hidden = data.get("hidden")
    if hidden is None:
        return jsonify({"error": "hidden must be provided"}), 400

    before_states: dict[int, dict] = {}
    updated: list[int] = []
    for pid in post_ids:
        post = get_post_by_id(pid)
        if not post or not post.thread or not post.thread.category:
            continue
        if not user_can_moderate_category(user, post.thread.category):
            continue
        before_states[post.id] = {"status": post.status}
        if hidden:
            hide_post(post)
        else:
            unhide_post(post)
        updated.append(post.id)

    new_status = "hidden" if hidden else "visible"
    if updated:
        log_activity(
            actor=user,
            category="forum",
            action="posts_bulk_hidden" if hidden else "posts_bulk_unhidden",
            status="success",
            message=f"Posts {updated} {'hidden' if hidden else 'unhidden'}",
            route=request.path,
            method=request.method,
            target_type="forum_post",
            target_id=",".join(str(x) for x in updated),
            metadata={"before": {str(pid): before_states.get(pid, {}) for pid in updated}, "after": {"status": new_status}},
        )
    return jsonify({"updated_ids": updated, "hidden": bool(hidden)}), 200


@api_v1_bp.route("/forum/moderation/log", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_moderation_log():
    """
    Moderator/admin-visible moderation log for forum actions.
    Thin wrapper around activity logs filtered by category=forum.

    Query: q, status, date_from, date_to, page, limit.
    """
    user = get_current_user()
    if not user or not current_user_is_moderator_or_admin():
        return jsonify({"error": "Forbidden"}), 403

    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 50, min_val=1, max_val=100)
    q = request.args.get("q", "").strip() or None
    status = request.args.get("status", "").strip() or None
    date_from = request.args.get("date_from", "").strip() or None
    date_to = request.args.get("date_to", "").strip() or None

    items, total = list_activity_logs(
        page=page,
        limit=limit,
        q=q,
        category="forum",
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return jsonify(
        {
            "items": [e.to_dict() for e in items],
            "total": total,
            "page": page,
            "limit": limit,
        }
    ), 200


@api_v1_bp.route("/forum/moderation/pinned-threads", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_moderation_pinned_threads():
    """List pinned threads for dashboard (moderator/admin only). Query: limit (default 20, max 100)."""
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    threads = (
        ForumThread.query.filter_by(is_pinned=True)
        .filter(ForumThread.status != "deleted")
        .order_by(ForumThread.updated_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    items = []
    for t in threads:
        items.append({
            "id": t.id,
            "slug": t.slug,
            "title": t.title,
            "category_slug": t.category.slug if t.category else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        })
    return jsonify({"items": items, "total": len(items)}), 200


@api_v1_bp.route("/forum/moderation/hidden-posts", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_moderation_hidden_posts():
    """List hidden posts for dashboard (moderator/admin only). Query: limit (default 20, max 100)."""
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        return err_resp
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    posts = (
        ForumPost.query.filter_by(status="hidden")
        .order_by(ForumPost.updated_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    items = []
    for p in posts:
        thread = p.thread
        items.append({
            "id": p.id,
            "thread_id": p.thread_id,
            "thread_slug": thread.slug if thread and thread.deleted_at is None else None,
            "thread_title": thread.title if thread else None,
            "content_snippet": (p.content or "")[:120] + ("..." if len(p.content or "") > 120 else ""),
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        })
    return jsonify({"items": items, "total": len(items)}), 200


# --- Notifications (Foundation) -----------------------------------------------


@api_v1_bp.route("/notifications", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def notifications_list():
    """
    List notifications for current user.
    Query: page, limit, unread_only (boolean).
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp

    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)
    unread_only = request.args.get("unread_only", "").lower() in ("1", "true", "yes")

    q = Notification.query.filter_by(user_id=user.id)
    if unread_only:
        q = q.filter_by(is_read=False)
    q = q.order_by(Notification.created_at.desc())

    total = q.count()
    page = max(1, page)
    limit = max(1, min(limit, 100))
    start = (page - 1) * limit
    end = start + limit

    items = q.offset(start).limit(limit).all()
    items_data = []
    for n in items:
        d = n.to_dict()
        if n.target_type == "forum_thread":
            thread = get_thread_by_id(n.target_id)
            d["thread_slug"] = thread.slug if thread and thread.deleted_at is None else None
            d["target_post_id"] = None
        elif n.target_type == "forum_post":
            post = get_post_by_id(n.target_id)
            if post and post.thread and post.thread.deleted_at is None:
                d["thread_slug"] = post.thread.slug
                d["target_post_id"] = post.id
            else:
                d["thread_slug"] = None
                d["target_post_id"] = None
        else:
            d["thread_slug"] = None
            d["target_post_id"] = None
        items_data.append(d)

    return jsonify({
        "items": items_data,
        "total": total,
        "page": page,
        "per_page": limit,
    }), 200


@api_v1_bp.route("/notifications/<int:notification_id>/read", methods=["PATCH", "PUT"])
@limiter.limit("60 per minute")
@jwt_required()
def notification_mark_read(notification_id: int):
    """Mark a notification as read. Only the owner can mark it."""
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    n = Notification.query.filter_by(id=notification_id, user_id=user.id).first()
    if not n:
        return jsonify({"error": "Not found"}), 404
    n.is_read = True
    n.read_at = _utc_now()
    db.session.commit()
    return jsonify(n.to_dict()), 200


@api_v1_bp.route("/notifications/read-all", methods=["POST", "PUT"])
@limiter.limit("30 per minute")
@jwt_required()
def notifications_mark_all_read():
    """Mark all notifications for the current user as read."""
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    now = _utc_now()
    updated = Notification.query.filter_by(user_id=user.id, is_read=False).update(
        {Notification.is_read: True, Notification.read_at: now},
        synchronize_session=False,
    )
    db.session.commit()
    return jsonify({"message": "Marked all as read", "updated": updated}), 200

