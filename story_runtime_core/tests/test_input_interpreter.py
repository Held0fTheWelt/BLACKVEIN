from story_runtime_core.input_interpreter import interpret_player_input
from story_runtime_core.models import InterpretedInputKind, RuntimeDeliveryHint


def test_interpreter_handles_explicit_command():
    result = interpret_player_input("/roll d20")
    assert result.kind == InterpretedInputKind.EXPLICIT_COMMAND
    assert result.command_name == "roll"
    assert result.runtime_delivery_hint is None


def test_interpreter_handles_meta_input():
    result = interpret_player_input("ooc: let's pause here")
    assert result.kind == InterpretedInputKind.META
    assert result.runtime_delivery_hint is None


def test_interpreter_handles_mixed_input():
    result = interpret_player_input('I say "sorry" and open the door')
    assert result.kind == InterpretedInputKind.MIXED
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.SAY


def test_interpreter_handles_pure_dialogue():
    result = interpret_player_input('I say "we should calm down"')
    assert result.kind == InterpretedInputKind.SPEECH
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.SAY


def test_interpreter_handles_pure_action():
    result = interpret_player_input("open the chest")
    assert result.kind == InterpretedInputKind.ACTION
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.EMOTE


def test_interpreter_handles_reaction_input():
    result = interpret_player_input("wow")
    assert result.kind == InterpretedInputKind.REACTION
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.NARRATIVE_BODY


def test_interpreter_handles_ambiguous_input():
    result = interpret_player_input("...")
    assert result.kind == InterpretedInputKind.AMBIGUOUS
    assert result.ambiguity is not None
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.NARRATIVE_BODY


def test_interpreter_handles_intent_only_input():
    result = interpret_player_input("escape now")
    assert result.kind == InterpretedInputKind.INTENT_ONLY
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.EMOTE


def test_interpreter_tell_him_without_quotes_is_speech():
    result = interpret_player_input("Tell him I am not leaving.")
    assert result.kind == InterpretedInputKind.SPEECH
    assert result.intent == "dialogue"
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.SAY


def test_interpreter_action_plus_reaction_is_mixed_with_ambiguity():
    result = interpret_player_input("open door wow")
    assert result.kind == InterpretedInputKind.MIXED
    assert result.ambiguity == "conflicting_action_reaction"
    assert result.confidence < 0.62
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.NARRATIVE_BODY


def test_interpreter_withhold_silence_is_intent_only():
    result = interpret_player_input("I do not answer. I just stare at him.")
    assert result.kind == InterpretedInputKind.INTENT_ONLY
    assert result.intent == "withheld_response_or_silence"
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.EMOTE


def test_interpreter_i_ask_pattern_is_speech():
    result = interpret_player_input("I ask if we can pause.")
    assert result.kind == InterpretedInputKind.SPEECH


def test_interpreter_mixed_with_conflicting_signals_uses_narrative_delivery():
    result = interpret_player_input("move wow")
    assert result.kind == InterpretedInputKind.MIXED
    assert result.ambiguity == "conflicting_action_reaction"
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.NARRATIVE_BODY
