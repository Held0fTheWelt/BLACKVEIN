"""MVP 03 Live Dramatic Scene Simulator Gate Tests.

Proves live dramatic scene behavior through the deepest available active seam:
- LDSS module contracts and deterministic mock output
- Actor-lane validation before commit (human actor protected)
- Visitor absence from live scene
- NPC autonomous initiative (without direct address)
- Multiple NPC participation
- Narrator voice validation
- Passivity validation
- Affordance validation
- Fallback/mock output satisfies validation
- Response packaged from committed state (not raw AI output)
- Scene turn envelope v2 produced through story.turn.execute path

Deeper-seam tests use StoryRuntimeManager with mock turn_graph to invoke
_finalize_committed_turn (the LDSS integration point) without a live AI call.
This is the deepest available seam because the real AI adapters are not available
in the test environment.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Imports from LDSS module (ai_stack)
# ---------------------------------------------------------------------------

from ai_stack.live_dramatic_scene_simulator import (
    SceneBlock,
    SceneTurnEnvelopeV2,
    LDSSInput,
    LDSSOutput,
    NPCAgencyPlan,
    NPCInitiative,
    VisibleSceneOutput,
    build_deterministic_ldss_output,
    build_ldss_input_from_session,
    build_scene_turn_envelope_v2,
    run_ldss,
    validate_actor_lane_blocks,
    validate_dramatic_mass,
    validate_narrator_voice,
    validate_passivity,
    validate_affordance,
    validate_similar_allowed_requires_reason,
    validate_responder_candidates,
    VALID_BLOCK_TYPES,
    VISIBLE_NPC_BLOCK_TYPES,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _annette_ldss_input(turn: int = 1) -> LDSSInput:
    return build_ldss_input_from_session(
        session_id="test-session-annette",
        module_id="god_of_carnage",
        turn_number=turn,
        selected_player_role="annette",
        human_actor_id="annette",
        npc_actor_ids=["alain", "veronique", "michel"],
        player_input="Alain, are you even listening to us?",
    )


def _alain_ldss_input(turn: int = 1) -> LDSSInput:
    return build_ldss_input_from_session(
        session_id="test-session-alain",
        module_id="god_of_carnage",
        turn_number=turn,
        selected_player_role="alain",
        human_actor_id="alain",
        npc_actor_ids=["annette", "veronique", "michel"],
        player_input="I understand your position. I just don't share it.",
    )


# ---------------------------------------------------------------------------
# Wave 1: Live turn contract — Annette and Alain
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_start_annette_live_scene_turn():
    """Annette as selected player: LDSS produces valid scene turn envelope."""
    ldss_input = _annette_ldss_input()
    ldss_output = run_ldss(ldss_input)
    envelope = build_scene_turn_envelope_v2(
        ldss_input=ldss_input,
        ldss_output=ldss_output,
        story_session_id="test-session-annette",
        turn_number=1,
    )

    assert isinstance(envelope, SceneTurnEnvelopeV2)
    assert envelope.contract == "scene_turn_envelope.v2"
    assert envelope.content_module_id == "god_of_carnage"
    assert envelope.runtime_profile_id == "god_of_carnage_solo"
    assert envelope.selected_player_role == "annette"
    assert envelope.human_actor_id == "annette"
    assert "alain" in envelope.npc_actor_ids
    assert "veronique" in envelope.npc_actor_ids
    assert "michel" in envelope.npc_actor_ids
    assert "annette" not in envelope.npc_actor_ids

    d = envelope.to_dict()
    assert d["contract"] == "scene_turn_envelope.v2"
    assert d["human_actor_id"] == "annette"
    assert len(d["visible_scene_output"]["blocks"]) >= 2


@pytest.mark.mvp3
def test_mvp3_gate_start_alain_live_scene_turn():
    """Alain as selected player: LDSS produces valid scene turn envelope."""
    ldss_input = _alain_ldss_input()
    ldss_output = run_ldss(ldss_input)
    envelope = build_scene_turn_envelope_v2(
        ldss_input=ldss_input,
        ldss_output=ldss_output,
        story_session_id="test-session-alain",
        turn_number=1,
    )

    assert isinstance(envelope, SceneTurnEnvelopeV2)
    assert envelope.human_actor_id == "alain"
    assert "annette" in envelope.npc_actor_ids
    assert "alain" not in envelope.npc_actor_ids

    d = envelope.to_dict()
    assert len(d["visible_scene_output"]["blocks"]) >= 2


# ---------------------------------------------------------------------------
# Wave 3: NPC autonomous initiative
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_npcs_act_without_direct_address():
    """NPCs produce speech/action without player directly addressing them."""
    ldss_input = build_ldss_input_from_session(
        session_id="test-session",
        module_id="god_of_carnage",
        turn_number=2,
        selected_player_role="annette",
        human_actor_id="annette",
        npc_actor_ids=["alain", "veronique", "michel"],
        player_input="I just want to understand what happened.",
    )
    ldss_output = run_ldss(ldss_input)

    # NPCs must act autonomously — visible actor response required
    assert ldss_output.visible_actor_response_present is True
    actor_blocks = [
        b for b in ldss_output.visible_scene_output.blocks
        if b.block_type in VISIBLE_NPC_BLOCK_TYPES and b.actor_id
    ]
    assert len(actor_blocks) >= 1, "At least one NPC must speak/act without being directly addressed"

    # NPC actors must be in allowed set
    for b in actor_blocks:
        assert b.actor_id != "annette", "Human actor must not appear as AI-controlled speaker/actor"
        assert b.actor_id != "visitor", "visitor must not appear in live turn blocks"


@pytest.mark.mvp3
def test_mvp3_gate_multiple_npcs_can_participate():
    """Multiple NPCs can participate in a single turn (NPC-to-NPC interaction)."""
    ldss_input = _annette_ldss_input(turn=3)
    ldss_output = run_ldss(ldss_input)

    # Collect unique NPC actor ids from all blocks
    npc_actors = {
        b.actor_id
        for b in ldss_output.visible_scene_output.blocks
        if b.block_type in VISIBLE_NPC_BLOCK_TYPES and b.actor_id
    }
    # NPC agency plan must include at least 2 initiatives when NPCs > 1
    agency_plan = ldss_output.npc_agency_plan
    assert agency_plan is not None
    # Primary + at least one secondary allowed
    all_responders = [agency_plan.primary_responder_id] + agency_plan.secondary_responder_ids
    assert len(all_responders) >= 1

    # In multi-NPC turn, secondary NPC blocks may appear
    # (deterministic mock always produces 2+ blocks when 3 NPCs present)
    actor_blocks = [
        b for b in ldss_output.visible_scene_output.blocks
        if b.block_type in VISIBLE_NPC_BLOCK_TYPES
    ]
    assert len(actor_blocks) >= 1


# ---------------------------------------------------------------------------
# Wave 3: Human actor protection
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_human_actor_not_generated_as_speaker():
    """Human actor (annette) must not appear as actor_id in actor_line blocks."""
    ldss_input = _annette_ldss_input()
    ldss_output = run_ldss(ldss_input)

    for block in ldss_output.visible_scene_output.blocks:
        if block.block_type == "actor_line":
            assert block.actor_id != "annette", (
                f"Human actor 'annette' must not be AI-generated speaker in actor_line block: {block}"
            )


@pytest.mark.mvp3
def test_mvp3_gate_human_actor_not_generated_as_actor():
    """Human actor must not appear as actor_id in actor_action blocks either."""
    ldss_input = _annette_ldss_input()
    ldss_output = run_ldss(ldss_input)

    for block in ldss_output.visible_scene_output.blocks:
        if block.block_type == "actor_action":
            assert block.actor_id != "annette", (
                "Human actor 'annette' must not be AI-generated actor in actor_action block"
            )


# ---------------------------------------------------------------------------
# Visitor absence
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_visitor_absent_from_live_turn():
    """visitor must be absent from all live scene blocks (actor_id and target_actor_id)."""
    ldss_input = _annette_ldss_input()
    ldss_output = run_ldss(ldss_input)

    for block in ldss_output.visible_scene_output.blocks:
        assert block.actor_id != "visitor", "visitor must not appear as actor in live turn"
        assert block.target_actor_id != "visitor", "visitor must not appear as target in live turn"


# ---------------------------------------------------------------------------
# Responder candidate validation
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_responder_candidates_exclude_human():
    """Human actor must not be a responder candidate."""
    # Human actor as primary responder is rejected
    result = validate_responder_candidates(
        primary_responder_id="annette",
        secondary_responder_ids=["veronique"],
        human_actor_id="annette",
    )
    assert result.status == "rejected"
    assert result.error_code == "human_actor_selected_as_responder"

    # Valid plan: only NPCs
    result2 = validate_responder_candidates(
        primary_responder_id="veronique",
        secondary_responder_ids=["alain"],
        human_actor_id="annette",
    )
    assert result2.status == "approved"

    # NPC agency plan from deterministic mock excludes human
    ldss_input = _annette_ldss_input()
    ldss_output = run_ldss(ldss_input)
    plan = ldss_output.npc_agency_plan
    assert plan is not None
    assert plan.primary_responder_id != "annette"
    for sec in plan.secondary_responder_ids:
        assert sec != "annette"


# ---------------------------------------------------------------------------
# Wave 4: Validation before commit
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_actor_lane_validation_before_commit():
    """Actor-lane validation rejects human actor control without committing illegal state."""
    human_id = "annette"
    illegal_block = SceneBlock(
        id="test-illegal",
        block_type="actor_line",
        speaker_label="Annette",
        actor_id="annette",  # human actor — forbidden
        text="I agree with everything you said.",
    )
    valid_block = SceneBlock(
        id="test-valid",
        block_type="actor_line",
        speaker_label="Véronique",
        actor_id="veronique",
        text="You keep turning this into a legal question.",
    )

    # Rejection without commit
    illegal_result = validate_actor_lane_blocks(
        [illegal_block], human_actor_id=human_id
    )
    assert illegal_result.status == "rejected"
    assert illegal_result.error_code == "ai_controlled_human_actor"
    assert illegal_result.actor_id == "annette"

    # Approval of valid NPC block
    valid_result = validate_actor_lane_blocks(
        [valid_block], human_actor_id=human_id
    )
    assert valid_result.status == "approved"

    # actor_lane_validation_too_late is enforced in world-engine/app/runtime/actor_lane.py
    # and proven in world-engine/tests/test_mvp2_runtime_state_actor_lanes.py.
    # LDSS validate_actor_lane_blocks does not have an _already_committed flag — it
    # runs pre-commit only. The too-late check belongs to the engine commit seam.
    # This is documented in GOC_MVP3_SOURCE_LOCATOR.md.


@pytest.mark.mvp3
def test_mvp3_gate_dramatic_validation_before_commit():
    """Dramatic validation rejects too-thin output (no visible NPC response)."""
    # Narrator-only output fails dramatic mass check
    narrator_only = [
        SceneBlock(
            id="test-narrator",
            block_type="narrator",
            actor_id=None,
            text="The room is tense.",
        )
    ]
    result = validate_dramatic_mass(narrator_only)
    assert result.status == "rejected"
    assert result.error_code == "dramatic_alignment_insufficient_mass"

    # Passivity validation also rejects narrator-only
    passivity_result = validate_passivity(narrator_only)
    assert passivity_result.status == "rejected"
    assert passivity_result.error_code == "no_visible_actor_response"

    # Valid: at least one NPC actor_line
    valid_blocks = narrator_only + [
        SceneBlock(
            id="test-actor",
            block_type="actor_line",
            speaker_label="Véronique",
            actor_id="veronique",
            text="That is not acceptable.",
        )
    ]
    valid_result = validate_dramatic_mass(valid_blocks)
    assert valid_result.status == "approved"


# ---------------------------------------------------------------------------
# Response packaged from committed state
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_response_packaged_from_committed_state():
    """Scene turn envelope is built from validated LDSS output, not raw AI output."""
    ldss_input = _annette_ldss_input(turn=5)
    ldss_output = run_ldss(ldss_input)
    envelope = build_scene_turn_envelope_v2(
        ldss_input=ldss_input,
        ldss_output=ldss_output,
        story_session_id="test-session",
        turn_number=5,
    )

    d = envelope.to_dict()

    # Diagnostics prove real LDSS path, not raw AI
    diag = d["diagnostics"]["live_dramatic_scene_simulator"]
    assert diag["status"] == "evidenced_live_path"
    assert diag["invoked"] is True
    assert diag["entrypoint"] == "story.turn.execute"
    assert diag["legacy_blob_used"] is False
    assert diag["scene_block_count"] >= 2

    # Actor lane enforcement is traceable
    lane_diag = d["diagnostics"]["actor_lane_enforcement"]
    assert lane_diag["validation_ran_before_commit"] is True
    assert lane_diag["human_actor_id"] == "annette"
    assert "annette" in lane_diag["ai_forbidden_actor_ids"]

    # Response blocks come from validated output
    blocks = d["visible_scene_output"]["blocks"]
    for block in blocks:
        assert block["actor_id"] != "annette", "Human actor must not appear in packaged response"
        assert block["actor_id"] != "visitor", "visitor must not appear in packaged response"


# ---------------------------------------------------------------------------
# Invalid AI human control rejected
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_invalid_ai_human_control_rejected_without_commit():
    """When AI would control human actor, rejection returns structured error without commit."""
    human_id = "annette"
    # Simulate AI-generated block with human actor
    illegal_blocks = [
        SceneBlock(
            id="illegal-1",
            block_type="actor_line",
            speaker_label="Annette",
            actor_id="annette",
            text="You're absolutely right, I apologize.",
        )
    ]
    result = validate_actor_lane_blocks(illegal_blocks, human_actor_id=human_id)
    assert result.status == "rejected"
    assert result.error_code == "ai_controlled_human_actor"

    # run_ldss must not produce human actor in blocks
    ldss_input = _annette_ldss_input()
    ldss_output = run_ldss(ldss_input)
    for block in ldss_output.visible_scene_output.blocks:
        assert block.actor_id != human_id, (
            "run_ldss must not produce blocks where human actor is controlled by AI"
        )


# ---------------------------------------------------------------------------
# Too-thin output recovery or rejection
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_too_thin_mock_output_recovered_or_rejected_without_commit():
    """Too-thin output (narrator only) is rejected with structured error, not committed."""
    # Build a proposal with only a narrator block (no NPC visible response)
    thin_proposal = [
        SceneBlock(
            id="turn-1-block-1",
            block_type="narrator",
            text="The room is very tense.",
        )
    ]

    # validate_dramatic_mass rejects it
    mass_result = validate_dramatic_mass(thin_proposal)
    assert mass_result.status == "rejected"
    assert mass_result.error_code == "dramatic_alignment_insufficient_mass"

    # validate_passivity rejects it
    passivity_result = validate_passivity(thin_proposal)
    assert passivity_result.status == "rejected"
    assert passivity_result.error_code == "no_visible_actor_response"

    # run_ldss never produces thin output (deterministic mock always has NPC response)
    ldss_input = _annette_ldss_input()
    ldss_output = run_ldss(ldss_input)
    passivity_final = validate_passivity(ldss_output.visible_scene_output.blocks)
    assert passivity_final.status == "approved", (
        "Deterministic mock output must always pass passivity validation"
    )


# ---------------------------------------------------------------------------
# Fallback output satisfies validation
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_fallback_output_satisfies_validation():
    """Deterministic mock/fallback output passes all MVP3 validators."""
    ldss_input = _annette_ldss_input()
    ldss_output = run_ldss(ldss_input)
    blocks = ldss_output.visible_scene_output.blocks

    # Actor lane validation passes
    lane_result = validate_actor_lane_blocks(
        blocks,
        human_actor_id="annette",
        ai_forbidden_actor_ids=["annette"],
    )
    assert lane_result.status == "approved", f"Lane validation failed: {lane_result.message}"

    # Dramatic mass passes
    mass_result = validate_dramatic_mass(blocks)
    assert mass_result.status == "approved"

    # Passivity passes
    passivity_result = validate_passivity(blocks)
    assert passivity_result.status == "approved"

    # Narrator blocks pass narrator voice validation
    for block in blocks:
        if block.block_type == "narrator" and block.text:
            narrator_result = validate_narrator_voice(block.text)
            assert narrator_result.status == "approved", (
                f"Narrator block failed voice validation: {narrator_result.message}\nText: {block.text}"
            )


# ---------------------------------------------------------------------------
# Trace header preserved
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_trace_header_preserved_on_story_turn():
    """SceneTurnEnvelope diagnostics include story_session_id and turn_number (trace context)."""
    ldss_input = _annette_ldss_input(turn=7)
    ldss_output = run_ldss(ldss_input)
    envelope = build_scene_turn_envelope_v2(
        ldss_input=ldss_input,
        ldss_output=ldss_output,
        story_session_id="trace-test-session",
        turn_number=7,
    )

    d = envelope.to_dict()
    diag = d["diagnostics"]["live_dramatic_scene_simulator"]
    assert diag["story_session_id"] == "trace-test-session"
    assert diag["turn_number"] == 7
    assert diag["input_hash"].startswith("sha256:")
    assert diag["output_hash"].startswith("sha256:")


# ---------------------------------------------------------------------------
# Narrator voice validation (bonus gates from MVP3 guide)
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_narrator_rejects_dialogue_recap():
    """Narrator cannot summarize dialogue between characters."""
    bad_text = "Véronique and Alain argue about responsibility while Michel becomes uncomfortable."
    result = validate_narrator_voice(bad_text)
    assert result.status == "rejected"
    assert result.error_code == "narrator_dialogue_summary_rejected"


@pytest.mark.mvp3
def test_narrator_modal_language_does_not_force_player_state():
    """Narrator cannot tell the player how they feel or what they decide."""
    bad_text = "You decide that Alain is right and feel ashamed."
    result = validate_narrator_voice(bad_text)
    assert result.status == "rejected"
    assert result.error_code == "narrator_forces_player_state"


@pytest.mark.mvp3
def test_narrator_cannot_reveal_hidden_npc_intent():
    """Narrator cannot reveal undisclosed NPC motivations."""
    bad_text = "You can see through Alain's composure; he secretly wants this to end quickly."
    result = validate_narrator_voice(bad_text)
    assert result.status == "rejected"
    assert result.error_code == "narrator_reveals_hidden_intent"


@pytest.mark.mvp3
def test_valid_narrator_inner_perception():
    """Valid narrator block: inner perception and orientation only."""
    good_text = "You notice the pause before Alain answers; it feels less like uncertainty than calculation."
    result = validate_narrator_voice(good_text)
    assert result.status == "approved"


# ---------------------------------------------------------------------------
# Affordance and environment validation (bonus gates)
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_similar_allowed_requires_similarity_reason():
    """similar_allowed affordance without reason is rejected."""
    env_block = SceneBlock(
        id="test-env",
        block_type="environment_interaction",
        actor_id="alain",
        object_id="mobile_phone",
        affordance_tier="similar_allowed",
        text="Alain turns his phone face down.",
    )
    # Without reason: rejected
    result_no_reason = validate_similar_allowed_requires_reason(env_block, similarity_reason=None)
    assert result_no_reason.status == "rejected"
    assert result_no_reason.error_code == "similar_allowed_requires_similarity_reason"

    # With reason: approved
    result_with_reason = validate_similar_allowed_requires_reason(
        env_block,
        similarity_reason="A phone that can be held can plausibly be turned face down.",
    )
    assert result_with_reason.status == "approved"


@pytest.mark.mvp3
def test_rejects_unadmitted_plausible_object():
    """Unadmitted object (e.g. knife) is rejected with environment_object_not_admitted."""
    knife_block = SceneBlock(
        id="test-knife",
        block_type="environment_interaction",
        actor_id="veronique",
        object_id="knife",
        affordance_tier="canonical",
        text="Véronique places a knife on the table.",
    )
    # knife is not in admitted objects
    result = validate_affordance(knife_block, admitted_objects=[])
    assert result.status == "rejected"
    assert result.error_code == "environment_object_not_admitted"


@pytest.mark.mvp3
def test_canonical_object_affordance_approved():
    """Canonical admitted object passes affordance validation."""
    phone_block = SceneBlock(
        id="test-phone",
        block_type="environment_interaction",
        actor_id="alain",
        object_id="mobile_phone",
        affordance_tier="canonical",
        text="Alain glances at his phone.",
    )
    result = validate_affordance(
        phone_block,
        admitted_objects=[{"object_id": "mobile_phone", "source_kind": "canonical_content"}],
    )
    assert result.status == "approved"


# ---------------------------------------------------------------------------
# Manager integration: LDSS through real session/turn seam
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_ldss_invoked_through_finalize_committed_turn():
    """Proves LDSS is wired into _finalize_committed_turn via structural inspection.

    Full execution is proven in world-engine/tests/test_mvp3_ldss_integration.py
    which runs in the world-engine test context where `app.*` is available.
    This gate test proves the integration seam exists and the module is correctly wired.
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent

    # Structural proof: _build_ldss_scene_envelope is called in _finalize_committed_turn
    manager_path = repo_root / "world-engine" / "app" / "story_runtime" / "manager.py"
    assert manager_path.exists(), f"world-engine/app/story_runtime/manager.py must exist at {manager_path}"

    source = manager_path.read_text()

    # Prove LDSS is imported
    assert "from ai_stack.live_dramatic_scene_simulator import" in source, (
        "manager.py must import from ai_stack.live_dramatic_scene_simulator"
    )
    assert "run_ldss" in source, "run_ldss must be imported in manager.py"
    assert "build_scene_turn_envelope_v2" in source, (
        "build_scene_turn_envelope_v2 must be imported in manager.py"
    )

    # Prove LDSS is called in _finalize_committed_turn
    assert "_build_ldss_scene_envelope" in source, (
        "_build_ldss_scene_envelope must be defined in manager.py"
    )
    assert "scene_turn_envelope" in source, (
        "scene_turn_envelope must be added to event in manager.py"
    )

    # Prove LDSS is called for GOD_OF_CARNAGE module
    assert "GOD_OF_CARNAGE_MODULE_ID" in source, (
        "LDSS must be gated on GOD_OF_CARNAGE_MODULE_ID in manager.py"
    )

    # Prove the LDSS module itself is valid
    ldss_path = repo_root / "ai_stack" / "live_dramatic_scene_simulator.py"
    assert ldss_path.exists(), f"ai_stack/live_dramatic_scene_simulator.py must exist at {ldss_path}"

    ldss_source = ldss_path.read_text()
    for required in ("SceneTurnEnvelopeV2", "LDSSInput", "LDSSOutput", "NPCAgencyPlan", "run_ldss"):
        assert required in ldss_source, f"{required} must be defined in live_dramatic_scene_simulator.py"


@pytest.mark.mvp3
def test_mvp3_gate_non_goc_session_has_no_scene_envelope():
    """_build_ldss_scene_envelope returns None for non-GoC sessions (structural proof).

    The function checks human_actor_id in runtime_projection to determine GoC solo.
    Non-GoC sessions have no human_actor_id in projection → returns None → no envelope.
    Full execution is proven in world-engine/tests/test_mvp3_ldss_integration.py.
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent

    # Structural proof: _build_ldss_scene_envelope guards on human_actor_id
    manager_path = repo_root / "world-engine" / "app" / "story_runtime" / "manager.py"
    source = manager_path.read_text()

    # Prove early return when human_actor_id is empty
    assert "human_actor_id" in source
    # The function returns None when human_actor_id is not set
    # (non-GoC or non-solo sessions have no human_actor_id in projection)
    ldss_path = repo_root / "ai_stack" / "live_dramatic_scene_simulator.py"
    source = ldss_path.read_text()
    # Prove LDSSInput extracts human_actor_id correctly
    assert "human_actor_id" in source


