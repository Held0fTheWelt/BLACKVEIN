"""Forum API: categories, threads, posts, likes, reports.

Public/community endpoints are read-only and allow anonymous access where safe.
Authenticated endpoints require JWT; moderation/admin flows are role-restricted.
"""
from datetime import datetime
from typing import Optional

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.v1 import api_v1_bp
from app.auth.permissions import (
    current_user_is_admin,
    current_user_is_moderator,
    current_user_is_moderator_or_admin,
    get_current_user,
)
from app.extensions import limiter, db
from app.models import ForumCategory, ForumPostLike, ForumThread, ForumPost, ForumReport, ForumThreadSubscription, Notification
from app.services import log_activity
from app.services.forum_service import (
    create_category,
    create_post,
    create_report,
    create_thread,
    delete_category,
    get_category_by_slug_for_user,
    get_post_by_id,
    get_report_by_id,
    get_thread_by_id,
    get_thread_by_slug,
    hide_post,
    hide_thread,
    increment_thread_view,
    like_post,
    list_categories_for_user,
    list_posts_for_thread,
    list_reports,
    list_reports_for_target,
    list_threads_for_category,
    recalc_thread_counters,
    set_thread_featured,
    set_thread_lock,
    set_thread_pinned,
    soft_delete_post,
    soft_delete_thread,
    subscribe_thread,
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
    _utc_now,
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

    # Get raw threads for the category ...
    raw_items, _total = list_threads_for_category(cat, page=1, per_page=1000)
    # ... then apply per-thread visibility rules to avoid leaking hidden/archived/private threads.
    visible = [t for t in raw_items if user_can_view_thread(user, t)]

    total_visible = len(visible)
    page = max(1, page)
    limit = max(1, min(limit, 100))
    start = (page - 1) * limit
    end = start + limit
    page_items = visible[start:end]

    items_data = []
    for t in page_items:
        d = t.to_dict()
        d["author_username"] = t.author.username if t.author else None
        items_data.append(d)
    return jsonify(
        {
            "items": items_data,
            "total": total_visible,
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
    increment_thread_view(thread)
    data = thread.to_dict()
    data["author_username"] = thread.author.username if thread.author else None
    if thread.category:
        data["category"] = thread.category.to_dict()
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
    Simple search over thread titles (and optionally post content).
    Query: q, page, limit.
    """
    from app.models import ForumThread, ForumPost  # imported lazily to avoid cycles

    user = _current_user_optional()
    q_raw = (request.args.get("q") or "").strip()
    if not q_raw:
        return jsonify({"items": [], "total": 0, "page": 1, "per_page": 20}), 200
    page = _parse_int(request.args.get("page"), 1, min_val=1)
    limit = _parse_int(request.args.get("limit"), 20, min_val=1, max_val=100)

    like_pattern = f"%{q_raw}%"
    q = ForumThread.query.filter(ForumThread.status != "deleted")
    q = q.filter(ForumThread.title.ilike(like_pattern))
    # Restrict to categories the user may access
    q = q.join(ForumCategory).filter(ForumCategory.id == ForumThread.category_id)

    # Apply per-thread visibility rules in Python; for large data sets this could be optimized.
    all_matches = q.order_by(ForumThread.is_pinned.desc(), ForumThread.last_post_at.desc().nullslast()).all()
    visible = [t for t in all_matches if user_can_view_thread(user, t)]
    total = len(visible)
    page = max(1, page)
    limit = max(1, min(limit, 100))
    start = (page - 1) * limit
    end = start + limit
    items = visible[start:end]
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
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    if not title or not content:
        return jsonify({"error": "title and content are required"}), 400

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
    Update thread title. Author or moderators/admins only.
    Body: title (optional).
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
    title = data.get("title")
    if title is not None:
        title = title.strip()
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
    Soft-delete a thread. Author or moderators/admins only.
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    thread = get_thread_by_id(thread_id)
    if not thread:
        return jsonify({"error": "Thread not found"}), 404
    if not (thread.author_id == user.id or current_user_is_moderator() or current_user_is_admin()):
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
@limiter.limit("60 per minute")
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
    content = (data.get("content") or "").strip()
    parent_post_id = data.get("parent_post_id")
    parent_id_int: Optional[int] = None
    if parent_post_id is not None:
        try:
            parent_id_int = int(parent_post_id)
        except (TypeError, ValueError):
            return jsonify({"error": "parent_post_id must be an integer"}), 400

    post, err = create_post(
        thread=thread,
        author_id=user.id,
        content=content,
        parent_post_id=parent_id_int,
    )
    if err:
        return jsonify({"error": err}), 400
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


@api_v1_bp.route("/forum/posts/<int:post_id>", methods=["PUT"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_post_update(post_id: int):
    """
    Update a post's content. Author or moderators/admins only.
    Body: content.
    """
    user, err_resp = _require_user()
    if err_resp:
        return err_resp
    post = get_post_by_id(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    if not (user_can_edit_post(user, post) or current_user_is_moderator() or current_user_is_admin()):
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    content = data.get("content")
    if content is None:
        return jsonify({"error": "content is required"}), 400
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
    Like a post. Duplicate likes are ignored (idempotent).
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
        return jsonify({"error": err}), 400
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
    )
    return jsonify(thread.to_dict()), 200


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
    )
    return jsonify(post.to_dict()), 200


@api_v1_bp.route("/forum/reports", methods=["GET"])
@limiter.limit("60 per minute")
@jwt_required()
def forum_reports_list():
    """
    List forum reports (moderator/admin only).
    Query: status (open, reviewed, resolved, dismissed).
    """
    user, err_resp = _require_moderator_or_admin()
    if err_resp:
        # Allow moderators as well, but admin-only helper above already ensures admin;
        # to avoid introducing a new feature flag, we keep this simple.
        return err_resp
    status = (request.args.get("status") or "").strip() or None
    items = list_reports(status=status)
    return jsonify({"items": [r.to_dict() for r in items]}), 200


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
    Update report status (moderator/admin only).
    Body: status (open, reviewed, resolved, dismissed).
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
    try:
        report = update_report_status(report, status=status, handled_by=user.id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
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
    )
    return jsonify(report.to_dict()), 200


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
    slug = (data.get("slug") or "").strip()
    title = (data.get("title") or "").strip()
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

    return jsonify({
        "open_reports": open_reports,
        "hidden_posts": hidden_posts,
        "locked_threads": locked_threads,
    }), 200


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
    items = [r.to_dict() for r in reports]
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
    items_data = [n.to_dict() for n in items]

    return jsonify({
        "items": items_data,
        "total": total,
        "page": page,
        "per_page": limit,
    }), 200

