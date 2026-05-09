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


def test_sanitize_strips_accent_mismatched_duplicate_speaker_prefix():
    clean, _ = sanitize_visible_block_text(
        "Véronique: Bonjour.",
        block_type="actor_line",
        speaker_label="Veronique",
        actor_id="veronique_vallon",
        expected_language="de",
    )
    assert clean == "Bonjour."


def test_sanitize_collapses_veronique_colon_veronique_accent_variant():
    clean, _ = sanitize_visible_block_text(
        "Veronique: Véronique lächelt leise.",
        block_type="actor_action",
        speaker_label="Veronique",
        actor_id="veronique_vallon",
        expected_language="de",
    )
    assert clean == "Véronique lächelt leise."


def test_finalize_drops_name_only_accent_mismatch():
    blocks = [
        {
            "block_type": "actor_line",
            "speaker_label": "Veronique",
            "actor_id": "veronique_vallon",
            "text": "Véronique",
        },
    ]
    out, diag = finalize_visible_scene_blocks(
        blocks,
        expected_language="de",
        human_actor_id="annette",
        selected_player_role="annette",
        turn_number=1,
    )
    assert len(out) == 0
    assert diag["name_only_actor_block_removed"] >= 1


def test_finalize_subsumes_actor_action_contained_in_prior_actor_line():
    long_line = (
        "Veronique steht auf und geht zur Tür, während sie sagt, "
        "dass sie das nicht länger ertragen kann."
    )
    short_action = "Veronique steht auf und geht zur Tür"
    blocks = [
        {
            "block_type": "actor_line",
            "speaker_label": "Veronique",
            "actor_id": "veronique_vallon",
            "text": long_line,
        },
        {
            "block_type": "actor_action",
            "speaker_label": "Veronique",
            "actor_id": "veronique_vallon",
            "text": short_action,
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
    assert diag["actor_action_subsumed_by_actor_line_removed"] == 1


def test_finalize_removes_npc_actor_line_that_echoes_player_input():
    player = "Ich gehe jetzt zur Tür und möchte nicht länger diskutieren."
    blocks = [
        {"block_type": "narrator", "speaker_label": "Narrator", "text": "Szene."},
        {
            "block_type": "actor_line",
            "speaker_label": "Veronique",
            "actor_id": "veronique_vallon",
            "text": f"Veronique: {player}",
        },
        {
            "block_type": "actor_line",
            "speaker_label": "Veronique",
            "actor_id": "veronique_vallon",
            "text": "Das reicht mir.",
        },
    ]
    out, diag = finalize_visible_scene_blocks(
        blocks,
        expected_language="de",
        human_actor_id="annette_reille",
        selected_player_role="annette",
        turn_number=1,
        player_input_echo_strings=[player],
    )
    assert len(out) == 2
    assert diag["player_input_echo_removed_from_npc_block"] == 1


def test_finalize_keeps_human_lane_when_text_matches_player_input():
    player = "Ich bleibe ruhig und höre zu."
    blocks = [
        {
            "block_type": "actor_line",
            "speaker_label": "Annette",
            "actor_id": "annette_reille",
            "text": player,
        },
    ]
    out, diag = finalize_visible_scene_blocks(
        blocks,
        expected_language="de",
        human_actor_id="annette_reille",
        selected_player_role="annette",
        turn_number=1,
        player_input_echo_strings=[player],
    )
    assert len(out) == 1
    assert diag["player_input_echo_removed_from_npc_block"] == 0


def test_finalize_drops_narrator_label_colon_only_line():
    blocks = [
        {"block_type": "narrator", "speaker_label": "Narrator", "text": "Szene im Salon."},
        {"block_type": "narrator", "speaker_label": "Narrator", "text": "Veronique:"},
        {
            "block_type": "actor_line",
            "speaker_label": "Veronique",
            "actor_id": "veronique_vallon",
            "text": "Wir sollten das klären.",
        },
    ]
    out, diag = finalize_visible_scene_blocks(
        blocks,
        expected_language="de",
        human_actor_id="annette_reille",
        selected_player_role="annette",
        turn_number=1,
    )
    assert len(out) == 2
    assert diag["label_only_line_removed"] == 1
    assert all("Veronique:" not in (str(b.get("text") or "")) for b in out)
