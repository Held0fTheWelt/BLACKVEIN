"""OPEN-00-01: Opening block ordering contract — narrator_intro + role_anchor + scene_setup before actor_line/action."""
from __future__ import annotations

import pytest

from ai_stack.live_dramatic_scene_simulator import LDSSInput, build_deterministic_ldss_output


def _ldss_input(human: str, turn: int = 0, session_output_language: str = "en") -> LDSSInput:
    npc_ids = ["alain", "veronique", "michel"] if human == "annette" else ["annette", "veronique", "michel"]
    return LDSSInput(
        story_session_state={
            "contract": "story_session_state.v1",
            "story_session_id": f"test-open-{human}",
            "turn_number": turn,
            "current_scene_id": "phase_1",
            "content_module_id": "god_of_carnage",
            "runtime_profile_id": "god_of_carnage_solo",
            "runtime_module_id": "solo_story_runtime",
            "selected_player_role": human,
            "human_actor_id": human,
            "npc_actor_ids": npc_ids,
            "visitor_present": False,
        },
        actor_lane_context={
            "contract": "actor_lane_context.v1",
            "content_module_id": "god_of_carnage",
            "runtime_profile_id": "god_of_carnage_solo",
            "selected_player_role": human,
            "human_actor_id": human,
            "actor_lanes": {human: "human", **{n: "npc" for n in npc_ids}},
            "ai_allowed_actor_ids": sorted(npc_ids),
            "ai_forbidden_actor_ids": [human],
        },
        player_input="",
        admitted_objects=[],
        session_output_language=session_output_language,
    )


@pytest.mark.parametrize("human_role", ["annette", "alain"])
def test_opening_starts_with_three_narrator_blocks(human_role: str) -> None:
    """Turn 0 must emit narrator_intro, role_anchor, scene_setup before any actor_line/action."""
    out = build_deterministic_ldss_output(_ldss_input(human_role, turn=0))
    blocks = out.visible_scene_output.blocks
    assert len(blocks) >= 4, f"Opening needs ≥ 4 blocks (3 narrator + actor), got {len(blocks)}"
    assert blocks[0].block_type == "narrator", "Block 0 (narrator_intro) must be narrator"
    assert blocks[1].block_type == "narrator", "Block 1 (role_anchor) must be narrator"
    assert blocks[2].block_type == "narrator", "Block 2 (scene_setup) must be narrator"
    first_actor = next((b for b in blocks if b.block_type in ("actor_line", "actor_action")), None)
    assert first_actor is not None, "Opening must have at least one NPC actor block"
    actor_idx = blocks.index(first_actor)
    assert actor_idx >= 3, f"actor_line/action must not appear before block index 3, got index {actor_idx}"


@pytest.mark.parametrize("human_role", ["annette", "alain"])
def test_opening_role_anchor_is_role_specific(human_role: str) -> None:
    """Block 1 (role_anchor) must reference the player's character by name."""
    out = build_deterministic_ldss_output(_ldss_input(human_role, turn=0))
    role_anchor_text = out.visible_scene_output.blocks[1].text
    assert human_role.capitalize() in role_anchor_text, (
        f"role_anchor for {human_role!r} must mention {human_role.capitalize()!r}, "
        f"got: {role_anchor_text!r}"
    )


@pytest.mark.parametrize("human_role", ["annette", "alain"])
def test_opening_no_human_actor_in_blocks(human_role: str) -> None:
    """No block may assign actor_id to the human player."""
    out = build_deterministic_ldss_output(_ldss_input(human_role, turn=0))
    for block in out.visible_scene_output.blocks:
        assert block.actor_id != human_role, (
            f"Human actor {human_role!r} must not control any block, "
            f"but found block_type={block.block_type!r} actor_id={block.actor_id!r}"
        )


def test_regular_turn_keeps_single_narrator_structure() -> None:
    """Turn > 0 must retain the original 1-narrator + actor_line structure (not 3 narrators)."""
    out = build_deterministic_ldss_output(_ldss_input("annette", turn=1))
    blocks = out.visible_scene_output.blocks
    narrator_blocks = [b for b in blocks if b.block_type == "narrator"]
    assert len(narrator_blocks) == 1, (
        f"Regular turn must have exactly 1 narrator block, got {len(narrator_blocks)}"
    )
    assert blocks[0].block_type == "narrator", "First block of regular turn must be narrator"
    assert any(b.block_type == "actor_line" for b in blocks), "Regular turn must include an actor_line"


# ---------------------------------------------------------------------------
# STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P1: locale enforcement
# ---------------------------------------------------------------------------


def test_ldss_opening_fallback_respects_german_session_output_language() -> None:
    """P1: when session_output_language='de', the deterministic LDSS opening must produce
    German narrator text — not the English fallback that the staging audit observed."""
    out = build_deterministic_ldss_output(_ldss_input("annette", turn=0, session_output_language="de"))
    blocks = out.visible_scene_output.blocks
    narrator_texts = [b.text for b in blocks if b.block_type == "narrator"]
    assert narrator_texts, "Opening must emit narrator blocks"
    combined = " ".join(narrator_texts)
    # German runtime locale must use German orthography / common German articles.
    assert any(ch in combined for ch in "äöüÄÖÜß"), (
        f"German session must include German-specific characters; got: {combined!r}"
    )
    # And must NOT use the English summary-only template that was committed in staging.
    assert "Two couples meet in a Paris apartment" not in combined
    assert "You are Annette Reille" not in combined


def test_ldss_opening_fallback_does_not_emit_english_role_anchor_for_german_session() -> None:
    """P1: the role anchor block (block index 1) must be German for a German session and
    must include the player role name without the English 'You are <Name>' phrase."""
    out = build_deterministic_ldss_output(_ldss_input("annette", turn=0, session_output_language="de"))
    blocks = out.visible_scene_output.blocks
    assert len(blocks) >= 3, f"Need ≥ 3 narrator blocks; got {len(blocks)}"
    role_anchor_text = blocks[1].text
    assert "Du bist Annette" in role_anchor_text or "Annette Reille" in role_anchor_text
    assert "You are Annette" not in role_anchor_text


def test_ldss_opening_fallback_english_session_still_works() -> None:
    """P1: regression guard — English sessions must still receive the English opening text."""
    out = build_deterministic_ldss_output(_ldss_input("annette", turn=0, session_output_language="en"))
    blocks = out.visible_scene_output.blocks
    role_anchor_text = blocks[1].text
    assert "You are Annette" in role_anchor_text
