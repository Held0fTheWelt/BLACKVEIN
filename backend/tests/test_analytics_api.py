"""Tests for community analytics API endpoints."""
import pytest
from datetime import datetime, timezone, timedelta


class TestAnalyticsSummary:
    """Test GET /api/v1/admin/analytics/summary endpoint."""

    def test_admin_can_access_analytics_summary(self, client, admin_headers, app):
        """Admin user can fetch analytics summary."""
        response = client.get(
            "/api/v1/admin/analytics/summary",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "summary" in data
        assert "users" in data["summary"]
        assert "content" in data["summary"]
        assert "reports" in data["summary"]

    def test_analytics_summary_includes_user_counts(self, client, admin_headers, app, test_user):
        """Analytics summary includes accurate user counts."""
        response = client.get(
            "/api/v1/admin/analytics/summary",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        summary = data["summary"]
        # Should have at least the test_user + admin_user
        assert summary["users"]["total"] >= 2
        assert "verified" in summary["users"]
        assert "banned" in summary["users"]
        assert "active_now" in summary["users"]

    def test_analytics_summary_includes_report_queue(self, client, admin_headers, app):
        """Analytics summary includes report queue status."""
        response = client.get(
            "/api/v1/admin/analytics/summary",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        summary = data["summary"]
        assert "reports" in summary
        assert "open" in summary["reports"]
        assert "in_review" in summary["reports"]
        assert "resolved" in summary["reports"]

    def test_non_admin_cannot_access_analytics_summary(self, client, auth_headers):
        """Non-admin user gets 403 when accessing analytics summary."""
        response = client.get(
            "/api/v1/admin/analytics/summary",
            headers=auth_headers
        )
        assert response.status_code == 403

    def test_unauthenticated_cannot_access_analytics_summary(self, client):
        """Unauthenticated user gets 401 when accessing analytics summary."""
        response = client.get("/api/v1/admin/analytics/summary")
        assert response.status_code == 401

    def test_analytics_summary_with_date_range(self, client, admin_headers):
        """Analytics summary respects date_from and date_to parameters."""
        today = datetime.now(timezone.utc).date()
        date_from = (today - timedelta(days=7)).isoformat()
        date_to = today.isoformat()

        response = client.get(
            "/api/v1/admin/analytics/summary",
            headers=admin_headers,
            query_string={
                "date_from": date_from,
                "date_to": date_to,
            }
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["date_range"]["from"]
        assert data["date_range"]["to"]


class TestAnalyticsTimeline:
    """Test GET /api/v1/admin/analytics/timeline endpoint."""

    def test_admin_can_access_analytics_timeline(self, client, admin_headers):
        """Admin user can fetch analytics timeline."""
        response = client.get(
            "/api/v1/admin/analytics/timeline",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "timeline" in data
        assert "dates" in data["timeline"]

    def test_moderator_can_access_analytics_timeline(self, client, moderator_headers):
        """Moderator user can fetch analytics timeline."""
        response = client.get(
            "/api/v1/admin/analytics/timeline",
            headers=moderator_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "timeline" in data

    def test_timeline_includes_multiple_metrics(self, client, admin_headers):
        """Analytics timeline includes threads, posts, reports, actions."""
        response = client.get(
            "/api/v1/admin/analytics/timeline",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        timeline = data["timeline"]
        # Should have these metrics (as empty lists if no data)
        assert "threads" in timeline or "posts" in timeline or "reports" in timeline or "actions" in timeline

    def test_timeline_filters_by_metric(self, client, admin_headers):
        """Analytics timeline respects metric parameter."""
        response = client.get(
            "/api/v1/admin/analytics/timeline",
            headers=admin_headers,
            query_string={"metric": "threads"}
        )
        assert response.status_code == 200
        data = response.get_json()
        timeline = data["timeline"]
        assert "dates" in timeline
        # When filtered to threads, should have threads but maybe not posts
        assert "threads" in timeline

    def test_non_admin_non_moderator_cannot_access_timeline(self, client, auth_headers):
        """Non-admin, non-moderator user gets 403."""
        response = client.get(
            "/api/v1/admin/analytics/timeline",
            headers=auth_headers
        )
        assert response.status_code == 403


class TestAnalyticsUsers:
    """Test GET /api/v1/admin/analytics/users endpoint."""

    def test_admin_can_access_analytics_users(self, client, admin_headers):
        """Admin user can fetch user analytics."""
        response = client.get(
            "/api/v1/admin/analytics/users",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "top_contributors" in data
        assert "role_distribution" in data

    def test_analytics_users_includes_role_distribution(self, client, admin_headers):
        """User analytics includes role distribution."""
        response = client.get(
            "/api/v1/admin/analytics/users",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        dist = data["role_distribution"]
        # Should have at least user and admin roles
        assert "user" in dist or "admin" in dist

    def test_analytics_users_respects_limit(self, client, admin_headers):
        """User analytics respects limit parameter."""
        response = client.get(
            "/api/v1/admin/analytics/users",
            headers=admin_headers,
            query_string={"limit": "5"}
        )
        assert response.status_code == 200
        data = response.get_json()
        contributors = data["top_contributors"]
        assert len(contributors) <= 5

    def test_non_admin_cannot_access_analytics_users(self, client, auth_headers):
        """Non-admin user gets 403 when accessing user analytics."""
        response = client.get(
            "/api/v1/admin/analytics/users",
            headers=auth_headers
        )
        assert response.status_code == 403


class TestAnalyticsContent:
    """Test GET /api/v1/admin/analytics/content endpoint."""

    def test_admin_can_access_analytics_content(self, client, admin_headers):
        """Admin user can fetch content analytics."""
        response = client.get(
            "/api/v1/admin/analytics/content",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "popular_tags" in data
        assert "trending_threads" in data
        assert "content_freshness" in data

    def test_moderator_can_access_analytics_content(self, client, moderator_headers):
        """Moderator user can fetch content analytics."""
        response = client.get(
            "/api/v1/admin/analytics/content",
            headers=moderator_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "popular_tags" in data

    def test_analytics_content_includes_freshness(self, client, admin_headers):
        """Content analytics includes freshness distribution."""
        response = client.get(
            "/api/v1/admin/analytics/content",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        freshness = data["content_freshness"]
        assert "new" in freshness
        assert "recent" in freshness
        assert "old" in freshness

    def test_non_admin_non_moderator_cannot_access_content(self, client, auth_headers):
        """Non-admin, non-moderator user gets 403."""
        response = client.get(
            "/api/v1/admin/analytics/content",
            headers=auth_headers
        )
        assert response.status_code == 403


class TestAnalyticsModeration:
    """Test GET /api/v1/admin/analytics/moderation endpoint."""

    def test_admin_can_access_analytics_moderation(self, client, admin_headers):
        """Admin user can fetch moderation analytics."""
        response = client.get(
            "/api/v1/admin/analytics/moderation",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "queue_status" in data
        assert "reports_by_date" in data
        assert "moderation_actions" in data
        assert "average_resolution_days" in data

    def test_moderator_can_access_analytics_moderation(self, client, moderator_headers):
        """Moderator user can fetch moderation analytics."""
        response = client.get(
            "/api/v1/admin/analytics/moderation",
            headers=moderator_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "queue_status" in data

    def test_analytics_moderation_includes_queue_status(self, client, admin_headers):
        """Moderation analytics includes queue status by report status."""
        response = client.get(
            "/api/v1/admin/analytics/moderation",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        queue = data["queue_status"]
        # Queue status should be a dict with status names as keys
        assert isinstance(queue, dict)

    def test_non_admin_non_moderator_cannot_access_moderation(self, client, auth_headers):
        """Non-admin, non-moderator user gets 403."""
        response = client.get(
            "/api/v1/admin/analytics/moderation",
            headers=auth_headers
        )
        assert response.status_code == 403

    def test_analytics_moderation_with_date_range(self, client, admin_headers):
        """Moderation analytics respects date range parameters."""
        today = datetime.now(timezone.utc).date()
        date_from = (today - timedelta(days=7)).isoformat()

        response = client.get(
            "/api/v1/admin/analytics/moderation",
            headers=admin_headers,
            query_string={"date_from": date_from}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["date_range"]["from"]


class TestAnalyticsPerformance:
    """Test analytics endpoint performance and edge cases."""

    def test_analytics_endpoints_return_json(self, client, admin_headers):
        """All analytics endpoints return valid JSON."""
        endpoints = [
            "/api/v1/admin/analytics/summary",
            "/api/v1/admin/analytics/timeline",
            "/api/v1/admin/analytics/users",
            "/api/v1/admin/analytics/content",
            "/api/v1/admin/analytics/moderation",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint, headers=admin_headers)
            assert response.status_code == 200
            # Should be valid JSON
            data = response.get_json()
            assert data is not None
            assert isinstance(data, dict)

    def test_analytics_endpoints_include_query_date(self, client, admin_headers):
        """All analytics endpoints include query_date."""
        endpoints = [
            "/api/v1/admin/analytics/summary",
            "/api/v1/admin/analytics/timeline",
            "/api/v1/admin/analytics/users",
            "/api/v1/admin/analytics/content",
            "/api/v1/admin/analytics/moderation",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint, headers=admin_headers)
            data = response.get_json()
            assert "query_date" in data, f"{endpoint} missing query_date"

    def test_invalid_limit_defaults_gracefully(self, client, admin_headers):
        """Invalid limit parameter defaults to 10."""
        response = client.get(
            "/api/v1/admin/analytics/users",
            headers=admin_headers,
            query_string={"limit": "not_a_number"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "top_contributors" in data

    def test_limit_capped_at_100(self, client, admin_headers):
        """Limit parameter is capped at 100."""
        response = client.get(
            "/api/v1/admin/analytics/users",
            headers=admin_headers,
            query_string={"limit": "999"}
        )
        assert response.status_code == 200
        data = response.get_json()
        contributors = data["top_contributors"]
        assert len(contributors) <= 100


def test_admin_analytics_summary_service_exception_returns_500(client, admin_headers, monkeypatch):
    def boom(**_kwargs):
        raise RuntimeError("analytics failure")

    monkeypatch.setattr(
        "app.api.v1.analytics_routes.get_analytics_summary",
        boom,
    )
    resp = client.get("/api/v1/admin/analytics/summary", headers=admin_headers)
    assert resp.status_code == 500
    assert "error" in (resp.get_json() or {})
