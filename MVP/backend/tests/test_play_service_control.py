"""Tests for Play-Service control API and service (application-level, no host orchestration)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest

from app.extensions import db
from app.models import SiteSetting
from app.services import play_service_control_service as psc
from app.services.play_service_control_service import STORAGE_KEY, _empty_document, run_test_persist


@pytest.fixture
def _httpx_ok(monkeypatch):
    class Resp:
        def __init__(self, status_code, body):
            self.status_code = status_code
            self.content = b"{}"
            self._body = body

        def json(self):
            return self._body

    class Client:
        def __init__(self, *a, **kw):
            self._kw = kw

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            u = str(url)
            if u.endswith("/api/health"):
                return Resp(200, {"status": "ok"})
            if u.endswith("/api/health/ready"):
                return Resp(200, {"status": "ready", "app": "t", "store": {}, "template_count": 0, "run_count": 0})
            return Resp(502, {"error": u})

    monkeypatch.setattr(psc.httpx, "Client", Client)


@pytest.fixture
def _httpx_timeout(monkeypatch):
    class Client:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            raise httpx.TimeoutException("timeout", request=MagicMock())

    monkeypatch.setattr(psc.httpx, "Client", Client)


def test_control_get_requires_auth(client):
    r = client.get("/api/v1/admin/play-service-control")
    assert r.status_code == 401


def test_control_get_forbidden_for_moderator(client, moderator_headers):
    r = client.get("/api/v1/admin/play-service-control", headers=moderator_headers)
    assert r.status_code == 403


def test_control_get_forbidden_admin_without_feature(client, admin_headers, monkeypatch):
    from app.auth import feature_registry as fr

    orig = fr.user_can_access_feature

    def wrapped(user, fid):
        if fid == fr.FEATURE_MANAGE_PLAY_SERVICE_CONTROL:
            return False
        return orig(user, fid)

    monkeypatch.setattr(fr, "user_can_access_feature", wrapped)
    r = client.get("/api/v1/admin/play-service-control", headers=admin_headers)
    assert r.status_code == 403


def test_control_get_payload_shape(client, admin_headers):
    r = client.get("/api/v1/admin/play-service-control", headers=admin_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert set(data.keys()) >= {
        "desired_state",
        "observed_state",
        "capabilities",
        "last_test_result",
        "last_apply_result",
        "generated_at",
    }
    obs = data["observed_state"]
    assert "effective_mode" in obs and "config_complete" in obs
    assert "shared_secret_present" in data["desired_state"]


def test_control_post_validation_disabled_mode(client, admin_headers):
    r = client.post(
        "/api/v1/admin/play-service-control",
        headers=admin_headers,
        json={
            "mode": "disabled",
            "enabled": True,
            "public_url": "",
            "internal_url": "",
            "request_timeout_ms": 30000,
            "allow_new_sessions": True,
        },
    )
    assert r.status_code == 400
    body = r.get_json()
    assert body["saved"] is False
    assert body["validation_errors"]


def test_control_post_save_disabled_ok(client, admin_headers):
    r = client.post(
        "/api/v1/admin/play-service-control",
        headers=admin_headers,
        json={
            "mode": "disabled",
            "enabled": False,
            "public_url": "",
            "internal_url": "",
            "request_timeout_ms": 30000,
            "allow_new_sessions": False,
        },
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["saved"] is True
    assert body["desired_state"]["mode"] == "disabled"


def test_control_post_rejects_bad_remote(client, admin_headers):
    r = client.post(
        "/api/v1/admin/play-service-control",
        headers=admin_headers,
        json={
            "mode": "remote",
            "enabled": True,
            "public_url": "not-a-url",
            "internal_url": "https://internal.example.com",
            "request_timeout_ms": 30000,
            "allow_new_sessions": True,
        },
    )
    assert r.status_code == 400


def test_apply_without_save(client, admin_headers):
    with client.application.app_context():
        doc = _empty_document()
        row = db.session.get(SiteSetting, STORAGE_KEY)
        if row is None:
            db.session.add(SiteSetting(key=STORAGE_KEY, value=json.dumps(doc)))
        else:
            row.value = json.dumps(doc)
        db.session.commit()
    r = client.post("/api/v1/admin/play-service-control/apply", headers=admin_headers, json={})
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is False
    assert "save before apply" in (data.get("result") or {}).get("message", "").lower()


def test_apply_updates_runtime_config(client, admin_headers, app):
    app.config["PLAY_SERVICE_SHARED_SECRET"] = "apply-test-secret-value"
    r_save = client.post(
        "/api/v1/admin/play-service-control",
        headers=admin_headers,
        json={
            "mode": "remote",
            "enabled": True,
            "public_url": "https://play.apply.test",
            "internal_url": "https://internal.apply.test",
            "request_timeout_ms": 8000,
            "allow_new_sessions": True,
        },
    )
    assert r_save.status_code == 200
    r_apply = client.post("/api/v1/admin/play-service-control/apply", headers=admin_headers, json={})
    assert r_apply.status_code == 200
    data = r_apply.get_json()
    assert data["ok"] is True
    with app.app_context():
        assert app.config["PLAY_SERVICE_PUBLIC_URL"] == "https://play.apply.test"
        assert app.config["PLAY_SERVICE_INTERNAL_URL"] == "https://internal.apply.test"
        assert app.config["PLAY_SERVICE_REQUEST_TIMEOUT"] == 8
        assert app.config["PLAY_SERVICE_CONTROL_DISABLED"] is False
    assert "apply-test-secret-value" not in r_apply.get_data(as_text=True)


def test_test_persist_does_not_change_play_urls(client, admin_headers, app, _httpx_ok):
    internal_before = app.config.get("PLAY_SERVICE_INTERNAL_URL")
    client.post(
        "/api/v1/admin/play-service-control",
        headers=admin_headers,
        json={
            "mode": "remote",
            "enabled": True,
            "public_url": "https://play.example.test",
            "internal_url": "https://internal.example.test",
            "request_timeout_ms": 30000,
            "allow_new_sessions": True,
        },
    )
    r = client.post("/api/v1/admin/play-service-control/test", headers=admin_headers, json={})
    assert r.status_code == 200
    assert r.get_json().get("ok") is True
    assert app.config.get("PLAY_SERVICE_INTERNAL_URL") == internal_before


def test_test_timeout_operator_message(client, admin_headers, app, _httpx_timeout):
    client.post(
        "/api/v1/admin/play-service-control",
        headers=admin_headers,
        json={
            "mode": "remote",
            "enabled": True,
            "public_url": "https://play.example.test",
            "internal_url": "https://internal.example.test",
            "request_timeout_ms": 30000,
            "allow_new_sessions": True,
        },
    )
    r = client.post("/api/v1/admin/play-service-control/test", headers=admin_headers, json={})
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] is False
    checks = (data.get("result") or {}).get("checks") or []
    assert any((c.get("detail") or {}).get("error") == "timeout" for c in checks if c.get("id") == "health")


def test_get_response_has_no_raw_secrets(client, admin_headers, app):
    app.config["PLAY_SERVICE_SHARED_SECRET"] = "ultra-secret-token-xyz"
    r = client.get("/api/v1/admin/play-service-control", headers=admin_headers)
    text = r.get_data(as_text=True)
    assert "ultra-secret-token-xyz" not in text


def test_run_test_persist_disabled_no_network(app):
    with app.app_context():
        doc = _empty_document()
        doc["desired"] = {
            "mode": "disabled",
            "enabled": False,
            "public_url": "",
            "internal_url": "",
            "request_timeout_ms": 30000,
            "allow_new_sessions": True,
            "updated_at": "t",
            "updated_by_user_id": 1,
        }
        row = db.session.get(SiteSetting, STORAGE_KEY)
        if row is None:
            db.session.add(SiteSetting(key=STORAGE_KEY, value=json.dumps(doc)))
        else:
            row.value = json.dumps(doc)
        db.session.commit()
        out = run_test_persist(app, user_id=1)
        assert out["ok"] is True
        assert out["result"]["checks"][0]["id"] == "disabled"
