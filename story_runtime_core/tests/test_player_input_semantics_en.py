"""PLAYER-INPUT-ACTION-SEMANTICS-ALGORITHM-01: English-language regression corpus.

Covers all required semantic categories. All test inputs are in English (lang_hint="en").
Tests verify:
  - correct player_input_kind / semantic_category
  - speech_projection_allowed gate
  - visible projection does not render raw action input as quoted speech
"""

from __future__ import annotations

import pytest

from story_runtime_core.content_locale import (
    build_player_attributed_visible_line,
    classify_player_input_from_rules,
    clear_content_locale_caches,
    resolve_content_modules_root,
)

MODULE = "god_of_carnage"
LANG = "en"
NAME = "Annette"


def setup_module(_m: object) -> None:
    clear_content_locale_caches()


def _root():
    return resolve_content_modules_root()


def _classify(text: str):
    return classify_player_input_from_rules(
        text,
        module_id=MODULE,
        lang_hint=LANG,
        content_modules_root=_root(),
    )


def _project(text: str, hit: dict) -> str:
    return build_player_attributed_visible_line(
        name=NAME,
        raw=text,
        input_kind=hit["player_input_kind"],
        lang=LANG,
        module_id=MODULE,
        content_modules_root=_root(),
        projection_key=hit.get("projection_key"),
        projection_captures=hit.get("captures"),
    )


def _assert_no_speech_wrapping(line: str, raw: str) -> None:
    """Asserts raw action input is not quoted as dialogue."""
    assert 'says: "' not in line, f"Action rendered as speech (says): {line!r}"
    assert 'asks: "' not in line, f"Action rendered as speech (asks): {line!r}"
    assert f'says: "{raw}"' not in line
    assert f'asks: "{raw}"' not in line


# ---------------------------------------------------------------------------
# Speech / question — speech projection IS allowed
# ---------------------------------------------------------------------------


def test_speech_i_say_colon_is_speech():
    hit = _classify("I say: That is enough.")
    assert hit["player_input_kind"] == "speech"
    assert hit["speech_projection_allowed"] is True
    assert hit["player_speech_committed"] is True
    assert hit["player_action_committed"] is False


def test_speech_question_why_are_we_here():
    hit = _classify("Why are we here?")
    assert hit["player_input_kind"] == "speech"
    assert hit["speech_projection_allowed"] is True
    line = _project("Why are we here?", hit)
    assert "asks" in line.lower() or "fragt" in line.lower()
    assert "Why are we here?" in line


def test_speech_direct_statement_is_speech():
    hit = _classify('"That is enough."')
    assert hit["speech_projection_allowed"] is True


# ---------------------------------------------------------------------------
# Movement — speech projection NOT allowed
# ---------------------------------------------------------------------------


def test_movement_go_to_bathroom():
    hit = _classify("Go to the bathroom.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False
    assert hit["player_action_committed"] is True
    line = _project("Go to the bathroom.", hit)
    _assert_no_speech_wrapping(line, "Go to the bathroom.")
    assert "bathroom" in line.lower() or NAME in line


def test_movement_i_go_to_kitchen():
    hit = _classify("I go to the kitchen.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False
    line = _project("I go to the kitchen.", hit)
    _assert_no_speech_wrapping(line, "I go to the kitchen.")


def test_movement_sit_down():
    hit = _classify("Sit down.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Sit down.", hit)
    _assert_no_speech_wrapping(line, "Sit down.")
    assert NAME in line


def test_movement_stand_up():
    hit = _classify("Stand up.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Stand up.", hit)
    _assert_no_speech_wrapping(line, "Stand up.")
    assert NAME in line


def test_movement_i_stand_up():
    hit = _classify("I stand up.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False


def test_movement_go_to_door():
    hit = _classify("Go to the door.")
    assert hit["player_input_kind"] == "action"
    assert hit["speech_projection_allowed"] is False


# ---------------------------------------------------------------------------
# Perception — speech projection NOT allowed
# ---------------------------------------------------------------------------


def test_perception_look_out_window():
    hit = _classify("Look out the window.")
    assert hit["player_input_kind"] == "perception"
    assert hit["speech_projection_allowed"] is False
    assert hit["narrator_response_expected"] is True
    line = _project("Look out the window.", hit)
    _assert_no_speech_wrapping(line, "Look out the window.")


def test_perception_look_around_room():
    hit = _classify("Look around the room.")
    assert hit["player_input_kind"] == "perception"
    assert hit["speech_projection_allowed"] is False
    line = _project("Look around the room.", hit)
    _assert_no_speech_wrapping(line, "Look around the room.")


def test_perception_listen_at_door():
    hit = _classify("Listen at the door.")
    assert hit["player_input_kind"] == "perception"
    assert hit["speech_projection_allowed"] is False
    line = _project("Listen at the door.", hit)
    _assert_no_speech_wrapping(line, "Listen at the door.")


def test_perception_look_at_table():
    hit = _classify("Look at the table.")
    assert hit["player_input_kind"] == "perception"
    assert hit["speech_projection_allowed"] is False


def test_perception_what_do_i_see_window_question():
    hit = _classify("What do I see through the window?")
    assert hit["player_input_kind"] == "perception"
    assert hit["speech_projection_allowed"] is False
    line = _project("What do I see through the window?", hit)
    assert "asks" not in line.lower()
    assert "says" not in line.lower()


# ---------------------------------------------------------------------------
# Object interaction — speech projection NOT allowed
# ---------------------------------------------------------------------------


def test_object_take_the_glass():
    hit = _classify("Take the glass.")
    assert hit["player_input_kind"] == "object_interaction"
    assert hit["speech_projection_allowed"] is False
    assert hit["player_action_committed"] is True
    line = _project("Take the glass.", hit)
    _assert_no_speech_wrapping(line, "Take the glass.")


def test_object_put_down_the_bag():
    hit = _classify("Put down the bag.")
    assert hit["player_input_kind"] == "object_interaction"
    assert hit["speech_projection_allowed"] is False
    line = _project("Put down the bag.", hit)
    _assert_no_speech_wrapping(line, "Put down the bag.")


def test_object_open_the_door():
    hit = _classify("Open the door.")
    assert hit["player_input_kind"] == "object_interaction"
    assert hit["speech_projection_allowed"] is False
    line = _project("Open the door.", hit)
    _assert_no_speech_wrapping(line, "Open the door.")


def test_object_place_phone_on_table():
    hit = _classify("Place the phone on the table.")
    assert hit["player_input_kind"] == "object_interaction"
    assert hit["speech_projection_allowed"] is False


# ---------------------------------------------------------------------------
# Social gesture — speech projection NOT allowed
# ---------------------------------------------------------------------------


def test_social_greet():
    hit = _classify("Greet Veronique.")
    assert hit["player_input_kind"] == "social_nonverbal_action"
    assert hit["speech_projection_allowed"] is False
    assert hit["npc_response_expected"] is True
    line = _project("Greet Veronique.", hit)
    _assert_no_speech_wrapping(line, "Greet Veronique.")


def test_social_apologize():
    hit = _classify("Apologize to Michel.")
    assert hit["player_input_kind"] == "social_nonverbal_action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Apologize to Michel.", hit)
    _assert_no_speech_wrapping(line, "Apologize to Michel.")


def test_social_thank():
    hit = _classify("Thank them for the invitation.")
    assert hit["player_input_kind"] == "social_nonverbal_action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Thank them for the invitation.", hit)
    _assert_no_speech_wrapping(line, "Thank them for the invitation.")


# ---------------------------------------------------------------------------
# Physical / hostile action — speech projection NOT allowed
# ---------------------------------------------------------------------------


def test_physical_push_michel():
    hit = _classify("Push Michel.")
    assert hit["player_input_kind"] == "physical_action"
    assert hit["speech_projection_allowed"] is False
    assert hit["player_action_committed"] is True
    line = _project("Push Michel.", hit)
    _assert_no_speech_wrapping(line, "Push Michel.")


def test_physical_hit_alain():
    hit = _classify("Hit Alain.")
    assert hit["player_input_kind"] == "physical_action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Hit Alain.", hit)
    _assert_no_speech_wrapping(line, "Hit Alain.")


def test_physical_attack_someone():
    hit = _classify("Attack someone.")
    assert hit["player_input_kind"] == "physical_action"
    assert hit["speech_projection_allowed"] is False


def test_physical_throw_the_glass():
    hit = _classify("Throw the glass.")
    assert hit["player_input_kind"] == "physical_action"
    assert hit["speech_projection_allowed"] is False
    line = _project("Throw the glass.", hit)
    _assert_no_speech_wrapping(line, "Throw the glass.")


# ---------------------------------------------------------------------------
# Mixed action + speech — action frame and speech component both present
# ---------------------------------------------------------------------------


def test_mixed_stand_up_and_say():
    hit = _classify("I stand up and say: That is enough.")
    assert hit["player_input_kind"] == "mixed"
    assert hit["speech_projection_allowed"] is False  # whole input is not pure speech
    assert hit["player_action_committed"] is True
    assert hit["player_speech_committed"] is True
    line = _project("I stand up and say: That is enough.", hit)
    # Must contain the speech fragment, must not render entire raw as dialogue
    assert "That is enough" in line
    assert hit.get("captures", {}).get("speech") == "That is enough."


def test_mixed_go_to_door_and_ask():
    hit = _classify("I go to the door and ask if someone is coming.")
    assert hit["player_input_kind"] == "mixed"
    assert hit["speech_projection_allowed"] is False
    assert hit["player_action_committed"] is True
    assert hit["player_speech_committed"] is True
    line = _project("I go to the door and ask if someone is coming.", hit)
    _assert_no_speech_wrapping(line, "I go to the door and ask if someone is coming.")


# ---------------------------------------------------------------------------
# Wait / observe
# ---------------------------------------------------------------------------


def test_wait_or_observe():
    hit = _classify("I wait.")
    assert hit["player_input_kind"] == "wait_or_observe"
    assert hit["speech_projection_allowed"] is False
    line = _project("I wait.", hit)
    _assert_no_speech_wrapping(line, "I wait.")


# ---------------------------------------------------------------------------
# Unclassified inputs: no_rule_match returns unclear / speech_projection_allowed=False
# ---------------------------------------------------------------------------


def test_no_rule_match_returns_unclear_not_speech():
    hit = _classify("Do that strange thing over there.")
    assert hit["deterministic_intent_rule"] == "no_rule_match"
    assert hit["speech_projection_allowed"] is False


# ---------------------------------------------------------------------------
# speech_projection_allowed gate: non-speech inputs never produce says/asks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected_kind",
    [
        ("Go to the bathroom.", "action"),
        ("Look out the window.", "perception"),
        ("Take the glass.", "object_interaction"),
        ("Open the door.", "object_interaction"),
        ("Push Michel.", "physical_action"),
        ("Throw the glass.", "physical_action"),
        ("Sit down.", "action"),
        ("Stand up.", "action"),
        ("Greet Veronique.", "social_nonverbal_action"),
        ("Apologize to Michel.", "social_nonverbal_action"),
    ],
)
def test_non_speech_inputs_gate(raw: str, expected_kind: str) -> None:
    hit = _classify(raw)
    assert hit["player_input_kind"] == expected_kind, (
        f"{raw!r}: expected {expected_kind!r}, got {hit['player_input_kind']!r}"
    )
    assert hit["speech_projection_allowed"] is False, (
        f"{raw!r}: speech_projection_allowed should be False for {expected_kind}"
    )
    line = _project(raw, hit)
    assert 'says: "' not in line, f"Non-speech rendered as speech: {line!r} for {raw!r}"
    assert 'asks: "' not in line, f"Non-speech rendered as question: {line!r} for {raw!r}"
