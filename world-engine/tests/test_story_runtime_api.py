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
    assert state_response.json()["turn_counter"] == 2

    diagnostics_response = client.get(
        f"/api/story/sessions/{session_id}/diagnostics",
        headers=_headers(internal_api_key),
    )
    assert diagnostics_response.status_code == 200
    diagnostics = diagnostics_response.json()["diagnostics"]
    assert diagnostics
    assert "raw_input" in diagnostics[-1]
