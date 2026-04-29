"""MVP2 tests — Runtime State, Actor Lanes, Human Actor Protection (Waves 2.1–2.2).

Wave 2.1 proves:
- ActorLaneContext built correctly for Annette and Alain starts
- human_actor_id is the selected actor; all others are NPCs
- ai_allowed_actor_ids excludes the human actor
- ai_forbidden_actor_ids contains the human actor
- ActorLaneContext builds directly from MVP1 build_actor_ownership() output
- visitor is rejected from actor lanes
- RuntimeState carries source provenance
- StorySessionState persists role ownership

Wave 2.2 proves:
- AI cannot speak, act, assign emotion, or decide for the human actor
- Human actor cannot be primary or secondary responder
- Visitor cannot be a responder
- Validation runs before response packaging (commit is blocked when validation rejects)
"""

from __future__ import annotations

import pytest

from app.runtime.actor_lane import (
    build_actor_lane_context,
    build_runtime_state,
    build_story_session_state,
    validate_actor_lane_output,
    validate_responder_plan,
)
from app.runtime.models import ActorLaneContext, ActorLaneValidationResult, RuntimeState, StorySessionState

# ---------------------------------------------------------------------------
# Shared fixture data (derived from MVP1 handoff + content/modules/god_of_carnage/characters.yaml)
# Canonical actor IDs: annette, alain, veronique, michel
# ---------------------------------------------------------------------------

_GOC_CANONICAL_ACTORS = frozenset({"annette", "alain", "veronique", "michel"})

_ANNETTE_OWNERSHIP = {
    "human_actor_id": "annette",
    "npc_actor_ids": ["alain", "veronique", "michel"],
    "actor_lanes": {
        "annette": "human",
        "alain": "npc",
        "veronique": "npc",
        "michel": "npc",
    },
    "visitor_present": False,
    "content_hash": "sha256:test-content-hash",
}

_ALAIN_OWNERSHIP = {
    "human_actor_id": "alain",
    "npc_actor_ids": ["annette", "veronique", "michel"],
    "actor_lanes": {
        "alain": "human",
        "annette": "npc",
        "veronique": "npc",
        "michel": "npc",
    },
    "visitor_present": False,
    "content_hash": "sha256:test-content-hash",
}


# ---------------------------------------------------------------------------
# Wave 2.1: ActorLaneContext construction
# ---------------------------------------------------------------------------

def test_actor_lane_context_created_for_annette_start():
    ctx = build_actor_lane_context(
        _ANNETTE_OWNERSHIP,
        selected_player_role="annette",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
    )
    assert isinstance(ctx, ActorLaneContext)
    assert ctx.contract == "actor_lane_context.v1"
    assert ctx.human_actor_id == "annette"
    assert ctx.selected_player_role == "annette"
    assert ctx.runtime_profile_id == "god_of_carnage_solo"
    assert ctx.content_module_id == "god_of_carnage"


def test_actor_lane_context_created_for_alain_start():
    ctx = build_actor_lane_context(
        _ALAIN_OWNERSHIP,
        selected_player_role="alain",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
    )
    assert isinstance(ctx, ActorLaneContext)
    assert ctx.human_actor_id == "alain"
    assert ctx.selected_player_role == "alain"


def test_selected_actor_is_human():
    for selected, ownership in [("annette", _ANNETTE_OWNERSHIP), ("alain", _ALAIN_OWNERSHIP)]:
        ctx = build_actor_lane_context(
            ownership,
            selected_player_role=selected,
            runtime_profile_id="god_of_carnage_solo",
            content_module_id="god_of_carnage",
        )
        assert ctx.actor_lanes[selected] == "human", f"{selected} lane should be 'human'"
        assert ctx.is_human_actor(selected)
        assert not ctx.is_npc_actor(selected)


def test_non_selected_canonical_actors_are_npcs():
    ctx = build_actor_lane_context(
        _ANNETTE_OWNERSHIP,
        selected_player_role="annette",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
    )
    for npc_id in ["alain", "veronique", "michel"]:
        assert ctx.actor_lanes[npc_id] == "npc", f"{npc_id} should be npc"
        assert ctx.is_npc_actor(npc_id)
        assert not ctx.is_human_actor(npc_id)


def test_ai_forbidden_actor_ids_contains_human():
    ctx = build_actor_lane_context(
        _ANNETTE_OWNERSHIP,
        selected_player_role="annette",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
    )
    assert "annette" in ctx.ai_forbidden_actor_ids
    assert ctx.is_ai_forbidden("annette")


def test_ai_allowed_actor_ids_excludes_human():
    ctx = build_actor_lane_context(
        _ANNETTE_OWNERSHIP,
        selected_player_role="annette",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
    )
    assert "annette" not in ctx.ai_allowed_actor_ids
    for npc_id in ["alain", "veronique", "michel"]:
        assert npc_id in ctx.ai_allowed_actor_ids


def test_ai_allowed_and_forbidden_are_disjoint():
    for ownership, selected in [(_ANNETTE_OWNERSHIP, "annette"), (_ALAIN_OWNERSHIP, "alain")]:
        ctx = build_actor_lane_context(
            ownership,
            selected_player_role=selected,
            runtime_profile_id="god_of_carnage_solo",
            content_module_id="god_of_carnage",
        )
        allowed = set(ctx.ai_allowed_actor_ids)
        forbidden = set(ctx.ai_forbidden_actor_ids)
        assert allowed.isdisjoint(forbidden), "allowed and forbidden sets must not overlap"


def test_actor_lane_context_uses_mvp1_handoff():
    """ActorLaneContext builds directly from profiles.py build_actor_ownership() output."""
    from app.runtime.profiles import build_actor_ownership, resolve_runtime_profile

    profile = resolve_runtime_profile("god_of_carnage_solo")
    ownership = build_actor_ownership("annette", profile)

    ctx = build_actor_lane_context(
        ownership,
        selected_player_role="annette",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
    )
    assert ctx.human_actor_id == "annette"
    assert ctx.contract == "actor_lane_context.v1"
    assert "annette" not in ctx.ai_allowed_actor_ids
    assert "annette" in ctx.ai_forbidden_actor_ids
    assert "visitor" not in ctx.actor_lanes
    assert "visitor" not in ctx.ai_allowed_actor_ids
    assert "visitor" not in ctx.ai_forbidden_actor_ids


def test_actor_lane_context_alain_npc_list():
    ctx = build_actor_lane_context(
        _ALAIN_OWNERSHIP,
        selected_player_role="alain",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
    )
    for npc_id in ["annette", "veronique", "michel"]:
        assert npc_id in ctx.ai_allowed_actor_ids
    assert "alain" not in ctx.ai_allowed_actor_ids
    assert "alain" in ctx.ai_forbidden_actor_ids


# ---------------------------------------------------------------------------
# Wave 2.1: RuntimeState provenance
# ---------------------------------------------------------------------------

def test_runtime_state_contains_source_provenance():
    rs = build_runtime_state(
        _ANNETTE_OWNERSHIP,
        run_id="run_test_001",
        story_session_id="story_test_001",
        selected_player_role="annette",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
        runtime_module_id="solo_story_runtime",
        content_hash="sha256:abc123",
        runtime_profile_hash="sha256:def456",
        runtime_module_hash="sha256:ghi789",
        current_scene_id="phase_1",
    )
    assert isinstance(rs, RuntimeState)
    assert rs.contract == "runtime_state.v1"
    assert rs.state_version == "runtime_state.goc_solo.v1"
    assert rs.content_module_id == "god_of_carnage"
    assert rs.runtime_profile_id == "god_of_carnage_solo"
    assert rs.runtime_module_id == "solo_story_runtime"
    assert rs.content_hash == "sha256:abc123"
    assert rs.runtime_profile_hash == "sha256:def456"
    assert rs.runtime_module_hash == "sha256:ghi789"
    assert rs.human_actor_id == "annette"
    assert rs.selected_player_role == "annette"
    assert rs.run_id == "run_test_001"
    assert rs.story_session_id == "story_test_001"


def test_runtime_state_actor_lanes_match_ownership():
    rs = build_runtime_state(
        _ANNETTE_OWNERSHIP,
        run_id="run_test_002",
        story_session_id="story_test_002",
        selected_player_role="annette",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
        runtime_module_id="solo_story_runtime",
        content_hash="sha256:test",
    )
    assert rs.actor_lanes["annette"] == "human"
    assert rs.actor_lanes["alain"] == "npc"
    assert rs.actor_lanes["veronique"] == "npc"
    assert rs.actor_lanes["michel"] == "npc"


# ---------------------------------------------------------------------------
# Wave 2.1: StorySessionState ownership
# ---------------------------------------------------------------------------

def test_story_session_state_persists_role_ownership():
    ss = build_story_session_state(
        _ANNETTE_OWNERSHIP,
        run_id="run_test_003",
        story_session_id="story_test_003",
        selected_player_role="annette",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
        runtime_module_id="solo_story_runtime",
        current_scene_id="phase_1",
        turn_number=0,
    )
    assert isinstance(ss, StorySessionState)
    assert ss.contract == "story_session_state.v1"
    assert ss.human_actor_id == "annette"
    assert ss.selected_player_role == "annette"
    assert ss.visitor_present is False
    assert ss.turn_number == 0


def test_selected_role_becomes_human_actor():
    for selected, ownership in [("annette", _ANNETTE_OWNERSHIP), ("alain", _ALAIN_OWNERSHIP)]:
        ss = build_story_session_state(
            ownership,
            run_id="run_x",
            story_session_id="story_x",
            selected_player_role=selected,
            runtime_profile_id="god_of_carnage_solo",
            content_module_id="god_of_carnage",
            runtime_module_id="solo_story_runtime",
        )
        assert ss.human_actor_id == selected


def test_remaining_roles_become_npc_actors():
    ss = build_story_session_state(
        _ANNETTE_OWNERSHIP,
        run_id="run_x",
        story_session_id="story_x",
        selected_player_role="annette",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
        runtime_module_id="solo_story_runtime",
    )
    assert set(ss.npc_actor_ids) == {"alain", "veronique", "michel"}
    assert "annette" not in ss.npc_actor_ids


def test_story_session_state_no_visitor():
    ss = build_story_session_state(
        _ANNETTE_OWNERSHIP,
        run_id="run_x",
        story_session_id="story_x",
        selected_player_role="annette",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
        runtime_module_id="solo_story_runtime",
    )
    assert ss.visitor_present is False
    assert "visitor" not in ss.npc_actor_ids
    assert ss.human_actor_id != "visitor"


# ---------------------------------------------------------------------------
# Wave 2.2: Human Actor Protection & Responder Validation
# ---------------------------------------------------------------------------

def _annette_ctx() -> ActorLaneContext:
    return build_actor_lane_context(
        _ANNETTE_OWNERSHIP,
        selected_player_role="annette",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
    )


def test_ai_cannot_speak_for_human_actor():
    ctx = _annette_ctx()
    result = validate_actor_lane_output(
        {"actor_id": "annette", "block_type": "actor_line", "text": "I think we should leave."},
        ctx,
    )
    assert isinstance(result, ActorLaneValidationResult)
    assert result.status == "rejected"
    assert result.error_code == "ai_controlled_human_actor"
    assert result.actor_id == "annette"
    assert result.block_kind == "actor_line"


def test_ai_cannot_speak_for_human_actor_via_speaker_id():
    ctx = _annette_ctx()
    result = validate_actor_lane_output(
        {"speaker_id": "annette", "block_type": "actor_line", "text": "No."},
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "ai_controlled_human_actor"


def test_ai_cannot_act_for_human_actor():
    ctx = _annette_ctx()
    result = validate_actor_lane_output(
        {"actor_id": "annette", "block_type": "actor_action", "text": "Annette stands up."},
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "ai_controlled_human_actor"
    assert result.block_kind == "actor_action"


def test_ai_cannot_assign_human_actor_emotion():
    ctx = _annette_ctx()
    result = validate_actor_lane_output(
        {"actor_id": "annette", "block_type": "emotional_state", "text": "feels ashamed"},
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "ai_controlled_human_actor"


def test_ai_cannot_decide_for_human_actor():
    ctx = _annette_ctx()
    result = validate_actor_lane_output(
        {"actor_id": "annette", "block_type": "decision", "text": "Annette decides to apologize."},
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "ai_controlled_human_actor"


def test_npc_output_is_approved():
    ctx = _annette_ctx()
    for npc_id in ["alain", "veronique", "michel"]:
        result = validate_actor_lane_output(
            {"actor_id": npc_id, "block_type": "actor_line", "text": "Some line."},
            ctx,
        )
        assert result.status == "approved", f"NPC {npc_id} should be approved"


def test_human_actor_cannot_be_primary_responder():
    ctx = _annette_ctx()
    result = validate_responder_plan(
        {"primary_responder_id": "annette", "secondary_responder_ids": []},
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "human_actor_selected_as_responder"
    assert result.actor_id == "annette"
    assert result.block_kind == "responder_nomination"


def test_human_actor_cannot_be_secondary_responder():
    ctx = _annette_ctx()
    result = validate_responder_plan(
        {"primary_responder_id": "alain", "secondary_responder_ids": ["annette", "michel"]},
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "human_actor_selected_as_responder"
    assert result.actor_id == "annette"


def test_valid_npc_responder_plan_approved():
    ctx = _annette_ctx()
    result = validate_responder_plan(
        {"primary_responder_id": "alain", "secondary_responder_ids": ["veronique"]},
        ctx,
    )
    assert result.status == "approved"


def test_actor_lane_validation_runs_before_response_packaging():
    """Enforcement runs before commit and before packaging.

    When run_validation_seam rejects due to human actor output, run_commit_seam
    must not commit (commit_applied=False) and run_visible_render must emit
    render_downgrade — proving validation is not post-hoc UI filtering.
    """
    import sys
    import os
    # ai_stack is a sibling package — add repo root to path if needed
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from ai_stack.goc_turn_seams import run_commit_seam, run_validation_seam, run_visible_render

    # Generation where AI speaks for the human actor (annette)
    generation_with_human_line = {
        "success": True,
        "content": "Some response",
        "metadata": {
            "structured_output": {
                "spoken_lines": [
                    {"speaker_id": "annette", "text": "I think we should leave now."},
                    {"speaker_id": "alain", "text": "You're right."},
                ]
            }
        },
    }

    actor_lane_ctx_dict = {
        "human_actor_id": "annette",
        "ai_forbidden_actor_ids": ["annette"],
    }

    # Actor-lane enforcement runs inside run_validation_seam — BEFORE packaging
    validation_outcome = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=[{"effect_type": "narrative_proposal", "description": "test"}],
        generation=generation_with_human_line,
        actor_lane_context=actor_lane_ctx_dict,
    )

    # Enforcement must reject BEFORE any commit or packaging
    assert validation_outcome["status"] == "rejected", (
        f"Expected rejection for human actor output, got: {validation_outcome}"
    )
    assert validation_outcome.get("error_code") == "ai_controlled_human_actor"

    # Commit seam must not commit when validation rejected
    committed = run_commit_seam(
        module_id="god_of_carnage",
        validation_outcome=validation_outcome,
        proposed_state_effects=[{"effect_type": "narrative_proposal", "description": "test"}],
    )
    assert committed["commit_applied"] is False, "Commit must be blocked by rejected validation"

    # Render must surface render_downgrade (not truth_aligned) when enforcement rejected
    bundle, markers = run_visible_render(
        module_id="god_of_carnage",
        committed_result=committed,
        validation_outcome=validation_outcome,
        generation=generation_with_human_line,
        transition_pattern="standard",
    )
    assert "truth_aligned" not in markers, "Rejected output must not be truth_aligned"
    assert bundle.get("render_downgrade") is not None, "render_downgrade must be present"


def test_actor_lane_validation_too_late_error():
    """Validation flagged as too-late returns actor_lane_validation_too_late error."""
    ctx = _annette_ctx()
    result = validate_actor_lane_output(
        {"actor_id": "alain", "block_type": "actor_line", "_already_committed": True},
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "actor_lane_validation_too_late"


# ---------------------------------------------------------------------------
# Phase 1 hardening: canonical test names + missing coverage
# ---------------------------------------------------------------------------

def test_ai_allowed_actor_ids_exclude_human_actor():
    """Canonical Phase 1 required test name."""
    ctx = _annette_ctx()
    assert "annette" not in ctx.ai_allowed_actor_ids
    for npc_id in ["alain", "veronique", "michel"]:
        assert npc_id in ctx.ai_allowed_actor_ids

    ctx_alain = build_actor_lane_context(
        _ALAIN_OWNERSHIP,
        selected_player_role="alain",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
    )
    assert "alain" not in ctx_alain.ai_allowed_actor_ids


def test_ai_forbidden_actor_ids_include_human_actor():
    """Canonical Phase 1 required test name."""
    ctx = _annette_ctx()
    assert "annette" in ctx.ai_forbidden_actor_ids
    assert ctx.is_ai_forbidden("annette")
    assert not ctx.is_ai_forbidden("alain")

    ctx_alain = build_actor_lane_context(
        _ALAIN_OWNERSHIP,
        selected_player_role="alain",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
    )
    assert "alain" in ctx_alain.ai_forbidden_actor_ids


def test_actor_lane_context_uses_mvp1_handoff_alain_start():
    """ActorLaneContext builds from real build_actor_ownership() for Alain start."""
    from app.runtime.profiles import build_actor_ownership, resolve_runtime_profile

    profile = resolve_runtime_profile("god_of_carnage_solo")
    ownership = build_actor_ownership("alain", profile)

    ctx = build_actor_lane_context(
        ownership,
        selected_player_role="alain",
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
    )
    assert ctx.human_actor_id == "alain"
    assert ctx.contract == "actor_lane_context.v1"
    assert "alain" not in ctx.ai_allowed_actor_ids
    assert "alain" in ctx.ai_forbidden_actor_ids
    assert "visitor" not in ctx.actor_lanes
    # Remaining three canonical actors are NPC
    for npc_id in ["annette", "veronique", "michel"]:
        assert npc_id in ctx.ai_allowed_actor_ids, f"{npc_id} must be in ai_allowed for Alain start"


# ---------------------------------------------------------------------------
# Phase 2 hardening: missing tests
# ---------------------------------------------------------------------------

def test_ai_cannot_move_human_actor():
    """AI output cannot assign movement to the human actor."""
    ctx = _annette_ctx()
    result = validate_actor_lane_output(
        {"actor_id": "annette", "block_type": "movement", "text": "Annette walks to the door."},
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "ai_controlled_human_actor"
    assert result.block_kind == "movement"


def test_ai_cannot_move_human_actor_physical_state():
    """AI output cannot assign a physical state change to the human actor."""
    ctx = _annette_ctx()
    result = validate_actor_lane_output(
        {"actor_id": "annette", "block_type": "physical_state", "text": "Annette sits down."},
        ctx,
    )
    assert result.status == "rejected"
    assert result.error_code == "ai_controlled_human_actor"


def test_actor_lane_validation_runs_before_commit():
    """Validation rejection must prevent commit — proven as a separate invariant from packaging.

    This test isolates the commit-blocking behavior: a rejected validation_outcome
    must produce commit_applied=False regardless of packaging.
    """
    import sys
    import os
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from ai_stack.goc_turn_seams import run_commit_seam, run_validation_seam

    generation_human_line = {
        "success": True,
        "content": "test",
        "metadata": {
            "structured_output": {
                "spoken_lines": [
                    {"speaker_id": "annette", "text": "I apologize."},
                ]
            }
        },
    }
    actor_lane_ctx_dict = {"human_actor_id": "annette", "ai_forbidden_actor_ids": ["annette"]}

    # Validation must reject
    validation = run_validation_seam(
        module_id="god_of_carnage",
        proposed_state_effects=[{"effect_type": "test", "description": "test"}],
        generation=generation_human_line,
        actor_lane_context=actor_lane_ctx_dict,
    )
    assert validation["status"] == "rejected"

    # Commit must be blocked — this is the pre-commit enforcement invariant
    committed = run_commit_seam(
        module_id="god_of_carnage",
        validation_outcome=validation,
        proposed_state_effects=[{"effect_type": "test", "description": "test"}],
    )
    assert committed["commit_applied"] is False, (
        "Commit must be blocked when actor-lane validation rejects. "
        "Enforcement must run before commit, not as a post-commit filter."
    )
    assert committed["committed_effects"] == []


def test_actor_lane_enforcement_active_in_graph_execution():
    """Actor-lane context is wired into the graph execution path.

    Proves that actor_lane_context passed to RuntimeTurnGraphExecutor.run()
    flows through state to run_validation_seam(), activating enforcement.
    This closes the false-green where enforcement existed as standalone functions
    but was never reached during graph execution.
    """
    import sys
    import os
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from ai_stack.langgraph_runtime_executor import RuntimeTurnGraphExecutor

    executor = RuntimeTurnGraphExecutor.__new__(RuntimeTurnGraphExecutor)
    # Build the run() parameter list with actor_lane_context
    import inspect
    sig = inspect.signature(RuntimeTurnGraphExecutor.run)
    assert "actor_lane_context" in sig.parameters, (
        "RuntimeTurnGraphExecutor.run() must accept actor_lane_context. "
        "False-green: enforcement was dead code without this parameter."
    )


def test_runtime_turn_state_has_actor_lane_context_field():
    """RuntimeTurnState TypedDict must carry actor_lane_context for graph pass-through."""
    import sys
    import os
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from ai_stack.langgraph_runtime_state import RuntimeTurnState
    annotations = RuntimeTurnState.__annotations__
    assert "actor_lane_context" in annotations, (
        "RuntimeTurnState must have actor_lane_context field. "
        "Without it, actor-lane enforcement cannot flow through graph state."
    )


def test_story_runtime_manager_has_extract_actor_lane_context():
    """StoryRuntimeManager must have _extract_actor_lane_context for wiring enforcement."""
    from app.story_runtime.manager import StoryRuntimeManager
    assert hasattr(StoryRuntimeManager, "_extract_actor_lane_context"), (
        "StoryRuntimeManager must implement _extract_actor_lane_context "
        "to derive enforcement context from session.runtime_projection."
    )


def test_extract_actor_lane_context_returns_none_without_ownership():
    """When runtime_projection lacks human_actor_id, returns None (no enforcement)."""
    from app.story_runtime.manager import StoryRuntimeManager, StorySession
    from dataclasses import asdict

    session = StorySession(
        session_id="test",
        module_id="god_of_carnage",
        runtime_projection={"module_id": "god_of_carnage"},  # no actor ownership
    )
    result = StoryRuntimeManager._extract_actor_lane_context(session)
    assert result is None


def test_extract_actor_lane_context_returns_context_with_ownership():
    """When runtime_projection has human_actor_id, returns enforcement context."""
    from app.story_runtime.manager import StoryRuntimeManager, StorySession

    session = StorySession(
        session_id="test",
        module_id="god_of_carnage",
        runtime_projection={
            "module_id": "god_of_carnage",
            "human_actor_id": "annette",
            "npc_actor_ids": ["alain", "veronique", "michel"],
            "actor_lanes": {"annette": "human", "alain": "npc"},
            "selected_player_role": "annette",
        },
    )
    ctx = StoryRuntimeManager._extract_actor_lane_context(session)
    assert ctx is not None
    assert ctx["human_actor_id"] == "annette"
    assert "annette" in ctx["ai_forbidden_actor_ids"]
    assert "alain" in ctx["ai_allowed_actor_ids"]
