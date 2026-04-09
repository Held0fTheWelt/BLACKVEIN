# W3.4.1: Canonical Character and Conflict Presenter Mapping

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define and implement a canonical presenter layer that exposes bounded, readable character and conflict panel data from the playable session state.

**Architecture:** The presenter layer maps canonical runtime data (SessionState, context layers) through explicit Pydantic models (CharacterPanelOutput, ConflictPanelOutput) into UI-facing contracts. No invented state; all fields derive deterministically from canonical sources.

**Tech Stack:** Python, Pydantic, SQLAlchemy (for existing session/state access), pytest (for presenter unit tests).

---

## Context

**W3.3** established the playable session shell at `/play/<session_id>` with session rendering and interaction flow. Operators can now start sessions and see basic session info.

**W3.4.1** adds the character and conflict presenter layer—the foundation for bounded UI panels that show:
- Which characters are in play, their relationship trajectories, and salient relationship movements
- Current conflict pressure and escalation trends, without a full conflict analytics dump

This step defines only the presenter/mapping logic. Final panel rendering in templates and route integration occur in later W3.4 sub-steps.

---

## Design

### Output Models

#### **RelationshipMovement**

```python
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
```

#### **CharacterPanelOutput**

```python
class CharacterPanelOutput(BaseModel):
    """Bounded character panel output for UI display."""

    character_id: str
    """Character identifier from canonical state."""

    character_name: str | None
    """Character name if available in canonical_state.characters[id].name."""

    overall_trajectory: str
    """Relationship trend for this character: 'escalating', 'stable', 'de-escalating', 'mixed', 'unknown'.
    Derived only from axes in relationship_axis_context where this character is involved.
    """

    top_relationship_movements: list[RelationshipMovement]
    """Up to 2 most salient relationship movements involving this character, sorted by salience_score."""
```

#### **ConflictTrendSignal**

```python
class ConflictTrendSignal(BaseModel):
    """A compact recent trend derived from canonical signals."""

    signal: str
    """Trend: 'escalating', 'stable', 'de-escalating', 'uncertain'."""

    source_basis: list[str]
    """Canonical sources contributing to this signal: 'guard_outcomes', 'relationship_tension', 'pressure_change', etc."""
```

#### **ConflictPanelOutput**

```python
class ConflictPanelOutput(BaseModel):
    """Bounded conflict panel output for UI display."""

    current_pressure: int | float | None
    """Numeric pressure from canonical_state.conflict_state.pressure or short_term_context.conflict_pressure.
    None if not present in canonical data.
    """

    current_escalation_status: str
    """Classification based on pressure: 'low' (0–33), 'medium' (34–66), 'high' (67–100), or 'unknown' if pressure is None."""

    recent_trend: ConflictTrendSignal | None
    """Trend signal derived from guard outcomes and relationship escalation markers.
    None if context layers are missing or no trend data available.
    """

    turning_point_risk: bool | None
    """True if relationship_axis_context.has_escalation_markers is True.
    Strictly derived from canonical signals; no invented heuristics.
    None if context layers missing.
    """
```

### Presenter Functions

#### **present_character_panel**

```python
def present_character_panel(
    session_state: SessionState,
    character_id: str,
) -> CharacterPanelOutput:
    """Map canonical session data to character panel output.

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
```

#### **present_conflict_panel**

```python
def present_conflict_panel(
    session_state: SessionState,
) -> ConflictPanelOutput:
    """Map canonical session data to conflict panel output.

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
        3. Derive recent_trend from canonical sources:
           - If progression_summary.most_recent_guard_outcomes shows increasing rejections → 'escalating'
           - If relationship_axis_context.has_escalation_markers → add 'relationship_tension' to source_basis
           - If overall_stability_signal == 'stable' → 'stable'
           - Basis list shows all sources contributing to the signal.
           - If no clear signal → 'uncertain'
           - If context layers missing → None
        4. Derive turning_point_risk:
           - True if relationship_axis_context.has_escalation_markers is True
           - None if context layers missing
        5. Return ConflictPanelOutput.
    """
```

---

## Mapping Sources

### Character Panel Mapping

| Output Field | Canonical Source |
|---|---|
| `character_id` | Function parameter |
| `character_name` | `canonical_state.characters[character_id].name` |
| `overall_trajectory` | `relationship_axis_context.salient_axes` (filtered to this character) |
| `top_relationship_movements[*]` | `relationship_axis_context.salient_axes` (top 2 by salience_score) |

### Conflict Panel Mapping

| Output Field | Canonical Source |
|---|---|
| `current_pressure` | `short_term_context.conflict_pressure` or `canonical_state.conflict_state.pressure` |
| `current_escalation_status` | Derived from `current_pressure` |
| `recent_trend.signal` | `progression_summary.most_recent_guard_outcomes`, `relationship_axis_context.has_escalation_markers`, `relationship_axis_context.overall_stability_signal` |
| `recent_trend.source_basis` | List of canonical sources that contributed |
| `turning_point_risk` | `relationship_axis_context.has_escalation_markers` |

---

## Hard Constraints

1. **No invented UI state.** All fields derive strictly from canonical runtime data.
2. **Bounded and deterministic.** Presenter logic is explicit, repeatable, and testable.
3. **Top 2 relationship movements exactly.** Not 1, not 3; exactly up to 2.
4. **Trajectory derived only from involved axes.** Don't aggregate unrelated relationships.
5. **Pressure missing → None and unknown.** Don't invent default values.
6. **Escalation markers strictly from canonical signals.** No heuristics beyond what already exists in context layers.

---

## Testing Strategy

### Unit Tests for present_character_panel

- **Test:** Character with no relationship axes → overall_trajectory = 'unknown', top_relationship_movements = []
- **Test:** Character with 1 salient axis (escalating) → overall_trajectory = 'escalating', top_relationship_movements = [that axis]
- **Test:** Character with 3+ salient axes → top_relationship_movements includes exactly top 2 by salience_score
- **Test:** Character with mixed escalation/stable axes → overall_trajectory = 'mixed'
- **Test:** Character name present in canonical_state → CharacterPanelOutput.character_name is populated
- **Test:** Character name absent → character_name = None

### Unit Tests for present_conflict_panel

- **Test:** Pressure present and low (20) → current_pressure = 20, current_escalation_status = 'low'
- **Test:** Pressure present and high (75) → current_pressure = 75, current_escalation_status = 'high'
- **Test:** Pressure absent → current_pressure = None, current_escalation_status = 'unknown'
- **Test:** Multiple guard outcomes with increasing rejections → recent_trend.signal = 'escalating', 'guard_outcomes' in source_basis
- **Test:** Relationship escalation markers present → 'relationship_tension' in source_basis
- **Test:** Escalation markers present → turning_point_risk = True
- **Test:** No escalation markers → turning_point_risk = False
- **Test:** Context layers missing → recent_trend = None, turning_point_risk = None

---

## Implementation Notes

1. **File location:** `backend/app/runtime/scene_presenter.py`
2. **Dependencies:** SessionState, relationship_axis_context, progression_summary, short_term_context models from `app.runtime.w2_models` and related modules.
3. **Integration point (future W3.4.2):** Routes in `backend/app/web/routes.py` will call these presenters to populate template context.
4. **Serialization (future W3.4.2):** Models can be serialized to JSON via `.model_dump()` for JSON API responses or `.model_dump_json()` for direct JSON output.

---

## Acceptance Criteria

- ✅ CharacterPanelOutput model is typed, bounded, and derived from canonical relationship_axis_context.
- ✅ ConflictPanelOutput model is typed, bounded, and derived from short_term_context, progression_summary, and relationship_axis_context.
- ✅ present_character_panel() and present_conflict_panel() functions are explicit and deterministic.
- ✅ All mapping logic traces back to canonical SessionState sources.
- ✅ Unit tests cover normal cases, edge cases, and missing data handling.
- ✅ No invented UI state; all fields are canonical-derived.

---

## Out of Scope (Deferred to Later W3.4 Steps)

- Final template rendering for character and conflict panels
- Route integration (`GET /play/<session_id>` updates to call presenters)
- Character list panel (showing all characters in session)
- Full conflict analytics (detailed breakdown of triggers, outcomes, etc.)
- Module-specific character or conflict adaptations
- Scene panel rendering (upcoming W3.4.2)
- Interaction/history panels (upcoming W3.4.3)

---

## Suggested Commit Message

```
feat(w3): add canonical character and conflict presenter mapping for UI panels
```
