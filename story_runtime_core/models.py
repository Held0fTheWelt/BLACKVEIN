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
