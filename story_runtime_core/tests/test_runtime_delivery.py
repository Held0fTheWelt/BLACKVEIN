import pytest

from story_runtime_core import interpret_player_input, natural_input_to_room_command
from story_runtime_core.models import InterpretedInputKind


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
