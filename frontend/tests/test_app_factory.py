"""Tests for Flask app factory and global middleware."""
from __future__ import annotations

import pytest

from app import create_app
from app.config import TestingConfig


class MissingSecretConfig(TestingConfig):
    SECRET_KEY = None


def test_create_app_requires_secret_key():
    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app(MissingSecretConfig)


def test_404_returns_json_for_api_path():
    app = create_app(TestingConfig)
    client = app.test_client()
    r = client.get("/api/no-such-route")
    assert r.status_code == 404
    assert r.is_json
    assert r.get_json()["error"] == "Not found"


def test_404_returns_plain_text_elsewhere():
    app = create_app(TestingConfig)
    client = app.test_client()
    r = client.get("/this-route-does-not-exist-xyz")
    assert r.status_code == 404
    assert r.data == b"Not found"


def test_500_returns_json_for_api_path():
    app = create_app(TestingConfig)
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.route("/api/trigger-500")
    def boom_api():
        raise RuntimeError("fail")

    client = app.test_client()
    r = client.get("/api/trigger-500")
    assert r.status_code == 500
    assert r.is_json
    assert r.get_json()["error"] == "Internal server error"


def test_500_returns_plain_text_elsewhere():
    app = create_app(TestingConfig)
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.route("/trigger-500")
    def boom():
        raise RuntimeError("fail")

    client = app.test_client()
    r = client.get("/trigger-500")
    assert r.status_code == 500
    assert r.data == b"Internal server error"


def test_security_headers_on_response():
    app = create_app(TestingConfig)
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert "default-src 'self'" in (r.headers.get("Content-Security-Policy") or "")
