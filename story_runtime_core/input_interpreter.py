from __future__ import annotations

from .models import InterpretedInputKind, PlayerInputInterpretation


META_PREFIXES = ("ooc:", "meta:", "out of character:")
COMMAND_PREFIXES = ("/", "!")
REACTION_TOKENS = ("wow", "uh", "huh", "oh", "hmm", "what?")
ACTION_VERBS = ("go", "take", "open", "look", "attack", "talk", "move", "inspect", "use")
SPEECH_MARKERS = ('"', "say ", "ask ", "tell ")


def interpret_player_input(raw_text: str) -> PlayerInputInterpretation:
    text = (raw_text or "").strip()
    lowered = text.lower()
    tokens = [token for token in lowered.replace(",", " ").split() if token]

    if not text:
        return PlayerInputInterpretation(
            raw_text=raw_text,
            normalized_text="",
            kind=InterpretedInputKind.AMBIGUOUS,
            confidence=0.0,
            ambiguity="empty_input",
            intent=None,
            selected_handling_path="nl_runtime",
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
        )

    if lowered.startswith(META_PREFIXES):
        return PlayerInputInterpretation(
            raw_text=raw_text,
            normalized_text=text,
            kind=InterpretedInputKind.META,
            confidence=0.98,
            intent="meta_instruction",
            selected_handling_path="meta",
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
        )

    has_action = any(token in ACTION_VERBS for token in tokens)
    has_speech = any(marker in lowered for marker in SPEECH_MARKERS)
    has_reaction = len(tokens) <= 3 and any(token in REACTION_TOKENS for token in tokens)

    if has_action and has_speech:
        kind = InterpretedInputKind.MIXED
        confidence = 0.82
        intent = "speak_and_act"
    elif has_action:
        kind = InterpretedInputKind.ACTION
        confidence = 0.78
        intent = "player_action"
    elif has_reaction:
        kind = InterpretedInputKind.REACTION
        confidence = 0.74
        intent = "player_reaction"
    elif has_speech:
        kind = InterpretedInputKind.SPEECH
        confidence = 0.76
        intent = "dialogue"
    elif len(tokens) <= 2:
        kind = InterpretedInputKind.INTENT_ONLY
        confidence = 0.62
        intent = "high_level_intent"
    else:
        kind = InterpretedInputKind.AMBIGUOUS
        confidence = 0.45
        intent = "uncertain"

    ambiguity = None
    if kind is InterpretedInputKind.AMBIGUOUS:
        ambiguity = "unable_to_classify_with_high_confidence"

    return PlayerInputInterpretation(
        raw_text=raw_text,
        normalized_text=text,
        kind=kind,
        confidence=confidence,
        ambiguity=ambiguity,
        intent=intent,
        entities={},
        selected_handling_path="nl_runtime",
    )
