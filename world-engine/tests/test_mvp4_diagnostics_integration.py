"""MVP4 DiagnosticsEnvelope Manager Integration Tests.

Proves that _finalize_committed_turn produces diagnostics_envelope for GoC
solo sessions, and get_narrative_gov_summary returns operator health evidence.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock, patch

from story_runtime_core.model_registry import ModelRegistry
from app.observability.trace import LANGFUSE_TRACE_ID, set_langfuse_trace_id
from app.story_runtime.manager import StoryRuntimeManager


def _mock_graph_state():
    return {
        "validation_outcome": {
            "status": "approved",
            "reason": "mock_approved",
            "actor_lane_validation": {"status": "approved", "reason": ""},
        },
        "generation": {
            "attempted": True,
            "success": True,
            "content": "Mock narration.",
            "metadata": {
                "adapter": "mock",
                "model": "mock-model",
                "adapter_invocation_mode": "mock_test",
            },
            "structured_output": {"mock": True},
        },
        "routing": {
            "route_id": "test_route",
            "route_family": "narrative_live_generation",
            "selected_provider": "mock",
            "selected_model": "mock-model",
            "fallback_model": "mock-fallback",
            "fallback_chain": ["mock-model", "mock-fallback"],
            "fallback_stage_reached": "primary_only",
            "generation_execution_mode": "routed_llm_slm",
        },
        "nodes_executed": [
            "route_model",
            "invoke_model",
            "validate_seam",
            "commit_seam",
            "render_visible",
        ],
        "graph_diagnostics": {"errors": []},
        "visible_output_bundle": {"gm_narration": ["Mock."]},
        "committed_result": {"commit_applied": True},
        "quality_class": "canonical",
        "degradation_signals": [],
        "actor_survival_telemetry": {},
        "interpreted_input": {"input_kind": "dialogue"},
    }


def _goc_projection(human: str = "annette"):
    npc_map = {"annette": ["alain", "veronique", "michel"], "alain": ["annette", "veronique", "michel"]}
    npcs = npc_map.get(human, ["alain", "veronique", "michel"])
    return {
        "module_id": "god_of_carnage",
        "start_scene_id": "phase_1",
        "selected_player_role": human,
        "human_actor_id": human,
        "npc_actor_ids": npcs,
        "actor_lanes": {human: "human", **{n: "npc" for n in npcs}},
        "runtime_profile_id": "god_of_carnage_solo",
        "runtime_module_id": "solo_story_runtime",
        "content_module_id": "god_of_carnage",
    }


def _make_manager(human: str = "annette"):
    mgr = StoryRuntimeManager(registry=ModelRegistry(), adapters={})
    session = mgr.create_session(
        module_id="god_of_carnage",
        runtime_projection=_goc_projection(human),
    )
    mock_tg = MagicMock()
    mock_tg.run.return_value = _mock_graph_state()
    mgr.turn_graph = mock_tg
    return mgr, session


@pytest.mark.mvp4
def test_execute_turn_produces_diagnostics_envelope_annette():
    """execute_turn for Annette session includes diagnostics_envelope."""
    mgr, session = _make_manager("annette")
    result = mgr.execute_turn(
        session_id=session.session_id,
        player_input="What are we doing here?",
    )
    assert "diagnostics_envelope" in result
    env = result["diagnostics_envelope"]
    assert env["contract"] == "diagnostics_envelope.v1"
    assert env["human_actor_id"] == "annette"
    assert env["response_packaged_from_committed_state"] is True
    assert "visitor" not in json.dumps(env)


@pytest.mark.mvp4
def test_execute_turn_produces_diagnostics_envelope_alain():
    """execute_turn for Alain session includes diagnostics_envelope."""
    mgr, session = _make_manager("alain")
    result = mgr.execute_turn(
        session_id=session.session_id,
        player_input="I disagree with that.",
    )
    assert "diagnostics_envelope" in result
    env = result["diagnostics_envelope"]
    assert env["human_actor_id"] == "alain"
    assert "annette" in env["npc_actor_ids"]


@pytest.mark.mvp4
def test_diagnostics_envelope_actor_ownership():
    """Envelope includes actor ownership fields correctly."""
    mgr, session = _make_manager("annette")
    result = mgr.execute_turn(session_id=session.session_id, player_input="test")
    env = result["diagnostics_envelope"]
    assert env["human_actor_id"] == "annette"
    assert "alain" in env["ai_allowed_actor_ids"]
    assert "annette" in env["ai_forbidden_actor_ids"]
    assert "visitor" not in env["ai_allowed_actor_ids"]


@pytest.mark.mvp4
def test_diagnostics_envelope_includes_phase_b_cost_truth():
    """GoC diagnostics include detailed deterministic phase cost records."""
    mgr, session = _make_manager("annette")
    result = mgr.execute_turn(session_id=session.session_id, player_input="test")
    cost_summary = result["diagnostics_envelope"]["cost_summary"]

    assert cost_summary["input_tokens"] == 0
    assert cost_summary["output_tokens"] == 0
    assert cost_summary["cost_usd"] == 0.0
    assert "phase_costs" in cost_summary
    assert "ldss" in cost_summary["phase_costs"]
    assert "narrator" in cost_summary["phase_costs"]
    ldss_cost = cost_summary["phase_costs"]["ldss"]
    assert ldss_cost["billing_mode"] == "deterministic"
    assert ldss_cost["token_source"] == "deterministic_no_model_call"
    assert ldss_cost["billable"] is False
    assert ldss_cost["model"] == "ldss_deterministic"


@pytest.mark.mvp4
def test_diagnostics_cost_summary_matches_phase_cost_sum():
    """Aggregated cost summary equals the sum of detailed phase records."""
    mgr, session = _make_manager("annette")
    result = mgr.execute_turn(session_id=session.session_id, player_input="test")
    cost_summary = result["diagnostics_envelope"]["cost_summary"]
    phases = cost_summary["phase_costs"].values()

    assert cost_summary["input_tokens"] == sum(p["input_tokens"] for p in phases)
    assert cost_summary["output_tokens"] == sum(p["output_tokens"] for p in phases)
    assert cost_summary["cost_usd"] == pytest.approx(sum(p["cost_usd"] for p in phases))


@pytest.mark.mvp4
def test_diagnostics_envelope_langfuse_status():
    """langfuse_status reflects runtime adapter state."""
    mgr, session = _make_manager("annette")
    with patch("app.story_runtime.manager.LangfuseAdapter.get_instance") as get_instance:
        get_instance.return_value.is_enabled.return_value = False
        result = mgr.execute_turn(session_id=session.session_id, player_input="test")

    env = result["diagnostics_envelope"]
    assert env["langfuse_status"] == "disabled"
    assert env["langfuse_trace_id"] == ""


@pytest.mark.mvp4
def test_diagnostics_envelope_uses_request_langfuse_trace_id():
    """Diagnostics include the propagated Langfuse trace id when tracing is runtime-enabled."""
    mgr, session = _make_manager("annette")
    token = set_langfuse_trace_id("0123456789abcdef0123456789abcdef")
    try:
        with patch("app.story_runtime.manager.LangfuseAdapter.get_instance") as get_instance:
            get_instance.return_value.is_enabled.return_value = True
            result = mgr.execute_turn(session_id=session.session_id, player_input="test")
    finally:
        LANGFUSE_TRACE_ID.reset(token)

    env = result["diagnostics_envelope"]
    assert env["langfuse_status"] == "traced"
    assert env["langfuse_trace_id"] == "0123456789abcdef0123456789abcdef"


@pytest.mark.mvp4
def test_execute_turn_emits_langfuse_path_spans():
    """Langfuse trace shows model route/invoke/fallback/validation/commit path truth."""
    mgr, session = _make_manager("annette")
    adapter = MagicMock()
    adapter.is_enabled.return_value = True
    adapter.create_child_span.return_value = MagicMock()

    with patch("app.story_runtime.manager.LangfuseAdapter.get_instance", return_value=adapter):
        result = mgr.execute_turn(session_id=session.session_id, player_input="test")

    summary = result.get("observability_path_summary") or {}
    assert summary["contract"] == "story_runtime_path_observability.v1"
    assert summary["route_model_called"] is True
    assert summary["invoke_model_called"] is True
    assert summary["fallback_model_called"] is False
    assert summary["validation_called"] is True
    assert summary["commit_called"] is True
    assert summary["selected_model"] == "mock-model"
    assert summary["adapter"] == "mock"
    assert summary["generation_success"] is True

    created_child_names = [call.kwargs["name"] for call in adapter.create_child_span.call_args_list]
    assert "story.graph.path_summary" in created_child_names
    assert "story.phase.model_route" in created_child_names
    assert "story.phase.model_invoke" in created_child_names
    assert "story.phase.model_fallback" in created_child_names
    assert "story.phase.validation" in created_child_names
    assert "story.phase.commit" in created_child_names


@pytest.mark.mvp4
def test_diagnostics_traceable_decisions_present():
    """Envelope includes traceable decisions for responder, actor-lane, drama, commit."""
    mgr, session = _make_manager("annette")
    result = mgr.execute_turn(session_id=session.session_id, player_input="test")
    env = result["diagnostics_envelope"]
    decisions = env.get("traceable_decisions") or []
    assert len(decisions) >= 2
    types = {d["decision_type"] for d in decisions}
    assert "actor_lane_validation" in types
    assert "engine_commit" in types


@pytest.mark.mvp4
def test_get_last_diagnostics_envelope_method():
    """get_last_diagnostics_envelope returns envelope after turn."""
    mgr, session = _make_manager("annette")
    mgr.execute_turn(session_id=session.session_id, player_input="test")
    envelope = mgr.get_last_diagnostics_envelope(session.session_id)
    assert envelope is not None
    assert envelope["contract"] == "diagnostics_envelope.v1"


@pytest.mark.mvp4
def test_narrative_gov_summary_after_turn():
    """get_narrative_gov_summary returns real operator health after turn."""
    mgr, session = _make_manager("annette")
    mgr.execute_turn(session_id=session.session_id, player_input="test")
    summary = mgr.get_narrative_gov_summary()
    assert summary["contract"] == "narrative_gov_summary.v1"
    assert summary["last_story_session_id"] == session.session_id
    assert summary["last_turn_number"] == 1
    assert summary["ldss_health"]["status"] == "evidenced_live_path"
    assert summary["actor_lane_health"]["visitor_present"] is False


@pytest.mark.mvp4
def test_non_goc_session_no_diagnostics_envelope():
    """Non-GoC sessions do not produce diagnostics_envelope."""
    mgr = StoryRuntimeManager(registry=ModelRegistry(), adapters={})
    session = mgr.create_session(
        module_id="test_module",
        runtime_projection={"module_id": "test_module", "start_scene_id": "start"},
    )
    mock_tg = MagicMock()
    mock_tg.run.return_value = _mock_graph_state()
    mgr.turn_graph = mock_tg
    result = mgr.execute_turn(session_id=session.session_id, player_input="test")
    assert "diagnostics_envelope" not in result
