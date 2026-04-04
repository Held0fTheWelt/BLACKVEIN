"""Unit tests for deterministic operator input interpretation (Task 1A)."""

from __future__ import annotations

from app.runtime.input_interpreter import (
    InputPrimaryMode,
    interpret_operator_input,
)


def test_pure_dialogue_quoted_and_speech_verb():
    """Quoted speech plus speech verb → dialogue."""
    text = "I say, 'That is enough.'"
    env = interpret_operator_input(text)
    assert env.primary_mode == InputPrimaryMode.DIALOGUE
    assert "That is enough." in env.spoken_text_segments or any(
        "enough" in s.lower() for s in env.spoken_text_segments
    )
    assert env.confidence >= 0.6


def test_pure_action_first_person():
    """First-person physical action → action."""
    text = "I step toward Alain and take the phone."
    env = interpret_operator_input(text)
    assert env.primary_mode == InputPrimaryMode.ACTION
    assert env.action_cues
    assert env.confidence >= 0.5


def test_pure_reaction_flinch():
    """Physical/emotional reaction cues → reaction."""
    text = "I flinch and look away."
    env = interpret_operator_input(text)
    assert env.primary_mode == InputPrimaryMode.REACTION
    assert env.reaction_cues


def test_pure_reaction_sigh():
    text = "I sigh."
    env = interpret_operator_input(text)
    assert env.primary_mode == InputPrimaryMode.REACTION


def test_mixed_dialogue_reaction_action():
    text = "I sigh, say 'fine', and sit down."
    env = interpret_operator_input(text)
    assert env.primary_mode == InputPrimaryMode.MIXED
    assert InputPrimaryMode.DIALOGUE in env.secondary_modes or env.primary_mode == InputPrimaryMode.MIXED


def test_ambiguous_short_utterance_fine():
    """Single-word acknowledgement must not be overclassified."""
    env = interpret_operator_input("Fine.")
    assert env.primary_mode == InputPrimaryMode.UNKNOWN
    assert "short_utterance" in env.ambiguity_markers
    assert env.confidence <= 0.5


def test_empty_and_whitespace_silence():
    assert interpret_operator_input("").primary_mode == InputPrimaryMode.SILENCE
    assert interpret_operator_input("   ").primary_mode == InputPrimaryMode.SILENCE


def test_punctuation_only_silence():
    env = interpret_operator_input("...")
    assert env.primary_mode == InputPrimaryMode.SILENCE


def test_parser_version_stable():
    env = interpret_operator_input("test")
    assert env.parser_version == "1a/1"


def test_raw_text_preserved():
    raw = "  hello  "
    env = interpret_operator_input(raw)
    assert env.raw_text == raw
    assert env.normalized_text == "hello"
