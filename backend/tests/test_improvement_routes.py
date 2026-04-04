from __future__ import annotations

from wos_ai_stack import CapabilityInvocationError

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
    assert retrieval["profile"] == "improvement_eval"
    assert review_bundle["status"] == "recommendation_only"
    assert any(entry["capability_name"] == "wos.context_pack.build" for entry in capability_audit)
    assert any(entry["capability_name"] == "wos.review_bundle.build" for entry in capability_audit)
    assert "retrieval_trace" in payload
    trace = payload["retrieval_trace"]
    assert trace["evidence_strength"] in {"strong", "none"}
    assert trace["profile"] == "improvement_eval"
    if trace["evidence_strength"] == "strong":
        assert trace["hit_count"] > 0
        assert review_bundle["summary"].startswith("[evidence:strong]")
    else:
        assert review_bundle["summary"].startswith("[evidence:none]")
    ctx_audit = next(entry for entry in capability_audit if entry["capability_name"] == "wos.context_pack.build")
    assert ctx_audit.get("result_summary") is not None
    assert ctx_audit["result_summary"]["kind"] == "context_pack"


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
                        "index_version": "c1_semantic_v2",
                        "corpus_fingerprint": "",
                        "storage_path": "",
                    },
                    "context_text": "",
                }
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
    assert body["retrieval_trace"]["hit_count"] == 0
    assert body["review_bundle"]["summary"].startswith("[evidence:none]")


def test_governance_accessibility_lists_recommendation_packages(client, auth_headers):
    response = client.get("/api/v1/improvement/recommendations", headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "packages" in data
    assert isinstance(data["packages"], list)


def test_improvement_route_surfaces_capability_failures_honestly(client, auth_headers, monkeypatch):
    class FailingRegistry:
        def __init__(self) -> None:
            self.calls = 0

        def invoke(self, *, name, mode, actor, payload, trace_id=None):
            self.calls += 1
            if self.calls == 1:
                return {"retrieval": {"sources": []}, "context_text": ""}
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
