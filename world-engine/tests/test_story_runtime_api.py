from __future__ import annotations


def _headers(internal_api_key: str) -> dict[str, str]:
    return {"X-Play-Service-Key": internal_api_key}


def test_story_session_lifecycle_and_nl_interpretation(client, internal_api_key):
    create_response = client.post(
        "/api/story/sessions",
        headers=_headers(internal_api_key),
        json={
            "module_id": "god_of_carnage",
            "runtime_projection": {"start_scene_id": "scene_1", "scenes": []},
        },
    )
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]

    turn_response = client.post(
        f"/api/story/sessions/{session_id}/turns",
        headers=_headers(internal_api_key),
        json={"player_input": 'I say "stop" and open the door'},
    )
    assert turn_response.status_code == 200
    turn_payload = turn_response.json()["turn"]
    assert turn_payload["interpreted_input"]["kind"] == "mixed"
    assert turn_payload["model_route"]["selected_model"]
    assert "retrieval" in turn_payload
    assert turn_payload["retrieval"]["domain"] == "runtime"
    assert turn_payload["retrieval"]["profile"] == "runtime_turn_support"
    assert "status" in turn_payload["retrieval"]
    assert "sources" in turn_payload["retrieval"]
    assert "graph" in turn_payload
    assert turn_payload["graph"]["graph_name"] == "wos_runtime_turn_graph"
    assert "nodes_executed" in turn_payload["graph"]
    assert "capability_audit" in turn_payload["graph"]

    command_response = client.post(
        f"/api/story/sessions/{session_id}/turns",
        headers=_headers(internal_api_key),
        json={"player_input": "/look around"},
    )
    assert command_response.status_code == 200
    assert command_response.json()["turn"]["interpreted_input"]["kind"] == "explicit_command"

    state_response = client.get(
        f"/api/story/sessions/{session_id}/state",
        headers=_headers(internal_api_key),
    )
    assert state_response.status_code == 200
    state_body = state_response.json()
    assert state_body["turn_counter"] == 2
    assert state_body.get("last_committed_turn", {}).get("turn_number") == 2
    assert "graph" not in (state_body.get("last_committed_turn") or {})

    diagnostics_response = client.get(
        f"/api/story/sessions/{session_id}/diagnostics",
        headers=_headers(internal_api_key),
    )
    assert diagnostics_response.status_code == 200
    diagnostics = diagnostics_response.json()["diagnostics"]
    assert diagnostics
    assert "raw_input" in diagnostics[-1]
    assert "retrieval" in diagnostics[-1]


def test_story_turns_cover_primary_free_input_paths(client, internal_api_key):
    create_response = client.post(
        "/api/story/sessions",
        headers=_headers(internal_api_key),
        json={
            "module_id": "god_of_carnage",
            "runtime_projection": {"start_scene_id": "scene_1", "scenes": []},
        },
    )
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]

    samples = [
        ("Tell him I am not leaving.", "speech"),
        ("I look at her and wait for a reaction.", "action"),
        ("I open the door and quietly say stop lying.", "mixed"),
        ("/inspect room", "explicit_command"),
        ("I do not answer. I just stare at him.", "intent_only"),
        ("open door wow", "mixed"),
    ]
    for raw_input, expected_kind in samples:
        response = client.post(
            f"/api/story/sessions/{session_id}/turns",
            headers=_headers(internal_api_key),
            json={"player_input": raw_input},
        )
        assert response.status_code == 200
        turn = response.json()["turn"]
        assert turn["raw_input"] == raw_input
        assert turn["interpreted_input"]["kind"] == expected_kind
        assert turn["turn_number"] >= 1

    state_response = client.get(
        f"/api/story/sessions/{session_id}/state",
        headers=_headers(internal_api_key),
    )
    assert state_response.status_code == 200
    assert state_response.json()["turn_counter"] == len(samples)
