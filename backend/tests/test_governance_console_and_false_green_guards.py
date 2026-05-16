from __future__ import annotations

import pytest

pytestmark = pytest.mark.routes_core


def test_runtime_config_truth_summary_not_ready_when_probes_unverified(monkeypatch):
    from app.services import runtime_config_truth_service as service

    monkeypatch.setattr(
        service,
        "get_backend_configured_state",
        lambda: {"status": "configured", "use_governed_runtime_config": True},
    )
    monkeypatch.setattr(
        service,
        "get_backend_effective_config",
        lambda: {"status": "configured"},
    )
    monkeypatch.setattr(
        service,
        "get_world_engine_loaded_state",
        lambda: {"status": "requires_http_probe", "governed_runtime_active": None},
    )
    monkeypatch.setattr(
        service,
        "get_play_service_reachability",
        lambda: {"status": "requires_http_probe", "play_service_reachable": None},
    )

    payload = service.get_runtime_config_truth()
    assert payload["summary"]["status"] != "ready"
    assert any("requires HTTP probe" in issue for issue in payload["summary"]["issues"])


def test_langfuse_toggle_endpoint_does_not_claim_mutation(client, admin_headers):
    response = client.post(
        "/api/v1/admin/mvp4/game/session/s-1/langfuse-toggle",
        headers=admin_headers,
        json={"enabled": True, "reason": "test"},
    )
    assert response.status_code == 501
    body = response.get_json()
    assert body["ok"] is False
    assert body["error"]["code"] == "langfuse_toggle_not_wired"
    assert body["error"]["details"]["mutated"] is False


def test_governance_console_routes_return_ok_data(client, admin_headers, monkeypatch):
    from app.api.v1 import governance_console_routes as routes

    monkeypatch.setattr(routes.service, "get_runtime_readiness_authority", lambda **_: {"k": "runtime"})
    monkeypatch.setattr(routes.service, "get_adr0041_authority_state", lambda **_: {"k": "adr"})
    monkeypatch.setattr(routes.service, "get_capability_matrix_status", lambda **_: {"rows": []})
    monkeypatch.setattr(routes.service, "get_validator_registry_status", lambda: {"rows": []})
    monkeypatch.setattr(routes.service, "get_langfuse_mcp_evidence_status", lambda: {"ready": False})
    monkeypatch.setattr(routes.service, "get_runtime_aspect_ledger_view", lambda **_: {"ledger": {}})
    monkeypatch.setattr(routes.service, "get_narrative_systems_governance", lambda **_: {"systems": []})
    monkeypatch.setattr(routes.service, "get_feature_flag_governance", lambda: {"rows": []})

    paths = [
        "/api/v1/admin/governance/runtime-readiness-authority",
        "/api/v1/admin/governance/adr0041-authority-state",
        "/api/v1/admin/governance/capability-matrix",
        "/api/v1/admin/governance/validators/registry",
        "/api/v1/admin/governance/evidence/langfuse-mcp",
        "/api/v1/admin/governance/runtime-aspect-ledger",
        "/api/v1/admin/governance/narrative-systems",
        "/api/v1/admin/governance/feature-flags",
    ]
    for path in paths:
        response = client.get(path, headers=admin_headers)
        assert response.status_code == 200, path
        body = response.get_json()
        assert body["ok"] is True, path
        assert "data" in body, path


def test_narrative_routes_are_feature_gated(client, moderator_headers, monkeypatch):
    from app.auth import feature_registry

    monkeypatch.setattr(feature_registry, "user_can_access_feature", lambda user, feature_id: False)
    response = client.get("/api/v1/admin/narrative/runtime/config", headers=moderator_headers)
    assert response.status_code == 403
    body = response.get_json()
    assert body["ok"] is False
    assert body["error"]["code"] == "feature_forbidden"
