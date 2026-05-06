"""Tests for Hugging Face Hub token governance (encrypted store + internal API)."""

from __future__ import annotations

import pytest


def test_hf_hub_status_default(client, admin_jwt):
    resp = client.get(
        "/api/v1/admin/ai/hf-hub/status",
        headers={"Authorization": f"Bearer {admin_jwt}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    data = body["data"]
    assert data["credential_configured"] is False
    assert data["service_id"] == "huggingface_hub"


def test_hf_hub_write_internal_get_roundtrip(app, client, admin_jwt):
    token = "hf_integration_test_dummy_token_value"
    w = client.post(
        "/api/v1/admin/ai/hf-hub/credential",
        json={"token": token},
        headers={"Authorization": f"Bearer {admin_jwt}"},
    )
    assert w.status_code == 200
    wf = w.get_json()
    assert wf["ok"] is True
    assert "hub_token" in wf["data"]

    internal = app.config.get("INTERNAL_RUNTIME_CONFIG_TOKEN")
    assert internal
    g = client.get(
        "/api/v1/internal/hf-hub/token",
        headers={"X-Internal-Config-Token": internal},
    )
    assert g.status_code == 200
    gf = g.get_json()
    assert gf["ok"] is True
    assert gf["data"]["token"] == token


def test_hf_hub_test_connection_mocked(client, admin_jwt, monkeypatch):
    import requests

    from app.services import hf_hub_governance_service as mod

    monkeypatch.setattr(
        mod,
        "get_hf_hub_token_for_runtime",
        lambda: "hf_test_token",
    )

    def fake_get(url, headers=None, timeout=None):
        class R:
            status_code = 200
            text = ""

            def json(self):
                return {"name": "testuser"}

        return R()

    monkeypatch.setattr(requests, "get", fake_get)

    resp = client.post(
        "/api/v1/admin/ai/hf-hub/test-connection",
        headers={"Authorization": f"Bearer {admin_jwt}"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["data"]["ok"] is True
    assert body["data"]["health_status"] == "connected"


def test_internal_hf_hub_token_forbidden_without_header(client):
    resp = client.get("/api/v1/internal/hf-hub/token")
    assert resp.status_code == 403
    body = resp.get_json()
    assert body["ok"] is False


def test_hf_hub_clear(client, admin_jwt):
    client.post(
        "/api/v1/admin/ai/hf-hub/credential",
        json={"token": "hf_clear_me_token"},
        headers={"Authorization": f"Bearer {admin_jwt}"},
    )
    d = client.delete(
        "/api/v1/admin/ai/hf-hub/credential",
        headers={"Authorization": f"Bearer {admin_jwt}"},
    )
    assert d.status_code == 200
    st = client.get(
        "/api/v1/admin/ai/hf-hub/status",
        headers={"Authorization": f"Bearer {admin_jwt}"},
    )
    assert st.get_json()["data"]["credential_configured"] is False
