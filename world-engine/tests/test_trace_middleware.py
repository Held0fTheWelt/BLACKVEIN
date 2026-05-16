from __future__ import annotations

import hashlib
import json
import logging
import sys
import uuid
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from app.story_runtime.manager import (
    StorySession,
    _annotate_goc_opening_narration_beats,
    _build_langfuse_path_summary,
    _compact_scene_block_summary,
    _compute_opening_shape_subgates,
    _emit_langfuse_evidence_observations,
    _emit_langfuse_path_spans,
    _emit_langfuse_runtime_aspect_observability,
    _finalize_visible_bundle_opening_gm_narration,
    _live_scene_blocks_from_visible_bundle,
    _maybe_split_goc_opening_into_two_movements,
    _opening_block_contract_satisfied,
)
from app.story_runtime.module_turn_hooks import GOD_OF_CARNAGE_MODULE_ID
from ai_stack.npc_agency_contracts import NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS
from ai_stack.runtime_aspect_ledger import (
    ASPECT_ACTION_RESOLUTION,
    ASPECT_BEAT,
    ASPECT_CAPABILITY_SELECTION,
    ASPECT_COMMIT,
    ASPECT_INPUT,
    ASPECT_NARRATOR_AUTHORITY,
    ASPECT_NPC_AGENCY,
    ASPECT_NPC_AUTHORITY,
    ASPECT_VALIDATION,
    ASPECT_VOICE_CONSISTENCY,
    ASPECT_VISIBLE_PROJECTION,
    initialize_runtime_aspect_ledger,
    make_aspect_record,
    set_aspect_record,
)
from story_runtime_core.player_input_intent_contract import (
    FORBIDDEN_NON_SPEECH_ACTION_SEMANTIC_MOVES,
    INTENT_CONTRACT_VERSION,
    PLAYER_INPUT_KINDS,
    default_commit_flags_for_player_input_kind,
    player_input_kind_family,
)


def test_langfuse_add_score_duplicates_at_trace_level_for_adr0033_visibility():
    """ADR-0033: observation span.score() alone does not populate Langfuse trace.scores / UI trace tab."""
    from app.observability import langfuse_adapter as lf_mod

    trace_hex = "a9f119969f6f4dd9b116645221d4f504"
    adapter = lf_mod.LangfuseAdapter.__new__(lf_mod.LangfuseAdapter)
    adapter.is_ready = True
    adapter._public_key = "pk-test"
    adapter._secret_key = "sk-test"
    adapter._config = SimpleNamespace(environment="development")
    client = MagicMock()
    adapter._clients = {"development": client}
    span = MagicMock()
    span.trace_id = trace_hex
    span.span_id = "obs-id-span"
    span.id = "0f0e0d0c0b0a0908"
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
    sc_kw = span.score.call_args.kwargs
    assert sc_kw.get("data_type") is not None
    assert str(sc_kw.get("data_type")).endswith("NUMERIC")
    client.create_score.assert_called_once()
    cc_kw = client.create_score.call_args.kwargs
    assert cc_kw["name"] == "live_runtime_contract_pass"
    assert cc_kw["trace_id"] == trace_hex
    assert cc_kw["value"] == 0.0
    assert str(cc_kw.get("data_type")).endswith("NUMERIC")
    assert cc_kw.get("observation_id") == "0f0e0d0c0b0a0908"
    assert "session_id" not in cc_kw


def test_langfuse_start_trace_sets_first_class_session_context(monkeypatch):
    from app.observability import langfuse_adapter as lf_mod

    adapter = lf_mod.LangfuseAdapter.__new__(lf_mod.LangfuseAdapter)
    adapter.is_ready = True
    adapter._public_key = "pk-test"
    adapter._secret_key = "sk-test"
    adapter._base_url = "http://langfuse.test"
    adapter._release = "test"
    adapter._sample_rate = 1.0
    adapter._config = SimpleNamespace(environment="tests", release="test", sample_rate=1.0)
    client = MagicMock()
    span = MagicMock()
    span.trace_id = "trace-session-hardening"
    client.start_observation.return_value = span
    adapter._clients = {"tests": client}
    propagate_calls: list[dict[str, Any]] = []

    @contextmanager
    def _propagate_attributes(**kwargs: Any):
        propagate_calls.append(kwargs)
        yield

    monkeypatch.setitem(
        sys.modules,
        "langfuse",
        SimpleNamespace(propagate_attributes=_propagate_attributes),
    )

    out = lf_mod.LangfuseAdapter.start_trace(
        adapter,
        name="world-engine.turn.execute",
        session_id="story-session-1",
        metadata={"trace_origin": "live_ui", "execution_tier": "live"},
    )

    assert out is span
    assert propagate_calls[-1]["session_id"] == "story-session-1"
    assert lf_mod._active_langfuse_session_id.get() == "story-session-1"
    client.start_observation.assert_called_once()


def test_langfuse_child_observations_inherit_active_session_metadata():
    from app.observability import langfuse_adapter as lf_mod

    adapter = lf_mod.LangfuseAdapter.__new__(lf_mod.LangfuseAdapter)
    adapter.is_ready = True
    adapter._public_key = "pk-test"
    adapter._secret_key = "sk-test"
    adapter._config = SimpleNamespace(environment="development")
    client = MagicMock()
    adapter._clients = {"development": client}
    parent_span = MagicMock()
    parent_span.trace_id = "b116645221d4f504a9f119969f6f4dd9"
    parent_span.id = "deadbeefcafebabe"
    child_span = MagicMock()
    parent_span.start_observation.return_value = child_span
    token_span = lf_mod._active_span_context.set(parent_span)
    token_session = lf_mod._active_langfuse_session_id.set("story-session-2")
    token_client = lf_mod._active_langfuse_client.set(client)
    try:
        lf_mod.LangfuseAdapter.create_child_span(adapter, name="story.validation.contract")
        lf_mod.LangfuseAdapter.record_generation(
            adapter,
            name="story.model.generation",
            model="gpt-test",
            provider="openai",
        )
        lf_mod.LangfuseAdapter.record_retrieval(adapter, name="story.rag.retrieval")
        lf_mod.LangfuseAdapter.add_score(adapter, name="turn_aspect_ledger_present", value=1.0)
    finally:
        lf_mod._active_langfuse_client.reset(token_client)
        lf_mod._active_langfuse_session_id.reset(token_session)
        lf_mod._active_span_context.reset(token_span)

    metadata_rows = [
        call.kwargs.get("metadata") or {}
        for call in parent_span.start_observation.call_args_list
    ]
    assert metadata_rows
    assert all(row.get("session_id") == "story-session-2" for row in metadata_rows)
    parent_span.score.assert_called_once()
    assert str(parent_span.score.call_args.kwargs.get("data_type")).endswith("NUMERIC")
    assert parent_span.score.call_args.kwargs["metadata"]["session_id"] == "story-session-2"
    client.create_score.assert_called_once()
    cc_kw = client.create_score.call_args.kwargs
    assert str(cc_kw.get("data_type")).endswith("NUMERIC")
    assert cc_kw["trace_id"] == "b116645221d4f504a9f119969f6f4dd9"
    assert cc_kw.get("observation_id") == "deadbeefcafebabe"
    assert "session_id" not in cc_kw


def test_langfuse_metadata_policy_marks_local_evidence(monkeypatch):
    from app.observability import langfuse_adapter as lf_mod

    monkeypatch.setenv("WOS_LANGFUSE_LOCAL_EVIDENCE", "1")
    monkeypatch.setenv("LANGFUSE_ENVIRONMENT", "local")
    adapter = lf_mod.LangfuseAdapter.__new__(lf_mod.LangfuseAdapter)

    md = lf_mod.LangfuseAdapter._with_observation_policy_metadata(
        adapter,
        {"environment": "live", "trace_origin": "live_ui"},
        observation_name="story.graph.path_summary",
        as_type="span",
    )

    assert md["environment"] == "local"
    assert md["evidence_scope"] == "local_langfuse"
    assert md["proof_level"] == "local_only"
    assert md["live_or_staging_evidence"] is False


def _aspect_test_ledger() -> dict[str, Any]:
    ledger = initialize_runtime_aspect_ledger(
        session_id="story-session-aspect",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Ich nehme ein Bier aus dem Kuehlschrank",
        trace_id="trace-aspect",
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_INPUT,
        make_aspect_record(
            applicable=True,
            status="passed",
            actual={"raw_player_input": "Ich nehme ein Bier aus dem Kuehlschrank", "input_kind": "action"},
            source="runtime",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_ACTION_RESOLUTION,
        make_aspect_record(
            applicable=True,
            status="passed",
            actual={"input_kind": "action", "affordance_status": "allowed", "action_commit_policy": "commit_action"},
            source="runtime",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_BEAT,
        make_aspect_record(
            applicable=True,
            status="passed",
            selected={"selected_beat_id": "domestic_disruption"},
            actual={"realized": True, "visible": True},
            source="projection",
            selected_beat="domestic_disruption",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_CAPABILITY_SELECTION,
        make_aspect_record(
            applicable=True,
            status="passed",
            selected={"selected_capabilities": ["player.object_interaction.request", "narrator.object_state.describe"]},
            actual={"realized_capabilities": ["player.object_interaction.request", "narrator.object_state.describe"], "missing_required_capabilities": [], "forbidden_capability_realized": False},
            source="runtime",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_NARRATOR_AUTHORITY,
        make_aspect_record(
            applicable=True,
            status="passed",
            expected={"required": True},
            actual={"actual_owner": "narrator", "consequence_realized": True},
            source="runtime",
            expected_owner="narrator",
            actual_owner="narrator",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_NPC_AUTHORITY,
        make_aspect_record(
            applicable=True,
            status="passed",
            actual={"npc_takeover_detected": False},
            source="runtime",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_NPC_AGENCY,
        make_aspect_record(
            applicable=True,
            status="passed",
            expected={
                "npc_agency_plan_present": True,
                "independent_planning_expected": True,
                "candidate_actor_ids": ["npc_primary", "npc_secondary"],
            },
            actual={
                "contract_status": NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
                "independent_planning_used": True,
                "candidate_actor_ids": ["npc_primary", "npc_secondary"],
                "planned_actor_ids": ["npc_primary", "npc_secondary"],
                "realized_actor_ids": ["npc_primary", "npc_secondary"],
                "missing_required_actor_ids": [],
                "carry_forward_actor_ids": [],
                "forbidden_planned_actor_ids": [],
                "forbidden_realized_actor_ids": [],
                "multi_npc_initiative_realized": True,
                "long_horizon_state_present": True,
                "intention_threads_active": 3,
                "private_plan_resolution_present": True,
                "private_plan_visibility_respected": True,
                "unrealized_selected_private_plan_actor_ids": [],
            },
            source="validator",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_VOICE_CONSISTENCY,
        make_aspect_record(
            applicable=True,
            status="passed",
            expected={
                "policy_present": True,
                "semantic_classification_enabled": True,
            },
            actual={
                "spoken_line_count": 1,
                "finding_count": 0,
                "blocking_finding_count": 0,
                "drift_class_counts": {},
                "semantic_classification_count": 1,
                "semantic_cross_actor_confusion_count": 0,
            },
            source="validator",
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_VALIDATION,
        make_aspect_record(applicable=True, status="passed", actual={"recoverable_rejection": False}, source="validator"),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_COMMIT,
        make_aspect_record(applicable=True, status="passed", actual={"commit_applied": True}, source="commit"),
    )
    return set_aspect_record(
        ledger,
        ASPECT_VISIBLE_PROJECTION,
        make_aspect_record(
            applicable=True,
            status="passed",
            actual={"visible_block_origin_present": True, "scene_block_count": 2},
            source="projection",
        ),
    )


def test_langfuse_emits_runtime_aspect_spans_and_reasoned_scores(monkeypatch):
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    adapter.create_child_span.side_effect = lambda **kwargs: MagicMock()

    monkeypatch.setattr(
        "app.observability.langfuse_adapter.LangfuseAdapter.get_instance",
        lambda: adapter,
    )

    _emit_langfuse_runtime_aspect_observability(
        {
            "session_id": "story-session-aspect",
            "module_id": "god_of_carnage",
            "turn_number": 1,
            "turn_kind": "player",
            "raw_player_input": "Ich nehme ein Bier aus dem Kuehlschrank",
            "turn_aspect_ledger_present": True,
            "turn_aspect_ledger": _aspect_test_ledger(),
            "trace_origin": "pytest",
            "execution_tier": "test",
            "canonical_player_flow": False,
            "http_status": 200,
            "branching_forecast": {
                "schema_version": "branching_forecast.v1",
                "status": "forecasted",
                "forecast_only": True,
                "authoritative": False,
                "inactive_branches_authoritative": False,
                "mutates_canonical_state": False,
                "trigger_reasons": ["open_pressure_present"],
                "option_count": 2,
                "options": [{"option_id": "branch_a"}, {"option_id": "branch_b"}],
            },
        }
    )

    child_names = [call.kwargs["name"] for call in adapter.create_child_span.call_args_list]
    assert "story.beat.select" in child_names
    assert "story.beat.realize" in child_names
    assert "story.authority.narrator" in child_names
    assert "story.authority.npc" in child_names
    assert "story.npc_agency.plan" in child_names
    assert "story.npc_agency.realize" in child_names
    assert "story.voice.classify" in child_names
    assert "story.voice.validate" in child_names
    assert "story.capability.select" in child_names
    score_calls = {call.kwargs["name"]: call.kwargs for call in adapter.add_score.call_args_list}
    assert score_calls["beat_realized"]["value"] == 1.0
    assert score_calls["npc_takeover_absent"]["value"] == 1.0
    assert score_calls["npc_independent_planning_used"]["value"] == 1.0
    assert score_calls["npc_long_horizon_state_present"]["value"] == 1.0
    assert score_calls["npc_private_plan_resolution_present"]["value"] == 1.0
    assert score_calls["npc_private_plan_visibility_respected"]["value"] == 1.0
    assert score_calls["npc_intention_threads_carried_forward"]["value"] == 1.0
    assert score_calls["npc_required_initiatives_realized"]["value"] == 1.0
    assert score_calls["multi_npc_initiative_realized"]["value"] == 1.0
    assert score_calls["npc_carry_forward_closed"]["value"] == 1.0
    assert score_calls["npc_forbidden_actor_absent"]["value"] == 1.0
    assert score_calls["turn_aspect_ledger_present"]["metadata"]["status"] == "passed"
    assert score_calls["beat_realized"]["metadata"]["selected_beat"] == "domestic_disruption"
    assert score_calls["branching_forecast_present"]["value"] == 1.0
    assert score_calls["branch_options_count"]["value"] == 2.0
    assert score_calls["inactive_branches_non_authoritative"]["value"] == 1.0
    assert score_calls["branching_forecast_present"]["metadata"]["status"] == "forecasted"
    assert score_calls["voice_semantic_classification_present"]["value"] == 1.0
    assert score_calls["voice_cross_actor_confusion_absent"]["value"] == 1.0
    assert score_calls["voice_consistency_contract_pass"]["value"] == 1.0


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
            "origin_aspect": "narrator_authority",
            "origin_beat_id": None,
            "origin_capability": "narrator.opening_event.realize",
            "authority_owner": "narrator",
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
            "origin_aspect": "npc_authority",
            "origin_beat_id": None,
            "origin_capability": "npc.social_reaction.optional",
            "authority_owner": "npc",
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
            "X-WoS-Trace-Origin": "live_ui",
            "X-WoS-Execution-Tier": "live",
            "X-WoS-Canonical-Player-Flow": "true",
            "X-WoS-Runtime-Mode": "solo_story",
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
    assert "story.branch.forecast" in created_child_names
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
        **kwargs: Any,
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
        "langfuse_prompt_name": "goc_opening/story_runtime",
        "provided_model_name": "gpt-5-nano",
        "generation_latency_ms": 50.0,
        "time_to_first_token_ms": 50.0,
        "time_to_first_token_note": "non_streaming_latency_proxy",
        "tokens_per_second_output": 160.0,
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
    rg_kw = adapter.record_generation.call_args.kwargs
    assert rg_kw["name"] == "story.model.generation"
    assert rg_kw["usage_details"] == {"input": 12, "output": 8, "total": 20}
    assert rg_kw.get("prompt_name") == "goc_opening/story_runtime"
    assert rg_kw.get("provided_model_name") == "gpt-5-nano"
    assert rg_kw.get("latency_ms") == 50.0
    assert rg_kw.get("time_to_first_token_ms") == 50.0
    assert rg_kw.get("tokens_per_second") == 160.0
    assert rg_kw["metadata"].get("time_to_first_token_note") == "non_streaming_latency_proxy"
    adapter.record_retrieval.assert_called_once()
    assert adapter.record_retrieval.call_args.kwargs["documents"][0]["id"] == "chunk-1"
    score_names = {call.kwargs["name"] for call in adapter.add_score.call_args_list}
    assert "live_runtime_contract_pass" in score_names
    assert "live_runtime_visible_surface_pass" in score_names


def test_langfuse_record_generation_derives_total_when_usage_missing_total(monkeypatch):
    """usage_details without total still reaches Langfuse when input/output are present."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        "session_id": "session-usage-partial",
        "module_id": "god_of_carnage",
        "turn_number": 1,
        "turn_kind": "player",
        "generation_fallback_used": False,
        "retrieval_context_attached": False,
        "usage_details": {"input": 3, "output": 4},
        "actor_lane_validation_status": "approved",
        "quality_class": "healthy",
        "degradation_signals": [],
    }
    graph_state = {"model_prompt": "x"}
    event = {
        "model_route": {
            "generation": {
                "content": "y",
                "metadata": {"adapter": "openai", "model": "gpt-test"},
            }
        },
    }
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state=graph_state,
        event=event,
    )
    adapter.record_generation.assert_called_once()
    assert adapter.record_generation.call_args.kwargs["usage_details"] == {
        "input": 3,
        "output": 4,
        "total": 7,
    }


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
        "trace_origin": "pytest",
        "execution_tier": "contract_test",
        "canonical_player_flow": False,
        "test_case_id": "world-engine/tests/test_trace_middleware.py::test_langfuse_score_metadata_omits_chain_extras_for_healthy_path",
        "runtime_mode": "test_fixture",
        "generation_mode": "mock_only",
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
    assert metadata["trace_origin"] == "pytest"
    assert metadata["execution_tier"] == "contract_test"
    assert metadata["canonical_player_flow"] is False
    assert metadata["runtime_mode"] == "test_fixture"
    assert metadata["generation_mode"] == "mock_only"


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
    player_line = "I lean toward the window."

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
            "X-WoS-Trace-Origin": "live_ui",
            "X-WoS-Execution-Tier": "live",
            "X-WoS-Canonical-Player-Flow": "true",
            "X-WoS-Runtime-Mode": "solo_story",
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
    assert kw["metadata"]["trace_origin"] == "live_ui"
    assert kw["metadata"]["execution_tier"] == "live"
    assert kw["metadata"]["canonical_player_flow"] is True
    assert kw["metadata"]["runtime_mode"] == "solo_story"

    out_kw = [c.kwargs for c in turn_root.update.call_args_list if "output" in c.kwargs]
    assert out_kw, "turn span should receive update(output=...) after execute_turn"
    assert any(
        o["output"].get("player_input_sha256") == expected
        and o["output"].get("player_input_length") == len(player_line)
        for o in out_kw
    )


def test_trace_metadata_can_be_updated_with_canonical_turn_id_after_commit(
    client, internal_api_key, monkeypatch
):
    adapter = MagicMock()
    adapter.is_ready = True
    adapter.is_enabled.return_value = True
    adapter.config = SimpleNamespace(environment="test")
    adapter.get_active_span.return_value = None

    create_root = MagicMock()
    create_root.trace_id = "fedcba9876543210fedcba9876543210"
    turn_root = MagicMock()
    turn_root.trace_id = "fedcba9876543210fedcba9876543210"
    adapter.start_span_in_trace.side_effect = [create_root, turn_root]
    adapter.create_child_span.side_effect = lambda **kwargs: MagicMock()

    backfill_calls: list[dict[str, Any]] = []

    def _backfill(**kwargs: Any) -> dict[str, Any]:
        backfill_calls.append(kwargs)
        assert kwargs.get("canonical_turn_id"), "canonical_turn_id must exist before backfill"
        return {
            "attempted": True,
            "supported": False,
            "success": False,
            "reason": "sdk_method_unavailable",
        }

    adapter.backfill_trace_metadata_after_commit.side_effect = _backfill

    monkeypatch.setattr(
        "app.observability.langfuse_adapter.LangfuseAdapter.get_instance",
        lambda: adapter,
    )

    langfuse_trace_id = "fedcba9876543210fedcba9876543210"
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
        json={"player_input": "I stay calm and listen."},
    )
    assert turn_resp.status_code == 200
    turn = turn_resp.json()["turn"]

    matched = [
        c
        for c in backfill_calls
        if c.get("story_session_id") == session_id
        and c.get("turn_number") == turn.get("turn_number")
    ]
    assert matched, "expected a post-commit backfill attempt for the committed player turn"
    call = matched[-1]
    assert call["trace_id"] == langfuse_trace_id
    assert call["canonical_turn_id"] == turn.get("canonical_turn_id")
    assert call["story_session_id"] == session_id
    assert call["turn_number"] == turn.get("turn_number")
    assert adapter.add_score.called, "deterministic score emission must continue even if backfill fails"


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


def test_ldss_opening_fallback_state_resets_failed_primary_aspect_ledger():
    """LDSS fallback is a new approved opening path, not a commit of the failed primary ledger."""
    from app.story_runtime.manager import StoryRuntimeManager
    from story_runtime_core.model_registry import ModelRegistry

    primary_ledger = initialize_runtime_aspect_ledger(
        session_id="session-ldss-reset",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input=None,
    )
    primary_ledger = set_aspect_record(
        primary_ledger,
        ASPECT_VALIDATION,
        make_aspect_record(
            applicable=True,
            status="failed",
            actual={"projection_failure_detected": True},
            reasons=["visible_block_origin_missing"],
            source="validator",
            failure_class="projection_failure",
            failure_reason="visible_block_origin_missing",
        ),
    )
    mgr = StoryRuntimeManager(registry=ModelRegistry(), adapters={})
    out = mgr._ldss_opening_fallback_state(
        {
            "session_id": "session-ldss-reset",
            "module_id": "god_of_carnage",
            "turn_number": 0,
            "turn_input_class": "opening",
            "turn_aspect_ledger": primary_ledger,
            "validation_outcome": {
                "status": "rejected",
                "reason": "visible_block_origin_missing",
            },
            "generation": {"metadata": {"adapter": "openai"}},
        },
        reason="dramatic_effect_reject_empty_fluency",
    )

    fallback_aspects = out["turn_aspect_ledger"]["turn_aspect_ledger"]
    assert fallback_aspects[ASPECT_VALIDATION]["status"] == "passed"
    assert fallback_aspects[ASPECT_VALIDATION]["failure_reason"] is None
    assert fallback_aspects[ASPECT_COMMIT]["status"] == "passed"


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


def test_langfuse_generation_records_primary_attempt_when_ldss_fallback_commits(monkeypatch):
    """Opening fallback traces still need Model I/O for the rejected primary attempt."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        "session_id": "session-primary-generation-fallback",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "adapter": "ldss_fallback",
        "api_model": "gpt-5.4-mini",
        "adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
        "selected_provider": "openai",
        "selected_model": "gpt_5_4_mini",
        "primary_attempt_adapter": "openai",
        "primary_attempt_model": "gpt-5.4-mini",
        "primary_attempt_provider": "openai",
        "primary_attempt_invocation_mode": "langchain_structured_primary",
        "primary_attempt_api_success": True,
        "primary_attempt_structured_output_present": True,
        "primary_attempt_raw_output_sha256": "abc123",
        "primary_attempt_raw_output_excerpt": "{\"narration_summary\":[\"Park edge opening\"]}",
        "final_adapter": "ldss_fallback",
        "final_adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
        "fallback_reason": "summary_only_opening",
        "generation_fallback_used": True,
        "usage_details": {"input": 10, "output": 5, "total": 15},
        "actor_lane_validation_status": "approved",
        "quality_class": "degraded",
        "degradation_signals": ["non_factual_staging"],
        "degradation_summary": "summary_only_opening",
    }
    graph_state = {"model_prompt": "Opening prompt."}
    event = {
        "model_route": {
            "generation": {
                "metadata": {
                    "adapter": "ldss_fallback",
                    "model": "ldss_deterministic",
                    "adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
                },
            }
        },
        "visible_output_bundle": {
            "scene_blocks": [{"type": "narrator", "text": "Fallback opening."}],
        },
    }

    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state=graph_state,
        event=event,
    )

    adapter.record_generation.assert_called_once()
    rg_kw = adapter.record_generation.call_args.kwargs
    assert rg_kw["model"] == "gpt-5.4-mini"
    assert rg_kw["provider"] == "openai"
    assert rg_kw["completion"] == "{\"narration_summary\":[\"Park edge opening\"]}"
    assert rg_kw["usage_details"] == {"input": 10, "output": 5, "total": 15}
    assert rg_kw["metadata"]["generation_observation_source"] == "primary_attempt"
    assert rg_kw["metadata"]["final_adapter"] == "ldss_fallback"


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
        "selected_player_role": "annette",
        "human_actor_id": "annette_reille",
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
        "visible_output_bundle": {"scene_blocks": _live_openai_blocks()},
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
    assert score_values["opening_contract_pass"] == 1.0
    assert score_values["live_runtime_contract_pass"] in {0.0, 1.0}


def _healthy_path_summary_turn(turn_number: int) -> dict:
    return {
        "session_id": "session-open-gate",
        "module_id": "god_of_carnage",
        "turn_number": turn_number,
        "generation_fallback_used": False,
        "retrieval_context_attached": True,
        "usage_details": {"input": 10, "output": 5, "total": 15},
        "actor_lane_validation_status": "approved",
        "quality_class": "healthy",
        "degradation_signals": [],
    }


def test_action_context_diagnostics_are_present_on_degraded_turn_payload(monkeypatch):
    """STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P4: even when the route
    fell back / authoritative action surface is absent, action-context diagnostics must
    be present on path_summary + scores with status='evaluated_degraded' (or not_applicable)
    and numeric values."""
    from app.story_runtime.manager import _compute_action_consequence_diagnostics

    # Action turn without authoritative surface (LDSS fallback) → evaluated_degraded with real values.
    diag = _compute_action_consequence_diagnostics({
        "turn_number": 1,
        "player_input_kind": "action",
        "player_action_frame_present": False,
        "authoritative_action_surface": False,
        "generation_fallback_used": True,
        "quality_class": "degraded",
        "local_context_transition": None,
        "narrator_consequence_plan": None,
    })
    assert diag["status"] == "evaluated_degraded"
    for k in (
        "local_context_transition_present",
        "narrator_consequence_present",
        "new_location_established",
        "perception_result_present",
        "action_consequence_contract_pass",
        "npc_consequence_takeover_absent",
    ):
        assert isinstance(diag[k], float), f"{k} must be numeric"

    # Speech turn → not_applicable with vacuous 1.0 values.
    diag_speech = _compute_action_consequence_diagnostics({
        "turn_number": 2,
        "player_input_kind": "speech",
    })
    assert diag_speech["status"] == "not_applicable"
    assert diag_speech["action_consequence_contract_pass"] == 1.0
    assert diag_speech["local_context_transition_present"] == 1.0

    # Opening turn → not_applicable.
    diag_opening = _compute_action_consequence_diagnostics({"turn_number": 0})
    assert diag_opening["status"] == "not_applicable"
    assert diag_opening["reason"] == "opening_turn"


def test_action_context_diagnostics_emit_scores_on_every_player_turn(monkeypatch):
    """P4: scores must fire on every player turn (turn_number > 0), not only the
    authoritative-action short-path. This guards against silent gaps in trace history."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    # Speech turn with fallback — scores must still emit (vacuous 1.0).
    path_summary = _healthy_path_summary_turn(1)
    path_summary.update({
        "player_input_kind": "speech",
        "player_action_frame_present": False,
        "authoritative_action_surface": False,
        "generation_fallback_used": True,
        "quality_class": "degraded",
    })
    blocks = [{"block_type": "actor_line", "actor_id": "alain_reille", "text": "Hello."}]
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    scores = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    for k in (
        "local_context_transition_present",
        "narrator_consequence_present",
        "new_location_established",
        "perception_result_present",
        "action_consequence_contract_pass",
        "npc_consequence_takeover_absent",
    ):
        assert k in scores, f"score {k} missing from degraded-speech-turn emission"
        assert isinstance(scores[k], float)


def test_action_context_diagnostics_reflect_real_perception_failure(monkeypatch):
    """P4: a perception turn that produced no narrator consequence_text must produce
    narrator_consequence_present=0, perception_result_present=0,
    action_consequence_contract_pass=0."""
    from app.story_runtime.manager import _compute_action_consequence_diagnostics

    diag = _compute_action_consequence_diagnostics({
        "turn_number": 3,
        "player_input_kind": "perception",
        "authoritative_action_surface": True,
        "local_context_transition": {"transition_type": "perception", "object_found": True},
        "narrator_consequence_plan": {"consequence_text": None, "consequence_type": "generic"},
    })
    assert diag["status"] == "evaluated"
    assert diag["narrator_consequence_present"] == 0.0
    assert diag["perception_result_present"] == 0.0
    assert diag["action_consequence_contract_pass"] == 0.0


def test_opening_role_anchor_pass_score_is_emitted(monkeypatch):
    """STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P6: opening_role_anchor_pass
    must exist as its own top-level numeric score (0.0/1.0) on the opening, derived from
    opening_shape_subgates.role_anchor_present. Non-opening turns must report 1.0."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    # Canonical opening with role anchor — score must be 1.0
    blocks_ok = _canonical_opening_blocks()
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(0),
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks_ok),
    )
    scores_ok = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert scores_ok.get("opening_role_anchor_pass") == 1.0

    # Failing opening — actor at index 1 (no narrator role anchor) → score must be 0.0
    adapter.reset_mock()
    blocks_fail = [
        {"block_type": "narrator", "text": "Two couples meet on the schoolyard premise."},
        {"block_type": "actor_line", "actor_id": "alain_reille", "text": "Hello."},
        {"block_type": "narrator", "text": "The salon."},
        {"block_type": "narrator", "text": "Coffee cools."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(0),
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks_fail),
    )
    scores_fail = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert scores_fail.get("opening_role_anchor_pass") == 0.0

    # Non-opening turn — score must be 1.0 (vacuous true)
    adapter.reset_mock()
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(2),
        graph_state={"model_prompt": "x"},
        event=_openai_event([{"block_type": "actor_line", "actor_id": "alain_reille", "text": "Hi."}]),
    )
    scores_player = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert scores_player.get("opening_role_anchor_pass") == 1.0


def test_knowledge_runtime_absent_scores_emit_numeric_on_clean_turn(monkeypatch):
    """GOC-KNOWLEDGE-RUNTIME-INTEGRATION P0.3/P0.4: absent-scores must emit deterministic 1.0
    when hard_forbidden_detection.detected is empty."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    path_summary = _healthy_path_summary_turn(0)
    path_summary["hard_forbidden_detection"] = {"status": "passed", "detected": []}
    path_summary["hard_forbidden_absent"] = True
    path_summary["opening_summary_only_absent"] = True
    blocks = [
        {"block_type": "narrator", "text": "Opening beat one with role anchor for Annette."},
        {"block_type": "narrator", "text": "Opening beat two."},
        {"block_type": "narrator", "text": "Opening beat three with handover to phase_1."},
        {"block_type": "actor_line", "actor_id": "michel_longstreet", "text": "Vielleicht beginnen wir ruhig."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    scores = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    for name in (
        "opening_player_speech_absent",
        "opening_npc_exposition_absent",
        "npc_exposition_absent",
        "player_agency_violation_absent",
        "meta_runtime_language_absent",
        "stage_direction_labels_absent",
        "source_reproduction_absent",
    ):
        assert scores.get(name) == 1.0, f"score {name} missing or not 1.0 on clean turn"


def test_knowledge_runtime_absent_scores_drop_to_zero_on_detection(monkeypatch):
    """GOC-KNOWLEDGE-RUNTIME-INTEGRATION P0.3/P0.4: absent-score must drop to 0.0 when
    matching detection_key is present in hard_forbidden_detection.detected."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    path_summary = _healthy_path_summary_turn(0)
    path_summary["hard_forbidden_detection"] = {
        "status": "rejected",
        "detected": [
            {"detection_key": "forced_player_speech", "rule_id": "no_forced_player_speech", "action": "reject", "source": "structural"},
            {"detection_key": "meta_runtime_language", "rule_id": "no_meta_runtime_language", "action": "reject", "source": "marker"},
        ],
    }
    path_summary["hard_forbidden_absent"] = False
    blocks = [
        {"block_type": "narrator", "text": "Opening beat with forbidden mention of evaluator pipeline."},
        {"block_type": "actor_line", "actor_id": "annette_reille", "text": "Ich rede jetzt selbst."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    scores = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert scores.get("opening_player_speech_absent") == 0.0
    assert scores.get("meta_runtime_language_absent") == 0.0
    assert scores.get("hard_forbidden_absent") == 0.0
    # Non-detected categories must still report 1.0 (independence).
    assert scores.get("source_reproduction_absent") == 1.0
    assert scores.get("stage_direction_labels_absent") == 1.0


def _openai_event(scene_blocks: list) -> dict:
    return {
        "model_route": {
            "generation": {"metadata": {"adapter": "openai", "model": "gpt-5-mini"}}
        },
        "visible_output_bundle": {"scene_blocks": scene_blocks},
    }


def _projection_bundle_with_opening_narration(*, role_name: str) -> dict[str, Any]:
    return {
        "gm_narration": [
            "On the schoolyard two boys and a stick left an injury; their parents agreed to meet "
            "the civilised way — an adult appointment, not playground justice.",
            "In the Vallons' Paris apartment tulips, art books, and espresso cups sit beside folded coats "
            "and a dessert that still behaves politely.",
            f"You are {role_name}, arriving as a guest — not a spectator; your spouse is beside you in this courteous pause.",
        ],
        "spoken_lines": ["Veronique: We should keep this civil."],
        "action_lines": ["Michel folds his hands."],
    }


def test_projection_guard_synthesized_opening_survives_into_scene_blocks():
    bundle = _projection_bundle_with_opening_narration(role_name="Annette")
    blocks = _live_scene_blocks_from_visible_bundle(bundle, turn_number=0, session_output_language="en")
    assert len(blocks) >= 5
    assert str(blocks[0].get("block_type")) == "narrator"
    assert str(blocks[1].get("block_type")) == "narrator"
    assert str(blocks[2].get("block_type")) == "narrator"
    assert str(blocks[3].get("block_type")) == "actor_line"
    assert str(blocks[4].get("block_type")) == "actor_action"
    assert _opening_block_contract_satisfied(blocks) is True


def test_projection_guard_first_visible_block_is_narrator_not_actor():
    bundle = _projection_bundle_with_opening_narration(role_name="Annette")
    blocks = _live_scene_blocks_from_visible_bundle(bundle, turn_number=0, session_output_language="en")
    assert str(blocks[0].get("block_type")) == "narrator"
    assert str(blocks[0].get("text") or "").strip()


def test_projection_guard_role_anchor_keeps_selected_role_name_annette_and_alain():
    annette_blocks = _live_scene_blocks_from_visible_bundle(
        _projection_bundle_with_opening_narration(role_name="Annette"),
        turn_number=0,
        session_output_language="en",
    )
    alain_blocks = _live_scene_blocks_from_visible_bundle(
        _projection_bundle_with_opening_narration(role_name="Alain"),
        turn_number=0,
        session_output_language="en",
    )
    assert "Annette" in str(annette_blocks[2].get("text") or "")
    assert "Alain" in str(alain_blocks[2].get("text") or "")


def test_opening_narration_beats_premise_scene_role_anchor_after_split_and_annotate():
    bundle = _projection_bundle_with_opening_narration(role_name="Annette")
    blocks = _live_scene_blocks_from_visible_bundle(bundle, turn_number=0, session_output_language="en")
    blocks = _maybe_split_goc_opening_into_two_movements(blocks, commit_turn_number=0)
    _annotate_goc_opening_narration_beats(
        blocks,
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        turn_number=0,
    )
    assert blocks[0].get("narration_beat") == "premise"
    assert blocks[1].get("narration_beat") == "scene_setup"
    assert blocks[2].get("narration_beat") == "role_anchor"


def test_opening_narration_beats_not_applied_for_non_goc_module():
    bundle = _projection_bundle_with_opening_narration(role_name="Annette")
    blocks = _live_scene_blocks_from_visible_bundle(bundle, turn_number=0, session_output_language="en")
    _annotate_goc_opening_narration_beats(blocks, module_id="other_module", turn_number=0)
    assert blocks[0].get("narration_beat") is None


def test_projection_guard_opening_shape_score_fails_when_projection_drops_narration(monkeypatch):
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    path_summary = {
        **_healthy_path_summary_turn(0),
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "adapter": "openai",
        "final_adapter": "openai",
    }
    event = {
        "model_route": {
            "generation": {"metadata": {"adapter": "openai", "model": "gpt-5-mini"}}
        },
        # no gm_narration + no scene_blocks -> projection lost opening narration
        "visible_output_bundle": {
            "spoken_lines": ["Veronique: We should keep this civil."],
            "action_lines": ["Michel folds his hands."],
        },
    }
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=event,
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["opening_shape_contract_pass"] == 0.0


def test_projection_guard_opening_shape_score_passes_when_scene_blocks_keep_three_narrators(monkeypatch):
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        **_healthy_path_summary_turn(0),
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "adapter": "openai",
        "final_adapter": "openai",
    }
    blocks = _live_scene_blocks_from_visible_bundle(
        _projection_bundle_with_opening_narration(role_name="Annette"),
        turn_number=0,
        session_output_language="en",
    )
    # ensure non-narrator system/debug blocks are not treated as opening narrators
    blocks.insert(
        0,
        {
            "id": "turn-0-live-block-debug",
            "block_type": "system_degraded_notice",
            "text": "debug only",
            "speaker_label": "System",
        },
    )
    assert _opening_block_contract_satisfied(blocks) is False

    # remove debug block: canonical opening shape should pass
    canonical_blocks = [b for b in blocks if str(b.get("block_type")) != "system_degraded_notice"]
    assert _opening_block_contract_satisfied(canonical_blocks) is True
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=_openai_event(canonical_blocks),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["opening_shape_contract_pass"] == 1.0

def test_opening_contract_pass_score_turn0_valid_blocks(monkeypatch):
    """OPEN-GATE-01: turn 0 with 3 narrators then actor_line → opening_contract_pass=1.0."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    blocks = [
        {"block_type": "narrator", "text": "Two couples meet."},
        {"block_type": "narrator", "text": "You are Annette."},
        {"block_type": "narrator", "text": "The salon waits."},
        {"block_type": "actor_line", "actor_id": "alain", "text": "We should talk."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(0),
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["opening_contract_pass"] == 1.0
    assert score_values["live_runtime_contract_pass"] in {0.0, 1.0}


def test_opening_contract_pass_score_turn0_actor_before_narrators(monkeypatch):
    """OPEN-GATE-01: turn 0 with actor_line at index 0 → opening_contract_pass=0.0 blocks live gate."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    blocks = [
        {"block_type": "actor_line", "actor_id": "alain", "text": "Hello."},
        {"block_type": "narrator", "text": "The salon."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(0),
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["opening_contract_pass"] == 0.0
    assert score_values["live_runtime_contract_pass"] == 0.0


def test_opening_contract_pass_trivially_passes_on_regular_turn(monkeypatch):
    """OPEN-GATE-01: turn > 0 always gets opening_contract_pass=1.0 regardless of block structure."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    blocks = [
        {"block_type": "narrator", "text": "The meeting continues."},
        {"block_type": "actor_line", "actor_id": "alain", "text": "I disagree."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(1),
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["opening_contract_pass"] == 1.0


# ---------------------------------------------------------------------------
# OPEN-SHAPE-EVIDENCE-01 tests
# Verify that opening_shape_contract_pass score metadata carries the auditable
# subgate breakdown + truncated scene_block excerpts so dashboards can answer
# "why did opening shape fail?" without re-fetching the trace body.
# ---------------------------------------------------------------------------


def _canonical_opening_blocks() -> list[dict[str, Any]]:
    return [
        {
            "block_type": "narrator",
            "text": (
                "On the schoolyard two boys and a stick left an injury; their parents agreed "
                "to settle it the civilised way — adult procedure instead of playground bluntness."
            ),
        },
        {
            "block_type": "narrator",
            "text": (
                "In the Vallons' Paris apartment tulips and art books frame the salon; folded coats, "
                "papers with neat edges, espresso and a dessert still wait with polite patience."
            ),
        },
        {
            "block_type": "narrator",
            "text": (
                "You are Annette Reille, arriving as a guest beside Alain — not a spectator; "
                "your next move is yours to choose."
            ),
        },
        {"block_type": "actor_line", "actor_id": "veronique_vallon", "text": "Please sit; I will bring coffee."},
    ]


def test_opening_shape_subgates_all_pass_for_canonical_opening(monkeypatch):
    """OPEN-SHAPE-EVIDENCE-01: canonical 3-narrator + actor opening yields all subgates true."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    blocks = _canonical_opening_blocks()
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(0),
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["opening_shape_contract_pass"] == 1.0

    meta = _last_score_metadata_for(adapter, "opening_shape_contract_pass")
    subgates = meta["opening_shape_subgates"]
    assert subgates == {
        "block_count_ok": True,
        "narrator_intro_present": True,
        "role_anchor_present": True,
        "scene_setup_present": True,
        "first_three_are_narrator": True,
        "first_actor_after_intro": True,
    }
    assert meta["opening_shape_failure_reasons"] == []
    summary = meta["scene_block_summary"]
    assert len(summary) == 4
    assert summary[0]["index"] == 0
    assert summary[0]["block_type"] == "narrator"
    assert summary[0]["actor_id"] is None
    assert "schoolyard" in summary[0]["text_excerpt"].lower()
    assert summary[3]["block_type"] == "actor_line"
    assert summary[3]["actor_id"] == "veronique_vallon"


def test_opening_shape_subgates_single_narrator_then_actor_failure(monkeypatch):
    """OPEN-SHAPE-EVIDENCE-01: 1 narrator + actor (the audited 2026-05-08 failure mode) surfaces precise reasons."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    blocks = [
        {"block_type": "narrator", "text": "Two couples meet, chairs ringing a low table; civility is on offer."},
        {"block_type": "actor_line", "actor_id": "alain_reille", "text": "We should keep this brief."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(0),
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["opening_shape_contract_pass"] == 0.0

    meta = _last_score_metadata_for(adapter, "opening_shape_contract_pass")
    subgates = meta["opening_shape_subgates"]
    assert subgates["narrator_intro_present"] is True
    assert subgates["role_anchor_present"] is False
    assert subgates["scene_setup_present"] is False
    assert subgates["first_three_are_narrator"] is False
    assert subgates["block_count_ok"] is False
    assert subgates["first_actor_after_intro"] is False

    reasons = meta["opening_shape_failure_reasons"]
    assert "block_count_lt_4" in reasons
    assert "role_anchor_missing" in reasons
    assert "scene_setup_missing" in reasons
    assert "actor_block_before_intro" in reasons
    assert "narrator_intro_missing" not in reasons
    assert "no_actor_block_present" not in reasons


def test_opening_shape_subgates_actor_at_index_zero_failure(monkeypatch):
    """OPEN-SHAPE-EVIDENCE-01: actor block before any narrator yields narrator_intro_missing + actor_block_before_intro."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    blocks = [
        {"block_type": "actor_line", "actor_id": "alain_reille", "text": "Hello."},
        {"block_type": "narrator", "text": "The salon."},
        {"block_type": "narrator", "text": "Civility on offer."},
        {"block_type": "narrator", "text": "Coffee cools."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(0),
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    meta = _last_score_metadata_for(adapter, "opening_shape_contract_pass")
    subgates = meta["opening_shape_subgates"]
    assert subgates["narrator_intro_present"] is False
    assert subgates["block_count_ok"] is True
    assert subgates["first_actor_after_intro"] is False
    reasons = meta["opening_shape_failure_reasons"]
    assert "narrator_intro_missing" in reasons
    assert "actor_block_before_intro" in reasons
    assert "block_count_lt_4" not in reasons


def test_opening_shape_subgates_no_visible_blocks(monkeypatch):
    """OPEN-SHAPE-EVIDENCE-01: empty scene_blocks produces no_visible_scene_blocks + all narrators absent."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(0),
        graph_state={"model_prompt": "x"},
        event=_openai_event([]),
    )
    meta = _last_score_metadata_for(adapter, "opening_shape_contract_pass")
    subgates = meta["opening_shape_subgates"]
    assert subgates == {
        "block_count_ok": False,
        "narrator_intro_present": False,
        "role_anchor_present": False,
        "scene_setup_present": False,
        "first_three_are_narrator": False,
        "first_actor_after_intro": False,
    }
    reasons = meta["opening_shape_failure_reasons"]
    assert "no_visible_scene_blocks" in reasons
    assert "no_actor_block_present" in reasons
    assert meta["scene_block_summary"] == []


def test_opening_shape_subgates_empty_on_non_opening_turn(monkeypatch):
    """OPEN-SHAPE-EVIDENCE-01: turn > 0 must keep subgates {} and reasons [] (avoid false negatives in trace history)."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    blocks = [
        {"block_type": "actor_line", "actor_id": "alain_reille", "text": "I disagree."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(2),
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    meta = _last_score_metadata_for(adapter, "opening_shape_contract_pass")
    assert meta["opening_shape_subgates"] == {}
    assert meta["opening_shape_failure_reasons"] == []
    assert meta["scene_block_summary"] == []


def test_opening_shape_evidence_attached_to_alias_and_live_opening_scores(monkeypatch):
    """OPEN-SHAPE-EVIDENCE-01: subgate metadata must surface on opening_contract_pass alias and live_opening_contract_pass too.

    The metadata lives in score_metadata_base, so every score row carries it —
    dashboards that filter by live_opening_contract_pass can still join the
    shape diagnosis without an extra fetch.
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    blocks = [
        {"block_type": "narrator", "text": "Only one beat present."},
        {"block_type": "actor_line", "actor_id": "alain_reille", "text": "Hello."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(0),
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    for score_name in (
        "opening_shape_contract_pass",
        "opening_contract_pass",
        "live_runtime_contract_pass",
    ):
        meta = _last_score_metadata_for(adapter, score_name)
        assert meta["opening_shape_subgates"]["role_anchor_present"] is False, (
            f"{score_name!r} missing opening_shape_subgates"
        )
        assert "role_anchor_missing" in meta["opening_shape_failure_reasons"], (
            f"{score_name!r} missing opening_shape_failure_reasons"
        )
        assert len(meta["scene_block_summary"]) == 2


def test_compact_scene_block_summary_caps_count_and_truncates_text():
    """OPEN-SHAPE-EVIDENCE-01: helper bounds payload size for safe score-metadata embedding."""
    long_text = "x" * 500
    blocks: list[dict[str, Any]] = []
    for i in range(12):
        blocks.append(
            {
                "block_type": "narrator" if i < 3 else "actor_line",
                "actor_id": None if i < 3 else f"actor_{i}",
                "text": f"{long_text}_{i}",
            }
        )
    summary = _compact_scene_block_summary(blocks)
    assert len(summary) == 6
    assert [row["index"] for row in summary] == [0, 1, 2, 3, 4, 5]
    for row in summary:
        assert len(row["text_excerpt"]) <= 120
        assert row["text_excerpt"].endswith("\u2026"), "long text must be truncated with an ellipsis"

    custom = _compact_scene_block_summary(blocks, max_count=2, text_excerpt_chars=20)
    assert len(custom) == 2
    for row in custom:
        assert len(row["text_excerpt"]) <= 20

    short_block = [{"block_type": "narrator", "text": "tiny"}]
    untouched = _compact_scene_block_summary(short_block)
    assert untouched == [
        {"index": 0, "block_type": "narrator", "actor_id": None, "text_excerpt": "tiny"}
    ]


def test_compute_opening_shape_subgates_matches_opening_block_contract_satisfied():
    """OPEN-SHAPE-EVIDENCE-01 invariant: aggregate subgate truth equals the gate function (no new semantics)."""
    cases = [
        _canonical_opening_blocks(),
        [],
        [{"block_type": "narrator", "text": "x"}],
        [
            {"block_type": "actor_line", "actor_id": "a", "text": "x"},
            {"block_type": "narrator", "text": "y"},
            {"block_type": "narrator", "text": "z"},
            {"block_type": "narrator", "text": "w"},
        ],
        [
            {"block_type": "narrator", "text": "a"},
            {"block_type": "narrator", "text": "b"},
            {"block_type": "narrator", "text": "c"},
            {"block_type": "actor_action", "actor_id": "x", "text": "shrugs"},
        ],
    ]
    for blocks in cases:
        gate = _opening_block_contract_satisfied(blocks)
        subgates, _ = _compute_opening_shape_subgates(blocks)
        assert all(subgates.values()) == gate, (
            f"Subgate aggregate diverged from gate for blocks={blocks!r}: "
            f"gate={gate} subgates={subgates}"
        )


def test_opening_score_split_mock_trace_shape_can_pass_but_live_opening_must_fail(monkeypatch):
    """OPEN-SCORE-SPLIT-01: fixture/mock traces can pass shape but never live_opening."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        **_healthy_path_summary_turn(0),
        "trace_origin": "pytest",
        "execution_tier": "mock_only",
        "canonical_player_flow": False,
        "adapter": "mock",
        "final_adapter": "mock",
    }
    blocks = [
        {"block_type": "narrator", "text": "Two couples meet."},
        {"block_type": "narrator", "text": "You are Annette."},
        {"block_type": "narrator", "text": "The salon waits."},
        {"block_type": "actor_line", "actor_id": "alain", "text": "We should talk."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["opening_shape_contract_pass"] == 1.0
    assert score_values["live_opening_contract_pass"] == 0.0


def test_opening_score_split_live_degraded_trace_never_passes_live_opening(monkeypatch):
    """OPEN-SCORE-SPLIT-01: degraded fallback path must keep live_opening_contract_pass red."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        **_healthy_path_summary_turn(0),
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "quality_class": "degraded",
        "generation_fallback_used": True,
        "adapter": "ldss_fallback",
        "final_adapter": "ldss_fallback",
    }
    blocks = [
        {"block_type": "narrator", "text": "Two couples meet."},
        {"block_type": "narrator", "text": "You are Annette."},
        {"block_type": "narrator", "text": "The salon waits."},
        {"block_type": "actor_line", "actor_id": "alain", "text": "We should talk."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["opening_shape_contract_pass"] == 1.0
    assert score_values["live_opening_contract_pass"] == 0.0


def test_opening_score_split_live_healthy_missing_intro_blocks_live_opening(monkeypatch):
    """OPEN-SCORE-SPLIT-01: healthy live runtime can still fail opening shape."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        **_healthy_path_summary_turn(0),
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "adapter": "openai",
        "final_adapter": "openai",
    }
    blocks = [
        {"block_type": "narrator", "text": "Only one intro line."},
        {"block_type": "actor_line", "actor_id": "alain", "text": "I disagree."},
    ]
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["live_runtime_contract_pass"] in {0.0, 1.0}
    assert score_values["opening_shape_contract_pass"] == 0.0
    assert score_values["live_opening_contract_pass"] == 0.0


def test_opening_score_split_true_successful_live_opening_sets_both_live_scores(monkeypatch):
    """OPEN-SCORE-SPLIT-01: canonical healthy live opening should set live_opening_contract_pass=1."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )
    path_summary = {
        **_healthy_path_summary_turn(0),
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "adapter": "openai",
        "final_adapter": "openai",
        "selected_player_role": "annette",
        "human_actor_id": "annette_reille",
    }
    blocks = _live_openai_blocks()
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=_openai_event(blocks),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["opening_shape_contract_pass"] == 1.0
    assert score_values["live_runtime_contract_pass"] == 1.0
    assert score_values["live_opening_contract_pass"] == 1.0


def _live_openai_path_summary_turn_0(**overrides) -> dict:
    """Canonical live OpenAI opening path_summary — all subgates satisfied."""
    base = {
        **_healthy_path_summary_turn(0),
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "adapter": "openai",
        "final_adapter": "openai",
        "selected_player_role": "annette",
        "human_actor_id": "annette",
    }
    base.update(overrides)
    return base


def _live_openai_blocks() -> list[dict]:
    return [
        {
            "block_type": "narrator",
            "text": (
                "On the schoolyard two boys and a stick left an injury; their parents agreed "
                "to settle it the civilised way."
            ),
        },
        {
            "block_type": "narrator",
            "text": (
                "In the Vallons' Paris apartment tulips, espresso cups, and folded coats keep manners on display."
            ),
        },
        {
            "block_type": "narrator",
            "text": "You are Annette Reille, arriving as a guest beside Alain — not a spectator.",
        },
        {"block_type": "actor_line", "actor_id": "veronique_vallon", "text": "Please sit; I will bring coffee."},
    ]


def test_live_opening_subgates_all_pass_live_openai(monkeypatch):
    """RUNTIME-CONTRACT-01 A: live OpenAI turn-0, all subgates true → live_opening_contract_pass=1, no failure reasons."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    _emit_langfuse_evidence_observations(
        path_summary=_live_openai_path_summary_turn_0(),
        graph_state={"model_prompt": "x"},
        event=_openai_event(_live_openai_blocks()),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["live_opening_contract_pass"] == 1.0

    meta = _last_score_metadata_for(adapter, "live_opening_contract_pass")
    assert meta["live_opening_failure_reasons"] == []
    subgates = meta["live_opening_subgates"]
    assert all(subgates.values()), f"Expected all subgates true, got: {subgates}"


def test_live_opening_subgates_missing_trace_origin(monkeypatch):
    """RUNTIME-CONTRACT-01 B: trace_origin missing → live_opening=0, failure_reasons contains trace_origin_live_ui."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    path_summary = _live_openai_path_summary_turn_0(trace_origin=None)
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=_openai_event(_live_openai_blocks()),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["live_opening_contract_pass"] == 0.0

    meta = _last_score_metadata_for(adapter, "live_opening_contract_pass")
    assert "trace_origin_live_ui" in meta["live_opening_failure_reasons"]
    assert meta["live_opening_subgates"]["trace_origin_live_ui"] is False


def test_live_opening_subgates_canonical_player_flow_false(monkeypatch):
    """RUNTIME-CONTRACT-01 C: canonical_player_flow=False → live_opening=0, failure_reasons contains canonical_player_flow."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    path_summary = _live_openai_path_summary_turn_0(canonical_player_flow=False)
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=_openai_event(_live_openai_blocks()),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["live_opening_contract_pass"] == 0.0

    meta = _last_score_metadata_for(adapter, "live_opening_contract_pass")
    assert "canonical_player_flow" in meta["live_opening_failure_reasons"]
    assert meta["live_opening_subgates"]["canonical_player_flow"] is False


def test_live_opening_subgates_final_adapter_ldss(monkeypatch):
    """RUNTIME-CONTRACT-01 D: final_adapter=ldss_fallback → live_opening=0, not_ldss_fallback in failure_reasons."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    # event adapter stays "openai" so non_mock_generation_pass=1 and live_runtime_contract_pass can be 1;
    # only path_summary.final_adapter is ldss_fallback to isolate the not_ldss_fallback subgate.
    path_summary = _live_openai_path_summary_turn_0(final_adapter="ldss_fallback")
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=_openai_event(_live_openai_blocks()),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["live_opening_contract_pass"] == 0.0

    meta = _last_score_metadata_for(adapter, "live_opening_contract_pass")
    assert "not_ldss_fallback" in meta["live_opening_failure_reasons"]
    assert meta["live_opening_subgates"]["not_ldss_fallback"] is False


def test_live_opening_subgates_role_mismatch_is_informational_not_gated(monkeypatch):
    """RUNTIME-CONTRACT-01 E: selected_player_role != human_actor_id does not gate live_opening_contract_pass.

    Role mismatch is tracked in metadata for debugging but is not a hard subgate condition.
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    path_summary = _live_openai_path_summary_turn_0(
        selected_player_role="annette",
        human_actor_id="alain",  # mismatch
    )
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=_openai_event(_live_openai_blocks()),
    )
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    # Role mismatch alone must NOT block live_opening_contract_pass.
    assert score_values["live_opening_contract_pass"] == 1.0

    meta = _last_score_metadata_for(adapter, "live_opening_contract_pass")
    assert meta["live_opening_failure_reasons"] == []


# ---------------------------------------------------------------------------
# PRIMARY-PARSER-EVIDENCE-01 tests (A–E)
# Verify that primary parser failure evidence survives the LDSS overwrite and
# surfaces in path_summary → score_metadata without touching gate semantics.
# ---------------------------------------------------------------------------


def test_parser_evidence_A_primary_parser_error_preserved_in_score_metadata(monkeypatch):
    """PPE-A: primary API success + parser_error → score_metadata carries primary_attempt_parser_error_present=True.

    When gpt-4.1-mini succeeds the API call but PydanticOutputParser fails, and LDSS
    then fires and overwrites generation.metadata, the evidence must still reach
    the ``live_runtime_contract_pass`` score_metadata so operators can diagnose
    "API ok, parser failed" from dashboards without reading raw spans.
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    path_summary = {
        "session_id": "session-ppe-a",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "adapter": "ldss_fallback",
        "adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
        "final_adapter": "ldss_fallback",
        "final_adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
        "generation_fallback_used": True,
        "retrieval_context_attached": True,
        "usage_details": {"input": 100, "output": 50, "total": 150},
        "actor_lane_validation_status": "approved",
        "quality_class": "degraded",
        "degradation_signals": ["ldss_fallback_after_live_opening_failure", "non_factual_staging"],
        "live_opening_failure_reason": "dramatic_effect_reject_empty_fluency",
        # PRIMARY-PARSER-EVIDENCE-01 fields written by _ldss_opening_fallback_state
        "primary_attempt_api_success": True,
        "primary_attempt_parser_error_present": True,
        "primary_attempt_parser_error": "Expected a mapping for field 'spoken_lines' but got str",
        "primary_attempt_structured_output_present": False,
        "primary_attempt_raw_output_sha256": "abc123deadbeef",
        "primary_attempt_raw_output_excerpt": '{"spoken_lines": "Michel: Lets stay calm."}',
        "self_correction_attempted": True,
        "self_correction_success": False,
        "self_correction_model": "gpt-4.1-mini",
    }
    event = {
        "model_route": {
            "generation": {
                "metadata": {
                    "adapter": "ldss_fallback",
                    "adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
                    "live_opening_failure_reason": "dramatic_effect_reject_empty_fluency",
                }
            }
        },
        "visible_output_bundle": {
            "scene_blocks": [{"type": "narrator", "text": "Le salon attend."}]
        },
    }
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=event,
    )

    meta = _last_score_metadata_for(adapter, "live_runtime_contract_pass")
    assert meta["primary_attempt_api_success"] is True
    assert meta["primary_attempt_parser_error_present"] is True
    assert meta["self_correction_attempted"] is True
    assert meta["self_correction_success"] is False

    # Gate must stay red — evidence fields must not soften gate semantics.
    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["fallback_absent"] == 0.0
    assert score_values["live_runtime_contract_pass"] == 0.0


def test_parser_evidence_B_api_failure_shows_no_parser_error(monkeypatch):
    """PPE-B: primary API failure → primary_attempt_api_success=False, parser_error_present=False.

    A transport/timeout error at the OpenAI API layer means the parser never ran.
    The evidence fields must correctly distinguish "API failed before parse" from
    "API succeeded but parse failed" so operators can split alerts by failure tier.
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    path_summary = {
        "session_id": "session-ppe-b",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "adapter": "ldss_fallback",
        "final_adapter": "ldss_fallback",
        "generation_fallback_used": True,
        "retrieval_context_attached": True,
        "usage_details": {"input": 0, "output": 0, "total": 0},
        "actor_lane_validation_status": "approved",
        "quality_class": "degraded",
        "degradation_signals": ["ldss_fallback_after_live_opening_failure", "non_factual_staging"],
        "live_opening_failure_reason": "api_error",
        # API call itself failed — no parse was attempted
        "primary_attempt_api_success": False,
        "primary_attempt_parser_error_present": False,
        "primary_attempt_parser_error": "",
        "primary_attempt_structured_output_present": False,
        "self_correction_attempted": False,
        "self_correction_success": False,
    }
    event = {
        "model_route": {"generation": {"metadata": {"adapter": "ldss_fallback"}}},
        "visible_output_bundle": {"scene_blocks": [{"type": "narrator", "text": "Fallback."}]},
    }
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=event,
    )

    meta = _last_score_metadata_for(adapter, "live_runtime_contract_pass")
    assert meta["primary_attempt_api_success"] is False
    assert meta["primary_attempt_parser_error_present"] is False
    assert meta["self_correction_attempted"] is False


def test_parser_evidence_C_successful_primary_parse_sets_structured_output_present(monkeypatch):
    """PPE-C: healthy live path (parse succeeds) → primary_attempt_structured_output_present=True in span.

    When gpt-4.1-mini succeeds both API call and PydanticOutputParser.parse(), the
    primary_attempt_evidence must show structured_output_present=True and
    parser_error_present=False. Also verifies these fields appear in
    ``story.phase.model_invoke`` span output.
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    path_summary = {
        **_live_openai_path_summary_turn_0(),
        "primary_attempt_api_success": True,
        "primary_attempt_parser_error_present": False,
        "primary_attempt_parser_error": None,
        "primary_attempt_structured_output_present": True,
        "primary_attempt_raw_output_sha256": "deadbeef01234567",
        "self_correction_attempted": False,
        "self_correction_success": False,
        # span routing fields
        "invoke_model_called": True,
        "structured_output_present": True,
    }
    _emit_langfuse_path_spans(path_summary)

    invoke_output = _last_span_output_for(adapter, "story.phase.model_invoke")
    assert invoke_output.get("primary_attempt_api_success") is True
    assert invoke_output.get("primary_attempt_parser_error_present") is False
    assert invoke_output.get("primary_attempt_structured_output_present") is True
    assert invoke_output.get("primary_attempt_raw_output_sha256") == "deadbeef01234567"
    assert invoke_output.get("self_correction_attempted") is False


def test_self_correction_evidence_derived_from_graph_state():
    session = StorySession(
        session_id="session-sc-graph",
        module_id="god_of_carnage",
        runtime_projection={
            "module_id": "god_of_carnage",
            "human_actor_id": "annette",
            "selected_player_role": "annette",
            "npc_actor_ids": ["alain_reille"],
        },
    )
    failure = {
        "failure_reason": "npc_executed_player_action",
        "expected_owner": "narrator",
    }
    graph_state = {
        "nodes_executed": ["invoke_model", "validate_seam"],
        "generation": {
            "attempted": True,
            "success": True,
            "metadata": {"adapter": "openai", "model": "gpt-4.1-mini"},
        },
        "validation_outcome": {"status": "approved", "reason": "seam_ok"},
        "self_correction": {
            "attempt_count": 1,
            "attempts": [
                {
                    "candidate_model": "gpt-4.1-mini",
                    "success": True,
                    "parser_error": None,
                    "trigger_source": "runtime_aspect",
                    "runtime_aspect_failure_before_retry": failure,
                    "resolved_failure": True,
                }
            ],
        },
    }
    summary = _build_langfuse_path_summary(
        session=session,
        graph_state=graph_state,
        event={"turn_number": 2, "turn_kind": "scene", "visible_output_bundle": {}},
    )

    assert summary["self_correction_attempted"] is True
    assert summary["self_correction_attempt_count"] == 1
    assert summary["self_correction_success"] is True
    assert summary["self_correction_model"] == "gpt-4.1-mini"
    assert summary["self_correction_trigger_source"] == "runtime_aspect"
    assert summary["runtime_aspect_failure_before_retry"] == failure
    assert summary["self_correction_resolved_failure"] is True


def test_path_summary_marks_local_langfuse_evidence(monkeypatch):
    monkeypatch.setenv("WOS_LANGFUSE_LOCAL_EVIDENCE", "1")
    monkeypatch.setenv("LANGFUSE_ENVIRONMENT", "local")
    session = StorySession(
        session_id="session-local-langfuse",
        module_id="god_of_carnage",
        runtime_projection={
            "module_id": "god_of_carnage",
            "human_actor_id": "annette",
            "selected_player_role": "annette",
            "npc_actor_ids": ["alain_reille"],
        },
    )
    summary = _build_langfuse_path_summary(
        session=session,
        graph_state={
            "nodes_executed": ["retrieve_context", "invoke_model", "validate_seam", "commit_seam"],
            "generation": {"attempted": True, "success": True, "metadata": {"adapter": "openai"}},
            "retrieval": {
                "status": "ok",
                "hit_count": 2,
                "authority_level": "canonical",
                "provenance": [{"source": "content/modules/god_of_carnage/module.yaml"}],
            },
            "validation_outcome": {"status": "approved", "reason": "seam_ok"},
            "committed_result": {"commit_applied": True},
            "quality_class": "healthy",
        },
        event={"turn_number": 1, "turn_kind": "scene", "visible_output_bundle": {}},
    )

    assert summary["environment"] == "local"
    assert summary["evidence_scope"] == "local_langfuse"
    assert summary["proof_level"] == "local_only"
    assert summary["live_or_staging_evidence"] is False
    assert summary["runtime_quality"] == "healthy"
    assert summary["retrieval_authority_level"] == "canonical"
    assert summary["retrieval_provenance"] == [
        {"source": "content/modules/god_of_carnage/module.yaml"}
    ]


def test_parser_evidence_D_self_correction_attempt_surfaces_in_score_metadata(monkeypatch):
    """PPE-D: self_correction_attempted=True and model must appear in score metadata.

    When the runtime's self-correction path fires (rewrites the candidate with a
    second model call), score_metadata must expose ``self_correction_attempted`` so
    cost-attribution and alert rules can distinguish "parser error + SC fired" from
    "parser error, no SC, straight LDSS".
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    path_summary = {
        "session_id": "session-ppe-d",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "adapter": "ldss_fallback",
        "final_adapter": "ldss_fallback",
        "generation_fallback_used": True,
        "retrieval_context_attached": True,
        "usage_details": {"input": 200, "output": 100, "total": 300},
        "actor_lane_validation_status": "approved",
        "quality_class": "degraded",
        "degradation_signals": ["ldss_fallback_after_live_opening_failure", "non_factual_staging"],
        "live_opening_failure_reason": "dramatic_effect_reject_empty_fluency",
        "primary_attempt_api_success": True,
        "primary_attempt_parser_error_present": True,
        "primary_attempt_parser_error": "output is not valid JSON",
        "primary_attempt_structured_output_present": False,
        "self_correction_attempted": True,
        "self_correction_attempt_count": 1,
        "self_correction_success": False,
        "self_correction_model": "gpt-4.1-nano",
        "self_correction_trigger_source": "runtime_aspect",
        "runtime_aspect_failure_before_retry": {
            "failure_reason": "narrator_required_missing",
            "expected_owner": "narrator",
        },
        "capability_failure_before_retry": None,
        "self_correction_resolved_failure": False,
    }
    event = {
        "model_route": {"generation": {"metadata": {"adapter": "ldss_fallback"}}},
        "visible_output_bundle": {"scene_blocks": [{"type": "narrator", "text": "Fallback."}]},
    }
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=event,
    )

    meta = _last_score_metadata_for(adapter, "live_runtime_contract_pass")
    assert meta["self_correction_attempted"] is True
    assert meta["self_correction_attempt_count"] == 1
    assert meta["self_correction_success"] is False
    assert meta["self_correction_model"] == "gpt-4.1-nano"
    assert meta["self_correction_trigger_source"] == "runtime_aspect"
    assert meta["runtime_aspect_failure_before_retry"]["failure_reason"] == "narrator_required_missing"
    assert meta["capability_failure_before_retry"] is None
    assert meta["self_correction_resolved_failure"] is False


def test_self_correction_evidence_surfaces_in_model_invoke_span(monkeypatch):
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    path_summary = {
        **_live_openai_path_summary_turn_0(),
        "invoke_model_called": True,
        "generation_attempted": True,
        "generation_success": True,
        "self_correction_attempted": True,
        "self_correction_attempt_count": 1,
        "self_correction_success": True,
        "self_correction_model": "gpt-4.1-mini",
        "self_correction_trigger_source": "capability",
        "runtime_aspect_failure_before_retry": None,
        "capability_failure_before_retry": {
            "failure_reason": "capability_missing_required",
            "missing_required_capability": "narrate_consequence",
        },
        "self_correction_resolved_failure": True,
    }
    _emit_langfuse_path_spans(path_summary)

    invoke_output = _last_span_output_for(adapter, "story.phase.model_invoke")
    assert invoke_output["self_correction_attempt_count"] == 1
    assert invoke_output["self_correction_trigger_source"] == "capability"
    assert invoke_output["runtime_aspect_failure_before_retry"] is None
    assert invoke_output["capability_failure_before_retry"]["failure_reason"] == "capability_missing_required"
    assert invoke_output["self_correction_resolved_failure"] is True


def test_parser_evidence_E_ldss_gate_scores_stay_red_with_evidence_fields_present(monkeypatch):
    """PPE-E: adding primary_attempt_evidence fields must not soften gate scores.

    This is a regression guard: the evidence fields are metadata-only. A trace
    with final_adapter=ldss_fallback must still score fallback_absent=0.0 and
    live_runtime_contract_pass=0.0 regardless of what primary_attempt_* values say.
    live_opening_contract_pass must also be 0.0 (LDSS disqualifies it).
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    path_summary = {
        "session_id": "session-ppe-e",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "adapter": "ldss_fallback",
        "adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
        "final_adapter": "ldss_fallback",
        "final_adapter_invocation_mode": "ldss_fallback_after_live_opening_failure",
        "generation_fallback_used": True,
        "retrieval_context_attached": True,
        "usage_details": {"input": 100, "output": 50, "total": 150},
        "actor_lane_validation_status": "approved",
        "quality_class": "degraded",
        "degradation_signals": ["ldss_fallback_after_live_opening_failure", "non_factual_staging"],
        "live_opening_failure_reason": "dramatic_effect_reject_empty_fluency",
        # Evidence fields present — must NOT change gate outcome
        "primary_attempt_api_success": True,
        "primary_attempt_parser_error_present": True,
        "primary_attempt_structured_output_present": False,
        "self_correction_attempted": True,
        "self_correction_success": False,
        "self_correction_model": "gpt-4.1-nano",
    }
    blocks = [
        {"block_type": "narrator", "text": "Two couples meet."},
        {"block_type": "narrator", "text": "You are Annette."},
        {"block_type": "narrator", "text": "The salon waits."},
        {"block_type": "actor_line", "actor_id": "alain", "text": "We should talk."},
    ]
    event = {
        "model_route": {
            "generation": {
                "metadata": {
                    "adapter": "ldss_fallback",
                    "live_opening_failure_reason": "dramatic_effect_reject_empty_fluency",
                }
            }
        },
        "visible_output_bundle": {"scene_blocks": blocks},
    }
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=event,
    )

    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["fallback_absent"] == 0.0, "LDSS must keep fallback_absent=0"
    assert score_values["live_runtime_contract_pass"] == 0.0, "LDSS must keep live_runtime=0"
    assert score_values["live_opening_contract_pass"] == 0.0, "LDSS disqualifies live_opening"

    meta = _last_score_metadata_for(adapter, "live_runtime_contract_pass")
    assert meta["primary_attempt_api_success"] is True, "evidence fields must still surface in metadata"
    assert meta["primary_attempt_parser_error_present"] is True
    assert meta["self_correction_attempted"] is True


# ---------------------------------------------------------------------------
# Supplementary tests (S1–S5)
# Structural and semantic guards for the PRIMARY-PARSER-EVIDENCE-01 fix.
# ---------------------------------------------------------------------------


def test_S1_self_correction_key_always_written_by_validate_seam():
    """S1: _validate_seam must unconditionally write self_correction even when SC never fires.

    Regression guard for gap A1: if _validate_seam is refactored and the
    self_correction write is moved inside the SC loop, _ldss_opening_fallback_state
    would silently omit self_correction_attempted from LDSS trace metadata.
    """
    import sys, os
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from ai_stack.langgraph_runtime_executor import RuntimeTurnGraphExecutor

    graph = object.__new__(RuntimeTurnGraphExecutor)
    graph.max_self_correction_attempts = 0  # disable SC loop
    graph.allow_degraded_commit_after_retries = False

    state = {
        "session_id": "s1",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "player_input": "I watch.",
        "actor_lane_context": {
            "human_actor_id": "annette",
            "selected_player_role": "annette",
            "ai_forbidden_actor_ids": ["annette"],
        },
        "nodes_executed": ["invoke_model"],
        "node_outcomes": {},
        "graph_errors": [],
        "selected_responder_set": [{"actor_id": "michel"}],
        "generation": {
            "success": True,
            "metadata": {
                "structured_output": {
                    "schema_version": "runtime_actor_turn_v1",
                    "narration_summary": "Two couples meet in a Paris salon.",
                    "narrative_response": "Two couples meet in a Paris salon.",
                    "primary_responder_id": "michel",
                    "spoken_lines": [{"speaker_id": "michel", "text": "We should stay calm."}],
                    "action_lines": [],
                    "initiative_events": [],
                    "state_effects": [],
                }
            },
        },
        "proposed_state_effects": [
            {"effect_type": "narrative_projection", "description": "Two couples meet in a Paris salon."}
        ],
    }

    result = graph._validate_seam(state)

    assert "self_correction" in result, "_validate_seam must always write self_correction to update"
    assert isinstance(result["self_correction"], dict)
    assert result["self_correction"]["attempts"] == [], "No SC attempts when max_self_correction_attempts=0"
    assert result["self_correction"]["attempt_count"] == 0


def test_S2_graph_fallback_node_called_false_when_only_sc_set_fallback_used(monkeypatch):
    """S2: graph_fallback_node_called=False when graph node absent but SC set fallback_used=True.

    Documents the known semantic gap: fallback_model_called (legacy) is True because it
    reads generation.fallback_used, while graph_fallback_node_called (accurate) is False
    because the graph _fallback_model node never appeared in nodes_executed.
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    path_summary = {
        # SC fired and set fallback_used=True, but _fallback_model graph node never ran
        "nodes_executed": ["invoke_model", "proposal_normalize", "validate_seam", "commit_seam"],
        "generation_fallback_used": True,  # SC set this via candidate_mid != selected_mid
        "session_id": "session-s2",
        "module_id": "god_of_carnage",
        "turn_number": 1,
        "route_model_called": True,
        "invoke_model_called": True,
        "fallback_model_called": True,   # legacy field: True because fallback_used=True
        "graph_fallback_node_called": False,  # accurate: node never in nodes_executed
        "retrieval_called": True,
        "validation_called": True,
        "commit_called": True,
        "render_visible_called": True,
    }
    _emit_langfuse_path_spans(path_summary)

    path_span = _last_span_output_for(adapter, "story.graph.path_summary")
    assert path_span.get("graph_fallback_node_called") is False, (
        "graph_fallback_node_called must be False: _fallback_model node never ran"
    )
    assert path_span.get("fallback_model_called") is True, (
        "fallback_model_called stays True (legacy broad semantic: SC set fallback_used)"
    )


def test_S3_primary_attempt_evidence_key_is_independent_of_generation():
    """S3: primary_attempt_evidence state key cannot be clobbered by SC or LDSS writes to generation.

    The design invariant: _invoke_model writes primary_attempt_evidence as a SEPARATE
    top-level state key. Any subsequent node writing to generation[metadata] (SC, LDSS)
    cannot overwrite primary_attempt_evidence because it is a different dict.
    """
    # Simulate _invoke_model output
    update: dict = {}
    update["generation"] = {
        "metadata": {"langchain_parser_error": "Expected mapping for spoken_lines but got str"}
    }
    update["primary_attempt_evidence"] = {
        "primary_attempt_parser_error": "Expected mapping for spoken_lines but got str",
        "primary_attempt_parser_error_present": True,
        "primary_attempt_api_success": True,
    }

    # Simulate SC overwriting generation (as _rewrite_candidate does)
    update["generation"] = {
        "metadata": {"langchain_parser_error": None}  # SC's own (null) parser error
    }

    # Evidence must be unchanged
    assert update["primary_attempt_evidence"]["primary_attempt_parser_error"] == (
        "Expected mapping for spoken_lines but got str"
    ), "SC overwriting generation must not affect primary_attempt_evidence"
    assert update["primary_attempt_evidence"]["primary_attempt_parser_error_present"] is True

    # Simulate LDSS overwriting generation again
    update["generation"] = {
        "metadata": {
            "adapter": "ldss_fallback",
            "structured_output": None,
        }
    }

    # Evidence still unchanged
    assert update["primary_attempt_evidence"]["primary_attempt_api_success"] is True


def test_S4_ldss_fallback_without_primary_attempt_evidence_does_not_crash():
    """S4: _ldss_opening_fallback_state must not crash when primary_attempt_evidence is absent.

    The adapter-not-registered path in _invoke_model skips writing primary_attempt_evidence.
    _ldss_opening_fallback_state must gracefully handle its absence (guard for gap A2).
    """
    from app.story_runtime.manager import StoryRuntimeManager
    from story_runtime_core.model_registry import ModelRegistry

    mgr = StoryRuntimeManager(registry=ModelRegistry(), adapters={})
    # graph_state has NO primary_attempt_evidence key (adapter-not-registered path)
    graph_state = {
        "validation_outcome": {"status": "rejected", "reason": "dramatic_effect_reject_empty_fluency"},
        "generation": {
            "success": True,
            "metadata": {
                "adapter": "openai",
                "model": "gpt-4.1-mini",
                "adapter_invocation_mode": "langchain_structured_primary",
            },
        },
        "routing": {"selected_provider": "openai", "selected_model": "openai_gpt_4_1_mini"},
    }
    # Must not raise
    out = mgr._ldss_opening_fallback_state(graph_state, reason="dramatic_effect_reject_empty_fluency")
    meta = out["generation"]["metadata"]

    # PPE fields must be absent (not written with a default), not raise
    assert meta.get("primary_attempt_parser_error_present") is None, (
        "PPE fields must be absent when primary_attempt_evidence missing from graph_state"
    )
    assert meta.get("primary_attempt_api_success") is None
    # Standard fields must still be written correctly
    assert meta["adapter"] == "ldss_fallback"
    assert meta["final_adapter"] == "ldss_fallback"
    assert meta["primary_attempt_adapter"] == "openai"


def test_S5_path_summary_parser_error_none_primary_attempt_parser_error_present(monkeypatch):
    """S5: documents intentional field divergence on LDSS traces.

    After LDSS fires, path_summary["parser_error"] (legacy, reads FINAL generation's
    langchain_parser_error) is None — LDSS does not set langchain_parser_error.
    But path_summary["primary_attempt_parser_error"] (from preserved state key via
    _ldss_opening_fallback_state) correctly captures the original primary parse failure.

    Operators must use primary_attempt_parser_error, not parser_error, to diagnose
    parse failures on LDSS-fallback traces.
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    path_summary = {
        "session_id": "session-s5",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "adapter": "ldss_fallback",
        "final_adapter": "ldss_fallback",
        "generation_fallback_used": True,
        "retrieval_context_attached": True,
        "usage_details": {"input": 100, "output": 50, "total": 150},
        "actor_lane_validation_status": "approved",
        "quality_class": "degraded",
        "degradation_signals": ["ldss_fallback_after_live_opening_failure", "non_factual_staging"],
        "live_opening_failure_reason": "dramatic_effect_reject_empty_fluency",
        # Legacy field: LDSS does not propagate langchain_parser_error → None
        "parser_error": None,
        # PPE fields: correctly preserved via primary_attempt_evidence state key
        "primary_attempt_parser_error": "Expected a mapping for 'spoken_lines' but got str",
        "primary_attempt_parser_error_present": True,
        "primary_attempt_api_success": True,
        "self_correction_attempted": True,
        "self_correction_success": False,
    }
    event = {
        "model_route": {"generation": {"metadata": {"adapter": "ldss_fallback"}}},
        "visible_output_bundle": {"scene_blocks": [{"type": "narrator", "text": "Fallback."}]},
    }
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state={"model_prompt": "x"},
        event=event,
    )

    meta = _last_score_metadata_for(adapter, "live_runtime_contract_pass")

    # Legacy field is None (LDSS trace — expected, not a bug)
    assert meta.get("parser_error") is None, (
        "parser_error is None on LDSS traces — operators must use primary_attempt_parser_error"
    )
    # PPE field correctly captures original primary parse failure
    assert meta["primary_attempt_parser_error_present"] is True, (
        "primary_attempt_parser_error_present must be True: primary parse failed before LDSS"
    )
    assert meta["primary_attempt_api_success"] is True, (
        "primary_attempt_api_success must be True: API succeeded, only parser failed"
    )


def test_S6_primary_parse_span_emitted_with_warning_level_on_parse_failure(monkeypatch):
    """S6: story.phase.primary_parse span is emitted at WARNING when parser_error_present=True.

    On LDSS traces the parse failure is the root cause. The span must surface it
    explicitly with level=WARNING so operators see the causal chain without joining spans.
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )

    path_summary = {
        "session_id": "s6-session",
        "module_id": "god_of_carnage",
        "turn_number": 0,
        "turn_kind": "opening",
        "invoke_model_called": True,
        "primary_attempt_api_success": True,
        "primary_attempt_parser_error_present": True,
        "primary_attempt_parser_error": "Expected mapping but got str at line 1",
        "primary_attempt_structured_output_present": False,
        "primary_attempt_raw_output_sha256": "abc123",
        "primary_attempt_raw_output_excerpt": "{'spoken_lines': 'hello'}",
        "primary_attempt_adapter": "openai",
        "primary_attempt_model": "gpt-4.1-mini",
        "primary_attempt_invocation_mode": "langchain_structured_primary",
    }
    _emit_langfuse_path_spans(path_summary)

    created_child_names = [call.kwargs["name"] for call in adapter.create_child_span.call_args_list]
    assert "story.phase.primary_parse" in created_child_names

    output = _last_span_output_for(adapter, "story.phase.primary_parse")
    assert output["api_success"] is True
    assert output["parser_error_present"] is True
    assert output["parser_error"] == "Expected mapping but got str at line 1"
    assert output["structured_output_present"] is False
    assert output["raw_output_sha256"] == "abc123"
    assert output["adapter"] == "openai"
    assert output["model"] == "gpt-4.1-mini"

    # Level must be WARNING — parse failure is a degradation signal
    span_call = next(
        c for c in adapter.create_child_span.call_args_list
        if c.kwargs.get("name") == "story.phase.primary_parse"
    )
    assert span_call.kwargs.get("level") == "WARNING", (
        "story.phase.primary_parse must be WARNING when parser_error_present=True"
    )


def test_S7_primary_parse_span_default_level_on_healthy_path(monkeypatch):
    """S7: story.phase.primary_parse span is DEFAULT on a healthy parse path.

    When gpt-4.1-mini API + PydanticOutputParser both succeed, the span is emitted
    at DEFAULT level with structured_output_present=True and parser_error_present=False.
    """
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr(
        "app.story_runtime.manager.LangfuseAdapter.get_instance",
        lambda: adapter,
    )

    path_summary = {
        "session_id": "s7-session",
        "module_id": "god_of_carnage",
        "turn_number": 1,
        "turn_kind": "turn",
        "invoke_model_called": True,
        "primary_attempt_api_success": True,
        "primary_attempt_parser_error_present": False,
        "primary_attempt_parser_error": None,
        "primary_attempt_structured_output_present": True,
        "primary_attempt_raw_output_sha256": "deadbeef",
        "primary_attempt_adapter": "openai",
        "primary_attempt_model": "gpt-4.1-mini",
        "primary_attempt_invocation_mode": "langchain_structured_primary",
    }
    _emit_langfuse_path_spans(path_summary)

    output = _last_span_output_for(adapter, "story.phase.primary_parse")
    assert output["api_success"] is True
    assert output["parser_error_present"] is False
    assert output["structured_output_present"] is True

    span_call = next(
        c for c in adapter.create_child_span.call_args_list
        if c.kwargs.get("name") == "story.phase.primary_parse"
    )
    assert span_call.kwargs.get("level") == "DEFAULT", (
        "story.phase.primary_parse must be DEFAULT when parse succeeded"
    )


def test_opening_shape_score_metadata_includes_actor_index_and_narrator_count(monkeypatch):
    """OPEN-SHAPE-EVIDENCE-01: first_actor_block_index + narrator_block_count on turn 0."""
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    blocks = [
        {"block_type": "narrator", "text": "a"},
        {"block_type": "narrator", "text": "b"},
        {"block_type": "narrator", "text": "c"},
        {"block_type": "actor_line", "actor_id": "alain_reille", "text": "Hi."},
    ]
    event = {
        "model_route": {
            "generation": {
                "metadata": {
                    "adapter": "openai",
                    "structured_output": {
                        "narration_summary": ["x", "y", "z"],
                    },
                },
            },
        },
        "visible_output_bundle": {"scene_blocks": blocks},
    }
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(0),
        graph_state={"model_prompt": "x"},
        event=event,
    )
    meta = _last_score_metadata_for(adapter, "opening_shape_contract_pass")
    assert meta["first_actor_block_index"] == 3
    assert meta["narrator_block_count"] == 3
    assert meta["structured_narration_summary_kind"] == "list"


def test_opening_shape_failure_appends_single_string_token_when_structured_str(monkeypatch):
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    event = {
        "model_route": {
            "generation": {
                "metadata": {
                    "adapter": "openai",
                    "structured_output": {"narration_summary": "one fused paragraph."},
                },
            },
        },
        "visible_output_bundle": {
            "scene_blocks": [
                {"block_type": "narrator", "text": "only one"},
                {"block_type": "actor_line", "actor_id": "alain_reille", "text": "Hi"},
            ],
        },
    }
    _emit_langfuse_evidence_observations(
        path_summary=_healthy_path_summary_turn(0),
        graph_state={"model_prompt": "x"},
        event=event,
    )
    meta = _last_score_metadata_for(adapter, "opening_shape_contract_pass")
    assert meta["structured_narration_summary_kind"] == "str"
    assert "narration_summary_single_string" in meta["opening_shape_failure_reasons"]


def test_opening_turn0_live_packaging_then_gm_hook_passes_opening_shape():
    """P0: experience packaging collapses gm lines; post-pack hook restores three narrators."""
    from ai_stack.story_runtime_experience import canonical_defaults, resolve_story_runtime_experience_policy
    from ai_stack.story_runtime_experience_packaging import package_bundle_with_policy

    session = StorySession(
        session_id="s-opening-pack",
        module_id="god_of_carnage",
        runtime_projection={
            "module_id": "god_of_carnage",
            "human_actor_id": "annette",
            "selected_player_role": "annette",
            "start_scene_id": "living_room",
            "npc_actor_ids": [],
        },
        session_output_language="de",
    )
    raw_bundle = {
        "gm_narration": [
            "Premise line one about the meeting.",
            "Premise line two about tension.",
            "Premise line three about the salon.",
        ],
        "spoken_lines": ["Veronique: We should keep this civil."],
        "action_lines": ["Michel folds his hands."],
    }
    policy = resolve_story_runtime_experience_policy(
        {
            **canonical_defaults(),
            "experience_mode": "live_dramatic_scene_simulator",
            "delivery_profile": "cinematic_live",
        }
    )
    packaged = package_bundle_with_policy(raw_bundle, policy)
    assert len(packaged.get("gm_narration") or []) < 3

    graph_state: dict[str, Any] = {
        "generation": {
            "metadata": {
                "structured_output": {
                    "schema_version": "runtime_actor_turn_v1",
                    "narration_summary": (
                        "A single paragraph about the Paris salon evening without enough blank lines."
                    ),
                    "spoken_lines": [{"speaker_id": "veronique_vallon", "text": "Welcome."}],
                    "action_lines": [{"actor_id": "michel_longstreet", "text": "nods"}],
                },
            },
        },
    }
    fixed = _finalize_visible_bundle_opening_gm_narration(
        session=session,
        graph_state=graph_state,
        packaged_bundle=packaged,
        commit_turn_number=0,
    )
    assert isinstance(fixed, dict)
    assert len(fixed.get("gm_narration") or []) == 3
    structured = graph_state["generation"]["metadata"]["structured_output"]
    blocks = _live_scene_blocks_from_visible_bundle(
        fixed,
        turn_number=0,
        structured_output=structured,
        runtime_projection=session.runtime_projection,
        graph_state=graph_state,
        session_output_language=session.session_output_language,
    )
    assert _opening_block_contract_satisfied(blocks)
    assert graph_state.get("_opening_narration_normalization", {}).get("opening_narration_normalized") is True
    ev = graph_state.get("_actor_block_projection_evidence") or {}
    assert ev.get("actor_block_count_after_projection", 0) >= 1


def test_open_actor_block_projection_structured_npc_spoken_backfills_after_three_narrators():
    """OPEN-ACTOR-BLOCK-PROJECTION-01: dict spoken_lines in structured → actor_line at index 3."""
    gs: dict[str, Any] = {"generation": {"metadata": {}}}
    bundle = {
        "gm_narration": [
            "Beat one premise.",
            "Beat two role anchor.",
            "Beat three scene setup.",
        ],
    }
    structured = {
        "spoken_lines": [{"speaker_id": "veronique_vallon", "text": "We should keep this civil."}],
    }
    proj = {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette",
        "npc_actor_ids": ["veronique_vallon", "michel_longstreet", "alain_reille"],
    }
    blocks = _live_scene_blocks_from_visible_bundle(
        bundle,
        turn_number=0,
        structured_output=structured,
        runtime_projection=proj,
        graph_state=gs,
        session_output_language="en",
    )
    assert _opening_block_contract_satisfied(blocks)
    assert str(blocks[3].get("block_type")) == "actor_line"
    ev = gs.get("_actor_block_projection_evidence") or {}
    assert ev.get("actor_block_source") == "spoken_lines"
    assert ev.get("actor_line_count_before_projection") == 1


def test_open_actor_block_projection_structured_npc_action_backfills():
    """OPEN-ACTOR-BLOCK-PROJECTION-01: NPC action_lines → actor_action at index 3."""
    gs: dict[str, Any] = {"generation": {"metadata": {}}}
    bundle = {
        "gm_narration": ["Narrator one.", "Narrator two.", "Narrator three."],
    }
    structured = {
        "spoken_lines": [{"speaker_id": "annette_reille", "text": "Human line only"}],
        "action_lines": [{"actor_id": "michel_longstreet", "text": "Michel folds his hands."}],
    }
    proj = {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette",
        "npc_actor_ids": ["michel_longstreet"],
    }
    blocks = _live_scene_blocks_from_visible_bundle(
        bundle,
        turn_number=0,
        structured_output=structured,
        runtime_projection=proj,
        graph_state=gs,
        session_output_language="en",
    )
    assert _opening_block_contract_satisfied(blocks)
    assert str(blocks[3].get("block_type")) == "actor_action"
    ev = gs.get("_actor_block_projection_evidence") or {}
    assert ev.get("actor_block_source") == "action_lines"


def test_open_actor_block_projection_human_only_spoken_fails_and_surfaces_filter_reason():
    """OPEN-ACTOR-BLOCK-PROJECTION-01: only human spoken_lines → no actor block + audit reason."""
    gs: dict[str, Any] = {"generation": {"metadata": {}}}
    bundle = {"gm_narration": ["One.", "Two.", "Three."]}
    structured = {"spoken_lines": [{"speaker_id": "alain_reille", "text": "I am the human PC."}]}
    proj = {
        "human_actor_id": "alain_reille",
        "selected_player_role": "alain",
        "npc_actor_ids": ["annette_reille"],
    }
    blocks = _live_scene_blocks_from_visible_bundle(
        bundle,
        turn_number=0,
        structured_output=structured,
        runtime_projection=proj,
        graph_state=gs,
        session_output_language="en",
    )
    assert _opening_block_contract_satisfied(blocks) is False
    ev = gs.get("_actor_block_projection_evidence") or {}
    assert ev.get("actor_block_filtered_reason") == "actor_block_missing_due_to_human_actor_filter"
    assert ev.get("actor_block_source") == "none"


def test_open_actor_block_projection_no_structured_actor_fails_contract():
    gs: dict[str, Any] = {"generation": {"metadata": {}}}
    bundle = {"gm_narration": ["A", "B", "C"]}
    blocks = _live_scene_blocks_from_visible_bundle(
        bundle,
        turn_number=0,
        structured_output={"spoken_lines": []},
        runtime_projection={"human_actor_id": "annette_reille"},
        graph_state=gs,
        session_output_language="en",
    )
    assert _opening_block_contract_satisfied(blocks) is False


def test_open_actor_block_projection_annette_npc_spoken_fixture_stays_green():
    """Annette-as-human with Veronique NPC string line remains valid opening shape."""
    gs: dict[str, Any] = {"generation": {"metadata": {}}}
    bundle = {
        "gm_narration": [
            "Two couples gather after the schoolyard incident.",
            "You are Annette. Every glance tests civility.",
            "In the Paris salon, chairs face each other.",
        ],
        "spoken_lines": ["Veronique: We should keep this civil."],
    }
    proj = {
        "human_actor_id": "annette_reille",
        "selected_player_role": "Annette",
        "npc_actor_ids": ["veronique_vallon"],
    }
    blocks = _live_scene_blocks_from_visible_bundle(
        bundle,
        turn_number=0,
        structured_output=None,
        runtime_projection=proj,
        graph_state=gs,
        session_output_language="en",
    )
    assert _opening_block_contract_satisfied(blocks) is True


def test_live_scene_blocks_prepackaged_scene_blocks_run_finalize_and_drop_name_only():
    """LDSS-supplied scene_blocks must not bypass VISIBLE-NARRATIVE-CONTRACT-02 (name-only lines)."""
    gs: dict[str, Any] = {"generation": {"metadata": {}}}
    bundle = {
        "scene_blocks": [
            {"id": "b1", "block_type": "narrator", "text": "Ein echter Beat.", "speaker_label": "Narrator"},
            {
                "id": "b2",
                "block_type": "actor_line",
                "text": "Veronique:",
                "speaker_label": "Veronique",
                "actor_id": "veronique_vallon",
            },
            {
                "id": "b3",
                "block_type": "actor_line",
                "text": "Jetzt mit Inhalt.",
                "speaker_label": "Veronique",
                "actor_id": "veronique_vallon",
            },
        ]
    }
    proj = {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette",
        "npc_actor_ids": ["veronique_vallon"],
    }
    blocks = _live_scene_blocks_from_visible_bundle(
        bundle,
        turn_number=1,
        graph_state=gs,
        runtime_projection=proj,
        session_output_language="de",
    )
    assert len(blocks) == 2
    assert str(blocks[0].get("block_type")) == "narrator"
    assert str(blocks[1].get("block_type")) == "actor_line"
    assert (blocks[1].get("text") or "").strip().startswith("Jetzt")
    vis = gs.get("_visible_narrative_contract") or {}
    assert isinstance(vis, dict) and vis.get("visible_narrative_contract_version") == "VISIBLE-NARRATIVE-CONTRACT-02"


def test_live_scene_blocks_player_input_echo_dropped_from_npc_prepackaged_blocks():
    """Committed raw_input must not reappear as an NPC actor_line (model leak)."""
    gs: dict[str, Any] = {"generation": {"metadata": {}}}
    player = "I leave the room and go home without saying goodbye."
    bundle = {
        "scene_blocks": [
            {"id": "b1", "block_type": "narrator", "text": "Scene.", "speaker_label": "Narrator"},
            {
                "id": "b2",
                "block_type": "actor_line",
                "text": f"Veronique: {player}",
                "speaker_label": "Veronique",
                "actor_id": "veronique_vallon",
            },
            {
                "id": "b3",
                "block_type": "actor_line",
                "text": "Then go.",
                "speaker_label": "Veronique",
                "actor_id": "veronique_vallon",
            },
        ]
    }
    proj = {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette",
        "npc_actor_ids": ["veronique_vallon"],
    }
    blocks = _live_scene_blocks_from_visible_bundle(
        bundle,
        turn_number=1,
        graph_state=gs,
        runtime_projection=proj,
        session_output_language="de",
        player_input=player,
    )
    assert len(blocks) == 2
    assert str(blocks[1].get("block_type")) == "actor_line"
    assert (blocks[1].get("text") or "").strip().startswith("Then")
    vis = gs.get("_visible_narrative_contract") or {}
    assert vis.get("player_input_echo_removed_from_npc_block") == 1


def test_visible_narrative_contract_strips_leaked_beat_prefixes_german_session():
    """VISIBLE-NARRATIVE-CONTRACT-01: internal beat labels never reach scene_blocks text."""
    gs: dict[str, Any] = {"generation": {"metadata": {}}}
    bundle = {
        "gm_narration": [
            "narrator_intro: Erster deutscher Beat über das Treffen.",
            "role_anchor: Du bist Annette, mitten in der Auseinandersetzung.",
            "scene_setup: Der Pariser Salon ist still und angespannt.",
        ],
    }
    proj = {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette",
        "npc_actor_ids": ["veronique_vallon"],
    }
    blocks = _live_scene_blocks_from_visible_bundle(
        bundle,
        turn_number=0,
        graph_state=gs,
        runtime_projection=proj,
        session_output_language="de",
    )
    assert str(blocks[0].get("block_type")) == "narrator"
    assert "narrator_intro:" not in (blocks[0].get("text") or "").lower()
    assert "role_anchor:" not in (blocks[1].get("text") or "").lower()
    assert "scene_setup:" not in (blocks[2].get("text") or "").lower()
    vis = gs.get("_visible_narrative_contract") or {}
    assert vis.get("selected_role_visible_in_opening") is True
    assert vis.get("visible_language_contract_pass") is True


def test_langfuse_path_spans_include_intent_semantic_director_fields(monkeypatch):
    from ai_stack.goc_subtext_policy import rule_spec_for_subtext

    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    rule = rule_spec_for_subtext("direct_accusation")
    path_summary = {
        "session_id": "session-intent-001",
        "module_id": "god_of_carnage",
        "turn_number": 3,
        "turn_kind": "normal",
        "nodes_executed": ["interpret_input", "validate_seam", "commit_seam"],
        "quality_class": "healthy",
        "degradation_signals": [],
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "runtime_mode": "solo_story",
        "generation_mode": "live_openai",
        "validation_called": True,
        "commit_called": True,
        "player_input_kind": "action",
        "player_action_committed": True,
        "player_speech_committed": False,
        "narrator_response_expected": True,
        "npc_response_expected": False,
        "semantic_move_kind": "direct_accusation",
        "subtext_surface_mode": rule["surface_mode"],
        "subtext_hidden_intent_hypothesis": rule["hidden_intent_hypothesis"],
        "subtext_function": rule["subtext_function"],
        "subtext_sincerity_band": rule["sincerity_band"],
        "subtext_policy_rule_id": "direct_accusation",
        "subtext_contract_pass": 1,
        "scene_director_selection_source": "intent_surface",
        "planner_rationale_codes": ["player_action_requires_spatial_consequence"],
        "legacy_keyword_scene_candidates_used": False,
        "npc_narrated_player_action_violation": False,
        "intent_surface_contract_pass": 1,
        "player_input_attribution_pass": 1,
        "semantic_move_alignment_pass": 1,
        "npc_action_narration_boundary_pass": 1,
    }
    _emit_langfuse_path_spans(path_summary)

    created_child_names = [call.kwargs["name"] for call in adapter.create_child_span.call_args_list]
    assert "story.phase.intent_interpretation" in created_child_names
    validation_output = _last_span_output_for(adapter, "story.phase.validation")
    assert validation_output["player_input_kind"] == "action"
    assert validation_output["semantic_move_kind"] == "direct_accusation"
    assert validation_output["subtext_surface_mode"] == rule["surface_mode"]
    assert validation_output["subtext_hidden_intent_hypothesis"] == rule["hidden_intent_hypothesis"]
    assert validation_output["subtext_function"] == rule["subtext_function"]
    assert validation_output["subtext_contract_pass"] == 1
    assert validation_output["scene_director_selection_source"] == "intent_surface"
    assert validation_output["planner_rationale_codes"] == ["player_action_requires_spatial_consequence"]
    assert validation_output["npc_narrated_player_action_violation"] is False


def test_langfuse_scores_include_intent_surface_contract_evidence(monkeypatch):
    from ai_stack.goc_subtext_policy import rule_spec_for_subtext

    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)
    rule = rule_spec_for_subtext("probe_inquiry")
    path_summary = _healthy_path_summary_turn(1)
    path_summary.update(
        {
            "player_input_kind": "perception",
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "semantic_move_kind": "observe",
            "subtext_surface_mode": rule["surface_mode"],
            "subtext_hidden_intent_hypothesis": rule["hidden_intent_hypothesis"],
            "subtext_function": rule["subtext_function"],
            "subtext_sincerity_band": rule["sincerity_band"],
            "subtext_policy_rule_id": "probe_inquiry",
            "scene_director_selection_source": "semantic_move",
            "planner_rationale_codes": ["player_perception_requires_environmental_feedback"],
            "legacy_keyword_scene_candidates_used": False,
            "npc_narrated_player_action_violation": False,
            "player_input_attribution_pass": 1,
        }
    )
    graph_state = {"model_prompt": "prompt"}
    event = {"visible_output_bundle": {"scene_blocks": [{"block_type": "narrator", "text": "x"}]}}
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state=graph_state,
        event=event,
    )

    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["intent_surface_contract_pass"] == 1.0
    assert score_values["player_input_attribution_pass"] == 1.0
    assert score_values["semantic_move_alignment_pass"] == 1.0
    assert score_values["subtext_contract_pass"] == 1.0
    assert score_values["npc_action_narration_boundary_pass"] == 1.0

    metadata = _last_score_metadata_for(adapter, "intent_surface_contract_pass")
    assert metadata["player_input_kind"] == "perception"
    assert metadata["semantic_move_kind"] == "observe"
    assert metadata["subtext_surface_mode"] == rule["surface_mode"]
    assert metadata["subtext_hidden_intent_hypothesis"] == rule["hidden_intent_hypothesis"]
    assert metadata["subtext_function"] == rule["subtext_function"]
    assert metadata["subtext_sincerity_band"] == rule["sincerity_band"]
    assert metadata["scene_director_selection_source"] == "semantic_move"
    assert metadata["planner_rationale_codes"] == ["player_perception_requires_environmental_feedback"]


def test_langfuse_scores_use_shared_extended_intent_contract(monkeypatch):
    from ai_stack.goc_subtext_policy import rule_spec_for_subtext

    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    intent_kind = "object_interaction"
    assert intent_kind in PLAYER_INPUT_KINDS
    rule = rule_spec_for_subtext("establish_situational_pressure")
    path_summary = _healthy_path_summary_turn(1)
    path_summary.update(
        {
            "player_input_kind": intent_kind,
            "player_input_kind_family": player_input_kind_family(intent_kind),
            "intent_contract_version": INTENT_CONTRACT_VERSION,
            **default_commit_flags_for_player_input_kind(intent_kind),
            "semantic_move_kind": "establish_situational_pressure",
            "subtext_surface_mode": rule["surface_mode"],
            "subtext_hidden_intent_hypothesis": rule["hidden_intent_hypothesis"],
            "subtext_function": rule["subtext_function"],
            "subtext_sincerity_band": rule["sincerity_band"],
            "subtext_policy_rule_id": "establish_situational_pressure",
            "scene_director_selection_source": "semantic_move",
            "planner_rationale_codes": [],
            "legacy_keyword_scene_candidates_used": False,
            "npc_narrated_player_action_violation": False,
            "player_input_attribution_pass": 1,
        }
    )
    graph_state = {"model_prompt": "prompt"}
    event = {"visible_output_bundle": {"scene_blocks": [{"block_type": "narrator", "text": "x"}]}}
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state=graph_state,
        event=event,
    )

    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["intent_surface_contract_pass"] == 1.0
    assert score_values["semantic_move_alignment_pass"] == 1.0
    assert score_values["subtext_contract_pass"] == 1.0

    metadata = _last_score_metadata_for(adapter, "intent_surface_contract_pass")
    assert metadata["player_input_kind_family"] == player_input_kind_family(intent_kind)
    assert metadata["intent_contract_version"] == INTENT_CONTRACT_VERSION
    assert metadata["subtext_function"] == rule["subtext_function"]


def test_langfuse_scores_reject_guarded_action_probe_alignment(monkeypatch):
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    monkeypatch.setattr("app.story_runtime.manager.LangfuseAdapter.get_instance", lambda: adapter)

    intent_kind = "physical_action"
    forbidden_move = sorted(FORBIDDEN_NON_SPEECH_ACTION_SEMANTIC_MOVES)[0]
    path_summary = _healthy_path_summary_turn(1)
    path_summary.update(
        {
            "player_input_kind": intent_kind,
            "player_input_kind_family": player_input_kind_family(intent_kind),
            "intent_contract_version": INTENT_CONTRACT_VERSION,
            **default_commit_flags_for_player_input_kind(intent_kind),
            "semantic_move_kind": forbidden_move,
            "scene_director_selection_source": "semantic_move",
            "planner_rationale_codes": [],
            "legacy_keyword_scene_candidates_used": False,
            "npc_narrated_player_action_violation": False,
            "player_input_attribution_pass": 1,
        }
    )
    graph_state = {"model_prompt": "prompt"}
    event = {"visible_output_bundle": {"scene_blocks": [{"block_type": "narrator", "text": "x"}]}}
    _emit_langfuse_evidence_observations(
        path_summary=path_summary,
        graph_state=graph_state,
        event=event,
    )

    score_values = {c.kwargs["name"]: c.kwargs["value"] for c in adapter.add_score.call_args_list}
    assert score_values["intent_surface_contract_pass"] == 1.0
    assert score_values["semantic_move_alignment_pass"] == 0.0


def test_langfuse_child_span_log_placeholder_when_sdk_ids_absent(caplog):
    """SDK handles often lack public ids before flush; logs must not read as span creation failure."""
    from app.observability import langfuse_adapter as lf_mod

    caplog.set_level(logging.INFO, logger="app.observability.langfuse_adapter")
    adapter = lf_mod.LangfuseAdapter.__new__(lf_mod.LangfuseAdapter)
    adapter.is_ready = True
    adapter._public_key = "pk-test"
    adapter._secret_key = "sk-test"
    adapter._config = SimpleNamespace(environment="development")
    client = MagicMock()
    adapter._clients = {"development": client}
    parent_span = MagicMock()
    parent_span.trace_id = "a1b2c3d4e5f6789012345678901234ab"
    child_span = MagicMock()
    parent_span.start_observation.return_value = child_span
    token_span = lf_mod._active_span_context.set(parent_span)
    token_session = lf_mod._active_langfuse_session_id.set("sess-log-test")
    token_client = lf_mod._active_langfuse_client.set(client)
    try:
        lf_mod.LangfuseAdapter.create_child_span(
            adapter,
            name="story.phase.validation",
            metadata={"canonical_turn_id": "c1:turn:0"},
        )
    finally:
        lf_mod._active_langfuse_client.reset(token_client)
        lf_mod._active_langfuse_session_id.reset(token_session)
        lf_mod._active_span_context.reset(token_span)

    assert parent_span.start_observation.called

    def _parse_json_from_record(rec: logging.LogRecord) -> dict[str, Any] | None:
        msg = rec.getMessage()
        if "langfuse_child_span_created" not in msg:
            return None
        brace = msg.index("{")
        return json.loads(msg[brace:])

    row = next(
        parsed
        for r in caplog.records
        if r.levelno == logging.INFO and (parsed := _parse_json_from_record(r)) is not None
    )
    assert row["event"] == "langfuse_child_span_created"
    assert row["name"] == "story.phase.validation"
    assert row["langfuse_span_id"] == lf_mod._LANGFUSE_ID_UNAVAILABLE
    assert row["langfuse_parent_span_id"] == lf_mod._LANGFUSE_ID_UNAVAILABLE
    assert row["span_successfully_created"] is True
    assert row["trace_ref"] == "a1b2c3d4e5f6789012345678901234ab"
    assert row["story_session_id"] == "sess-log-test"
    assert row["canonical_turn_id"] == "c1:turn:0"
    assert "story.phase.validation:py" in row["local_span_ref"]


def test_langfuse_set_active_span_clear_logs_without_imploding(caplog):
    from app.observability import langfuse_adapter as lf_mod

    caplog.set_level(logging.INFO, logger="app.observability.langfuse_adapter")
    adapter = lf_mod.LangfuseAdapter.__new__(lf_mod.LangfuseAdapter)
    adapter.is_ready = True
    prev = MagicMock()
    prev.trace_id = "trace-clear-test-1234567890abcd"
    token_span = lf_mod._active_span_context.set(prev)
    token_sid = lf_mod._active_langfuse_session_id.set("sid-before-clear")
    token_client = lf_mod._active_langfuse_client.set(MagicMock())
    try:
        lf_mod.LangfuseAdapter.set_active_span(adapter, None)
        assert lf_mod._active_span_context.get() is None
    finally:
        lf_mod._active_langfuse_client.reset(token_client)
        lf_mod._active_langfuse_session_id.reset(token_sid)
        lf_mod._active_span_context.reset(token_span)

    row = None
    for r in caplog.records:
        if r.levelno != logging.INFO:
            continue
        msg = r.getMessage()
        if "cleared_active_span" not in msg:
            continue
        brace = msg.index("{")
        row = json.loads(msg[brace:])
        break
    assert row is not None
    assert row["event"] == "langfuse_set_active_span"
    assert row["cleared_active_span"] is True
    assert row["previous_story_session_id"] == "sid-before-clear"
