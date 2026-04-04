from __future__ import annotations

from wos_ai_stack import CapabilityInvocationError


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
