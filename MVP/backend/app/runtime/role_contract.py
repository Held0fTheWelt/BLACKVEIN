"""W2.4.1 — Canonical Internal AI Role Contract

Defines the structured output contract for three internal logical roles operating
inside a single AI call: interpreter, director, responder.

All three roles are required. Interpreter and Director remain diagnostic (non-executive).
Only Responder emits runtime-relevant candidates that feed the normalization layer.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class InterpreterSection(BaseModel):
    """Scene reading and interpretation (diagnostic only)."""

    scene_reading: str
    """Narrative description of what's happening in the scene."""

    detected_tensions: list[str]
    """List of interpersonal/situational tensions identified."""

    trigger_candidates: list[str]
    """List of potential triggers the scene could activate."""

    uncertainty_markers: list[str] | None = Field(default=None)
    """Optional: Places where interpretation is ambiguous."""


class DirectorSection(BaseModel):
    """Conflict steering and narrative direction (diagnostic only)."""

    conflict_steering: str
    """Narrative rationale for the chosen direction."""

    escalation_level: int = Field(ge=0, le=10)
    """0-10 scale: how much should conflict intensity change?"""

    recommended_direction: Literal["escalate", "stabilize", "shift_alliance", "redirect", "hold"]
    """Enum: type of narrative movement (bounded set, not free text)."""

    pressure_movement: str | None = Field(default=None)
    """Optional: specific description of where conflict pressure shifts."""


class ResponseImpulse(BaseModel):
    """A concrete behavioral or emotional impulse from responder."""

    character_id: str
    """Character experiencing the impulse."""

    impulse_type: Literal["emotional_reaction", "dialogue_urge", "action_urge"]
    """Category of impulse (enumerated, not free text)."""

    intensity: int = Field(ge=0, le=10)
    """0-10 scale: how strong is the impulse?"""

    rationale: str
    """Why this character has this impulse in this moment."""


class StateChangeCandidate(BaseModel):
    """A pre-delta proposal for state mutation from responder."""

    target_path: str
    """Path to the state field (e.g., "characters.alice.emotional_state")."""

    proposed_value: Any
    """New value for the target (any type allowed at this stage)."""

    rationale: str
    """Why this state change is proposed."""


class ResponderSection(BaseModel):
    """Runtime-relevant proposals (feeds normalization)."""

    response_impulses: list[ResponseImpulse] = Field(default_factory=list)
    """Concrete behavioral/emotional impulses before execution."""

    state_change_candidates: list[StateChangeCandidate] = Field(default_factory=list)
    """Pre-delta format proposals for state mutations."""

    dialogue_impulses: list[str] | None = Field(default=None)
    """Suggested dialogue lines or dialogue directions."""

    trigger_assertions: list[str] = Field(default_factory=list)
    """Triggers the responder asserts should be activated."""

    scene_transition_candidate: str | None = Field(default=None)
    """If responder proposes scene change, candidate scene_id."""


class AIRoleContract(BaseModel):
    """Canonical structured output contract for AI roles.

    All three roles are required; prevents silent failures or role omission.
    Interpreter and Director remain non-executive (diagnostic).
    Only Responder emits runtime-relevant candidates (pre-normalized).
    """

    interpreter: InterpreterSection
    director: DirectorSection
    responder: ResponderSection
