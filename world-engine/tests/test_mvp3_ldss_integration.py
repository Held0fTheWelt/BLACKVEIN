"""MVP3 LDSS Manager Integration Tests.

Proves that _finalize_committed_turn produces SceneTurnEnvelope.v2 for GoC
solo sessions through the real world-engine story runtime seam (deepest active
seam without a live AI call).

These tests complement the gate tests in tests/gates/test_goc_mvp03_live_dramatic_scene_simulator_gate.py
which are limited by the backend/world-engine `app` namespace conflict in the
root test context.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from story_runtime_core.model_registry import ModelRegistry
from app.story_runtime.manager import StoryRuntimeManager


# ---------------------------------------------------------------------------
# Mock graph state for testing without real AI
# ---------------------------------------------------------------------------

def _mock_graph_state(*, force_ldss_scene_fallback: bool = False) -> dict:
    """Graph state returned by the mocked turn graph.

    By default the visible bundle yields live scene blocks (live graph primary).
    Set ``force_ldss_scene_fallback=True`` to skip live projection and exercise
    the LDSS envelope builder (``evidenced_live_path`` diagnostics).
    """
    state = {
        "validation_outcome": {
            "status": "approved",
            "reason": "mock_approved",
            "actor_lane_validation": {"status": "approved"},
        },
        "generation": {
            "success": True,
            "content": "Mock narration text.",
            "metadata": {"adapter": "mock", "model": "mock"},
        },
        "routing": {
            "selected_provider": "mock",
            "selected_model": "mock",
            "fallback_stage_reached": "primary_only",
        },
        "graph_diagnostics": {"errors": []},
        "visible_output_bundle": {
            "gm_narration": ["Mock narration."],
            "spoken_lines": [{"actor_id": "veronique", "text": "Test line."}],
            "action_lines": [],
        },
        "committed_result": {"commit_applied": True},
        "quality_class": "canonical",
        "degradation_signals": [],
        "actor_survival_telemetry": {},
        "interpreted_input": {"input_kind": "dialogue"},
    }
    if force_ldss_scene_fallback:
        state["force_ldss_scene_fallback"] = True
    return state


def _goc_solo_projection(human: str = "annette") -> dict:
    npc_map = {
        "annette": ["alain", "veronique", "michel"],
        "alain": ["annette", "veronique", "michel"],
    }
    npcs = npc_map.get(human, ["alain", "veronique", "michel"])
    lanes = {human: "human"}
    for n in npcs:
        lanes[n] = "npc"
    return {
        "module_id": "god_of_carnage",
        "start_scene_id": "phase_1",
        "selected_player_role": human,
        "human_actor_id": human,
        "npc_actor_ids": npcs,
        "actor_lanes": lanes,
        "runtime_profile_id": "god_of_carnage_solo",
        "runtime_module_id": "solo_story_runtime",
    }


def _make_manager_with_session(
    human: str = "annette",
    *,
    force_ldss_scene_fallback: bool = False,
) -> tuple[StoryRuntimeManager, object]:
    mgr = StoryRuntimeManager(registry=ModelRegistry(), adapters={})
    assert mgr._skip_graph_opening_on_create is True

    session = mgr.create_session(
        module_id="god_of_carnage",
        runtime_projection=_goc_solo_projection(human),
    )
    mock_turn_graph = MagicMock()
    mock_turn_graph.run.return_value = _mock_graph_state(
        force_ldss_scene_fallback=force_ldss_scene_fallback,
    )
    mgr.turn_graph = mock_turn_graph
    return mgr, session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_execute_turn_produces_scene_turn_envelope_annette():
    """execute_turn for GoC Annette session produces SceneTurnEnvelope.v2."""
    mgr, session = _make_manager_with_session("annette")
    result = mgr.execute_turn(
        session_id=session.session_id,
        player_input="Alain, can you please listen to what we're saying?",
    )

    assert "scene_turn_envelope" in result, (
        "scene_turn_envelope must be present in execute_turn result for GoC solo sessions"
    )
    env = result["scene_turn_envelope"]
    assert env["contract"] == "scene_turn_envelope.v2"
    assert env["human_actor_id"] == "annette"
    assert env["content_module_id"] == "god_of_carnage"
    assert "alain" in env["npc_actor_ids"]
    assert "annette" not in env["npc_actor_ids"]


@pytest.mark.mvp3
def test_execute_turn_produces_scene_turn_envelope_alain():
    """execute_turn for GoC Alain session produces SceneTurnEnvelope.v2."""
    mgr, session = _make_manager_with_session("alain")
    result = mgr.execute_turn(
        session_id=session.session_id,
        player_input="I understand your position.",
    )

    assert "scene_turn_envelope" in result
    env = result["scene_turn_envelope"]
    assert env["human_actor_id"] == "alain"
    assert "alain" not in env["npc_actor_ids"]
    assert "annette" in env["npc_actor_ids"]


@pytest.mark.mvp3
def test_scene_envelope_blocks_exclude_human_actor():
    """Human actor must not be AI-controlled speaker/actor in scene envelope blocks."""
    mgr, session = _make_manager_with_session("annette")
    result = mgr.execute_turn(
        session_id=session.session_id,
        player_input="What is going on here?",
    )

    env = result["scene_turn_envelope"]
    blocks = env["visible_scene_output"]["blocks"]
    for block in blocks:
        assert block.get("actor_id") != "annette", (
            "Human actor 'annette' must not be AI-generated in scene envelope"
        )
        assert block.get("actor_id") != "visitor", (
            "visitor must not appear in scene envelope blocks"
        )


@pytest.mark.mvp3
def test_scene_envelope_diagnostics_live_graph_primary_skips_ldss():
    """When live runtime projects scene blocks, LDSS is not invoked (primary graph path)."""
    mgr, session = _make_manager_with_session("annette")
    result = mgr.execute_turn(
        session_id=session.session_id,
        player_input="I just want to understand.",
    )

    env = result["scene_turn_envelope"]
    diag = env["diagnostics"]["live_dramatic_scene_simulator"]
    assert diag["status"] == "not_invoked_live_graph_primary"
    assert diag["invoked"] is False
    assert diag["entrypoint"] == "story.turn.execute"
    assert diag["legacy_blob_used"] is False
    assert diag["scene_block_count"] >= 1
    assert diag["scene_block_count"] == len(
        env["visible_scene_output"].get("blocks") or []
    )


@pytest.mark.mvp3
def test_scene_envelope_diagnostics_evidenced_live_path_via_ldss_fallback():
    """When live projection is bypassed, LDSS builds the envelope (evidenced_live_path)."""
    mgr, session = _make_manager_with_session("annette", force_ldss_scene_fallback=True)
    result = mgr.execute_turn(
        session_id=session.session_id,
        player_input="I just want to understand.",
    )

    env = result["scene_turn_envelope"]
    diag = env["diagnostics"]["live_dramatic_scene_simulator"]
    assert diag["status"] == "evidenced_live_path"
    assert diag["invoked"] is True
    assert diag["entrypoint"] == "story.turn.execute"
    assert diag["legacy_blob_used"] is False
    assert diag["scene_block_count"] >= 2


@pytest.mark.mvp3
def test_non_goc_session_has_no_scene_envelope():
    """Non-GoC sessions (no human_actor_id in projection) produce no scene_turn_envelope."""
    mgr = StoryRuntimeManager(registry=ModelRegistry(), adapters={})
    session = mgr.create_session(
        module_id="test_module",
        runtime_projection={"module_id": "test_module", "start_scene_id": "start"},
    )

    mock_turn_graph = MagicMock()
    mock_turn_graph.run.return_value = _mock_graph_state()
    mgr.turn_graph = mock_turn_graph

    result = mgr.execute_turn(session_id=session.session_id, player_input="Hello world")
    assert "scene_turn_envelope" not in result, (
        "scene_turn_envelope must only appear for GoC solo sessions with human_actor_id"
    )


@pytest.mark.mvp3
def test_actor_lane_enforcement_in_envelope():
    """Scene envelope diagnostics record actor lane enforcement metadata."""
    mgr, session = _make_manager_with_session("annette")
    result = mgr.execute_turn(
        session_id=session.session_id,
        player_input="Michel, please say something.",
    )

    env = result["scene_turn_envelope"]
    lane_diag = env["diagnostics"]["actor_lane_enforcement"]
    assert lane_diag["human_actor_id"] == "annette"
    assert lane_diag["validation_ran_before_commit"] is True
    assert "annette" in lane_diag["ai_forbidden_actor_ids"]
    assert "alain" in lane_diag["ai_allowed_actor_ids"]
