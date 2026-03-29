from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Role, User
from app.n8n_trigger import trigger_webhook, validate_secret
from app.services.metrics_service import get_metrics


class _DummyResponse:
    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestMetricsServiceAdditionalCoverage:
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


class TestN8nTriggerAdditionalCoverage:
    @pytest.mark.parametrize(
        ("secret", "expected"),
        [
            ("1234567890abcdef", True),
            ("short", False),
            ("x" * 65, False),
            (None, False),
        ],
    )
    def test_validate_secret_contract(self, secret, expected):
        assert validate_secret(secret) is expected

    def test_trigger_webhook_returns_false_when_url_missing(self, app):
        with app.app_context():
            app.config["N8N_WEBHOOK_URL"] = ""
            assert trigger_webhook("story.updated", {"run_id": "abc"}) is False

    def test_trigger_webhook_signs_and_posts_payload(self, app, monkeypatch):
        captured = {}

        def fake_urlopen(request, timeout=10):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = request.data
            captured["timeout"] = timeout
            return _DummyResponse(status=202)

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

        with app.app_context():
            app.config["N8N_WEBHOOK_URL"] = "https://n8n.example/webhook"
            app.config["N8N_WEBHOOK_SECRET"] = "1234567890abcdef"

            ok = trigger_webhook("story.updated", {"run_id": "run-1", "beat": "courtesy"})

        assert ok is True
        assert captured["url"] == "https://n8n.example/webhook"
        assert captured["timeout"] == 10
        assert ("X-webhook-signature" in captured["headers"] or "X-Webhook-Signature" in captured["headers"])
        assert b'"event": "story.updated"' in captured["body"]
        assert b'"run_id": "run-1"' in captured["body"]

    def test_trigger_webhook_returns_false_on_transport_error(self, app, monkeypatch):
        def boom(request, timeout=10):
            raise OSError("network down")

        monkeypatch.setattr("urllib.request.urlopen", boom)

        with app.app_context():
            app.config["N8N_WEBHOOK_URL"] = "https://n8n.example/webhook"
            app.config["N8N_WEBHOOK_SECRET"] = "1234567890abcdef"
            assert trigger_webhook("story.updated", {"run_id": "run-1"}) is False
