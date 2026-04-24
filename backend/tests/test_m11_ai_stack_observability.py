"""Milestone 11: trace continuity, governance evidence API, and failure visibility tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.observability.audit_log import log_world_engine_bridge, log_workflow_audit
from app.runtime.session_store import clear_registry as clear_runtime_session_registry
from app.services.ai_stack_closure_cockpit_parsing import G9B_ATTEMPT_RECORD_PATH, read_audit_json as closure_read_audit_json
from app.services.game_service import GameServiceError


@pytest.fixture(autouse=True)
def _isolate_runtime_session_store():
    """Prevent cross-test runtime-session bleed in this module."""
    clear_runtime_session_registry()
    yield
    clear_runtime_session_registry()


def test_admin_session_evidence_returns_runtime_bundle(client, moderator_headers, monkeypatch):
    create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
    assert create_resp.status_code == 201
    session_id = create_resp.get_json()["session_id"]

    monkeypatch.setattr(
        "app.services.game_service.get_story_state",
        lambda *_a, **_k: {"session_id": "we-x", "turn_counter": 0},
    )
    monkeypatch.setattr(
        "app.services.game_service.get_story_diagnostics",
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
            "authoritative_history_tail": [
                {
                    "turn_number": 1,
                    "trace_id": "t-committed",
                    "narrative_commit": {"allowed": False, "commit_reason_code": "no_scene_proposal"},
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
    xc = data.get("cross_layer_classifiers") or {}
    assert xc.get("last_turn_diagnostics_available") is True
    assert xc.get("graph_execution_posture") == "primary_graph_path"
    assert xc.get("runtime_retrieval_evidence_tier") == "weak"
    assert xc.get("tool_influenced_last_turn") is True
    rm = data.get("reproducibility_metadata") or {}
    assert "retrieval_index_version" in rm


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
        "app.services.game_service.get_story_state",
        lambda *_a, **_k: {"session_id": "we-y", "turn_counter": 1},
    )
    monkeypatch.setattr(
        "app.services.game_service.get_story_diagnostics",
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
            "generated_at": "2026-04-04T12:00:00+00:00",
            "review_status": "pending_governance_review",
            "recommendation_summary": "promote",
            "evaluation": {"comparison": {"quality_heuristic_delta": 0.1}},
            "evidence_strength_map": {
                "retrieval_context": "moderate",
                "transcript_tool_readback": "moderate",
                "governance_review_bundle": "moderate",
            },
            "evidence_bundle": {
                "comparison": {"quality_heuristic_delta": 0.1},
                "retrieval_source_paths": ["modules/a.md"],
                "transcript_evidence": {"run_id": "run-1"},
                "governance_review_bundle_id": "rb-1",
            },
            "workflow_stages": [
                {"id": "governance_review_bundle", "loop_stage": "bounded_proposal_generation"}
            ],
            "semantic_compliance_validation": {"status": "pass"},
            "improvement_loop_progress": [],
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
    wr_rr = payload["repaired_layer_signals"]["writers_room"]["review_readiness"]
    assert wr_rr["retrieval_evidence_sufficient_for_review"] is True
    assert wr_rr["retrieval_evidence_tier"] == "moderate"
    assert payload["repaired_layer_signals"]["writers_room"]["review_bundle_id"] == "b1"
    assert payload["repaired_layer_signals"]["improvement"]["package_id"] == "pkg_1"
    inf = payload["repaired_layer_signals"]["improvement"]["evidence_influence"]
    assert inf["retrieval_source_path_count"] == 1
    assert inf["has_transcript_evidence"] is True
    assert inf["has_governance_review_bundle"] is True
    assert inf["evidence_strength_map"]["retrieval_context"] == "moderate"
    assert inf["governance_pending_review"] is True
    assert inf["distinct_from_publishable_recommendation"] is True
    assert inf["governance_terminal_accepted"] is False
    assert "governance_review_bundle" in inf["workflow_stage_ids"]
    assert inf.get("improvement_loop_stages") == ["bounded_proposal_generation"]
    assert inf.get("semantic_compliance_status") == "pass"
    assert inf.get("improvement_loop_progress_len") == 0
    et = payload.get("execution_truth") or {}
    assert et.get("last_turn_graph_mode", {}).get("graph_path_summary") == "primary_invoke_langchain_only"
    assert et.get("tool_influence", {}).get("material_influence") is True
    assert et.get("retrieval_influence", {}).get("evidence_tier") == "moderate"
    assert et.get("retrieval_influence", {}).get("retrieval_trace_schema_version") == "retrieval_closure_v1"


def test_session_evidence_surfaces_degraded_execution_health(client, moderator_headers, monkeypatch):
    """Degraded graph paths must appear in execution_truth and degraded_path_signals."""
    create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
    session_id = create_resp.get_json()["session_id"]

    monkeypatch.setattr(
        "app.services.game_service.get_story_state",
        lambda *_a, **_k: {"session_id": "we-z", "turn_counter": 1},
    )
    monkeypatch.setattr(
        "app.services.game_service.get_story_diagnostics",
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
    xc = payload.get("cross_layer_classifiers") or {}
    assert xc.get("graph_execution_posture") == "fallback_or_alternate_path"
    assert "fallback_path_taken" in (xc.get("active_degradation_markers") or [])


def test_session_evidence_empty_diagnostics_surfaces_no_turn_cross_layer(client, moderator_headers, monkeypatch):
    """Empty diagnostics must not imply a healthy last-turn graph or retrieval tier."""
    create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
    session_id = create_resp.get_json()["session_id"]
    monkeypatch.setattr(
        "app.services.game_service.get_story_state",
        lambda *_a, **_k: {"session_id": "we-empty", "turn_counter": 0},
    )
    monkeypatch.setattr(
        "app.services.game_service.get_story_diagnostics",
        lambda *_a, **_k: {"diagnostics": [], "committed_state": {"current_scene_id": "s0", "turn_counter": 0}},
    )
    from app.runtime.session_store import get_session as get_runtime_session

    runtime_session = get_runtime_session(session_id)
    runtime_session.current_runtime_state.metadata["world_engine_story_session_id"] = "we-empty"
    monkeypatch.setattr("app.services.ai_stack_evidence_service._latest_writers_room_review", lambda: None)
    monkeypatch.setattr("app.services.ai_stack_evidence_service._latest_improvement_package", lambda: None)

    response = client.get(
        f"/api/v1/admin/ai-stack/session-evidence/{session_id}",
        headers=moderator_headers,
    )
    assert response.status_code == 200
    payload = response.get_json()
    xc = payload.get("cross_layer_classifiers") or {}
    assert xc.get("last_turn_diagnostics_available") is False
    assert xc.get("runtime_retrieval_evidence_tier") == "no_turn_diagnostics"
    assert xc.get("graph_execution_posture") == "no_turn_diagnostics"


def test_latest_improvement_package_selects_newest_generated_at(monkeypatch):
    from app.services import ai_stack_evidence_service as evidence_svc

    packages = [
        {"package_id": "older", "generated_at": "2026-01-01T00:00:00+00:00"},
        {"package_id": "newer", "generated_at": "2026-06-15T08:30:00+00:00"},
    ]
    monkeypatch.setattr(evidence_svc, "list_recommendation_packages", lambda: packages)
    latest = evidence_svc._latest_improvement_package()
    assert latest is not None
    assert latest["package_id"] == "newer"


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
    areas_by_name = {area["gate_id"]: area["status"] for area in payload["areas"]}
    assert areas_by_name.get("story_runtime_cross_layer") == "partial"
    assert areas_by_name.get("writers_room_review_artifacts") == "partial"
    assert areas_by_name.get("writers_room_retrieval_evidence_surface") == "partial"
    assert areas_by_name.get("improvement_governance_evidence") == "partial"
    assert areas_by_name.get("improvement_retrieval_evidence_backing") == "partial"
    assert areas_by_name.get("writers_room_langgraph_orchestration_depth") == "partial"
    assert areas_by_name.get("runtime_turn_graph_contract") == "closed"
    assert areas_by_name.get("retrieval_subsystem_compact_traces") == "closed"
    rsum = payload.get("retrieval_readiness_summary") or {}
    assert "strengths" in rsum and "known_degradations" in rsum
    assert "subsystem_maturity" in payload
    assert "decision_support" in payload
    assert payload["decision_support"]["latest_writers_room_retrieval_tier"] is None
    assert "known_environment_sensitivities" in payload


def test_release_readiness_writers_room_weak_retrieval_is_not_ready(client, moderator_headers, monkeypatch):
    """Presence of retrieval_trace with none/weak tier must not count as review-grade retrieval surface."""
    monkeypatch.setattr(
        "app.services.ai_stack_evidence_service._latest_writers_room_review",
        lambda: {
            "review_id": "r1",
            "review_state": {"status": "pending"},
            "retrieval_trace": {"evidence_tier": "weak", "evidence_strength": "weak"},
        },
    )
    monkeypatch.setattr("app.services.ai_stack_evidence_service._latest_improvement_package", lambda: None)

    response = client.get("/api/v1/admin/ai-stack/release-readiness", headers=moderator_headers)
    assert response.status_code == 200
    payload = response.get_json()
    areas_by_name = {a["gate_id"]: a for a in payload["areas"]}
    wr = areas_by_name["writers_room_retrieval_evidence_surface"]
    assert wr["status"] == "partial"
    assert "weak" in (wr.get("evidence_posture") or "")
    assert payload["decision_support"]["writers_room_review_ready_for_retrieval_graded_review"] is False


def test_release_readiness_improvement_weak_retrieval_backing_is_partial(client, moderator_headers, monkeypatch):
    monkeypatch.setattr("app.services.ai_stack_evidence_service._latest_writers_room_review", lambda: None)
    monkeypatch.setattr(
        "app.services.ai_stack_evidence_service._latest_improvement_package",
        lambda: {
            "package_id": "pkg_weak",
            "generated_at": "2026-04-04T10:00:00+00:00",
            "evidence_bundle": {"comparison": {"ok": True}, "governance_review_bundle_id": "rb-1"},
            "evidence_strength_map": {
                "retrieval_context": "none",
                "transcript_tool_readback": "low",
                "governance_review_bundle": "moderate",
            },
        },
    )

    response = client.get("/api/v1/admin/ai-stack/release-readiness", headers=moderator_headers)
    assert response.status_code == 200
    payload = response.get_json()
    areas_by_name = {a["gate_id"]: a for a in payload["areas"]}
    assert areas_by_name["improvement_governance_evidence"]["status"] == "closed"
    backing = areas_by_name["improvement_retrieval_evidence_backing"]
    assert backing["status"] == "partial"
    assert backing.get("evidence_posture") == "weak_retrieval_backing"
    assert payload["decision_support"]["latest_improvement_retrieval_context_class"] == "none"
    assert payload["decision_support"]["improvement_review_ready_for_retrieval_graded_review"] is False


def test_closure_cockpit_endpoint_returns_normalized_gate_truth(client, moderator_headers, monkeypatch):
    """Contract test: pin G9B attempt JSON so CI does not depend on fork-evolved evidence files."""
    g9b_fixture = {
        "audit_run_id": "m11_closure_cockpit_contract",
        "level_b_attempt_status": "failed_insufficient_independence",
        "reason_codes": ["independence_evidence_insufficient_for_level_b"],
        "independence_classification_primary": "insufficient_process_separation",
    }

    def _read_audit_json(path):
        if Path(path).resolve() == G9B_ATTEMPT_RECORD_PATH.resolve():
            return g9b_fixture
        return closure_read_audit_json(path)

    monkeypatch.setattr("app.services.ai_stack_closure_cockpit_service.read_audit_json", _read_audit_json)

    response = client.get("/api/v1/admin/ai-stack/closure-cockpit", headers=moderator_headers)
    assert response.status_code == 200
    payload = response.get_json()

    assert payload.get("canonical_model") == "ai_stack_closure_cockpit_v1"
    assert "aggregate_summary" in payload
    assert "gate_stack" in payload
    assert "current_blockers" in payload
    assert "g9_g9b_g10_focus" in payload
    assert "source_refs" in payload

    gate_ids = [gate.get("gate_id") for gate in payload.get("gate_stack", [])]
    assert gate_ids == ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G9B", "G10"]

    agg = payload.get("aggregate_summary") or {}
    assert "level_a_status" in agg
    assert "level_b_status" in agg
    assert "key_blocker_summary" in agg
    assert "authoritative_reference" in agg

    blockers = payload.get("current_blockers") or {}
    assert "repo_local_resolved" in blockers
    assert "evidential_or_external" in blockers
    assert blockers.get("decisive_blocker_id") == "g9b_independence"
    evidential = blockers.get("evidential_or_external") or []
    assert len(evidential) == 1
    assert evidential[0].get("id") == "g9b_independence"

    focus = payload.get("g9_g9b_g10_focus") or {}
    assert "anti_misread_statement" in focus
    assert (focus.get("g9b_independence") or {}).get("level_b_attempt_status") == "failed_insufficient_independence"
