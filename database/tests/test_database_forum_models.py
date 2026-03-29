from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    ForumCategory,
    ForumPost,
    ForumPostLike,
    ForumTag,
    ForumThread,
    ForumThreadBookmark,
    ForumThreadSubscription,
    ForumThreadTag,
    ModeratorAssignment,
)


class TestForumCategoryAndThreadModels:
    def test_forum_category_slug_must_be_unique(self, db, category_factory):
        category_factory(slug="general")
        db.session.add(ForumCategory(slug="general", title="General 2"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_forum_category_parent_relationship_roundtrip(self, category_factory):
        parent = category_factory(slug="parent-cat", title="Parent")
        child = category_factory(slug="child-cat", title="Child", parent_id=parent.id)

        assert child.parent.id == parent.id
        assert [c.slug for c in parent.children] == ["child-cat"]
        assert child.to_dict()["parent_id"] == parent.id

    def test_forum_thread_requires_category_and_unique_slug(self, db, category_factory, user_factory, thread_factory):
        category = category_factory(slug="threads")
        author = user_factory()
        thread_factory(slug="welcome-thread", category=category, author=author)

        db.session.add(ForumThread(category_id=category.id, author_id=author.id, slug="welcome-thread", title="Duplicate"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        db.session.add(ForumThread(category_id=None, author_id=author.id, slug="missing-category", title="Broken"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_forum_thread_to_dict_contains_counters_and_flags(self, thread_factory):
        thread = thread_factory(is_pinned=True, is_locked=False, is_featured=True, view_count=12, reply_count=3)
        payload = thread.to_dict()
        assert payload["slug"] == thread.slug
        assert payload["is_pinned"] is True
        assert payload["is_featured"] is True
        assert payload["view_count"] == 12
        assert payload["reply_count"] == 3


class TestForumPostModels:
    def test_forum_post_parent_and_editor_relationships_roundtrip(self, db, post_factory, user_factory):
        parent = post_factory(content="Parent")
        editor = user_factory(role_name="moderator")
        child = post_factory(thread_id=parent.thread_id, parent_post_id=parent.id, edited_by=editor.id, content="Child")

        assert child.parent_post.id == parent.id
        assert [reply.id for reply in parent.replies] == [child.id]
        payload = child.to_dict()
        assert payload["parent_post_id"] == parent.id
        assert payload["edited_by"] == editor.id

    def test_forum_post_to_dict_exposes_author_username(self, post_factory, user_factory):
        author = user_factory(username="forum-author")
        post = post_factory(author=author)
        payload = post.to_dict()
        assert payload["author_id"] == author.id
        assert payload["author_username"] == "forum-author"

    def test_deleting_thread_cascades_posts(self, db, thread_factory, post_factory):
        thread = thread_factory(slug="cascade-thread")
        post_factory(thread=thread)
        post_factory(thread=thread)

        db.session.delete(thread)
        db.session.commit()
        assert ForumPost.query.count() == 0


class TestForumInteractionTables:
    def test_forum_post_like_unique_per_post_and_user(self, db, post_factory, user_factory):
        post = post_factory()
        user = user_factory(username="liker")
        db.session.add(ForumPostLike(post_id=post.id, user_id=user.id))
        db.session.commit()

        db.session.add(ForumPostLike(post_id=post.id, user_id=user.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_forum_post_delete_cascades_post_likes(self, db, post_factory, user_factory):
        post = post_factory()
        user = user_factory(username="cascade-liker")
        db.session.add(ForumPostLike(post_id=post.id, user_id=user.id))
        db.session.commit()

        db.session.delete(post)
        db.session.commit()
        assert ForumPostLike.query.count() == 0

    def test_thread_subscription_unique_per_thread_and_user(self, db, thread_factory, user_factory):
        thread = thread_factory()
        user = user_factory(username="subscriber")
        db.session.add(ForumThreadSubscription(thread_id=thread.id, user_id=user.id))
        db.session.commit()

        db.session.add(ForumThreadSubscription(thread_id=thread.id, user_id=user.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_thread_bookmark_unique_per_thread_and_user(self, db, thread_factory, user_factory):
        thread = thread_factory()
        user = user_factory(username="bookmark-user")
        db.session.add(ForumThreadBookmark(thread_id=thread.id, user_id=user.id))
        db.session.commit()

        db.session.add(ForumThreadBookmark(thread_id=thread.id, user_id=user.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_thread_delete_cascades_subscriptions_and_bookmarks(self, db, thread_factory, user_factory):
        thread = thread_factory()
        user = user_factory(username="reader")
        db.session.add_all(
            [
                ForumThreadSubscription(thread_id=thread.id, user_id=user.id),
                ForumThreadBookmark(thread_id=thread.id, user_id=user.id),
            ]
        )
        db.session.commit()

        db.session.delete(thread)
        db.session.commit()
        assert ForumThreadSubscription.query.count() == 0
        assert ForumThreadBookmark.query.count() == 0

    def test_forum_tag_unique_slug_and_thread_tag_unique_pair(self, db, thread_factory):
        thread = thread_factory()
        tag = ForumTag(slug="release-notes", label="Release Notes")
        db.session.add(tag)
        db.session.commit()

        db.session.add(ForumThreadTag(thread_id=thread.id, tag_id=tag.id))
        db.session.commit()

        db.session.add(ForumThreadTag(thread_id=thread.id, tag_id=tag.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        db.session.add(ForumTag(slug="release-notes", label="Duplicate"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_thread_delete_cascades_thread_tags(self, db, thread_factory):
        thread = thread_factory(slug="tagged-thread")
        tag = ForumTag(slug="cyberpunk", label="Cyberpunk")
        db.session.add(tag)
        db.session.commit()
        db.session.add(ForumThreadTag(thread_id=thread.id, tag_id=tag.id))
        db.session.commit()

        db.session.delete(thread)
        db.session.commit()
        assert ForumThreadTag.query.count() == 0


class TestModeratorAssignments:
    def test_moderator_assignment_unique_per_user_and_category(self, db, user_factory, category_factory):
        moderator = user_factory(role_name="moderator")
        admin = user_factory(role_name="admin")
        category = category_factory(slug="moderated")

        db.session.add(ModeratorAssignment(user_id=moderator.id, category_id=category.id, assigned_by=admin.id))
        db.session.commit()

        db.session.add(ModeratorAssignment(user_id=moderator.id, category_id=category.id, assigned_by=admin.id))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_moderator_assignment_to_dict_exposes_assignment_data(self, db, user_factory, category_factory):
        moderator = user_factory(role_name="moderator")
        admin = user_factory(role_name="admin")
        category = category_factory(slug="ops")
        assignment = ModeratorAssignment(user_id=moderator.id, category_id=category.id, assigned_by=admin.id, assigned_at=datetime.now(timezone.utc))
        db.session.add(assignment)
        db.session.commit()

        payload = assignment.to_dict()
        assert payload["user_id"] == moderator.id
        assert payload["category_id"] == category.id
        assert payload["assigned_by"] == admin.id
        assert payload["assigned_at"] is not None

    def test_deleting_category_cascades_moderator_assignments(self, db, user_factory, category_factory):
        moderator = user_factory(role_name="moderator")
        category = category_factory(slug="to-delete")
        db.session.add(ModeratorAssignment(user_id=moderator.id, category_id=category.id))
        db.session.commit()

        db.session.delete(category)
        db.session.commit()
        assert ModeratorAssignment.query.count() == 0
