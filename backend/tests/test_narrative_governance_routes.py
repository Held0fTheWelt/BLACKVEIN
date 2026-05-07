"""Contract tests for narrative governance admin APIs."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.extensions import db
from app.models import NarrativeEvaluationRun, NarrativeRevisionCandidate

pytestmark = pytest.mark.routes_core


def test_runtime_config_get_returns_envelope(client, moderator_headers):
    response = client.get("/api/v1/admin/narrative/runtime/config", headers=moderator_headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert "data" in body
    assert "meta" in body


def test_runtime_config_post_rejects_invalid_strategy(client, moderator_headers):
    response = client.post(
        "/api/v1/admin/narrative/runtime/config",
        headers=moderator_headers,
        json={"output_validator": {"strategy": "made_up"}},
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body["ok"] is False
    assert body["error"]["code"] == "invalid_validation_strategy"


def test_revision_transition_invalid_path_returns_409(app, client, moderator_headers):
    with app.app_context():
        row = NarrativeRevisionCandidate(
            revision_id="rev_test_001",
            module_id="god_of_carnage",
            source_finding_id=None,
            target_kind="actor_mind",
            target_ref="veronique",
            operation="replace_clause",
            structured_delta_json={"path": "actor_minds.veronique", "value": "x"},
            expected_effects_json=["stability"],
            risk_flags_json=[],
            review_status="pending",
            requires_review=True,
            mutation_allowed=False,
            created_by="system",
        )
        db.session.add(row)
        db.session.commit()

    response = client.post(
        "/api/v1/admin/narrative/revisions/rev_test_001/transition",
        headers=moderator_headers,
        json={"to_status": "promoted", "by_role": "operator"},
    )
    assert response.status_code == 409
    body = response.get_json()
    assert body["ok"] is False
    assert body["error"]["code"] == "invalid_revision_transition"


def test_notifications_rule_upsert_roundtrip(client, moderator_headers):
    response = client.post(
        "/api/v1/admin/narrative/notifications/rules",
        headers=moderator_headers,
        json={
            "rule_id": "notif_rule_test",
            "event_type": "evaluation_failed",
            "condition": {"count": {"$gte": 1}},
            "channels": ["admin_ui"],
            "recipients": ["ops"],
            "enabled": True,
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert body["data"]["rule_id"] == "notif_rule_test"

    list_response = client.get("/api/v1/admin/narrative/notifications/rules", headers=moderator_headers)
    assert list_response.status_code == 200
    rows = list_response.get_json()["data"]["rules"]
    assert any(item["rule_id"] == "notif_rule_test" for item in rows)


def test_revision_transition_role_violation_returns_403(app, client, moderator_headers):
    with app.app_context():
        row = NarrativeRevisionCandidate(
            revision_id="rev_role_403",
            module_id="god_of_carnage",
            source_finding_id=None,
            target_kind="actor_mind",
            target_ref="michel",
            operation="replace_clause",
            structured_delta_json={"path": "actor_minds.michel", "value": "x"},
            expected_effects_json=["stability"],
            risk_flags_json=[],
            review_status="pending",
            requires_review=True,
            mutation_allowed=False,
            created_by="system",
        )
        db.session.add(row)
        db.session.commit()
    response = client.post(
        "/api/v1/admin/narrative/revisions/rev_role_403/transition",
        headers=moderator_headers,
        json={"to_status": "in_review", "by_role": "system"},
    )
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "transition_role_not_allowed"


def test_promote_preview_route_maps_reload_refusal(client, moderator_headers, monkeypatch):
    from app.api.v1 import narrative_governance_routes as routes_module
    from app.services.narrative_governance_service import NarrativeGovernanceError

    def _raise(**kwargs):
        raise NarrativeGovernanceError("reload refused", code="world_engine_reload_refused")

    monkeypatch.setattr(routes_module, "promote_preview_to_active", _raise)
    response = client.post(
        "/api/v1/admin/narrative/packages/god_of_carnage/promote-preview",
        headers=moderator_headers,
        json={"preview_id": "preview_001", "approved_by": "operator"},
    )
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "world_engine_reload_refused"


def test_runtime_health_sync_route_success(client, moderator_headers, monkeypatch):
    from app.api.v1 import narrative_governance_routes as routes_module

    monkeypatch.setattr(
        routes_module,
        "sync_runtime_health_from_world_engine",
        lambda module_id: {"module_id": module_id, "ingested_events": 1},
    )
    response = client.post(
        "/api/v1/admin/narrative/runtime/health/sync",
        headers=moderator_headers,
        json={"module_id": "god_of_carnage"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["ingested_events"] == 1


def test_runtime_preview_load_route_success(client, moderator_headers, monkeypatch):
    from app.api.v1 import narrative_governance_routes as routes_module

    monkeypatch.setattr(
        routes_module,
        "load_preview_into_runtime",
        lambda module_id, preview_id, isolation_mode: {"preview_id": preview_id, "load_status": "loaded"},
    )
    response = client.post(
        "/api/v1/admin/narrative/runtime/previews/load",
        headers=moderator_headers,
        json={"module_id": "god_of_carnage", "preview_id": "preview_001"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["preview_id"] == "preview_001"


def test_complete_evaluation_route_updates_run(app, client, moderator_headers):
    with app.app_context():
        db.session.add(
            NarrativeEvaluationRun(
                run_id="eval_complete_1",
                module_id="god_of_carnage",
                preview_id="preview_001",
                package_version="2.1.5-preview.1",
                run_type="preview_comparison",
                status="started",
                scores_json={},
                promotion_readiness_json={},
                created_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()
    response = client.post(
        "/api/v1/admin/narrative/evaluations/eval_complete_1/complete",
        headers=moderator_headers,
        json={
            "status": "completed",
            "scores": {"policy_compliance": 0.9},
            "promotion_readiness": {"is_promotable": True, "blocking_reasons": []},
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert body["data"]["status"] == "completed"
