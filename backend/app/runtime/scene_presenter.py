"""W3.4.1 — Canonical character and conflict presenter mapping.

Maps bounded, canonical SessionState data to typed UI-facing output models.
All fields derive strictly from canonical runtime sources; no invented state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.runtime.w2_models import SessionState


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


def present_character_panel(
    session_state: SessionState,
    character_id: str,
) -> CharacterPanelOutput:
    """Map canonical session data to character panel output.

    Extracts character name and relationship trajectory from SessionState.
    All fields derive strictly from canonical sources.

    Args:
        session_state: The active SessionState.
        character_id: The character to present.

    Returns:
        CharacterPanelOutput with bounded, canonical-derived fields.

    Logic:
        1. Extract character_name from canonical_state.characters[character_id].name if present.
        2. Filter relationship_axis_context.salient_axes to only those involving character_id.
        3. Classify overall_trajectory from filtered axes:
           - All escalating → 'escalating'
           - All stable → 'stable'
           - All de-escalating → 'de-escalating'
           - Mixed → 'mixed'
           - None or missing context → 'unknown'
        4. Sort filtered axes by salience_score; take top 2 as RelationshipMovement objects.
        5. Return CharacterPanelOutput.
    """
    # Step 1: Extract character_name
    character_name = None
    if session_state.canonical_state:
        characters = session_state.canonical_state.get("characters", {})
        if isinstance(characters, dict) and character_id in characters:
            char_data = characters[character_id]
            if isinstance(char_data, dict):
                character_name = char_data.get("name")

    # Step 2: Filter salient_axes for this character
    filtered_axes = []
    if (
        session_state.context_layers
        and session_state.context_layers.relationship_axis_context
    ):
        for axis in session_state.context_layers.relationship_axis_context.salient_axes:
            if axis.character_a == character_id or axis.character_b == character_id:
                filtered_axes.append(axis)

    # Step 3: Classify overall_trajectory
    if not filtered_axes:
        overall_trajectory = "unknown"
    else:
        # Collect all change directions from filtered axes
        change_directions = {axis.recent_change_direction for axis in filtered_axes}

        if change_directions == {"escalating"}:
            overall_trajectory = "escalating"
        elif change_directions == {"stable"}:
            overall_trajectory = "stable"
        elif change_directions == {"de-escalating"}:
            overall_trajectory = "de-escalating"
        else:
            # Mixed directions
            overall_trajectory = "mixed"

    # Step 4: Sort by salience_score and take top 2
    sorted_axes = sorted(filtered_axes, key=lambda a: a.salience_score, reverse=True)
    top_two = sorted_axes[:2]

    top_relationship_movements = [
        RelationshipMovement(
            other_character_id=axis.character_b
            if axis.character_a == character_id
            else axis.character_a,
            signal_type=axis.signal_type,
            recent_change=axis.recent_change_direction,
            salience_score=axis.salience_score,
        )
        for axis in top_two
    ]

    # Step 5: Return CharacterPanelOutput
    return CharacterPanelOutput(
        character_id=character_id,
        character_name=character_name,
        overall_trajectory=overall_trajectory,
        top_relationship_movements=top_relationship_movements,
    )
