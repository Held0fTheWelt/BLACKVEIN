"""Deterministic pre-AI interpretation of natural-language operator input (Task 1A).

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
_SPEECH_LEAD_IN = re.compile(
    r"(?:^|\b)(?:i\s+)?(?:say|says|said|tell|tells|told|ask|asks|asked|whisper|whispers|"
    r"shout|shouts|mutter|mutters|reply|replies|answered|answer|answers)\b",
    re.IGNORECASE,
)
_SPEECH_TELL_THEM = re.compile(r"\b(?:tell|ask)\s+(?:him|her|them)\b", re.IGNORECASE)
_ACTION_I = re.compile(
    r"\bi\s+(?:step|steps|walk|walks|move|moves|take|takes|grab|grabs|reach|reaches|"
    r"open|opens|close|closes|pick|picks|put|puts|turn|turns|run|runs|sit|sits|stand|stands|"
    r"enter|leaves?|leave|pull|pulls|push|pushes|give|gives|hand|hands|approach|approaches)\b",
    re.IGNORECASE,
)
_IMPERATIVE_LEAD = re.compile(
    r"^(?:step|walk|move|take|grab|reach|open|close|pick|put|turn|run|sit|stand|enter|"
    r"leave|pull|push|give|hand|approach|go|get|drop|use)\b",
    re.IGNORECASE,
)
# Chained physical actions after comma / "and" / "then" (same verb whitelist as _ACTION_I;
# two-word phrases first so "sit down" wins over bare "sit").
_ACTION_CHAIN_TAIL = (
    r"sit down|stand up|look around|step back|move away|"
    r"step|steps|walk|walks|move|moves|take|takes|grab|grabs|reach|reaches|"
    r"open|opens|close|closes|pick|picks|put|puts|turn|turns|run|runs|sit|sits|stand|stands|"
    r"enter|leave|leaves|pull|pulls|push|pushes|give|gives|hand|hands|approach|approaches"
)
_CHAINED_ACTION = re.compile(
    rf"(?:,|\band\b|\bthen\b)\s+({_ACTION_CHAIN_TAIL})\b",
    re.IGNORECASE,
)
_REACTION = re.compile(
    r"\b(?:flinch(?:es)?|sigh(?:s)?|pause(?:s)?|hesitate(?:s)?|recoil(?:s)?|stare(?:s)?|"
    r"shrug(?:s)?|nod(?:s)?|gasp(?:s)?|wince(?:s)?|tremble(?:s)?|shudder(?:s)?|"
    r"look(?:s)?\s+away|freeze(?:s)?|swallow(?:s)?)\b",
    re.IGNORECASE,
)
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
    cues: list[str] = []
    for m in _REACTION.finditer(lowered):
        cues.append(m.group(0).strip().lower())
    return cues


def _find_action_cues(lowered: str, original: str) -> list[str]:
    """Collect first-person, imperative-leading, and chained action cues (deterministic, deduped)."""
    seen: set[str] = set()
    cues: list[str] = []

    def add(cue: str) -> None:
        c = cue.strip().lower()
        if c and c not in seen:
            seen.add(c)
            cues.append(c)

    for m in _ACTION_I.finditer(lowered):
        add(m.group(0))
    if _IMPERATIVE_LEAD.match(original.strip()):
        first = original.strip().split(None, 1)[0].lower()
        add(first)
    for m in _CHAINED_ACTION.finditer(lowered):
        add(m.group(1))
    return cues


def interpret_operator_input(text: str) -> InputInterpretationEnvelope:
    """Classify and extract bounded cues from operator text using deterministic rules only."""
    raw_text = text if text is not None else ""
    normalized_text = raw_text.strip()
    lowered = normalized_text.lower()
    collapsed = _normalize_for_match(normalized_text)

    if not normalized_text:
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

    tokens = _tokens_with_alnum(lowered)
    if not tokens:
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

    if _SILENCE_EXPLICIT.match(normalized_text):
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

    spoken = _extract_spoken_segments(normalized_text)
    reaction_cues = _find_reaction_cues(lowered)
    action_cues = _find_action_cues(lowered, normalized_text)

    has_quotes = len(spoken) > 0
    has_speech_verb = bool(_SPEECH_LEAD_IN.search(lowered) or _SPEECH_TELL_THEM.search(lowered))
    dialogue_signal = has_quotes or has_speech_verb

    reaction_signal = len(reaction_cues) > 0
    action_signal = len(action_cues) > 0

    # Scores in [0, 1] for disambiguation (deterministic).
    d_score = 0.0
    if has_quotes:
        d_score += 0.55
    if has_speech_verb:
        d_score += 0.45
    d_score = min(d_score, 1.0)

    r_score = min(0.35 + 0.3 * len(reaction_cues), 1.0)
    a_score = min(0.35 + 0.25 * len(action_cues), 1.0)

    modes_active = []
    if dialogue_signal:
        modes_active.append(InputPrimaryMode.DIALOGUE)
    if reaction_signal:
        modes_active.append(InputPrimaryMode.REACTION)
    if action_signal:
        modes_active.append(InputPrimaryMode.ACTION)

    ambiguity: list[str] = []
    secondary: list[InputPrimaryMode] = []

    # Short utterance ambiguity (e.g. "Fine.")
    if len(tokens) <= 2 and len(normalized_text) <= 16:
        ambiguity.append("short_utterance")

    if len(modes_active) >= 2:
        primary = InputPrimaryMode.MIXED
        secondary = [m for m in modes_active]
        confidence = 0.72
        if ambiguity:
            confidence = min(confidence, 0.55)
        rationale = (
            f"Multiple mode signals (dialogue={dialogue_signal}, reaction={reaction_signal}, "
            f"action={action_signal}); classified as mixed."
        )
    elif dialogue_signal:
        primary = InputPrimaryMode.DIALOGUE
        confidence = 0.82 if has_quotes and has_speech_verb else 0.68 if has_quotes else 0.62
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
            rationale = "Quoted speech and/or speech-act verbs indicate dialogue."
    elif reaction_signal and not action_signal:
        primary = InputPrimaryMode.REACTION
        confidence = 0.78 if not ambiguity else 0.5
        rationale = "Reaction cues (e.g. sigh, flinch) without competing action phrasing."
    elif action_signal and not dialogue_signal:
        primary = InputPrimaryMode.ACTION
        confidence = 0.78 if not ambiguity else 0.52
        rationale = "First-person or imperative physical action cues detected."
    elif reaction_signal and action_signal:
        primary = InputPrimaryMode.MIXED
        secondary = [InputPrimaryMode.REACTION, InputPrimaryMode.ACTION]
        confidence = 0.7
        rationale = "Both reaction and action cues present."
    else:
        primary = InputPrimaryMode.UNKNOWN
        confidence = 0.35
        ambiguity.append("no_strong_mode_pattern")
        rationale = "No reliable dialogue, action, or reaction pattern; classified as unknown."

    # Refine: single-token short without signals stays unknown
    if primary == InputPrimaryMode.UNKNOWN and not secondary and dialogue_signal:
        pass  # already handled above

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
