from story_runtime_core.input_interpreter import interpret_player_input
from story_runtime_core.models import InterpretedInputKind


def test_interpreter_handles_explicit_command():
    result = interpret_player_input("/roll d20")
    assert result.kind == InterpretedInputKind.EXPLICIT_COMMAND
    assert result.command_name == "roll"


def test_interpreter_handles_meta_input():
    result = interpret_player_input("ooc: let's pause here")
    assert result.kind == InterpretedInputKind.META


def test_interpreter_handles_mixed_input():
    result = interpret_player_input('I say "sorry" and open the door')
    assert result.kind == InterpretedInputKind.MIXED


def test_interpreter_handles_pure_dialogue():
    result = interpret_player_input('I say "we should calm down"')
    assert result.kind == InterpretedInputKind.SPEECH


def test_interpreter_handles_pure_action():
    result = interpret_player_input("open the chest")
    assert result.kind == InterpretedInputKind.ACTION


def test_interpreter_handles_reaction_input():
    result = interpret_player_input("wow")
    assert result.kind == InterpretedInputKind.REACTION


def test_interpreter_handles_ambiguous_input():
    result = interpret_player_input("...")
    assert result.kind == InterpretedInputKind.AMBIGUOUS
    assert result.ambiguity is not None


def test_interpreter_handles_intent_only_input():
    result = interpret_player_input("escape now")
    assert result.kind == InterpretedInputKind.INTENT_ONLY
