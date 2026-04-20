from __future__ import annotations

from pathlib import Path

import pytest

from story_runtime_core.adapters import build_default_model_adapters
from app.services.writers_room_model_routing import build_writers_room_model_route_specs
from ai_stack import (
    build_capability_tool_bridge,
    build_langchain_retriever_bridge,
    build_runtime_retriever,
    build_seed_writers_room_graph,
)
from ai_stack.rag import ContextRetriever

from app.services import writers_room_service as writers_room_service_module
from app.services.writers_room_service import _WritersRoomWorkflow


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _context_pack_for_paths(paths: list[str], *, context_tag: str = "") -> dict:
    return {
        "retrieval": {
            "domain": "writers_room",
            "profile": "writers_review",
            "status": "ok",
            "hit_count": len(paths),
            "sources": [
                {"source_path": p, "content_class": "canon", "snippet": f"excerpt:{p}"}
                for p in paths
            ],
            "ranking_notes": [],
            "index_version": "test",
            "corpus_fingerprint": "",
            "storage_path": "",
            "retrieval_route": "test_route",
            "embedding_model_id": "",
            "top_hit_score": "0.91",
        },
        "context_text": f"[{context_tag}]\n" + "\n".join(paths),
    }


def _build_controlled_workflow(
    repo_root: Path,
    context_pack_body: dict,
    review_bundle_body: dict,
) -> _WritersRoomWorkflow:
    class ControlledRegistry:
        def __init__(self) -> None:
            self._audit: list[dict] = []

        def invoke(self, *, name, mode, actor, payload, trace_id=None):
            if name == "wos.context_pack.build":
                self._audit.append({"capability_name": name, "outcome": "allowed"})
                return context_pack_body
            if name == "wos.review_bundle.build":
                self._audit.append({"capability_name": name, "outcome": "allowed"})
                return review_bundle_body
            raise AssertionError(f"unexpected capability {name}")

        def recent_audit(self, limit=20):
            return list(self._audit[-limit:])

    retriever, assembler, _corpus = build_runtime_retriever(repo_root)
    registry = ControlledRegistry()
    review_tool = build_capability_tool_bridge(
        capability_registry=registry,
        capability_name="wos.review_bundle.build",
        mode="writers_room",
        actor="writers_room:test_controlled",
    )
    lc_bridge = build_langchain_retriever_bridge(retriever)
    return _WritersRoomWorkflow(
        capability_registry=registry,
        model_route_specs=build_writers_room_model_route_specs(),
        adapters=build_default_model_adapters(),
        seed_graph=build_seed_writers_room_graph(),
        langchain_retriever=lc_bridge,
        review_bundle_tool=review_tool,
    )


def test_writers_room_review_requires_jwt(client):
    response = client.post(
        "/api/v1/writers-room/reviews",
        json={"module_id": "god_of_carnage", "focus": "canon consistency"},
    )
    assert response.status_code == 401


def test_writers_room_unified_review_calls_context_retriever_once(client, auth_headers, monkeypatch):
    """Writers-Room workflow must not issue a second retrieve for LangChain preview."""
    calls = {"n": 0}
    orig = ContextRetriever.retrieve

    def counting(self, request):
        calls["n"] += 1
        return orig(self, request)

    monkeypatch.setattr(ContextRetriever, "retrieve", counting)
    monkeypatch.setattr(writers_room_service_module, "_WORKFLOW", None)
    response = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "single retrieve probe"},
    )
    assert response.status_code == 200
    assert calls["n"] == 1


def test_writers_room_review_runs_unified_stack_flow(client, auth_headers):
    response = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "canon consistency"},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["canonical_flow"] == "writers_room_unified_stack_workflow"
    assert data.get("trace_id")
    assert data.get("review_id")
    assert data["module_id"] == "god_of_carnage"
    assert data["outputs_are_recommendations_only"] is True
    assert data["review_state"]["status"] == "pending_human_review"
    assert "governance_outcome_artifact" not in data
    ap = data.get("artifact_provenance") or {}
    assert "kind" not in ap
    assert ap.get("workflow") == "writers_room_unified_stack_workflow"
    assert ap.get("module_id") == "god_of_carnage"
    assert ap.get("shared_semantic_contract_version")
    assert "recommendation_artifacts" in data
    assert isinstance(data["recommendation_artifacts"], list)
    assert data["recommendation_artifacts"]
    assert "recommendations" not in data
    assert "recommendations" not in data["proposal_package"]
    assert isinstance(data.get("writers_room_artifact_manifest"), list)
    assert "workflow_manifest" in data
    assert data["workflow_manifest"]["workflow"] == "writers_room_unified_stack_workflow"
    stage_ids = [s["id"] for s in data["workflow_manifest"]["stages"]]
    assert data["workflow_stages"] == stage_ids
    assert "request_intake" in stage_ids
    assert "retrieval_analysis" in stage_ids
    assert "retrieval_bridge_preview" in stage_ids
    assert "governance_envelope" in stage_ids
    assert "human_review_pending" in stage_ids
    assert "review_checkpoint" in data["review_summary"]
    assert data["review_summary"]["review_checkpoint"]["verify_recommendation_only_semantics"] is True
    rd = data["proposal_package"]["retrieval_digest"]
    assert "hit_count" in rd and "evidence_tier" in rd
    assert "context_fingerprint_sha256_16" in rd
    assert rd.get("langchain_preview_source") in {"primary_context_pack", "primary_context_pack_no_hits"}
    assert "review_summary" in data
    assert data["review_summary"]["issue_count"] >= 0
    assert data["review_summary"]["bundle_id"] == (data.get("review_bundle") or {}).get("bundle_id")
    assert "proposal_package" in data
    assert data["proposal_package"].get("artifact_class") == "proposal_artifact"
    assert data["proposal_package"].get("shared_semantic_contract_version")
    if data.get("issues"):
        assert data["issues"][0].get("artifact_class") == "analysis_artifact"
        for key in (
            "artifact_id",
            "source_module_id",
            "evidence_refs",
            "proposal_scope",
            "approval_state",
        ):
            assert key in data["issues"][0]
    assert "comment_bundle" in data
    assert "patch_candidates" in data
    assert "variant_candidates" in data
    assert "workflow_stages" in data
    assert "retrieval" in data
    assert "retrieval_trace" in data
    assert data["retrieval_trace"]["evidence_strength"] in {"none", "weak", "moderate", "strong"}
    assert data["retrieval_trace"]["evidence_tier"] == data["retrieval_trace"]["evidence_strength"]
    assert data["retrieval_trace"].get("retrieval_trace_schema_version")
    assert data["retrieval_trace"].get("readiness_label")
    assert data["retrieval_trace"].get("artifact_class") == "analysis_artifact"
    assert data["retrieval_trace"].get("artifact_id")
    assert "review_bundle" in data
    assert "capability_audit" in data
    assert "langchain_retriever_preview" in data
    assert data["langchain_retriever_preview"]["document_count"] >= 0
    assert "stack_components" in data
    assert "wos.context_pack.build" in data["stack_components"]["capabilities"]
    assert data["stack_components"]["langchain_integration"]["enabled"] is True
    mg = data.get("model_generation") or {}
    assert mg.get("artifact_class") == "analysis_artifact"
    assert mg.get("artifact_id")
    assert mg.get("adapter_invocation_mode") in {"langchain_structured_primary", "raw_adapter_fallback"}
    meta = mg.get("metadata") or {}
    if mg.get("adapter_invocation_mode") == "langchain_structured_primary":
        assert meta.get("langchain_prompt_used") is True
    if mg.get("adapter_invocation_mode") == "raw_adapter_fallback":
        assert meta.get("langchain_prompt_used") is False
        assert meta.get("bypass_note")
    assert (
        data["stack_components"]["langchain_integration"].get("writers_room_generation_bridge")
        == "invoke_writers_room_adapter_with_langchain"
    )
    t2a = (data.get("model_generation") or {}).get("task_2a_routing") or {}
    for key in ("preflight", "synthesis"):
        st = t2a.get(key) or {}
        assert st.get("stage_id") == key
        rev = st.get("routing_evidence") or {}
        assert rev.get("requested_workflow_phase") == st.get("workflow_phase")
        assert rev.get("requested_task_kind") == st.get("task_kind")
        assert rev.get("route_reason_code") == (st.get("decision") or {}).get("route_reason_code")
        assert "routing_overview" in rev
        assert rev["routing_overview"].get("title")
        assert "no_eligible_spec_selection" in rev
        assert "diagnostics_overview" in rev
        d = rev["diagnostics_overview"]
        assert d.get("summary") and d.get("severity") and "short_explanation" in d
        assert "diagnostics_flags" in rev and "diagnostics_causes" in rev
        assert "policy_execution_aligned" in rev
        assert "execution_deviation" in rev
    oa = data.get("operator_audit") or {}
    assert oa.get("audit_schema_version")
    assert oa.get("audit_summary", {}).get("surface") == "writers_room"
    assert oa.get("audit_timeline")
    gt = data.get("governance_truth") or {}
    assert gt.get("langgraph_orchestration_depth") == "seed_graph_stub"
    assert gt.get("retrieval_evidence_tier") == data["retrieval_trace"]["evidence_tier"]
    assert "wos.context_pack.build" in (gt.get("capabilities_invoked") or [])
    assert gt.get("artifact_class") == "analysis_artifact"
    lp = data.get("langchain_retriever_preview") or {}
    assert lp.get("artifact_class") == "analysis_artifact"
    leg = (data.get("legacy_paths") or [{}])[0]
    assert leg.get("artifact_class") == "analysis_artifact"
    assert leg.get("body")


def test_writers_room_patch_candidates_have_preview_summary_and_confidence(client, auth_headers):
    response = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "canon consistency"},
    )
    assert response.status_code == 200
    data = response.get_json()
    patch_candidates = data.get("patch_candidates", [])
    assert len(patch_candidates) >= 1, "Expected at least one patch candidate"
    for candidate in patch_candidates:
        assert "preview_summary" in candidate, f"Missing preview_summary in candidate: {candidate}"
        assert "confidence" in candidate, f"Missing confidence in candidate: {candidate}"
        assert isinstance(candidate["confidence"], float), (
            f"confidence must be a float, got {type(candidate['confidence'])}"
        )
        assert 0.0 <= candidate["confidence"] <= 1.0, (
            f"confidence must be between 0 and 1, got {candidate['confidence']}"
        )
        assert isinstance(candidate["preview_summary"], str), (
            f"preview_summary must be a string, got {type(candidate['preview_summary'])}"
        )
        assert len(candidate["preview_summary"]) > 0, "preview_summary must not be empty"
        assert candidate.get("review_bundle_id") == (data.get("review_bundle") or {}).get("bundle_id")
        assert candidate.get("confidence_kind") == "retrieval_heuristic"
        assert "evidence_tier" in candidate


def test_proposal_package_langchain_preview_paths_materialized(client, auth_headers, monkeypatch):
    """LangChain retriever preview paths must be copied into the packaged proposal."""
    from app.services import writers_room_service as wrs

    repo = _repo_root()
    rb = {
        "bundle_id": "bundle_preview_pkg",
        "status": "recommendation_only",
        "summary": "s",
        "recommendations": [],
        "evidence_sources": [],
    }
    ctx = _context_pack_for_paths(["corp/d1_with_preview.md"])
    monkeypatch.setattr(wrs, "_WORKFLOW", None)
    monkeypatch.setattr(
        wrs,
        "_get_workflow",
        lambda: _build_controlled_workflow(repo, ctx, rb),
    )
    r = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "preview packaging"},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["proposal_package"]["langchain_preview_paths"] == ["corp/d1_with_preview.md"]
    assert body["proposal_package"]["retrieval_digest"]["langchain_preview_source"] == "primary_context_pack"
    gr = body["proposal_package"]["governance_readiness"]
    assert gr["langchain_preview_path_count"] == 1


def test_revision_submit_preserves_prior_snapshot_and_refreshes_artifacts(client, auth_headers, monkeypatch):
    """After revise, revision-submit re-runs workflow and appends a revision cycle."""
    from app.services import writers_room_service as wrs

    repo = _repo_root()
    rb = {
        "bundle_id": "bundle_rev",
        "status": "recommendation_only",
        "summary": "s",
        "recommendations": [],
        "evidence_sources": [],
    }
    alpha = _context_pack_for_paths(["corp/rev_alpha.md"], context_tag="a")
    monkeypatch.setattr(wrs, "_WORKFLOW", None)
    monkeypatch.setattr(
        wrs,
        "_get_workflow",
        lambda: _build_controlled_workflow(repo, alpha, rb),
    )
    c1 = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "revision cycle"},
    )
    assert c1.status_code == 200
    review_id = c1.get_json()["review_id"]
    assert c1.get_json()["proposal_package"]["evidence_sources"][0] == "corp/rev_alpha.md"

    rev = client.post(
        f"/api/v1/writers-room/reviews/{review_id}/decision",
        headers=auth_headers,
        json={"decision": "revise", "note": "expand evidence"},
    )
    assert rev.status_code == 200

    beta = _context_pack_for_paths(["corp/rev_beta.md"], context_tag="b")
    monkeypatch.setattr(wrs, "_WORKFLOW", None)
    monkeypatch.setattr(
        wrs,
        "_get_workflow",
        lambda: _build_controlled_workflow(repo, beta, rb),
    )
    sub = client.post(
        f"/api/v1/writers-room/reviews/{review_id}/revision-submit",
        headers=auth_headers,
        json={"note": "second pass", "focus": "revision cycle B"},
    )
    assert sub.status_code == 200
    final = sub.get_json()
    assert final["review_state"]["status"] == "pending_human_review"
    assert len(final["revision_cycles"]) == 1
    prior = final["revision_cycles"][0]["prior_snapshot"]
    assert prior["proposal_package"]["evidence_sources"][0] == "corp/rev_alpha.md"
    assert final["proposal_package"]["evidence_sources"][0] == "corp/rev_beta.md"
    assert final["proposal_package"]["langchain_preview_paths"] == ["corp/rev_beta.md"]
    assert final["focus"] == "revision cycle B"
    assert "governance_outcome_artifact" not in final


def test_revision_submit_rejected_when_not_pending_revision(client, auth_headers):
    create_resp = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "no revision"},
    )
    review_id = create_resp.get_json()["review_id"]
    bad = client.post(
        f"/api/v1/writers-room/reviews/{review_id}/revision-submit",
        headers=auth_headers,
        json={},
    )
    assert bad.status_code == 400
    assert "revision" in bad.get_json().get("error", "").lower()


def test_writers_room_review_state_transition_and_fetch(client, auth_headers):
    create_resp = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "state transition"},
    )
    assert create_resp.status_code == 200
    review_id = create_resp.get_json()["review_id"]

    get_resp = client.get(f"/api/v1/writers-room/reviews/{review_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    fetched = get_resp.get_json()
    assert fetched["review_id"] == review_id
    assert "governance_outcome_artifact" not in fetched

    decision_resp = client.post(
        f"/api/v1/writers-room/reviews/{review_id}/decision",
        headers=auth_headers,
        json={"decision": "accept", "note": "Looks good for publication review."},
    )
    assert decision_resp.status_code == 200
    decision_data = decision_resp.get_json()
    assert decision_data["review_state"]["status"] == "accepted"
    assert decision_data["human_decision"]["decision"] == "accept"
    assert decision_data["review_state"]["history"][-1]["status"] == "accepted"
    assert decision_data["review_state"]["history"][-1]["decision"] == "accept"
    goa = decision_data.get("governance_outcome_artifact") or {}
    assert goa.get("artifact_class") == "approved_authored_artifact"
    assert goa.get("shared_semantic_contract_version")


def test_writers_room_retrieval_sources_materially_change_proposal_artifacts(
    client, auth_headers, monkeypatch
):
    """Different context_pack sources must change proposal evidence and issue linkage."""
    from app.services import writers_room_service as wrs

    repo = _repo_root()
    rb = {
        "bundle_id": "bundle_retrieval_test",
        "status": "recommendation_only",
        "summary": "s",
        "recommendations": [],
        "evidence_sources": [],
    }
    alpha = _context_pack_for_paths(["corp/d1_alpha_retrieval_only.md"], context_tag="alpha")
    monkeypatch.setattr(wrs, "_WORKFLOW", None)
    monkeypatch.setattr(wrs, "_get_workflow", lambda: _build_controlled_workflow(repo, alpha, rb))
    r1 = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "retrieval materiality A"},
    )
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert d1["proposal_package"]["evidence_sources"][0] == "corp/d1_alpha_retrieval_only.md"
    assert d1["issues"][0]["evidence_source"] == "corp/d1_alpha_retrieval_only.md"
    assert "corp/d1_alpha_retrieval_only.md" in d1["issues"][0]["description"]

    beta = _context_pack_for_paths(["corp/d1_beta_retrieval_only.md"], context_tag="beta")
    monkeypatch.setattr(wrs, "_WORKFLOW", None)
    monkeypatch.setattr(wrs, "_get_workflow", lambda: _build_controlled_workflow(repo, beta, rb))
    r2 = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "retrieval materiality B"},
    )
    assert r2.status_code == 200
    d2 = r2.get_json()
    assert d2["proposal_package"]["evidence_sources"][0] == "corp/d1_beta_retrieval_only.md"
    assert d2["issues"][0]["evidence_source"] == "corp/d1_beta_retrieval_only.md"
    assert d1["proposal_package"]["evidence_sources"] != d2["proposal_package"]["evidence_sources"]


def test_writers_room_review_bundle_tool_output_in_review_summary(client, auth_headers, monkeypatch):
    """Governance envelope (review bundle) ids must flow into review_summary."""
    from app.services import writers_room_service as wrs

    repo = _repo_root()
    ctx = _context_pack_for_paths(["corp/d1_tool_surface.md"])
    bundle_a = {
        "bundle_id": "governance_bundle_alpha_001",
        "status": "recommendation_only",
        "summary": "alpha summary",
        "recommendations": ["r1"],
        "evidence_sources": ["corp/d1_tool_surface.md"],
    }
    monkeypatch.setattr(wrs, "_WORKFLOW", None)
    monkeypatch.setattr(wrs, "_get_workflow", lambda: _build_controlled_workflow(repo, ctx, bundle_a))
    ra = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "tool surface"},
    )
    assert ra.status_code == 200
    pa = ra.get_json()
    assert pa["review_summary"]["bundle_id"] == "governance_bundle_alpha_001"
    assert pa["review_summary"]["bundle_status"] == "recommendation_only"
    assert pa["review_bundle"]["bundle_id"] == "governance_bundle_alpha_001"

    bundle_b = dict(bundle_a)
    bundle_b["bundle_id"] = "governance_bundle_beta_002"
    monkeypatch.setattr(wrs, "_WORKFLOW", None)
    monkeypatch.setattr(wrs, "_get_workflow", lambda: _build_controlled_workflow(repo, ctx, bundle_b))
    rb = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "tool surface"},
    )
    assert rb.status_code == 200
    pb = rb.get_json()
    assert pb["review_summary"]["bundle_id"] == "governance_bundle_beta_002"
    assert pb["review_summary"]["bundle_id"] != pa["review_summary"]["bundle_id"]


def test_writers_room_revise_then_accept_hitl_loop(client, auth_headers):
    create_resp = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "revise loop"},
    )
    assert create_resp.status_code == 200
    review_id = create_resp.get_json()["review_id"]

    rev = client.post(
        f"/api/v1/writers-room/reviews/{review_id}/decision",
        headers=auth_headers,
        json={"decision": "revise", "note": "Needs another dramaturgy pass."},
    )
    assert rev.status_code == 200
    body = rev.get_json()
    assert body["review_state"]["status"] == "pending_revision"
    assert body["last_hitl_action"]["decision"] == "revise"
    assert body["review_state"]["history"][-1]["decision"] == "revise"
    assert "human_decision" not in body or body.get("human_decision") is None
    assert "governance_outcome_artifact" not in body

    acc = client.post(
        f"/api/v1/writers-room/reviews/{review_id}/decision",
        headers=auth_headers,
        json={"decision": "accept", "note": "Revised package ok for governance."},
    )
    assert acc.status_code == 200
    final = acc.get_json()
    assert final["review_state"]["status"] == "accepted"
    assert final["human_decision"]["decision"] == "accept"
    goa = final.get("governance_outcome_artifact") or {}
    assert goa.get("artifact_class") == "approved_authored_artifact"
    assert goa.get("approval_state") == "accepted"


@pytest.mark.parametrize("bad_decision", ["", "maybe", "approve"])
def test_writers_room_invalid_decision_rejected(client, auth_headers, bad_decision):
    create_resp = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "bad decision"},
    )
    review_id = create_resp.get_json()["review_id"]
    resp = client.post(
        f"/api/v1/writers-room/reviews/{review_id}/decision",
        headers=auth_headers,
        json={"decision": bad_decision},
    )
    assert resp.status_code == 400
    assert "decision" in resp.get_json().get("error", "").lower() or "decision" in str(resp.get_json())


def test_writers_room_cannot_finalize_twice(client, auth_headers):
    create_resp = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "double finalize"},
    )
    review_id = create_resp.get_json()["review_id"]
    first = client.post(
        f"/api/v1/writers-room/reviews/{review_id}/decision",
        headers=auth_headers,
        json={"decision": "reject"},
    )
    assert first.status_code == 200
    assert (first.get_json() or {}).get("governance_outcome_artifact", {}).get("artifact_class") == "rejected_artifact"
    second = client.post(
        f"/api/v1/writers-room/reviews/{review_id}/decision",
        headers=auth_headers,
        json={"decision": "accept"},
    )
    assert second.status_code == 400
    assert "finalized" in second.get_json().get("error", "")


# Extension tests for error-path coverage

def test_post_review_missing_module_id_validation(client, auth_headers):
    """POST /api/v1/writers-room/reviews without required fields returns error."""
    resp = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"focus": "no module_id provided"},
    )
    # Should return an error (400 or 422 depending on validation)
    assert resp.status_code >= 400


def test_post_review_missing_module_id_returns_400(client, auth_headers):
    """POST /api/v1/writers-room/reviews without module_id returns 400."""
    resp = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"focus": "no module_id provided"},
    )
    assert resp.status_code == 400
    assert "module_id" in resp.get_json().get("error", "").lower()
