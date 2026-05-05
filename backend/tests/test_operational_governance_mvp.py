"""Integration tests for operational settings and runtime governance MVP."""

from __future__ import annotations

import base64

import app.services.governance_runtime_service as governance_runtime_service


def _with_kek(monkeypatch):
    monkeypatch.setenv("SECRETS_KEK", base64.b64encode(b"a" * 32).decode("utf-8"))


def test_bootstrap_public_status_available(client):
    response = client.get("/api/v1/bootstrap/public-status")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert "bootstrap_required" in payload["data"]


def test_admin_bootstrap_initialize_and_modes_flow(client, admin_headers, monkeypatch):
    _with_kek(monkeypatch)
    response = client.post(
        "/api/v1/admin/bootstrap/initialize",
        headers=admin_headers,
        json={
            "selected_preset": "balanced",
            "admin_email": "operator@example.com",
            "secret_storage_mode": "same_db_encrypted",
            "generation_execution_mode": "mock_only",
            "retrieval_execution_mode": "disabled",
            "validation_execution_mode": "schema_only",
            "provider_selection_mode": "local_only",
            "trust_anchor": {"allow_reopen_with_recovery_token": True},
        },
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["bootstrap_status"] == "initialized"

    modes_response = client.get("/api/v1/admin/runtime/modes", headers=admin_headers)
    assert modes_response.status_code == 200
    modes = modes_response.get_json()["data"]
    assert modes["generation_execution_mode"] == "mock_only"


def test_provider_credential_write_is_write_only(client, admin_headers, monkeypatch):
    _with_kek(monkeypatch)
    create_provider_response = client.post(
        "/api/v1/admin/ai/providers",
        headers=admin_headers,
        json={"provider_type": "openai", "display_name": "OpenAI Primary", "base_url": "https://api.openai.com/v1", "is_enabled": True},
    )
    assert create_provider_response.status_code == 200
    provider_id = create_provider_response.get_json()["data"]["provider_id"]

    write_response = client.post(
        f"/api/v1/admin/ai/providers/{provider_id}/credential",
        headers=admin_headers,
        json={"api_key": "sk-test-credential"},
    )
    assert write_response.status_code == 200
    write_payload = write_response.get_json()["data"]
    assert write_payload["credential_written"] is True
    assert "sk-test-credential" not in str(write_payload)

    provider_list_response = client.get("/api/v1/admin/ai/providers", headers=admin_headers)
    assert provider_list_response.status_code == 200
    providers = provider_list_response.get_json()["data"]["providers"]
    match = next(provider for provider in providers if provider["provider_id"] == provider_id)
    assert match["credential_configured"] is True
    assert "sk-test-credential" not in str(match)


def test_runtime_mode_validation_blocks_ai_without_real_provider(client, admin_headers):
    response = client.patch(
        "/api/v1/admin/runtime/modes",
        headers=admin_headers,
        json={
            "generation_execution_mode": "ai_only",
            "retrieval_execution_mode": "disabled",
            "validation_execution_mode": "schema_only",
            "provider_selection_mode": "remote_allowed",
            "runtime_profile": "balanced",
        },
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["ok"] is False
    assert payload["error"]["code"] == "generation_mode_invalid"


def test_runtime_readiness_payload_includes_actionable_fields(client, admin_headers):
    response = client.get("/api/v1/admin/ai/runtime-readiness", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data.get("readiness_headline")
    assert data.get("readiness_severity") in {"healthy", "blocked", "degraded"}
    assert isinstance(data.get("status_semantics"), dict)
    assert data["status_semantics"].get("healthy")
    assert isinstance(data.get("readiness_legend"), list)
    assert len(data["readiness_legend"]) >= 2
    assert isinstance(data.get("provider_summary"), dict)
    assert isinstance(data.get("blockers"), list)
    for row in data["blockers"]:
        assert row.get("suggested_action"), f"missing suggested_action on {row!r}"


def test_moderator_denied_ai_runtime_governance_api(client, moderator_headers):
    response = client.get("/api/v1/admin/ai/providers", headers=moderator_headers)
    assert response.status_code == 403
    payload = response.get_json()
    assert "feature" in (payload.get("error") or "").lower()


def test_provider_contract_exposes_first_class_openrouter_metadata(client, admin_headers):
    create_response = client.post(
        "/api/v1/admin/ai/providers",
        headers=admin_headers,
        json={"provider_type": "openrouter", "display_name": "OpenRouter Main", "is_enabled": True},
    )
    assert create_response.status_code == 200

    list_response = client.get("/api/v1/admin/ai/providers", headers=admin_headers)
    assert list_response.status_code == 200
    providers = list_response.get_json()["data"]["providers"]
    row = next(p for p in providers if p["provider_type"] == "openrouter")
    assert row["auth_mode"] == "bearer_api_key"
    assert "Authorization" in row["required_headers"]
    assert row["stage_support"] == "template"
    assert row["supports_model_discovery"] is True


def test_ollama_health_check_reports_normalized_status(client, admin_headers, monkeypatch):
    class _StubResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(governance_runtime_service, "urlopen", lambda req, timeout=0: _StubResp())
    create_response = client.post(
        "/api/v1/admin/ai/providers",
        headers=admin_headers,
        json={"provider_type": "ollama", "display_name": "Local Ollama", "base_url": "http://localhost:11434/api", "is_enabled": True},
    )
    assert create_response.status_code == 200
    provider_id = create_response.get_json()["data"]["provider_id"]

    test_response = client.post(f"/api/v1/admin/ai/providers/{provider_id}/test-connection", headers=admin_headers, json={})
    assert test_response.status_code == 200
    payload = test_response.get_json()["data"]
    assert payload["health_status"] == "healthy"
    assert payload["reachable"] is True
    assert payload["authenticated"] is True
    assert payload["usable"] is True


def test_internal_runtime_config_requires_token(client):
    response = client.get("/api/v1/internal/runtime-config")
    assert response.status_code == 403
    payload = response.get_json()
    assert payload["ok"] is False


def test_model_route_crud_and_runtime_readiness(client, admin_headers, monkeypatch):
    _with_kek(monkeypatch)
    provider_response = client.post(
        "/api/v1/admin/ai/providers",
        headers=admin_headers,
        json={
            "provider_type": "openai",
            "display_name": "Primary OpenAI",
            "base_url": "https://api.openai.com/v1",
            "is_enabled": True,
        },
    )
    assert provider_response.status_code == 200
    provider_id = provider_response.get_json()["data"]["provider_id"]

    client.post(
        f"/api/v1/admin/ai/providers/{provider_id}/credential",
        headers=admin_headers,
        json={"api_key": "sk-phase1-test"},
    )

    class _StubResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(governance_runtime_service, "urlopen", lambda req, timeout=0: _StubResp())
    health_response = client.post(
        f"/api/v1/admin/ai/providers/{provider_id}/test-connection",
        headers=admin_headers,
        json={},
    )
    assert health_response.status_code == 200

    model_response = client.post(
        "/api/v1/admin/ai/models",
        headers=admin_headers,
        json={
            "provider_id": provider_id,
            "model_name": "gpt-4o-mini",
            "display_name": "GPT 4o Mini",
            "model_role": "llm",
            "supports_structured_output": True,
            "is_enabled": True,
            "timeout_seconds": 30,
        },
    )
    assert model_response.status_code == 200
    model_id = model_response.get_json()["data"]["model_id"]

    route_response = client.post(
        "/api/v1/admin/ai/routes",
        headers=admin_headers,
        json={
            "task_kind": "narrative_live_generation",
            "workflow_scope": "global",
            "preferred_model_id": model_id,
            "fallback_model_id": model_id,
            "is_enabled": True,
            "use_mock_when_provider_unavailable": False,
        },
    )
    assert route_response.status_code == 200

    readiness_response = client.get("/api/v1/admin/ai/runtime-readiness", headers=admin_headers)
    assert readiness_response.status_code == 200
    readiness = readiness_response.get_json()["data"]
    assert readiness["ai_only_valid"] is True
    assert readiness["mock_only_required"] is False
    assert readiness["enabled_non_mock_provider_present"] is True
    assert readiness["enabled_non_mock_model_present"] is True
    assert readiness["enabled_ai_route_present"] is True


def test_cost_budget_and_usage_endpoints(client, admin_headers):
    budget_response = client.post(
        "/api/v1/admin/costs/budgets",
        headers=admin_headers,
        json={
            "scope_kind": "global",
            "scope_ref": None,
            "daily_limit": "100.00",
            "monthly_limit": "1000.00",
            "warning_threshold_percent": 80,
            "hard_stop_enabled": False,
        },
    )
    assert budget_response.status_code == 200
    budget_id = budget_response.get_json()["data"]["budget_policy_id"]
    assert budget_id

    usage_response = client.post(
        "/api/v1/admin/costs/usage-events",
        headers=admin_headers,
        json={
            "task_kind": "narrative_live_generation",
            "workflow_scope": "global",
            "request_id": "req-001",
            "cost_method_used": "none",
            "estimated_cost": "0.00",
        },
    )
    assert usage_response.status_code == 200
    usage_id = usage_response.get_json()["data"]["usage_event_id"]
    assert usage_id

    list_response = client.get("/api/v1/admin/costs/usage-events", headers=admin_headers)
    assert list_response.status_code == 200
    items = list_response.get_json()["data"]["items"]
    assert any(item["usage_event_id"] == usage_id for item in items)


def test_mvp4_session_summary_exposes_live_cost_budget_and_overrides(client, admin_headers, monkeypatch):
    session_id = "story-session-phase-c-summary"

    with client.application.app_context():
        from ai_stack.evaluation_pipeline import EvaluationPipeline, TurnScore
        from app.services.observability_governance_service import (
            get_runtime_governance_storage,
            ingest_runtime_turn_cost,
        )

        redis_client = get_runtime_governance_storage()
        ingest_runtime_turn_cost(
            redis_client,
            session_id=session_id,
            turn_number=0,
            cost_summary={
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "cost_breakdown": {"ldss": 0.0, "narrator": 0.0},
                "phase_costs": {
                    "ldss": {"phase": "ldss", "billing_mode": "deterministic", "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
                    "narrator": {"phase": "narrator", "billing_mode": "deterministic", "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
                },
            },
            metadata={"module_id": "god_of_carnage", "selected_player_role": "veronique"},
        )

        pipeline = EvaluationPipeline(redis_client)
        pipeline.record_turn_score(
            TurnScore(
                turn_id="turn-0",
                session_id=session_id,
                scores={"coherence": 4.0, "authenticity": 4.5, "player_agency": 4.5, "immersion": 4.0},
                average_score=4.25,
                passed=True,
                annotated_by="tester",
            ),
            session_id,
        )

    monkeypatch.setattr(
        "app.services.game_service.get_story_state",
        lambda requested_session_id: {
            "session_id": requested_session_id,
            "module_id": "god_of_carnage",
            "turn_counter": 0,
            "current_scene_id": "scene_1_opening",
            "runtime_projection": {"selected_player_role": "veronique", "human_actor_id": "veronique"},
            "story_window": {"entries": [{"turn_number": 0, "role": "runtime", "text": "Opening pressure."}], "entry_count": 1},
            "updated_at": "2026-05-05T12:00:00+00:00",
            "last_committed_turn": {
                "turn_number": 0,
                "narrator_streaming": {"status": "streaming", "session_id": requested_session_id},
                "diagnostics_envelope": {
                    "quality_class": "healthy",
                    "degradation_timeline": [],
                    "cost_summary": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
                },
            },
        },
    )

    object_override_response = client.post(
        "/api/v1/admin/mvp4/overrides/object-admission",
        headers=admin_headers,
        json={
            "object_id": "glass_tulips",
            "session_id": session_id,
            "tier_change": "allow",
            "reason": "operator review",
        },
    )
    assert object_override_response.status_code == 200

    response = client.get(f"/api/v1/admin/mvp4/game/session/{session_id}/summary", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["session_id"] == session_id
    assert data["diagnostics_envelope"]["quality_class"] == "healthy"
    assert data["cost_summary"]["turns_executed"] == 1
    assert data["budget_status"]["used_tokens"] == 0
    assert data["narrator_streaming"]["status"] == "streaming"
    assert data["evaluation"]["recent_turns"][0]["turn_id"] == "turn-0"
    assert data["overrides"]["active_count"] >= 1


def test_mvp4_evaluation_routes_close_annotation_baseline_and_regression_loop(client, admin_headers):
    session_id = "story-session-phase-c-eval"

    record_response = client.post(
        f"/api/v1/admin/mvp4/evaluation/session/{session_id}/turn-score",
        headers=admin_headers,
        json={
            "turn_id": "turn-1",
            "scores": {"coherence": 4.0, "authenticity": 4.0, "player_agency": 5.0, "immersion": 4.0},
            "average_score": 4.25,
            "passed": True,
            "feedback_tags": ["baseline_candidate"],
            "notes": "Strong opening follow-through",
        },
    )
    assert record_response.status_code == 200

    baseline_response = client.post(
        "/api/v1/admin/mvp4/evaluation/baseline/turns",
        headers=admin_headers,
        json={
            "baseline_id": "goc_evaluation_baseline",
            "session_id": session_id,
            "turn_id": "turn-1",
        },
    )
    assert baseline_response.status_code == 200
    baseline_data = baseline_response.get_json()["data"]
    assert baseline_data["canonical_turn_count"] >= 1
    assert "coherence" in baseline_data["metrics"]

    recent_response = client.get(
        f"/api/v1/admin/mvp4/evaluation/session/{session_id}/recent-turns?limit=5",
        headers=admin_headers,
    )
    assert recent_response.status_code == 200
    recent_data = recent_response.get_json()["data"]
    assert recent_data["recent_turns"][0]["turn_id"] == "turn-1"

    regression_response = client.get(
        f"/api/v1/admin/mvp4/evaluation/session/{session_id}/regression?turn_count=5",
        headers=admin_headers,
    )
    assert regression_response.status_code == 200
    regression = regression_response.get_json()["data"]
    assert regression["session_id"] == session_id
    assert regression["turn_count_evaluated"] >= 1
    assert regression["regression_detected"] is False


def test_runtime_governance_redis_json_storage_round_trips_structured_values():
    from app.services.observability_governance_service import RedisJsonObservabilityStorage, TokenBudgetConfig

    class FakeRedis:
        def __init__(self):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value):
            self.data[key] = value

        def delete(self, key):
            self.data.pop(key, None)

    storage = RedisJsonObservabilityStorage(FakeRedis())
    storage.set("token_budget:test", TokenBudgetConfig(session_id="test", used_tokens=7))
    storage.set("cost_usage_events", [{"session_id": "test", "cost_usd": 0.0}])

    budget = storage.get("token_budget:test")
    assert budget["session_id"] == "test"
    assert budget["used_tokens"] == 7
    assert storage.get("cost_usage_events") == [{"session_id": "test", "cost_usd": 0.0}]
