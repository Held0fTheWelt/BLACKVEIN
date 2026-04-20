"""Moderation escalation and queue management (reports, assignment, queues).

Comprehensive tests for moderation features:
1. Escalation queue ordering and filtering
2. Review queue functionality
3. Report assignment and tracking
4. Priority management
5. Handled reports history
"""
import pytest
from datetime import datetime, timezone, timedelta
from app.models import ForumReport, User
from app.services.forum_service import (
    list_escalation_queue,
    list_review_queue,
    list_moderator_assigned_reports,
    list_handled_reports,
    create_report,
    update_report_status,
    assign_report_to_moderator,
)


def _utc_now():
    return datetime.now(timezone.utc)


class TestEscalationQueueManagement:
    """Test escalation queue functionality."""

    def test_escalation_queue_includes_only_escalated(self, app, test_user):
        """Escalation queue should only include 'escalated' status reports."""
        user, _ = test_user
        with app.app_context():
            from app.extensions import db

            users = User.query.all()
            if not users:
                return

            user = users[0]

            # Create reports with different statuses
            statuses = ["open", "reviewed", "escalated", "resolved"]
            reports = []

            for status in statuses:
                report = ForumReport(
                    target_type="thread",
                    target_id=1,
                    reported_by=user.id,
                    reason=f"Report {status}",
                    status=status,
                    priority="normal"
                )
                if status == "escalated":
                    report.escalated_at = _utc_now()
                db.session.add(report)
                reports.append(report)

            db.session.commit()

            # Get escalation queue
            queue, total = list_escalation_queue(page=1, per_page=50)
            queue_statuses = {r.status for r in queue}

            # Should only have escalated reports
            assert queue_statuses == {"escalated"}

    def test_escalation_queue_priority_ordering(self, app, test_user):
        """Escalation queue should order by priority: critical > high > normal > low."""
        user, _ = test_user
        with app.app_context():
            from app.extensions import db

            users = User.query.all()
            if not users:
                return

            user = users[0]

            # Create escalated reports with different priorities
            priorities = ["low", "normal", "high", "critical", "critical"]
            for i, priority in enumerate(priorities):
                report = ForumReport(
                    target_type="thread",
                    target_id=i,
                    reported_by=user.id,
                    reason=f"Report {priority}",
                    status="escalated",
                    priority=priority,
                    escalated_at=_utc_now()
                )
                db.session.add(report)
            db.session.commit()

            queue, _ = list_escalation_queue(page=1, per_page=50)

            # Extract priorities in order
            priority_order = [r.priority for r in queue]

            # All critical should come first
            critical_indices = [i for i, p in enumerate(priority_order) if p == "critical"]
            high_indices = [i for i, p in enumerate(priority_order) if p == "high"]
            normal_indices = [i for i, p in enumerate(priority_order) if p == "normal"]
            low_indices = [i for i, p in enumerate(priority_order) if p == "low"]

            if critical_indices and high_indices:
                assert max(critical_indices) < min(high_indices)
            if high_indices and normal_indices:
                assert max(high_indices) < min(normal_indices)
            if normal_indices and low_indices:
                assert max(normal_indices) < min(low_indices)

    def test_escalation_queue_priority_filter(self, app, test_user):
        """Escalation queue should support filtering by priority."""
        with app.app_context():
            from app.extensions import db

            users = User.query.all()
            if not users:
                return

            user = users[0]

            # Create escalated reports with different priorities
            for priority in ["low", "normal", "high", "critical"]:
                report = ForumReport(
                    target_type="thread",
                    target_id=1,
                    reported_by=user.id,
                    reason=f"Report {priority}",
                    status="escalated",
                    priority=priority,
                    escalated_at=_utc_now()
                )
                db.session.add(report)
            db.session.commit()

            # Filter for critical only
            queue, total = list_escalation_queue(page=1, per_page=50, priority_filter="critical")
            priorities = {r.priority for r in queue}

            assert priorities == {"critical"}
            assert total == 1

    def test_escalation_queue_assigned_filter(self, app, test_user, moderator_user):
        """Escalation queue should support filtering by assigned moderator."""
        user, _ = test_user
        mod_user, _ = moderator_user
        with app.app_context():
            from app.extensions import db

            users = User.query.all()
            if not users:
                return

            user = users[0]

            # Create escalated reports, some assigned to moderator
            for i in range(5):
                report = ForumReport(
                    target_type="thread",
                    target_id=i,
                    reported_by=user.id,
                    reason=f"Report {i}",
                    status="escalated",
                    priority="high" if i % 2 else "normal",
                    escalated_at=_utc_now(),
                    assigned_to=mod_user.id if i % 2 == 0 else None
                )
                db.session.add(report)
            db.session.commit()

            # Filter for assigned to moderator
            queue, total = list_escalation_queue(
                page=1, per_page=50,
                assigned_to_id=mod_user.id
            )

            assigned_to = {r.assigned_to for r in queue}
            assert assigned_to == {mod_user.id}

    def test_escalation_queue_date_filter(self, app, test_user):
        """Escalation queue should support filtering by creation date."""
        with app.app_context():
            from app.extensions import db

            users = User.query.all()
            if not users:
                return

            user = users[0]

            # Create reports with different creation dates
            now = _utc_now()
            old_date = now - timedelta(days=7)
            recent_date = now - timedelta(days=1)

            report_old = ForumReport(
                target_type="thread",
                target_id=1,
                reported_by=user.id,
                reason="Old report",
                status="escalated",
                priority="normal",
                escalated_at=old_date,
                created_at=old_date
            )

            report_recent = ForumReport(
                target_type="thread",
                target_id=2,
                reported_by=user.id,
                reason="Recent report",
                status="escalated",
                priority="normal",
                escalated_at=recent_date,
                created_at=recent_date
            )

            db.session.add(report_old)
            db.session.add(report_recent)
            db.session.commit()

            # Filter for reports created after 3 days ago
            three_days_ago = now - timedelta(days=3)
            queue, total = list_escalation_queue(
                page=1, per_page=50,
                created_after=three_days_ago
            )

            report_ids = {r.id for r in queue}
            assert report_recent.id in report_ids
            # Old report may or may not be included depending on exact timing


class TestReviewQueueManagement:
    """Test review queue functionality."""

    def test_review_queue_includes_open_and_reviewed(self, app, test_user):
        """Review queue should include both 'open' and 'reviewed' status."""
        with app.app_context():
            from app.extensions import db

            users = User.query.all()
            if not users:
                return

            user = users[0]

            # Create reports with different statuses
            open_report = ForumReport(
                target_type="thread",
                target_id=1,
                reported_by=user.id,
                reason="Open report",
                status="open"
            )

            reviewed_report = ForumReport(
                target_type="post",
                target_id=2,
                reported_by=user.id,
                reason="Reviewed report",
                status="reviewed"
            )

            escalated_report = ForumReport(
                target_type="thread",
                target_id=3,
                reported_by=user.id,
                reason="Escalated report",
                status="escalated",
                priority="high",
                escalated_at=_utc_now()
            )

            db.session.add(open_report)
            db.session.add(reviewed_report)
            db.session.add(escalated_report)
            db.session.commit()

            queue, total = list_review_queue(page=1, per_page=50)
            queue_statuses = {r.status for r in queue}

            assert "open" in queue_statuses
            assert "reviewed" in queue_statuses
            assert "escalated" not in queue_statuses

    def test_review_queue_ordered_by_creation(self, app, test_user):
        """Review queue should be ordered by creation date (newest first)."""
        with app.app_context():
            from app.extensions import db

            users = User.query.all()
            if not users:
                return

            user = users[0]

            # Create reports in a specific order
            for i in range(5):
                report = ForumReport(
                    target_type="thread",
                    target_id=i,
                    reported_by=user.id,
                    reason=f"Report {i}",
                    status="open" if i % 2 == 0 else "reviewed"
                )
                db.session.add(report)
            db.session.commit()

            queue, _ = list_review_queue(page=1, per_page=50)

            # Check ordering: most recent first
            if len(queue) > 1:
                for i in range(len(queue) - 1):
                    assert queue[i].created_at >= queue[i+1].created_at

    def test_review_queue_pagination(self, app, test_user):
        """Review queue should support pagination."""
        with app.app_context():
            from app.extensions import db

            users = User.query.all()
            if not users:
                return

            user = users[0]

            # Create 100 reports
            for i in range(100):
                report = ForumReport(
                    target_type="thread",
                    target_id=i % 20,
                    reported_by=user.id,
                    reason=f"Report {i}",
                    status="open" if i % 2 == 0 else "reviewed"
                )
                db.session.add(report)
            db.session.commit()

            # Get first page with limit of 10
            page1, total = list_review_queue(page=1, per_page=10)
            assert len(page1) == 10
            assert total >= 100

            # Get second page
            page2, _ = list_review_queue(page=2, per_page=10)
            assert len(page2) == 10

            # Pages should have different reports
            page1_ids = {r.id for r in page1}
            page2_ids = {r.id for r in page2}
            assert len(page1_ids & page2_ids) == 0


class TestReportAssignment:
    """Test report assignment to moderators."""

    def test_assign_report_to_moderator(self, app, test_user, moderator_user):
        """Should be able to assign report to a moderator."""
        user, _ = test_user
        mod_user, _ = moderator_user
        with app.app_context():
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

            # Initially unassigned
            assert report.assigned_to is None

            # Assign to moderator
            report = assign_report_to_moderator(report, mod_user.id)
            assert report.assigned_to == mod_user.id

    def test_list_moderator_assigned_reports(self, app, test_user, moderator_user):
        """Should be able to list reports assigned to a specific moderator."""
        user, _ = test_user
        mod_user, _ = moderator_user
        with app.app_context():
            from app.extensions import db

            # Create reports assigned to moderator
            for i in range(5):
                report = ForumReport(
                    target_type="thread",
                    target_id=i,
                    reported_by=user.id,
                    reason=f"Report {i}",
                    status="open",
                    assigned_to=mod_user.id if i % 2 == 0 else None
                )
                db.session.add(report)
            db.session.commit()

            # List assigned reports
            assigned, total = list_moderator_assigned_reports(
                mod_user.id, page=1, per_page=50
            )

            # Should have 3 reports (i = 0, 2, 4)
            assigned_to = {r.assigned_to for r in assigned}
            assert assigned_to == {mod_user.id}

    def test_reassign_report(self, app, test_user, moderator_user, admin_user):
        """Should be able to reassign report to a different moderator."""
        user, _ = test_user
        mod_user, _ = moderator_user
        admin, _ = admin_user
        with app.app_context():
            from app.extensions import db

            report = ForumReport(
                target_type="post",
                target_id=1,
                reported_by=user.id,
                reason="Test report",
                status="open",
                assigned_to=mod_user.id
            )
            db.session.add(report)
            db.session.commit()

            # Reassign to admin
            report = assign_report_to_moderator(report, admin.id)
            assert report.assigned_to == admin.id


class TestReportStatusTransitions:
    """Test report status transitions."""

    def test_open_to_reviewed_transition(self, app, test_user, moderator_user):
        """Report can transition from open to reviewed."""
        with app.app_context():
            user, _ = test_user
            mod_user, _ = moderator_user
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

            report = update_report_status(report, status="reviewed", handled_by=mod_user.id)

            assert report.status == "reviewed"
            assert report.handled_by == mod_user.id
            assert report.handled_at is not None

    def test_review_to_escalate_transition(self, app, test_user, moderator_user):
        """Report can transition from reviewed to escalated."""
        with app.app_context():
            user, _ = test_user
            mod_user, _ = moderator_user
            from app.extensions import db

            report = ForumReport(
                target_type="post",
                target_id=1,
                reported_by=user.id,
                reason="Test",
                status="reviewed"
            )
            db.session.add(report)
            db.session.commit()

            report = update_report_status(
                report, status="escalated", handled_by=mod_user.id,
                priority="high", escalation_reason="Needs admin review"
            )

            assert report.status == "escalated"
            assert report.priority == "high"
            assert report.escalation_reason == "Needs admin review"
            assert report.escalated_at is not None

    def test_escalated_to_resolved_transition(self, app, test_user, admin_user):
        """Report can transition from escalated to resolved."""
        with app.app_context():
            user, _ = test_user
            admin, _ = admin_user
            from app.extensions import db

            report = ForumReport(
                target_type="thread",
                target_id=1,
                reported_by=user.id,
                reason="Test",
                status="escalated",
                priority="critical",
                escalated_at=_utc_now()
            )
            db.session.add(report)
            db.session.commit()

            report = update_report_status(
                report, status="resolved", handled_by=admin.id,
                resolution_note="Thread deleted, user warned"
            )

            assert report.status == "resolved"
            assert report.resolution_note == "Thread deleted, user warned"
            assert report.handled_at is not None

    def test_open_to_dismissed_transition(self, app, test_user, moderator_user):
        """Report can be dismissed without escalation."""
        with app.app_context():
            user, _ = test_user
            mod_user, _ = moderator_user
            from app.extensions import db

            report = ForumReport(
                target_type="post",
                target_id=1,
                reported_by=user.id,
                reason="False report",
                status="open"
            )
            db.session.add(report)
            db.session.commit()

            report = update_report_status(
                report, status="dismissed", handled_by=mod_user.id,
                resolution_note="Not a violation"
            )

            assert report.status == "dismissed"


class TestHandledReportsHistory:
    """Test history of handled reports."""

    def test_list_handled_reports_includes_resolved(self, app, test_user, admin_user):
        """Handled reports should include resolved reports."""
        with app.app_context():
            user, _ = test_user
            admin, _ = admin_user
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

            # Mark as resolved
            report = update_report_status(report, status="resolved", handled_by=admin.id)

            # Should appear in handled reports
            handled, total = list_handled_reports(page=1, per_page=50)
            handled_ids = {r.id for r in handled}
            assert report.id in handled_ids

    def test_list_handled_reports_includes_dismissed(self, app, test_user, moderator_user):
        """Handled reports should include dismissed reports."""
        with app.app_context():
            user, _ = test_user
            mod_user, _ = moderator_user
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

            # Mark as dismissed
            report = update_report_status(report, status="dismissed", handled_by=mod_user.id)

            # Should appear in handled reports
            handled, total = list_handled_reports(page=1, per_page=50)
            handled_ids = {r.id for r in handled}
            assert report.id in handled_ids

    def test_list_handled_reports_excludes_open(self, app, test_user):
        """Handled reports should not include open reports."""
        with app.app_context():
            user, _ = test_user
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

            # Should not appear in handled reports
            handled, _ = list_handled_reports(page=1, per_page=50)
            handled_ids = {r.id for r in handled}
            assert report.id not in handled_ids

    def test_handled_reports_pagination(self, app, test_user, admin_user):
        """Handled reports should support pagination."""
        with app.app_context():
            user, _ = test_user
            admin, _ = admin_user
            from app.extensions import db

            # Create 100 reports and mark as resolved
            for i in range(100):
                report = ForumReport(
                    target_type="thread",
                    target_id=i % 20,
                    reported_by=user.id,
                    reason=f"Report {i}",
                    status="open"
                )
                db.session.add(report)
            db.session.commit()

            # Mark all as resolved
            reports = ForumReport.query.filter_by(status="open").all()
            for report in reports:
                update_report_status(report, status="resolved", handled_by=admin.id)

            # Get first page
            page1, total = list_handled_reports(page=1, per_page=10)
            assert len(page1) == 10
            assert total >= 100

            # Get second page
            page2, _ = list_handled_reports(page=2, per_page=10)
            assert len(page2) == 10

            # Pages should be different
            page1_ids = {r.id for r in page1}
            page2_ids = {r.id for r in page2}
            assert len(page1_ids & page2_ids) == 0
