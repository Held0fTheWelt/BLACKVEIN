"""Tests for VISIBLE-NARRATIVE-CONTRACT-01 visible text sanitizer."""

from __future__ import annotations

from ai_stack.visible_narrative_contract import (
    detect_english_leak_in_german_session,
    finalize_visible_scene_blocks,
    sanitize_gm_narration_beat_line,
    sanitize_visible_block_text,
    strip_internal_beat_markers,
)


def test_strip_internal_beat_prefixes_multiline():
    raw = "narrator_intro: First line\n\nrole_anchor: Second\nscene_setup: Third"
    out = strip_internal_beat_markers(raw)
    assert "narrator_intro:" not in out.lower()
    assert "role_anchor:" not in out.lower()
    assert "scene_setup:" not in out.lower()


def test_sanitize_gm_beat_strips_prefix_and_scaffold():
    line = "role_anchor: Veronique reacts immediately."
    out = sanitize_gm_narration_beat_line(line)
    assert "role_anchor:" not in out.lower()
    assert "reacts immediately" not in out.lower()


def test_german_session_english_placeholder_flagged():
    t = "You are Annette, arriving with Alain into a room."
    assert detect_english_leak_in_german_session(t) is True
    assert detect_english_leak_in_german_session("Du bist Annette.") is False


def test_sanitize_actor_line_strips_duplicate_veronique_label():
    clean, _ = sanitize_visible_block_text(
        "Veronique: Bonjour.",
        block_type="actor_line",
        speaker_label="Veronique",
        actor_id="veronique_vallon",
        expected_language="de",
    )
    assert clean == "Bonjour."


def test_finalize_dedupes_consecutive_identical_actor_blocks():
    blocks = [
        {
            "block_type": "actor_line",
            "speaker_label": "Veronique",
            "actor_id": "veronique_vallon",
            "text": "Same line.",
        },
        {
            "block_type": "actor_line",
            "speaker_label": "Veronique",
            "actor_id": "veronique_vallon",
            "text": "Same line.",
        },
    ]
    out, diag = finalize_visible_scene_blocks(
        blocks,
        expected_language="de",
        human_actor_id="annette",
        selected_player_role="annette",
        turn_number=1,
    )
    assert len(out) == 1
    assert diag["visible_language_contract_pass"] is True


def test_finalize_annette_role_visible_turn_zero():
    blocks = [
        {"block_type": "narrator", "speaker_label": "Narrator", "text": "Intro."},
        {
            "block_type": "narrator",
            "speaker_label": "Narrator",
            "text": "Du bist Annette, hier im Salon.",
        },
        {"block_type": "narrator", "speaker_label": "Narrator", "text": "Szene."},
        {
            "block_type": "actor_line",
            "speaker_label": "Veronique",
            "actor_id": "veronique_vallon",
            "text": "Willkommen.",
        },
    ]
    out, diag = finalize_visible_scene_blocks(
        blocks,
        expected_language="de",
        human_actor_id="annette_reille",
        selected_player_role="annette",
        turn_number=0,
    )
    assert diag["selected_role_visible_in_opening"] is True
    assert diag["player_identity_anchor_present"] is True
    assert len(out) == 4
