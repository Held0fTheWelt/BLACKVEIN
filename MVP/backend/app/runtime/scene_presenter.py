"""W3.4.1 — Canonical character and conflict presenter mapping.

Maps bounded, canonical SessionState data to typed UI-facing output models.
All fields derive strictly from canonical runtime sources; no invented state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.runtime.runtime_models import SessionState


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


def present_conflict_panel(
    session_state: SessionState,
) -> ConflictPanelOutput:
    """Map canonical session data to conflict panel output.

    Extracts conflict pressure, escalation status, and trend signals from SessionState.
    All fields derive strictly from canonical sources.

    Args:
        session_state: The active SessionState.

    Returns:
        ConflictPanelOutput with bounded, canonical-derived fields.

    Logic:
        1. Extract current_pressure from short_term_context.conflict_pressure or
           canonical_state.conflict_state.pressure. Keep as None if absent.
        2. Derive current_escalation_status:
           - If pressure is None → 'unknown'
           - Else: 0–33 → 'low', 34–66 → 'medium', 67–100 → 'high'
        3. Derive recent_trend from canonical sources using priority rule:
           - Priority 1: If guard_outcomes show more rejections → 'escalating'
           - Priority 2: If relationship escalation markers present → 'escalating'
           - Priority 3: If relationship stability signal == 'de-escalating' → 'de-escalating'
           - Priority 4: If relationship stability signal == 'stable' → 'stable'
           - Fallback: 'uncertain'
           - source_basis lists all sources that contributed.
           - If context layers missing → None
        4. Derive turning_point_risk:
           - True if relationship_axis_context.has_escalation_markers is True
           - False otherwise
           - None if context layers missing
        5. Return ConflictPanelOutput.
    """
    # Step 1: Extract current_pressure
    current_pressure = None
    if session_state.context_layers and session_state.context_layers.short_term_context:
        current_pressure = session_state.context_layers.short_term_context.conflict_pressure
    if current_pressure is None and session_state.canonical_state:
        conflict_state = session_state.canonical_state.get("conflict_state", {})
        if isinstance(conflict_state, dict):
            current_pressure = conflict_state.get("pressure")

    # Step 2: Derive current_escalation_status
    if current_pressure is None:
        current_escalation_status = "unknown"
    elif current_pressure <= 33:
        current_escalation_status = "low"
    elif current_pressure <= 66:
        current_escalation_status = "medium"
    else:
        current_escalation_status = "high"

    # Step 3: Derive recent_trend using priority rule
    recent_trend = None
    if (
        session_state.context_layers
        and (
            session_state.context_layers.progression_summary
            or session_state.context_layers.relationship_axis_context
        )
    ):
        signal = None
        source_basis = []

        # Priority 1: Check guard outcomes for escalation
        if session_state.context_layers.progression_summary:
            outcomes = (
                session_state.context_layers.progression_summary.most_recent_guard_outcomes
            )
            if outcomes:
                rejections = outcomes.count("rejected")
                acceptances = outcomes.count("accepted")
                if rejections > acceptances:
                    signal = "escalating"
                    source_basis.append("guard_outcomes")

        # Priority 2: Check relationship escalation markers
        if session_state.context_layers.relationship_axis_context:
            rel_ctx = session_state.context_layers.relationship_axis_context
            if rel_ctx.has_escalation_markers:
                if signal != "escalating":
                    signal = "escalating"
                source_basis.append("relationship_tension")
            elif signal is None:
                # Check overall stability signal (only if not escalating)
                if rel_ctx.overall_stability_signal == "de-escalating":
                    signal = "de-escalating"
                    source_basis.append("stability_signal")
                elif rel_ctx.overall_stability_signal == "stable":
                    signal = "stable"
                    source_basis.append("stability_signal")

        # Fallback
        if signal is None:
            signal = "uncertain"

        if source_basis or signal != "uncertain":
            recent_trend = ConflictTrendSignal(
                signal=signal,
                source_basis=source_basis,
            )

    # Step 4: Derive turning_point_risk
    turning_point_risk = None
    if session_state.context_layers and session_state.context_layers.relationship_axis_context:
        turning_point_risk = (
            session_state.context_layers.relationship_axis_context.has_escalation_markers
        )

    # Step 5: Return ConflictPanelOutput
    return ConflictPanelOutput(
        current_pressure=current_pressure,
        current_escalation_status=current_escalation_status,
        recent_trend=recent_trend,
        turning_point_risk=turning_point_risk,
    )


def present_all_characters(
    session_state: SessionState,
) -> list[CharacterPanelOutput]:
    """Map all characters in play to bounded character panel outputs.

    Collects all characters from canonical_state, orders deterministically,
    calls present_character_panel for each, handles all edge cases gracefully.

    Args:
        session_state: The active SessionState.

    Returns:
        List of CharacterPanelOutput for all characters in play, deterministically ordered.
        Empty list if no characters in canonical_state or canonical_state is missing.

    Logic:
        1. Extract character_ids from canonical_state.characters (empty dict if not present)
        2. Order deterministically by character_id
        3. For each character_id, call present_character_panel(session_state, character_id)
        4. Collect results into list
        5. Return list (may be empty)
    """
    # Step 1: Extract character_ids from canonical_state
    character_ids = []
    if session_state.canonical_state:
        characters = session_state.canonical_state.get("characters", {})
        if isinstance(characters, dict):
            character_ids = list(characters.keys())

    # Step 2: Order deterministically by character_id
    character_ids.sort()

    # Step 3 & 4: For each character_id, call present_character_panel and collect results
    results = [
        present_character_panel(session_state, char_id)
        for char_id in character_ids
    ]

    # Step 5: Return list
    return results
