from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock


def _goc_projection():
    return {
        "module_id": "god_of_carnage",
        "start_scene_id": "phase_1",
        "selected_player_role": "annette",
        "human_actor_id": "annette",
        "npc_actor_ids": ["alain", "veronique", "michel"],
        "actor_lanes": {
            "annette": "human",
            "alain": "npc",
            "veronique": "npc",
            "michel": "npc",
        },
        "runtime_profile_id": "god_of_carnage_solo",
        "runtime_module_id": "solo_story_runtime",
        "content_module_id": "god_of_carnage",
    }


def test_story_turn_echoes_trace_header(client, internal_api_key):
    custom = str(uuid.uuid4())
    response = client.post(
        "/api/story/sessions",
        headers={"X-Play-Service-Key": internal_api_key, "X-WoS-Trace-Id": custom},
        json={"module_id": "god_of_carnage", "runtime_projection": _goc_projection()},
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


def test_story_session_create_sets_langfuse_parent_for_opening_turn(client, internal_api_key, monkeypatch):
    adapter = MagicMock()
    adapter.is_ready = True
    adapter.is_enabled.return_value = True
    adapter.config = SimpleNamespace(environment="test")
    adapter.get_active_span.return_value = None

    root_span = MagicMock()
    ldss_span = MagicMock()
    narrator_span = MagicMock()
    adapter.start_span_in_trace.return_value = root_span
    path_spans = [MagicMock() for _ in range(6)]
    adapter.create_child_span.side_effect = [*path_spans, ldss_span, narrator_span]

    monkeypatch.setattr(
        "app.observability.langfuse_adapter.LangfuseAdapter.get_instance",
        lambda: adapter,
    )

    langfuse_trace_id = "0123456789abcdef0123456789abcdef"
    response = client.post(
        "/api/story/sessions",
        headers={
            "X-Play-Service-Key": internal_api_key,
            "X-Langfuse-Trace-Id": langfuse_trace_id,
        },
        json={"module_id": "god_of_carnage", "runtime_projection": _goc_projection()},
    )

    assert response.status_code == 200
    session_id = response.json()["session_id"]
    adapter.start_span_in_trace.assert_called_once()
    assert adapter.start_span_in_trace.call_args.kwargs["trace_id"] == langfuse_trace_id
    assert adapter.start_span_in_trace.call_args.kwargs["input"]["session_id"] == session_id
    adapter.session_scope.assert_called_once()
    assert adapter.session_scope.call_args.kwargs["session_id"] == session_id
    adapter.set_active_span.assert_any_call(root_span)
    created_child_names = [call.kwargs["name"] for call in adapter.create_child_span.call_args_list]
    assert "story.graph.path_summary" in created_child_names
    assert "story.phase.model_route" in created_child_names
    assert "story.phase.model_invoke" in created_child_names
    assert "story.phase.model_fallback" in created_child_names
    assert "story.phase.validation" in created_child_names
    assert "story.phase.commit" in created_child_names
    assert "story.phase.ldss" in created_child_names
    assert "story.phase.narrator" in created_child_names
    root_span.end.assert_called_once()
    adapter.flush.assert_called_once()
