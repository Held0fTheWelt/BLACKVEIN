"""MCP operations cockpit: ingest, admin APIs, diagnostic rules."""

from __future__ import annotations

import json
import time
import uuid

import pytest

from app.extensions import db
from app.models.mcp_diagnostic_case import McpDiagnosticCase
from app.models.mcp_ops_telemetry import McpOpsTelemetry
from app.services.mcp_operations_service import ingest_telemetry_batch


def _auth_service(client, monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "svc-test-token")
    return {"Authorization": "Bearer svc-test-token"}


def test_telemetry_ingest_requires_token(client, monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "x")
    r = client.post(
        "/api/v1/operator/mcp-telemetry/ingest",
        data=json.dumps({"records": []}),
        content_type="application/json",
    )
    assert r.status_code == 401


def test_telemetry_ingest_accepts_batch(client, monkeypatch, app):
    h = _auth_service(client, monkeypatch)
    trace = str(uuid.uuid4())
    recs = [
        {
            "type": "request",
            "trace_id": trace,
            "timestamp": time.time(),
            "method": "tools/call",
            "params_keys": ["name", "arguments"],
            "wos_mcp_suite": "all",
        },
        {
            "type": "response",
            "trace_id": trace,
            "timestamp": time.time(),
            "method": "tools/call",
            "status": "success",
            "duration_ms": 12.3,
            "wos_mcp_suite": "all",
        },
        {
            "type": "tool_call",
            "trace_id": trace,
            "timestamp": time.time(),
            "tool_name": "wos.system.health",
            "status": "success",
            "duration_ms": 5.0,
            "wos_mcp_suite": "all",
        },
    ]
    r = client.post(
        "/api/v1/operator/mcp-telemetry/ingest",
        data=json.dumps({"records": recs}),
        content_type="application/json",
        headers=h,
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["accepted"] == 3
    with app.app_context():
        assert McpOpsTelemetry.query.filter_by(trace_id=trace).count() == 3


def test_admin_mcp_overview_forbidden_without_jwt(client):
    r = client.get("/api/v1/admin/mcp/overview")
    assert r.status_code == 401


def test_admin_mcp_overview_ok_moderator(client, monkeypatch, moderator_headers):
    r = client.get("/api/v1/admin/mcp/overview", headers=moderator_headers)
    assert r.status_code == 200
    data = r.get_json()
    assert "suites" in data
    assert len(data["suites"]) >= 5
    assert data["open_diagnostic_cases"] >= 0


def test_activity_projection_tool_calls_only(client, monkeypatch, moderator_headers, app):
    h = _auth_service(client, monkeypatch)
    trace = str(uuid.uuid4())
    ingest_telemetry_batch(
        [
            {
                "type": "request",
                "trace_id": trace,
                "timestamp": time.time(),
                "method": "tools/call",
                "params_keys": [],
                "wos_mcp_suite": "wos-admin",
            },
            {
                "type": "tool_call",
                "trace_id": trace,
                "timestamp": time.time(),
                "tool_name": "wos.system.health",
                "status": "success",
                "duration_ms": 1.0,
                "wos_mcp_suite": "wos-admin",
            },
        ]
    )
    with app.app_context():
        db.session.commit()
    r = client.get("/api/v1/admin/mcp/activity?limit=50", headers=moderator_headers)
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert any(i.get("correlation_id") == trace for i in items)


def test_auto_case_failed_tool_call(client, monkeypatch, moderator_headers, app):
    h = _auth_service(client, monkeypatch)
    trace = str(uuid.uuid4())
    client.post(
        "/api/v1/operator/mcp-telemetry/ingest",
        data=json.dumps(
            {
                "records": [
                    {
                        "type": "tool_call",
                        "trace_id": trace,
                        "timestamp": time.time(),
                        "tool_name": "wos.system.health",
                        "status": "error",
                        "duration_ms": 2.0,
                        "error_code": "TOOL_ERROR",
                        "wos_mcp_suite": "wos-admin",
                    }
                ]
            }
        ),
        content_type="application/json",
        headers=h,
    )
    with app.app_context():
        c = McpDiagnosticCase.query.filter_by(case_type="failed_tool_call").first()
        assert c is not None
        assert c.trace_id == trace


def test_auto_case_policy_rejection(client, monkeypatch, moderator_headers, app):
    h = _auth_service(client, monkeypatch)
    trace = str(uuid.uuid4())
    client.post(
        "/api/v1/operator/mcp-telemetry/ingest",
        data=json.dumps(
            {
                "records": [
                    {
                        "type": "response",
                        "trace_id": trace,
                        "timestamp": time.time(),
                        "method": "tools/call",
                        "status": "error",
                        "duration_ms": 1.0,
                        "error_code": "PERMISSION_DENIED",
                        "wos_mcp_suite": "wos-runtime-control",
                    }
                ]
            }
        ),
        content_type="application/json",
        headers=h,
    )
    with app.app_context():
        c = McpDiagnosticCase.query.filter_by(case_type="policy_rejection").first()
        assert c is not None


def test_logs_distinct_from_activity_count(client, monkeypatch, moderator_headers, app):
    h = _auth_service(client, monkeypatch)
    trace = str(uuid.uuid4())
    client.post(
        "/api/v1/operator/mcp-telemetry/ingest",
        data=json.dumps(
            {
                "records": [
                    {
                        "type": "request",
                        "trace_id": trace,
                        "timestamp": time.time(),
                        "method": "initialize",
                        "params_keys": [],
                        "wos_mcp_suite": "all",
                    },
                    {
                        "type": "tool_call",
                        "trace_id": trace,
                        "timestamp": time.time(),
                        "tool_name": "wos.goc.list_modules",
                        "status": "success",
                        "duration_ms": 3.0,
                        "wos_mcp_suite": "all",
                    },
                ]
            }
        ),
        content_type="application/json",
        headers=h,
    )
    act = client.get("/api/v1/admin/mcp/activity", headers=moderator_headers).get_json()
    logs = client.get("/api/v1/admin/mcp/logs", headers=moderator_headers).get_json()
    assert logs["total"] >= act["total"]


def test_action_refresh_catalog(client, moderator_headers):
    r = client.post("/api/v1/admin/mcp/actions/refresh-catalog", headers=moderator_headers, json={})
    assert r.status_code == 200
    data = r.get_json()
    assert "catalog_alignment" in data
    assert "operator_truth" in data


def test_reclassify_diagnostic(client, monkeypatch, moderator_headers, app):
    h = _auth_service(client, monkeypatch)
    trace = str(uuid.uuid4())
    client.post(
        "/api/v1/operator/mcp-telemetry/ingest",
        data=json.dumps(
            {
                "records": [
                    {
                        "type": "tool_call",
                        "trace_id": trace,
                        "timestamp": time.time(),
                        "tool_name": "wos.system.health",
                        "status": "error",
                        "duration_ms": 1.0,
                        "error_code": "TOOL_ERROR",
                        "wos_mcp_suite": "all",
                    }
                ]
            }
        ),
        content_type="application/json",
        headers=h,
    )
    with app.app_context():
        c = McpDiagnosticCase.query.filter_by(case_type="failed_tool_call").first()
        pid = c.public_id
    r = client.post(
        "/api/v1/admin/mcp/actions/reclassify-diagnostic",
        headers=moderator_headers,
        json={"case_id": pid, "suite_display_override": "wos-admin", "status": "acknowledged"},
    )
    assert r.status_code == 200
    assert r.get_json()["suite_display"] == "wos-admin"


def test_seed_many_events_for_realistic_activity(client, monkeypatch, moderator_headers):
    """≥20 tool_call rows for roadmap-style activity volume (synthetic ingest)."""
    h = _auth_service(client, monkeypatch)
    recs = []
    for i in range(22):
        trace = str(uuid.uuid4())
        recs.append(
            {
                "type": "tool_call",
                "trace_id": trace,
                "timestamp": time.time(),
                "tool_name": "wos.system.health",
                "status": "success",
                "duration_ms": float(i),
                "wos_mcp_suite": "wos-admin",
            }
        )
    r = client.post(
        "/api/v1/operator/mcp-telemetry/ingest",
        data=json.dumps({"records": recs}),
        content_type="application/json",
        headers=h,
    )
    assert r.status_code == 200
    r2 = client.get("/api/v1/admin/mcp/activity?limit=100", headers=moderator_headers)
    assert r2.get_json()["total"] >= 22
