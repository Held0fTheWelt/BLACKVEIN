"""Tests for data export/import API (admin-only)."""
from __future__ import annotations

import json

from app.services.data_export_service import EXPORT_FORMAT_VERSION


def test_data_export_full_requires_auth(client):
    resp = client.post("/api/v1/data/export", json={"scope": "full"})
    assert resp.status_code == 401


def test_data_export_full_as_admin_returns_metadata(client, admin_headers):
    resp = client.post("/api/v1/data/export", json={"scope": "full"}, headers=admin_headers)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "metadata" in data and "data" in data
    md = data["metadata"]
    assert md["format_version"] == EXPORT_FORMAT_VERSION
    # In tests without Alembic version table this may be empty, but the key must exist.
    assert "schema_revision" in md
    assert md.get("exported_at")
    assert md.get("scope", {}).get("type") == "full"
    assert isinstance(md.get("tables"), list)


def test_data_export_table_unknown_table_returns_400(client, admin_headers):
    resp = client.post(
        "/api/v1/data/export",
        json={"scope": "table", "table": "does_not_exist"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert "error" in body


def test_data_import_preflight_rejects_missing_metadata(client, admin_headers):
    payload = {"foo": "bar"}
    resp = client.post("/api/v1/data/import/preflight", json=payload, headers=admin_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is False
    codes = {issue["code"] for issue in body["issues"]}
    assert "MISSING_METADATA" in codes or "INVALID_DATA_SECTION" in codes


def test_data_import_preflight_schema_mismatch_detected(client, admin_headers):
    # Take a real export and then tamper with schema_revision to simulate old payload.
    export_resp = client.post("/api/v1/data/export", json={"scope": "full"}, headers=admin_headers)
    assert export_resp.status_code == 200
    payload = export_resp.get_json()
    payload["metadata"]["schema_revision"] = "old_revision"

    resp = client.post("/api/v1/data/import/preflight", json=payload, headers=admin_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is False
    codes = {issue["code"] for issue in body["issues"]}
    assert "SCHEMA_MISMATCH" in codes


def test_data_import_execute_requires_superadmin(client, admin_headers):
    # Minimal invalid payload, we only care about 403 vs 401/200.
    payload = {"metadata": {"format_version": EXPORT_FORMAT_VERSION, "schema_revision": "x"}, "data": {"tables": {}}}
    resp = client.post("/api/v1/data/import/execute", json=payload, headers=admin_headers)
    assert resp.status_code == 403


def test_data_import_execute_detects_primary_key_conflict(client, super_admin_headers):
    # Export current DB and try to import back; preflight should report PK conflicts.
    export_resp = client.post("/api/v1/data/export", json={"scope": "full"}, headers=super_admin_headers)
    assert export_resp.status_code == 200
    payload = export_resp.get_json()

    pre_resp = client.post("/api/v1/data/import/preflight", json=payload, headers=super_admin_headers)
    assert pre_resp.status_code == 200
    pre_body = pre_resp.get_json()
    assert pre_body["ok"] is False
    codes = {issue["code"] for issue in pre_body["issues"]}
    assert "PRIMARY_KEY_CONFLICT" in codes

    exec_resp = client.post("/api/v1/data/import/execute", json=payload, headers=super_admin_headers)
    assert exec_resp.status_code == 400
    exec_body = exec_resp.get_json()
    assert exec_body["ok"] is False

