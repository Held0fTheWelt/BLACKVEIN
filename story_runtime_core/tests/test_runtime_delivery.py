import pytest

from story_runtime_core import interpret_player_input, natural_input_to_room_command
from story_runtime_core.models import InterpretedInputKind
from story_runtime_core.runtime_delivery import extract_spoken_text_for_delivery


def test_natural_input_maps_speech_to_say():
    interp = interpret_player_input('I say "hello there"')
    cmd = natural_input_to_room_command(interp, 'I say "hello there"')
    assert cmd == {"action": "say", "text": "hello there"}


def test_natural_input_maps_conflicting_mixed_to_emote_channel():
    interp = interpret_player_input("open door wow")
    cmd = natural_input_to_room_command(interp, "open door wow")
    assert cmd["action"] == "emote"
    assert cmd["text"] == "open door wow"


def test_natural_input_rejects_command_kind():
    interp = interpret_player_input("/look")
    with pytest.raises(ValueError):
        natural_input_to_room_command(interp, "/look")


def test_extract_spoken_text_prefers_first_quoted_span():
    assert extract_spoken_text_for_delivery('X "first" and "second"') == "first"


def test_extract_spoken_text_parses_say_clause():
    assert extract_spoken_text_for_delivery("I say: pack your things.") == "pack your things."


def test_extract_spoken_text_tell_prefix_uses_say_pattern_capture():
    # ``re.search`` hits ``\\btell\\b`` before the line-20 ``tell him`` ``re.match`` runs, so the
    # captured tail includes the indirect-object pronoun (current helper behavior).
    assert extract_spoken_text_for_delivery("Tell him the meeting is off.") == "him the meeting is off."


def test_extract_spoken_text_falls_back_to_whole_string():
    assert extract_spoken_text_for_delivery("   just thinking aloud.  ") == "just thinking aloud."
