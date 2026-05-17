from story_runtime_core.input_interpreter import interpret_player_input
from story_runtime_core.models import InterpretedInputKind, RuntimeDeliveryHint
from story_runtime_core.player_input_intent_contract import (
    default_commit_flags_for_player_input_kind,
    is_non_story_control_player_input_kind,
)


def test_interpreter_handles_explicit_command():
    result = interpret_player_input("/roll d20")
    assert result.kind == InterpretedInputKind.EXPLICIT_COMMAND
    assert result.command_name == "roll"
    assert result.runtime_delivery_hint is None


def test_interpreter_handles_meta_input():
    result = interpret_player_input("ooc: let's pause here")
    assert result.kind == InterpretedInputKind.META
    assert result.runtime_delivery_hint is None


def test_meta_intent_defaults_are_non_story_control():
    result = interpret_player_input("meta: pause")
    flags = default_commit_flags_for_player_input_kind(result.kind.value)
    assert is_non_story_control_player_input_kind(result.kind.value) is True
    assert result.selected_handling_path == "meta"
    assert flags == {
        "player_action_committed": False,
        "player_speech_committed": False,
        "narrator_response_expected": False,
        "npc_response_expected": False,
    }


def test_interpreter_handles_out_of_character_meta_prefix():
    result = interpret_player_input("out of character: pause")
    assert result.kind == InterpretedInputKind.META
    assert result.selected_handling_path == "meta"
    assert result.runtime_delivery_hint is None


def test_interpreter_handles_quoted_dialogue_structurally():
    result = interpret_player_input('I say "we should calm down"')
    assert result.kind == InterpretedInputKind.SPEECH
    assert result.intent == "quoted_dialogue"
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.SAY


def test_unquoted_action_like_text_requires_ai_semantic_resolution():
    result = interpret_player_input("open the chest")
    assert result.kind == InterpretedInputKind.AMBIGUOUS
    assert result.ambiguity == "semantic_ai_resolution_required"
    assert result.intent == "semantic_resolution_required"
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.NARRATIVE_BODY


def test_unquoted_reaction_like_text_requires_ai_semantic_resolution():
    result = interpret_player_input("wow")
    assert result.kind == InterpretedInputKind.AMBIGUOUS
    assert result.ambiguity == "semantic_ai_resolution_required"


def test_interpreter_handles_punctuation_only_as_silence():
    result = interpret_player_input("...")
    assert result.kind == InterpretedInputKind.AMBIGUOUS
    assert result.ambiguity == "no_lexical_tokens"
    assert result.intent == "withheld_response_or_silence"
    assert result.runtime_delivery_hint == RuntimeDeliveryHint.NARRATIVE_BODY


def test_short_unquoted_lines_do_not_default_to_speech():
    result = interpret_player_input("Das reicht.")
    assert result.kind == InterpretedInputKind.AMBIGUOUS
    assert result.ambiguity == "semantic_ai_resolution_required"


def test_unquoted_questions_do_not_use_language_specific_question_maps():
    result = interpret_player_input("Wieso sind wir hier?")
    assert result.kind == InterpretedInputKind.AMBIGUOUS
    assert result.ambiguity == "semantic_ai_resolution_required"
