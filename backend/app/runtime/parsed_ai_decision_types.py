"""ParsedAIDecision — zyklusfrei gegenüber role_structured_decision."""

from __future__ import annotations

from pydantic import BaseModel

from app.runtime.ai_output import ConflictVector, DialogueImpulse, ProposedDelta


class ParsedAIDecision(BaseModel):
    """Canonical internal decision representation after parsing and normalization.

    This is the authoritative form that the runtime consumes.
    Raw output and parse source are preserved for diagnostics.
    """

    scene_interpretation: str
    detected_triggers: list[str]
    proposed_deltas: list[ProposedDelta]
    proposed_scene_id: str | None
    rationale: str

    dialogue_impulses: list[DialogueImpulse] = []
    conflict_vector: ConflictVector | None = None
    confidence: float | None = None

    raw_output: str
    parsed_source: str
