"""Thin pre-AI structural preview of natural-language operator input (Task 1A).

Produces a bounded, inspectable envelope for diagnostics and AdapterRequest attachment.
This is not authoritative committed runtime truth; guards and validators remain unchanged.

Optional re-export: ``interpret_player_input`` from ``story_runtime_core`` for callers that
still use the shared core contract (e.g. API routes, improvement sandbox).
"""

from __future__ import annotations

import re
from enum import Enum
from pydantic import BaseModel, Field

try:
    from enum import StrEnum
except ImportError:
    # Python 3.10 compatibility
    class StrEnum(str, Enum):
        pass

# Precautionary compatibility for existing backend import sites.
from story_runtime_core import interpret_player_input

PARSER_VERSION = "1a/2"

_QUOTED_DOUBLE = re.compile(r'"([^"]*)"')
_QUOTED_SINGLE = re.compile(r"'([^']*)'")
_SILENCE_EXPLICIT = re.compile(
    r"^\s*(?:\.\.\.|…)\s*$|^\s*\(?\s*silence\s*\)?\s*$",
    re.IGNORECASE,
)


class InputPrimaryMode(StrEnum):
    """High-level classification of operator text before the AI adapter call."""

    DIALOGUE = "dialogue"
    ACTION = "action"
    REACTION = "reaction"
    MIXED = "mixed"
    SILENCE = "silence"
    UNKNOWN = "unknown"


class InputInterpretationEnvelope(BaseModel):
    """Bounded diagnostic interpretation of operator natural-language input."""

    raw_text: str
    normalized_text: str
    is_empty: bool
    primary_mode: InputPrimaryMode
    secondary_modes: list[InputPrimaryMode] = Field(default_factory=list)
    spoken_text_segments: list[str] = Field(default_factory=list)
    action_cues: list[str] = Field(default_factory=list)
    reaction_cues: list[str] = Field(default_factory=list)
    ambiguity_markers: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    parser_version: str = PARSER_VERSION


def _normalize_for_match(text: str) -> str:
    return " ".join(text.split())


def _tokens_with_alnum(lowered: str) -> list[str]:
    return [t for t in re.split(r"\s+", lowered.strip()) if any(c.isalnum() for c in t)]


def _extract_spoken_segments(text: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for pattern in (_QUOTED_DOUBLE, _QUOTED_SINGLE):
        for m in pattern.finditer(text):
            inner = m.group(1).strip()
            if inner and inner not in seen:
                seen.add(inner)
                out.append(inner)
    return out


def _find_reaction_cues(lowered: str) -> list[str]:
    del lowered
    return []


def _find_action_cues(lowered: str, original: str) -> list[str]:
    del lowered, original
    return []


def _envelope_empty_silence(raw_text: str) -> InputInterpretationEnvelope:
    return InputInterpretationEnvelope(
        raw_text=raw_text,
        normalized_text="",
        is_empty=True,
        primary_mode=InputPrimaryMode.SILENCE,
        secondary_modes=[],
        spoken_text_segments=[],
        action_cues=[],
        reaction_cues=[],
        ambiguity_markers=["empty_input"],
        confidence=1.0,
        rationale="Empty or whitespace-only input classified as silence.",
        parser_version=PARSER_VERSION,
    )


def _envelope_punctuation_silence(raw_text: str, collapsed: str) -> InputInterpretationEnvelope:
    return InputInterpretationEnvelope(
        raw_text=raw_text,
        normalized_text=collapsed,
        is_empty=False,
        primary_mode=InputPrimaryMode.SILENCE,
        secondary_modes=[],
        spoken_text_segments=[],
        action_cues=[],
        reaction_cues=[],
        ambiguity_markers=["punctuation_only"],
        confidence=0.95,
        rationale="No alphanumeric tokens; treated as silence-like input.",
        parser_version=PARSER_VERSION,
    )


def _envelope_explicit_silence(raw_text: str, collapsed: str) -> InputInterpretationEnvelope:
    return InputInterpretationEnvelope(
        raw_text=raw_text,
        normalized_text=collapsed,
        is_empty=False,
        primary_mode=InputPrimaryMode.SILENCE,
        secondary_modes=[],
        spoken_text_segments=[],
        action_cues=[],
        reaction_cues=[],
        ambiguity_markers=["explicit_silence_marker"],
        confidence=0.9,
        rationale="Explicit silence or ellipsis-only pattern detected.",
        parser_version=PARSER_VERSION,
    )


def _mode_signals_from_cues(
    lowered: str,
    normalized_text: str,
) -> tuple[list[str], list[str], list[str], bool, bool, bool, bool, bool]:
    spoken = _extract_spoken_segments(normalized_text)
    reaction_cues = _find_reaction_cues(lowered)
    action_cues = _find_action_cues(lowered, normalized_text)
    has_quotes = len(spoken) > 0
    has_speech_verb = False
    dialogue_signal = has_quotes
    reaction_signal = len(reaction_cues) > 0
    action_signal = len(action_cues) > 0
    return (
        spoken,
        action_cues,
        reaction_cues,
        has_quotes,
        has_speech_verb,
        dialogue_signal,
        reaction_signal,
        action_signal,
    )


def _classify_primary_and_meta(
    *,
    tokens: list[str],
    normalized_text: str,
    has_quotes: bool,
    has_speech_verb: bool,
    dialogue_signal: bool,
    reaction_signal: bool,
    action_signal: bool,
) -> tuple[InputPrimaryMode, list[InputPrimaryMode], list[str], float, str]:
    ambiguity: list[str] = []
    secondary: list[InputPrimaryMode] = []

    if len(tokens) <= 2 and len(normalized_text) <= 16:
        ambiguity.append("short_utterance")

    modes_active: list[InputPrimaryMode] = []
    if dialogue_signal:
        modes_active.append(InputPrimaryMode.DIALOGUE)
    if reaction_signal:
        modes_active.append(InputPrimaryMode.REACTION)
    if action_signal:
        modes_active.append(InputPrimaryMode.ACTION)

    if len(modes_active) >= 2:
        primary = InputPrimaryMode.MIXED
        secondary = list(modes_active)
        confidence = 0.72
        if ambiguity:
            confidence = min(confidence, 0.55)
        rationale = (
            f"Multiple mode signals (dialogue={dialogue_signal}, reaction={reaction_signal}, "
            f"action={action_signal}); classified as mixed."
        )
        return primary, secondary, ambiguity, confidence, rationale

    if dialogue_signal:
        primary = InputPrimaryMode.DIALOGUE
        confidence = 0.68
        if ambiguity:
            ambiguity.append("dialogue_possible_acknowledgment")
            confidence = min(confidence, 0.48)
            primary = InputPrimaryMode.UNKNOWN
            secondary = [InputPrimaryMode.DIALOGUE]
            rationale = (
                "Dialogue-like signal on a very short utterance; conservative unknown with "
                "dialogue secondary."
            )
        else:
            rationale = "Quoted speech provides a structural dialogue preview."
        return primary, secondary, ambiguity, confidence, rationale

    ambiguity.append("semantic_ai_resolution_required")
    return (
        InputPrimaryMode.UNKNOWN,
        [],
        ambiguity,
        0.35,
        "No structural dialogue marker; authoritative meaning is deferred to semantic AI resolution.",
    )


def interpret_operator_input(text: str) -> InputInterpretationEnvelope:
    """Return a bounded structural preview without language or verb maps."""
    raw_text = text if text is not None else ""
    normalized_text = raw_text.strip()
    lowered = normalized_text.lower()
    collapsed = _normalize_for_match(normalized_text)

    if not normalized_text:
        return _envelope_empty_silence(raw_text)

    tokens = _tokens_with_alnum(lowered)
    if not tokens:
        return _envelope_punctuation_silence(raw_text, collapsed)

    if _SILENCE_EXPLICIT.match(normalized_text):
        return _envelope_explicit_silence(raw_text, collapsed)

    (
        spoken,
        action_cues,
        reaction_cues,
        has_quotes,
        has_speech_verb,
        dialogue_signal,
        reaction_signal,
        action_signal,
    ) = _mode_signals_from_cues(lowered, normalized_text)

    primary, secondary, ambiguity, confidence, rationale = _classify_primary_and_meta(
        tokens=tokens,
        normalized_text=normalized_text,
        has_quotes=has_quotes,
        has_speech_verb=has_speech_verb,
        dialogue_signal=dialogue_signal,
        reaction_signal=reaction_signal,
        action_signal=action_signal,
    )

    if not ambiguity and primary == InputPrimaryMode.UNKNOWN:
        ambiguity.append("low_signal")

    return InputInterpretationEnvelope(
        raw_text=raw_text,
        normalized_text=collapsed,
        is_empty=False,
        primary_mode=primary,
        secondary_modes=secondary,
        spoken_text_segments=spoken,
        action_cues=action_cues,
        reaction_cues=reaction_cues,
        ambiguity_markers=ambiguity,
        confidence=round(min(max(confidence, 0.0), 1.0), 3),
        rationale=rationale,
        parser_version=PARSER_VERSION,
    )


__all__ = [
    "InputInterpretationEnvelope",
    "InputPrimaryMode",
    "interpret_operator_input",
    "interpret_player_input",
    "PARSER_VERSION",
]
