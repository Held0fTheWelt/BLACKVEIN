"""Contract tests for world-engine internal narrative governance APIs."""

from __future__ import annotations

import app.api.http as http_module


def _internal_headers() -> dict[str, str]:
    key = http_module.PLAY_SERVICE_INTERNAL_API_KEY
    if key:
        return {"x-play-service-key": key}
    return {}


def test_internal_narrative_runtime_state_endpoint(client):
    response = client.get(
        "/api/internal/narrative/runtime/state",
        params={"module_id": "god_of_carnage"},
        headers=_internal_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["module_id"] == "god_of_carnage"


def test_internal_narrative_validator_config_endpoint(client):
    response = client.get("/api/internal/narrative/runtime/validator-config", headers=_internal_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["strategy"] in {"schema_only", "schema_plus_semantic", "strict_rule_engine"}


def test_internal_narrative_validate_and_recover_uses_safe_fallback(client):
    payload = {
        "packet": {
            "module_id": "god_of_carnage",
            "package_version": "2.1.3",
            "scene_id": "scene_02",
            "phase_id": "phase_2",
            "turn_number": 7,
            "player_input": "I insist",
            "selected_scene_function": "respond",
            "pacing_mode": "normal",
            "responder_set": [],
            "active_threads": [],
            "scene_constraints": {},
            "scene_guidance": {},
            "actor_minds": {"veronique": {}},
            "voice_rules": {},
            "legality_table": {"allowed_triggers": ["legal_trigger"]},
            "effective_policy": {},
            "output_schema_version": "runtime_turn_v2",
        },
        "output": {
            "narrative_response": "",
            "intent_summary": "",
            "responder_actor_ids": ["invalid_actor"],
            "detected_triggers": ["illegal_trigger"],
            "conflict_vector": "",
            "proposed_state_effects": [],
            "confidence": 0.1,
            "blocked_turn_reason": None,
        },
    }
    response = client.post(
        "/api/internal/narrative/runtime/validate-and-recover",
        json=payload,
        headers=_internal_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["mode"] in {"corrective_retry", "safe_fallback"}
    assert "validation_feedback" in body["data"]


def test_internal_narrative_reload_active_endpoint(client):
    response = client.post(
        "/api/internal/narrative/packages/reload-active",
        json={"module_id": "god_of_carnage", "expected_active_version": "2.1.3"},
        headers=_internal_headers(),
    )
    assert response.status_code in {200, 404}
    if response.status_code == 200:
        body = response.json()
        assert body["ok"] is True
        assert body["data"]["reload_status"] == "accepted"


def test_internal_narrative_preview_load_unload_and_session_endpoints(client):
    load_response = client.post(
        "/api/internal/narrative/packages/load-preview",
        json={"module_id": "god_of_carnage", "preview_id": "preview_0008", "isolation_mode": "session_namespace"},
        headers=_internal_headers(),
    )
    assert load_response.status_code in {200, 404}
    if load_response.status_code == 200:
        session_response = client.post(
            "/api/internal/narrative/preview/start-session",
            json={
                "module_id": "god_of_carnage",
                "preview_id": "preview_0008",
                "session_seed": "sim_001",
                "isolation_mode": "session_namespace",
            },
            headers=_internal_headers(),
        )
        assert session_response.status_code == 200
        payload = session_response.json()
        session_id = payload["data"]["preview_session_id"]
        end_response = client.post(
            "/api/internal/narrative/preview/end-session",
            json={"preview_session_id": session_id},
            headers=_internal_headers(),
        )
        assert end_response.status_code == 200
        unload_response = client.post(
            "/api/internal/narrative/packages/unload-preview",
            json={"module_id": "god_of_carnage", "preview_id": "preview_0008"},
            headers=_internal_headers(),
        )
        assert unload_response.status_code == 200


def test_internal_narrative_runtime_health_endpoint(client):
    response = client.get("/api/internal/narrative/runtime/health", headers=_internal_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "safe_fallback_rate" in body["data"]
