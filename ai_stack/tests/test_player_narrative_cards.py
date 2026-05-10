"""PLAYER-SHELL-NARRATIVE-CARD-01: semantic scene_blocks → player shell cards."""

from __future__ import annotations

from ai_stack.player_narrative_cards import (
    build_player_facing_narrative_cards,
    player_shell_typewriter_start_index,
)


def test_fold_adjacent_actor_action_into_actor_line_same_actor() -> None:
    blocks = [
        {
            "id": "a1",
            "block_type": "actor_line",
            "actor_id": "actor_a_npc",
            "speaker_label": "Actor A",
            "text": 'Actor A: "Hello."',
        },
        {
            "id": "a2",
            "block_type": "actor_action",
            "actor_id": "actor_a_npc",
            "speaker_label": "Actor A",
            "text": "Actor A nickt freundlich.",
        },
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 1
    assert out[0]["block_type"] == "actor_line"
    assert out[0]["card_style"] == "npc_story"
    assert "nickt" in (out[0].get("player_display_text") or "")
    assert "Hello" in (out[0].get("player_display_text") or "")
    assert diag["actor_action_folded_into_actor_card"] == 1


def test_standalone_actor_action_is_npc_story_card() -> None:
    blocks = [
        {
            "id": "x1",
            "block_type": "actor_action",
            "actor_id": "actor_b_npc",
            "speaker_label": "Actor B",
            "text": "Actor B sieht sich um.",
        },
    ]
    out, _diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 1
    assert out[0]["block_type"] == "actor_action"
    assert out[0]["card_style"] == "npc_story"
    assert out[0]["visible_lane"] == "story"


def test_narrator_preserved_with_narrative_story_style() -> None:
    blocks = [{"id": "n1", "block_type": "narrator", "text": "The door is open."}]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 1
    assert out[0]["block_type"] == "narrator"
    assert out[0]["card_style"] == "narrative_story"
    assert diag["narrator_card_preserved"] == 1


def test_player_input_stays_player_lane() -> None:
    blocks = [
        {"id": "p1", "block_type": "player_input", "speaker_label": "You", "text": "Hello?"},
        {
            "id": "p2",
            "block_type": "player_input_outcome",
            "speaker_label": "Actor A",
            "text": 'Actor A says: "Hello?"',
        },
    ]
    out, _diag = build_player_facing_narrative_cards(blocks)
    assert out[0]["card_style"] == "player_lane"
    assert out[1]["card_style"] == "player_lane"


def test_duplicate_action_subsumed_not_second_card() -> None:
    line = 'Actor A: "Welcome." Actor A smiles and offers a handshake.'
    action = "Actor A smiles and offers a handshake."
    blocks = [
        {"id": "l1", "block_type": "actor_line", "actor_id": "actor_a_npc", "speaker_label": "Actor A", "text": line},
        {"id": "a1", "block_type": "actor_action", "actor_id": "actor_a_npc", "speaker_label": "Actor A", "text": action},
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 1
    assert diag.get("subsumed_actor_action_removed", 0) >= 1


def test_duplicate_action_subsumed_only_after_prior_action_merged() -> None:
    """Action B is not a substring of the line alone but is duplicate of line + A merged."""
    line = "Actor A: Just a short sentence."
    a1 = "Actor A adds a longer stage direction that will be repeated later."
    a2 = "Actor A adds a longer stage direction that will be repeated later."
    blocks = [
        {"id": "l1", "block_type": "actor_line", "actor_id": "actor_a_npc", "speaker_label": "Actor A", "text": line},
        {"id": "x1", "block_type": "actor_action", "actor_id": "actor_a_npc", "speaker_label": "Actor A", "text": a1},
        {"id": "x2", "block_type": "actor_action", "actor_id": "actor_a_npc", "speaker_label": "Actor A", "text": a2},
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 1
    assert diag.get("subsumed_actor_action_removed", 0) >= 1


def test_paraphrase_actor_action_subsumed_when_tokens_overlap_line() -> None:
    """Paraphrase of handshake beat: not substring of long line but high token recall on action."""
    line = (
        "Veronique warmly welcomes Annette and expresses that she is glad to see her. "
        "She offers her hand in greeting and signals the beginning of a polite, "
        "civil exchange. Alain watches the scene carefully, ready to react if needed."
    )
    action = "Veronique smiles warmly and offers Annette her hand in greeting."
    blocks = [
        {
            "id": "l1",
            "block_type": "actor_line",
            "actor_id": "veronique_vallon",
            "speaker_label": "Véronique",
            "text": line,
        },
        {
            "id": "a1",
            "block_type": "actor_action",
            "actor_id": "veronique_vallon",
            "speaker_label": "Véronique",
            "text": action,
        },
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 1
    assert diag.get("subsumed_actor_action_removed", 0) >= 1
    assert diag.get("near_duplicate_actor_action_removed", 0) >= 1


def test_standalone_actor_action_subsumed_after_player_gap() -> None:
    line = 'Actor A: "Hello." Actor A waves.'
    dup = "Actor A waves."
    blocks = [
        {"id": "l1", "block_type": "actor_line", "actor_id": "actor_a_npc", "speaker_label": "Actor A", "text": line},
        {"id": "p1", "block_type": "player_input", "speaker_label": "You", "text": "Hi"},
        {"id": "a1", "block_type": "actor_action", "actor_id": "actor_a_npc", "speaker_label": "Actor A", "text": dup},
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 2
    assert all(b.get("block_type") != "actor_action" for b in out)
    assert diag.get("subsumed_actor_action_removed", 0) >= 1


def test_colon_stutter_stripped_on_display() -> None:
    blocks = [
        {
            "id": "s1",
            "block_type": "actor_line",
            "actor_id": "actor_a_npc",
            "speaker_label": "Actor A",
            "text": "Actor A: Actor A testet etwas.",
        },
    ]
    out, _diag = build_player_facing_narrative_cards(blocks)
    disp = out[0].get("player_display_text") or ""
    assert "Actor A: Actor A" not in disp


def test_typewriter_index_maps_across_fold() -> None:
    cards = [
        {"id": "n0", "block_type": "narrator", "player_shell_semantic_span": (0, 0)},
        {"id": "l1", "block_type": "actor_line", "player_shell_semantic_span": (1, 2)},
    ]
    assert player_shell_typewriter_start_index(cards, prior_semantic_index=1, used_cumulative_story_blocks=True) == 1
    assert player_shell_typewriter_start_index(cards, prior_semantic_index=2, used_cumulative_story_blocks=True) == 1


def _long_goc_dup_tail_pair() -> tuple[str, str]:
    """Long dialogue plus trailing clause duplicated as a second block (redundancy path)."""
    long_line = (
        'Actor A: "Hello." Actor A watches the group and pauses as the tension rises. '
        "This sentence is intentionally long enough for token and fold rules."
    )
    dup_tail = (
        "Actor A watches the group and pauses as the tension rises. "
        "This sentence is intentionally long enough for token and fold rules."
    )
    return long_line, dup_tail


def test_consecutive_actor_line_same_actor_dedupes_redundant_second() -> None:
    long_line, dup_tail = _long_goc_dup_tail_pair()
    blocks = [
        {
            "id": "l1",
            "block_type": "actor_line",
            "actor_id": "actor_a_npc",
            "speaker_label": "Actor A",
            "text": long_line,
        },
        {
            "id": "l2",
            "block_type": "actor_line",
            "actor_id": "actor_a_npc",
            "speaker_label": "Actor A",
            "text": dup_tail,
        },
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 1
    assert diag.get("consecutive_redundant_story_card_removed", 0) >= 1


def test_consecutive_actor_line_different_actors_no_collapse() -> None:
    long_line, dup_tail = _long_goc_dup_tail_pair()
    dup_b = dup_tail.replace("Actor A", "Actor B")
    blocks = [
        {
            "id": "l1",
            "block_type": "actor_line",
            "actor_id": "actor_a_npc",
            "speaker_label": "Actor A",
            "text": long_line,
        },
        {
            "id": "l2",
            "block_type": "actor_line",
            "actor_id": "actor_b_npc",
            "speaker_label": "Actor B",
            "text": dup_b,
        },
    ]
    out, _diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 2


def test_consecutive_actor_line_accent_matched_speaker_labels_dedupe() -> None:
    long_line = (
        'Véronique: "Bonjour." Véronique turns toward the door and waits patiently for the next reply. '
        "Additional filler text ensures substring and token rules trigger reliably."
    )
    dup_tail = (
        "Véronique turns toward the door and waits patiently for the next reply. "
        "Additional filler text ensures substring and token rules trigger reliably."
    )
    blocks = [
        {
            "id": "l1",
            "block_type": "actor_line",
            "speaker_label": "Véronique",
            "text": long_line,
        },
        {
            "id": "l2",
            "block_type": "actor_line",
            "speaker_label": "Veronique",
            "text": dup_tail,
        },
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 1
    assert diag.get("consecutive_redundant_story_card_removed", 0) >= 1


def test_typewriter_index_after_consecutive_story_collapse() -> None:
    long_line, dup_tail = _long_goc_dup_tail_pair()
    blocks = [
        {"id": "n0", "block_type": "narrator", "text": "Intro."},
        {
            "id": "l1",
            "block_type": "actor_line",
            "actor_id": "actor_a_npc",
            "speaker_label": "Actor A",
            "text": long_line,
        },
        {
            "id": "l2",
            "block_type": "actor_line",
            "actor_id": "actor_a_npc",
            "speaker_label": "Actor A",
            "text": dup_tail,
        },
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 2
    assert diag.get("consecutive_redundant_story_card_removed", 0) >= 1
    span = out[1].get("player_shell_semantic_span")
    assert isinstance(span, tuple) and span == (1, 2)
    i1 = player_shell_typewriter_start_index(out, prior_semantic_index=1, used_cumulative_story_blocks=True)
    i2 = player_shell_typewriter_start_index(out, prior_semantic_index=2, used_cumulative_story_blocks=True)
    assert i1 == i2 == 1


def test_narrator_adjacent_redundant_actor_action_removed() -> None:
    blocks = [
        {
            "id": "n1",
            "block_type": "narrator",
            "text": "Veronique smiles warmly and offers Annette her hand.",
        },
        {
            "id": "a1",
            "block_type": "actor_action",
            "actor_id": "veronique_vallon",
            "speaker_label": "Véronique",
            "text": "Veronique smiles warmly and offers Annette her hand.",
        },
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 1
    assert out[0]["block_type"] == "narrator"
    assert diag.get("narrator_adjacent_redundant_story_card_removed", 0) >= 1
    assert diag.get("narrator_adjacent_redundant_actor_action_removed", 0) >= 1


def test_narrator_adjacent_actor_line_with_new_dialogue_is_kept() -> None:
    blocks = [
        {
            "id": "n1",
            "block_type": "narrator",
            "text": "Veronique tries to remain polite.",
        },
        {
            "id": "l1",
            "block_type": "actor_line",
            "actor_id": "veronique_vallon",
            "speaker_label": "Véronique",
            "text": 'Véronique: "Welcome. I hope we can speak calmly."',
        },
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 2
    assert diag.get("narrator_adjacent_redundant_actor_line_removed", 0) == 0


def test_narrator_adjacent_actor_line_regie_like_can_be_removed_when_policy_enabled() -> None:
    blocks = [
        {
            "id": "n1",
            "block_type": "narrator",
            "text": "Veronique greets Annette politely.",
        },
        {
            "id": "l1",
            "block_type": "actor_line",
            "actor_id": "veronique_vallon",
            "speaker_label": "Véronique",
            "text": "Veronique greets Annette politely.",
        },
    ]
    out, diag = build_player_facing_narrative_cards(
        blocks,
        policy={"narrator_adjacent_actor_line_dedupe": True},
    )
    assert len(out) == 1
    assert diag.get("narrator_adjacent_redundant_actor_line_removed", 0) >= 1


def test_narrator_adjacent_two_redundant_npc_cards_both_removed() -> None:
    blocks = [
        {
            "id": "n1",
            "block_type": "narrator",
            "text": "Veronique smiles warmly and offers Annette her hand.",
        },
        {
            "id": "a1",
            "block_type": "actor_action",
            "actor_id": "veronique_vallon",
            "speaker_label": "Véronique",
            "text": "Veronique smiles warmly and offers Annette her hand.",
        },
        {
            "id": "a2",
            "block_type": "actor_action",
            "actor_id": "veronique_vallon",
            "speaker_label": "Véronique",
            "text": "Veronique smiles warmly and offers Annette her hand.",
        },
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 1
    assert diag.get("narrator_adjacent_redundant_story_card_removed", 0) >= 2
    assert diag.get("narrator_adjacent_redundant_actor_action_removed", 0) >= 2


def test_player_lane_between_narrator_and_npc_blocks_cross_dedupe() -> None:
    blocks = [
        {
            "id": "n1",
            "block_type": "narrator",
            "text": "Veronique smiles warmly and offers Annette her hand.",
        },
        {"id": "p1", "block_type": "player_input", "speaker_label": "You", "text": "Greet Veronique"},
        {
            "id": "a1",
            "block_type": "actor_action",
            "actor_id": "veronique_vallon",
            "speaker_label": "Véronique",
            "text": "Veronique smiles warmly and offers Annette her hand.",
        },
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 3
    assert diag.get("narrator_adjacent_redundant_story_card_removed", 0) == 0


def test_narrator_adjacent_non_redundant_actor_action_kept() -> None:
    blocks = [
        {
            "id": "n1",
            "block_type": "narrator",
            "text": "Veronique seems tense and briefly looks out the window.",
        },
        {
            "id": "a1",
            "block_type": "actor_action",
            "actor_id": "alain_reille",
            "speaker_label": "Alain",
            "text": "Alain leans forward and responds sharply to the latest accusation.",
        },
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 2
    assert diag.get("narrator_adjacent_redundant_story_card_removed", 0) == 0
