"""W2.1.2 — Canonical Structured AI Story Output Contract

Defines the schema-driven output contract for AI story decisions.

The AI is allowed to propose changes through structured fields, but proposals
are not authoritative. The runtime validates all proposals against module rules.

Model hierarchy:
- StructuredAIStoryOutput: Main decision output (required + optional fields)
  - proposed_state_deltas: List[ProposedDelta]
  - dialogue_impulses: List[DialogueImpulse]
  - conflict_vector: ConflictVector | None
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator


class ProposedDelta(BaseModel):
    """An AI-proposed state change (pre-validation).

    A lightweight representation of a state change proposal.
    The runtime validates all proposals against module rules.

    Attributes:
        target_path: Dot-path to state location (e.g., "characters.veronique.emotional_state")
        next_value: Proposed new value for the target
        delta_type: Optional hint about change type (not authoritative, for clarity only)
        rationale: AI's reasoning for this specific change
    """

    target_path: str
    next_value: Any
    delta_type: str | None = None
    rationale: str = ""


class DialogueImpulse(BaseModel):
    """A character's narrative action or dialogue impulse.

    Represents what a character wants to say or do. Not authoritative—
    the dialogue/action system decides whether and how to enact impulses.

    Attributes:
        character_id: ID of the character proposing the impulse
        impulse_text: What the character wants to say/do
        intensity: 0.0 (mild) to 1.0 (extreme), default 0.5
    """

    character_id: str
    impulse_text: str
    intensity: float = 0.5

    @field_validator("intensity")
    @classmethod
    def validate_intensity(cls, v: float) -> float:
        """Ensure intensity is in [0.0, 1.0] range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"intensity must be in [0.0, 1.0], got {v}")
        return v


class ConflictVector(BaseModel):
    """The dominant narrative conflict direction and intensity.

    Describes the primary tension or conflict dynamic in the current
    narrative state. Used for downstream narrative tracking and analysis.

    Attributes:
        primary_axis: Main tension axis (e.g., "trust", "aggression", "guilt")
        intensity: 0.0 (dormant) to 1.0 (critical), default 0.5
        notes: Optional elaboration on the conflict
    """

    primary_axis: str
    intensity: float = 0.5
    notes: str | None = None

    @field_validator("intensity")
    @classmethod
    def validate_intensity(cls, v: float) -> float:
        """Ensure intensity is in [0.0, 1.0] range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"intensity must be in [0.0, 1.0], got {v}")
        return v


class StructuredAIStoryOutput(BaseModel):
    """Canonical structured AI story decision output.

    The contract that defines what AI models are allowed to output in
    structured form. All proposals are validated by the runtime before
    taking effect.

    Attributes (Required):
        scene_interpretation: AI's reading of the current scene state
        detected_triggers: List of trigger IDs detected (empty if none)
        proposed_state_deltas: List of proposed state changes (empty if none)
        rationale: Overall reasoning for the AI's decision

    Attributes (Optional):
        proposed_scene_id: Scene to transition to (None = continue current)
        dialogue_impulses: Character action/dialogue impulses (empty if none)
        conflict_vector: Dominant narrative tension (None if not applicable)
        confidence: AI's confidence 0.0-1.0 (None if not provided)
    """

    # Required fields
    scene_interpretation: str
    detected_triggers: list[str]
    proposed_state_deltas: list[ProposedDelta]
    rationale: str

    # Optional fields
    proposed_scene_id: str | None = None
    dialogue_impulses: list[DialogueImpulse] = []
    conflict_vector: ConflictVector | None = None
    confidence: float | None = None

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float | None:
        """Ensure confidence is in [0.0, 1.0] range if provided."""
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {v}")
        return v
