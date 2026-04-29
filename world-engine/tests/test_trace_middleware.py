from __future__ import annotations

import uuid


def test_story_turn_echoes_trace_header(client, internal_api_key):
    custom = str(uuid.uuid4())
    response = client.post(
        "/api/story/sessions",
        headers={"X-Play-Service-Key": internal_api_key, "X-WoS-Trace-Id": custom},
        json={"module_id": "god_of_carnage", "runtime_projection": {"start_scene_id": "s1"}},
    )
    assert response.status_code == 200
    assert response.headers.get("X-WoS-Trace-Id") == custom

    session_id = response.json()["session_id"]
    turn_resp = client.post(
        f"/api/story/sessions/{session_id}/turns",
        headers={"X-Play-Service-Key": internal_api_key, "X-WoS-Trace-Id": custom},
        json={"player_input": "I listen to the parents argue."},
    )
    assert turn_resp.status_code == 200
    assert turn_resp.headers.get("X-WoS-Trace-Id") == custom
    turn = turn_resp.json()["turn"]
    assert turn.get("trace_id") == custom
    graph = turn.get("graph") or {}
    repro = graph.get("repro_metadata") or {}
    assert repro.get("trace_id") == custom
    assert repro.get("module_id") == "god_of_carnage"

    diag = client.get(
        f"/api/story/sessions/{session_id}/diagnostics",
        headers={"X-Play-Service-Key": internal_api_key, "X-WoS-Trace-Id": custom},
    )
    assert diag.status_code == 200
    body = diag.json()
    tail = body.get("authoritative_history_tail") or []
    assert tail, "authoritative_history_tail should list committed turns without graph envelope"
    assert tail[-1].get("trace_id") == custom
    full = body.get("diagnostics") or []
    assert full[-1].get("trace_id") == custom
    assert "graph" in full[-1]
    assert "graph" not in tail[-1]


def test_trace_middleware_generates_id_when_missing(client):
    """Test app from conftest includes install_trace_middleware."""
    response = client.get("/api/templates")
    assert response.status_code == 200
    tid = response.headers.get("X-WoS-Trace-Id")
    assert tid and len(tid) >= 8
