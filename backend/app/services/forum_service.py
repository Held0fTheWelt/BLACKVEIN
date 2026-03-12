"""Forum service layer: categories, threads, posts, likes, reports, subscriptions, permissions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from flask import current_app

from app.extensions import db
from app.models import (
    ForumCategory,
    ForumThread,
    ForumPost,
    ForumPostLike,
    ForumReport,
    ForumThreadSubscription,
    User,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


ROLE_RANK = {
    User.ROLE_USER: 1,
    User.ROLE_QA: 2,
    User.ROLE_MODERATOR: 3,
    User.ROLE_ADMIN: 4,
}


# --- Permission helpers ------------------------------------------------------


def _user_role_rank(user: Optional[User]) -> int:
    if not user:
        return 0
    name = user.role
    return ROLE_RANK.get(name, 0)


def user_is_moderator(user: Optional[User]) -> bool:
    return bool(user and user.has_any_role((User.ROLE_MODERATOR, User.ROLE_ADMIN)))


def user_is_admin(user: Optional[User]) -> bool:
    return bool(user and user.has_role(User.ROLE_ADMIN))


def user_can_access_category(user: Optional[User], category: ForumCategory) -> bool:
    """True if user may read threads in this category."""
    if not category.is_active:
        # Only admins may see inactive categories.
        return user_is_admin(user)
    if not category.is_private and not category.required_role:
        return True
    # Private or role-restricted category.
    if user is None:
        return False
    if category.required_role:
        required_rank = ROLE_RANK.get(category.required_role, 0)
        return _user_role_rank(user) >= required_rank
    # Private without explicit required_role: treat as staff (moderator+)
    return user_is_moderator(user) or user_is_admin(user)


def user_can_create_thread(user: Optional[User], category: ForumCategory) -> bool:
    if user is None or user.is_banned:
        return False
    if not user_can_access_category(user, category):
        return False
    # Disallow posts in inactive categories for non-admins.
    if not category.is_active and not user_is_admin(user):
        return False
    return True


def user_can_post_in_thread(user: Optional[User], thread: ForumThread) -> bool:
    if user is None or user.is_banned:
        return False
    if thread.is_locked or thread.status in ("locked", "archived", "hidden", "deleted"):
        # Only moderators/admins may still post in locked/hidden/archived threads if needed.
        return user_is_moderator(user) or user_is_admin(user)
    if thread.category is None:
        return False
    if not user_can_access_category(user, thread.category):
        return False
    return True


def user_can_view_thread(user: Optional[User], thread: ForumThread) -> bool:
    """True if user may view the thread itself (ignores per-post moderation)."""
    if thread.status == "deleted":
        # Deleted threads are only visible to moderators/admins.
        return user_is_moderator(user) or user_is_admin(user)
    if thread.category is None:
        return False
    if thread.status in ("hidden", "archived"):
        # Hidden/archived threads are staff-only.
        return user_is_moderator(user) or user_is_admin(user)
    return user_can_access_category(user, thread.category)


def user_can_view_post(user: Optional[User], post: ForumPost) -> bool:
    """True if user may view a specific post."""
    thread = post.thread
    if thread is None:
        return False
    if not user_can_view_thread(user, thread):
        return False
    if post.status == "deleted":
        # Deleted posts: moderators/admins only.
        return user_is_moderator(user) or user_is_admin(user)
    if post.status == "hidden":
        # Hidden posts are staff-only.
        return user_is_moderator(user) or user_is_admin(user)
    return True


def user_can_edit_post(user: Optional[User], post: ForumPost) -> bool:
    if user is None or user.is_banned:
        return False
    if user_is_moderator(user) or user_is_admin(user):
        return True
    return post.author_id == user.id and post.status not in ("hidden", "deleted")


def user_can_soft_delete_post(user: Optional[User], post: ForumPost) -> bool:
    if user is None or user.is_banned:
        return False
    if user_is_moderator(user) or user_is_admin(user):
        return True
    # Author may soft-delete own visible post.
    return post.author_id == user.id and post.status not in ("hidden", "deleted")


def user_can_like_post(user: Optional[User], post: ForumPost) -> bool:
    if user is None or user.is_banned:
        return False
    # Like is only allowed if the user may actually view the post (thread + category checks).
    if not user_can_view_post(user, post):
        return False
    if post.status in ("hidden", "deleted"):
        return False
    if post.thread and (post.thread.is_locked or post.thread.status in ("locked", "archived", "hidden", "deleted")):
        return False
    return True


def user_can_moderate_category(user: Optional[User], category: ForumCategory) -> bool:
    """Moderation permission for a category: moderators and admins only."""
    return user_is_moderator(user) or user_is_admin(user)


def user_can_manage_categories(user: Optional[User]) -> bool:
    return user_is_admin(user)


# --- Category operations -----------------------------------------------------


def list_categories_for_user(user: Optional[User]) -> List[ForumCategory]:
    q = ForumCategory.query.order_by(ForumCategory.sort_order.asc(), ForumCategory.title.asc())
    cats = q.all()
    return [c for c in cats if user_can_access_category(user, c)]


def get_category_by_slug_for_user(user: Optional[User], slug: str) -> Optional[ForumCategory]:
    cat = ForumCategory.query.filter_by(slug=slug).first()
    if not cat:
        return None
    if not user_can_access_category(user, cat):
        return None
    return cat


def create_category(*, slug: str, title: str, description: str | None, parent_id: int | None, sort_order: int, is_active: bool, is_private: bool, required_role: str | None) -> Tuple[Optional[ForumCategory], Optional[str]]:
    if not slug or not title:
        return None, "slug and title are required"
    if ForumCategory.query.filter(db.func.lower(ForumCategory.slug) == slug.lower()).first():
        return None, "Category slug already exists"
    cat = ForumCategory(
        slug=slug,
        title=title,
        description=description or None,
        parent_id=parent_id,
        sort_order=sort_order or 0,
        is_active=bool(is_active),
        is_private=bool(is_private),
        required_role=required_role or None,
    )
    db.session.add(cat)
    db.session.commit()
    return cat, None


def update_category(cat: ForumCategory, *, title: str | None = None, description: str | None = None, sort_order: Optional[int] = None, is_active: Optional[bool] = None, is_private: Optional[bool] = None, required_role: Optional[str] = None) -> ForumCategory:
    if title is not None:
        cat.title = title
    if description is not None:
        cat.description = description or None
    if sort_order is not None:
        cat.sort_order = sort_order
    if is_active is not None:
        cat.is_active = is_active
    if is_private is not None:
        cat.is_private = is_private
    if required_role is not None:
        cat.required_role = required_role or None
    db.session.commit()
    return cat


def delete_category(cat: ForumCategory) -> None:
    db.session.delete(cat)
    db.session.commit()


# --- Thread operations -------------------------------------------------------


def list_threads_for_category(category: ForumCategory, page: int = 1, per_page: int = 20) -> Tuple[List[ForumThread], int]:
    q = ForumThread.query.filter_by(category_id=category.id)
    # Exclude deleted by default
    q = q.filter(ForumThread.status != "deleted")
    q = q.order_by(
        ForumThread.is_pinned.desc(),
        ForumThread.last_post_at.desc().nullslast(),
        ForumThread.created_at.desc(),
    )
    total = q.count()
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    offset = (page - 1) * per_page
    items = q.offset(offset).limit(per_page).all()
    return items, total


def get_thread_by_slug(slug: str) -> Optional[ForumThread]:
    return ForumThread.query.filter_by(slug=slug).first()


def get_thread_by_id(thread_id: int) -> Optional[ForumThread]:
    return ForumThread.query.get(thread_id)


def _normalize_slug(text: str) -> str:
    import re

    s = (text or "").strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s or "thread"


def _ensure_unique_thread_slug(base: str) -> str:
    slug = base
    idx = 1
    while ForumThread.query.filter(db.func.lower(ForumThread.slug) == slug.lower()).first():
        idx += 1
        slug = f"{base}-{idx}"
    return slug


def create_thread(*, category: ForumCategory, author_id: int | None, title: str, content: str) -> Tuple[Optional[ForumThread], Optional[ForumPost], Optional[str]]:
    title = (title or "").strip()
    content = (content or "").strip()
    if not title or not content:
        return None, None, "title and content are required"
    base_slug = _normalize_slug(title)
    slug = _ensure_unique_thread_slug(base_slug)
    now = _utc_now()
    thread = ForumThread(
        category_id=category.id,
        author_id=author_id,
        slug=slug,
        title=title,
        status="open",
        is_pinned=False,
        is_locked=False,
        is_featured=False,
        view_count=0,
        reply_count=0,
        created_at=now,
        updated_at=now,
    )
    db.session.add(thread)
    db.session.flush()
    # First post
    post = ForumPost(
        thread_id=thread.id,
        author_id=author_id,
        content=content,
        status="visible",
        created_at=now,
        updated_at=now,
    )
    db.session.add(post)
    db.session.flush()
    thread.last_post_at = now
    thread.last_post_id = post.id
    db.session.commit()
    return thread, post, None


def update_thread(thread: ForumThread, *, title: Optional[str] = None) -> ForumThread:
    if title is not None and title.strip():
        thread.title = title.strip()
    db.session.commit()
    return thread


def soft_delete_thread(thread: ForumThread) -> ForumThread:
    thread.status = "deleted"
    thread.deleted_at = _utc_now()
    db.session.commit()
    return thread


def hide_thread(thread: ForumThread) -> ForumThread:
    """Hide a thread from normal listings without deleting it."""
    thread.status = "hidden"
    thread.updated_at = _utc_now()
    db.session.commit()
    return thread


def unhide_thread(thread: ForumThread) -> ForumThread:
    """Unhide a previously hidden thread (re-open it)."""
    if thread.status == "hidden":
        thread.status = "open"
        thread.updated_at = _utc_now()
        db.session.commit()
    return thread


def set_thread_lock(thread: ForumThread, locked: bool) -> ForumThread:
    """Lock or unlock a thread for new posts."""
    thread.is_locked = bool(locked)
    if locked:
        thread.status = "locked"
    elif thread.status == "locked":
        thread.status = "open"
    thread.updated_at = _utc_now()
    db.session.commit()
    return thread


def set_thread_pinned(thread: ForumThread, pinned: bool) -> ForumThread:
    """Pin or unpin a thread within its category."""
    thread.is_pinned = bool(pinned)
    thread.updated_at = _utc_now()
    db.session.commit()
    return thread


def set_thread_featured(thread: ForumThread, featured: bool) -> ForumThread:
    """Mark a thread as featured (for future highlighting)."""
    thread.is_featured = bool(featured)
    thread.updated_at = _utc_now()
    db.session.commit()
    return thread


def increment_thread_view(thread: ForumThread) -> None:
    thread.view_count = (thread.view_count or 0) + 1
    thread.updated_at = _utc_now()
    db.session.commit()


def recalc_thread_counters(thread: ForumThread) -> None:
    """Recalculate reply_count, last_post_at, last_post_id based on non-hidden, non-deleted posts."""
    q = ForumPost.query.filter_by(thread_id=thread.id).filter(
        ForumPost.status.notin_(("deleted", "hidden"))
    )
    # Count posts excluding the first one as replies
    total_posts = q.count()
    thread.reply_count = max(0, total_posts - 1)
    last_post = q.order_by(ForumPost.created_at.desc()).first()
    if last_post:
        thread.last_post_at = last_post.created_at
        thread.last_post_id = last_post.id
    db.session.commit()


# --- Post operations ---------------------------------------------------------


def list_posts_for_thread(
    thread: ForumThread,
    page: int = 1,
    per_page: int = 20,
    include_hidden: bool = False,
    include_deleted: bool = False,
) -> Tuple[List[ForumPost], int]:
    """
    List posts for a thread.

    By default, excludes posts with status 'hidden' or 'deleted'. Moderation
    views can set include_hidden/include_deleted to True to see everything.
    """
    q = ForumPost.query.filter_by(thread_id=thread.id)
    if not include_deleted:
        q = q.filter(ForumPost.status != "deleted")
    if not include_hidden:
        q = q.filter(ForumPost.status != "hidden")
    q = q.order_by(ForumPost.created_at.asc())
    total = q.count()
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    offset = (page - 1) * per_page
    items = q.offset(offset).limit(per_page).all()
    return items, total


def get_post_by_id(post_id: int) -> Optional[ForumPost]:
    return ForumPost.query.get(post_id)


def create_post(*, thread: ForumThread, author_id: int | None, content: str, parent_post_id: int | None = None) -> Tuple[Optional[ForumPost], Optional[str]]:
    content = (content or "").strip()
    if not content:
        return None, "content is required"

    parent = None
    if parent_post_id is not None:
        # Validate that parent exists
        parent = ForumPost.query.get(parent_post_id)
        if not parent:
            return None, "Parent post not found"
        # Validate that parent belongs to the same thread
        if parent.thread_id != thread.id:
            return None, "Parent post must belong to the same thread"
        # Enforce shallow reply depth (only one level of replies)
        if parent.parent_post_id is not None:
            return None, "Maximum reply depth exceeded"
        # Do not allow replies to hidden/deleted posts
        if parent.status in ("hidden", "deleted"):
            return None, "Cannot reply to hidden or deleted post"

    now = _utc_now()
    post = ForumPost(
        thread_id=thread.id,
        author_id=author_id,
        parent_post_id=parent_post_id,
        content=content,
        status="visible",
        created_at=now,
        updated_at=now,
    )
    db.session.add(post)
    db.session.flush()
    thread.reply_count = (thread.reply_count or 0) + 1
    thread.last_post_at = now
    thread.last_post_id = post.id
    db.session.commit()
    return post, None


def update_post(post: ForumPost, *, content: str, editor_id: Optional[int]) -> ForumPost:
    post.content = (content or "").strip()
    post.edited_at = _utc_now()
    post.edited_by = editor_id
    if post.status == "visible":
        post.status = "edited"
    post.updated_at = _utc_now()
    db.session.commit()
    return post


def soft_delete_post(post: ForumPost) -> ForumPost:
    post.status = "deleted"
    post.deleted_at = _utc_now()
    db.session.commit()
    # Recalculate thread counters
    if post.thread:
        recalc_thread_counters(post.thread)
    return post


def hide_post(post: ForumPost) -> ForumPost:
    post.status = "hidden"
    post.updated_at = _utc_now()
    db.session.commit()
    if post.thread:
        recalc_thread_counters(post.thread)
    return post


def unhide_post(post: ForumPost) -> ForumPost:
    if post.status == "hidden":
        post.status = "visible"
        post.updated_at = _utc_now()
        db.session.commit()
        if post.thread:
            recalc_thread_counters(post.thread)
    return post


# --- Reports helpers -----------------------------------------------------------


def get_report_by_id(report_id: int) -> Optional[ForumReport]:
    return ForumReport.query.get(report_id)


def list_reports_for_target(target_type: str, target_id: int) -> List[ForumReport]:
    return (
        ForumReport.query.filter_by(target_type=target_type, target_id=target_id)
        .order_by(ForumReport.created_at.desc())
        .all()
    )


# --- Likes -------------------------------------------------------------------


def like_post(user: User, post: ForumPost) -> Tuple[Optional[ForumPostLike], Optional[str]]:
    existing = ForumPostLike.query.filter_by(post_id=post.id, user_id=user.id).first()
    if existing:
        return existing, None
    like = ForumPostLike(post_id=post.id, user_id=user.id, created_at=_utc_now())
    db.session.add(like)
    post.like_count = (post.like_count or 0) + 1
    db.session.commit()
    return like, None


def unlike_post(user: User, post: ForumPost) -> None:
    existing = ForumPostLike.query.filter_by(post_id=post.id, user_id=user.id).first()
    if not existing:
        return
    db.session.delete(existing)
    post.like_count = max(0, (post.like_count or 0) - 1)
    db.session.commit()


# --- Reports -----------------------------------------------------------------


def create_report(*, target_type: str, target_id: int, reported_by: Optional[int], reason: str) -> Tuple[Optional[ForumReport], Optional[str]]:
    if target_type not in ("thread", "post"):
        return None, "Invalid target_type"
    reason = (reason or "").strip()
    if not reason:
        return None, "reason is required"
    report = ForumReport(
        target_type=target_type,
        target_id=target_id,
        reported_by=reported_by,
        reason=reason,
        status="open",
        created_at=_utc_now(),
    )
    db.session.add(report)
    db.session.commit()
    return report, None


def list_reports(*, status: Optional[str] = None) -> List[ForumReport]:
    q = ForumReport.query
    if status:
        q = q.filter_by(status=status)
    return q.order_by(ForumReport.created_at.desc()).all()


def update_report_status(report: ForumReport, *, status: str, handled_by: Optional[int]) -> ForumReport:
    if status not in ("open", "reviewed", "resolved", "dismissed"):
        raise ValueError("Invalid report status")
    report.status = status
    report.handled_by = handled_by
    report.handled_at = _utc_now()
    db.session.commit()
    return report


# --- Subscriptions -----------------------------------------------------------


def subscribe_thread(user: User, thread: ForumThread) -> ForumThreadSubscription:
    existing = ForumThreadSubscription.query.filter_by(thread_id=thread.id, user_id=user.id).first()
    if existing:
        return existing
    sub = ForumThreadSubscription(thread_id=thread.id, user_id=user.id, created_at=_utc_now())
    db.session.add(sub)
    db.session.commit()
    return sub


def unsubscribe_thread(user: User, thread: ForumThread) -> None:
    existing = ForumThreadSubscription.query.filter_by(thread_id=thread.id, user_id=user.id).first()
    if not existing:
        return
    db.session.delete(existing)
    db.session.commit()

