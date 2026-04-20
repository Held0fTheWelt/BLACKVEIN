from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class InterpretedInputKind(str, Enum):
    SPEECH = "speech"
    ACTION = "action"
    REACTION = "reaction"
    MIXED = "mixed"
    INTENT_ONLY = "intent_only"
    EXPLICIT_COMMAND = "explicit_command"
    META = "meta"
    AMBIGUOUS = "ambiguous"


class RuntimeDeliveryHint(str, Enum):
    """How live-run / thin hosts should map NL to say vs emote (conservative under low confidence)."""

    SAY = "say"
    EMOTE = "emote"
    NARRATIVE_BODY = "narrative_body"


class PlayerInputInterpretation(BaseModel):
    raw_text: str
    kind: InterpretedInputKind
    normalized_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    ambiguity: str | None = None
    intent: str | None = None
    entities: dict[str, Any] = Field(default_factory=dict)
    command_name: str | None = None
    command_args: list[str] = Field(default_factory=list)
    selected_handling_path: str = "nl_runtime"
    runtime_delivery_hint: RuntimeDeliveryHint | None = None
