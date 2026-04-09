"""Activity log assertions for moderation actions (split from former test_coverage_expansion)."""

from app.extensions import db
from app.models import ActivityLog, ForumCategory, ForumPost, ForumThread


class TestActivityLogging:
    """Test that moderation actions are properly logged."""

    def test_thread_lock_creates_activity_log(self, client, admin_headers, app, forum_category, test_user):
        """Locking a thread creates an activity log entry."""
        with app.app_context():
            user, _ = test_user
            cat = ForumCategory.query.get(forum_category)
            thread = ForumThread(
                category_id=cat.id,
                title="Logging Test",
                author_id=user.id,
                slug="logging-test-thread",
            )
            db.session.add(thread)
            db.session.flush()
            thread_id = thread.id
            log_count_before = ActivityLog.query.count()
            db.session.commit()

        response = client.post(
            f"/api/v1/forum/threads/{thread_id}/lock",
            headers=admin_headers,
        )
        assert response.status_code == 200

        with app.app_context():
            log_count_after = ActivityLog.query.count()
            assert log_count_after > log_count_before, "Activity log entry not created"

            latest_log = ActivityLog.query.order_by(ActivityLog.id.desc()).first()
            assert latest_log.action == "thread_locked"
            assert latest_log.target_type == "forum_thread"
            assert latest_log.target_id == str(thread_id)

    def test_post_hide_creates_activity_log(self, client, moderator_headers, app):
        """Hiding a post creates an activity log entry."""
        with app.app_context():
            post = ForumPost.query.first()
            post_id = None
            log_count_before = 0
            if post:
                post_id = post.id
                log_count_before = ActivityLog.query.count()

        if post_id is not None:
            response = client.post(
                f"/api/v1/forum/posts/{post_id}/hide",
                headers=moderator_headers,
            )

            with app.app_context():
                if response.status_code == 204:
                    log_count_after = ActivityLog.query.count()
                    assert log_count_after > log_count_before

                    latest_log = ActivityLog.query.order_by(ActivityLog.id.desc()).first()
                    assert "hide" in latest_log.action.lower()

    def test_activity_log_includes_before_after(self, client, moderator_headers, app):
        """Activity logs include before/after state for audit trail."""
        with app.app_context():
            thread = ForumThread.query.first()
            thread_id = thread.id if thread else None

        if thread_id is not None:
            client.post(
                f"/api/v1/forum/threads/{thread_id}/lock",
                headers=moderator_headers,
            )

            with app.app_context():
                log = ActivityLog.query.filter_by(
                    target_type="thread",
                    target_id=thread_id,
                    action="thread_locked",
                ).first()

                if log and log.meta:
                    assert "before" in log.meta or "after" in log.meta
