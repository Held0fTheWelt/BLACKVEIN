from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.story_runtime.manager import _emit_langfuse_evidence_observations


def test_langfuse_add_score_duplicates_at_trace_level_for_adr0033_visibility():
    """ADR-0033: observation span.score() alone does not populate Langfuse trace.scores / UI trace tab."""
    from app.observability import langfuse_adapter as lf_mod

    adapter = lf_mod.LangfuseAdapter.__new__(lf_mod.LangfuseAdapter)
    adapter.is_ready = True
    client = MagicMock()
    adapter.client = client
    span = MagicMock()
    span.trace_id = "trace-id-adr0033"
    span.span_id = "obs-id-span"
    span.name = "world-engine.session.create"
    token = lf_mod._active_span_context.set(span)
    try:
        lf_mod.LangfuseAdapter.add_score(
            adapter,
            name="live_runtime_contract_pass",
            value=0.0,
            comment="deterministic gate",
            metadata={"session_id": "s1"},
        )
    finally:
        lf_mod._active_span_context.reset(token)

    span.score.assert_called_once()
    client.create_score.assert_called_once()
    cc_kw = client.create_score.call_args.kwargs
    assert cc_kw["name"] == "live_runtime_contract_pass"
    assert cc_kw["trace_id"] == "trace-id-adr0033"
    assert cc_kw["value"] == 0.0


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
    narrator_span = MagicMock()
    adapter.start_span_in_trace.return_value = root_span
    path_spans = [MagicMock() for _ in range(7)]
    adapter.create_child_span.side_effect = [*path_spans, narrator_span]

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
    assert "story.phase.retrieval" in created_child_names
    assert "story.phase.validation" in created_child_names
    assert "story.phase.commit" in created_child_names
    assert "story.phase.ldss_fallback" not in created_child_names
    assert "story.phase.narrator" in created_child_names
    adapter.record_generation.assert_not_called()
    adapter.record_retrieval.assert_called_once()
    assert adapter.record_retrieval.call_args.kwargs["name"] == "story.rag.retrieval"
    score_names = {call.kwargs["name"] for call in adapter.add_score.call_args_list}
    assert {
        "non_mock_generation_pass",
        "visible_output_present",
        "actor_lane_safety_pass",
        "fallback_absent",
        "usage_present",
        "rag_context_attached",
        "live_runtime_contract_pass",
    }.issubset(score_names)
    root_span.end.assert_called_once()
    adapter.flush.assert_called_once()


def test_langfuse_evidence_observations_record_live_generation_retrieval_and_scores(monkeypatch):
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )

    path_summary = {
        "session_id": "session-live-evidence",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "api_model": "gpt-5-nano",
        "selected_provider": "openai_primary",
        "selected_model": "gpt-5-nano",
        "adapter_invocation_mode": "langchain_structured_primary",
        "route_id": "goc_opening",
        "route_family": "story_runtime",
        "generation_fallback_used": False,
        "structured_output_present": True,
        "parser_error": None,
        "retrieval_context_attached": True,
        "usage_available": True,
        "usage_source": "provider_response",
        "usage_details": {"input": 12, "output": 8, "total": 20},
        "retrieval_status": "ok",
        "retrieval_route": "hybrid",
        "retrieval_hit_count": 1,
        "retrieval_profile": "runtime_turn_support",
        "retrieval_domain": "runtime",
        "retrieval_top_hit_score": 0.91,
        "retrieval_corpus_fingerprint": "fingerprint",
        "retrieval_index_version": "idx-v1",
        "retrieval_degradation_mode": None,
        "retrieval_governance_summary": {"published": 1},
        "actor_lane_validation_status": "approved",
        "quality_class": "healthy",
        "degradation_signals": [],
    }
    graph_state = {"model_prompt": "Prompt with retrieved context."}
    event = {
        "raw_input": "Start the scene.",
        "model_route": {
            "generation": {
                "content": "Generated opening.",
                "metadata": {
                    "adapter": "openai",
                    "model": "gpt-5-nano",
                },
            }
        },
        "retrieval": {
            "query": "GoC opening",
            "sources": [
                {
                    "chunk_id": "chunk-1",
                    "snippet": "Canonical room context.",
                    "score": 0.91,
                    "source_path": "canon/goc.md",
                    "content_class": "published_canon",
                }
            ],
        },
        "visible_output_bundle": {
            "scene_blocks": [{"type": "narrator", "text": "Generated opening."}],
        },
    }

    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state=graph_state,
        event=event,
    )

    adapter.record_generation.assert_called_once()
    assert adapter.record_generation.call_args.kwargs["name"] == "story.model.generation"
    assert adapter.record_generation.call_args.kwargs["usage_details"] == {"input": 12, "output": 8, "total": 20}
    adapter.record_retrieval.assert_called_once()
    assert adapter.record_retrieval.call_args.kwargs["documents"][0]["id"] == "chunk-1"
    score_names = {call.kwargs["name"] for call in adapter.add_score.call_args_list}
    assert "live_runtime_contract_pass" in score_names
