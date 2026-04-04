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
    assert data["module_id"] == "god_of_carnage"
    assert data["outputs_are_recommendations_only"] is True
    assert "retrieval" in data
    assert "review_bundle" in data
    assert "capability_audit" in data
    assert "stack_components" in data
    assert "wos.context_pack.build" in data["stack_components"]["capabilities"]
