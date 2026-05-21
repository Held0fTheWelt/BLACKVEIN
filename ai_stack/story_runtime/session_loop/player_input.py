"""Player input extraction and compacting helpers."""

from __future__ import annotations

import uuid
from typing import Any

from .constants import MAX_COMPOSED_FOLLOW_UP_CHARS, MAX_PROMOTED_INPUT_EXCERPT_CHARS


def _player_input_text(player_input_payload: dict[str, Any] | None) -> str:
    if not isinstance(player_input_payload, dict):
        return ""
    for key in ("player_input", "text", "utterance"):
        value = player_input_payload.get(key)
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _compact_one_line(text: str, *, limit: int) -> str:
    compact = " ".join(str(text or "").split())
    if limit <= 0 or len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _promoted_player_input_id(player_input_payload: dict[str, Any] | None) -> str:
    if isinstance(player_input_payload, dict):
        for key in ("player_input_id", "input_id", "message_id"):
            value = str(player_input_payload.get(key) or "").strip()
            if value:
                return value
    return str(uuid.uuid4())
