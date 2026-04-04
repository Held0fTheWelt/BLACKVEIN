from __future__ import annotations

from wos_ai_stack import CapabilityInvocationError
from wos_ai_stack.rag import INDEX_VERSION

from app.services.improvement_service import (
    _simulate_sandbox_turn,
    run_sandbox_experiment,
    create_variant,
    ImprovementStore,
)


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

    assert experiment["sandbox"] is True
    assert experiment["variant_id"] == variant_id
    assert recommendation["candidate"]["variant_id"] == variant_id
    assert recommendation["review_status"] == "pending_governance_review"
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
    assert trace["profile"] == "improvement_eval"
    assert "|tr_turns=3|" in recommendation["recommendation_summary"]
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


def test_governance_accessibility_lists_recommendation_packages(client, auth_headers):
    response = client.get("/api/v1/improvement/recommendations", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "packages" in data
    assert isinstance(data["packages"], list)


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
