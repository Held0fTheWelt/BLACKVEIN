from __future__ import annotations


def _headers(internal_api_key: str) -> dict[str, str]:
    return {"X-Play-Service-Key": internal_api_key}


def _goc_projection(**overrides):
    projection = {
        "module_id": "god_of_carnage",
        "start_scene_id": "scene_1",
        "scenes": [],
        "selected_player_role": "annette",
        "human_actor_id": "annette",
        "npc_actor_ids": ["alain", "veronique", "michel"],
        "actor_lanes": {
            "annette": "human",
            "alain": "npc",
            "veronique": "npc",
            "michel": "npc",
        },
    }
    projection.update(overrides)
    return projection


def test_story_sessions_list_empty_then_populated(client, internal_api_key):
    list_empty = client.get("/api/story/sessions", headers=_headers(internal_api_key))
    assert list_empty.status_code == 200
    body0 = list_empty.json()
    assert body0["total"] == 0
    assert body0["items"] == []

    create_response = client.post(
        "/api/story/sessions",
        headers=_headers(internal_api_key),
        json={
            "module_id": "god_of_carnage",
            "runtime_projection": _goc_projection(),
        },
    )
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]

    list_one = client.get("/api/story/sessions", headers=_headers(internal_api_key))
    assert list_one.status_code == 200
    body1 = list_one.json()
    assert body1["total"] == 1
    assert len(body1["items"]) == 1
    row = body1["items"][0]
    assert row["session_id"] == session_id
    assert row["module_id"] == "god_of_carnage"
    assert row["turn_counter"] == 0
    assert row["current_scene_id"] == "scene_1"
    assert "updated_at" in row
    assert "created_at" in row


def test_story_session_lifecycle_and_nl_interpretation(client, internal_api_key):
    create_response = client.post(
        "/api/story/sessions",
        headers=_headers(internal_api_key),
        json={
            "module_id": "god_of_carnage",
            "runtime_projection": _goc_projection(),
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    session_id = created["session_id"]
    opening = created.get("opening_turn")
    assert opening is not None
    assert opening.get("turn_kind") == "opening"
    assert opening.get("turn_number") == 0

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
    assert state_body.get("history_count") == 3
    assert "graph" not in (state_body.get("last_committed_turn") or {})
    story_window = state_body.get("story_window") or {}
    assert story_window.get("contract") == "authoritative_story_window_v1"
    story_entries = story_window.get("entries") or []
    assert story_entries
    assert story_entries[0]["kind"] == "opening"
    assert any(entry.get("role") == "player" and "open the door" in entry.get("text", "") for entry in story_entries)
    assert any(entry.get("role") == "runtime" and entry.get("turn_number") == 2 for entry in story_entries)

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
            "runtime_projection": _goc_projection(),
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


def _visible_output_text_lower(turn: dict) -> str:
    bundle = turn.get("visible_output_bundle") or {}
    parts: list[str] = []
    for key in ("gm_narration", "spoken_lines", "action_lines"):
        val = bundle.get(key)
        if isinstance(val, list):
            for row in val:
                if isinstance(row, dict):
                    parts.append(str(row.get("text") or row.get("line") or ""))
                else:
                    parts.append(str(row))
        elif isinstance(val, str):
            parts.append(val)
    for block in bundle.get("scene_blocks") or []:
        if isinstance(block, dict):
            parts.append(str(block.get("text") or block.get("player_display_text") or ""))
    return " ".join(parts).lower()


def test_p0_action_resolution_evidence_opening_vs_schalte_fernseher(client, internal_api_key):
    """Opening traces must not carry applicable P0 player-action evidence; real turns must."""
    create_response = client.post(
        "/api/story/sessions",
        headers=_headers(internal_api_key),
        json={
            "module_id": "god_of_carnage",
            "runtime_projection": _goc_projection(),
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    opening = created.get("opening_turn") or {}
    opening_path = opening.get("observability_path_summary") or {}
    opening_p0 = opening_path.get("p0_action_resolution_evidence") or {}
    assert opening_p0.get("p0_player_action_evidence_applicable") is False
    assert opening_p0.get("player_action_frame") is None

    session_id = created["session_id"]
    raw = "Schalte den Fernseher ein"
    turn_response = client.post(
        f"/api/story/sessions/{session_id}/turns",
        headers=_headers(internal_api_key),
        json={"player_input": raw},
    )
    assert turn_response.status_code == 200
    turn = turn_response.json()["turn"]
    assert turn.get("turn_number", 0) >= 1
    assert turn.get("http_status") == 200
    assert turn.get("turn_status") in {"committed", "committed_degraded"}
    path = turn.get("observability_path_summary") or {}
    p0 = path.get("p0_action_resolution_evidence") or {}
    assert p0.get("p0_player_action_evidence_applicable") is True
    assert p0.get("raw_player_input") == raw
    frame = p0.get("player_action_frame") or {}
    assert frame.get("input_kind") == "action"
    assert frame.get("action_kind") == "object_interaction"
    assert frame.get("verb") == "activate"
    assert frame.get("target_query") == "Fernseher"
    assert p0.get("player_speech_committed") is False
    assert p0.get("npc_committed_player_action") is False
    assert "interpreted_input" in turn
    assert turn["interpreted_input"].get("player_input_kind") == "action"
    aff = str(p0.get("affordance_status") or "").strip().lower()
    assert aff in {"allowed", "unknown_target", "blocked", "partial", "ambiguous", "allowed_offscreen"}
    if aff in {"unknown_target", "blocked"}:
        assert p0.get("player_action_committed") is False
    visible = _visible_output_text_lower(turn)
    assert "alain sagt:" not in visible
    assert "alain says:" not in visible


def test_story_turn_hard_boundary_maps_to_422(client, internal_api_key, monkeypatch):
    create_response = client.post(
        "/api/story/sessions",
        headers=_headers(internal_api_key),
        json={
            "module_id": "god_of_carnage",
            "runtime_projection": _goc_projection(),
        },
    )
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]

    manager = client.app.state.story_manager

    def _raise_hard_boundary(*, session_id: str, player_input: str, trace_id=None):
        raise RuntimeError("Hard narrative boundary: boundary_player_safety_violation")

    monkeypatch.setattr(manager, "execute_turn", _raise_hard_boundary)

    response = client.post(
        f"/api/story/sessions/{session_id}/turns",
        headers=_headers(internal_api_key),
        json={"player_input": "unsafe"},
    )
    assert response.status_code == 422
    assert response.json().get("detail") == "boundary_player_safety_violation"


def test_story_turn_rejected_recoverable_stays_http_200(client, internal_api_key, monkeypatch):
    create_response = client.post(
        "/api/story/sessions",
        headers=_headers(internal_api_key),
        json={
            "module_id": "god_of_carnage",
            "runtime_projection": _goc_projection(),
        },
    )
    assert create_response.status_code == 200
    session_id = create_response.json()["session_id"]

    manager = client.app.state.story_manager

    def _recoverable_turn(*, session_id: str, player_input: str, trace_id=None):
        return {
            "turn_number": 1,
            "turn_kind": "player_rejected_recoverable",
            "raw_input": player_input,
            "interpreted_input": {"kind": "action", "player_input_kind": "action"},
            "narrative_commit": {
                "situation_status": "continue",
                "allowed": False,
                "commit_reason_code": "recoverable_rejection",
                "committed_scene_id": "scene_1",
            },
            "validation_outcome": {
                "status": "rejected",
                "reason": "dramatic_effect_reject_continuity_pressure",
            },
            "visible_output_bundle": {"gm_narration": ["blocked"], "spoken_lines": [], "action_lines": []},
            "ok": False,
            "turn_status": "rejected_recoverable",
            "reason": "dramatic_effect_reject_continuity_pressure",
            "player_visible_message": "blocked",
            "diagnostics": {"recoverable_rejection": True, "hard_boundary_failure": False},
        }

    monkeypatch.setattr(manager, "execute_turn", _recoverable_turn)

    response = client.post(
        f"/api/story/sessions/{session_id}/turns",
        headers=_headers(internal_api_key),
        json={"player_input": "Gehe ins Bad"},
    )
    assert response.status_code == 200
    turn = response.json()["turn"]
    assert turn["ok"] is False
    assert turn["turn_status"] == "rejected_recoverable"

