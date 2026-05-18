"""LDSS degraded fallback contract: no deterministic substitute story prose."""
from __future__ import annotations

import pytest

from ai_stack.live_dramatic_scene_simulator import (
    LDSSInput,
    build_deterministic_ldss_output,
    build_scene_turn_envelope_v2,
)


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


def _canonical_ldss_input(
    human: str,
    *,
    turn: int = 0,
    session_output_language: str = "de",
) -> LDSSInput:
    roster = {
        "annette_reille": "annette",
        "alain_reille": "alain",
        "veronique_vallon": "veronique",
        "michel_longstreet": "michel",
    }
    human_slug = roster[human]
    npc_ids = [actor_id for actor_id in roster if actor_id != human]
    return LDSSInput(
        story_session_state={
            "contract": "story_session_state.v1",
            "story_session_id": f"test-open-{human}",
            "turn_number": turn,
            "current_scene_id": "phase_1",
            "content_module_id": "god_of_carnage",
            "runtime_profile_id": "god_of_carnage_solo",
            "runtime_module_id": "solo_story_runtime",
            "selected_player_role": human_slug,
            "human_actor_id": human,
            "npc_actor_ids": npc_ids,
            "visitor_present": False,
        },
        actor_lane_context={
            "contract": "actor_lane_context.v1",
            "content_module_id": "god_of_carnage",
            "runtime_profile_id": "god_of_carnage_solo",
            "selected_player_role": human_slug,
            "human_actor_id": human,
            "actor_lanes": {human: "human", **{n: "npc" for n in npc_ids}},
            "ai_allowed_actor_ids": sorted(npc_ids),
            "ai_forbidden_actor_ids": [human],
        },
        player_input="",
        admitted_objects=[],
        session_output_language=session_output_language,
    )


FORBIDDEN_CANNED_TEXT = (
    "Two couples meet in a Paris apartment",
    "Zwei Paare treffen sich",
    "The incident began at the edge",
    "Der Vorfall begann",
    "You are Annette",
    "Du bist Annette",
    "You are Alain",
    "Du bist Alain",
    "The salon:",
    "Der Salon:",
    "Beneath the surface",
    "You notice the silence",
    "holds back for a moment",
    "hält sich einen Moment zurück",
)


def _combined_text(out) -> str:
    return "\n".join(block.text for block in out.visible_scene_output.blocks)


@pytest.mark.parametrize("human_role", ["annette", "alain"])
def test_opening_uses_explicit_degraded_fallback_only(human_role: str) -> None:
    """Turn 0 must not synthesize narrator_intro, role_anchor, room, or NPC prose."""
    out = build_deterministic_ldss_output(_ldss_input(human_role, turn=0))
    blocks = out.visible_scene_output.blocks
    assert len(blocks) == 1
    assert blocks[0].block_type == "system_degraded_notice"
    assert blocks[0].speaker_label == "System"
    assert blocks[0].actor_id is None
    assert out.status == "degraded_error"
    assert out.error_code == "ldss_no_live_visible_generation"
    assert "LDSS error" in blocks[0].text
    assert "ldss_no_live_visible_generation" in blocks[0].text
    assert out.visible_actor_response_present is False
    assert out.npc_agency_plan is None
    assert out.decision_count == 0
    assert "Fallback:" in blocks[0].text
    combined = _combined_text(out)
    for phrase in FORBIDDEN_CANNED_TEXT:
        assert phrase not in combined


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
    """Turn > 0 must not use the old narrator + actor_line deterministic mock."""
    out = build_deterministic_ldss_output(_ldss_input("annette", turn=1))
    blocks = out.visible_scene_output.blocks
    assert len(blocks) == 1
    assert blocks[0].block_type == "system_degraded_notice"
    assert out.error_code == "ldss_no_live_visible_generation"
    assert "ldss_no_live_visible_generation" in blocks[0].text
    assert out.visible_actor_response_present is False
    combined = _combined_text(out)
    for phrase in FORBIDDEN_CANNED_TEXT:
        assert phrase not in combined


# ---------------------------------------------------------------------------
# STAGING-OPENING-LANGUAGE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P1: output language enforcement
# ---------------------------------------------------------------------------


def test_ldss_opening_fallback_respects_german_session_output_language() -> None:
    """The explicit fallback follows session_output_language without story prose."""
    out = build_deterministic_ldss_output(_ldss_input("annette", turn=0, session_output_language="de"))
    combined = _combined_text(out)
    assert "LDSS-Fehler ldss_no_live_visible_generation" in combined
    assert "Die Live-Szenengenerierung" in combined
    assert "Ersatz-Erzählung" in combined
    for phrase in FORBIDDEN_CANNED_TEXT:
        assert phrase not in combined


def test_ldss_opening_fallback_does_not_emit_role_anchor_for_german_session() -> None:
    """The fallback must not pretend to place the player role."""
    out = build_deterministic_ldss_output(_ldss_input("annette", turn=0, session_output_language="de"))
    combined = _combined_text(out)
    assert "Du bist Annette" not in combined
    assert "You are Annette" not in combined
    assert "Annette Reille" not in combined


def test_ldss_opening_fallback_english_session_still_works() -> None:
    """English sessions receive an explicit English fallback, not an opening template."""
    out = build_deterministic_ldss_output(_ldss_input("annette", turn=0, session_output_language="en"))
    combined = _combined_text(out)
    assert "LDSS error ldss_no_live_visible_generation" in combined
    assert "Live scene generation" in combined
    assert "No substitute story text" in combined
    assert "You are Annette" not in combined


def test_ldss_opening_fallback_does_not_emit_park_or_schoolyard_prose() -> None:
    out = build_deterministic_ldss_output(_canonical_ldss_input("annette_reille"))
    combined = _combined_text(out)
    assert "Parc Montsouris" not in combined
    assert "Schulhof" not in combined
    assert "schoolyard" not in combined.lower()


def test_ldss_opening_fallback_normalizes_canonical_actor_ids() -> None:
    out = build_deterministic_ldss_output(_canonical_ldss_input("annette_reille"))
    combined = _combined_text(out)
    assert "annette_reille" not in combined
    assert "alain_reille" not in combined
    assert "Du bist Annette" not in combined
    assert "considers the situation" not in combined


def test_ldss_error_is_structured_in_output_and_envelope_diagnostics() -> None:
    ldss_input = _ldss_input("annette", turn=0, session_output_language="de")
    out = build_deterministic_ldss_output(ldss_input)
    out_dict = out.to_dict()
    assert out_dict["status"] == "degraded_error"
    assert out_dict["error_code"] == "ldss_no_live_visible_generation"

    envelope = build_scene_turn_envelope_v2(
        ldss_input=ldss_input,
        ldss_output=out,
        story_session_id="test-ldss-error",
        turn_number=0,
    )
    diag = envelope.to_dict()["diagnostics"]["live_dramatic_scene_simulator"]
    assert diag["status"] == "degraded_error"
    assert diag["error_present"] is True
    assert diag["error_code"] == "ldss_no_live_visible_generation"
