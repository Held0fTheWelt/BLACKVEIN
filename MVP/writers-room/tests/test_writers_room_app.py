from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_app_module():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    spec = importlib.util.spec_from_file_location("writers_room_app_test", str(app_path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_index_redirects_to_login_when_not_authenticated(monkeypatch):
    monkeypatch.setenv("WRITERS_ROOM_SECRET_KEY", "test-secret")
    module = _load_app_module()
    client = module.app.test_client()

    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.location


def test_legacy_oracle_route_remains_transitional(monkeypatch):
    monkeypatch.setenv("WRITERS_ROOM_SECRET_KEY", "test-secret")
    module = _load_app_module()
    client = module.app.test_client()

    response = client.get("/legacy-oracle")
    assert response.status_code == 200
    assert b"Legacy Oracle (Transitional)" in response.data


def test_unified_review_flow_renders_report(monkeypatch):
    monkeypatch.setenv("WRITERS_ROOM_SECRET_KEY", "test-secret")
    module = _load_app_module()
    client = module.app.test_client()

    def fake_review(**kwargs):
        return {
            "canonical_flow": "writers_room_unified_stack_workflow",
            "module_id": kwargs["module_id"],
            "focus": kwargs["focus"],
            "outputs_are_recommendations_only": True,
            "issues": [],
            "recommendation_artifacts": [
                {
                    "artifact_id": "rec_test_1",
                    "artifact_class": "analysis_artifact",
                    "source_module_id": "god_of_carnage",
                    "shared_semantic_contract_version": "goc_frozen_vocab_surface_v1",
                    "evidence_refs": [],
                    "proposal_scope": "writers_room_bounded_recommendation",
                    "approval_state": "pending_review",
                    "body": "Recommend tightening canon references.",
                }
            ],
            "retrieval": {"sources": []},
            "review_bundle": {"bundle_id": "bundle_1"},
        }

    monkeypatch.setattr(module, "_request_writers_room_review", fake_review)

    with client.session_transaction() as sess:
        sess["access_token"] = "token"
    response = client.post(
        "/",
        data={"module_id": "god_of_carnage", "focus": "canon consistency"},
    )
    assert response.status_code == 200
    assert b"writers_room_unified_stack_workflow" in response.data
