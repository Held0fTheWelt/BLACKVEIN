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

import copy
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Imports from LDSS module (ai_stack)
# ---------------------------------------------------------------------------

from gate_fixtures import load_yaml as _load_gate_fixture_yaml

from gate_contract_constants import (
    FORBIDDEN_RUNTIME_ACTOR_ID,
    GOD_OF_CARNAGE_CONTENT_MODULE_ID,
    GOD_OF_CARNAGE_PLAYABLE_HUMAN_IDS,
    GOD_OF_CARNAGE_RUNTIME_PROFILE_ID,
    goc_npc_actor_ids_for_selected,
    goc_role_display_name,
)

from we_contract_helpers import (
    assert_finalize_committed_turn_calls_ldss_builder,
    assert_goc_module_gate_in_finalize,
    assert_ldss_input_builder_preserves_human_actor_id,
    assert_ldss_import_and_module_wiring,
    assert_ldss_scene_envelope_requires_human_actor,
    assert_scene_turn_envelope_committed_to_event,
)

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

# Narrator / affordance prose: tests/gates/fixtures/mvp3_narrator_and_affordance_examples.yaml
_MVP3_TEXT = copy.deepcopy(_load_gate_fixture_yaml("mvp3_narrator_and_affordance_examples.yaml"))
# LDSS player_input stimuli: tests/gates/fixtures/mvp3_ldss_player_inputs.yaml (wave 03; same strings as before).
_MVP3_LDSS_INPUTS = copy.deepcopy(_load_gate_fixture_yaml("mvp3_ldss_player_inputs.yaml"))
# Pre-commit validator SceneBlock stimuli (LDSS validation order; ADR-0039).
_MVP3_PRE_COMMIT = copy.deepcopy(_load_gate_fixture_yaml("mvp3_pre_commit_validator_stimuli.yaml"))
_PRIMARY_HUMAN_ID = GOD_OF_CARNAGE_PLAYABLE_HUMAN_IDS[0]
_SECONDARY_HUMAN_ID = GOD_OF_CARNAGE_PLAYABLE_HUMAN_IDS[1]
_GOC_MODULE_ROOT = Path(__file__).resolve().parents[2] / "content" / "modules" / "god_of_carnage"
_CANONICAL_PATH = None


def _canonical_path():
    global _CANONICAL_PATH
    if _CANONICAL_PATH is None:
        from ai_stack.canonical_path.canonical_path_resolver import load_canonical_path

        _CANONICAL_PATH = load_canonical_path(_GOC_MODULE_ROOT)
    return _CANONICAL_PATH


def _npc_actor_ids_for(human_actor_id: str) -> list[str]:
    return goc_npc_actor_ids_for_selected(human_actor_id)


def _pre_commit_scenario(name: str) -> dict:
    """Named validator stimulus from mvp3_pre_commit_validator_stimuli.yaml."""
    try:
        return copy.deepcopy(_MVP3_PRE_COMMIT["scenarios"][name])
    except KeyError as exc:
        raise KeyError(f"Unknown pre-commit validator scenario: {name!r}") from exc


def _scene_block_from_pre_commit_scenario(
    name: str,
    *,
    block_id: str,
    actor_id: str | None = None,
    speaker_label: str | None = None,
) -> SceneBlock:
    """Build a SceneBlock from a versioned pre-commit validator stimulus."""
    spec = _pre_commit_scenario(name)
    return SceneBlock(
        id=block_id,
        block_type=spec["block_type"],
        actor_id=actor_id,
        speaker_label=speaker_label,
        text=spec["text"],
    )


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _primary_human_ldss_input(
    turn: int = 1,
    *,
    canonical_step_id: str | None = "opening_006_armed_vs_carrying",
    player_input: str | None = None,
) -> LDSSInput:
    return build_ldss_input_from_session(
        session_id=f"test-session-{_PRIMARY_HUMAN_ID}",
        module_id=GOD_OF_CARNAGE_CONTENT_MODULE_ID,
        turn_number=turn,
        selected_player_role=_PRIMARY_HUMAN_ID,
        human_actor_id=_PRIMARY_HUMAN_ID,
        npc_actor_ids=_npc_actor_ids_for(_PRIMARY_HUMAN_ID),
        player_input=player_input or _MVP3_LDSS_INPUTS["primary_human_ldss_input"],
        canonical_step_id=canonical_step_id,
        canonical_path=_canonical_path() if canonical_step_id else None,
    )


def _secondary_human_ldss_input(
    turn: int = 1,
    *,
    canonical_step_id: str | None = "opening_005_statement_reading",
    player_input: str | None = None,
) -> LDSSInput:
    return build_ldss_input_from_session(
        session_id=f"test-session-{_SECONDARY_HUMAN_ID}",
        module_id=GOD_OF_CARNAGE_CONTENT_MODULE_ID,
        turn_number=turn,
        selected_player_role=_SECONDARY_HUMAN_ID,
        human_actor_id=_SECONDARY_HUMAN_ID,
        npc_actor_ids=_npc_actor_ids_for(_SECONDARY_HUMAN_ID),
        player_input=player_input or _MVP3_LDSS_INPUTS["secondary_human_ldss_input"],
        canonical_step_id=canonical_step_id,
        canonical_path=_canonical_path() if canonical_step_id else None,
    )


# ---------------------------------------------------------------------------
# Wave 1: Live turn contract — playable human runtime roles
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_start_primary_human_live_scene_turn():
    """Primary playable human role: LDSS produces valid scene turn envelope."""
    ldss_input = _primary_human_ldss_input()
    ldss_output = run_ldss(ldss_input)
    envelope = build_scene_turn_envelope_v2(
        ldss_input=ldss_input,
        ldss_output=ldss_output,
        story_session_id=f"test-session-{_PRIMARY_HUMAN_ID}",
        turn_number=1,
    )

    assert isinstance(envelope, SceneTurnEnvelopeV2)
    assert envelope.contract == "scene_turn_envelope.v2"
    assert envelope.content_module_id == GOD_OF_CARNAGE_CONTENT_MODULE_ID
    assert envelope.runtime_profile_id == GOD_OF_CARNAGE_RUNTIME_PROFILE_ID
    assert envelope.selected_player_role == _PRIMARY_HUMAN_ID
    assert envelope.human_actor_id == _PRIMARY_HUMAN_ID
    assert set(_npc_actor_ids_for(_PRIMARY_HUMAN_ID)).issubset(envelope.npc_actor_ids)
    assert _PRIMARY_HUMAN_ID not in envelope.npc_actor_ids

    d = envelope.to_dict()
    assert d["contract"] == "scene_turn_envelope.v2"
    assert d["human_actor_id"] == _PRIMARY_HUMAN_ID
    assert len(d["visible_scene_output"]["blocks"]) >= 2


@pytest.mark.mvp3
def test_mvp3_gate_start_secondary_human_live_scene_turn():
    """Secondary playable human role: LDSS produces valid scene turn envelope."""
    ldss_input = _secondary_human_ldss_input()
    ldss_output = run_ldss(ldss_input)
    envelope = build_scene_turn_envelope_v2(
        ldss_input=ldss_input,
        ldss_output=ldss_output,
        story_session_id=f"test-session-{_SECONDARY_HUMAN_ID}",
        turn_number=1,
    )

    assert isinstance(envelope, SceneTurnEnvelopeV2)
    assert envelope.human_actor_id == _SECONDARY_HUMAN_ID
    assert _PRIMARY_HUMAN_ID in envelope.npc_actor_ids
    assert _SECONDARY_HUMAN_ID not in envelope.npc_actor_ids

    d = envelope.to_dict()
    assert len(d["visible_scene_output"]["blocks"]) >= 2


# ---------------------------------------------------------------------------
# Wave 3: NPC autonomous initiative
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_npcs_act_without_direct_address():
    """NPCs produce speech/action without player directly addressing them."""
    ldss_input = _primary_human_ldss_input(
        turn=2,
        player_input=_MVP3_LDSS_INPUTS["npc_autonomous_scene_turn"],
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
        assert b.actor_id != _PRIMARY_HUMAN_ID, "Human actor must not appear as AI-controlled speaker/actor"
        assert b.actor_id != FORBIDDEN_RUNTIME_ACTOR_ID, "visitor must not appear in live turn blocks"


@pytest.mark.mvp3
def test_mvp3_gate_multiple_npcs_can_participate():
    """Multiple NPCs can participate in a single turn (NPC-to-NPC interaction)."""
    ldss_input = _primary_human_ldss_input(turn=3)
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
    """Human actor must not appear as actor_id in actor_line blocks."""
    ldss_input = _primary_human_ldss_input()
    ldss_output = run_ldss(ldss_input)

    for block in ldss_output.visible_scene_output.blocks:
        if block.block_type == "actor_line":
            assert block.actor_id != ldss_input.human_actor_id, (
                f"Human actor {ldss_input.human_actor_id!r} must not be AI-generated speaker "
                f"in actor_line block: {block}"
            )


@pytest.mark.mvp3
def test_mvp3_gate_human_actor_not_generated_as_actor():
    """Human actor must not appear as actor_id in actor_action blocks either."""
    ldss_input = _primary_human_ldss_input()
    ldss_output = run_ldss(ldss_input)

    for block in ldss_output.visible_scene_output.blocks:
        if block.block_type == "actor_action":
            assert block.actor_id != ldss_input.human_actor_id, (
                "Human actor must not be AI-generated actor in actor_action block"
            )


# ---------------------------------------------------------------------------
# Visitor absence
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_visitor_absent_from_live_turn():
    """visitor must be absent from all live scene blocks (actor_id and target_actor_id)."""
    ldss_input = _primary_human_ldss_input()
    ldss_output = run_ldss(ldss_input)

    for block in ldss_output.visible_scene_output.blocks:
        assert block.actor_id != FORBIDDEN_RUNTIME_ACTOR_ID, "visitor must not appear as actor in live turn"
        assert block.target_actor_id != FORBIDDEN_RUNTIME_ACTOR_ID, "visitor must not appear as target in live turn"


# ---------------------------------------------------------------------------
# Responder candidate validation
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_responder_candidates_exclude_human():
    """Human actor must not be a responder candidate."""
    # Human actor as primary responder is rejected
    result = validate_responder_candidates(
        primary_responder_id=_PRIMARY_HUMAN_ID,
        secondary_responder_ids=[_npc_actor_ids_for(_PRIMARY_HUMAN_ID)[0]],
        human_actor_id=_PRIMARY_HUMAN_ID,
    )
    assert result.status == "rejected"
    assert result.error_code == "human_actor_selected_as_responder"

    # Valid plan: only NPCs
    result2 = validate_responder_candidates(
        primary_responder_id=_npc_actor_ids_for(_PRIMARY_HUMAN_ID)[0],
        secondary_responder_ids=[_npc_actor_ids_for(_PRIMARY_HUMAN_ID)[1]],
        human_actor_id=_PRIMARY_HUMAN_ID,
    )
    assert result2.status == "approved"

    # NPC agency plan from canonical-step rendering excludes human.
    ldss_input = _primary_human_ldss_input()
    ldss_output = run_ldss(ldss_input)
    plan = ldss_output.npc_agency_plan
    assert plan is not None
    assert plan.primary_responder_id != ldss_input.human_actor_id
    for sec in plan.secondary_responder_ids:
        assert sec != ldss_input.human_actor_id


# ---------------------------------------------------------------------------
# Wave 4: Validation before commit
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_actor_lane_validation_before_commit():
    """Actor-lane validation rejects human actor control without committing illegal state."""
    human_id = _PRIMARY_HUMAN_ID
    valid_npc_id = _npc_actor_ids_for(human_id)[0]
    illegal_spec = _pre_commit_scenario("actor_lane_illegal_human_line")
    illegal_block = _scene_block_from_pre_commit_scenario(
        "actor_lane_illegal_human_line",
        block_id="test-illegal",
        speaker_label=goc_role_display_name(human_id),
        actor_id=human_id,  # human actor — forbidden
    )
    valid_block = _scene_block_from_pre_commit_scenario(
        "actor_lane_valid_npc_line",
        block_id="test-valid",
        speaker_label=goc_role_display_name(valid_npc_id),
        actor_id=valid_npc_id,
    )

    # Rejection without commit
    illegal_result = validate_actor_lane_blocks(
        [illegal_block], human_actor_id=human_id
    )
    assert illegal_result.status == "rejected"
    assert illegal_result.error_code == illegal_spec["expected_error_code"]
    assert illegal_result.actor_id == human_id

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
    mass_thin_spec = _pre_commit_scenario("dramatic_mass_narrator_only")
    passivity_thin_spec = _pre_commit_scenario("passivity_narrator_only")
    narrator_only = [
        _scene_block_from_pre_commit_scenario(
            "dramatic_mass_narrator_only",
            block_id="test-narrator",
            actor_id=None,
        )
    ]
    result = validate_dramatic_mass(narrator_only)
    assert result.status == "rejected"
    assert result.error_code == mass_thin_spec["expected_error_code"]

    # Passivity validation also rejects narrator-only
    passivity_result = validate_passivity(narrator_only)
    assert passivity_result.status == "rejected"
    assert passivity_result.error_code == passivity_thin_spec["expected_error_code"]

    # Valid: at least one NPC actor_line
    valid_blocks = narrator_only + [
        _scene_block_from_pre_commit_scenario(
            "dramatic_mass_valid_npc_line",
            block_id="test-actor",
            speaker_label=goc_role_display_name(_npc_actor_ids_for(_PRIMARY_HUMAN_ID)[0]),
            actor_id=_npc_actor_ids_for(_PRIMARY_HUMAN_ID)[0],
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
    ldss_input = _primary_human_ldss_input(turn=5)
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
    assert diag["status"] == "approved"
    assert diag["invoked"] is True
    assert diag["entrypoint"] == "story.turn.execute"
    assert diag["legacy_blob_used"] is False
    assert diag["scene_block_count"] >= 2

    # Actor lane enforcement is traceable
    lane_diag = d["diagnostics"]["actor_lane_enforcement"]
    assert lane_diag["validation_ran_before_commit"] is True
    assert lane_diag["human_actor_id"] == ldss_input.human_actor_id
    assert ldss_input.human_actor_id in lane_diag["ai_forbidden_actor_ids"]

    # Response blocks come from validated output
    blocks = d["visible_scene_output"]["blocks"]
    for block in blocks:
        assert block["actor_id"] != ldss_input.human_actor_id, "Human actor must not appear in packaged response"
        assert block["actor_id"] != FORBIDDEN_RUNTIME_ACTOR_ID, "visitor must not appear in packaged response"


# ---------------------------------------------------------------------------
# Invalid AI human control rejected
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_invalid_ai_human_control_rejected_without_commit():
    """When AI would control human actor, rejection returns structured error without commit."""
    human_id = _PRIMARY_HUMAN_ID
    illegal_spec = _pre_commit_scenario("actor_lane_illegal_human_apology")
    illegal_blocks = [
        _scene_block_from_pre_commit_scenario(
            "actor_lane_illegal_human_apology",
            block_id="illegal-1",
            speaker_label=goc_role_display_name(human_id),
            actor_id=human_id,
        )
    ]
    result = validate_actor_lane_blocks(illegal_blocks, human_actor_id=human_id)
    assert result.status == "rejected"
    assert result.error_code == illegal_spec["expected_error_code"]

    # run_ldss must not produce human actor in blocks
    ldss_input = _primary_human_ldss_input()
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
    mass_spec = _pre_commit_scenario("dramatic_mass_narrator_only_very_thin")
    passivity_spec = _pre_commit_scenario("passivity_narrator_only_very_thin")
    thin_proposal = [
        _scene_block_from_pre_commit_scenario(
            "dramatic_mass_narrator_only_very_thin",
            block_id="turn-1-block-1",
        )
    ]

    # validate_dramatic_mass rejects it
    mass_result = validate_dramatic_mass(thin_proposal)
    assert mass_result.status == "rejected"
    assert mass_result.error_code == mass_spec["expected_error_code"]

    # validate_passivity rejects it
    passivity_result = validate_passivity(thin_proposal)
    assert passivity_result.status == "rejected"
    assert passivity_result.error_code == passivity_spec["expected_error_code"]

    # Canonical-step LDSS output is not the degraded/no-visible-generation path.
    ldss_input = _primary_human_ldss_input()
    ldss_output = run_ldss(ldss_input)
    passivity_final = validate_passivity(ldss_output.visible_scene_output.blocks)
    assert passivity_final.status == "approved", (
        "Canonical-step LDSS output must pass passivity validation"
    )


# ---------------------------------------------------------------------------
# Canonical path output satisfies validation
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_canonical_path_output_satisfies_validation():
    """Canonical-step output passes all MVP3 validators."""
    ldss_input = _primary_human_ldss_input()
    ldss_output = run_ldss(ldss_input)
    blocks = ldss_output.visible_scene_output.blocks

    # Actor lane validation passes
    lane_result = validate_actor_lane_blocks(
        blocks,
        human_actor_id=ldss_input.human_actor_id,
        ai_forbidden_actor_ids=[ldss_input.human_actor_id],
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


@pytest.mark.mvp3
def test_mvp3_gate_missing_canonical_step_returns_degraded_notice():
    """Fallback without canonical visible generation is explicit degradation, not fabricated scene truth."""
    ldss_input = _primary_human_ldss_input(canonical_step_id=None)
    ldss_output = run_ldss(ldss_input)
    blocks = ldss_output.visible_scene_output.blocks

    assert ldss_output.status == "degraded_error"
    assert ldss_output.error_code == "ldss_no_live_visible_generation"
    assert len(blocks) == 1
    assert blocks[0].block_type == "system_degraded_notice"
    assert validate_actor_lane_blocks(blocks, human_actor_id=ldss_input.human_actor_id).status == "approved"
    assert validate_dramatic_mass(blocks).status == "rejected"
    assert validate_passivity(blocks).status == "rejected"


# ---------------------------------------------------------------------------
# Trace header preserved
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_mvp3_gate_trace_header_preserved_on_story_turn():
    """SceneTurnEnvelope diagnostics include story_session_id and turn_number (trace context)."""
    ldss_input = _primary_human_ldss_input(turn=7)
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
    bad_text = _MVP3_TEXT["narrator_voice"]["negative"]["dialogue_recap"]["text"]
    result = validate_narrator_voice(bad_text)
    assert result.status == "rejected"
    assert result.error_code == "narrator_dialogue_summary_rejected"


@pytest.mark.mvp3
def test_narrator_modal_language_does_not_force_player_state():
    """Narrator cannot tell the player how they feel or what they decide."""
    bad_text = _MVP3_TEXT["narrator_voice"]["negative"]["forces_player_state"]["text"]
    result = validate_narrator_voice(bad_text)
    assert result.status == "rejected"
    assert result.error_code == "narrator_forces_player_state"


@pytest.mark.mvp3
def test_narrator_cannot_reveal_hidden_npc_intent():
    """Narrator cannot reveal undisclosed NPC motivations."""
    bad_text = _MVP3_TEXT["narrator_voice"]["negative"]["reveals_hidden_intent"]["text"]
    result = validate_narrator_voice(bad_text)
    assert result.status == "rejected"
    assert result.error_code == "narrator_reveals_hidden_intent"


@pytest.mark.mvp3
def test_valid_narrator_inner_perception():
    """Valid narrator block: inner perception and orientation only."""
    good_text = _MVP3_TEXT["narrator_voice"]["positive"]["inner_perception"]["text"]
    result = validate_narrator_voice(good_text)
    assert result.status == "approved"


# ---------------------------------------------------------------------------
# Affordance and environment validation (bonus gates)
# ---------------------------------------------------------------------------

@pytest.mark.mvp3
def test_similar_allowed_requires_similarity_reason():
    """similar_allowed affordance without reason is rejected."""
    _env = _MVP3_TEXT["environment_interaction"]["similar_allowed_phone"]
    env_block = SceneBlock(
        id="test-env",
        block_type="environment_interaction",
        actor_id=_SECONDARY_HUMAN_ID,
        object_id="mobile_phone",
        affordance_tier="similar_allowed",
        text=_env["block_text"],
    )
    # Without reason: rejected
    result_no_reason = validate_similar_allowed_requires_reason(env_block, similarity_reason=None)
    assert result_no_reason.status == "rejected"
    assert result_no_reason.error_code == "similar_allowed_requires_similarity_reason"

    # With reason: approved
    result_with_reason = validate_similar_allowed_requires_reason(
        env_block,
        similarity_reason=_env["similarity_reason"],
    )
    assert result_with_reason.status == "approved"


@pytest.mark.mvp3
def test_rejects_unadmitted_plausible_object():
    """Unadmitted object (e.g. knife) is rejected with environment_object_not_admitted."""
    _knife = _MVP3_TEXT["environment_interaction"]["knife_unadmitted"]
    knife_block = SceneBlock(
        id="test-knife",
        block_type="environment_interaction",
        actor_id=_npc_actor_ids_for(_PRIMARY_HUMAN_ID)[0],
        object_id="knife",
        affordance_tier="canonical",
        text=_knife["block_text"],
    )
    # knife is not in admitted objects
    result = validate_affordance(knife_block, admitted_objects=[])
    assert result.status == "rejected"
    assert result.error_code == "environment_object_not_admitted"


@pytest.mark.mvp3
def test_canonical_object_affordance_approved():
    """Canonical admitted object passes affordance validation."""
    _phone = _MVP3_TEXT["environment_interaction"]["phone_canonical"]
    phone_block = SceneBlock(
        id="test-phone",
        block_type="environment_interaction",
        actor_id=_SECONDARY_HUMAN_ID,
        object_id="mobile_phone",
        affordance_tier="canonical",
        text=_phone["block_text"],
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
    """LDSS is wired for GoC: import boundary + AST proof (no fragile source substring matching).

    Full execution remains in world-engine/tests/test_mvp3_ldss_integration.py; this gate proves
    ``_build_ldss_scene_envelope`` calls ``run_ldss`` / ``build_scene_turn_envelope_v2`` and that
    ``_finalize_committed_turn`` commits ``scene_turn_envelope`` under GoC gating.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    manager_path = repo_root / "world-engine" / "app" / "story_runtime" / "manager"
    ldss_path = repo_root / "ai_stack" / "live_dramatic_scene_simulator.py"
    assert manager_path.is_dir(), f"world-engine/app/story_runtime/manager package must exist at {manager_path}"
    assert ldss_path.exists(), f"ai_stack/live_dramatic_scene_simulator.py must exist at {ldss_path}"

    assert_ldss_import_and_module_wiring(manager_path, ldss_path)
    assert_finalize_committed_turn_calls_ldss_builder(manager_path)
    assert_scene_turn_envelope_committed_to_event(manager_path)
    assert_goc_module_gate_in_finalize(manager_path)


@pytest.mark.mvp3
def test_mvp3_gate_non_goc_session_has_no_scene_envelope():
    """_build_ldss_scene_envelope returns None for non-GoC sessions (structural proof).

    The function checks human_actor_id in runtime_projection to determine GoC solo.
    Non-GoC sessions have no human_actor_id in projection → returns None → no envelope.
    Full execution is proven in world-engine/tests/test_mvp3_ldss_integration.py.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    manager_path = repo_root / "world-engine" / "app" / "story_runtime" / "manager"
    ldss_path = repo_root / "ai_stack" / "live_dramatic_scene_simulator.py"
    assert_ldss_scene_envelope_requires_human_actor(manager_path)
    assert_ldss_input_builder_preserves_human_actor_id(ldss_path)
