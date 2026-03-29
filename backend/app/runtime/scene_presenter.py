"""W3.4.1 — Canonical character and conflict presenter mapping.

Maps bounded, canonical SessionState data to typed UI-facing output models.
All fields derive strictly from canonical runtime sources; no invented state.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RelationshipMovement(BaseModel):
    """A single salient relationship change tied to a character."""

    other_character_id: str
    """The character this relationship is with."""

    signal_type: str
    """Classification: 'tension', 'alliance', 'instability', 'stable'."""

    recent_change: str
    """Trend: 'escalating', 'stable', 'de-escalating'."""

    salience_score: float
    """Relevance 0.0–1.0; how much this relationship matters now."""


class CharacterPanelOutput(BaseModel):
    """Bounded character panel output for UI display."""

    character_id: str
    """Character identifier from canonical state."""

    character_name: Optional[str] = None
    """Character name if available in canonical_state.characters[id].name."""

    overall_trajectory: str
    """Relationship trend for this character: 'escalating', 'stable', 'de-escalating', 'mixed', 'unknown'.
    Derived only from axes in relationship_axis_context where this character is involved.
    """

    top_relationship_movements: list[RelationshipMovement] = Field(default_factory=list)
    """Up to 2 most salient relationship movements involving this character, sorted by salience_score."""


class ConflictTrendSignal(BaseModel):
    """A compact recent trend derived from canonical signals."""

    signal: str
    """Trend: 'escalating', 'stable', 'de-escalating', 'uncertain'."""

    source_basis: list[str] = Field(default_factory=list)
    """Canonical sources contributing to this signal: 'guard_outcomes', 'relationship_tension', 'pressure_change', etc."""


class ConflictPanelOutput(BaseModel):
    """Bounded conflict panel output for UI display."""

    current_pressure: Optional[int | float] = None
    """Numeric pressure from canonical_state.conflict_state.pressure or short_term_context.conflict_pressure.
    None if not present in canonical data.
    """

    current_escalation_status: str
    """Classification based on pressure: 'low' (0–33), 'medium' (34–66), 'high' (67–100), or 'unknown' if pressure is None."""

    recent_trend: Optional[ConflictTrendSignal] = None
    """Trend signal derived from guard outcomes and relationship escalation markers.
    None if context layers are missing or no trend data available.
    """

    turning_point_risk: Optional[bool] = None
    """True if relationship_axis_context.has_escalation_markers is True.
    Strictly derived from canonical signals; no invented heuristics.
    None if context layers missing.
    """
