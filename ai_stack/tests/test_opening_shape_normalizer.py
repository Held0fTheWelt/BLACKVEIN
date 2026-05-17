from __future__ import annotations

from ai_stack.opening_shape_normalizer import (
    GOD_OF_CARNAGE_MODULE_ID,
    normalize_opening_narration_beats,
)


def test_non_opening_returns_none_tuple():
    beats, meta = normalize_opening_narration_beats(
        "any",
        selected_player_role="annette",
        human_actor_id="annette",
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        turn_number=1,
        output_language="de",
        existing_actor_lines=None,
    )
    assert beats is None and meta is None


def test_wrong_module_returns_none():
    beats, meta = normalize_opening_narration_beats(
        "x",
        selected_player_role="annette",
        human_actor_id="annette",
        module_id="other",
        turn_number=0,
        output_language="de",
        existing_actor_lines=[{"speaker_id": "v", "text": "hi"}],
    )
    assert beats is None and meta is None


def test_model_list_preserves_extra_opening_beats():
    beats, meta = normalize_opening_narration_beats(
        [
            "narrator_intro: On the schoolyard two boys and a stick left an injury; parents chose a civilised meeting.",
            "scene_setup: In the Paris apartment tulips, espresso, folded coats, and art books stage the ritual before dessert.",
            "role_anchor: You are Annette Reille, arriving as a guest beside Alain — not a spectator.",
            "The threshold remains visible as everyone enters the room.",
            "The host and guest positions settle around the table.",
            "The first playable silence opens.",
        ],
        selected_player_role="annette",
        human_actor_id="annette_reille",
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        turn_number=0,
        output_language="en",
        existing_actor_lines=None,
    )
    assert beats and len(beats) == 6
    assert "schoolyard" in beats[0].lower()
    assert "paris" in beats[1].lower() or "tulip" in beats[1].lower()
    assert "You are" in beats[2] and "Annette" in beats[2]
    assert "first playable" in beats[-1].lower()
    assert meta and meta.get("opening_narration_source") == "model_list_three_plus"
    assert meta.get("opening_narration_extra_beats_preserved") == 3


def test_single_string_split_paragraphs():
    text = (
        "On the schoolyard two boys and a stick left an injury; their parents agreed on a civilised sit-down.\n\n"
        "In the Paris apartment tulips, espresso cups, and folded coats keep manners on display.\n\n"
        "You are Annette Reille, arriving as a guest beside Alain — not a spectator."
    )
    beats, meta = normalize_opening_narration_beats(
        text,
        selected_player_role="annette",
        human_actor_id="annette",
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        turn_number=0,
        output_language="en",
        existing_actor_lines=[{"speaker_id": "veronique_vallon", "text": "Hi"}],
    )
    assert beats and len(beats) == 3
    assert "schoolyard" in beats[0].lower()
    assert meta and meta["opening_narration_source"] == "single_string_split_paragraphs"


def test_annette_deterministic_anchor_contains_name():
    beats, _meta = normalize_opening_narration_beats(
        "Only one paragraph about the salon.",
        selected_player_role="annette",
        human_actor_id="annette",
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        turn_number=0,
        output_language="en",
        existing_actor_lines=[{"speaker_id": "veronique_vallon", "text": "Welcome."}],
    )
    assert beats and len(beats) == 3
    assert "Annette" in beats[2]


def test_alain_deterministic_anchor_contains_name():
    beats, _meta = normalize_opening_narration_beats(
        "Opening prose without triple newline.",
        selected_player_role="alain",
        human_actor_id="alain",
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        turn_number=0,
        output_language="en",
        existing_actor_lines=[{"speaker_id": "veronique_vallon", "text": "Welcome."}],
    )
    assert beats and len(beats) == 3
    assert "Alain" in beats[2]


def test_german_anchor_when_language_de():
    beats, _meta = normalize_opening_narration_beats(
        "Ein Absatz.",
        selected_player_role="annette",
        human_actor_id="annette",
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        turn_number=0,
        output_language="de",
        existing_actor_lines=[{"speaker_id": "veronique_vallon", "text": "Welcome."}],
    )
    assert beats and "Du bist" in beats[2]


def test_empty_without_actor_lanes_returns_none():
    beats, meta = normalize_opening_narration_beats(
        "",
        selected_player_role="annette",
        human_actor_id="annette",
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        turn_number=0,
        output_language="de",
        existing_actor_lines=None,
    )
    assert beats is None and meta is None


def test_diagnostic_string_rejected():
    beats, meta = normalize_opening_narration_beats(
        "system_degraded_notice: hidden",
        selected_player_role="annette",
        human_actor_id="annette",
        module_id=GOD_OF_CARNAGE_MODULE_ID,
        turn_number=0,
        output_language="de",
        existing_actor_lines=[{"speaker_id": "v", "text": "x"}],
    )
    assert beats is None and meta is None
