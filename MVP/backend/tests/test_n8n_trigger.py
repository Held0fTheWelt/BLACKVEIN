"""Tests for app.n8n_trigger."""

from __future__ import annotations

import pytest

from app.n8n_trigger import trigger_webhook, validate_secret


class _DummyResponse:
    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestN8nTrigger:
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
