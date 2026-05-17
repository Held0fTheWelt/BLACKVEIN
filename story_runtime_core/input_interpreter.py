from __future__ import annotations

import re

from .models import InterpretedInputKind, PlayerInputInterpretation, RuntimeDeliveryHint


META_PREFIXES = ("ooc:", "meta:", "out of character:")
COMMAND_PREFIXES = ("/", "!")
_QUOTED_SPAN = re.compile(r'"([^"]+)"')


def _tokens_with_alnum(text: str) -> list[str]:
    return [token for token in text.split() if any(ch.isalnum() for ch in token)]


def _interpret_player_empty_or_noise(raw_text: str, text: str) -> PlayerInputInterpretation | None:
    if not text:
        return PlayerInputInterpretation(
            raw_text=raw_text,
            normalized_text="",
            kind=InterpretedInputKind.AMBIGUOUS,
            confidence=0.0,
            ambiguity="empty_input",
            intent="withheld_response_or_silence",
            selected_handling_path="nl_runtime",
            runtime_delivery_hint=RuntimeDeliveryHint.NARRATIVE_BODY,
        )
    if not _tokens_with_alnum(text):
        return PlayerInputInterpretation(
            raw_text=raw_text,
            normalized_text=text,
            kind=InterpretedInputKind.AMBIGUOUS,
            confidence=0.15,
            ambiguity="no_lexical_tokens",
            intent="withheld_response_or_silence",
            selected_handling_path="nl_runtime",
            runtime_delivery_hint=RuntimeDeliveryHint.NARRATIVE_BODY,
        )
    return None


def _interpret_meta_or_command(raw_text: str, text: str, lowered: str) -> PlayerInputInterpretation | None:
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
    return None


def interpret_player_input(raw_text: str) -> PlayerInputInterpretation:
    """Return a thin structural preview without language or verb maps.

    This function is diagnostic glue for old callers. It intentionally avoids
    deciding whether natural language means action, reaction, question, or
    speech unless the surface contains an explicit quoted span. Authoritative
    interpretation belongs to the AI semantic adapter contract.
    """
    text = (raw_text or "").strip()
    lowered = text.lower()

    early = _interpret_player_empty_or_noise(raw_text, text)
    if early is not None:
        return early

    meta_cmd = _interpret_meta_or_command(raw_text, text, lowered)
    if meta_cmd is not None:
        return meta_cmd

    if _QUOTED_SPAN.search(text):
        return PlayerInputInterpretation(
            raw_text=raw_text,
            normalized_text=text,
            kind=InterpretedInputKind.SPEECH,
            confidence=0.7,
            intent="quoted_dialogue",
            selected_handling_path="nl_runtime",
            runtime_delivery_hint=RuntimeDeliveryHint.SAY,
        )

    return PlayerInputInterpretation(
        raw_text=raw_text,
        normalized_text=text,
        kind=InterpretedInputKind.AMBIGUOUS,
        confidence=0.45,
        ambiguity="semantic_ai_resolution_required",
        intent="semantic_resolution_required",
        entities={},
        selected_handling_path="nl_runtime",
        runtime_delivery_hint=RuntimeDeliveryHint.NARRATIVE_BODY,
    )
