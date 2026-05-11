"""PLAYER-ACTION-INTENT-01: deterministic rules + diegetic projection from module locale."""

from __future__ import annotations

import yaml

from story_runtime_core.content_locale import (
    build_player_attributed_visible_line,
    classify_player_input_from_rules,
    clear_content_locale_caches,
    resolve_content_modules_root,
)


def _root() -> object:
    clear_content_locale_caches()
    return resolve_content_modules_root()


def test_gehe_kuche_de_action_projection():
    root = _root()
    hit = classify_player_input_from_rules(
        "Gehe in die Küche",
        module_id="god_of_carnage",
        lang_hint="de",
        content_modules_root=root,
    )
    assert hit["deterministic_intent_rule"] == "de_movement_gehe"
    assert hit["player_input_kind"] == "action"
    line = build_player_attributed_visible_line(
        name="Annette",
        raw="Gehe in die Küche",
        input_kind="action",
        lang="de",
        module_id="god_of_carnage",
        content_modules_root=root,
        projection_key=hit.get("projection_key"),
        projection_captures=hit.get("captures"),
    )
    bundle = yaml.safe_load((root / "god_of_carnage" / "locale" / "module_strings.yaml").read_text(encoding="utf-8"))
    expected = bundle["strings"]["player_outcome.action_toward_room"]["de"].format(name="Annette", room="Küche")
    assert line == expected


def test_schau_fenster_perception_projection():
    root = _root()
    hit = classify_player_input_from_rules(
        "Schau aus dem Fenster",
        module_id="god_of_carnage",
        lang_hint="de",
        content_modules_root=root,
    )
    assert hit["deterministic_intent_rule"] == "de_perception_window"
    assert hit["player_input_kind"] == "perception"
    line = build_player_attributed_visible_line(
        name="Annette",
        raw="Schau aus dem Fenster",
        input_kind="action",
        lang="de",
        module_id="god_of_carnage",
        content_modules_root=root,
        projection_key=hit.get("projection_key"),
        projection_captures=hit.get("captures"),
    )
    bundle = yaml.safe_load((root / "god_of_carnage" / "locale" / "module_strings.yaml").read_text(encoding="utf-8"))
    expected = bundle["strings"]["player_outcome.perception_at_window"]["de"].format(name="Annette")
    assert line == expected


def test_gibt_es_question_speech():
    root = _root()
    hit = classify_player_input_from_rules(
        "Gibt es hier ein Bad?",
        module_id="god_of_carnage",
        lang_hint="de",
        content_modules_root=root,
    )
    assert hit["player_input_kind"] == "speech"
    assert hit["projection_key"] == "player_outcome.speech_question"
    line = build_player_attributed_visible_line(
        name="Annette",
        raw="Gibt es hier ein Bad?",
        input_kind="speech",
        lang="de",
        module_id="god_of_carnage",
        content_modules_root=root,
        projection_key=hit.get("projection_key"),
        projection_captures=hit.get("captures"),
    )
    assert "fragt" in line.lower()
    assert "Bad" in line


def test_ich_sage_speech():
    root = _root()
    hit = classify_player_input_from_rules(
        "Ich sage: Guten Abend",
        module_id="god_of_carnage",
        lang_hint="de",
        content_modules_root=root,
    )
    assert hit["deterministic_intent_rule"] == "de_ich_sage_speech"
    line = build_player_attributed_visible_line(
        name="Annette",
        raw="Ich sage: Guten Abend",
        input_kind="speech",
        lang="de",
        module_id="god_of_carnage",
        content_modules_root=root,
        projection_key=hit.get("projection_key"),
        projection_captures=hit.get("captures"),
    )
    assert "sagt" in line.lower()
    assert "Guten Abend" in line


def test_mixed_stand_and_say():
    root = _root()
    hit = classify_player_input_from_rules(
        "Ich stehe auf und sage: Das reicht.",
        module_id="god_of_carnage",
        lang_hint="de",
        content_modules_root=root,
    )
    assert hit["player_input_kind"] == "mixed"
    line = build_player_attributed_visible_line(
        name="Annette",
        raw="Ich stehe auf und sage: Das reicht.",
        input_kind="mixed",
        lang="de",
        module_id="god_of_carnage",
        content_modules_root=root,
        projection_key=hit.get("projection_key"),
        projection_captures=hit.get("captures"),
    )
    assert "steht auf" in line.lower()
    assert "Das reicht" in line


def test_was_sehe_ich_fenster_question_is_perception_not_quoted_speech():
    """Regression: perception question must not use speech_question (no „Annette fragt: …“)."""
    root = _root()
    text = "Was sehe ich, wenn ich aus dem Fenster schaue?"
    hit = classify_player_input_from_rules(
        text,
        module_id="god_of_carnage",
        lang_hint="de",
        content_modules_root=root,
    )
    assert hit["deterministic_intent_rule"] == "de_perception_question_window"
    assert hit["player_input_kind"] == "perception"
    line = build_player_attributed_visible_line(
        name="Annette",
        raw=text,
        input_kind="action",
        lang="de",
        module_id="god_of_carnage",
        content_modules_root=root,
        projection_key=hit.get("projection_key"),
        projection_captures=hit.get("captures"),
    )
    assert "fragt" not in line.lower()
    assert "sagt:" not in line.lower()
    bundle = yaml.safe_load((root / "god_of_carnage" / "locale" / "module_strings.yaml").read_text(encoding="utf-8"))
    expected = bundle["strings"]["player_outcome.perception_question_at_window"]["de"].format(name="Annette")
    assert line == expected


def test_ich_gehe_badezimmer():
    root = _root()
    hit = classify_player_input_from_rules(
        "Ich gehe ins Badezimmer",
        module_id="god_of_carnage",
        lang_hint="de",
        content_modules_root=root,
    )
    assert hit["player_input_kind"] == "action"
    line = build_player_attributed_visible_line(
        name="Annette",
        raw="Ich gehe ins Badezimmer",
        input_kind="action",
        lang="de",
        module_id="god_of_carnage",
        content_modules_root=root,
        projection_key=hit.get("projection_key"),
        projection_captures=hit.get("captures"),
    )
    assert "Badezimmer" in line
