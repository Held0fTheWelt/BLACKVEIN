"""Producer-side checks for nested run V1 and terminate envelope (Gate Block 1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.conftest import build_test_app


@pytest.fixture
def client(tmp_path: Path):
    app = build_test_app(tmp_path)
    return TestClient(app)


def _api_key() -> dict[str, str]:
    return {"X-Play-Service-Key": "internal-api-key-for-ops"}


def test_post_runs_returns_nested_run_v1_without_flat_run_id(client):
    r = client.post("/api/runs", json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "P"})
    assert r.status_code == 200
    body = r.json()
    assert "run" in body and isinstance(body["run"], dict)
    assert isinstance(body["run"].get("id"), str) and body["run"]["id"]
    assert "run_id" not in body
    assert isinstance(body.get("store"), dict)
    assert isinstance(body.get("hint"), str)


def test_get_run_details_nested_run_id_matches_path(client):
    run_id = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "P"},
    ).json()["run"]["id"]
    d = client.get(f"/api/runs/{run_id}").json()
    assert d["run"]["id"] == run_id
    assert "run_id" not in d
    for key in ("template_source", "template", "store", "lobby"):
        assert key in d


def test_internal_terminate_envelope_v1(client):
    run_id = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "P"},
    ).json()["run"]["id"]
    tr = client.post(
        f"/api/internal/runs/{run_id}/terminate",
        json={"actor_display_name": "admin", "reason": "pytest"},
        headers=_api_key(),
    )
    assert tr.status_code == 200
    b = tr.json()
    assert b["terminated"] is True
    assert b["run_id"] == run_id
    assert b["actor_display_name"] == "admin"
    assert b["reason"] == "pytest"
    assert isinstance(b.get("template_id"), str) and b["template_id"]


def test_delete_run_legacy_alias_returns_same_envelope_shape(client):
    run_id = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "P"},
    ).json()["run"]["id"]
    dr = client.delete(f"/api/runs/{run_id}", headers=_api_key())
    assert dr.status_code == 200
    b = dr.json()
    assert b["terminated"] is True
    assert b["run_id"] == run_id
    assert b["actor_display_name"] == "internal_delete"
    assert b["reason"] == "DELETE /api/runs"
