"""Focused tests for Inspector Suite M1 canonical turn projection."""

from __future__ import annotations

from app.contracts.inspector_turn_projection import (
    INSPECTOR_COMPARISON_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_COVERAGE_HEALTH_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_PROVENANCE_RAW_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_REQUIRED_SECTION_KEYS,
    INSPECTOR_TIMELINE_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_TURN_PROJECTION_SCHEMA_VERSION,
    build_inspector_turn_projection_root,
    make_unavailable_section,
)
from app.services.inspector_projection_service import (
    build_inspector_comparison_projection,
    build_inspector_coverage_health_projection,
    build_inspector_provenance_raw_projection,
    build_inspector_timeline_projection,
)
from app.services.inspector_turn_projection_service import build_inspector_turn_projection


def _bundle_with_turn() -> dict:
    return {
        "trace_id": "trace-123",
        "backend_session_id": "backend-sid",
        "module_id": "god_of_carnage",
        "current_scene_id": "s1",
        "turn_counter_backend": 2,
        "world_engine_story_session_id": "we-sid",
        "world_engine_state": {"session_id": "we-sid", "turn_counter": 2},
        "world_engine_diagnostics": {
            "diagnostics": [
                {
                    "turn_number": 2,
                    "trace_id": "trace-turn-2",
                    "raw_input": "Hello?",
                    "interpreted_input": {"signals": ["probe"]},
                    "retrieval": {"status": "ok", "hit_count": 2},
                    "model_route": {
                        "route_mode": "primary",
                        "route_reason_code": "policy_ok",
                        "fallback_chain": [],
                        "fallback_stage_reached": None,
                        "generation": {"success": True, "fallback_used": False},
                    },
                    "graph": {
                        "graph_name": "wos_runtime_turn_graph",
                        "graph_version": "v-test",
                        "nodes_executed": ["input_interpretation", "routing", "validation"],
                        "node_outcomes": {"input_interpretation": "ok", "routing": "ok", "validation": "ok"},
                        "execution_health": "healthy",
                        "fallback_path_taken": False,
                    },
                    "validation_outcome": {
                        "status": "rejected",
                        "reason": "dramatic_effect_reject_unknown",
                        "validator_lane": "goc_rule_engine_v1",
                        "dramatic_effect_weak_signal": False,
                        "dramatic_effect_gate_outcome": {
                            "gate_result": "rejected_scene_function_mismatch",
                            "dominant_rejection_category": "scene_mismatch",
                            "rejection_reasons": ["scene_function_mismatch"],
                            "effect_rationale_codes": ["scene_function_mismatch_signal"],
                            "supports_scene_function": False,
                            "continues_or_changes_pressure": True,
                            "character_plausibility_posture": "uncertain",
                            "continuity_support_posture": "weak",
                            "empty_fluency_risk": "moderate",
                            "legacy_fallback_used": True,
                            "diagnostic_trace": [{"code": "gate_eval_complete", "detail": "ok"}],
                        },
                    },
                    "committed_result": {"commit_applied": False, "committed_effects": []},
                    "selected_scene_function": "establish_pressure",
                    "visible_output_bundle": {"gm_narration": ["x"]},
                    "diagnostics_refs": [],
                    "experiment_preview": False,
                }
            ]
        },
        "execution_truth": {"last_turn_graph_mode": {"execution_health": "healthy"}},
        "cross_layer_classifiers": {"graph_execution_posture": "primary_graph_path"},
        "bridge_errors": [],
        "last_turn_repro_metadata": {
            "graph_path_summary": "primary_invoke_langchain_only",
            "adapter_invocation_mode": "langchain_structured_primary",
        },
        "degraded_path_signals": [],
    }


def _bundle_with_two_turns() -> dict:
    bundle = _bundle_with_turn()
    rows = bundle["world_engine_diagnostics"]["diagnostics"]
    rows.append(
                {
            "turn_number": 3,
            "trace_id": "trace-turn-3",
            "raw_input": "Next",
            "interpreted_input": {},
            "retrieval": {"status": "ok", "hit_count": 1},
            "model_route": {
                "route_mode": "fallback",
                "route_reason_code": "safety_guardrail",
                "fallback_chain": ["model_fallback"],
                "fallback_stage_reached": "model_fallback",
                "generation": {"success": True, "fallback_used": True},
            },
            "graph": {
                "graph_name": "wos_runtime_turn_graph",
                "graph_version": "v-test",
                "nodes_executed": ["input_interpretation", "routing", "validation"],
                "node_outcomes": {"input_interpretation": "ok", "routing": "ok", "validation": "ok"},
                "execution_health": "model_fallback",
                "fallback_path_taken": True,
            },
            "validation_outcome": {
                "status": "approved",
                "reason": "dramatic_effect_pass",
                "validator_lane": "goc_rule_engine_v1",
                "dramatic_effect_weak_signal": False,
                "dramatic_effect_gate_outcome": {
                    "gate_result": "accepted",
                    "dominant_rejection_category": None,
                    "rejection_reasons": [],
                    "effect_rationale_codes": [],
                    "supports_scene_function": True,
                    "continues_or_changes_pressure": False,
                    "character_plausibility_posture": "plausible",
                    "continuity_support_posture": "adequate",
                    "empty_fluency_risk": "low",
                    "legacy_fallback_used": False,
                },
            },
            "committed_result": {"commit_applied": True, "committed_effects": [{"id": "effect-1"}]},
            "selected_scene_function": "escalate_pressure",
            "visible_output_bundle": {"gm_narration": ["y"]},
            "diagnostics_refs": [],
            "experiment_preview": False,
        }
    )
    return bundle


def test_contract_root_serializes_required_sections_deterministically():
    sections = {}
    payload = build_inspector_turn_projection_root(
        trace_id="trace-x",
        backend_session_id="backend-1",
        world_engine_story_session_id="we-1",
        projection_status="partial",
        sections=sections,
        warnings=["missing"],
        raw_evidence_refs={"source": "x"},
    )
    assert payload["schema_version"] == INSPECTOR_TURN_PROJECTION_SCHEMA_VERSION
    assert payload["projection_status"] == "partial"
    for key in INSPECTOR_REQUIRED_SECTION_KEYS:
        assert key in payload
        assert payload[key]["status"] == "unavailable"


def test_service_marks_missing_turn_data_as_explicit_unavailable(monkeypatch):
    bundle = {
        "trace_id": "trace-missing",
        "backend_session_id": "backend-missing",
        "module_id": "god_of_carnage",
        "current_scene_id": "s0",
        "turn_counter_backend": 0,
        "world_engine_story_session_id": "we-missing",
        "world_engine_state": {"session_id": "we-missing", "turn_counter": 0},
        "world_engine_diagnostics": {"diagnostics": []},
        "execution_truth": None,
        "cross_layer_classifiers": {},
        "bridge_errors": [],
        "degraded_path_signals": [],
    }
    monkeypatch.setattr(
        "app.services.inspector_turn_projection_service.build_session_evidence_bundle",
        lambda **_kwargs: bundle,
    )
    payload = build_inspector_turn_projection(session_id="backend-missing", trace_id="trace-missing")
    assert payload["projection_status"] == "partial"
    assert payload["turn_identity"]["status"] == "unavailable"
    assert payload["planner_state_projection"]["status"] == "unavailable"
    assert payload["decision_trace_projection"]["status"] == "unavailable"
    assert payload["comparison_ready_fields"]["status"] == "supported"


def test_service_preserves_authority_fallback_provenance_and_rejection(monkeypatch):
    monkeypatch.setattr(
        "app.services.inspector_turn_projection_service.build_session_evidence_bundle",
        lambda **_kwargs: _bundle_with_turn(),
    )
    payload = build_inspector_turn_projection(session_id="backend-sid", trace_id="trace-123")
    assert payload["projection_status"] == "ok"

    authority = payload["authority_projection"]["data"]
    assert authority["authoritative_surface"] == "world_engine_session_commit_state"
    assert authority["commit_applied"] is False

    fallback = payload["fallback_projection"]["data"]
    assert fallback["fallback_path_taken"] is False
    assert fallback["legacy_fallback_used"] is True

    gate = payload["gate_projection"]
    assert gate["status"] == "supported"
    gdata = gate["data"]
    assert gdata["gate_result"] == "rejected_scene_function_mismatch"
    assert gdata["rejection_reasons"] == ["scene_function_mismatch"]
    assert gdata["effect_rationale_codes"] == ["scene_function_mismatch_signal"]
    assert gdata["empty_fluency_risk"] == "moderate"
    assert gdata["legacy_compatibility_summary"]["dominant_rejection_category"] == "scene_mismatch"

    dt = payload["decision_trace_projection"]["data"]
    assert "semantic_decision_flow" in dt
    stages = dt["semantic_decision_flow"]["stages"]
    assert any(s["id"] == "player_input" and s["presence"] == "present" for s in stages)
    assert "graph_execution_flow" in dt
    assert dt["graph_execution_flow"]["flow_nodes"] == ["input_interpretation", "routing", "validation"]

    provenance = payload["provenance_projection"]["data"]
    entries = provenance["entries"]
    fields = {entry["field"] for entry in entries}
    assert "commit_applied" in fields
    assert "execution_health" in fields
    assert "legacy_fallback_used" in fields
    assert "effect_rationale_codes" in fields
    assert "dramatic_effect_diagnostic_trace" in fields


def test_endpoint_returns_canonical_projection_shape(client, moderator_headers, monkeypatch):
    create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
    assert create_resp.status_code == 201
    backend_session_id = create_resp.get_json()["session_id"]

    monkeypatch.setattr(
        "app.services.inspector_turn_projection_service.build_session_evidence_bundle",
        lambda **_kwargs: {**_bundle_with_turn(), "backend_session_id": backend_session_id},
    )

    response = client.get(
        f"/api/v1/admin/ai-stack/inspector/turn/{backend_session_id}",
        headers=moderator_headers,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["schema_version"] == INSPECTOR_TURN_PROJECTION_SCHEMA_VERSION
    for key in INSPECTOR_REQUIRED_SECTION_KEYS:
        assert key in payload
        assert "status" in payload[key]
    assert "raw_evidence" not in payload


def test_endpoint_raw_mode_returns_expanded_evidence(client, moderator_headers, monkeypatch):
    create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
    assert create_resp.status_code == 201
    backend_session_id = create_resp.get_json()["session_id"]
    monkeypatch.setattr(
        "app.services.inspector_turn_projection_service.build_session_evidence_bundle",
        lambda **_kwargs: {**_bundle_with_turn(), "backend_session_id": backend_session_id},
    )
    response = client.get(
        f"/api/v1/admin/ai-stack/inspector/turn/{backend_session_id}?mode=raw",
        headers=moderator_headers,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert "raw_evidence" in payload
    assert "world_engine_diagnostics" in payload["raw_evidence"]


def test_endpoint_has_no_mutation_semantics(client, moderator_headers):
    response = client.post(
        "/api/v1/admin/ai-stack/inspector/turn/nonexistent",
        headers=moderator_headers,
        json={"mutate": True},
    )
    assert response.status_code == 405


def test_missing_section_template_uses_unavailable_default():
    section = make_unavailable_section(reason="missing_data")
    assert section["status"] == "unavailable"
    assert section["unsupported_reason"] is None
    assert section["unavailable_reason"] == "missing_data"


def test_timeline_includes_semantic_planner_columns(monkeypatch):
    monkeypatch.setattr(
        "app.services.inspector_projection_service.build_session_evidence_bundle",
        lambda **_kwargs: _bundle_with_turn(),
    )
    payload = build_inspector_timeline_projection(session_id="backend-sid", trace_id="trace-123")
    turn0 = payload["timeline_projection"]["data"]["turns"][0]
    assert turn0["semantic_planner_support_level"] == "full_goc"
    assert turn0["gate_result"] == "rejected_scene_function_mismatch"


def test_timeline_projection_returns_multi_turn_rows(monkeypatch):
    monkeypatch.setattr(
        "app.services.inspector_projection_service.build_session_evidence_bundle",
        lambda **_kwargs: _bundle_with_two_turns(),
    )
    payload = build_inspector_timeline_projection(session_id="backend-sid", trace_id="trace-123")
    assert payload["schema_version"] == INSPECTOR_TIMELINE_PROJECTION_SCHEMA_VERSION
    section = payload["timeline_projection"]
    assert section["status"] == "supported"
    turns = section["data"]["turns"]
    assert len(turns) == 2
    assert turns[0]["turn_number"] == 2
    assert turns[1]["turn_number"] == 3


def test_comparison_projection_requires_two_turns(monkeypatch):
    monkeypatch.setattr(
        "app.services.inspector_projection_service.build_session_evidence_bundle",
        lambda **_kwargs: _bundle_with_turn(),
    )
    payload = build_inspector_comparison_projection(session_id="backend-sid", trace_id="trace-123")
    assert payload["schema_version"] == INSPECTOR_COMPARISON_PROJECTION_SCHEMA_VERSION
    section = payload["comparison_projection"]
    assert section["status"] == "unavailable"
    assert section["unavailable_reason"] == "comparison_requires_at_least_two_turns"


def test_comparison_projection_includes_turn_to_turn_deltas(monkeypatch):
    monkeypatch.setattr(
        "app.services.inspector_projection_service.build_session_evidence_bundle",
        lambda **_kwargs: _bundle_with_two_turns(),
    )
    payload = build_inspector_comparison_projection(session_id="backend-sid", trace_id="trace-123")
    section = payload["comparison_projection"]
    assert section["status"] == "supported"
    assert "turn_to_turn_within_session" in section["data"]["supported_dimensions"]
    assert "planner_gate_posture_delta" in section["data"]["supported_dimensions"]
    assert len(section["data"]["comparisons"]) == 1
    delta = section["data"]["comparisons"][0]
    assert delta["from_turn_number"] == 2
    assert delta["to_turn_number"] == 3


def test_coverage_health_projection_reports_required_metrics(monkeypatch):
    monkeypatch.setattr(
        "app.services.inspector_projection_service.build_session_evidence_bundle",
        lambda **_kwargs: _bundle_with_two_turns(),
    )
    payload = build_inspector_coverage_health_projection(session_id="backend-sid", trace_id="trace-123")
    assert payload["schema_version"] == INSPECTOR_COVERAGE_HEALTH_PROJECTION_SCHEMA_VERSION
    section = payload["coverage_health_projection"]
    assert section["status"] == "supported"
    dist = section["data"]["distribution"]
    assert "gate_outcome_distribution" in dist
    assert "validation_outcome_distribution" in dist
    assert "unsupported_unavailable_frequency" in dist
    assert "effect_and_rejection_rationale_distribution" in dist
    assert "empty_fluency_risk_distribution" in dist
    fallback = section["data"]["metrics"]["fallback_frequency"]
    assert fallback["total_turns"] == 2
    assert fallback["fallback_turns"] == 1


def test_provenance_raw_projection_respects_mode(monkeypatch):
    monkeypatch.setattr(
        "app.services.inspector_projection_service.build_session_evidence_bundle",
        lambda **_kwargs: _bundle_with_two_turns(),
    )
    canonical = build_inspector_provenance_raw_projection(
        session_id="backend-sid",
        trace_id="trace-123",
        mode="canonical",
    )
    assert canonical["schema_version"] == INSPECTOR_PROVENANCE_RAW_PROJECTION_SCHEMA_VERSION
    assert canonical["provenance_raw_projection"]["status"] == "supported"
    prov_fields = {e["field"] for e in canonical["provenance_raw_projection"]["data"]["entries"]}
    assert "semantic_planner_support_level" in prov_fields
    assert "effect_rationale_codes" in prov_fields
    assert canonical["raw_mode_loaded"] is False
    assert "raw_evidence" not in canonical

    raw = build_inspector_provenance_raw_projection(
        session_id="backend-sid",
        trace_id="trace-123",
        mode="raw",
    )
    assert raw["raw_mode_loaded"] is True
    assert "raw_evidence" in raw


def test_new_inspector_projection_endpoints_are_read_only(client, moderator_headers):
    create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
    assert create_resp.status_code == 201
    backend_session_id = create_resp.get_json()["session_id"]
    for path in (
        f"/api/v1/admin/ai-stack/inspector/timeline/{backend_session_id}",
        f"/api/v1/admin/ai-stack/inspector/comparison/{backend_session_id}",
        f"/api/v1/admin/ai-stack/inspector/coverage-health/{backend_session_id}",
        f"/api/v1/admin/ai-stack/inspector/provenance-raw/{backend_session_id}",
    ):
        response = client.post(path, headers=moderator_headers, json={"mutate": True})
        assert response.status_code == 405


def test_new_inspector_projection_endpoints_return_payload(client, moderator_headers, monkeypatch):
    create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
    assert create_resp.status_code == 201
    backend_session_id = create_resp.get_json()["session_id"]
    monkeypatch.setattr(
        "app.services.inspector_projection_service.build_session_evidence_bundle",
        lambda **_kwargs: {**_bundle_with_two_turns(), "backend_session_id": backend_session_id},
    )

    timeline = client.get(
        f"/api/v1/admin/ai-stack/inspector/timeline/{backend_session_id}",
        headers=moderator_headers,
    )
    assert timeline.status_code == 200
    assert timeline.get_json()["timeline_projection"]["status"] in {"supported", "unavailable"}

    comparison = client.get(
        f"/api/v1/admin/ai-stack/inspector/comparison/{backend_session_id}",
        headers=moderator_headers,
    )
    assert comparison.status_code == 200
    assert "comparison_projection" in comparison.get_json()

    coverage = client.get(
        f"/api/v1/admin/ai-stack/inspector/coverage-health/{backend_session_id}",
        headers=moderator_headers,
    )
    assert coverage.status_code == 200
    assert "coverage_health_projection" in coverage.get_json()

    provenance = client.get(
        f"/api/v1/admin/ai-stack/inspector/provenance-raw/{backend_session_id}?mode=raw",
        headers=moderator_headers,
    )
    assert provenance.status_code == 200
    pjson = provenance.get_json()
    assert "provenance_raw_projection" in pjson
    assert pjson["raw_mode_loaded"] is True
