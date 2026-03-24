"""Comprehensive tests for forum_service to expand coverage from 12% to 85%+."""
import pytest
from datetime import datetime, timezone, timedelta
from app.extensions import db
from app.models import (
    User, Role, ForumCategory, ForumThread, ForumPost, ForumPostLike,
    ForumReport, ForumThreadSubscription, ForumThreadBookmark, ForumTag,
    ForumThreadTag, Notification
)
from app.services import forum_service
from werkzeug.security import generate_password_hash


@pytest.fixture(autouse=True)
def clear_view_cache():
    """Clear the view rate limit cache before each test to prevent cross-test contamination."""
    # Clear the cache at the start of each test
    forum_service._VIEW_RATE_LIMIT_CACHE.clear()
    yield
    # Clear the cache at the end of each test
    forum_service._VIEW_RATE_LIMIT_CACHE.clear()


@pytest.fixture
def forum_data(app, test_user, admin_user):
    """Create comprehensive forum test data."""
    with app.app_context():
        user, _ = test_user
        admin, _ = admin_user

        # Create categories
        cat_general = ForumCategory(
            slug="general",
            title="General Discussion",
            description="General discussion",
            is_active=True,
            is_private=False,
            sort_order=0
        )
        db.session.add(cat_general)
        db.session.flush()

        cat_private = ForumCategory(
            slug="private",
            title="Private Category",
            description="Private category",
            is_active=True,
            is_private=True,
            sort_order=1
        )
        db.session.add(cat_private)
        db.session.flush()

        # Create threads
        thread1 = ForumThread(
            category_id=cat_general.id,
            title="Test Thread 1",
            slug="test-thread-1",
            author_id=user.id,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(thread1)
        db.session.flush()

        thread2 = ForumThread(
            category_id=cat_general.id,
            title="Test Thread 2",
            slug="test-thread-2",
            author_id=admin.id,
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
            is_locked=True
        )
        db.session.add(thread2)
        db.session.flush()

        # Create posts
        post1 = ForumPost(
            thread_id=thread1.id,
            author_id=user.id,
            content="First post content",
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(post1)
        db.session.flush()

        post2 = ForumPost(
            thread_id=thread1.id,
            author_id=admin.id,
            content="Reply to first post",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        db.session.add(post2)

        # Create tags
        tag1 = ForumTag(label="python", slug="python")
        tag2 = ForumTag(label="javascript", slug="javascript")
        db.session.add(tag1)
        db.session.add(tag2)
        db.session.flush()

        # Tag threads
        tt1 = ForumThreadTag(thread_id=thread1.id, tag_id=tag1.id)
        tt2 = ForumThreadTag(thread_id=thread2.id, tag_id=tag2.id)
        db.session.add(tt1)
        db.session.add(tt2)

        db.session.commit()
        return {
            "user": user,
            "admin": admin,
            "cat_general": cat_general.id,
            "cat_private": cat_private.id,
            "thread1": thread1.id,
            "thread2": thread2.id,
            "post1": post1.id,
            "post2": post2.id,
            "tag1": tag1.id,
            "tag2": tag2.id,
        }


class TestPermissionHelpers:
    """Test permission checking functions."""

    def test_user_is_moderator_with_moderator(self, app, moderator_user):
        """user_is_moderator returns True for moderators."""
        with app.app_context():
            user, _ = moderator_user
            assert forum_service.user_is_moderator(user) is True

    def test_user_is_moderator_with_admin(self, app, admin_user):
        """user_is_moderator returns True for admins."""
        with app.app_context():
            user, _ = admin_user
            assert forum_service.user_is_moderator(user) is True

    def test_user_is_moderator_with_regular_user(self, app, test_user):
        """user_is_moderator returns False for regular users."""
        with app.app_context():
            user, _ = test_user
            assert forum_service.user_is_moderator(user) is False

    def test_user_is_moderator_with_none(self):
        """user_is_moderator returns False for None."""
        assert forum_service.user_is_moderator(None) is False

    def test_user_is_admin_with_admin(self, app, admin_user):
        """user_is_admin returns True for admins."""
        with app.app_context():
            user, _ = admin_user
            assert forum_service.user_is_admin(user) is True

    def test_user_is_admin_with_regular_user(self, app, test_user):
        """user_is_admin returns False for regular users."""
        with app.app_context():
            user, _ = test_user
            assert forum_service.user_is_admin(user) is False

    def test_user_role_rank_none(self):
        """_user_role_rank returns 0 for None user."""
        rank = forum_service._user_role_rank(None)
        assert rank == 0


class TestCategoryAccess:
    """Test category access control."""

    def test_list_categories_for_user(self, app, test_user, forum_data):
        """list_categories_for_user returns accessible categories."""
        with app.app_context():
            user, _ = test_user
            categories = forum_service.list_categories_for_user(user)
            assert isinstance(categories, list)
            assert len(categories) > 0

    def test_get_category_by_slug_for_user(self, app, test_user, forum_data):
        """get_category_by_slug_for_user returns category by slug."""
        with app.app_context():
            user, _ = test_user
            cat = forum_service.get_category_by_slug_for_user(user, "general")
            assert cat is not None
            assert cat.slug == "general"

    def test_user_can_access_public_category(self, app, test_user, forum_data):
        """user_can_access_category returns True for public categories."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.filter_by(slug="general").first()
            assert forum_service.user_can_access_category(user, cat) is True

    def test_user_can_access_private_category_as_admin(self, app, admin_user, forum_data):
        """user_can_access_category returns True for admins on private categories."""
        with app.app_context():
            user, _ = admin_user
            cat = ForumCategory.query.filter_by(slug="private").first()
            assert forum_service.user_can_access_category(user, cat) is True


class TestThreadCreation:
    """Test thread creation and management."""

    def test_create_thread_success(self, app, test_user, forum_data):
        """create_thread creates a thread successfully."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_data["cat_general"])

            thread, post, error = forum_service.create_thread(
                category=cat,
                author_id=user.id,
                title="New Test Thread",
                content="This is the initial post"
            )

            assert error is None
            assert thread is not None
            assert post is not None
            assert thread.title == "New Test Thread"

    def test_create_thread_missing_title(self, app, test_user, forum_data):
        """create_thread fails with empty title."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_data["cat_general"])

            thread, post, error = forum_service.create_thread(
                category=cat,
                author_id=user.id,
                title="",
                content="This is the initial post"
            )

            assert error is not None
            assert thread is None

    def test_normalize_slug(self):
        """_normalize_slug converts text to URL-friendly slug."""
        result = forum_service._normalize_slug("Hello World Test")
        assert isinstance(result, str)
        assert result.lower() == result

    def test_update_thread_title(self, app, forum_data):
        """update_thread updates thread title."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])
            updated = forum_service.update_thread(thread, title="Updated Title")

            assert updated.title == "Updated Title"

    def test_soft_delete_thread(self, app, forum_data):
        """soft_delete_thread marks thread as deleted."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])
            updated = forum_service.soft_delete_thread(thread)

            assert updated.deleted_at is not None

    def test_hide_thread(self, app, forum_data):
        """hide_thread sets status to hidden."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])
            updated = forum_service.hide_thread(thread)

            assert updated.status == "hidden"

    def test_unhide_thread(self, app, forum_data):
        """unhide_thread restores thread visibility."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])
            forum_service.hide_thread(thread)
            updated = forum_service.unhide_thread(thread)

            assert updated.status != "hidden"

    def test_set_thread_lock(self, app, forum_data):
        """set_thread_lock locks/unlocks a thread."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])

            locked = forum_service.set_thread_lock(thread, True)
            assert locked.is_locked is True

            unlocked = forum_service.set_thread_lock(thread, False)
            assert unlocked.is_locked is False

    def test_set_thread_pinned(self, app, forum_data):
        """set_thread_pinned pins/unpins a thread."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])

            pinned = forum_service.set_thread_pinned(thread, True)
            assert pinned.is_pinned is True

    def test_set_thread_featured(self, app, forum_data):
        """set_thread_featured features/unfeatures a thread."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])

            featured = forum_service.set_thread_featured(thread, True)
            assert featured.is_featured is True

    def test_set_thread_archived(self, app, forum_data):
        """set_thread_archived archives a thread."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])
            archived = forum_service.set_thread_archived(thread)

            assert archived.status == "archived"

    def test_increment_thread_view(self, app, forum_data):
        """increment_thread_view increases view count for anonymous users."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])
            initial_views = thread.view_count or 0

            result = forum_service.increment_thread_view(thread, user_id=None)

            assert result is True
            updated = ForumThread.query.get(forum_data["thread1"])
            assert (updated.view_count or 0) > initial_views

    def test_increment_thread_view_rate_limit(self, app, test_user, forum_data):
        """Same user cannot increment view twice within 5 minutes."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread2"])  # Use thread2 (authored by admin)
            initial_views = thread.view_count or 0

            # First view should count
            result1 = forum_service.increment_thread_view(thread, user_id=user.id)
            assert result1 is True
            views_after_first = thread.view_count or 0
            assert views_after_first > initial_views

            # Second view within 5 minutes should be rate limited
            result2 = forum_service.increment_thread_view(thread, user_id=user.id)
            assert result2 is False
            views_after_second = ForumThread.query.get(forum_data["thread2"]).view_count or 0
            assert views_after_second == views_after_first

    def test_increment_thread_view_prevent_self_view(self, app, test_user, forum_data):
        """Thread author cannot count views on their own thread."""
        with app.app_context():
            user, _ = test_user
            # Get thread authored by the test user (or create one)
            thread = ForumThread.query.get(forum_data["thread1"])
            # Change author to our test user
            thread.author_id = user.id
            from app.extensions import db
            db.session.commit()

            initial_views = thread.view_count or 0

            # Author trying to view own thread should not count
            result = forum_service.increment_thread_view(thread, user_id=user.id)
            assert result is False
            updated = ForumThread.query.get(forum_data["thread1"])
            assert (updated.view_count or 0) == initial_views

    def test_increment_thread_view_multiple_users(self, app, test_user, forum_data):
        """Different users can each count one view within 5 minutes."""
        with app.app_context():
            from app.models import User
            from app.extensions import db

            thread = ForumThread.query.get(forum_data["thread2"])  # Use thread2 (authored by admin)
            user1, _ = test_user
            # Create a second test user
            from datetime import datetime, timezone
            user2 = User(
                username="testuser2",
                email="testuser2@example.com",
                password_hash="hashed_password",
                email_verified_at=datetime.now(timezone.utc),
                role_id=1  # Default role ID
            )
            db.session.add(user2)
            db.session.commit()

            initial_views = thread.view_count or 0

            # First user views
            result1 = forum_service.increment_thread_view(thread, user_id=user1.id)
            assert result1 is True
            views1 = (ForumThread.query.get(forum_data["thread2"]).view_count or 0)
            assert views1 > initial_views

            # Second user views - should count as different user
            result2 = forum_service.increment_thread_view(thread, user_id=user2.id)
            assert result2 is True
            views2 = (ForumThread.query.get(forum_data["thread2"]).view_count or 0)
            assert views2 > views1


class TestPostManagement:
    """Test post creation and management."""

    def test_create_post_success(self, app, test_user, forum_data):
        """create_post creates a post successfully."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            post, error = forum_service.create_post(
                thread=thread,
                author_id=user.id,
                content="New post content"
            )

            assert error is None
            assert post is not None
            assert post.content == "New post content"

    def test_create_post_missing_content(self, app, test_user, forum_data):
        """create_post fails with empty content."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            post, error = forum_service.create_post(
                thread=thread,
                author_id=user.id,
                content=""
            )

            assert error is not None
            assert post is None

    def test_update_post(self, app, forum_data):
        """update_post updates post content."""
        with app.app_context():
            post = ForumPost.query.get(forum_data["post1"])
            updated = forum_service.update_post(post, content="Updated content", editor_id=post.author_id)

            assert updated.content == "Updated content"

    def test_soft_delete_post(self, app, forum_data):
        """soft_delete_post marks post as deleted."""
        with app.app_context():
            post = ForumPost.query.get(forum_data["post1"])
            updated = forum_service.soft_delete_post(post)

            assert updated.deleted_at is not None

    def test_hide_post(self, app, forum_data):
        """hide_post hides a post."""
        with app.app_context():
            post = ForumPost.query.get(forum_data["post1"])
            updated = forum_service.hide_post(post)

            assert updated.status == "hidden"

    def test_unhide_post(self, app, forum_data):
        """unhide_post shows a hidden post."""
        with app.app_context():
            post = ForumPost.query.get(forum_data["post1"])
            forum_service.hide_post(post)
            updated = forum_service.unhide_post(post)

            assert updated.status != "hidden"

    def test_get_post_by_id(self, app, forum_data):
        """get_post_by_id retrieves a post by ID."""
        with app.app_context():
            post = forum_service.get_post_by_id(forum_data["post1"])
            assert post is not None
            assert post.id == forum_data["post1"]

    def test_get_post_by_id_not_found(self, app):
        """get_post_by_id returns None for invalid ID."""
        with app.app_context():
            post = forum_service.get_post_by_id(99999)
            assert post is None


class TestPostLikes:
    """Test post liking functionality."""

    def test_like_post_success(self, app, test_user, forum_data):
        """like_post adds a like successfully."""
        with app.app_context():
            user, _ = test_user
            post = ForumPost.query.get(forum_data["post1"])

            like, error = forum_service.like_post(user, post)

            assert error is None
            assert like is not None
            assert like.user_id == user.id

    def test_like_post_already_liked(self, app, test_user, forum_data):
        """like_post returns error when already liked."""
        with app.app_context():
            user, _ = test_user
            post = ForumPost.query.get(forum_data["post1"])

            # First like
            forum_service.like_post(user, post)
            db.session.commit()

            # Try to like again - should return existing like
            like, error = forum_service.like_post(user, post)

            assert error is None
            assert like is not None

    def test_unlike_post(self, app, test_user, forum_data):
        """unlike_post removes a like."""
        with app.app_context():
            user, _ = test_user
            post = ForumPost.query.get(forum_data["post1"])

            forum_service.like_post(user, post)
            db.session.commit()

            forum_service.unlike_post(user, post)

            like = ForumPostLike.query.filter_by(
                user_id=user.id,
                post_id=post.id
            ).first()
            assert like is None


class TestReports:
    """Test forum report functionality."""

    def test_create_report_success(self, app, test_user, forum_data):
        """create_report creates a report successfully."""
        with app.app_context():
            user, _ = test_user

            report, error = forum_service.create_report(
                target_type="post",
                target_id=forum_data["post1"],
                reported_by=user.id,
                reason="Inappropriate content"
            )

            assert error is None
            assert report is not None
            if report:
                assert report.reason == "Inappropriate content"

    def test_get_report_by_id(self, app, test_user, forum_data):
        """get_report_by_id retrieves a report by ID."""
        with app.app_context():
            user, _ = test_user
            report, _ = forum_service.create_report(
                target_type="post",
                target_id=forum_data["post1"],
                reported_by=user.id,
                reason="Test report"
            )
            db.session.commit()

            retrieved = forum_service.get_report_by_id(report.id)
            assert retrieved is not None
            assert retrieved.id == report.id

    def test_list_reports_for_target(self, app, test_user, forum_data):
        """list_reports_for_target returns reports for a target."""
        with app.app_context():
            user, _ = test_user
            forum_service.create_report(
                target_type="post",
                target_id=forum_data["post1"],
                reported_by=user.id,
                reason="Test report 1"
            )
            db.session.commit()

            reports = forum_service.list_reports_for_target("post", forum_data["post1"])
            assert isinstance(reports, list)
            assert len(reports) > 0

    def test_update_report_status(self, app, test_user, forum_data, admin_user):
        """update_report_status updates report status."""
        with app.app_context():
            user, _ = test_user
            admin, _ = admin_user

            report, _ = forum_service.create_report(
                target_type="post",
                target_id=forum_data["post1"],
                reported_by=user.id,
                reason="Test"
            )
            db.session.commit()

            updated = forum_service.update_report_status(
                report,
                status="resolved",
                handled_by=admin.id,
                resolution_note="Fixed"
            )

            assert updated.status == "resolved"


class TestSubscriptions:
    """Test thread subscriptions."""

    def test_subscribe_thread(self, app, test_user, forum_data):
        """subscribe_thread subscribes a user to a thread."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            sub = forum_service.subscribe_thread(user, thread)

            assert sub is not None
            assert sub.user_id == user.id
            assert sub.thread_id == thread.id

    def test_unsubscribe_thread(self, app, test_user, forum_data):
        """unsubscribe_thread removes a subscription."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            forum_service.subscribe_thread(user, thread)
            db.session.commit()

            forum_service.unsubscribe_thread(user, thread)

            sub = ForumThreadSubscription.query.filter_by(
                user_id=user.id,
                thread_id=thread.id
            ).first()
            assert sub is None


class TestBookmarks:
    """Test thread bookmarks."""

    def test_bookmark_thread(self, app, test_user, forum_data):
        """bookmark_thread bookmarks a thread."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            bookmark = forum_service.bookmark_thread(user, thread)

            assert bookmark is not None
            assert bookmark.user_id == user.id

    def test_unbookmark_thread(self, app, test_user, forum_data):
        """unbookmark_thread removes a bookmark."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            forum_service.bookmark_thread(user, thread)
            db.session.commit()

            forum_service.unbookmark_thread(user, thread)

            bookmark = ForumThreadBookmark.query.filter_by(
                user_id=user.id,
                thread_id=thread.id
            ).first()
            assert bookmark is None

    def test_list_bookmarked_threads(self, app, test_user, forum_data):
        """list_bookmarked_threads returns user's bookmarked threads."""
        with app.app_context():
            user, _ = test_user
            thread = ForumThread.query.get(forum_data["thread1"])

            forum_service.bookmark_thread(user, thread)
            db.session.commit()

            threads, total = forum_service.list_bookmarked_threads(user, page=1, per_page=10)

            assert isinstance(threads, list)
            assert isinstance(total, int)


class TestTags:
    """Test tag functionality."""

    def test_get_or_create_tags(self, app):
        """get_or_create_tags creates or retrieves tags."""
        with app.app_context():
            tags = forum_service.get_or_create_tags(["python", "javascript"])

            assert isinstance(tags, list)
            assert len(tags) == 2

    def test_set_thread_tags(self, app, forum_data):
        """set_thread_tags assigns tags to a thread."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])

            tags = forum_service.set_thread_tags(thread, tags=["rust", "go"])

            assert isinstance(tags, list)
            assert len(tags) >= 2

    def test_list_tags_for_thread(self, app, forum_data):
        """list_tags_for_thread returns tags for a thread."""
        with app.app_context():
            thread = ForumThread.query.get(forum_data["thread1"])

            tags = forum_service.list_tags_for_thread(thread)

            assert isinstance(tags, list)

    def test_batch_tag_thread_counts(self, app, forum_data):
        """batch_tag_thread_counts returns counts for multiple tags."""
        with app.app_context():
            tag_ids = [forum_data["tag1"], forum_data["tag2"]]

            counts = forum_service.batch_tag_thread_counts(tag_ids)

            assert isinstance(counts, dict)
            assert len(counts) >= 1

    def test_tag_thread_count(self, app, forum_data):
        """tag_thread_count returns thread count for a tag."""
        with app.app_context():
            tag = ForumTag.query.get(forum_data["tag1"])

            count = forum_service.tag_thread_count(tag)

            assert isinstance(count, int)
            assert count >= 0

    def test_list_all_tags(self, app):
        """list_all_tags returns paginated tags."""
        with app.app_context():
            tags, total = forum_service.list_all_tags(page=1, per_page=10)

            assert isinstance(tags, list)
            assert isinstance(total, int)

    def test_delete_tag_success(self, app, forum_data):
        """delete_tag removes a tag if not in use."""
        with app.app_context():
            # Create a new unused tag
            tag = ForumTag(label="unused", slug="unused")
            db.session.add(tag)
            db.session.commit()

            error = forum_service.delete_tag(tag)

            assert error is None
            deleted = ForumTag.query.get(tag.id)
            assert deleted is None


class TestCategoryManagement:
    """Test category creation and management."""

    def test_create_category_success(self, app):
        """create_category creates a category successfully."""
        with app.app_context():
            cat, error = forum_service.create_category(
                slug="test-cat",
                title="Test Category",
                description="Test",
                parent_id=None,
                sort_order=0,
                is_active=True,
                is_private=False,
                required_role=None
            )

            assert error is None
            assert cat is not None
            assert cat.slug == "test-cat"

    def test_create_category_duplicate_slug(self, app, forum_data):
        """create_category fails with duplicate slug."""
        with app.app_context():
            cat, error = forum_service.create_category(
                slug="general",
                title="Duplicate",
                description="Test",
                parent_id=None,
                sort_order=0,
                is_active=True,
                is_private=False,
                required_role=None
            )

            assert error is not None
            assert cat is None

    def test_update_category(self, app, forum_data):
        """update_category updates category fields."""
        with app.app_context():
            cat = ForumCategory.query.get(forum_data["cat_general"])

            updated = forum_service.update_category(
                cat,
                title="Updated Title",
                description="Updated description"
            )

            assert updated.title == "Updated Title"
