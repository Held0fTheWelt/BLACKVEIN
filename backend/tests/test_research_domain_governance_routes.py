"""HTTP tests for research-domain governance admin APIs."""

from __future__ import annotations


def test_research_overview_requires_auth(client):
    r = client.get("/api/v1/admin/research-domain/overview")
    assert r.status_code == 401


def test_research_overview_forbidden_for_non_admin(client, auth_headers):
    r = client.get("/api/v1/admin/research-domain/overview", headers=auth_headers)
    assert r.status_code == 403


def test_research_overview_admin_envelope(client, admin_headers):
    r = client.get("/api/v1/admin/research-domain/overview", headers=admin_headers)
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("ok") is True
    data = body.get("data") or {}
    assert data.get("domain") == "research_governance"
    assert "layers" in data
    principles = data.get("governance_principles") or {}
    assert principles.get("single_promoted_canonical_truth_per_governed_module") is True


def test_research_layer_unknown_returns_400(client, admin_headers):
    r = client.get("/api/v1/admin/research-domain/layer/not_a_layer", headers=admin_headers)
    assert r.status_code == 400
    err = r.get_json().get("error") or {}
    assert err.get("code") == "unknown_layer"


def test_research_layer_findings_admin(client, admin_headers):
    r = client.get("/api/v1/admin/research-domain/layer/findings_candidates", headers=admin_headers)
    assert r.status_code == 200
    layer = (r.get_json().get("data") or {}).get("layer") or {}
    assert layer.get("is_canonical_layer") is False
