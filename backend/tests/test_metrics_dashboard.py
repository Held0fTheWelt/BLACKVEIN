"""Tests for real dashboard metrics API (admin JWT)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Role, User
from app.services.metrics_service import get_metrics


def test_dashboard_metrics_anonymous_returns_401(client):
    """GET /api/v1/admin/metrics without JWT returns 401."""
    r = client.get("/api/v1/admin/metrics", follow_redirects=False)
    assert r.status_code == 401


def test_dashboard_metrics_admin_returns_real_data(client, admin_headers):
    """GET /api/v1/admin/metrics as admin returns real user metrics (no fake revenue)."""
    r = client.get("/api/v1/admin/metrics?range=24h", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert "active_now" in data
    assert "registered_total" in data
    assert "verified_total" in data
    assert "banned_total" in data
    assert "active_users_over_time" in data
    assert "user_growth_over_time" in data
    assert "bucket_labels" in data
    assert "revenue" not in data
    assert "conversion" not in data
    assert isinstance(data["active_users_over_time"], list)
    assert isinstance(data["user_growth_over_time"], list)
    assert len(data["bucket_labels"]) == len(data["active_users_over_time"])


def test_dashboard_metrics_range_7d(client, admin_headers):
    """GET /api/v1/admin/metrics?range=7d returns 7 buckets."""
    r = client.get("/api/v1/admin/metrics?range=7d", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("selected_range") == "7d"
    assert len(data.get("bucket_labels", [])) == 7


def test_dashboard_metrics_range_30d(client, admin_headers):
    """GET /api/v1/admin/metrics?range=30d returns 30 buckets."""
    r = client.get("/api/v1/admin/metrics?range=30d", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("selected_range") == "30d"
    assert len(data.get("bucket_labels", [])) == 30


def test_dashboard_metrics_invalid_range_defaults_to_24h(client, admin_headers):
    """Unknown range query maps to 24h in get_metrics."""
    r = client.get("/api/v1/admin/metrics?range=__invalid__", headers=admin_headers)
    assert r.status_code == 200
    assert r.get_json().get("selected_range") == "24h"


class TestMetricsServiceAggregates:
    def test_get_metrics_aggregates_real_user_counts(self, app, monkeypatch):
        fixed_now = datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)
        monkeypatch.setattr("app.services.metrics_service._utc_now", lambda: fixed_now)

        with app.app_context():
            user_role = Role.query.filter_by(name=Role.NAME_USER).first()
            users = [
                User(
                    username="metrics_active_verified",
                    email="active@example.com",
                    password_hash=generate_password_hash("Secret123"),
                    role_id=user_role.id,
                    email_verified_at=fixed_now - timedelta(days=1),
                    created_at=fixed_now - timedelta(hours=2),
                    last_seen_at=fixed_now - timedelta(minutes=5),
                    is_banned=False,
                ),
                User(
                    username="metrics_banned_recent",
                    email="banned@example.com",
                    password_hash=generate_password_hash("Secret123"),
                    role_id=user_role.id,
                    created_at=fixed_now - timedelta(hours=6),
                    last_seen_at=fixed_now - timedelta(hours=1),
                    is_banned=True,
                ),
                User(
                    username="metrics_old",
                    email="old@example.com",
                    password_hash=generate_password_hash("Secret123"),
                    role_id=user_role.id,
                    created_at=fixed_now - timedelta(days=2),
                    last_seen_at=fixed_now - timedelta(days=2),
                    is_banned=False,
                ),
            ]
            db.session.add_all(users)
            db.session.commit()

            metrics = get_metrics("24h")
            fallback_metrics = get_metrics("not-a-range")

            assert metrics["active_now"] == 1
            assert metrics["registered_total"] == 3
            assert metrics["verified_total"] == 1
            assert metrics["banned_total"] == 1
            assert metrics["selected_range"] == "24h"
            assert metrics["bucket_info"]["bucket_count"] == 24
            assert len(metrics["bucket_labels"]) == 24
            assert len(metrics["active_users_over_time"]) == 24
            assert len(metrics["user_growth_over_time"]) == 24
            assert max(metrics["active_users_over_time"]) >= 1
            assert fallback_metrics["selected_range"] == "24h"

    def test_get_metrics_12m_monthly_bucket_labels(self, app, monkeypatch):
        """12m range uses _range_end_and_buckets branch and %Y-%m labels."""
        fixed_now = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
        monkeypatch.setattr("app.services.metrics_service._utc_now", lambda: fixed_now)
        with app.app_context():
            metrics = get_metrics("12m")
        assert metrics["selected_range"] == "12m"
        assert metrics["bucket_info"]["bucket_count"] == 12
        assert len(metrics["bucket_labels"]) == 12
        # Month-style labels (not HH:MM or YYYY-MM-DD)
        assert all(len(lbl) == 7 and lbl[4] == "-" for lbl in metrics["bucket_labels"])
