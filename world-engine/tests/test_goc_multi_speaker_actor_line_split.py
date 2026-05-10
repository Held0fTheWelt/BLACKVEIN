"""Split jammed multi-speaker actor_line blocks; drop duplicate actor_action tails.

Repro path (megablock → split → finalize): a single ``actor_line`` with two roster
``Name:`` prefixes is segmented in ``_finalize_visible_blocks_with_goc_actor_split``
via ``ai_stack.goc_npc_transcript_projection.split_merged_goc_actor_line_segments``
(roster from ``runtime_projection``; policy from ``story_runtime_experience``).
"""

from __future__ import annotations

from app.story_runtime.manager import (
    _dedupe_goc_speaker_colon_stutter,
    _expand_multi_speaker_actor_lines,
    _finalize_visible_blocks_with_goc_actor_split,
    _prune_actor_actions_subsumed_by_prior_actor_lines,
    _split_merged_goc_actor_line_segments,
)


def test_split_two_speakers_veronique_alain() -> None:
    segs = _split_merged_goc_actor_line_segments(
        'Veronique: "Hello." Alain: "Yes."',
    )
    assert len(segs) == 2
    assert segs[0][0] == "veronique_vallon"
    assert segs[1][0] == "alain_reille"


def test_merge_consecutive_same_speaker() -> None:
    segs = _split_merged_goc_actor_line_segments(
        'Veronique: "A." Veronique: smiles. Alain: nods.',
    )
    assert len(segs) == 2
    assert segs[0][0] == "veronique_vallon"
    assert '"A."' in segs[0][2] and "smiles" in segs[0][2]
    assert segs[1][0] == "alain_reille"


def test_finalize_splits_megablock_with_runtime_projection() -> None:
    """Repro: finalize + projection roster yields two distinct ``actor_id`` lines."""
    blocks = [
        {
            "id": "turn-2-live-block-1",
            "block_type": "actor_line",
            "speaker_label": "Veronique",
            "actor_id": "veronique_vallon",
            "text": 'Veronique: "Guten Tag." Alain: "Ja, bitte."',
            "source": "x",
        }
    ]
    out, _diag = _finalize_visible_blocks_with_goc_actor_split(
        blocks,
        expected_language="de",
        human_actor_id="annette_reille",
        selected_player_role="annette",
        turn_number=2,
        player_input_echo_strings=None,
        runtime_projection={
            "human_actor_id": "annette_reille",
            "selected_player_role": "annette",
            "npc_actor_ids": ["veronique_vallon", "alain_reille", "michel_longstreet"],
        },
        story_runtime_experience=None,
    )
    lines = [b for b in out if str(b.get("block_type") or "").lower() == "actor_line"]
    assert len(lines) >= 2
    assert {str(b.get("actor_id") or "") for b in lines} >= {"veronique_vallon", "alain_reille"}


def test_expand_one_block_into_two() -> None:
    blocks = [
        {
            "id": "turn-1-live-block-9",
            "block_type": "actor_line",
            "speaker_label": "Veronique",
            "actor_id": "veronique_vallon",
            "text": 'Veronique: "Hi." Alain: "Da."',
            "source": "x",
        }
    ]
    out = _expand_multi_speaker_actor_lines(blocks)
    assert len(out) == 2
    assert out[0]["actor_id"] == "veronique_vallon"
    assert out[1]["actor_id"] == "alain_reille"
    assert out[1]["id"] == "turn-1-live-block-9-spk1"


def test_single_speaker_unchanged() -> None:
    b = {
        "id": "b1",
        "block_type": "actor_line",
        "actor_id": "michel_longstreet",
        "text": "Michel: Nur eine Zeile.",
    }
    assert _expand_multi_speaker_actor_lines([b]) == [b]


def test_prune_action_when_substring_of_prior_line() -> None:
    line = (
        'Veronique: "Welcome." Veronique: Veronique smiles warmly '
        "and offers Annette her hand in greeting."
    )
    action = "Veronique smiles warmly and offers Annette her hand in greeting."
    blocks = [
        {"id": "1", "block_type": "actor_line", "actor_id": "veronique_vallon", "text": line},
        {"id": "2", "block_type": "actor_action", "actor_id": "veronique_vallon", "text": action},
    ]
    out = _prune_actor_actions_subsumed_by_prior_actor_lines(blocks)
    assert len(out) == 1
    assert out[0]["block_type"] == "actor_line"


def test_prune_action_accent_drift_still_matches() -> None:
    """Action lane uses accents; spoken lane uses Veronique: — fold must align for substring prune."""
    line = "Veronique: redet. Veronique: Véronique nickt leicht."
    action = "Véronique nickt leicht."
    blocks = [
        {"id": "1", "block_type": "actor_line", "actor_id": "veronique_vallon", "text": line},
        {"id": "2", "block_type": "actor_action", "actor_id": "veronique_vallon", "text": action},
    ]
    out = _prune_actor_actions_subsumed_by_prior_actor_lines(blocks)
    assert len(out) == 1


def test_dedupe_keeps_name_before_quoted_speech_only_fixes_regie_tail() -> None:
    raw = (
        'Veronique: "Welcome, Annette. I am very glad you are here." '
        "Veronique: Veronique smiles warmly and offers Annette her hand in greeting."
    )
    out = _dedupe_goc_speaker_colon_stutter(raw)
    assert 'Veronique: "Welcome' in out
    assert "Veronique: Véronique" not in out
    assert "Veronique smiles warmly" in out


def test_dedupe_michel_stutter_after_quote() -> None:
    raw = 'Michel: "Of course, Annette." Michel: Michel gestures forward with an inviting motion.'
    out = _dedupe_goc_speaker_colon_stutter(raw)
    assert 'Michel: "Of course' in out
    assert "Michel: Michel" not in out
    assert "Michel gestures forward" in out
