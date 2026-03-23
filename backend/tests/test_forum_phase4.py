"""Tests for Phase 4 forum moderation features:
- resolution_note on single and bulk report updates
- GET /api/v1/forum/reports pagination (page, limit)
- GET /api/v1/forum/reports target_type filter
- GET /api/v1/forum/moderation/log returns activity log entries
"""
from datetime import datetime, timezone

import pytest

from app.extensions import db
from app.models import (
    ForumCategory,
    ForumThread,
    ForumPost,
    ForumReport,
    User,
    Role,
)


@pytest.fixture
def forum_setup(app, admin_user):
    """Create a category, thread, posts, and reports for testing."""
    with app.app_context():
        user, _ = admin_user
        cat = ForumCategory(slug="test-cat", title="Test", is_active=True)
        db.session.add(cat)
        db.session.flush()

        thread = ForumThread(
            category_id=cat.id,
            author_id=user.id,
            slug="test-thread",
            title="Test Thread",
            status="open",
        )
        db.session.add(thread)
        db.session.flush()

        post = ForumPost(
            thread_id=thread.id,
            author_id=user.id,
            content="Test post content",
            status="visible",
        )
        db.session.add(post)
        db.session.flush()

        # Create reports of different types
        reports = []
        for i in range(5):
            r = ForumReport(
                target_type="thread" if i % 2 == 0 else "post",
                target_id=thread.id if i % 2 == 0 else post.id,
                reported_by=user.id,
                reason=f"Report reason {i}",
                status="open",
            )
            db.session.add(r)
            reports.append(r)
        db.session.commit()

        for r in reports:
            db.session.refresh(r)
        db.session.refresh(thread)
        db.session.refresh(post)

        return {
            "category": cat,
            "thread": thread,
            "post": post,
            "reports": reports,
        }


class TestResolutionNoteSingleReport:
    """Test resolution_note saved on single report update."""

    def test_resolution_note_saved_on_update(self, app, client, admin_headers, forum_setup):
        with app.app_context():
            report_id = forum_setup["reports"][0].id
            resp = client.put(
                f"/api/v1/forum/reports/{report_id}",
                json={"status": "resolved", "resolution_note": "Fixed the issue"},
                headers=admin_headers,
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "resolved"
            assert data["resolution_note"] == "Fixed the issue"

    def test_resolution_note_absent_when_not_provided(self, app, client, admin_headers, forum_setup):
        with app.app_context():
            report_id = forum_setup["reports"][0].id
            resp = client.put(
                f"/api/v1/forum/reports/{report_id}",
                json={"status": "reviewed"},
                headers=admin_headers,
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["status"] == "reviewed"
            assert data["resolution_note"] is None

    def test_resolution_note_persists_in_db(self, app, client, admin_headers, forum_setup):
        with app.app_context():
            report_id = forum_setup["reports"][0].id
            client.put(
                f"/api/v1/forum/reports/{report_id}",
                json={"status": "dismissed", "resolution_note": "Not a real issue"},
                headers=admin_headers,
            )
            # Fetch the report again
            resp = client.get(
                f"/api/v1/forum/reports/{report_id}",
                headers=admin_headers,
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["resolution_note"] == "Not a real issue"


class TestResolutionNoteBulkReport:
    """Test resolution_note saved on bulk report update."""

    def test_bulk_resolution_note(self, app, client, admin_headers, forum_setup):
        with app.app_context():
            ids = [r.id for r in forum_setup["reports"][:3]]
            resp = client.post(
                "/api/v1/forum/reports/bulk-status",
                json={
                    "report_ids": ids,
                    "status": "resolved",
                    "resolution_note": "All resolved in batch",
                },
                headers=admin_headers,
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert set(data["updated_ids"]) == set(ids)

            # Verify each report has the note
            for rid in ids:
                resp2 = client.get(
                    f"/api/v1/forum/reports/{rid}",
                    headers=admin_headers,
                )
                assert resp2.get_json()["resolution_note"] == "All resolved in batch"

    def test_bulk_without_resolution_note(self, app, client, admin_headers, forum_setup):
        with app.app_context():
            ids = [r.id for r in forum_setup["reports"][:2]]
            resp = client.post(
                "/api/v1/forum/reports/bulk-status",
                json={"report_ids": ids, "status": "escalated"},
                headers=admin_headers,
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data["updated_ids"]) == 2


class TestReportsPagination:
    """Test GET /api/v1/forum/reports pagination."""

    def test_default_pagination(self, app, client, admin_headers, forum_setup):
        with app.app_context():
            resp = client.get("/api/v1/forum/reports", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.get_json()
            assert "total" in data
            assert "page" in data
            assert "limit" in data
            assert data["page"] == 1
            assert data["limit"] == 20
            assert data["total"] >= 5

    def test_custom_page_and_limit(self, app, client, admin_headers, forum_setup):
        resp = client.get("/api/v1/forum/reports?page=1&limit=2", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["limit"] == 2

    def test_page_2(self, app, client, admin_headers, forum_setup):
        resp = client.get("/api/v1/forum/reports?page=2&limit=2", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["items"]) == 2
        assert data["page"] == 2

    def test_limit_capped_at_100(self, app, client, admin_headers, forum_setup):
        resp = client.get("/api/v1/forum/reports?limit=200", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["limit"] == 100


class TestReportsTargetTypeFilter:
    """Test GET /api/v1/forum/reports target_type filter."""

    def test_filter_thread_reports(self, app, client, admin_headers, forum_setup):
        resp = client.get("/api/v1/forum/reports?target_type=thread", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        for item in data["items"]:
            assert item["target_type"] == "thread"
        # We created 3 thread reports (indices 0, 2, 4)
        assert data["total"] == 3

    def test_filter_post_reports(self, app, client, admin_headers, forum_setup):
        resp = client.get("/api/v1/forum/reports?target_type=post", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        for item in data["items"]:
            assert item["target_type"] == "post"
        # We created 2 post reports (indices 1, 3)
        assert data["total"] == 2

    def test_filter_with_status_and_target_type(self, app, client, admin_headers, forum_setup):
        resp = client.get(
            "/api/v1/forum/reports?status=open&target_type=thread",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 3


class TestModerationLog:
    """Test GET /api/v1/forum/moderation/log returns activity log entries."""

    def test_moderation_log_returns_entries(self, app, client, admin_headers, forum_setup):
        with app.app_context():
            # First do a moderation action to create a log entry
            report_id = forum_setup["reports"][0].id
            client.put(
                f"/api/v1/forum/reports/{report_id}",
                json={"status": "resolved"},
                headers=admin_headers,
            )

            # Now fetch the moderation log
            resp = client.get("/api/v1/forum/moderation/log", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.get_json()
            assert "items" in data
            assert "total" in data
            assert data["total"] >= 1
            # Check structure of first entry
            entry = data["items"][0]
            assert "actor_username_snapshot" in entry
            assert "action" in entry
            assert "target_type" in entry
            assert "created_at" in entry

    def test_moderation_log_pagination(self, app, client, admin_headers, forum_setup):
        resp = client.get(
            "/api/v1/forum/moderation/log?page=1&limit=5",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["page"] == 1
        assert data["limit"] == 5

    def test_moderation_log_forbidden_for_regular_user(self, app, client, auth_headers):
        resp = client.get("/api/v1/forum/moderation/log", headers=auth_headers)
        assert resp.status_code == 403

    def test_before_after_meta_in_log(self, app, client, admin_headers, forum_setup):
        """Verify that moderation actions store before/after state in meta."""
        with app.app_context():
            report_id = forum_setup["reports"][0].id
            client.put(
                f"/api/v1/forum/reports/{report_id}",
                json={"status": "resolved"},
                headers=admin_headers,
            )

            resp = client.get("/api/v1/forum/moderation/log?limit=1", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.get_json()
            assert len(data["items"]) >= 1
            entry = data["items"][0]
            meta = entry.get("metadata", {})
            assert "before" in meta
            assert "after" in meta
            assert meta["before"]["status"] == "open"
            assert meta["after"]["status"] == "resolved"
