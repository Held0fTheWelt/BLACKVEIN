"""Milestone 11: trace continuity, governance evidence API, and failure visibility tests."""

from __future__ import annotations

from app.observability.audit_log import log_world_engine_bridge, log_workflow_audit
from app.services.game_service import GameServiceError


def test_admin_session_evidence_returns_runtime_bundle(client, moderator_headers, monkeypatch):
    create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
    assert create_resp.status_code == 201
    session_id = create_resp.get_json()["session_id"]

    monkeypatch.setattr(
        "app.services.ai_stack_evidence_service.get_story_state",
        lambda *_a, **_k: {"session_id": "we-x", "turn_counter": 0},
    )
    monkeypatch.setattr(
        "app.services.ai_stack_evidence_service.get_story_diagnostics",
        lambda *_a, **_k: {
            "diagnostics": [
                {
                    "retrieval": {"hit_count": 1, "status": "ok", "domain": "runtime", "profile": "turn"},
                    "graph": {
                        "execution_health": "healthy",
                        "fallback_path_taken": False,
                        "errors": [],
                        "capability_audit": [{"capability_name": "wos.context_pack.build", "outcome": "allowed"}],
                        "repro_metadata": {
                            "module_id": "god_of_carnage",
                            "graph_path_summary": "primary_invoke_langchain_only",
                            "adapter_invocation_mode": "langchain_structured_primary",
                        },
                    },
                }
            ],
            "committed_history_tail": [
                {
                    "turn_number": 1,
                    "trace_id": "t-committed",
                    "progression_commit": {"allowed": False, "reason": "no_scene_proposal"},
                    "committed_state_after": {"current_scene_id": "s1", "turn_counter": 1},
                }
            ],
            "committed_state": {"current_scene_id": "s1", "turn_counter": 1},
            "warnings": ["diagnostics_are_orchestration_envelopes_committed_truth_is_session_fields_and_history"],
        },
    )

    from app.runtime.session_store import get_session as get_runtime_session

    runtime_session = get_runtime_session(session_id)
    runtime_session.current_runtime_state.metadata["world_engine_story_session_id"] = "we-x"

    response = client.get(
        f"/api/v1/admin/ai-stack/session-evidence/{session_id}",
        headers=moderator_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["backend_session_id"] == session_id
    assert data["module_id"] == "god_of_carnage"
    assert data["world_engine_story_session_id"] == "we-x"
    assert data["world_engine_state"]["session_id"] == "we-x"
    assert data.get("last_turn_repro_metadata", {}).get("module_id") == "god_of_carnage"
    assert "trace_id" in data
    et = data.get("execution_truth") or {}
    assert et.get("last_turn_graph_mode", {}).get("execution_health") == "healthy"
    assert et.get("committed_narrative_surface", {}).get("last_committed_turn_summary", {}).get("trace_id") == "t-committed"
    assert et.get("retrieval_influence", {}).get("hit_count") == 1


def test_admin_session_evidence_404_for_unknown_session(client, moderator_headers):
    response = client.get(
        "/api/v1/admin/ai-stack/session-evidence/nonexistent-session-id",
        headers=moderator_headers,
    )
    assert response.status_code == 404
    data = response.get_json()
    assert data.get("error") == "backend_session_not_found"


def test_execute_turn_surfaces_world_engine_failure(client, monkeypatch):
    create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
    session_id = create_resp.get_json()["session_id"]

    def _boom(**_kwargs):
        raise GameServiceError("play down", status_code=503)

    monkeypatch.setattr("app.api.v1.session_routes.create_story_session", _boom)

    response = client.post(
        f"/api/v1/sessions/{session_id}/turns",
        json={"player_input": "look"},
    )
    assert response.status_code == 502
    body = response.get_json()
    assert body.get("failure_class") == "world_engine_unreachable"
    assert "trace_id" in body


def test_workflow_and_bridge_audit_emit_structured_dicts(monkeypatch):
    sent: list[dict] = []

    class _FakeLogger:
        def info(self, msg):
            sent.append(msg)

    monkeypatch.setattr("app.observability.audit_log.get_audit_logger", lambda: _FakeLogger())
    log_workflow_audit(
        "t-wf", workflow="writers_room_review", actor_id="1", outcome="ok", resource_id="god_of_carnage"
    )
    log_world_engine_bridge(
        "t-br",
        operation="execute_story_turn",
        backend_session_id="bs1",
        world_engine_story_session_id="we1",
        outcome="ok",
    )
    assert sent[0]["event"] == "workflow.run"
    assert sent[0]["trace_id"] == "t-wf"
    assert sent[1]["event"] == "world_engine.bridge"
    assert sent[1].get("failure_class") is None


def test_improvement_experiment_response_includes_trace(client, auth_headers):
    variant_resp = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={"baseline_id": "god_of_carnage", "candidate_summary": "Test candidate for trace field."},
    )
    assert variant_resp.status_code == 201
    variant_id = variant_resp.get_json()["variant_id"]
    experiment_resp = client.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers,
        json={"variant_id": variant_id},
    )
    assert experiment_resp.status_code == 200
    payload = experiment_resp.get_json()
    assert "trace_id" in payload
    assert "experiment" in payload
    assert "recommendation_package" in payload


def test_session_evidence_includes_repaired_layer_signals(client, moderator_headers, monkeypatch):
    create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
    session_id = create_resp.get_json()["session_id"]

    monkeypatch.setattr(
        "app.services.ai_stack_evidence_service.get_story_state",
        lambda *_a, **_k: {"session_id": "we-y", "turn_counter": 1},
    )
    monkeypatch.setattr(
        "app.services.ai_stack_evidence_service.get_story_diagnostics",
        lambda *_a, **_k: {
            "diagnostics": [
                {
                    "retrieval": {
                        "hit_count": 2,
                        "status": "ok",
                        "domain": "runtime",
                        "profile": "runtime_turn_support",
                    },
                    "graph": {
                        "execution_health": "healthy",
                        "errors": [],
                        "fallback_path_taken": False,
                        "capability_audit": [
                            {"capability_name": "wos.context_pack.build", "outcome": "allowed"}
                        ],
                        "repro_metadata": {
                            "trace_id": "trace-x",
                            "graph_name": "wos_runtime_turn_graph",
                            "runtime_turn_graph_version": "v-test",
                            "graph_path_summary": "primary_invoke_langchain_only",
                            "adapter_invocation_mode": "langchain_structured_primary",
                            "selected_model": "mock-small",
                            "selected_provider": "mock",
                            "model_success": True,
                            "model_fallback_used": False,
                            "retrieval_domain": "runtime",
                            "retrieval_profile": "runtime_turn_support",
                            "retrieval_status": "ok",
                            "retrieval_hit_count": 2,
                            "module_id": "god_of_carnage",
                            "session_id": "we-y",
                            "ai_stack_semantic_version": "test-semantic",
                            "routing_policy_version": "registry_default_v1",
                            "host_versions": {"world_engine_app_version": "test"},
                        },
                    },
                }
            ]
        },
    )
    monkeypatch.setattr(
        "app.services.ai_stack_evidence_service._latest_writers_room_review",
        lambda: {
            "review_id": "review_1",
            "review_state": {"status": "accepted"},
            "issues": [1],
            "patch_candidates": [1],
            "variant_candidates": [1],
            "retrieval_trace": {"evidence_tier": "moderate", "evidence_strength": "moderate"},
            "model_generation": {"adapter_invocation_mode": "langchain_structured_primary"},
            "review_summary": {"bundle_id": "b1", "bundle_status": "recommendation_only"},
            "capability_audit": [{"capability_name": "wos.review_bundle.build", "outcome": "allowed"}],
        },
    )
    monkeypatch.setattr(
        "app.services.ai_stack_evidence_service._latest_improvement_package",
        lambda: {
            "package_id": "pkg_1",
            "review_status": "pending_governance_review",
            "recommendation_summary": "promote",
            "evaluation": {"comparison": {"quality_heuristic_delta": 0.1}},
            "evidence_bundle": {
                "comparison": {"quality_heuristic_delta": 0.1},
                "retrieval_source_paths": ["modules/a.md"],
                "transcript_evidence": {"run_id": "run-1"},
                "governance_review_bundle_id": "rb-1",
            },
            "workflow_stages": [{"id": "governance_review_bundle"}],
        },
    )

    from app.runtime.session_store import get_session as get_runtime_session

    runtime_session = get_runtime_session(session_id)
    runtime_session.current_runtime_state.metadata["world_engine_story_session_id"] = "we-y"

    response = client.get(
        f"/api/v1/admin/ai-stack/session-evidence/{session_id}",
        headers=moderator_headers,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert "repaired_layer_signals" in payload
    assert payload["repaired_layer_signals"]["runtime"]["retrieval"]["profile"] == "runtime_turn_support"
    assert payload["repaired_layer_signals"]["runtime"]["execution_health"] == "healthy"
    assert payload["repaired_layer_signals"]["tools"]["capability_audit_count"] == 1
    assert payload["repaired_layer_signals"]["tools"]["material_influence"] is True
    assert payload["repaired_layer_signals"]["writers_room"]["review_status"] == "accepted"
    assert payload["repaired_layer_signals"]["writers_room"]["evidence_tier"] == "moderate"
    assert payload["repaired_layer_signals"]["writers_room"]["review_bundle_id"] == "b1"
    assert payload["repaired_layer_signals"]["improvement"]["package_id"] == "pkg_1"
    inf = payload["repaired_layer_signals"]["improvement"]["evidence_influence"]
    assert inf["retrieval_source_path_count"] == 1
    assert inf["has_transcript_evidence"] is True
    assert inf["has_governance_review_bundle"] is True
    assert "governance_review_bundle" in inf["workflow_stage_ids"]
    et = payload.get("execution_truth") or {}
    assert et.get("last_turn_graph_mode", {}).get("graph_path_summary") == "primary_invoke_langchain_only"
    assert et.get("tool_influence", {}).get("material_influence") is True
    assert et.get("retrieval_influence", {}).get("evidence_tier") == "moderate"


def test_session_evidence_surfaces_degraded_execution_health(client, moderator_headers, monkeypatch):
    """Degraded graph paths must appear in execution_truth and degraded_path_signals."""
    create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
    session_id = create_resp.get_json()["session_id"]

    monkeypatch.setattr(
        "app.services.ai_stack_evidence_service.get_story_state",
        lambda *_a, **_k: {"session_id": "we-z", "turn_counter": 1},
    )
    monkeypatch.setattr(
        "app.services.ai_stack_evidence_service.get_story_diagnostics",
        lambda *_a, **_k: {
            "diagnostics": [
                {
                    "graph": {
                        "execution_health": "model_fallback",
                        "fallback_path_taken": True,
                        "errors": [],
                        "capability_audit": [],
                        "repro_metadata": {
                            "graph_path_summary": "used_fallback_model_node_raw_adapter",
                            "adapter_invocation_mode": "raw_adapter_graph_managed_fallback",
                        },
                    }
                }
            ]
        },
    )
    from app.runtime.session_store import get_session as get_runtime_session

    runtime_session = get_runtime_session(session_id)
    runtime_session.current_runtime_state.metadata["world_engine_story_session_id"] = "we-z"

    response = client.get(
        f"/api/v1/admin/ai-stack/session-evidence/{session_id}",
        headers=moderator_headers,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert "fallback_path_taken" in (payload.get("degraded_path_signals") or [])
    assert (payload.get("execution_truth") or {}).get("last_turn_graph_mode", {}).get("execution_health") == "model_fallback"


def test_release_readiness_reports_partial_honestly(client, moderator_headers, monkeypatch):
    monkeypatch.setattr("app.services.ai_stack_evidence_service._latest_writers_room_review", lambda: None)
    monkeypatch.setattr("app.services.ai_stack_evidence_service._latest_improvement_package", lambda: None)

    response = client.get("/api/v1/admin/ai-stack/release-readiness", headers=moderator_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["overall_status"] == "partial"
    assert any(area["status"] == "partial" for area in payload["areas"])


def test_release_readiness_sparse_env_does_not_claim_ready(client, moderator_headers, monkeypatch):
    """Sparse environment: no improvement packages and no writers-room reviews exist.

    Proves the system is honest about partial evidence states rather than silently
    claiming readiness when the underlying artifact stores are empty.
    """
    monkeypatch.setattr("app.services.ai_stack_evidence_service._latest_writers_room_review", lambda: None)
    monkeypatch.setattr("app.services.ai_stack_evidence_service._latest_improvement_package", lambda: None)

    response = client.get("/api/v1/admin/ai-stack/release-readiness", headers=moderator_headers)
    assert response.status_code == 200
    payload = response.get_json()

    # Must not falsely claim ready
    assert payload["overall_status"] != "ready", (
        "Release readiness must not claim 'ready' when no improvement packages "
        "or writers-room reviews are present"
    )

    # The areas dict must exist and at least one area must report partial
    assert "areas" in payload, "Response must include an 'areas' breakdown"
    areas_by_name = {area["area"]: area["status"] for area in payload["areas"]}
    assert areas_by_name.get("story_runtime_cross_layer") == "partial"
    assert areas_by_name.get("writers_room_review_artifacts") == "partial"
    assert areas_by_name.get("writers_room_retrieval_evidence_surface") == "partial"
    assert areas_by_name.get("improvement_governance_evidence") == "partial"
    assert areas_by_name.get("writers_room_langgraph_orchestration_depth") == "partial"
    assert areas_by_name.get("runtime_turn_graph_contract") == "ready"
    assert "subsystem_maturity" in payload
