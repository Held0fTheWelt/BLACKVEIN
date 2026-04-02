"""Tests for data export/import API (admin-only)."""
from __future__ import annotations

import json
import pytest

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


def test_data_export_rate_limit_allows_5_per_hour(client, admin_headers):
    """Test that export endpoint allows up to 5 requests per hour per user."""
    for i in range(5):
        resp = client.post("/api/v1/data/export", json={"scope": "full"}, headers=admin_headers)
        assert resp.status_code == 200, f"Export request {i + 1} should succeed, got {resp.status_code}"


def test_data_export_rate_limit_blocks_6th_request(client, admin_headers):
    """Test that export endpoint returns 429 on 6th request within hour (rate limit: 5/hour)."""
    for i in range(5):
        resp = client.post("/api/v1/data/export", json={"scope": "full"}, headers=admin_headers)
        assert resp.status_code == 200, f"Export request {i + 1} should succeed"

    # 6th request should be rate limited
    resp = client.post("/api/v1/data/export", json={"scope": "full"}, headers=admin_headers)
    assert resp.status_code == 429, f"6th export request should return 429, got {resp.status_code}"
    body = resp.get_json()
    assert "error" in body
    assert "too many requests" in body["error"].lower()


def test_data_import_execute_rate_limit_allows_1_per_hour(client, super_admin_headers):
    """Test that import execute endpoint allows 1 request per hour per user."""
    export_resp = client.post("/api/v1/data/export", json={"scope": "full"}, headers=super_admin_headers)
    assert export_resp.status_code == 200
    payload = export_resp.get_json()

    # First request should succeed (but validation may fail - we only care about rate limit)
    resp = client.post("/api/v1/data/import/execute", json=payload, headers=super_admin_headers)
    # 200 or 400 (validation error) is fine; we just care it's not 429
    assert resp.status_code in (200, 400), f"First import request should not be rate limited, got {resp.status_code}"


def test_data_import_execute_rate_limit_blocks_2nd_request(client, super_admin_headers):
    """Test that import execute endpoint returns 429 on 2nd request within hour (rate limit: 1/hour)."""
    export_resp = client.post("/api/v1/data/export", json={"scope": "full"}, headers=super_admin_headers)
    assert export_resp.status_code == 200
    payload = export_resp.get_json()

    # First request
    resp1 = client.post("/api/v1/data/import/execute", json=payload, headers=super_admin_headers)
    assert resp1.status_code in (200, 400), f"First import request should not be rate limited, got {resp1.status_code}"

    # 2nd request should be rate limited
    resp2 = client.post("/api/v1/data/import/execute", json=payload, headers=super_admin_headers)
    assert resp2.status_code == 429, f"2nd import request should return 429, got {resp2.status_code}"
    body = resp2.get_json()
    assert "error" in body
    assert "too many requests" in body["error"].lower()


def test_data_export_rate_limit_per_user(client, app, admin_headers, super_admin_headers):
    """Test that export rate limit is per-user (different users have independent limits)."""
    # Admin user exhausts their 5/hour limit
    for i in range(5):
        resp = client.post("/api/v1/data/export", json={"scope": "full"}, headers=admin_headers)
        assert resp.status_code == 200

    # Admin user's 6th request is blocked
    resp = client.post("/api/v1/data/export", json={"scope": "full"}, headers=admin_headers)
    assert resp.status_code == 429

    # Super-admin user can still make requests (independent limit)
    resp = client.post("/api/v1/data/export", json={"scope": "full"}, headers=super_admin_headers)
    assert resp.status_code == 200, f"Different user should have independent rate limit, got {resp.status_code}"


def test_data_export_invalid_scope_returns_400(client, admin_headers):
    resp = client.post("/api/v1/data/export", json={"scope": "invalid_scope"}, headers=admin_headers)
    assert resp.status_code == 400


def test_data_export_table_without_table_returns_400(client, admin_headers):
    resp = client.post("/api/v1/data/export", json={"scope": "table"}, headers=admin_headers)
    assert resp.status_code == 400


def test_data_export_rows_without_keys_returns_400(client, admin_headers):
    resp = client.post(
        "/api/v1/data/export",
        json={"scope": "rows", "table": "users"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_data_decrypt_without_password_returns_400(client, admin_headers):
    resp = client.post(
        "/api/v1/data/export/decrypt",
        json={"encrypted_data": "x", "iv": "y", "salt": "z"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_data_import_preflight_missing_json_returns_400(client, admin_headers):
    resp = client.post(
        "/api/v1/data/import/preflight",
        data="not-json",
        headers={**admin_headers, "Content-Type": "application/json"},
    )
    assert resp.status_code == 400


"""Tests for TestDataAPI."""

class TestDataAPI:

    def test_data_export(self, app, client, admin_headers):
        resp = client.post("/api/v1/data/export", json={"format": "json"}, headers=admin_headers)
        assert resp.status_code in (200, 400)

    def test_data_export_forbidden(self, app, client, auth_headers):
        resp = client.post("/api/v1/data/export", json={}, headers=auth_headers)
        assert resp.status_code in (403, 401)


# ======================= AUTH ROUTES =======================



"""Tests for TestDataExportImport."""

class TestDataExportImport:

    def test_export_full(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/data/export",
            json={"scope": "full"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_export_table(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/data/export",
            json={"scope": "table", "table": "users"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    def test_export_list_tables(self, app, client, admin_headers):
        resp = client.get("/api/v1/data/tables", headers=admin_headers)
        assert resp.status_code in (200, 404)

    def test_import_preflight(self, app, client, admin_headers):
        resp = client.post(
            "/api/v1/data/import/preflight",
            json={"metadata": {"format_version": 1}, "data": {"tables": {}}},
            headers=admin_headers,
        )
        assert resp.status_code in (200, 400)


# ======================= SLOGAN API EXTENDED =======================
