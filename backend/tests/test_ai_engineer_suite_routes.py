"""Tests for Phase 2 AI Engineer Suite admin APIs."""

from __future__ import annotations

import app.api.v1.ai_engineer_suite_routes as suite_routes


def test_admin_ai_rag_status_endpoint(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        suite_routes,
        "get_rag_operations_status",
        lambda: {
            "corpus": {"chunk_count": 10},
            "safe_actions": [{"action_id": "refresh_corpus"}],
            "degraded_reasons": [],
        },
    )
    response = client.get("/api/v1/admin/ai/rag/status", headers=admin_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["data"]["corpus"]["chunk_count"] == 10
    assert payload["data"]["safe_actions"][0]["action_id"] == "refresh_corpus"


def test_admin_ai_rag_probe_endpoint(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        suite_routes,
        "run_rag_query_probe",
        lambda body: {
            "request": {"query": body.get("query")},
            "result": {"status": "ok", "hit_count": 1, "hits": [{"chunk_id": "c1"}]},
        },
    )
    response = client.post("/api/v1/admin/ai/rag/probe", headers=admin_headers, json={"query": "test probe"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["data"]["request"]["query"] == "test probe"
    assert payload["data"]["result"]["hit_count"] == 1


def test_admin_ai_rag_action_endpoint(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        suite_routes,
        "run_rag_safe_action",
        lambda action_id: {"action_id": action_id, "performed": True, "operator_message": "done"},
    )
    response = client.post("/api/v1/admin/ai/rag/actions/rebuild_dense_index", headers=admin_headers, json={})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["data"]["action_id"] == "rebuild_dense_index"
    assert payload["data"]["performed"] is True


def test_admin_ai_orchestration_status_endpoint(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        suite_routes,
        "get_orchestration_status",
        lambda trace_id=None: {
            "langgraph": {"dependency_available": True, "runtime_profile": "balanced"},
            "langchain": {"bridge_available": True},
        },
    )
    response = client.get("/api/v1/admin/ai/orchestration/status", headers=admin_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["data"]["langgraph"]["dependency_available"] is True
    assert payload["data"]["langchain"]["bridge_available"] is True


def test_admin_ai_runtime_dashboard_endpoint(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        suite_routes,
        "get_runtime_dashboard",
        lambda trace_id=None: {
            "summary": {"ai_only_valid": False},
            "blockers": [{"domain": "rag", "message": "Embedding unavailable"}],
            "links": [{"label": "RAG Operations", "path": "/manage/rag-operations"}],
        },
    )
    response = client.get("/api/v1/admin/ai/runtime-dashboard", headers=admin_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["data"]["summary"]["ai_only_valid"] is False
    assert payload["data"]["blockers"][0]["domain"] == "rag"


def test_admin_ai_presets_endpoints(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        suite_routes,
        "list_runtime_presets",
        lambda: {"active_preset_id": "safe_local", "presets": [{"preset_id": "safe_local"}]},
    )
    list_response = client.get("/api/v1/admin/ai/presets", headers=admin_headers)
    assert list_response.status_code == 200
    list_payload = list_response.get_json()
    assert list_payload["ok"] is True
    assert list_payload["data"]["active_preset_id"] == "safe_local"

    monkeypatch.setattr(
        suite_routes,
        "apply_runtime_preset",
        lambda preset_id, actor, keep_overrides=False: {
            "applied_preset_id": preset_id,
            "kept_overrides": keep_overrides,
            "actor": actor,
        },
    )
    apply_response = client.post(
        "/api/v1/admin/ai/presets/apply",
        headers=admin_headers,
        json={"preset_id": "balanced", "keep_overrides": True},
    )
    assert apply_response.status_code == 200
    apply_payload = apply_response.get_json()
    assert apply_payload["ok"] is True
    assert apply_payload["data"]["applied_preset_id"] == "balanced"
    assert apply_payload["data"]["kept_overrides"] is True


def test_admin_ai_advanced_settings_endpoints(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        suite_routes,
        "get_advanced_settings",
        lambda: {"settings": {"runtime_profile": "balanced"}, "effective_config": {"override_count": 1}},
    )
    get_response = client.get("/api/v1/admin/ai/advanced-settings", headers=admin_headers)
    assert get_response.status_code == 200
    get_payload = get_response.get_json()
    assert get_payload["ok"] is True
    assert get_payload["data"]["settings"]["runtime_profile"] == "balanced"

    monkeypatch.setattr(
        suite_routes,
        "update_advanced_settings",
        lambda body, actor: {"settings": {"runtime_profile": body.get("runtime_profile")}, "actor": actor},
    )
    patch_response = client.patch(
        "/api/v1/admin/ai/advanced-settings",
        headers=admin_headers,
        json={"runtime_profile": "quality_first"},
    )
    assert patch_response.status_code == 200
    patch_payload = patch_response.get_json()
    assert patch_payload["ok"] is True
    assert patch_payload["data"]["settings"]["runtime_profile"] == "quality_first"


def test_admin_ai_effective_config_and_changes(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        suite_routes,
        "get_effective_runtime_config",
        lambda: {"active_preset_id": "safe_local", "override_count": 0},
    )
    effective_response = client.get("/api/v1/admin/ai/effective-config", headers=admin_headers)
    assert effective_response.status_code == 200
    effective_payload = effective_response.get_json()
    assert effective_payload["ok"] is True
    assert effective_payload["data"]["active_preset_id"] == "safe_local"

    monkeypatch.setattr(
        suite_routes,
        "list_settings_changes",
        lambda limit=25: {"items": [{"scope": "ai_runtime", "summary": "updated"}], "limit": limit},
    )
    changes_response = client.get("/api/v1/admin/ai/settings-changes?limit=12", headers=admin_headers)
    assert changes_response.status_code == 200
    changes_payload = changes_response.get_json()
    assert changes_payload["ok"] is True
    assert changes_payload["data"]["items"][0]["scope"] == "ai_runtime"


def test_admin_ai_advanced_settings_reset(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        suite_routes,
        "reset_advanced_overrides",
        lambda actor: {"operator_message": "reset", "actor": actor},
    )
    response = client.post("/api/v1/admin/ai/advanced-settings/reset-overrides", headers=admin_headers, json={})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["data"]["operator_message"] == "reset"


def test_admin_ai_rag_settings_patch_roundtrip(client, admin_headers):
    patch_response = client.patch(
        "/api/v1/admin/ai/rag/settings",
        headers=admin_headers,
        json={
            "retrieval_execution_mode": "sparse_only",
            "retrieval_top_k": 5,
            "retrieval_profile": "runtime_turn_support",
            "embeddings_enabled": False,
        },
    )
    assert patch_response.status_code == 200
    patch_payload = patch_response.get_json()
    assert patch_payload["ok"] is True
    assert patch_payload["data"]["retrieval_execution_mode"] == "sparse_only"
    assert patch_payload["data"]["retrieval_top_k"] == 5

    get_response = client.get("/api/v1/admin/ai/rag/settings", headers=admin_headers)
    assert get_response.status_code == 200
    get_payload = get_response.get_json()
    assert get_payload["ok"] is True
    assert get_payload["data"]["retrieval_execution_mode"] == "sparse_only"


def test_admin_ai_orchestration_settings_patch_roundtrip(client, admin_headers):
    patch_response = client.patch(
        "/api/v1/admin/ai/orchestration/settings",
        headers=admin_headers,
        json={
            "runtime_profile": "balanced",
            "enable_corrective_feedback": True,
            "runtime_diagnostics_verbosity": "operator",
            "max_retry_attempts": 2,
        },
    )
    assert patch_response.status_code == 200
    patch_payload = patch_response.get_json()
    assert patch_payload["ok"] is True
    assert patch_payload["data"]["runtime_profile"] == "balanced"
    assert patch_payload["data"]["max_retry_attempts"] == 2

    get_response = client.get("/api/v1/admin/ai/orchestration/settings", headers=admin_headers)
    assert get_response.status_code == 200
    get_payload = get_response.get_json()
    assert get_payload["ok"] is True
    assert get_payload["data"]["runtime_profile"] == "balanced"
