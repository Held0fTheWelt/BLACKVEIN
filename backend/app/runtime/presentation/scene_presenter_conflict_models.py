"""Conflict-panel output models shared by scene presenter helpers."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


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
    """Classification based on pressure: 'low' (0-33), 'medium' (34-66), 'high' (67-100), or 'unknown' if pressure is None."""

    recent_trend: Optional[ConflictTrendSignal] = None
    """Trend signal derived from guard outcomes and relationship escalation markers.
    None if context layers are missing or no trend data available.
    """

    turning_point_risk: Optional[bool] = None
    """True if relationship_axis_context.has_escalation_markers is True.
    Strictly derived from canonical signals; no invented heuristics.
    None if context layers missing.
    """
