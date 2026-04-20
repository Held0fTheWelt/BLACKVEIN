from __future__ import annotations

import re

from .models import InterpretedInputKind, PlayerInputInterpretation, RuntimeDeliveryHint


META_PREFIXES = ("ooc:", "meta:", "out of character:")
COMMAND_PREFIXES = ("/", "!")
# Short interjections; reaction branch only applies when utterance is short (see has_reaction_signal).
REACTION_TOKENS = ("wow", "uh", "huh", "oh", "hmm", "what?", "damn", "ugh", "gasp", "sigh")
ACTION_VERBS = ("go", "take", "open", "look", "attack", "talk", "move", "inspect", "use")
SPEECH_MARKERS = ('"', "say ", "ask ", "tell ")
# NL dialogue without quotes: "Tell him ...", "I ask if ..."
_SPEECH_LEAD_IN = re.compile(
    r"^(?:i\s+(?:tell|ask|say|said|whisper|shout)\s+|\b(?:tell|ask)\s+(?:him|her|them)\s+)",
    re.IGNORECASE,
)
# Silence / refusal — still narrative play, not "unknown noise".
_WITHHOLD_PATTERN = re.compile(
    r"\b(?:do\s+not|don'?t)\s+answer\b|\b(?:stay|remain)\s+silent\b|\bjust\s+stare\b|\bwithout\s+say(?:ing)?\b",
    re.IGNORECASE,
)


def _tokens(lowered: str) -> list[str]:
    return [token for token in lowered.replace(",", " ").split() if token]


def _has_action_signal(tokens: list[str]) -> bool:
    return any(token in ACTION_VERBS for token in tokens)


def _has_speech_signal(lowered: str) -> bool:
    if any(marker in lowered for marker in SPEECH_MARKERS):
        return True
    return bool(_SPEECH_LEAD_IN.search(lowered.strip()))


def _has_reaction_signal(tokens: list[str]) -> bool:
    if not tokens:
        return False
    if len(tokens) > 4:
        return False
    return any(token in REACTION_TOKENS for token in tokens)


def _has_withhold_signal(lowered: str) -> bool:
    return bool(_WITHHOLD_PATTERN.search(lowered))


def _delivery_for_nl(
    *,
    kind: InterpretedInputKind,
    confidence: float,
    ambiguity: str | None,
    lowered: str,
) -> RuntimeDeliveryHint:
    """Conservative mapping: SAY only when dialogue is structurally extractable and confidence is sufficient."""
    if kind in (InterpretedInputKind.EXPLICIT_COMMAND, InterpretedInputKind.META):
        return RuntimeDeliveryHint.EMOTE
    if kind is InterpretedInputKind.SPEECH and confidence >= 0.55:
        return RuntimeDeliveryHint.SAY
    if kind is InterpretedInputKind.MIXED:
        if ambiguity == "conflicting_action_reaction" or confidence < 0.62:
            return RuntimeDeliveryHint.NARRATIVE_BODY
        if _has_speech_signal(lowered) and confidence >= 0.55:
            return RuntimeDeliveryHint.SAY
        return RuntimeDeliveryHint.NARRATIVE_BODY
    if kind is InterpretedInputKind.AMBIGUOUS and confidence < 0.52:
        return RuntimeDeliveryHint.NARRATIVE_BODY
    if kind is InterpretedInputKind.REACTION:
        return RuntimeDeliveryHint.NARRATIVE_BODY
    return RuntimeDeliveryHint.EMOTE


def interpret_player_input(raw_text: str) -> PlayerInputInterpretation:
    text = (raw_text or "").strip()
    lowered = text.lower()
    tokens = _tokens(lowered)

    if not text:
        return PlayerInputInterpretation(
            raw_text=raw_text,
            normalized_text="",
            kind=InterpretedInputKind.AMBIGUOUS,
            confidence=0.0,
            ambiguity="empty_input",
            intent=None,
            selected_handling_path="nl_runtime",
            runtime_delivery_hint=RuntimeDeliveryHint.NARRATIVE_BODY,
        )
    if not tokens or all(not any(ch.isalnum() for ch in token) for token in tokens):
        return PlayerInputInterpretation(
            raw_text=raw_text,
            normalized_text=text,
            kind=InterpretedInputKind.AMBIGUOUS,
            confidence=0.15,
            ambiguity="no_lexical_tokens",
            intent="uncertain",
            selected_handling_path="nl_runtime",
            runtime_delivery_hint=RuntimeDeliveryHint.NARRATIVE_BODY,
        )

    if lowered.startswith(META_PREFIXES):
        return PlayerInputInterpretation(
            raw_text=raw_text,
            normalized_text=text,
            kind=InterpretedInputKind.META,
            confidence=0.98,
            intent="meta_instruction",
            selected_handling_path="meta",
            runtime_delivery_hint=None,
        )

    if text.startswith(COMMAND_PREFIXES):
        parts = text[1:].split()
        command = parts[0].lower() if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        return PlayerInputInterpretation(
            raw_text=raw_text,
            normalized_text=text,
            kind=InterpretedInputKind.EXPLICIT_COMMAND,
            confidence=0.99,
            intent="explicit_command",
            command_name=command or None,
            command_args=args,
            selected_handling_path="command",
            runtime_delivery_hint=None,
        )

    has_action = _has_action_signal(tokens)
    has_speech = _has_speech_signal(lowered)
    has_reaction = _has_reaction_signal(tokens)
    has_withhold = _has_withhold_signal(lowered)

    # Order: withhold/silence beats generic ambiguity when the text clearly describes non-dialogue play.
    if has_withhold and not has_speech:
        kind = InterpretedInputKind.INTENT_ONLY
        confidence = 0.71
        intent = "withheld_response_or_silence"
        ambiguity = None
    elif has_action and has_reaction and not has_speech:
        # e.g. "go there huh" — action and interjection without quoted speech; do not pretend clean "action" only.
        kind = InterpretedInputKind.MIXED
        confidence = 0.54
        intent = "action_with_reaction"
        ambiguity = "conflicting_action_reaction"
    elif has_action and has_speech:
        kind = InterpretedInputKind.MIXED
        confidence = 0.82
        intent = "speak_and_act"
        ambiguity = None
    elif has_action:
        kind = InterpretedInputKind.ACTION
        confidence = 0.78
        intent = "player_action"
        ambiguity = None
    elif has_reaction:
        kind = InterpretedInputKind.REACTION
        confidence = 0.74
        intent = "player_reaction"
        ambiguity = None
    elif has_speech:
        kind = InterpretedInputKind.SPEECH
        confidence = 0.76
        intent = "dialogue"
        ambiguity = None
    elif len(tokens) <= 2:
        kind = InterpretedInputKind.INTENT_ONLY
        confidence = 0.62
        intent = "high_level_intent"
        ambiguity = None
    else:
        kind = InterpretedInputKind.AMBIGUOUS
        confidence = 0.45
        intent = "uncertain"
        ambiguity = "unable_to_classify_with_high_confidence"

    hint = _delivery_for_nl(
        kind=kind,
        confidence=confidence,
        ambiguity=ambiguity,
        lowered=lowered,
    )

    return PlayerInputInterpretation(
        raw_text=raw_text,
        normalized_text=text,
        kind=kind,
        confidence=confidence,
        ambiguity=ambiguity,
        intent=intent,
        entities={},
        selected_handling_path="nl_runtime",
        runtime_delivery_hint=hint,
    )
