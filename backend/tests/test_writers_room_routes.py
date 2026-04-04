from __future__ import annotations


def test_writers_room_review_requires_jwt(client):
    response = client.post(
        "/api/v1/writers-room/reviews",
        json={"module_id": "god_of_carnage", "focus": "canon consistency"},
    )
    assert response.status_code == 401


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
    assert data["outputs_are_recommendations_only"] is False
    assert data["review_state"]["status"] == "pending_human_review"
    assert "proposal_package" in data
    assert "comment_bundle" in data
    assert "patch_candidates" in data
    assert "variant_candidates" in data
    assert "workflow_stages" in data
    assert "retrieval" in data
    assert "retrieval_trace" in data
    assert data["retrieval_trace"]["evidence_strength"] in {"none", "weak", "moderate", "strong"}
    assert data["retrieval_trace"]["evidence_tier"] == data["retrieval_trace"]["evidence_strength"]
    assert "review_bundle" in data
    assert "capability_audit" in data
    assert "langchain_retriever_preview" in data
    assert data["langchain_retriever_preview"]["document_count"] >= 0
    assert "stack_components" in data
    assert "wos.context_pack.build" in data["stack_components"]["capabilities"]
    assert data["stack_components"]["langchain_integration"]["enabled"] is True
    mg = data.get("model_generation") or {}
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
    assert get_resp.get_json()["review_id"] == review_id

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
