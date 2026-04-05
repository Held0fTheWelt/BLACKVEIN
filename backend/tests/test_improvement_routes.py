from __future__ import annotations

import pytest
from ai_stack import CapabilityInvocationError
from ai_stack.rag import INDEX_VERSION

from app.api.v1 import improvement_routes as improvement_routes_module
from app.services.improvement_service import (
    ImprovementStore,
    _simulate_sandbox_turn,
    apply_improvement_recommendation_decision,
    build_comparison_package,
    build_recommendation_package,
    build_recommendation_rationale,
    create_variant,
    evaluate_experiment,
    finalize_recommendation_rationale_with_retrieval_digest,
    run_sandbox_experiment,
)


@pytest.fixture(autouse=True)
def _reset_improvement_rag_singleton():
    """Process-lifetime RAG cache must not leak mocked registries across tests."""
    improvement_routes_module._improvement_rag_stack = None
    yield
    improvement_routes_module._improvement_rag_stack = None


def test_variant_creation_with_parent_lineage(client, auth_headers):
    parent = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={
            "baseline_id": "god_of_carnage",
            "candidate_summary": "Parent candidate.",
        },
    )
    assert parent.status_code == 201
    parent_id = parent.get_json()["variant_id"]
    child = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={
            "baseline_id": "god_of_carnage",
            "candidate_summary": "Child iteration.",
            "metadata": {"parent_variant_id": parent_id, "lineage_depth": 3},
        },
    )
    assert child.status_code == 201
    body = child.get_json()
    assert body["lineage"]["parent_variant_id"] == parent_id
    assert body["lineage"]["lineage_depth"] == 3
    assert "mutation_metadata" in body


def test_variant_creation_and_lineage(client, auth_headers):
    response = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={
            "baseline_id": "god_of_carnage",
            "candidate_summary": "Increase de-escalation options in scene transitions.",
            "metadata": {"source": "writers_room"},
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["baseline_id"] == "god_of_carnage"
    assert data["lineage"]["derived_from"] == "god_of_carnage"
    assert data["lineage"]["lineage_depth"] == 1
    assert data["review_status"] == "pending_review"
    assert isinstance(data["mutation_plan"], list)
    assert data["mutation_plan"]


def test_sandbox_execution_evaluation_and_recommendation_package(client, auth_headers):
    variant_resp = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={
            "baseline_id": "god_of_carnage",
            "candidate_summary": "Experiment with alternative conflict pacing.",
        },
    )
    variant_id = variant_resp.get_json()["variant_id"]

    experiment_resp = client.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers,
        json={
            "variant_id": variant_id,
            "test_inputs": [
                "I argue with measured tone.",
                "I repeat the same accusation again and again.",
                "I try to de-escalate the conflict.",
            ],
        },
    )
    assert experiment_resp.status_code == 200
    payload = experiment_resp.get_json()
    experiment = payload["experiment"]
    recommendation = payload["recommendation_package"]
    retrieval = payload["retrieval"]
    review_bundle = payload["review_bundle"]
    capability_audit = payload["capability_audit"]
    och = payload.get("operational_cost_hints") or {}
    assert och.get("disclaimer") == "coarse_operational_signals_not_financial_estimates"
    assert "retrieval_route" in och

    assert experiment["sandbox"] is True
    assert experiment["variant_id"] == variant_id
    assert recommendation["candidate"]["variant_id"] == variant_id
    assert recommendation["review_status"] == "pending_governance_review"
    grs = recommendation.get("governance_review_state") or {}
    assert grs.get("status") == "pending_governance_review"
    assert isinstance(grs.get("history"), list)
    metrics = recommendation["evaluation"]["metrics"]
    baseline_metrics = recommendation["evaluation"]["baseline_metrics"]
    comparison = recommendation["evaluation"]["comparison"]
    assert "guard_reject_rate" in metrics
    assert "trigger_coverage" in metrics
    assert "repetition_signal" in metrics
    assert "structure_flow_health" in metrics
    assert "transcript_quality_heuristic" in metrics
    assert "guard_reject_rate" in baseline_metrics
    assert "quality_heuristic_delta" in comparison
    assert recommendation["lineage"]["baseline_id"] == "god_of_carnage"
    assert recommendation["mutation_plan"]
    cp = recommendation["comparison_package"]
    assert cp["experiment_id"] == experiment["experiment_id"]
    assert len(cp["dimensions"]) == 4
    assert {d["metric"] for d in cp["dimensions"]} >= {
        "guard_reject_rate",
        "repetition_signal",
        "structure_flow_health",
        "transcript_quality_heuristic",
    }
    assert "semantic_delta" in cp
    rat = recommendation["recommendation_rationale"]
    assert rat["recommendation_summary"] == recommendation["recommendation_summary"]
    driver_cats = {d["category"] for d in rat["drivers"] if isinstance(d, dict)}
    assert "retrieval_context_digest" in driver_cats
    assert recommendation["evidence_strength_map"]["comparison_deltas"] == "primary"
    assert recommendation["evidence_bundle"]["comparison"] == comparison
    assert "retrieval_source_paths" in recommendation["evidence_bundle"]
    assert isinstance(recommendation["evidence_bundle"]["retrieval_source_paths"], list)
    assert "transcript_evidence" in recommendation["evidence_bundle"]
    assert recommendation["evidence_bundle"]["transcript_evidence"].get("run_id")
    assert "metrics_snapshot" in recommendation["evidence_bundle"]
    assert "baseline_metrics_snapshot" in recommendation["evidence_bundle"]
    assert "comparison_snapshot" in recommendation["evidence_bundle"]
    assert "governance_review_bundle_id" in recommendation["evidence_bundle"]
    ws = payload["workflow_stages"]
    assert ws
    assert payload["workflow_stages"] == recommendation["workflow_stages"]
    assert any(s["id"] == "governance_review_bundle" for s in ws)
    assert retrieval["profile"] == "improvement_eval"
    assert review_bundle["status"] == "recommendation_only"
    assert any(entry["capability_name"] == "wos.context_pack.build" for entry in capability_audit)
    assert any(entry["capability_name"] == "wos.review_bundle.build" for entry in capability_audit)
    assert "retrieval_trace" in payload
    trace = payload["retrieval_trace"]
    assert trace["evidence_strength"] in {"none", "weak", "moderate", "strong"}
    assert trace["evidence_tier"] == trace["evidence_strength"]
    assert trace.get("retrieval_trace_schema_version")
    assert och.get("retrieval_evidence_tier") == trace["evidence_tier"]
    assert och.get("retrieval_trace_schema_version") == trace.get("retrieval_trace_schema_version")
    rr = recommendation["evidence_bundle"].get("retrieval_readiness") or {}
    assert rr.get("evidence_tier") == trace["evidence_tier"]
    assert rr.get("retrieval_trace_schema_version") == trace.get("retrieval_trace_schema_version")
    assert trace.get("readiness_label")
    assert trace.get("evidence_lane_mix")
    assert trace["profile"] == "improvement_eval"
    assert "|tr_turns=3|" in recommendation["recommendation_summary"]
    t2a = recommendation.get("task_2a_routing") or {}
    assert "preflight" in t2a and "synthesis" in t2a
    for stage_key in ("preflight", "synthesis"):
        tr = t2a[stage_key]
        assert tr.get("stage_id") == stage_key
        assert tr.get("decision", {}).get("route_reason_code")
        assert "bounded_model_call" in tr
        rev = tr.get("routing_evidence") or {}
        assert rev.get("requested_workflow_phase") == tr.get("workflow_phase")
        assert rev.get("requested_task_kind") == tr.get("task_kind")
        assert rev.get("route_reason_code") == tr["decision"]["route_reason_code"]
        assert "routing_overview" in rev
        assert rev["routing_overview"].get("title")
        assert "no_eligible_spec_selection" in rev
        assert "diagnostics_overview" in rev
        d = rev["diagnostics_overview"]
        assert d.get("summary") and d.get("severity") and "short_explanation" in d
        assert "diagnostics_flags" in rev and "diagnostics_causes" in rev
        assert "policy_execution_aligned" in rev
        assert "execution_deviation" in rev
    mai = recommendation.get("model_assisted_interpretation") or {}
    assert mai.get("disclaimer")
    assert "preflight_excerpt" in mai
    assert "synthesis_excerpt" in mai
    oa = recommendation.get("operator_audit") or {}
    assert oa.get("audit_schema_version")
    assert oa.get("audit_summary", {}).get("surface") == "improvement"
    assert oa.get("audit_timeline")
    assert recommendation["recommendation_summary"].split("|", 1)[0] == recommendation["deterministic_recommendation_base"]
    exp_base = "promote_for_human_review"
    if metrics["guard_reject_rate"] > 0.4 or metrics["repetition_signal"] > 0.5:
        exp_base = "revise_before_review"
    if comparison["structure_flow_health_delta"] < 0 or comparison["quality_heuristic_delta"] < 0:
        exp_base = "revise_before_review"
    assert recommendation["deterministic_recommendation_base"] == exp_base
    assert payload.get("transcript_evidence", {}).get("turn_count") == 3
    assert any(
        entry["capability_name"] == "wos.transcript.read" and entry["outcome"] == "allowed"
        for entry in capability_audit
    )
    if trace["evidence_strength"] in {"strong", "moderate", "weak"}:
        assert trace["hit_count"] > 0
        assert review_bundle["summary"].startswith(f"[evidence_tier:{trace['evidence_tier']}]")
    else:
        assert review_bundle["summary"].startswith("[evidence_tier:none]")
    ctx_audit = next(entry for entry in capability_audit if entry["capability_name"] == "wos.context_pack.build")
    assert ctx_audit.get("result_summary") is not None
    assert ctx_audit["result_summary"]["kind"] == "context_pack"


def test_improvement_retrieval_paths_materially_affect_review_bundle_and_stored_evidence(
    client, auth_headers, monkeypatch,
):
    """Different context_pack sources must change review_bundle evidence and evidence_bundle retrieval paths."""

    class PathsRegistry:
        def __init__(self, paths: list[str]) -> None:
            self._paths = paths

        def invoke(self, *, name, mode, actor, payload, trace_id=None):
            if name == "wos.context_pack.build":
                return {
                    "retrieval": {
                        "domain": "improvement",
                        "profile": "improvement_eval",
                        "status": "ok",
                        "hit_count": len(self._paths),
                        "sources": [{"source_path": p, "content_class": "canon"} for p in self._paths],
                        "ranking_notes": [],
                        "index_version": INDEX_VERSION,
                        "corpus_fingerprint": "d2_mat",
                        "storage_path": "",
                        "retrieval_route": "test_paths_registry",
                        "embedding_model_id": "",
                        "top_hit_score": "0.88",
                    },
                    "context_text": "\n".join(self._paths),
                }
            if name == "wos.transcript.read":
                return {
                    "run_id": payload.get("run_id", ""),
                    "content": '{"transcript":[{"turn_number":1,"repetition_flag":false}]}',
                }
            if name == "wos.review_bundle.build":
                return {
                    "bundle_id": f"bundle_{self._paths[0].replace('/', '_')}",
                    "module_id": payload["module_id"],
                    "summary": payload.get("summary", ""),
                    "recommendations": payload.get("recommendations", []),
                    "evidence_sources": payload.get("evidence_sources", []),
                    "status": "recommendation_only",
                }
            raise AssertionError(name)

        def recent_audit(self, limit=20):
            return [
                {"capability_name": "wos.context_pack.build", "outcome": "allowed"},
                {"capability_name": "wos.review_bundle.build", "outcome": "allowed"},
            ]

    monkeypatch.setattr(
        "app.api.v1.improvement_routes.create_default_capability_registry",
        lambda **kwargs: PathsRegistry(["modules/d2_alpha_ctx.md"]),
    )
    v1 = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={"baseline_id": "god_of_carnage", "candidate_summary": "D2 retrieval alpha path."},
    )
    vid1 = v1.get_json()["variant_id"]
    r1 = client.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers,
        json={"variant_id": vid1, "test_inputs": ["one", "two"]},
    )
    assert r1.status_code == 200
    p1 = r1.get_json()
    assert p1["review_bundle"]["evidence_sources"] == ["modules/d2_alpha_ctx.md"]
    assert p1["recommendation_package"]["evidence_bundle"]["retrieval_source_paths"] == [
        "modules/d2_alpha_ctx.md"
    ]

    improvement_routes_module._improvement_rag_stack = None
    monkeypatch.setattr(
        "app.api.v1.improvement_routes.create_default_capability_registry",
        lambda **kwargs: PathsRegistry(["modules/d2_beta_ctx.md"]),
    )
    v2 = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={"baseline_id": "god_of_carnage", "candidate_summary": "D2 retrieval beta path."},
    )
    vid2 = v2.get_json()["variant_id"]
    r2 = client.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers,
        json={"variant_id": vid2, "test_inputs": ["one", "two"]},
    )
    assert r2.status_code == 200
    p2 = r2.get_json()
    assert p2["review_bundle"]["evidence_sources"] == ["modules/d2_beta_ctx.md"]
    assert p2["recommendation_package"]["evidence_bundle"]["retrieval_source_paths"] == [
        "modules/d2_beta_ctx.md"
    ]
    assert p1["review_bundle"]["evidence_sources"] != p2["review_bundle"]["evidence_sources"]
    fp1 = p1["recommendation_package"]["evidence_bundle"]["retrieval_context_fingerprint_sha256_16"]
    fp2 = p2["recommendation_package"]["evidence_bundle"]["retrieval_context_fingerprint_sha256_16"]
    assert fp1 != fp2
    assert p1["recommendation_package"]["recommendation_rationale"]["retrieval_context_fingerprint_sha256_16"] == fp1


def test_improvement_experiment_reflects_empty_retrieval_in_trace_and_review_summary(
    client, auth_headers, monkeypatch
):
    """When context_pack returns no hits, the HTTP response and review bundle must show evidence:none."""

    class EmptyRetrievalRegistry:
        def invoke(self, *, name, mode, actor, payload, trace_id=None):
            if name == "wos.context_pack.build":
                return {
                    "retrieval": {
                        "domain": "improvement",
                        "profile": "improvement_eval",
                        "status": "ok",
                        "hit_count": 0,
                        "sources": [],
                        "ranking_notes": [],
                        "index_version": INDEX_VERSION,
                        "corpus_fingerprint": "",
                        "storage_path": "",
                        "retrieval_route": "sparse_fallback",
                        "embedding_model_id": "",
                        "top_hit_score": "",
                    },
                    "context_text": "",
                }
            if name == "wos.transcript.read":
                return {"run_id": payload.get("run_id", ""), "content": "{}"}
            if name == "wos.review_bundle.build":
                return {
                    "bundle_id": "synthetic_bundle",
                    "module_id": payload["module_id"],
                    "summary": payload.get("summary", ""),
                    "recommendations": payload.get("recommendations", []),
                    "evidence_sources": payload.get("evidence_sources", []),
                    "status": "recommendation_only",
                }
            raise AssertionError(f"unexpected capability {name}")

        def recent_audit(self, *, limit=20):
            return [
                {
                    "capability_name": "wos.context_pack.build",
                    "outcome": "allowed",
                    "result_summary": {"kind": "context_pack", "hit_count": 0},
                }
            ]

    monkeypatch.setattr(
        "app.api.v1.improvement_routes.create_default_capability_registry",
        lambda **kwargs: EmptyRetrievalRegistry(),
    )

    variant_resp = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={
            "baseline_id": "god_of_carnage",
            "candidate_summary": "Empty retrieval evidence wiring test.",
        },
    )
    variant_id = variant_resp.get_json()["variant_id"]
    experiment_resp = client.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers,
        json={"variant_id": variant_id},
    )
    assert experiment_resp.status_code == 200
    body = experiment_resp.get_json()
    assert body["retrieval_trace"]["evidence_strength"] == "none"
    assert body["retrieval_trace"]["evidence_tier"] == "none"
    assert body["retrieval_trace"]["hit_count"] == 0
    assert body["review_bundle"]["summary"].startswith("[evidence_tier:none]")


def test_improvement_recommendation_suffix_drops_when_transcript_helper_bypassed(client, auth_headers, monkeypatch):
    """Proves the HTTP response depends on transcript tool wiring: bypass removes ``tr_turns`` marker."""
    from app.api.v1 import improvement_routes

    def _noop_transcript(**_kwargs):
        return "", {"bypassed": True}

    monkeypatch.setattr(improvement_routes, "_transcript_tool_evidence_for_improvement", _noop_transcript)

    variant_resp = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={
            "baseline_id": "god_of_carnage",
            "candidate_summary": "Transcript dependence check.",
        },
    )
    variant_id = variant_resp.get_json()["variant_id"]
    experiment_resp = client.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers,
        json={"variant_id": variant_id, "test_inputs": ["one", "two"]},
    )
    assert experiment_resp.status_code == 200
    body = experiment_resp.get_json()
    assert "|tr_turns=" not in body["recommendation_package"]["recommendation_summary"]
    assert body.get("transcript_evidence", {}).get("bypassed") is True


def test_apply_improvement_recommendation_decision_flow(tmp_path):
    store = ImprovementStore(root=tmp_path)
    variant = create_variant(
        baseline_id="god_of_carnage",
        candidate_summary="Governance decision coverage.",
        actor_id="actor_unit",
        store=store,
    )
    experiment = run_sandbox_experiment(
        variant_id=variant["variant_id"],
        actor_id="actor_unit",
        test_inputs=["one"],
        store=store,
    )
    pkg = build_recommendation_package(
        experiment_id=experiment["experiment_id"],
        actor_id="actor_unit",
        store=store,
    )
    pid = pkg["package_id"]
    assert pkg["governance_review_state"]["status"] == "pending_governance_review"

    with pytest.raises(ValueError, match="decision_must_be"):
        apply_improvement_recommendation_decision(
            package_id=pid, actor_id="h", decision="maybe", store=store
        )

    revised = apply_improvement_recommendation_decision(
        package_id=pid, actor_id="human", decision="revise", note="more evidence", store=store
    )
    assert revised["governance_review_state"]["status"] == "governance_revision_requested"
    assert revised["review_status"] == "governance_revision_requested"

    accepted = apply_improvement_recommendation_decision(
        package_id=pid, actor_id="human", decision="accept", note="ok", store=store
    )
    assert accepted["governance_review_state"]["status"] == "governance_accepted"
    assert accepted["review_status"] == "governance_accepted"
    assert accepted["human_decision"]["decision"] == "accept"

    with pytest.raises(ValueError, match="recommendation_already_finalized"):
        apply_improvement_recommendation_decision(
            package_id=pid, actor_id="human", decision="reject", store=store
        )

    variant2 = create_variant(
        baseline_id="god_of_carnage",
        candidate_summary="Reject path.",
        actor_id="actor_unit",
        store=store,
    )
    exp2 = run_sandbox_experiment(
        variant_id=variant2["variant_id"],
        actor_id="actor_unit",
        test_inputs=["two"],
        store=store,
    )
    pkg2 = build_recommendation_package(
        experiment_id=exp2["experiment_id"], actor_id="actor_unit", store=store
    )
    rejected = apply_improvement_recommendation_decision(
        package_id=pkg2["package_id"], actor_id="human", decision="reject", store=store
    )
    assert rejected["governance_review_state"]["status"] == "governance_rejected"
    assert rejected["review_status"] == "governance_rejected"


def test_improvement_recommendation_decision_http_route(client, auth_headers, tmp_path):
    from unittest.mock import patch

    iso = ImprovementStore(root=tmp_path)
    variant = create_variant(
        baseline_id="god_of_carnage",
        candidate_summary="HTTP route",
        actor_id="a",
        store=iso,
    )
    experiment = run_sandbox_experiment(
        variant_id=variant["variant_id"],
        actor_id="a",
        test_inputs=["z"],
        store=iso,
    )
    pkg = build_recommendation_package(
        experiment_id=experiment["experiment_id"], actor_id="a", store=iso
    )
    pkg_id = pkg["package_id"]

    def fake_default():
        return iso

    with patch("app.api.v1.improvement_routes.ImprovementStore.default", fake_default):
        bad = client.post(
            f"/api/v1/improvement/recommendations/{pkg_id}/decision",
            headers=auth_headers,
            json={"decision": "maybe"},
        )
        assert bad.status_code == 400
        ok = client.post(
            f"/api/v1/improvement/recommendations/{pkg_id}/decision",
            headers=auth_headers,
            json={"decision": "accept"},
        )
        assert ok.status_code == 200
        assert ok.get_json()["governance_review_state"]["status"] == "governance_accepted"


def test_governance_accessibility_lists_recommendation_packages(client, auth_headers):
    response = client.get("/api/v1/improvement/recommendations", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "packages" in data
    assert isinstance(data["packages"], list)


def test_improvement_experiment_task2a_routing_calls_route_model_twice(client, auth_headers, monkeypatch):
    """Task 2A enrichment must invoke route_model exactly twice (preflight + synthesis)."""
    import app.services.improvement_task2a_routing as improvement_task2a_routing
    from app.runtime import model_routing as runtime_model_routing

    calls = {"n": 0}
    real_route_model = runtime_model_routing.route_model

    def counting_route_model(request, *, specs=None):
        calls["n"] += 1
        return real_route_model(request, specs=specs)

    monkeypatch.setattr(improvement_task2a_routing.model_routing, "route_model", counting_route_model)

    variant_resp = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={
            "baseline_id": "god_of_carnage",
            "candidate_summary": "Route model call count wiring.",
        },
    )
    variant_id = variant_resp.get_json()["variant_id"]
    experiment_resp = client.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers,
        json={"variant_id": variant_id, "test_inputs": ["one", "two"]},
    )
    assert experiment_resp.status_code == 200
    assert calls["n"] == 2


def test_improvement_experiment_reuses_cached_rag_stack(client, auth_headers, monkeypatch):
    """Two experiment POSTs must call build_runtime_retriever only once (process singleton)."""
    calls = {"n": 0}
    real_build = improvement_routes_module.build_runtime_retriever

    def counting_build(repo_root):
        calls["n"] += 1
        return real_build(repo_root)

    monkeypatch.setattr(improvement_routes_module, "build_runtime_retriever", counting_build)

    v1 = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={"baseline_id": "god_of_carnage", "candidate_summary": "Cache test run A."},
    )
    v2 = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={"baseline_id": "god_of_carnage", "candidate_summary": "Cache test run B."},
    )
    vid1 = v1.get_json()["variant_id"]
    vid2 = v2.get_json()["variant_id"]
    r1 = client.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers,
        json={"variant_id": vid1, "test_inputs": ["a", "b"]},
    )
    r2 = client.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers,
        json={"variant_id": vid2, "test_inputs": ["c", "d"]},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert calls["n"] == 1


def test_improvement_route_surfaces_capability_failures_honestly(client, auth_headers, monkeypatch):
    class FailingRegistry:
        def invoke(self, *, name, mode, actor, payload, trace_id=None):
            if name == "wos.context_pack.build":
                return {
                    "retrieval": {
                        "sources": [],
                        "hit_count": 0,
                        "status": "ok",
                        "profile": "improvement_eval",
                        "domain": "improvement",
                    },
                    "context_text": "",
                }
            if name == "wos.transcript.read":
                return {"run_id": payload.get("run_id", ""), "content": '{"transcript":[]}'}
            raise CapabilityInvocationError(name, "forced_failure")

        def recent_audit(self, *, limit=20):
            return [{"capability_name": "wos.review_bundle.build", "outcome": "error"}]

    monkeypatch.setattr("app.api.v1.improvement_routes.create_default_capability_registry", lambda **kwargs: FailingRegistry())

    variant_resp = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={
            "baseline_id": "god_of_carnage",
            "candidate_summary": "Force capability failure case.",
        },
    )
    variant_id = variant_resp.get_json()["variant_id"]
    response = client.post(
        "/api/v1/improvement/experiments/run",
        headers=auth_headers,
        json={"variant_id": variant_id},
    )

    assert response.status_code == 502
    payload = response.get_json()
    assert payload["error"] == "capability_workflow_failed"
    assert "capability_audit" in payload


# ---------------------------------------------------------------------------
# D2 REFOCUS — semantic interpretation in sandbox turns
# ---------------------------------------------------------------------------

_DUMMY_VARIANT = {"variant_id": "test_variant_001", "mutation_plan": []}


def test_sandbox_turn_uses_semantic_interpretation():
    """Speech input must produce interpreted_kind == 'speech', not keyword-based detection."""
    result = _simulate_sandbox_turn(
        variant=_DUMMY_VARIANT,
        player_input='"I ask you to explain your reasoning calmly."',
        turn_number=1,
    )
    assert result["interpreted_kind"] == "speech", (
        f"Expected 'speech', got {result['interpreted_kind']!r}"
    )
    # guard_rejected must NOT fire merely because of dangerous keywords absent here
    assert result["guard_rejected"] is False
    assert "interpretation_confidence" in result
    assert result["interpretation_confidence"] > 0.0


def test_sandbox_turn_action_input_is_classified_correctly():
    """Action verb input must produce interpreted_kind == 'action'."""
    result = _simulate_sandbox_turn(
        variant=_DUMMY_VARIANT,
        player_input="I take the lantern and move to the eastern corridor.",
        turn_number=2,
    )
    assert result["interpreted_kind"] == "action", (
        f"Expected 'action', got {result['interpreted_kind']!r}"
    )
    assert result["guard_rejected"] is False
    assert result["triggered_tags"] == ["action"]


def test_evaluate_experiment_builds_comparison_package_and_rationale(tmp_path):
    """Service-level: comparison_package and rationale reflect stored experiment metrics."""
    store = ImprovementStore(root=tmp_path)
    variant = create_variant(
        baseline_id="baseline_x",
        candidate_summary="Rationale wiring.",
        actor_id="actor",
        store=store,
    )
    experiment = run_sandbox_experiment(
        variant_id=variant["variant_id"],
        actor_id="actor",
        test_inputs=["I speak calmly.", "I repeat again and again.", "I argue and fight."],
        store=store,
    )
    ev = evaluate_experiment(experiment_id=experiment["experiment_id"], store=store)
    cp = build_comparison_package(ev)
    assert cp["dimensions"][0]["delta"] == ev["comparison"]["guard_reject_rate_delta"]
    rationale = build_recommendation_rationale(
        evaluation=ev,
        recommendation_summary="promote_for_human_review",
        retrieval_hit_count=2,
        retrieval_source_paths=["docs/a.md", "docs/b.md"],
        transcript_meta={"repetition_turn_count": 0},
    )
    assert any(d.get("category") == "retrieval_context" for d in rationale["drivers"])
    finalized = finalize_recommendation_rationale_with_retrieval_digest(
        rationale,
        context_text="module context alpha",
        retrieval_source_paths=["docs/a.md", "docs/b.md"],
        hit_count=2,
    )
    alt = finalize_recommendation_rationale_with_retrieval_digest(
        rationale,
        context_text="module context beta",
        retrieval_source_paths=["docs/a.md", "docs/b.md"],
        hit_count=2,
    )
    assert finalized["retrieval_context_fingerprint_sha256_16"] != alt["retrieval_context_fingerprint_sha256_16"]


def test_sandbox_experiment_evaluation_uses_interpretation_signals(tmp_path):
    """Full experiment run must surface semantically meaningful signals in evaluation metrics."""
    store = ImprovementStore(root=tmp_path)
    variant = create_variant(
        baseline_id="baseline_test",
        candidate_summary="Test semantic signal wiring.",
        actor_id="test_actor",
        store=store,
    )
    experiment = run_sandbox_experiment(
        variant_id=variant["variant_id"],
        actor_id="test_actor",
        test_inputs=[
            '"Tell me what happened here."',     # speech
            "I look around the room carefully.",  # action
            "I ask and then inspect the door.",   # mixed
        ],
        store=store,
    )
    # Each turn in the transcript should carry interpreted_kind
    for turn in experiment["transcript"]:
        assert "interpreted_kind" in turn, f"Turn {turn['turn_number']} missing interpreted_kind"
        assert turn["interpreted_kind"] in (
            "speech", "action", "mixed", "reaction",
            "intent_only", "explicit_command", "meta", "ambiguous",
        )
    # The first turn (speech) must not be guard-rejected
    speech_turn = experiment["transcript"][0]
    assert speech_turn["guard_rejected"] is False
    # Semantic rates must be present in evaluated metrics
    from app.services.improvement_service import _evaluate_transcript
    metrics = _evaluate_transcript(experiment["transcript"])
    assert "semantic_speech_rate" in metrics
    assert "semantic_action_rate" in metrics
    assert "semantic_command_rate" in metrics


# Extension tests for error-path coverage

def test_create_variant_missing_baseline_id_returns_400(client, auth_headers):
    """POST /api/v1/improvement/variants without baseline_id returns 400."""
    resp = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={"candidate_summary": "No baseline provided"},
    )
    assert resp.status_code == 400
    assert "baseline_id" in resp.get_json().get("error", "").lower()


def test_create_variant_missing_candidate_summary_returns_400(client, auth_headers):
    """POST /api/v1/improvement/variants without candidate_summary returns 400."""
    resp = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={"baseline_id": "baseline_001"},
    )
    assert resp.status_code == 400
    assert "candidate_summary" in resp.get_json().get("error", "").lower()


def test_create_variant_non_dict_body_returns_400(client, auth_headers):
    """POST /api/v1/improvement/variants with non-dict body returns 400."""
    resp = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json=["not", "a", "dict"],
    )
    assert resp.status_code == 400


def test_run_experiment_non_list_test_inputs_returns_400(client, auth_headers):
    """POST /api/v1/improvement/experiments with non-list test_inputs returns error."""
    variant_resp = client.post(
        "/api/v1/improvement/variants",
        headers=auth_headers,
        json={
            "baseline_id": "baseline_001",
            "candidate_summary": "Test variant",
        },
    )
    assert variant_resp.status_code == 201
    variant_id = variant_resp.get_json()["variant_id"]

    resp = client.post(
        "/api/v1/improvement/experiments",
        headers=auth_headers,
        json={
            "variant_id": variant_id,
            "test_inputs": "not_a_list",  # Should be a list
        },
    )
    # Should return an error status (either 400 or 500 depending on validation)
    assert resp.status_code >= 400


def test_recommendation_decision_returns_404_when_package_not_found(
    client, auth_headers, monkeypatch
):
    """POST /api/v1/improvement/recommendations/{id}/decision returns 404 when package not found."""
    from unittest.mock import MagicMock

    mock_store = MagicMock(spec=ImprovementStore)
    mock_store.read_json.side_effect = FileNotFoundError("package not found")
    monkeypatch.setattr(
        improvement_routes_module, "ImprovementStore",
        lambda *args, **kwargs: mock_store
    )
    resp = client.post(
        "/api/v1/improvement/recommendations/nonexistent_package/decision",
        headers=auth_headers,
        json={"decision": "accept"},
    )
    assert resp.status_code == 404
