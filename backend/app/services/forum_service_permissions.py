"""Forum permission helpers (split from forum_service for maintainability)."""

from __future__ import annotations

from typing import Optional

from app.models import ForumCategory, ForumPost, ForumThread, User

ROLE_RANK = {
    User.ROLE_USER: 1,
    User.ROLE_QA: 2,
    User.ROLE_MODERATOR: 3,
    User.ROLE_ADMIN: 4,
}


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
        return user_is_admin(user)
    if not category.is_private and not category.required_role:
        return True
    if user is None:
        return False
    if category.required_role:
        required_rank = ROLE_RANK.get(category.required_role, 0)
        return _user_role_rank(user) >= required_rank
    return user_is_moderator(user) or user_is_admin(user)


def user_can_create_thread(user: Optional[User], category: ForumCategory) -> bool:
    if user is None or user.is_banned:
        return False
    if not user_can_access_category(user, category):
        return False
    if not category.is_active and not user_is_admin(user):
        return False
    return True


def user_can_post_in_thread(user: Optional[User], thread: ForumThread) -> bool:
    if user is None or user.is_banned:
        return False
    if thread.is_locked or thread.status in ("locked", "archived", "hidden", "deleted"):
        return user_is_moderator(user) or user_is_admin(user)
    if thread.category is None:
        return False
    if not user_can_access_category(user, thread.category):
        return False
    return True


def user_can_view_thread(user: Optional[User], thread: ForumThread) -> bool:
    """True if user may view the thread itself (ignores per-post moderation)."""
    if thread.status == "deleted":
        return user_is_moderator(user) or user_is_admin(user)
    if thread.category is None:
        return False
    if thread.status in ("hidden", "archived"):
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
        return user_is_moderator(user) or user_is_admin(user)
    if post.status == "hidden":
        return user_is_moderator(user) or user_is_admin(user)
    return True


def user_can_edit_post(user: Optional[User], post: ForumPost) -> bool:
    if user is None or user.is_banned:
        return False
    if post.author_id == user.id and post.status not in ("hidden", "deleted"):
        return True
    if post.thread and post.thread.category:
        return user_can_moderate_category(user, post.thread.category)
    return False


def user_can_soft_delete_post(user: Optional[User], post: ForumPost) -> bool:
    if user is None or user.is_banned:
        return False
    if post.author_id == user.id and post.status not in ("hidden", "deleted"):
        return True
    if post.thread and post.thread.category:
        return user_can_moderate_category(user, post.thread.category)
    return False


def user_can_like_post(user: Optional[User], post: ForumPost) -> bool:
    if user is None or user.is_banned:
        return False
    if not user_can_view_post(user, post):
        return False
    if post.status in ("hidden", "deleted"):
        return False
    if post.thread and (
        post.thread.is_locked or post.thread.status in ("locked", "archived", "hidden", "deleted")
    ):
        return False
    return True


def user_can_moderate_category(user: Optional[User], category: ForumCategory) -> bool:
    if user is None or user.is_banned:
        return False
    if user_is_admin(user):
        return True
    if not user_is_moderator(user):
        return False
    from app.models.forum import ModeratorAssignment

    assignment = ModeratorAssignment.query.filter_by(
        user_id=user.id,
        category_id=category.id,
    ).first()
    return assignment is not None


def user_can_manage_categories(user: Optional[User]) -> bool:
    return user_is_admin(user)
