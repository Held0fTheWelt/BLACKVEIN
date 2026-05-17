"""Unit tests for the thin operator input preview (Task 1A)."""

from __future__ import annotations

from app.runtime.input_interpreter import (
    InputPrimaryMode,
    interpret_operator_input,
)


def test_quoted_dialogue_is_structural_preview():
    env = interpret_operator_input("I say, 'That is enough.'")
    assert env.primary_mode == InputPrimaryMode.DIALOGUE
    assert any("enough" in s.lower() for s in env.spoken_text_segments)
    assert env.confidence >= 0.45


def test_action_like_text_requires_semantic_ai_resolution():
    env = interpret_operator_input("I step toward Alain and take the phone.")
    assert env.primary_mode == InputPrimaryMode.UNKNOWN
    assert env.action_cues == []
    assert "semantic_ai_resolution_required" in env.ambiguity_markers


def test_reaction_like_text_requires_semantic_ai_resolution():
    env = interpret_operator_input("I flinch and look away.")
    assert env.primary_mode == InputPrimaryMode.UNKNOWN
    assert env.reaction_cues == []
    assert "semantic_ai_resolution_required" in env.ambiguity_markers


def test_ambiguous_short_utterance_fine():
    env = interpret_operator_input("Fine.")
    assert env.primary_mode == InputPrimaryMode.UNKNOWN
    assert "short_utterance" in env.ambiguity_markers
    assert "semantic_ai_resolution_required" in env.ambiguity_markers
    assert env.confidence <= 0.5


def test_empty_and_whitespace_silence():
    assert interpret_operator_input("").primary_mode == InputPrimaryMode.SILENCE
    assert interpret_operator_input("   ").primary_mode == InputPrimaryMode.SILENCE


def test_punctuation_only_silence():
    env = interpret_operator_input("...")
    assert env.primary_mode == InputPrimaryMode.SILENCE


def test_withheld_answer_text_is_not_phrase_mapped_to_silence():
    env = interpret_operator_input("I do not answer. I just stare at him.")
    assert env.primary_mode == InputPrimaryMode.UNKNOWN
    assert env.secondary_modes == []
    assert env.spoken_text_segments == []


def test_parser_version_stable():
    env = interpret_operator_input("test")
    assert env.parser_version == "1a/2"


def test_raw_text_preserved():
    raw = "  hello  "
    env = interpret_operator_input(raw)
    assert env.raw_text == raw
    assert env.normalized_text == "hello"
