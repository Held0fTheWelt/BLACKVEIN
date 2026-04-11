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
    """Chained clause: reaction + quoted speech + chained sit (Task 1C-R)."""
    text = "I sigh, say 'fine', and sit down."
    env = interpret_operator_input(text)
    assert env.primary_mode == InputPrimaryMode.MIXED
    assert InputPrimaryMode.DIALOGUE in env.secondary_modes or env.primary_mode == InputPrimaryMode.MIXED
    assert any("sigh" in r for r in env.reaction_cues)
    assert "fine" in env.spoken_text_segments
    assert any(c == "sit down" or c.startswith("sit") for c in env.action_cues)


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
    assert env.parser_version == "1a/2"


def test_raw_text_preserved():
    raw = "  hello  "
    env = interpret_operator_input(raw)
    assert env.raw_text == raw
    assert env.normalized_text == "hello"


def test_chained_actions_step_take_sit():
    """Multiple chained verbs after commas and *and* (Task 1C-R)."""
    env = interpret_operator_input("I step closer, take the phone, and sit down.")
    assert env.primary_mode in (InputPrimaryMode.ACTION, InputPrimaryMode.MIXED)
    cues = env.action_cues
    assert any("step" in c for c in cues)
    assert any("take" in c for c in cues)
    assert any(c == "sit down" or c.startswith("sit") for c in cues)


def test_dialogue_lead_in_with_chained_step_back():
    """Leading acknowledgement plus *I say* and chained *step back* stays classified (Task 1C-R)."""
    env = interpret_operator_input("Fine, I say, and step back.")
    assert env.primary_mode != InputPrimaryMode.UNKNOWN
    assert any("step back" in c or c == "step back" for c in env.action_cues)


def test_reaction_nod_and_chained_walk():
    """Reaction cue plus *and walk* yields mixed with both cue types (Task 1C-R)."""
    env = interpret_operator_input("I nod and walk to the door.")
    assert env.primary_mode == InputPrimaryMode.MIXED
    assert any("nod" in r for r in env.reaction_cues)
    assert any("walk" in a for a in env.action_cues)
