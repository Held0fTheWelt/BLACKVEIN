"""Tests for GET /api/v1/admin/system-diagnosis and system_diagnosis_service."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import httpx
import pytest

from app.services.system_diagnosis_service import (
    _resolve_overall,
    get_system_diagnosis,
    reset_diagnosis_cache_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_diagnosis_cache():
    reset_diagnosis_cache_for_tests()
    yield
    reset_diagnosis_cache_for_tests()


def _install_diagnosis_httpx_mock(monkeypatch, *, backend_ok=True, play_timeout=False, play_health_status=200):
    """Patch httpx.Client in system_diagnosis_service for backend + play HTTP checks."""

    import app.services.system_diagnosis_service as mod

    class Resp:
        def __init__(self, status_code, body):
            self.status_code = status_code
            self.content = b"{}"
            self._body = body

        def json(self):
            return self._body

    class Client:
        def __init__(self, *a, **kw):
            self._base = kw.get("base_url")

        def __enter__(self):
            return self

        def __exit__(self, *a, **k):
            return False

        def get(self, url):
            u = str(url)
            if not backend_ok and "api/v1/health" in u:
                return Resp(503, {"status": "error"})
            if "api/v1/health" in u:
                return Resp(200, {"status": "ok"})
            if play_timeout and self._base:
                raise httpx.TimeoutException("timeout", request=MagicMock())
            if self._base and u.endswith("/api/health"):
                return Resp(play_health_status, {"status": "ok"} if play_health_status == 200 else {})
            if self._base and u.endswith("/api/health/ready"):
                return Resp(
                    200,
                    {
                        "status": "ready",
                        "app": "t",
                        "store": {"backend": "x"},
                        "template_count": 0,
                        "run_count": 0,
                    },
                )
            return Resp(502, {"error": "unexpected", "url": u})

    monkeypatch.setattr(mod.httpx, "Client", Client)


def _install_ai_report_mock(monkeypatch, overall="partial"):
    import app.services.system_diagnosis_service as mod

    def _fast_report(*, trace_id: str):
        return {"overall_status": overall, "trace_id": trace_id}

    monkeypatch.setattr(mod, "build_release_readiness_report", _fast_report)


def test_resolve_overall_fail_if_critical_fail():
    checks = [
        {"id": "a", "status": "running", "critical": True},
        {"id": "b", "status": "fail", "critical": True},
        {"id": "c", "status": "initialized", "critical": False},
    ]
    assert _resolve_overall(checks) == "fail"


def test_resolve_overall_initialized_non_critical_fail():
    checks = [
        {"id": "a", "status": "running", "critical": True},
        {"id": "b", "status": "fail", "critical": False},
    ]
    assert _resolve_overall(checks) == "initialized"


def test_resolve_overall_initialized_any_yellow():
    checks = [
        {"id": "a", "status": "running", "critical": True},
        {"id": "b", "status": "initialized", "critical": False},
    ]
    assert _resolve_overall(checks) == "initialized"


def test_resolve_overall_running_all_green():
    checks = [
        {"id": "a", "status": "running", "critical": True},
        {"id": "b", "status": "running", "critical": False},
    ]
    assert _resolve_overall(checks) == "running"


def test_diagnosis_requires_auth(client):
    r = client.get("/api/v1/admin/system-diagnosis")
    assert r.status_code == 401


def test_diagnosis_forbidden_without_feature(client, moderator_headers, monkeypatch):
    from app.auth import feature_registry as fr

    def deny(user, fid):
        if fid == fr.FEATURE_MANAGE_SYSTEM_DIAGNOSIS:
            return False
        return True

    monkeypatch.setattr(fr, "user_can_access_feature", deny)
    r = client.get("/api/v1/admin/system-diagnosis", headers=moderator_headers)
    assert r.status_code == 403


def test_diagnosis_payload_shape(client, app, moderator_headers, monkeypatch):
    _install_diagnosis_httpx_mock(monkeypatch)
    _install_ai_report_mock(monkeypatch, overall="ready")
    r = client.get("/api/v1/admin/system-diagnosis", headers=moderator_headers, base_url="http://localhost")
    assert r.status_code == 200
    data = r.get_json()
    assert "generated_at" in data
    assert data["overall_status"] in ("fail", "initialized", "running")
    assert "summary" in data and set(data["summary"].keys()) >= {"running", "initialized", "fail"}
    assert "groups" in data and len(data["groups"]) >= 1
    assert "cached" in data
    flat = []
    for g in data["groups"]:
        for c in g["checks"]:
            flat.append(c)
            assert c["id"]
            assert c["label"]
            assert c["status"] in ("fail", "initialized", "running")
            assert "message" in c
    ids = {c["id"] for c in flat}
    assert "backend_api" in ids
    assert "database" in ids
    assert "play_service_configuration" in ids


def test_diagnosis_cache_hit(client, app, moderator_headers, monkeypatch):
    _install_diagnosis_httpx_mock(monkeypatch)
    _install_ai_report_mock(monkeypatch)
    r1 = client.get("/api/v1/admin/system-diagnosis", headers=moderator_headers, base_url="http://localhost")
    assert r1.status_code == 200
    g1 = r1.get_json()["generated_at"]
    r2 = client.get("/api/v1/admin/system-diagnosis", headers=moderator_headers, base_url="http://localhost")
    assert r2.status_code == 200
    data2 = r2.get_json()
    assert data2.get("cached") is True
    assert data2["generated_at"] == g1
    assert data2.get("cache", {}).get("hit") is True


def test_diagnosis_refresh_bypasses_cache(client, moderator_headers, monkeypatch):
    _install_diagnosis_httpx_mock(monkeypatch)
    _install_ai_report_mock(monkeypatch)
    r1 = client.get("/api/v1/admin/system-diagnosis", headers=moderator_headers, base_url="http://localhost")
    assert r1.status_code == 200
    time.sleep(0.01)
    r2 = client.get(
        "/api/v1/admin/system-diagnosis?refresh=1",
        headers=moderator_headers,
        base_url="http://localhost",
    )
    assert r2.status_code == 200
    assert r2.get_json().get("cached") is False


def test_diagnosis_play_health_timeout_fails_critical(client, moderator_headers, monkeypatch):
    _install_diagnosis_httpx_mock(monkeypatch, play_timeout=True)
    _install_ai_report_mock(monkeypatch)
    r = client.get("/api/v1/admin/system-diagnosis", headers=moderator_headers, base_url="http://localhost")
    assert r.status_code == 200
    data = r.get_json()
    assert data["overall_status"] == "fail"
    flat = [c for g in data["groups"] for c in g["checks"]]
    ph = next(x for x in flat if x["id"] == "play_service_health")
    assert ph["status"] == "fail"
    assert ph["timed_out"] is True
    assert "timeout" in ph["message"].lower()


def test_diagnosis_play_config_missing_overall_fail(app, monkeypatch):
    import app.services.system_diagnosis_service as mod

    monkeypatch.setattr(mod, "has_complete_play_service_config", lambda: False)
    _install_diagnosis_httpx_mock(monkeypatch)
    _install_ai_report_mock(monkeypatch)

    with app.app_context():
        payload = get_system_diagnosis(app, self_base_url="http://localhost", refresh=True, trace_id="t1")
    assert payload["overall_status"] == "fail"
    cfg = next(c for g in payload["groups"] for c in g["checks"] if c["id"] == "play_service_configuration")
    assert cfg["status"] == "fail"


def test_get_system_diagnosis_service_cache(app, monkeypatch):
    _install_diagnosis_httpx_mock(monkeypatch)
    _install_ai_report_mock(monkeypatch)
    with app.app_context():
        a = get_system_diagnosis(app, self_base_url="http://localhost", refresh=False, trace_id="t")
        b = get_system_diagnosis(app, self_base_url="http://localhost", refresh=False, trace_id="t")
    assert a["cached"] is False
    assert b["cached"] is True
    assert b["stale_seconds"] >= 0


def test_diagnosis_backend_fail_when_health_bad(client, moderator_headers, monkeypatch):
    _install_diagnosis_httpx_mock(monkeypatch, backend_ok=False)
    _install_ai_report_mock(monkeypatch)
    r = client.get("/api/v1/admin/system-diagnosis", headers=moderator_headers, base_url="http://localhost")
    assert r.status_code == 200
    assert r.get_json()["overall_status"] == "fail"
