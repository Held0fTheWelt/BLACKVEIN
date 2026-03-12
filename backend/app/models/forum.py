"""Forum models: categories, threads, posts, likes, reports, subscriptions."""
from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


class ForumCategory(db.Model):
    """Top-level forum category for grouping threads."""

    __tablename__ = "forum_categories"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("forum_categories.id", ondelete="SET NULL"), nullable=True)
    slug = db.Column(db.String(128), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(512), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_private = db.Column(db.Boolean, nullable=False, default=False)
    required_role = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)

    parent = db.relationship("ForumCategory", remote_side=[id], backref="children")

    def to_dict(self):
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "is_private": self.is_private,
            "required_role": self.required_role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ForumThread(db.Model):
    """Discussion thread inside a forum category."""

    __tablename__ = "forum_threads"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category_id = db.Column(db.Integer, db.ForeignKey("forum_categories.id", ondelete="CASCADE"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="open")
    is_pinned = db.Column(db.Boolean, nullable=False, default=False)
    is_locked = db.Column(db.Boolean, nullable=False, default=False)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    view_count = db.Column(db.Integer, nullable=False, default=0)
    reply_count = db.Column(db.Integer, nullable=False, default=0)
    last_post_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_post_id = db.Column(db.Integer, db.ForeignKey("forum_posts.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    category = db.relationship("ForumCategory", backref="threads")
    author = db.relationship("User", backref="forum_threads", foreign_keys=[author_id])

    def to_dict(self):
        return {
            "id": self.id,
            "category_id": self.category_id,
            "author_id": self.author_id,
            "slug": self.slug,
            "title": self.title,
            "status": self.status,
            "is_pinned": self.is_pinned,
            "is_locked": self.is_locked,
            "is_featured": self.is_featured,
            "view_count": self.view_count,
            "reply_count": self.reply_count,
            "last_post_at": self.last_post_at.isoformat() if self.last_post_at else None,
            "last_post_id": self.last_post_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class ForumPost(db.Model):
    """Post/comment within a forum thread."""

    __tablename__ = "forum_posts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("forum_threads.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    parent_post_id = db.Column(db.Integer, db.ForeignKey("forum_posts.id", ondelete="SET NULL"), nullable=True)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), nullable=False, default="visible")
    like_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)
    edited_at = db.Column(db.DateTime(timezone=True), nullable=True)
    edited_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)

    thread = db.relationship("ForumThread", backref="posts", foreign_keys=[thread_id])
    author = db.relationship("User", foreign_keys=[author_id])
    parent_post = db.relationship("ForumPost", remote_side=[id], backref="replies", foreign_keys=[parent_post_id])
    editor = db.relationship("User", foreign_keys=[edited_by])

    def to_dict(self):
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "author_id": self.author_id,
            "author_username": self.author.username if self.author else None,
            "parent_post_id": self.parent_post_id,
            "content": self.content,
            "status": self.status,
            "like_count": self.like_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "edited_at": self.edited_at.isoformat() if self.edited_at else None,
            "edited_by": self.edited_by,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class ForumPostLike(db.Model):
    """User like on a forum post."""

    __tablename__ = "forum_post_likes"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)

    __table_args__ = (
        db.UniqueConstraint("post_id", "user_id", name="uq_forum_post_like_post_user"),
    )

    post = db.relationship("ForumPost", backref="likes")


class ForumReport(db.Model):
    """User report on a thread or post for moderation."""

    __tablename__ = "forum_reports"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    target_type = db.Column(db.String(16), nullable=False)  # "thread" or "post"
    target_id = db.Column(db.Integer, nullable=False)
    reported_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reason = db.Column(db.String(512), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="open")
    handled_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    handled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)

    reporter = db.relationship("User", foreign_keys=[reported_by])
    handler = db.relationship("User", foreign_keys=[handled_by])

    def to_dict(self):
        return {
            "id": self.id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "reported_by": self.reported_by,
            "reason": self.reason,
            "status": self.status,
            "handled_by": self.handled_by,
            "handled_at": self.handled_at.isoformat() if self.handled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ForumThreadSubscription(db.Model):
    """User subscription to a thread (for future notifications)."""

    __tablename__ = "forum_thread_subscriptions"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("forum_threads.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)

    __table_args__ = (
        db.UniqueConstraint("thread_id", "user_id", name="uq_forum_thread_subscription_thread_user"),
    )

    thread = db.relationship("ForumThread", backref="subscriptions")

