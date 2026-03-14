"""Forum service layer: categories, threads, posts, likes, reports, subscriptions, permissions."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import List, Optional, Set, Tuple

from flask import current_app

from app.extensions import db
from app.models import (
    ForumCategory,
    ForumThread,
    ForumPost,
    ForumPostLike,
    ForumReport,
    ForumThreadSubscription,
    Notification,
    User,
    ForumThreadBookmark,
    ForumTag,
    ForumThreadTag,
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


def list_threads_for_category(
    category: ForumCategory,
    page: int = 1,
    per_page: int = 20,
    include_hidden: bool = False,
) -> Tuple[List[ForumThread], int]:
    q = ForumThread.query.filter_by(category_id=category.id)
    # Exclude deleted always; exclude hidden/archived for non-moderators
    q = q.filter(ForumThread.status != "deleted")
    if not include_hidden:
        q = q.filter(ForumThread.status.notin_(("hidden", "archived")))
    q = q.order_by(
        ForumThread.is_pinned.desc(),
        ForumThread.last_post_at.desc().nullslast(),
        ForumThread.created_at.desc(),
    )
    # Eager load author to prevent N+1 queries
    from sqlalchemy.orm import joinedload
    q = q.options(joinedload(ForumThread.author))

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


def set_thread_archived(thread: ForumThread) -> ForumThread:
    """Archive a thread (staff-only visibility, no new posts from regular users)."""
    thread.status = "archived"
    thread.updated_at = _utc_now()
    db.session.commit()
    return thread


def set_thread_unarchived(thread: ForumThread) -> ForumThread:
    """Restore an archived thread to open."""
    if thread.status == "archived":
        thread.status = "open"
        thread.updated_at = _utc_now()
        db.session.commit()
    return thread


def move_thread(thread: ForumThread, new_category: ForumCategory) -> Tuple[ForumThread, Optional[str]]:
    """Move a thread to another category. Returns (thread, error_message)."""
    if not new_category or not new_category.is_active:
        return thread, "Target category not found or inactive"
    if new_category.id == thread.category_id:
        return thread, None
    thread.category_id = new_category.id
    thread.updated_at = _utc_now()
    db.session.commit()
    return thread, None


def merge_threads(source: ForumThread, target: ForumThread) -> Optional[str]:
    """
    Merge source thread into target thread.

    Moves all posts and subscriptions from source into target, recalculates
    counters for both threads, and archives the source thread for staff-only
    visibility. Returns an error message string or None on success.
    """
    if not source or not target:
        return "Source and target threads are required"
    if source.id == target.id:
        return "Cannot merge a thread into itself"
    # Basic safety: do not merge already-deleted threads.
    if source.status == "deleted":
        return "Source thread is deleted and cannot be merged"

    # Move posts: reassign thread_id for all posts belonging to source.
    ForumPost.query.filter_by(thread_id=source.id).update(
        {ForumPost.thread_id: target.id},
        synchronize_session=False,
    )

    # Merge subscriptions: ensure all subscribers of source are subscribed to target.
    source_subs = ForumThreadSubscription.query.filter_by(thread_id=source.id).all()
    existing_target_user_ids = {
        s.user_id for s in ForumThreadSubscription.query.filter_by(thread_id=target.id).all()
    }
    for sub in source_subs:
        if sub.user_id not in existing_target_user_ids:
            new_sub = ForumThreadSubscription(
                thread_id=target.id,
                user_id=sub.user_id,
                created_at=_utc_now(),
            )
            db.session.add(new_sub)
            existing_target_user_ids.add(sub.user_id)
        db.session.delete(sub)

    # Archive the source thread (staff-only visibility).
    source.status = "archived"
    source.updated_at = _utc_now()

    db.session.commit()

    # Recalculate counters for both threads after merge.
    recalc_thread_counters(target)
    recalc_thread_counters(source)
    return None


def split_thread_from_post(
    *,
    source_thread: ForumThread,
    root_post: ForumPost,
    new_title: str,
    new_category: Optional[ForumCategory] = None,
) -> Tuple[Optional[ForumThread], Optional[str]]:
    """
    Split a thread starting from a given top-level post.

    Safe, constrained behavior:
    - root_post must belong to source_thread.
    - root_post must be a top-level post (parent_post_id is None) to avoid
      creating broken reply chains where a parent lives in another thread.
    - All direct replies whose parent_post_id == root_post.id move together
      with the root_post into the new thread.
    - Status/visibility of posts is preserved.
    - reply_count, last_post_at, last_post_id are recalculated for both
      source and new threads after the move.
    """
    if not source_thread or not root_post:
        return None, "Thread and root post are required"
    if root_post.thread_id != source_thread.id:
        return None, "Root post must belong to the source thread"
    if root_post.parent_post_id is not None:
        return None, "Only top-level posts can be used as split roots"

    title = (new_title or "").strip()
    if not title:
        return None, "New thread title is required"

    base_slug = _normalize_slug(title)
    slug = _ensure_unique_thread_slug(base_slug)
    now = _utc_now()

    category = new_category or source_thread.category
    if category is None:
        return None, "Source thread has no category"

    new_thread = ForumThread(
        category_id=category.id,
        author_id=root_post.author_id,
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
    db.session.add(new_thread)
    db.session.flush()

    # Move the root post and all its direct replies (single-level reply model).
    posts_to_move = ForumPost.query.filter(
        ForumPost.thread_id == source_thread.id,
        db.or_(ForumPost.id == root_post.id, ForumPost.parent_post_id == root_post.id),
    ).all()

    if not posts_to_move:
        return None, "No posts found to move for this split"

    for post in posts_to_move:
        post.thread_id = new_thread.id

    db.session.commit()

    # Recalculate counters for both threads after split.
    recalc_thread_counters(source_thread)
    recalc_thread_counters(new_thread)
    return new_thread, None


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
    # Eager load author to prevent N+1 queries
    from sqlalchemy.orm import joinedload
    q = q.options(joinedload(ForumPost.author))

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
    _create_mention_notifications_for_post(post, author_id)
    return post, None


def _mention_usernames_from_content(content: str) -> Set[str]:
    """Extract unique @username mentions from content (alphanumeric + underscore)."""
    if not content:
        return set()
    return set(re.findall(r"@([a-zA-Z0-9_]+)", content))


def _create_mention_notifications_for_post(post: ForumPost, author_id: Optional[int]) -> None:
    """Create mention notifications for users @mentioned in post content. Skip author and duplicates."""
    content = post.content or ""
    usernames = _mention_usernames_from_content(content)
    if not usernames:
        return
    thread = post.thread
    thread_title = (thread.title or "Post")[:60] if thread else "Post"
    author_username = post.author.username if post.author else "Someone"
    message = f"{author_username} mentioned you in: {thread_title}"
    already = set(
        n.user_id
        for n in Notification.query.filter_by(
            event_type="mention",
            target_type="forum_post",
            target_id=post.id,
        ).all()
    )
    for name in usernames:
        user = User.query.filter_by(username=name).first()
        if not user or user.id == author_id or user.id in already or getattr(user, "is_banned", False):
            continue
        already.add(user.id)
        n = Notification(
            user_id=user.id,
            event_type="mention",
            target_type="forum_post",
            target_id=post.id,
            message=message,
            is_read=False,
        )
        db.session.add(n)
    db.session.commit()


def update_post(post: ForumPost, *, content: str, editor_id: Optional[int]) -> ForumPost:
    post.content = (content or "").strip()
    post.edited_at = _utc_now()
    post.edited_by = editor_id
    if post.status == "visible":
        post.status = "edited"
    post.updated_at = _utc_now()
    db.session.commit()
    _create_mention_notifications_for_post(post, post.author_id)
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


def list_reports(
    *,
    status: Optional[str] = None,
    target_type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> Tuple[List[ForumReport], int]:
    """Return (items, total) with optional filters and pagination."""
    q = ForumReport.query
    if status:
        q = q.filter_by(status=status)
    if target_type and target_type in ("thread", "post"):
        q = q.filter_by(target_type=target_type)
    total = q.count()
    items = q.order_by(ForumReport.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return items, total


def update_report_status(
    report: ForumReport,
    *,
    status: str,
    handled_by: Optional[int],
    resolution_note: Optional[str] = None,
) -> ForumReport:
    if status not in ("open", "reviewed", "escalated", "resolved", "dismissed"):
        raise ValueError("Invalid report status")
    report.status = status
    report.handled_by = handled_by
    report.handled_at = _utc_now()
    if resolution_note is not None:
        report.resolution_note = resolution_note
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


def bookmark_thread(user: User, thread: ForumThread) -> ForumThreadBookmark:
    """Create or return an existing bookmark for a thread."""
    existing = ForumThreadBookmark.query.filter_by(thread_id=thread.id, user_id=user.id).first()
    if existing:
        return existing
    bm = ForumThreadBookmark(thread_id=thread.id, user_id=user.id, created_at=_utc_now())
    db.session.add(bm)
    db.session.commit()
    return bm


def unbookmark_thread(user: User, thread: ForumThread) -> None:
    """Remove a bookmark for a thread if it exists."""
    existing = ForumThreadBookmark.query.filter_by(thread_id=thread.id, user_id=user.id).first()
    if not existing:
        return
    db.session.delete(existing)
    db.session.commit()


def list_bookmarked_threads(user: User, *, page: int = 1, per_page: int = 20) -> Tuple[List[ForumThread], int]:
    """Return visible bookmarked threads for a user with pagination."""
    from sqlalchemy.orm import joinedload

    q = (
        ForumThread.query.join(ForumThreadBookmark, ForumThreadBookmark.thread_id == ForumThread.id)
        .filter(ForumThreadBookmark.user_id == user.id)
        .filter(ForumThread.deleted_at.is_(None))
    )
    q = q.join(ForumCategory, ForumCategory.id == ForumThread.category_id)
    q = q.filter(ForumCategory.is_active.is_(True))
    # Eager load author to prevent N+1 queries
    q = q.options(joinedload(ForumThread.author))

    total = q.count()
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    threads = (
        q.order_by(ForumThread.is_pinned.desc(), ForumThread.last_post_at.desc().nullslast())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return threads, total


def _normalize_tag_value(raw: str) -> Optional[str]:
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    s = re.sub(r"[^a-z0-9_-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or None


def get_or_create_tags(values: List[str]) -> List[ForumTag]:
    """Normalize tag strings, create missing ForumTag rows, and return tags."""
    if not values:
        return []
    normalized: List[Tuple[str, str]] = []
    for v in values:
        slug = _normalize_tag_value(v)
        if slug:
            normalized.append((slug, v.strip()))
    if not normalized:
        return []
    slug_to_label: dict[str, str] = {}
    for slug, label in normalized:
        if slug not in slug_to_label:
            slug_to_label[slug] = label
    existing_tags = ForumTag.query.filter(ForumTag.slug.in_(list(slug_to_label.keys()))).all()
    existing_by_slug = {t.slug: t for t in existing_tags}
    created: List[ForumTag] = []
    for slug, label in slug_to_label.items():
        if slug in existing_by_slug:
            continue
        tag = ForumTag(slug=slug, label=label[:64], created_at=_utc_now())
        db.session.add(tag)
        created.append(tag)
    if created:
        db.session.commit()
        for t in created:
            existing_by_slug[t.slug] = t
    return list(existing_by_slug.values())


def set_thread_tags(thread: ForumThread, *, tags: List[str]) -> List[ForumTag]:
    """Replace all tags on a thread with the given tag values."""
    tag_rows = get_or_create_tags(tags)
    tag_ids = {t.id for t in tag_rows}

    mappings = ForumThreadTag.query.filter_by(thread_id=thread.id).all()
    existing_tag_ids = {m.tag_id for m in mappings}

    for m in mappings:
        if m.tag_id not in tag_ids:
            db.session.delete(m)

    for t in tag_rows:
        if t.id not in existing_tag_ids:
            db.session.add(ForumThreadTag(thread_id=thread.id, tag_id=t.id))

    db.session.commit()
    return tag_rows


def list_tags_for_thread(thread: ForumThread) -> List[ForumTag]:
    """Return all tags associated with a thread."""
    return (
        ForumTag.query.join(ForumThreadTag, ForumThreadTag.tag_id == ForumTag.id)
        .filter(ForumThreadTag.thread_id == thread.id)
        .order_by(ForumTag.slug.asc())
        .all()
    )


def list_tags_for_threads(thread_ids: List[int]) -> dict[int, List[dict]]:
    """Return tags for multiple threads in a single query. Returns {thread_id: [{"slug": ..., "label": ...}]}."""
    if not thread_ids:
        return {}
    rows = (
        db.session.query(ForumThreadTag.thread_id, ForumTag.slug, ForumTag.label)
        .join(ForumTag, ForumTag.id == ForumThreadTag.tag_id)
        .filter(ForumThreadTag.thread_id.in_(thread_ids))
        .order_by(ForumThreadTag.thread_id, ForumTag.slug.asc())
        .all()
    )
    result: dict[int, List[dict]] = {}
    for tid, slug, label in rows:
        result.setdefault(tid, []).append({"slug": slug, "label": label})
    return result


def bookmarked_thread_ids_for_user(user_id: int, thread_ids: List[int]) -> Set[int]:
    """Return set of thread_ids that are bookmarked by a user from the given list."""
    if not user_id or not thread_ids:
        return set()
    rows = (
        ForumThreadBookmark.query.with_entities(ForumThreadBookmark.thread_id)
        .filter(ForumThreadBookmark.user_id == user_id, ForumThreadBookmark.thread_id.in_(thread_ids))
        .all()
    )
    return {r[0] for r in rows}


def list_all_tags(*, page: int = 1, per_page: int = 50, q: Optional[str] = None) -> Tuple[List[ForumTag], int]:
    """List all tags with optional label/slug search. Paginated."""
    query = ForumTag.query
    if q:
        like_pattern = f"%{q}%"
        query = query.filter(
            db.or_(ForumTag.slug.ilike(like_pattern), ForumTag.label.ilike(like_pattern))
        )
    query = query.order_by(ForumTag.slug.asc())
    total = query.count()
    page = max(1, page)
    per_page = max(1, min(per_page, 100))
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()
    return items, total


def tag_thread_count(tag: ForumTag) -> int:
    """Return number of thread-tag associations for a tag."""
    return ForumThreadTag.query.filter_by(tag_id=tag.id).count()


def batch_tag_thread_counts(tag_ids: List[int]) -> dict[int, int]:
    """Return a dict of tag_id -> thread count for all given tag IDs in a single query."""
    if not tag_ids:
        return {}
    from sqlalchemy import func
    rows = (
        db.session.query(ForumThreadTag.tag_id, func.count(ForumThreadTag.id))
        .filter(ForumThreadTag.tag_id.in_(tag_ids))
        .group_by(ForumThreadTag.tag_id)
        .all()
    )
    return dict(rows)


def delete_tag(tag: ForumTag) -> Optional[str]:
    """Delete a tag if it has no thread associations. Returns error string or None."""
    count = tag_thread_count(tag)
    if count > 0:
        return f"Tag is in use by {count} thread(s) and cannot be deleted"
    db.session.delete(tag)
    db.session.commit()
    return None


def create_notifications_for_thread_reply(
    thread: ForumThread,
    post: ForumPost,
    author_id: Optional[int],
) -> None:
    """Create notification for each thread subscriber except the post author."""
    subs = ForumThreadSubscription.query.filter_by(thread_id=thread.id).all()
    title_snippet = (thread.title or "Thread")[:80]
    message = f"New reply in: {title_snippet}"
    for sub in subs:
        if sub.user_id == author_id:
            continue
        n = Notification(
            user_id=sub.user_id,
            event_type="thread_reply",
            target_type="forum_thread",
            target_id=thread.id,
            message=message,
            is_read=False,
        )
        db.session.add(n)
    db.session.commit()

