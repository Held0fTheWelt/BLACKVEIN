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
            "text": "Actor A: „Hallo.“",
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
    assert "Hallo" in (out[0].get("player_display_text") or "")
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
    blocks = [{"id": "n1", "block_type": "narrator", "text": "Die Tür steht offen."}]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 1
    assert out[0]["block_type"] == "narrator"
    assert out[0]["card_style"] == "narrative_story"
    assert diag["narrator_card_preserved"] == 1


def test_player_input_stays_player_lane() -> None:
    blocks = [
        {"id": "p1", "block_type": "player_input", "speaker_label": "Du", "text": "Hallo?"},
        {
            "id": "p2",
            "block_type": "player_input_outcome",
            "speaker_label": "Actor A",
            "text": "Actor A sagt: „Hallo?“",
        },
    ]
    out, _diag = build_player_facing_narrative_cards(blocks)
    assert out[0]["card_style"] == "player_lane"
    assert out[1]["card_style"] == "player_lane"


def test_duplicate_action_subsumed_not_second_card() -> None:
    line = 'Actor A: „Willkommen.“ Actor A lächelt und reicht die Hand.'
    action = "Actor A lächelt und reicht die Hand."
    blocks = [
        {"id": "l1", "block_type": "actor_line", "actor_id": "actor_a_npc", "speaker_label": "Actor A", "text": line},
        {"id": "a1", "block_type": "actor_action", "actor_id": "actor_a_npc", "speaker_label": "Actor A", "text": action},
    ]
    out, diag = build_player_facing_narrative_cards(blocks)
    assert len(out) == 1
    assert diag.get("subsumed_actor_action_removed", 0) >= 1


def test_duplicate_action_subsumed_only_after_prior_action_merged() -> None:
    """Action B is not a substring of the line alone but is duplicate of line + A merged."""
    line = "Actor A: Nur ein kurzer Satz."
    a1 = "Actor A fügt eine längere Regie hinzu, die später wiederholt wird."
    a2 = "Actor A fügt eine längere Regie hinzu, die später wiederholt wird."
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
        "Véronique begrüßt Annette herzlich und drückt ihre Freude aus, sie zu sehen. "
        "Sie reicht ihr die Hand zum Gruß und signalisiert damit den Beginn eines "
        "höflichen und zivilen Austauschs. Alain beobachtet die Szene aufmerksam, "
        "bereit, bei Bedarf zu reagieren."
    )
    action = "Veronique lächelt herzlich und reicht Annette die Hand zum Gruß."
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
    line = 'Actor A: „Hallo.“ Actor A winkt.'
    dup = "Actor A winkt."
    blocks = [
        {"id": "l1", "block_type": "actor_line", "actor_id": "actor_a_npc", "speaker_label": "Actor A", "text": line},
        {"id": "p1", "block_type": "player_input", "speaker_label": "Du", "text": "Hi"},
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
