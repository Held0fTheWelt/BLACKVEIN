from __future__ import annotations

import hashlib
import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from app.story_runtime.manager import (
    _emit_langfuse_evidence_observations,
    _emit_langfuse_path_spans,
)


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
    """MVP4-aligned God of Carnage solo projection (see test_mvp4_contract_opening_truthfulness).

    With ``generation_execution_mode: mock_only``, the live graph often still cannot
    pack structured mock output into ``live_scene_blocks`` via
    ``_live_scene_blocks_from_visible_bundle`` — the runtime then legitimately takes
    the LDSS fallback branch (``story.phase.ldss_fallback`` span, degraded opening).
    Tests that require a **live envelope without that fallback** monkeypatch
    ``_live_scene_blocks_from_visible_bundle`` to return synthetic blocks (see
    ``test_story_session_create_opening_live_projection_skips_ldss_fallback_span``).
    """
    return {
        "module_id": "god_of_carnage",
        "module_version": "1.0.0",
        "start_scene_id": "scene_1_opening",
        "human_actor_id": "veronique",
        "npc_actor_ids": ["michel", "annette", "alain"],
        "actor_lanes": {
            "veronique": "human",
            "michel": "npc",
            "annette": "npc",
            "alain": "npc",
        },
        "selected_player_role": "veronique",
        "character_ids": ["veronique", "michel", "annette", "alain"],
        "runtime_profile_id": "god_of_carnage_solo",
        "runtime_module_id": "solo_story_runtime",
        "content_module_id": "god_of_carnage",
    }


def _minimal_goc_live_scene_blocks(*, turn_number: int) -> list[dict[str, Any]]:
    """Synthetic live-runtime blocks for tests that must skip the LDSS fallback branch."""
    delivery = {
        "mode": "typewriter",
        "characters_per_second": 44,
        "pause_before_ms": 150,
        "pause_after_ms": 650,
        "skippable": True,
    }
    return [
        {
            "id": f"turn-{turn_number}-live-block-1",
            "block_type": "narrator",
            "speaker_label": "Narrator",
            "actor_id": None,
            "target_actor_id": None,
            "text": "The salon waits in strained silence.",
            "delivery": delivery,
            "source": "live_runtime_graph",
        },
        {
            "id": f"turn-{turn_number}-live-block-2",
            "block_type": "actor_line",
            "speaker_label": "Michel",
            "actor_id": "michel",
            "target_actor_id": None,
            "text": "We should speak calmly.",
            "delivery": delivery,
            "source": "live_runtime_graph",
        },
    ]


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
    """Langfuse parent span + path spans for opening; mock stack LDSS fallback is first-class evidence.

    Under ``mock_only`` the runtime commonly reaches ``adapter=ldss_fallback`` because
    ``_live_scene_blocks_from_visible_bundle`` yields nothing until LDSS packs blocks —
    that is **not** a tracing bug. This test asserts wiring + explicit fallback span
    ``story.phase.ldss_fallback`` and deterministic scores that stay red on contract gate.
    """
    adapter = MagicMock()
    adapter.is_ready = True
    adapter.is_enabled.return_value = True
    adapter.config = SimpleNamespace(environment="test")
    adapter.get_active_span.return_value = None

    root_span = MagicMock()
    adapter.start_span_in_trace.return_value = root_span
    adapter.create_child_span.side_effect = lambda **kwargs: MagicMock()

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
    body = response.json()
    session_id = body["session_id"]
    opening = body.get("opening_turn") or {}
    path_summary = opening.get("observability_path_summary") if isinstance(opening, dict) else {}
    gov = opening.get("runtime_governance_surface") if isinstance(opening, dict) else {}

    # Fallback path (mock stack): explicit LDSS-after-live-opening evidence (canonical
    # degradation_signals may only retain non_factual_staging — assert durable fields too.)
    assert isinstance(path_summary, dict)
    assert path_summary.get("generation_fallback_used") is True
    raw_signals: list[str] = []
    raw_signals.extend(path_summary.get("degradation_signals") or [])
    if isinstance(gov, dict):
        raw_signals.extend(gov.get("degradation_signals") or [])
    val = opening.get("validation_outcome") if isinstance(opening, dict) else {}
    assert isinstance(val, dict)
    assert val.get("reason") == "ldss_fallback_after_live_opening_failure"
    assert path_summary.get("adapter") == "ldss_fallback"
    assert path_summary.get("adapter_invocation_mode") == "ldss_fallback_after_live_opening_failure"
    gov_signals = gov.get("degradation_signals") or [] if isinstance(gov, dict) else []
    assert "non_factual_staging" in raw_signals or "non_factual_staging" in gov_signals

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
    assert "story.phase.ldss_fallback" in created_child_names
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
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values.get("fallback_absent") == 0.0
    assert score_values.get("live_runtime_contract_pass") == 0.0
    assert score_values.get("live_runtime_visible_surface_pass") == 0.0
    root_span.end.assert_called_once()
    adapter.flush.assert_called_once()


def test_story_session_create_opening_live_projection_skips_ldss_fallback_span(
    client, internal_api_key, monkeypatch
):
    """No ``story.phase.ldss_fallback`` when live scene blocks are projected (test doubles).

    ``_ldss_opening_fallback_state`` sets ``force_ldss_scene_fallback`` which would skip
    block extraction; we clear that flag after the real helper and return synthetic
    live blocks from ``_live_scene_blocks_from_visible_bundle`` so ``_finalize_committed_turn``
    takes the live envelope branch (still ``mock_only`` — contract gate scores unchanged).
    """
    from app.story_runtime.manager import StoryRuntimeManager

    adapter = MagicMock()
    adapter.is_ready = True
    adapter.is_enabled.return_value = True
    adapter.config = SimpleNamespace(environment="test")
    adapter.get_active_span.return_value = None

    root_span = MagicMock()
    adapter.start_span_in_trace.return_value = root_span
    adapter.create_child_span.side_effect = lambda **kwargs: MagicMock()

    monkeypatch.setattr(
        "app.observability.langfuse_adapter.LangfuseAdapter.get_instance",
        lambda: adapter,
    )

    _orig_fb = StoryRuntimeManager._ldss_opening_fallback_state

    def _strip_force_ldss_flag(self, graph_state: dict[str, Any], *, reason: str):
        out = _orig_fb(self, graph_state, reason=reason)
        out.pop("force_ldss_scene_fallback", None)
        return out

    monkeypatch.setattr(
        StoryRuntimeManager,
        "_ldss_opening_fallback_state",
        _strip_force_ldss_flag,
    )

    def _patched_live_blocks(
        visible_output_bundle: dict[str, Any] | None,
        *,
        turn_number: int,
    ) -> list[dict[str, Any]]:
        return _minimal_goc_live_scene_blocks(turn_number=turn_number)

    monkeypatch.setattr(
        "app.story_runtime.manager._live_scene_blocks_from_visible_bundle",
        _patched_live_blocks,
    )

    langfuse_trace_id = "abcdef0123456789abcdef0123456789"
    response = client.post(
        "/api/story/sessions",
        headers={
            "X-Play-Service-Key": internal_api_key,
            "X-Langfuse-Trace-Id": langfuse_trace_id,
        },
        json={"module_id": "god_of_carnage", "runtime_projection": _goc_projection()},
    )
    assert response.status_code == 200
    opening = response.json().get("opening_turn") or {}
    path_summary = opening.get("observability_path_summary") if isinstance(opening, dict) else {}
    gov = opening.get("runtime_governance_surface") if isinstance(opening, dict) else {}

    created_child_names = [call.kwargs["name"] for call in adapter.create_child_span.call_args_list]
    assert "story.phase.ldss_fallback" not in created_child_names

    assert isinstance(path_summary, dict)
    assert isinstance(gov, dict)
    # Path summary may still show adapter=ldss_fallback / generation_fallback_used after the real
    # opening fallback policy ran — this test targets the **phase span** ``story.phase.ldss_fallback``,
    # which must not fire once live scene projection succeeds in ``_finalize_committed_turn``.


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
    assert "live_runtime_visible_surface_pass" in score_names


def test_langfuse_visible_output_counts_gm_narration_when_scene_blocks_absent(monkeypatch):
    """Opening-style bundles may expose prose via gm_narration without scene_blocks yet."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        "session_id": "session-opening-surface",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "generation_fallback_used": False,
        "retrieval_context_attached": True,
        "usage_details": {"input": 10, "output": 5, "total": 15},
        "actor_lane_validation_status": "approved",
        "quality_class": "healthy",
        "degradation_signals": [],
    }
    graph_state = {"model_prompt": "Opening prompt."}
    event = {
        "model_route": {
            "generation": {
                "metadata": {"adapter": "openai", "model": "gpt-test"},
            }
        },
        "visible_output_bundle": {
            "gm_narration": ["Le salon est silencieux."],
        },
    }
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state=graph_state,
        event=event,
    )
    scores_by_name = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert scores_by_name.get("visible_output_present") == 1.0
    assert scores_by_name.get("live_runtime_visible_surface_pass") == 1.0


def test_langfuse_visible_output_counts_structured_narrative_without_bundle_lines(monkeypatch):
    """Opening may expose prose only under generation.metadata.structured_output."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        "session_id": "session-structured-surface",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "generation_fallback_used": False,
        "retrieval_context_attached": True,
        "usage_details": {"input": 100, "output": 50, "total": 150},
        "actor_lane_validation_status": "approved",
        "quality_class": "healthy",
        "degradation_signals": [],
    }
    graph_state = {"model_prompt": "x"}
    event = {
        "model_route": {
            "generation": {
                "content": "",
                "metadata": {
                    "adapter": "openai",
                    "structured_output": {
                        "narrative_response": "Le salon attend.",
                    },
                },
            }
        },
        "visible_output_bundle": {},
    }
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state=graph_state,
        event=event,
    )
    scores_by_name = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert scores_by_name.get("visible_output_present") == 1.0


def _last_score_metadata_for(adapter, score_name: str) -> dict:
    """Return the metadata kwargs of the last ``add_score`` call for ``score_name``."""
    for call in reversed(adapter.add_score.call_args_list):
        if call.kwargs.get("name") == score_name:
            return call.kwargs.get("metadata") or {}
    raise AssertionError(f"No add_score call recorded for {score_name!r}")


def test_langfuse_score_metadata_surfaces_canonical_degradation_chain_for_ldss_fallback_after_live_opening_failure(monkeypatch):
    """Karte 6: score.metadata must expose the operative causation chain.

    Ground truth for the LDSS-fallback-after-live-opening-failure path:
      - canonical ``degradation_signals`` keep the ai_stack contract (filtered to
        ``DEGRADATION_SIGNAL_VALUES``) -> only ``non_factual_staging`` here.
      - ``degradation_chain`` orders the operator-facing causation
        ``[live_opening_failure_reason, ldss_fallback_after_live_opening_failure,
        non_factual_staging]`` so dashboards/alerts can read the full story.
      - ``degradation_summary`` carries a human-readable prose sentence.
      - ``live_opening_failure_reason`` is exposed verbatim for alert keys.
    Live-Gate booleans are unaffected: this only enriches score metadata.
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        "session_id": "session-6871-fallback",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "adapter": "ldss_fallback",
        "adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
        "selected_model": "openai_gpt_5_4_mini",
        "generation_fallback_used": True,
        "retrieval_context_attached": True,
        "usage_details": {"input": 100, "output": 50, "total": 150},
        "actor_lane_validation_status": "approved",
        "quality_class": "degraded",
        "degradation_signals": [
            "ldss_fallback_after_live_opening_failure",
            "non_factual_staging",
        ],
        "degradation_summary": "dramatic_effect_reject_empty_fluency",
        "live_opening_failure_reason": "dramatic_effect_reject_empty_fluency",
    }
    graph_state = {"model_prompt": "Opening prompt."}
    event = {
        "model_route": {
            "generation": {
                "metadata": {
                    "adapter": "ldss_fallback",
                    "adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
                    "live_opening_failure_reason": "dramatic_effect_reject_empty_fluency",
                },
            }
        },
        "visible_output_bundle": {
            "scene_blocks": [{"type": "narrator", "text": "Le salon attend."}],
        },
    }
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state=graph_state,
        event=event,
    )

    score_names = {call.kwargs["name"] for call in adapter.add_score.call_args_list}
    assert "live_runtime_contract_pass" in score_names

    metadata = _last_score_metadata_for(adapter, "live_runtime_contract_pass")
    assert metadata["session_id"] == "session-6871-fallback"
    assert metadata["quality_class"] == "degraded"

    assert metadata["degradation_signals"] == ["non_factual_staging"], (
        "Canonical contract: only DEGRADATION_SIGNAL_VALUES entries belong here. "
        "ldss_fallback_after_live_opening_failure is NOT canonical and must move "
        "to degradation_chain instead."
    )

    assert metadata["live_opening_failure_reason"] == "dramatic_effect_reject_empty_fluency"

    assert metadata["degradation_chain"] == [
        "dramatic_effect_reject_empty_fluency",
        "ldss_fallback_after_live_opening_failure",
        "non_factual_staging",
    ], (
        "Operator-facing chain order is cause -> action -> consequence. Any drift "
        "breaks alerts/dashboards that key on the chain ordering."
    )

    assert metadata["degradation_summary"] == (
        "Live opening failed dramatic-effect validation and fell back to LDSS; "
        "visible output exists but is degraded/fallback."
    )

    for score_name in (
        "non_mock_generation_pass",
        "fallback_absent",
        "live_runtime_visible_surface_pass",
        "live_runtime_contract_pass",
    ):
        assert score_name in score_names
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["non_mock_generation_pass"] == 0.0
    assert score_values["fallback_absent"] == 0.0
    assert score_values["live_runtime_visible_surface_pass"] == 0.0
    assert score_values["live_runtime_contract_pass"] == 0.0


def test_langfuse_score_metadata_omits_chain_extras_for_healthy_path(monkeypatch):
    """Healthy path keeps degradation_signals empty, chain empty, summary='none'."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        "session_id": "session-healthy",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "adapter": "openai",
        "selected_model": "gpt-test",
        "generation_fallback_used": False,
        "retrieval_context_attached": True,
        "usage_details": {"input": 10, "output": 5, "total": 15},
        "actor_lane_validation_status": "approved",
        "quality_class": "healthy",
        "degradation_signals": [],
        "degradation_summary": None,
        "live_opening_failure_reason": None,
    }
    graph_state = {"model_prompt": "Opening prompt."}
    event = {
        "model_route": {
            "generation": {"metadata": {"adapter": "openai", "model": "gpt-test"}},
        },
        "visible_output_bundle": {
            "scene_blocks": [{"type": "narrator", "text": "Le salon attend."}],
        },
    }
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state=graph_state,
        event=event,
    )

    metadata = _last_score_metadata_for(adapter, "live_runtime_contract_pass")
    assert metadata["degradation_signals"] == []
    assert metadata["degradation_chain"] == []
    assert metadata["degradation_summary"] == "none"
    assert metadata["live_opening_failure_reason"] is None


def test_world_engine_turn_execute_langfuse_correlates_player_input_hash(
    client, internal_api_key, monkeypatch
):
    """ADR-0033 §13.6: world-engine.turn.execute carries same non-PII digest as backend.turn.execute."""
    adapter = MagicMock()
    adapter.is_ready = True
    adapter.is_enabled.return_value = True
    adapter.config = SimpleNamespace(environment="test")
    adapter.get_active_span.return_value = None

    create_root = MagicMock()
    turn_root = MagicMock()
    adapter.start_span_in_trace.side_effect = [create_root, turn_root]
    adapter.create_child_span.side_effect = lambda **kwargs: MagicMock()

    monkeypatch.setattr(
        "app.observability.langfuse_adapter.LangfuseAdapter.get_instance",
        lambda: adapter,
    )

    langfuse_trace_id = "fedcba9876543210fedcba9876543210"
    player_line = "Ich lehne mich zum Fenster."

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

    turn_resp = client.post(
        f"/api/story/sessions/{session_id}/turns",
        headers={
            "X-Play-Service-Key": internal_api_key,
            "X-Langfuse-Trace-Id": langfuse_trace_id,
        },
        json={"player_input": player_line},
    )
    assert turn_resp.status_code == 200

    turn_calls = [
        c
        for c in adapter.start_span_in_trace.call_args_list
        if c.kwargs.get("name") == "world-engine.turn.execute"
    ]
    assert len(turn_calls) == 1
    kw = turn_calls[0].kwargs
    assert kw["trace_id"] == langfuse_trace_id
    expected = hashlib.sha256(player_line.encode("utf-8")).hexdigest()
    assert kw["input"]["player_input_sha256"] == expected
    assert kw["input"]["player_input_length"] == len(player_line)
    assert kw["metadata"]["player_input_sha256"] == expected
    assert kw["metadata"]["player_input_length"] == len(player_line)

    out_kw = [c.kwargs for c in turn_root.update.call_args_list if "output" in c.kwargs]
    assert out_kw, "turn span should receive update(output=...) after execute_turn"
    assert any(
        o["output"].get("player_input_sha256") == expected
        and o["output"].get("player_input_length") == len(player_line)
        for o in out_kw
    )


def test_ldss_opening_fallback_state_captures_primary_attempt_and_final_adapter():
    """ADR-0033 §13.10: LDSS fallback state preserves primary attempt evidence.

    Operators must be able to read from generation.metadata alone:
      - primary live route was attempted (provider=openai, adapter=openai,
        api model=gpt-5-mini, invocation mode=langchain_structured_primary),
      - the final committed adapter is ldss_fallback after live opening failure,
      - the precise fallback_reason that triggered the policy.
    """
    from app.story_runtime.manager import StoryRuntimeManager
    from story_runtime_core.model_registry import ModelRegistry

    mgr = StoryRuntimeManager(registry=ModelRegistry(), adapters={})
    graph_state = {
        "validation_outcome": {"status": "approved", "reason": "seam_ok"},
        "routing": {
            "selected_provider": "openai",
            "selected_model": "openai_gpt_5_4_mini",
        },
        "generation": {
            "success": True,
            "metadata": {
                "adapter": "openai",
                "model": "gpt-5-mini",
                "adapter_invocation_mode": "langchain_structured_primary",
            },
        },
    }
    out = mgr._ldss_opening_fallback_state(
        graph_state, reason="dramatic_effect_reject_empty_fluency"
    )
    meta = out["generation"]["metadata"]

    assert meta["adapter"] == "ldss_fallback"
    assert meta["adapter_invocation_mode"] == "ldss_fallback_after_live_opening_failure"
    assert meta["final_adapter"] == "ldss_fallback"
    assert meta["final_adapter_invocation_mode"] == "ldss_fallback_after_live_opening_failure"
    assert meta["fallback_reason"] == "dramatic_effect_reject_empty_fluency"
    assert meta["live_opening_failure_reason"] == "dramatic_effect_reject_empty_fluency"
    assert meta["ldss_fallback_after_live_opening_failure"] is True

    assert meta["primary_attempt_adapter"] == "openai"
    assert meta["primary_attempt_model"] == "gpt-5-mini"
    assert meta["primary_attempt_invocation_mode"] == "langchain_structured_primary"
    assert meta["primary_attempt_provider"] == "openai"
    assert meta["primary_attempt_selected_model"] == "openai_gpt_5_4_mini"


def test_ldss_opening_fallback_state_does_not_invent_primary_when_already_fallback():
    """If the prior generation had no real primary adapter, no primary_attempt_adapter is set.

    Prevents synthetic ``primary_attempt_adapter=ldss_fallback`` self-references
    on retry loops where the prior state was already a fallback shell.
    """
    from app.story_runtime.manager import StoryRuntimeManager
    from story_runtime_core.model_registry import ModelRegistry

    mgr = StoryRuntimeManager(registry=ModelRegistry(), adapters={})
    graph_state = {
        "validation_outcome": {"status": "approved", "reason": "seam_ok"},
        "generation": {"metadata": {"adapter": "ldss_fallback"}},
    }
    out = mgr._ldss_opening_fallback_state(graph_state, reason="x")
    meta = out["generation"]["metadata"]
    assert meta["adapter"] == "ldss_fallback"
    assert meta["final_adapter"] == "ldss_fallback"
    assert "primary_attempt_adapter" not in meta
    assert "primary_attempt_model" not in meta
    assert "primary_attempt_invocation_mode" not in meta


def _last_span_output_for(adapter, span_name: str) -> dict:
    """Return the ``output`` kwarg of the last ``create_child_span`` call for ``span_name``."""
    for call in reversed(adapter.create_child_span.call_args_list):
        if call.kwargs.get("name") == span_name:
            return call.kwargs.get("output") or {}
    raise AssertionError(f"No create_child_span call recorded for {span_name!r}")


def test_langfuse_score_metadata_surfaces_primary_vs_final_for_ldss_opening_fallback(monkeypatch):
    """ADR-0033 §13.10: score metadata + invoke/fallback spans expose primary-vs-final.

    For an LDSS-fallback-after-live-opening-failure path, all of these must be
    operator-readable without joining traces:
      - primary_attempt_adapter / primary_attempt_model / primary_attempt_provider
      - final_adapter == ldss_fallback
      - fallback_reason == live_opening_failure_reason
      - ldss_fallback_after_live_opening_failure == True
    Live-Gate booleans remain unchanged (still red on this fixture).
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        "session_id": "session-primary-vs-final-fallback",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "adapter": "ldss_fallback",
        "api_model": "gpt-5-mini",
        "adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
        "selected_provider": "openai",
        "selected_model": "openai_gpt_5_4_mini",
        "primary_attempt_adapter": "openai",
        "primary_attempt_model": "gpt-5-mini",
        "primary_attempt_provider": "openai",
        "primary_attempt_selected_model": "openai_gpt_5_4_mini",
        "primary_attempt_invocation_mode": "langchain_structured_primary",
        "final_adapter": "ldss_fallback",
        "final_adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
        "fallback_reason": "dramatic_effect_reject_empty_fluency",
        "ldss_fallback_after_live_opening_failure": True,
        "generation_fallback_used": True,
        "retrieval_context_attached": True,
        "usage_details": {"input": 100, "output": 50, "total": 150},
        "actor_lane_validation_status": "approved",
        "quality_class": "degraded",
        "degradation_signals": [
            "ldss_fallback_after_live_opening_failure",
            "non_factual_staging",
        ],
        "degradation_summary": "dramatic_effect_reject_empty_fluency",
        "live_opening_failure_reason": "dramatic_effect_reject_empty_fluency",
    }
    graph_state = {"model_prompt": "Opening prompt."}
    event = {
        "model_route": {
            "generation": {
                "metadata": {
                    "adapter": "ldss_fallback",
                    "adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
                    "primary_attempt_adapter": "openai",
                    "primary_attempt_model": "gpt-5-mini",
                    "primary_attempt_invocation_mode": "langchain_structured_primary",
                    "final_adapter": "ldss_fallback",
                    "final_adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
                    "fallback_reason": "dramatic_effect_reject_empty_fluency",
                    "ldss_fallback_after_live_opening_failure": True,
                    "live_opening_failure_reason": "dramatic_effect_reject_empty_fluency",
                },
            }
        },
        "visible_output_bundle": {
            "scene_blocks": [{"type": "narrator", "text": "Le salon attend."}],
        },
    }
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state=graph_state,
        event=event,
    )

    metadata = _last_score_metadata_for(adapter, "live_runtime_contract_pass")
    assert metadata["primary_attempt_adapter"] == "openai"
    assert metadata["primary_attempt_model"] == "gpt-5-mini"
    assert metadata["primary_attempt_provider"] == "openai"
    assert metadata["primary_attempt_invocation_mode"] == "langchain_structured_primary"
    assert metadata["final_adapter"] == "ldss_fallback"
    assert metadata["final_adapter_invocation_mode"] == "ldss_fallback_after_live_opening_failure"
    assert metadata["fallback_reason"] == "dramatic_effect_reject_empty_fluency"
    assert metadata["ldss_fallback_after_live_opening_failure"] is True

    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["non_mock_generation_pass"] == 0.0
    assert score_values["fallback_absent"] == 0.0
    assert score_values["live_runtime_visible_surface_pass"] == 0.0
    assert score_values["live_runtime_contract_pass"] == 0.0

    adapter.record_generation.assert_not_called()


def test_langfuse_phase_spans_surface_primary_vs_final_for_ldss_opening_fallback(monkeypatch):
    """ADR-0033 §13.10: ``story.phase.model_invoke`` and ``model_fallback`` carry
    enough metadata for operators to reconstruct primary attempt + final commit.

    Phase spans are emitted by ``_emit_langfuse_path_spans``; this test asserts
    the ``output`` payload carries the new primary/final fields.
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )

    path_summary = {
        "session_id": "session-primary-vs-final-spans",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "route_model_called": True,
        "invoke_model_called": True,
        "fallback_model_called": True,
        "selected_provider": "openai",
        "selected_model": "openai_gpt_5_4_mini",
        "adapter": "ldss_fallback",
        "api_model": "gpt-5-mini",
        "adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
        "primary_attempt_adapter": "openai",
        "primary_attempt_model": "gpt-5-mini",
        "primary_attempt_provider": "openai",
        "primary_attempt_selected_model": "openai_gpt_5_4_mini",
        "primary_attempt_invocation_mode": "langchain_structured_primary",
        "final_adapter": "ldss_fallback",
        "final_adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
        "fallback_reason": "dramatic_effect_reject_empty_fluency",
        "ldss_fallback_after_live_opening_failure": True,
        "generation_fallback_used": True,
        "live_opening_failure_reason": "dramatic_effect_reject_empty_fluency",
        "quality_class": "degraded",
        "degradation_signals": [
            "ldss_fallback_after_live_opening_failure",
            "non_factual_staging",
        ],
    }
    _emit_langfuse_path_spans(path_summary)

    invoke_output = _last_span_output_for(adapter, "story.phase.model_invoke")
    assert invoke_output["primary_attempt_adapter"] == "openai"
    assert invoke_output["primary_attempt_model"] == "gpt-5-mini"
    assert invoke_output["primary_attempt_invocation_mode"] == "langchain_structured_primary"
    assert invoke_output["final_adapter"] == "ldss_fallback"
    assert invoke_output["final_adapter_invocation_mode"] == "ldss_fallback_after_live_opening_failure"

    fallback_output = _last_span_output_for(adapter, "story.phase.model_fallback")
    assert fallback_output["fallback_reason"] == "dramatic_effect_reject_empty_fluency"
    assert fallback_output["final_adapter"] == "ldss_fallback"
    assert fallback_output["ldss_fallback_after_live_opening_failure"] is True
    assert fallback_output["live_opening_failure_reason"] == "dramatic_effect_reject_empty_fluency"
    assert fallback_output["primary_attempt_adapter"] == "openai"


def test_langfuse_primary_vs_final_metadata_for_healthy_path_marks_primary_eq_final(monkeypatch):
    """Healthy live path: primary == final, no fallback markers, scores remain 1.0.

    Sanity check that the metadata fields read cleanly on a non-degraded turn so
    operators can trust the absence of ``ldss_fallback_after_live_opening_failure``
    as a real signal of a healthy turn.
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        "session_id": "session-healthy-primary-eq-final",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "adapter": "openai",
        "api_model": "gpt-5-mini",
        "adapter_invocation_mode": "langchain_structured_primary",
        "selected_provider": "openai",
        "selected_model": "openai_gpt_5_4_mini",
        "final_adapter": "openai",
        "final_adapter_invocation_mode": "langchain_structured_primary",
        "fallback_reason": None,
        "ldss_fallback_after_live_opening_failure": False,
        "primary_attempt_provider": "openai",
        "primary_attempt_selected_model": "openai_gpt_5_4_mini",
        "generation_fallback_used": False,
        "retrieval_context_attached": True,
        "usage_details": {"input": 12, "output": 8, "total": 20},
        "actor_lane_validation_status": "approved",
        "quality_class": "healthy",
        "degradation_signals": [],
    }
    graph_state = {"model_prompt": "Opening prompt."}
    event = {
        "model_route": {
            "generation": {
                "metadata": {
                    "adapter": "openai",
                    "model": "gpt-5-mini",
                    "adapter_invocation_mode": "langchain_structured_primary",
                },
            }
        },
        "visible_output_bundle": {
            "scene_blocks": [{"type": "narrator", "text": "Le salon est silencieux."}],
        },
    }
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state=graph_state,
        event=event,
    )

    metadata = _last_score_metadata_for(adapter, "live_runtime_contract_pass")
    assert metadata["final_adapter"] == "openai"
    assert metadata["final_adapter_invocation_mode"] == "langchain_structured_primary"
    assert metadata["fallback_reason"] is None
    assert metadata["ldss_fallback_after_live_opening_failure"] is False
    assert metadata["primary_attempt_provider"] == "openai"

    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["non_mock_generation_pass"] == 1.0
    assert score_values["fallback_absent"] == 1.0
    assert score_values["live_runtime_contract_pass"] == 1.0
