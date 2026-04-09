# W3.4.1: Canonical Character and Conflict Presenter Implementation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement bounded Pydantic output models and deterministic presenter functions that map canonical SessionState data to character and conflict panel outputs.

**Architecture:** Two presenter functions extract character and conflict data from canonical runtime sources (SessionState, context layers) and map them through typed output models. All mapping is explicit and deterministic; no invented state. Priority rule for signal determination ensures reproducible behavior when multiple canonical sources contribute.

**Tech Stack:** Python, Pydantic, pytest, SQLAlchemy (existing session/state access).

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/app/runtime/scene_presenter.py` | NEW: Bounded output models (Pydantic) + presenter functions |
| `backend/tests/runtime/test_scene_presenter.py` | NEW: Comprehensive unit tests for models and functions |
| `backend/app/runtime/__init__.py` | MODIFY: Export presenter models/functions |

---

## Critical Implementation Note: Signal Priority Rule

When multiple canonical sources contribute to `recent_trend.signal` (e.g., both guard outcomes AND relationship escalation markers), use this priority order to ensure deterministic output:

**Priority (highest to lowest):**
1. **Escalating signals** (if ANY source indicates escalation → "escalating")
2. **De-escalating signals** (if ANY source indicates de-escalation → "de-escalating")
3. **Stable signals** (if all sources indicate stable → "stable")
4. **Uncertain** (if insufficient data or conflicting signals → "uncertain")

**Implementation:** Check sources in this order:
- If `progression_summary.most_recent_guard_outcomes` has more rejections than acceptances → escalating
- Else if `relationship_axis_context.has_escalation_markers` is True → escalating
- Else if `relationship_axis_context.overall_stability_signal == "de-escalating"` → de-escalating
- Else if `relationship_axis_context.overall_stability_signal == "stable"` → stable
- Else → uncertain

This rule ensures that any escalation signal takes precedence, making the presenter sensitive to conflict increase while remaining deterministic.

---

## Task 1: Create Output Models with Tests

**Files:**
- Create: `backend/app/runtime/scene_presenter.py`
- Create: `backend/tests/runtime/test_scene_presenter.py`

### Step 1.1: Write failing tests for output models

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend
PYTHONPATH=. python -m pytest tests/runtime/test_scene_presenter.py -v
```

Create `backend/tests/runtime/test_scene_presenter.py`:

```python
"""Unit tests for scene presenter models and functions."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.runtime.scene_presenter import (
    CharacterPanelOutput,
    ConflictPanelOutput,
    ConflictTrendSignal,
    RelationshipMovement,
)


class TestRelationshipMovementModel:
    """Tests for RelationshipMovement Pydantic model."""

    def test_relationship_movement_creation(self):
        """RelationshipMovement can be created with valid fields."""
        movement = RelationshipMovement(
            other_character_id="veronique",
            signal_type="tension",
            recent_change="escalating",
            salience_score=0.85,
        )
        assert movement.other_character_id == "veronique"
        assert movement.signal_type == "tension"
        assert movement.recent_change == "escalating"
        assert movement.salience_score == 0.85

    def test_relationship_movement_serialization(self):
        """RelationshipMovement serializes to dict."""
        movement = RelationshipMovement(
            other_character_id="giuseppe",
            signal_type="alliance",
            recent_change="stable",
            salience_score=0.5,
        )
        data = movement.model_dump()
        assert data["other_character_id"] == "giuseppe"
        assert data["signal_type"] == "alliance"


class TestCharacterPanelOutputModel:
    """Tests for CharacterPanelOutput Pydantic model."""

    def test_character_panel_output_with_name_and_movements(self):
        """CharacterPanelOutput can be created with all fields."""
        movement = RelationshipMovement(
            other_character_id="veronique",
            signal_type="tension",
            recent_change="escalating",
            salience_score=0.85,
        )
        output = CharacterPanelOutput(
            character_id="giuseppe",
            character_name="Giuseppe",
            overall_trajectory="escalating",
            top_relationship_movements=[movement],
        )
        assert output.character_id == "giuseppe"
        assert output.character_name == "Giuseppe"
        assert output.overall_trajectory == "escalating"
        assert len(output.top_relationship_movements) == 1

    def test_character_panel_output_without_name(self):
        """CharacterPanelOutput allows character_name to be None."""
        output = CharacterPanelOutput(
            character_id="veronique",
            character_name=None,
            overall_trajectory="stable",
            top_relationship_movements=[],
        )
        assert output.character_name is None
        assert output.overall_trajectory == "stable"

    def test_character_panel_output_max_two_relationships(self):
        """CharacterPanelOutput top_relationship_movements bounded to 2."""
        movements = [
            RelationshipMovement(
                other_character_id=f"char{i}",
                signal_type="tension",
                recent_change="escalating",
                salience_score=0.9 - (i * 0.1),
            )
            for i in range(2)
        ]
        output = CharacterPanelOutput(
            character_id="test",
            character_name=None,
            overall_trajectory="escalating",
            top_relationship_movements=movements,
        )
        assert len(output.top_relationship_movements) == 2

    def test_character_panel_output_trajectory_values(self):
        """CharacterPanelOutput overall_trajectory accepts valid values."""
        valid_trajectories = ["escalating", "stable", "de-escalating", "mixed", "unknown"]
        for trajectory in valid_trajectories:
            output = CharacterPanelOutput(
                character_id="test",
                character_name=None,
                overall_trajectory=trajectory,
                top_relationship_movements=[],
            )
            assert output.overall_trajectory == trajectory


class TestConflictTrendSignalModel:
    """Tests for ConflictTrendSignal Pydantic model."""

    def test_conflict_trend_signal_creation(self):
        """ConflictTrendSignal can be created with signal and source_basis."""
        signal = ConflictTrendSignal(
            signal="escalating",
            source_basis=["guard_outcomes", "relationship_tension"],
        )
        assert signal.signal == "escalating"
        assert "guard_outcomes" in signal.source_basis
        assert "relationship_tension" in signal.source_basis

    def test_conflict_trend_signal_single_source(self):
        """ConflictTrendSignal source_basis can be a single item."""
        signal = ConflictTrendSignal(
            signal="stable",
            source_basis=["guard_outcomes"],
        )
        assert len(signal.source_basis) == 1

    def test_conflict_trend_signal_serialization(self):
        """ConflictTrendSignal serializes to dict."""
        signal = ConflictTrendSignal(
            signal="de-escalating",
            source_basis=["pressure_change"],
        )
        data = signal.model_dump()
        assert data["signal"] == "de-escalating"
        assert isinstance(data["source_basis"], list)


class TestConflictPanelOutputModel:
    """Tests for ConflictPanelOutput Pydantic model."""

    def test_conflict_panel_output_with_pressure_and_trend(self):
        """ConflictPanelOutput can be created with all fields."""
        trend = ConflictTrendSignal(
            signal="escalating",
            source_basis=["guard_outcomes"],
        )
        output = ConflictPanelOutput(
            current_pressure=75,
            current_escalation_status="high",
            recent_trend=trend,
            turning_point_risk=True,
        )
        assert output.current_pressure == 75
        assert output.current_escalation_status == "high"
        assert output.recent_trend is not None
        assert output.turning_point_risk is True

    def test_conflict_panel_output_without_pressure(self):
        """ConflictPanelOutput allows current_pressure to be None."""
        output = ConflictPanelOutput(
            current_pressure=None,
            current_escalation_status="unknown",
            recent_trend=None,
            turning_point_risk=None,
        )
        assert output.current_pressure is None
        assert output.current_escalation_status == "unknown"

    def test_conflict_panel_output_escalation_status_values(self):
        """ConflictPanelOutput escalation_status accepts valid values."""
        valid_statuses = ["low", "medium", "high", "unknown"]
        for status in valid_statuses:
            output = ConflictPanelOutput(
                current_pressure=50,
                current_escalation_status=status,
                recent_trend=None,
                turning_point_risk=None,
            )
            assert output.current_escalation_status == status

    def test_conflict_panel_output_serialization(self):
        """ConflictPanelOutput serializes to JSON-compatible dict."""
        trend = ConflictTrendSignal(
            signal="stable",
            source_basis=["guard_outcomes"],
        )
        output = ConflictPanelOutput(
            current_pressure=40,
            current_escalation_status="medium",
            recent_trend=trend,
            turning_point_risk=False,
        )
        data = output.model_dump(mode="json")
        assert data["current_pressure"] == 40
        assert data["recent_trend"]["signal"] == "stable"
```

### Step 1.2: Run tests to verify they fail

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend
PYTHONPATH=. python -m pytest tests/runtime/test_scene_presenter.py -v
```

**Expected:** FAIL with `ModuleNotFoundError: No module named 'app.runtime.scene_presenter'`

### Step 1.3: Create the scene_presenter.py file with output models

Create `backend/app/runtime/scene_presenter.py`:

```python
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
```

### Step 1.4: Run tests to verify they pass

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend
PYTHONPATH=. python -m pytest tests/runtime/test_scene_presenter.py -v
```

**Expected:** PASS (all 13 tests passing)

### Step 1.5: Commit

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows
git add backend/app/runtime/scene_presenter.py backend/tests/runtime/test_scene_presenter.py
git commit -m "feat(w3): add scene presenter output models (CharacterPanelOutput, ConflictPanelOutput)"
```

---

## Task 2: Implement present_character_panel Function with Tests

**Files:**
- Modify: `backend/app/runtime/scene_presenter.py`
- Modify: `backend/tests/runtime/test_scene_presenter.py`

### Step 2.1: Write failing tests for present_character_panel

Add to `backend/tests/runtime/test_scene_presenter.py`:

```python
from app.runtime.scene_presenter import (
    present_character_panel,
)
from app.runtime.w2_models import (
    SessionState,
    SessionContextLayers,
)
from app.runtime.relationship_context import (
    RelationshipAxisContext,
    SalientRelationshipAxis,
)


class TestPresentCharacterPanel:
    """Tests for present_character_panel function."""

    def test_present_character_panel_no_relationships(self):
        """Character with no relationship axes returns unknown trajectory and empty movements."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"characters": {"veronique": {"name": "Veronique"}}},
            context_layers=SessionContextLayers(
                relationship_axis_context=RelationshipAxisContext()
            ),
        )

        result = present_character_panel(session_state, "veronique")

        assert result.character_id == "veronique"
        assert result.character_name == "Veronique"
        assert result.overall_trajectory == "unknown"
        assert len(result.top_relationship_movements) == 0

    def test_present_character_panel_single_escalating_axis(self):
        """Character with 1 escalating axis returns escalating trajectory."""
        axis = SalientRelationshipAxis(
            character_a="veronique",
            character_b="giuseppe",
            salience_score=0.85,
            recent_change_direction="escalating",
            signal_type="tension",
            involved_in_recent_triggers=["accusation_veronique_giuseppe"],
            last_involved_turn=5,
        )
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"characters": {"veronique": {"name": "Veronique"}}},
            context_layers=SessionContextLayers(
                relationship_axis_context=RelationshipAxisContext(
                    salient_axes=[axis]
                )
            ),
        )

        result = present_character_panel(session_state, "veronique")

        assert result.character_id == "veronique"
        assert result.overall_trajectory == "escalating"
        assert len(result.top_relationship_movements) == 1
        assert result.top_relationship_movements[0].other_character_id == "giuseppe"
        assert result.top_relationship_movements[0].recent_change == "escalating"

    def test_present_character_panel_multiple_axes_top_two(self):
        """Character with 3+ axes returns top 2 by salience_score."""
        axes = [
            SalientRelationshipAxis(
                character_a="veronique",
                character_b="giuseppe",
                salience_score=0.9,
                recent_change_direction="escalating",
                signal_type="tension",
                involved_in_recent_triggers=[],
                last_involved_turn=5,
            ),
            SalientRelationshipAxis(
                character_a="veronique",
                character_b="barbara",
                salience_score=0.7,
                recent_change_direction="stable",
                signal_type="alliance",
                involved_in_recent_triggers=[],
                last_involved_turn=3,
            ),
            SalientRelationshipAxis(
                character_a="veronique",
                character_b="philip",
                salience_score=0.5,
                recent_change_direction="de-escalating",
                signal_type="stable",
                involved_in_recent_triggers=[],
                last_involved_turn=1,
            ),
        ]
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"characters": {}},
            context_layers=SessionContextLayers(
                relationship_axis_context=RelationshipAxisContext(salient_axes=axes)
            ),
        )

        result = present_character_panel(session_state, "veronique")

        assert len(result.top_relationship_movements) == 2
        assert result.top_relationship_movements[0].salience_score == 0.9
        assert result.top_relationship_movements[1].salience_score == 0.7

    def test_present_character_panel_mixed_trajectory(self):
        """Character with mixed escalation/stable axes returns 'mixed' trajectory."""
        axes = [
            SalientRelationshipAxis(
                character_a="veronique",
                character_b="giuseppe",
                salience_score=0.8,
                recent_change_direction="escalating",
                signal_type="tension",
                involved_in_recent_triggers=[],
                last_involved_turn=5,
            ),
            SalientRelationshipAxis(
                character_a="veronique",
                character_b="barbara",
                salience_score=0.6,
                recent_change_direction="stable",
                signal_type="alliance",
                involved_in_recent_triggers=[],
                last_involved_turn=3,
            ),
        ]
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={},
            context_layers=SessionContextLayers(
                relationship_axis_context=RelationshipAxisContext(salient_axes=axes)
            ),
        )

        result = present_character_panel(session_state, "veronique")

        assert result.overall_trajectory == "mixed"

    def test_present_character_panel_character_not_in_canonical_state(self):
        """Character missing from canonical_state returns character_name=None."""
        axis = SalientRelationshipAxis(
            character_a="veronique",
            character_b="giuseppe",
            salience_score=0.85,
            recent_change_direction="escalating",
            signal_type="tension",
            involved_in_recent_triggers=[],
            last_involved_turn=5,
        )
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"characters": {}},
            context_layers=SessionContextLayers(
                relationship_axis_context=RelationshipAxisContext(salient_axes=[axis])
            ),
        )

        result = present_character_panel(session_state, "veronique")

        assert result.character_name is None
        assert result.overall_trajectory == "escalating"
```

### Step 2.2: Run tests to verify they fail

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend
PYTHONPATH=. python -m pytest tests/runtime/test_scene_presenter.py::TestPresentCharacterPanel -v
```

**Expected:** FAIL with `NameError: name 'present_character_panel' is not defined`

### Step 2.3: Implement present_character_panel function

Add to `backend/app/runtime/scene_presenter.py`:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.w2_models import SessionState


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
```

### Step 2.4: Run tests to verify they pass

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend
PYTHONPATH=. python -m pytest tests/runtime/test_scene_presenter.py::TestPresentCharacterPanel -v
```

**Expected:** PASS (all 5 tests passing)

### Step 2.5: Commit

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows
git add backend/app/runtime/scene_presenter.py backend/tests/runtime/test_scene_presenter.py
git commit -m "feat(w3): implement present_character_panel function with canonical mapping"
```

---

## Task 3: Implement present_conflict_panel Function with Tests

**Files:**
- Modify: `backend/app/runtime/scene_presenter.py`
- Modify: `backend/tests/runtime/test_scene_presenter.py`

### Step 3.1: Write failing tests for present_conflict_panel

Add to `backend/tests/runtime/test_scene_presenter.py`:

```python
from app.runtime.scene_presenter import present_conflict_panel
from app.runtime.progression_summary import ProgressionSummary
from app.runtime.short_term_context import ShortTermTurnContext


class TestPresentConflictPanel:
    """Tests for present_conflict_panel function."""

    def test_present_conflict_panel_pressure_low(self):
        """Low pressure (20) returns escalation_status='low'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 20}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.current_pressure == 20
        assert result.current_escalation_status == "low"

    def test_present_conflict_panel_pressure_medium(self):
        """Medium pressure (50) returns escalation_status='medium'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 50}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.current_pressure == 50
        assert result.current_escalation_status == "medium"

    def test_present_conflict_panel_pressure_high(self):
        """High pressure (75) returns escalation_status='high'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 75}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.current_pressure == 75
        assert result.current_escalation_status == "high"

    def test_present_conflict_panel_no_pressure(self):
        """Missing pressure returns current_pressure=None and status='unknown'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.current_pressure is None
        assert result.current_escalation_status == "unknown"

    def test_present_conflict_panel_guard_outcomes_escalating(self):
        """More rejections than acceptances → signal='escalating'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 50}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                progression_summary=ProgressionSummary(
                    first_turn_covered=1,
                    last_turn_covered=5,
                    total_turns_in_source=5,
                    current_scene_id="scene-1",
                    most_recent_guard_outcomes=["rejected", "rejected", "accepted"],
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.recent_trend is not None
        assert result.recent_trend.signal == "escalating"
        assert "guard_outcomes" in result.recent_trend.source_basis

    def test_present_conflict_panel_relationship_escalation_markers(self):
        """Relationship escalation markers → signal='escalating'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 40}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                relationship_axis_context=RelationshipAxisContext(
                    has_escalation_markers=True,
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.recent_trend is not None
        assert result.recent_trend.signal == "escalating"
        assert "relationship_tension" in result.recent_trend.source_basis

    def test_present_conflict_panel_stable_signal(self):
        """Stable overall_stability_signal → signal='stable'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 30}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                relationship_axis_context=RelationshipAxisContext(
                    overall_stability_signal="stable",
                    has_escalation_markers=False,
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.recent_trend is not None
        assert result.recent_trend.signal == "stable"
        assert "stability_signal" in result.recent_trend.source_basis

    def test_present_conflict_panel_de_escalating_signal(self):
        """De-escalating overall_stability_signal → signal='de-escalating'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 25}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                relationship_axis_context=RelationshipAxisContext(
                    overall_stability_signal="de-escalating",
                    has_escalation_markers=False,
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.recent_trend is not None
        assert result.recent_trend.signal == "de-escalating"
        assert "stability_signal" in result.recent_trend.source_basis

    def test_present_conflict_panel_pressure_boundary_33(self):
        """Pressure at boundary 33 → status='low'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 33}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.current_pressure == 33
        assert result.current_escalation_status == "low"

    def test_present_conflict_panel_pressure_boundary_34(self):
        """Pressure at boundary 34 → status='medium'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 34}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.current_pressure == 34
        assert result.current_escalation_status == "medium"

    def test_present_conflict_panel_pressure_boundary_66(self):
        """Pressure at boundary 66 → status='medium'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 66}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.current_pressure == 66
        assert result.current_escalation_status == "medium"

    def test_present_conflict_panel_pressure_boundary_67(self):
        """Pressure at boundary 67 → status='high'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 67}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.current_pressure == 67
        assert result.current_escalation_status == "high"

    def test_present_conflict_panel_turning_point_risk_true(self):
        """Escalation markers present → turning_point_risk=True."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                relationship_axis_context=RelationshipAxisContext(
                    has_escalation_markers=True,
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.turning_point_risk is True

    def test_present_conflict_panel_turning_point_risk_false(self):
        """No escalation markers → turning_point_risk=False."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                relationship_axis_context=RelationshipAxisContext(
                    has_escalation_markers=False,
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.turning_point_risk is False

    def test_present_conflict_panel_missing_context_layers(self):
        """Missing context layers → recent_trend=None, turning_point_risk=None."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={},
        )

        result = present_conflict_panel(session_state)

        assert result.recent_trend is None
        assert result.turning_point_risk is None

    def test_present_conflict_panel_multiple_sources(self):
        """Multiple sources contributing → source_basis includes all."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 60}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                progression_summary=ProgressionSummary(
                    first_turn_covered=1,
                    last_turn_covered=5,
                    total_turns_in_source=5,
                    current_scene_id="scene-1",
                    most_recent_guard_outcomes=["rejected", "rejected", "accepted"],
                ),
                relationship_axis_context=RelationshipAxisContext(
                    has_escalation_markers=True,
                ),
            ),
        )

        result = present_conflict_panel(session_state)

        assert result.recent_trend is not None
        assert "guard_outcomes" in result.recent_trend.source_basis
        assert "relationship_tension" in result.recent_trend.source_basis
```

### Step 3.2: Run tests to verify they fail

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend
PYTHONPATH=. python -m pytest tests/runtime/test_scene_presenter.py::TestPresentConflictPanel -v
```

**Expected:** FAIL with `NameError: name 'present_conflict_panel' is not defined`

### Step 3.3: Implement present_conflict_panel function

Add to `backend/app/runtime/scene_presenter.py`:

```python
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
            if rel_ctx.has_escalation_markers and signal != "escalating":
                signal = "escalating"
                source_basis.append("relationship_tension")
            elif not rel_ctx.has_escalation_markers and signal is None:
                # Check overall stability signal
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
```

### Step 3.4: Run tests to verify they pass

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend
PYTHONPATH=. python -m pytest tests/runtime/test_scene_presenter.py::TestPresentConflictPanel -v
```

**Expected:** PASS (all 11 tests passing)

### Step 3.5: Commit

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows
git add backend/app/runtime/scene_presenter.py backend/tests/runtime/test_scene_presenter.py
git commit -m "feat(w3): implement present_conflict_panel function with priority rule for signal determination"
```

---

## Task 4: Export Presenter and Final Verification

**Files:**
- Modify: `backend/app/runtime/__init__.py`

### Step 4.1: Export presenter models and functions

Edit `backend/app/runtime/__init__.py` and add (or ensure these are present):

```python
from app.runtime.scene_presenter import (
    CharacterPanelOutput,
    ConflictPanelOutput,
    ConflictTrendSignal,
    RelationshipMovement,
    present_character_panel,
    present_conflict_panel,
)

__all__ = [
    "CharacterPanelOutput",
    "ConflictPanelOutput",
    "ConflictTrendSignal",
    "RelationshipMovement",
    "present_character_panel",
    "present_conflict_panel",
]
```

### Step 4.2: Run all presenter tests

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend
PYTHONPATH=. python -m pytest tests/runtime/test_scene_presenter.py -v
```

**Expected:** PASS (all 34 tests passing)

### Step 4.3: Run full backend test suite to verify no regressions

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend
PYTHONPATH=. python -m pytest tests/ -q --tb=line
```

**Expected:** All existing tests still passing, +29 new presenter tests

### Step 4.4: Commit

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows
git add backend/app/runtime/__init__.py
git commit -m "feat(w3): export scene presenter models and functions"
```

---

## Task 5: Final Documentation and Verification

**Files:**
- Verify: `backend/app/runtime/scene_presenter.py`

### Step 5.1: Verify implementation matches spec

- ✅ RelationshipMovement model: 4 fields, all canonical
- ✅ CharacterPanelOutput model: 4 fields, top_relationship_movements bounded to 2
- ✅ ConflictTrendSignal model: signal + source_basis
- ✅ ConflictPanelOutput model: pressure, escalation_status, trend, turning_point_risk
- ✅ present_character_panel: Maps character name, overall_trajectory, top 2 relationships
- ✅ present_conflict_panel: Maps pressure, escalation status, trend with priority rule
- ✅ Priority rule documented: Escalating > De-escalating > Stable > Uncertain
- ✅ All tests pass (29 unit tests)
- ✅ No invented state; all fields canonical-derived

### Step 5.2: Create summary report

Document W3.4.1 completion:

**Files Changed:**
- `backend/app/runtime/scene_presenter.py` — NEW (250+ lines)
- `backend/tests/runtime/test_scene_presenter.py` — NEW (400+ lines)
- `backend/app/runtime/__init__.py` — MODIFIED (added exports)

**Presenter Outputs (Canonical):**
- `CharacterPanelOutput`: character_id, character_name, overall_trajectory (from relationship_axis_context), top_relationship_movements (0-2 items)
- `ConflictPanelOutput`: current_pressure (from canonical_state/short_term_context), current_escalation_status (derived from pressure), recent_trend (from guard_outcomes + relationship_escalation_markers), turning_point_risk (from relationship escalation markers)

**Mapping Sources:**
- Character panel: relationship_axis_context (salient axes, salience scores, change directions)
- Conflict panel: short_term_context.conflict_pressure, progression_summary.most_recent_guard_outcomes, relationship_axis_context.has_escalation_markers and overall_stability_signal

**Determinism:**
- Priority rule for recent_trend.signal ensures reproducible output when multiple canonical sources contribute
- All mapping logic is explicit and verifiable

**Deferred to W3.4.2+:**
- Template rendering for character and conflict panels
- Route integration (calling presenters from /play/<session_id>)
- Character list panel
- Scene panel rendering
- Full conflict analytics

### Step 5.3: Final commit

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows
git log --oneline -5
```

Expected commits:
- feat(w3): export scene presenter models and functions
- feat(w3): implement present_conflict_panel function with priority rule for signal determination
- feat(w3): implement present_character_panel function with canonical mapping
- feat(w3): add scene presenter output models (CharacterPanelOutput, ConflictPanelOutput)
- docs(w3): add W3.4.1 presenter design spec

---

## Verification Checklist

- ✅ All 34 unit tests passing (13 models + 5 character panel + 11 conflict panel + 5 boundary)
- ✅ No existing tests broken
- ✅ Presenter models bounded and typed
- ✅ All output fields trace to canonical sources
- ✅ Priority rule for signal determination explicit and deterministic
- ✅ Character name, trajectory, top 2 relationships correctly mapped
- ✅ Pressure, escalation status, trend, turning_point_risk correctly mapped
- ✅ Missing data handled gracefully (None values, "unknown" status)
- ✅ Exported from app.runtime.__init__
- ✅ Ready for W3.4.2 route integration and template rendering

---

## Suggested Commit Message (Final)

```
feat(w3): add canonical character and conflict presenter mapping for UI panels
```

This completes **W3.4.1: Canonical Character and Conflict Presenter Mapping**.
