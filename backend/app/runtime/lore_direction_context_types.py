"""Pydantic models for lore direction context (leaf — breaks context ↔ derivation import cycle)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModuleGuidanceUnit(BaseModel):
    """A single unit of selectable module guidance.

    Represents a discrete piece of lore, direction, or guidance that can be
    injected into context when relevant.
    """

    unit_type: str  # character, relationship, trigger, scene, phase, ending, transition
    unit_id: str  # ID from module (character id, trigger id, phase id, etc.)
    guidance_text: str  # The actual guidance content
    applicability_scope: str  # character, relationship, scene, trigger, phase
    relevance_signals: list[str] = Field(default_factory=list)


class LoreDirectionContext(BaseModel):
    """Bounded, selectively injected module guidance for current situation."""

    selected_units: list[ModuleGuidanceUnit] = Field(default_factory=list)
    total_available_units: int = 0
    selection_rationale: list[str] = Field(default_factory=list)
    module_id: str = ""
    derived_from_turn: int = 0
