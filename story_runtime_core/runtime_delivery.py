from __future__ import annotations

import re
from typing import Any

from .models import InterpretedInputKind, PlayerInputInterpretation, RuntimeDeliveryHint


def extract_spoken_text_for_delivery(raw_text: str) -> str:
    """Best-effort spoken line for SAY delivery (quotes, say:/ask: clauses, trailing dialogue)."""
    text = (raw_text or "").strip()
    quoted = re.findall(r'"([^"]+)"', text)
    if quoted:
        return quoted[0].strip()
    match = re.search(r"\b(?:say|says|said|ask|asks|asked|tell|tells|told)\b\s*[:,-]?\s*(.+)$", text, flags=re.IGNORECASE)
    if match:
        spoken = match.group(1).strip()
        if spoken:
            return spoken
    lead = re.match(
        r"^(?:\b(?:tell|ask)\s+(?:him|her|them)\s+)(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if lead:
        return lead.group(1).strip()
    return text


def natural_input_to_room_command(interpretation: PlayerInputInterpretation, raw_text: str) -> dict[str, Any]:
    """Map free-text NL (non-command, non-meta) to the thin room command shape: say | emote."""
    kind = interpretation.kind
    if kind in (InterpretedInputKind.EXPLICIT_COMMAND, InterpretedInputKind.META):
        raise ValueError("natural_input_to_room_command applies to nl_runtime path only")
    text = (raw_text or "").strip()
    hint = interpretation.runtime_delivery_hint or RuntimeDeliveryHint.EMOTE
    if hint is RuntimeDeliveryHint.SAY:
        return {"action": "say", "text": extract_spoken_text_for_delivery(text)}
    return {"action": "emote", "text": text}
