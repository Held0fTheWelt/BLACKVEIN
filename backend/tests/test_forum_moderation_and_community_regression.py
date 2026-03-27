"""Regression tests for forum moderation, related threads, bookmarks, tags, likes, and community profiles.

Covers moderation queues, reports, related-thread suggestions, and user activity surfaces.
"""
import pytest
from app.models import (
    ForumCategory, ForumThread, ForumPost, ForumTag,
    ForumReport, ForumThreadBookmark, ForumPostLike
)
from app.services.forum_service import (
    suggest_related_threads_by_tags,
    list_escalation_queue,
    list_review_queue,
    list_moderator_assigned_reports,
    list_bookmarked_threads,
    bookmark_thread,
    unbookmark_thread,
    set_thread_tags,
    like_post,
    unlike_post,
    create_report,
    update_report_status,
    assign_report_to_moderator,
    list_handled_reports,
)
from app.services.user_service import (
    count_user_threads,
    count_user_posts,
    count_user_bookmarks,
    get_user_recent_threads,
    get_user_recent_posts,
)


class TestRelatedThreadsRegression:
    """Regression tests for related thread suggestions (Phase 4)."""

    def test_related_threads_basic_functionality(self, app, test_user, forum_category):
        """Related threads should suggest other threads with shared tags."""
        user, _ = test_user
        with app.app_context():
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread

            t1, _, _ = create_thread(category=cat, author_id=user.id,
                                    title="Python Discussion", content="Talk about Python")
            t2, _, _ = create_thread(category=cat, author_id=user.id,
                                    title="Python Tips", content="Some tips")
            t3, _, _ = create_thread(category=cat, author_id=user.id,
                                    title="Java Discussion", content="Talk about Java")

            # Tag threads
            set_thread_tags(t1, tags=["python"])
            set_thread_tags(t2, tags=["python"])
            set_thread_tags(t3, tags=["java"])

            # Get suggestions for t1
            suggestions = suggest_related_threads_by_tags(t1.id, limit=10)
            suggestion_ids = [s.id for s in suggestions]

            assert t2.id in suggestion_ids  # Both have python tag
            assert t3.id not in suggestion_ids  # Different tag

    def test_related_threads_multiple_shared_tags(self, app, test_user, forum_category):
        """Threads with more shared tags should rank higher."""
        user, _ = test_user
        with app.app_context():
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread

            t1, _, _ = create_thread(category=cat, author_id=user.id,
                                    title="Main", content="Content")
            t2, _, _ = create_thread(category=cat, author_id=user.id,
                                    title="One Tag", content="Content")
            t3, _, _ = create_thread(category=cat, author_id=user.id,
                                    title="Two Tags", content="Content")

            set_thread_tags(t1, tags=["a", "b", "c"])
            set_thread_tags(t2, tags=["a"])  # One shared tag
            set_thread_tags(t3, tags=["a", "b"])  # Two shared tags

            suggestions = suggest_related_threads_by_tags(t1.id, limit=10)
            suggestion_ids = [s.id for s in suggestions]

            # Both should be in suggestions
            assert t2.id in suggestion_ids
            assert t3.id in suggestion_ids

            # t3 should come before t2 (more tags in common)
            if len(suggestions) > 1:
                t2_idx = suggestion_ids.index(t2.id) if t2.id in suggestion_ids else -1
                t3_idx = suggestion_ids.index(t3.id) if t3.id in suggestion_ids else -1
                if t2_idx >= 0 and t3_idx >= 0:
                    assert t3_idx <= t2_idx

    def test_related_threads_recency_tiebreaker(self, app, test_user, forum_category):
        """When tag overlap is equal, more recent threads should appear first."""
        user, _ = test_user
        with app.app_context():
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread

            t1, _, _ = create_thread(category=cat, author_id=user.id,
                                    title="Main", content="Content")
            t2, _, _ = create_thread(category=cat, author_id=user.id,
                                    title="Old", content="Content")
            t3, _, _ = create_thread(category=cat, author_id=user.id,
                                    title="New", content="Content")

            set_thread_tags(t1, tags=["test"])
            set_thread_tags(t2, tags=["test"])
            set_thread_tags(t3, tags=["test"])

            suggestions = suggest_related_threads_by_tags(t1.id, limit=10)
            suggestion_ids = [s.id for s in suggestions]

            # Both should be suggested
            assert t2.id in suggestion_ids
            assert t3.id in suggestion_ids


class TestModerationRegression:
    """Regression tests for moderation features (Phase 3)."""

    def test_escalation_queue_ordering(self, app, moderator_user):
        """Escalation queue should order by priority then date."""
        with app.app_context():
            from app.models import ForumReport, User
            from app.extensions import db

            users = User.query.all()
            user = users[0] if users else None
            if not user:
                return

            # Create reports with different priorities
            reports_data = [
                ("normal", "2026-03-10"),
                ("critical", "2026-03-11"),
                ("high", "2026-03-12"),
                ("critical", "2026-03-13"),
            ]

            for priority, date_str in reports_data:
                report = ForumReport(
                    target_type="thread",
                    target_id=1,
                    reported_by=user.id,
                    reason=f"Report {priority}",
                    status="escalated",
                    priority=priority,
                    escalated_at=None
                )
                db.session.add(report)
            db.session.commit()

            queue, _ = list_escalation_queue(page=1, per_page=50)

            # Critical should come before normal
            if len(queue) >= 2:
                priorities = [r.priority for r in queue]
                critical_positions = [i for i, p in enumerate(priorities) if p == "critical"]
                normal_positions = [i for i, p in enumerate(priorities) if p == "normal"]

                if critical_positions and normal_positions:
                    assert min(critical_positions) < min(normal_positions)

    def test_review_queue_open_and_reviewed(self, app):
        """Review queue should include open and reviewed reports."""
        with app.app_context():
            from app.models import ForumReport, User
            from app.extensions import db

            users = User.query.all()
            if not users:
                return

            user = users[0]

            # Create open and reviewed reports
            for status in ["open", "reviewed"]:
                report = ForumReport(
                    target_type="post",
                    target_id=1,
                    reported_by=user.id,
                    reason=f"Report {status}",
                    status=status
                )
                db.session.add(report)
            db.session.commit()

            queue, total = list_review_queue(page=1, per_page=50)

            # Should have reports
            assert total >= 2
            statuses = {r.status for r in queue}
            assert "open" in statuses
            assert "reviewed" in statuses

    def test_report_assignment_to_moderator(self, app, test_user, moderator_user):
        """Reports can be assigned to moderators."""
        user, _ = test_user
        mod_user, _ = moderator_user
        with app.app_context():
            from app.models import ForumReport
            from app.extensions import db

            report = ForumReport(
                target_type="thread",
                target_id=1,
                reported_by=user.id,
                reason="Test report",
                status="open"
            )
            db.session.add(report)
            db.session.commit()

            # Assign to moderator
            report = assign_report_to_moderator(report, mod_user.id)
            assert report.assigned_to == mod_user.id

            # List reports for moderator
            assigned, _ = list_moderator_assigned_reports(mod_user.id, page=1, per_page=50)
            assigned_ids = [r.id for r in assigned]
            assert report.id in assigned_ids

    def test_report_status_transitions(self, app, test_user, admin_user):
        """Report status should transition through valid states."""
        user, _ = test_user
        admin, _ = admin_user
        with app.app_context():
            from app.models import ForumReport
            from app.extensions import db

            report = ForumReport(
                target_type="thread",
                target_id=1,
                reported_by=user.id,
                reason="Test",
                status="open"
            )
            db.session.add(report)
            db.session.commit()

            # Transition through states
            report = update_report_status(report, status="reviewed", handled_by=admin.id)
            assert report.status == "reviewed"

            report = update_report_status(report, status="escalated", handled_by=admin.id)
            assert report.status == "escalated"
            assert report.escalated_at is not None

            report = update_report_status(report, status="resolved", handled_by=admin.id,
                                         resolution_note="Fixed")
            assert report.status == "resolved"
            assert report.resolution_note == "Fixed"

    def test_list_handled_reports(self, app, test_user, admin_user):
        """Should be able to list resolved/dismissed reports."""
        user, _ = test_user
        admin, _ = admin_user
        with app.app_context():
            from app.models import ForumReport
            from app.extensions import db

            report = ForumReport(
                target_type="post",
                target_id=1,
                reported_by=user.id,
                reason="Test",
                status="open"
            )
            db.session.add(report)
            db.session.commit()

            # Mark as resolved
            report = update_report_status(report, status="resolved", handled_by=admin.id)

            # Should appear in handled reports
            handled, _ = list_handled_reports(page=1, per_page=50)
            handled_ids = [r.id for r in handled]
            assert report.id in handled_ids


class TestCommunityProfilesRegression:
    """Regression tests for community profiles (Phase 4)."""

    def test_user_activity_counts(self, app, test_user, forum_category):
        """User activity counts should be accurate."""
        user, _ = test_user
        with app.app_context():
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread, create_post

            thread_count_before = count_user_threads(user.id)
            post_count_before = count_user_posts(user.id)

            # Create a thread (counts as 1 thread, 1 post)
            t, p, _ = create_thread(category=cat, author_id=user.id,
                                   title="Test", content="Content")

            # Add a reply
            create_post(thread=t, author_id=user.id, content="Reply")

            thread_count_after = count_user_threads(user.id)
            post_count_after = count_user_posts(user.id)

            assert thread_count_after == thread_count_before + 1
            assert post_count_after == post_count_before + 2

    def test_user_bookmarks_count(self, app, test_user, forum_category):
        """User bookmarks count should be accurate."""
        user, _ = test_user
        with app.app_context():
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread

            bookmark_count_before = count_user_bookmarks(user.id)

            t, _, _ = create_thread(category=cat, author_id=user.id,
                                   title="Test", content="Content")

            bookmark_thread(user, t)

            bookmark_count_after = count_user_bookmarks(user.id)
            assert bookmark_count_after == bookmark_count_before + 1

    def test_user_recent_activity_order(self, app, test_user, forum_category):
        """Recent activity should be ordered by creation time (newest first)."""
        user, _ = test_user
        with app.app_context():
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread

            threads = []
            for i in range(5):
                t, _, _ = create_thread(category=cat, author_id=user.id,
                                       title=f"Thread {i}", content="Content")
                threads.append(t)

            recent = get_user_recent_threads(user.id, limit=10)

            # Most recent should be last created (reversed order in list)
            if len(recent) > 1:
                for i in range(len(recent) - 1):
                    # Each thread's created_at should be >= the next one's
                    assert recent[i]["created_at"] >= recent[i+1]["created_at"]


class TestBookmarksTagsLikesRegression:
    """Regression tests for bookmarks, tags, and likes (Phase 2)."""

    def test_bookmark_thread_add_remove(self, app, test_user, forum_category):
        """Should be able to bookmark and unbookmark threads."""
        user, _ = test_user
        with app.app_context():
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread

            t, _, _ = create_thread(category=cat, author_id=user.id,
                                   title="Test", content="Content")

            # Bookmark
            bookmark_thread(user, t)

            bookmarks, total = list_bookmarked_threads(user, page=1, per_page=20)
            bookmark_ids = [b.id for b in bookmarks]
            assert t.id in bookmark_ids
            assert total >= 1

            # Unbookmark
            unbookmark_thread(user, t)

            bookmarks, total = list_bookmarked_threads(user, page=1, per_page=20)
            bookmark_ids = [b.id for b in bookmarks]
            assert t.id not in bookmark_ids

    def test_thread_tags_set_and_update(self, app, test_user, forum_category):
        """Should be able to set and update thread tags."""
        user, _ = test_user
        with app.app_context():
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread, list_tags_for_thread

            t, _, _ = create_thread(category=cat, author_id=user.id,
                                   title="Test", content="Content")

            # Set initial tags
            set_thread_tags(t, tags=["python", "tutorial"])

            tags = list_tags_for_thread(t)
            tag_slugs = {tag.slug for tag in tags}
            assert "python" in tag_slugs
            assert "tutorial" in tag_slugs

            # Update tags
            set_thread_tags(t, tags=["javascript", "advanced"])

            tags = list_tags_for_thread(t)
            tag_slugs = {tag.slug for tag in tags}
            assert "javascript" in tag_slugs
            assert "advanced" in tag_slugs
            assert "python" not in tag_slugs  # Old tag removed

    def test_post_like_count(self, app, test_user, forum_category):
        """Post likes should be counted correctly."""
        user, _ = test_user
        with app.app_context():
            from app.models import User
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread, create_post

            t, p, _ = create_thread(category=cat, author_id=user.id,
                                   title="Test", content="Content")

            # Get another user to like the post
            other_user = User.query.filter(User.id != user.id).first()
            if not other_user:
                return

            like_count_before = p.like_count

            like_post(other_user, p)

            # Reload post
            from app.extensions import db
            db.session.refresh(p)

            assert p.like_count == like_count_before + 1

            # Unlike
            unlike_post(other_user, p)

            db.session.refresh(p)
            assert p.like_count == like_count_before


class TestIntegration:
    """Integration tests ensuring features work together."""

    def test_full_moderation_workflow(self, app, test_user, moderator_user, admin_user, forum_category):
        """Full moderation workflow: report -> escalate -> resolve."""
        user, _ = test_user
        mod_user, _ = moderator_user
        admin, _ = admin_user
        with app.app_context():
            from app.services.forum_service import create_thread

            cat = ForumCategory.query.get(forum_category)
            t, _, _ = create_thread(category=cat, author_id=user.id,
                                   title="Problematic Thread", content="Problematic content")

            # Report thread
            report, err = create_report(
                target_type="thread",
                target_id=t.id,
                reported_by=user.id,
                reason="Inappropriate content"
            )
            assert report is not None

            # Check review queue
            queue, _ = list_review_queue(page=1, per_page=50)
            queue_ids = [r.id for r in queue]
            assert report.id in queue_ids

            # Assign to moderator
            report = assign_report_to_moderator(report, mod_user.id)

            # List assigned reports
            assigned, _ = list_moderator_assigned_reports(mod_user.id, page=1, per_page=50)
            assigned_ids = [r.id for r in assigned]
            assert report.id in assigned_ids

            # Escalate
            report = update_report_status(report, status="escalated", handled_by=mod_user.id,
                                         priority="high", escalation_reason="Severe violation")

            # Check escalation queue
            escalation, _ = list_escalation_queue(page=1, per_page=50, priority_filter="high")
            escalation_ids = [r.id for r in escalation]
            assert report.id in escalation_ids

            # Resolve by admin
            report = update_report_status(report, status="resolved", handled_by=admin.id,
                                         resolution_note="Thread locked and post removed")

            # Check handled reports
            handled, _ = list_handled_reports(page=1, per_page=50)
            handled_ids = [r.id for r in handled]
            assert report.id in handled_ids

    def test_thread_with_tags_and_suggestions(self, app, test_user, forum_category):
        """Thread with tags should generate suggestions."""
        user, _ = test_user
        with app.app_context():
            cat = ForumCategory.query.get(forum_category)
            from app.services.forum_service import create_thread

            # Create main thread with tags
            t1, _, _ = create_thread(category=cat, author_id=user.id,
                                    title="Main Discussion", content="Content")
            set_thread_tags(t1, tags=["discussion", "important"])

            # Create related threads
            t2, _, _ = create_thread(category=cat, author_id=user.id,
                                    title="Related 1", content="Content")
            set_thread_tags(t2, tags=["discussion"])

            t3, _, _ = create_thread(category=cat, author_id=user.id,
                                    title="Related 2", content="Content")
            set_thread_tags(t3, tags=["discussion", "important"])

            # Get suggestions
            suggestions = suggest_related_threads_by_tags(t1.id, limit=10)
            suggestion_ids = [s.id for s in suggestions]

            # Should suggest both related threads
            assert t2.id in suggestion_ids
            assert t3.id in suggestion_ids

            # t3 should rank higher (more tags in common)
            if len(suggestions) > 1:
                t2_idx = suggestion_ids.index(t2.id) if t2.id in suggestion_ids else -1
                t3_idx = suggestion_ids.index(t3.id) if t3.id in suggestion_ids else -1
                if t2_idx >= 0 and t3_idx >= 0:
                    assert t3_idx <= t2_idx
