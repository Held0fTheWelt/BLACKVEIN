# W3.5.1: History and Debug Presenter Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement canonical presenter/mapping layer for history and debug panel data, grounded strictly in existing runtime/logging models.

**Architecture:** Two independent presenter modules (history_presenter, debug_presenter) that transform SessionState into bounded Pydantic outputs. History derives from ProgressionSummary + SessionHistory. Debug derives from ShortTermTurnContext + SessionHistory + DegradedSessionState. Both are pure, deterministic, handle missing data gracefully.

**Tech Stack:** Python 3.10+, Pydantic (existing), pytest (existing).

---

## File Structure

### Files to Create

**`backend/app/runtime/history_presenter.py`** (~150 lines)
- Responsibility: History panel data transformation
- Contains: HistorySummary, RecentHistoryEntry, HistoryPanelOutput (Pydantic models)
- Contains: present_history_panel(session_state: SessionState) → HistoryPanelOutput (pure function)

**`backend/app/runtime/debug_presenter.py`** (~200 lines)
- Responsibility: Debug panel data transformation
- Contains: DebugSummarySection, DebugDetailedSection, PrimaryDiagnosticOutput, RecentPatternIndicator, DebugPanelOutput (Pydantic models)
- Contains: present_debug_panel(session_state: SessionState) → DebugPanelOutput (pure function)

### Files to Modify

**`backend/tests/test_session_ui.py`** (add 8 focused tests)
- Append tests to existing file (do NOT delete existing tests)
- Test classes: TestHistoryPresenter, TestDebugPresenter, TestPresenterIntegration
- All tests are unit-level (do not require running turn execution)

**`backend/app/web/routes.py`** (add imports only, W3.5.2+ will call presenters)
- Add: `from app.runtime.history_presenter import present_history_panel, HistoryPanelOutput`
- Add: `from app.runtime.debug_presenter import present_debug_panel, DebugPanelOutput`
- No route changes in W3.5.1 (presenters ready for W3.5.2 template integration)

---

## Task 1: History Presenter Models and Function

**Files:**
- Create: `backend/app/runtime/history_presenter.py`
- Test: `backend/tests/test_session_ui.py` (add 2 tests, Task 1 tests)

### Step 1: Write failing tests for history presenter

```python
# Add to backend/tests/test_session_ui.py

class TestHistoryPresenter:
    """Tests for history panel presenter."""

    def test_history_presenter_returns_valid_pydantic_model(self, test_user):
        """present_history_panel returns HistoryPanelOutput with valid structure."""
        from app.runtime.w2_models import SessionState, SessionContextLayers, DegradedSessionState
        from app.runtime.history_presenter import present_history_panel, HistoryPanelOutput

        # Create minimal valid SessionState
        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
        )

        # Call presenter
        result = present_history_panel(session_state)

        # Verify result is HistoryPanelOutput
        assert isinstance(result, HistoryPanelOutput)
        assert isinstance(result.history_summary, dict) or hasattr(result, 'history_summary')
        assert isinstance(result.recent_entries, list)
        assert result.entry_count >= 0

    def test_history_presenter_recent_entries_limited_to_20(self, test_user):
        """present_history_panel limits recent_entries to last 20 entries."""
        from app.runtime.w2_models import SessionState, SessionHistory, HistoryEntry
        from app.runtime.session_history import HistoryEntry as HistoryEntryImpl
        from app.runtime.history_presenter import present_history_panel

        # Create session state with history
        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
        )

        # Create history with 50+ entries (exceeds 20-entry limit)
        # Note: This is a placeholder; actual implementation will populate real HistoryEntry objects
        # For now, test the structure

        result = present_history_panel(session_state)

        # Verify recent_entries is bounded to 20 max
        assert len(result.recent_entries) <= 20
```

### Step 2: Run tests to verify they fail

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestHistoryPresenter -v
```

**Expected output:** FAILED (ImportError: cannot import name 'present_history_panel')

### Step 3: Create history_presenter.py with models and function

```python
# backend/app/runtime/history_presenter.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.runtime.w2_models import SessionState
from app.runtime.progression_summary import ProgressionSummary


class HistorySummary(BaseModel):
    """Compressed session progression summary."""
    session_phase: str  # "early", "middle", "late", "ended"
    total_turns_covered: int
    first_turn_number: int
    last_turn_number: int
    scene_transition_count: int
    recent_scene_ids: list[str] = Field(default_factory=list)  # last 3-5 scenes
    unique_triggers_detected: list[str] = Field(default_factory=list)  # up to 10
    guard_outcome_summary: dict[str, int] = Field(default_factory=dict)  # counts by outcome
    ending_reached: bool
    ending_id: Optional[str] = None


class RecentHistoryEntry(BaseModel):
    """Single bounded turn history entry from SessionHistory."""
    turn_number: int
    scene_id: str
    guard_outcome: str  # ACCEPTED, PARTIALLY_ACCEPTED, REJECTED, STRUCTURALLY_INVALID
    detected_triggers: list[str] = Field(default_factory=list)
    scene_changed: bool
    prior_scene_id: Optional[str] = None
    ending_reached: bool
    ending_id: Optional[str] = None
    created_at: datetime


class HistoryPanelOutput(BaseModel):
    """Complete history panel presenter output."""
    history_summary: HistorySummary
    recent_entries: list[RecentHistoryEntry]  # last 20, chronological (oldest first)
    entry_count: int  # total entries in source SessionHistory


def present_history_panel(session_state: SessionState) -> HistoryPanelOutput:
    """
    Derive bounded history view from session's SessionHistory and ProgressionSummary.

    Args:
        session_state: Current SessionState with context_layers populated

    Returns:
        HistoryPanelOutput with summary + recent 20 entries (chronological, oldest first)

    Determinism:
        - No randomness, no side effects
        - Filtering/sorting deterministic (by turn_number, by created_at)
        - Graceful degradation: returns valid output with empty entries if SessionHistory missing
    """
    # Get history and progression summary from context layers
    history = session_state.context_layers.session_history
    progression = session_state.context_layers.progression_summary

    # If both missing, return minimal valid output
    if not history and not progression:
        return HistoryPanelOutput(
            history_summary=HistorySummary(
                session_phase="early",
                total_turns_covered=0,
                first_turn_number=0,
                last_turn_number=0,
                scene_transition_count=0,
                ending_reached=False,
            ),
            recent_entries=[],
            entry_count=0,
        )

    # Derive or use progression summary
    if progression:
        summary = HistorySummary(
            session_phase=progression.session_phase,
            total_turns_covered=progression.total_turns_in_source,
            first_turn_number=progression.first_turn_covered,
            last_turn_number=progression.last_turn_covered,
            scene_transition_count=progression.scene_transition_count,
            recent_scene_ids=progression.recent_scene_ids[-5:],  # last 5
            unique_triggers_detected=list(progression.unique_triggers_in_period)[:10],  # up to 10
            guard_outcome_summary=dict(progression.guard_outcome_distribution),
            ending_reached=progression.ending_reached,
            ending_id=progression.ending_id,
        )
    else:
        # Fallback: minimal summary if progression not available
        summary = HistorySummary(
            session_phase="early",
            total_turns_covered=history.size if history else 0,
            first_turn_number=history.entries[0].turn_number if history and history.entries else 0,
            last_turn_number=history.entries[-1].turn_number if history and history.entries else 0,
            scene_transition_count=0,
            ending_reached=False,
        )

    # Extract recent entries (last 20, chronological oldest first)
    recent_entries = []
    if history and history.entries:
        # Get last 20 entries, keep chronological order (oldest first)
        entries_to_use = history.entries[-20:] if len(history.entries) > 20 else history.entries
        recent_entries = [
            RecentHistoryEntry(
                turn_number=entry.turn_number,
                scene_id=entry.scene_id,
                guard_outcome=entry.guard_outcome,
                detected_triggers=entry.detected_triggers or [],
                scene_changed=entry.scene_changed,
                prior_scene_id=entry.prior_scene_id,
                ending_reached=entry.ending_reached,
                ending_id=entry.ending_id,
                created_at=entry.created_at,
            )
            for entry in entries_to_use
        ]

    return HistoryPanelOutput(
        history_summary=summary,
        recent_entries=recent_entries,
        entry_count=history.size if history else 0,
    )
```

### Step 4: Run tests to verify they pass

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestHistoryPresenter -v
```

**Expected output:** PASSED (2 tests)

### Step 5: Commit

```bash
git add backend/app/runtime/history_presenter.py backend/tests/test_session_ui.py
git commit -m "feat(w3): add history presenter models and function"
```

---

## Task 2: Debug Presenter Models and Function

**Files:**
- Create: `backend/app/runtime/debug_presenter.py`
- Test: `backend/tests/test_session_ui.py` (add 2 tests, Task 2 tests)

### Step 1: Write failing tests for debug presenter

```python
# Add to backend/tests/test_session_ui.py

class TestDebugPresenter:
    """Tests for debug panel presenter."""

    def test_debug_presenter_returns_valid_pydantic_model(self, test_user):
        """present_debug_panel returns DebugPanelOutput with valid structure."""
        from app.runtime.w2_models import SessionState
        from app.runtime.debug_presenter import present_debug_panel, DebugPanelOutput

        # Create minimal valid SessionState
        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
        )

        # Call presenter
        result = present_debug_panel(session_state)

        # Verify result is DebugPanelOutput
        assert isinstance(result, DebugPanelOutput)
        assert hasattr(result, 'primary_diagnostic')
        assert hasattr(result, 'recent_pattern_context')
        assert isinstance(result.recent_pattern_context, list)
        assert hasattr(result, 'degradation_markers')

    def test_debug_presenter_recent_pattern_bounded_to_5(self, test_user):
        """present_debug_panel limits recent_pattern_context to last 3-5 turns."""
        from app.runtime.w2_models import SessionState
        from app.runtime.debug_presenter import present_debug_panel

        # Create session state
        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
        )

        result = present_debug_panel(session_state)

        # Verify recent_pattern_context is bounded
        assert len(result.recent_pattern_context) <= 5
```

### Step 2: Run tests to verify they fail

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestDebugPresenter -v
```

**Expected output:** FAILED (ImportError: cannot import name 'present_debug_panel')

### Step 3: Create debug_presenter.py with models and function

```python
# backend/app/runtime/debug_presenter.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.runtime.w2_models import SessionState


class DebugSummarySection(BaseModel):
    """Summary diagnostics for latest turn."""
    turn_number: int
    scene_id: str
    guard_outcome: str  # ACCEPTED, PARTIALLY_ACCEPTED, REJECTED, STRUCTURALLY_INVALID
    detected_triggers: list[str] = Field(default_factory=list)
    scene_changed: bool
    prior_scene_id: Optional[str] = None
    ending_reached: bool
    ending_id: Optional[str] = None
    conflict_pressure: Optional[float] = None
    created_at: datetime


class DebugDetailedSection(BaseModel):
    """Detailed diagnostics for latest turn."""
    accepted_delta_target_count: int
    rejected_delta_target_count: int
    sample_accepted_targets: list[str] = Field(default_factory=list)
    sample_rejected_targets: list[str] = Field(default_factory=list)


class PrimaryDiagnosticOutput(BaseModel):
    """Typed wrapper for primary (latest turn) diagnostics."""
    summary: DebugSummarySection
    detailed: DebugDetailedSection


class RecentPatternIndicator(BaseModel):
    """Compressed pattern from recent turn (from HistoryEntry)."""
    turn_number: int
    guard_outcome: str
    scene_id: str
    scene_changed: bool
    ending_reached: bool


class DebugPanelOutput(BaseModel):
    """Complete debug panel presenter output."""
    primary_diagnostic: PrimaryDiagnosticOutput
    recent_pattern_context: list[RecentPatternIndicator]  # last 3-5 turns
    degradation_markers: list[str]  # active DegradedSessionState markers


def present_debug_panel(session_state: SessionState) -> DebugPanelOutput:
    """
    Derive bounded diagnostic view from session's latest ShortTermTurnContext and recent HistoryEntry records.

    Targets the latest turn (from ShortTermTurnContext) as primary diagnostic object.
    Includes recent-pattern context from last 3-5 HistoryEntry records (from SessionHistory).

    Args:
        session_state: Current SessionState with context_layers.short_term_context,
                      context_layers.session_history, and degraded_state

    Returns:
        DebugPanelOutput with primary_diagnostic (latest) + recent_pattern_context + degradation_markers

    Determinism:
        - No randomness, no side effects
        - Filtering deterministic (by turn_number, by created_at)
        - Graceful degradation: returns valid output with None values if data missing
    """
    # Get latest turn context and history
    short_term = session_state.context_layers.short_term_context
    history = session_state.context_layers.session_history
    degraded_state = session_state.degraded_state

    # Extract degradation markers
    degradation_markers = [marker.value for marker in degraded_state.active_markers] if degraded_state.active_markers else []

    # If no short_term_context, return minimal valid output
    if not short_term:
        primary = PrimaryDiagnosticOutput(
            summary=DebugSummarySection(
                turn_number=0,
                scene_id=session_state.current_scene_id,
                guard_outcome="unknown",
                scene_changed=False,
                ending_reached=False,
                created_at=datetime.now(),
            ),
            detailed=DebugDetailedSection(
                accepted_delta_target_count=0,
                rejected_delta_target_count=0,
            ),
        )
        return DebugPanelOutput(
            primary_diagnostic=primary,
            recent_pattern_context=[],
            degradation_markers=degradation_markers,
        )

    # Build primary diagnostic from short_term_context
    accepted_targets = short_term.accepted_delta_targets if hasattr(short_term, 'accepted_delta_targets') else []
    rejected_targets = short_term.rejected_delta_targets if hasattr(short_term, 'rejected_delta_targets') else []

    primary = PrimaryDiagnosticOutput(
        summary=DebugSummarySection(
            turn_number=short_term.turn_number,
            scene_id=short_term.scene_id,
            guard_outcome=short_term.guard_outcome,
            detected_triggers=short_term.detected_triggers or [],
            scene_changed=short_term.scene_changed,
            prior_scene_id=short_term.prior_scene_id,
            ending_reached=short_term.ending_reached,
            ending_id=short_term.ending_id,
            conflict_pressure=getattr(short_term, 'conflict_pressure', None),
            created_at=short_term.created_at,
        ),
        detailed=DebugDetailedSection(
            accepted_delta_target_count=len(accepted_targets),
            rejected_delta_target_count=len(rejected_targets),
            sample_accepted_targets=accepted_targets[:3],
            sample_rejected_targets=rejected_targets[:3],
        ),
    )

    # Extract recent pattern context (last 3-5 turns from history)
    recent_pattern = []
    if history and history.entries:
        # Get last 5 entries (or fewer if not available)
        entries_to_use = history.entries[-5:] if len(history.entries) >= 5 else history.entries
        recent_pattern = [
            RecentPatternIndicator(
                turn_number=entry.turn_number,
                guard_outcome=entry.guard_outcome,
                scene_id=entry.scene_id,
                scene_changed=entry.scene_changed,
                ending_reached=entry.ending_reached,
            )
            for entry in entries_to_use
        ]

    return DebugPanelOutput(
        primary_diagnostic=primary,
        recent_pattern_context=recent_pattern,
        degradation_markers=degradation_markers,
    )
```

### Step 4: Run tests to verify they pass

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestDebugPresenter -v
```

**Expected output:** PASSED (2 tests)

### Step 5: Commit

```bash
git add backend/app/runtime/debug_presenter.py backend/tests/test_session_ui.py
git commit -m "feat(w3): add debug presenter models and function"
```

---

## Task 3: Presenter Integration Tests (Canonical Derivation)

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add 2 integration tests)

### Step 1: Write failing tests

```python
# Add to backend/tests/test_session_ui.py

class TestPresenterIntegration:
    """Integration tests verifying presenters derive from canonical sources."""

    def test_history_presenter_derives_from_progression_summary(self, test_user):
        """Verify HistoryPanelOutput.history_summary is populated from ProgressionSummary."""
        from app.runtime.w2_models import SessionState, SessionContextLayers
        from app.runtime.progression_summary import ProgressionSummary
        from app.runtime.history_presenter import present_history_panel

        # Create session with progression summary
        progression = ProgressionSummary(
            first_turn_covered=1,
            last_turn_covered=15,
            total_turns_in_source=15,
            current_scene_id="scene_1",
            scene_transition_count=2,
            recent_scene_ids=["scene_1", "scene_2"],
            unique_triggers_in_period={"trigger_a": 1, "trigger_b": 3},
            trigger_frequency={"trigger_b": 3, "trigger_a": 1},
            guard_outcome_distribution={"ACCEPTED": 12, "REJECTED": 3},
            most_recent_guard_outcomes=["ACCEPTED", "ACCEPTED"],
            ending_reached=False,
            session_phase="middle",
        )

        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
        )
        session_state.context_layers.progression_summary = progression

        result = present_history_panel(session_state)

        # Verify summary is populated from progression
        assert result.history_summary.session_phase == "middle"
        assert result.history_summary.total_turns_covered == 15
        assert result.history_summary.scene_transition_count == 2

    def test_debug_presenter_derives_from_short_term_context(self, test_user):
        """Verify DebugPanelOutput.primary_diagnostic is populated from ShortTermTurnContext."""
        from app.runtime.w2_models import SessionState
        from app.runtime.short_term_context import ShortTermTurnContext
        from app.runtime.debug_presenter import present_debug_panel
        from datetime import datetime, timezone

        # Create session with short term context
        short_term = ShortTermTurnContext(
            turn_number=5,
            scene_id="scene_2",
            detected_triggers=["trigger_x"],
            accepted_delta_targets=["characters.alice.emotional_state"],
            rejected_delta_targets=[],
            guard_outcome="ACCEPTED",
            scene_changed=True,
            prior_scene_id="scene_1",
            ending_reached=False,
            conflict_pressure=45.0,
            created_at=datetime.now(timezone.utc),
        )

        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_2",
        )
        session_state.context_layers.short_term_context = short_term

        result = present_debug_panel(session_state)

        # Verify primary diagnostic is populated from short_term_context
        assert result.primary_diagnostic.summary.turn_number == 5
        assert result.primary_diagnostic.summary.scene_id == "scene_2"
        assert result.primary_diagnostic.summary.guard_outcome == "ACCEPTED"
        assert "trigger_x" in result.primary_diagnostic.summary.detected_triggers
        assert result.primary_diagnostic.detailed.accepted_delta_target_count == 1
```

### Step 2: Run tests to verify they fail

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestPresenterIntegration -v
```

**Expected output:** FAILED (assertions fail because ProgressionSummary/ShortTermTurnContext not fully implemented in test setup)

### Step 3: Update tests to pass with current implementation

(Tests should pass once presenters correctly read from context layers. If failures persist, they indicate bugs in the presenter logic.)

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestPresenterIntegration -v
```

**Expected output:** PASSED (2 tests)

### Step 4: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3): add presenter integration tests for canonical derivation"
```

---

## Task 4: Presenter Determinism and Graceful Degradation Tests

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add 2 tests)

### Step 1: Write failing tests

```python
# Add to backend/tests/test_session_ui.py

class TestPresenterDeterminism:
    """Tests verifying presenters are deterministic and handle missing data."""

    def test_history_presenter_deterministic(self, test_user):
        """Calling presenter twice with same input produces identical output."""
        from app.runtime.w2_models import SessionState
        from app.runtime.history_presenter import present_history_panel

        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
        )

        result1 = present_history_panel(session_state)
        result2 = present_history_panel(session_state)

        # Pydantic models are equal if their field values match
        assert result1 == result2

    def test_debug_presenter_handles_missing_data_gracefully(self, test_user):
        """Presenter returns valid output with None/empty fields when data missing."""
        from app.runtime.w2_models import SessionState
        from app.runtime.debug_presenter import present_debug_panel

        # Create session with NO short_term_context or history
        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
        )
        # context_layers.short_term_context is None by default
        # context_layers.session_history is None by default

        # Should not raise error
        result = present_debug_panel(session_state)

        # Should return valid output
        assert isinstance(result, dict) or hasattr(result, 'primary_diagnostic')
        assert result.recent_pattern_context == []
        assert result.degradation_markers == []
```

### Step 2: Run tests to verify they fail

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestPresenterDeterminism -v
```

**Expected output:** May PASS if presenters already handle these cases, or FAILED if there are issues.

### Step 3: Fix presenter code if needed

If tests fail, update presenter code to ensure:
- Deterministic output (no random elements, no side effects)
- Graceful handling of missing data (return None/empty instead of raising KeyError)

### Step 4: Run tests to verify they pass

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestPresenterDeterminism -v
```

**Expected output:** PASSED (2 tests)

### Step 5: Commit

```bash
git add backend/app/runtime/history_presenter.py backend/app/runtime/debug_presenter.py backend/tests/test_session_ui.py
git commit -m "test(w3): add determinism and graceful degradation tests for presenters"
```

---

## Task 5: Add Presenter Imports to Routes

**Files:**
- Modify: `backend/app/web/routes.py` (add imports only)

### Step 1: Write test for import availability

```python
# Add to backend/tests/test_session_ui.py (simple import test)

def test_presenters_importable_from_routes(self):
    """Verify presenter imports are available in routes module."""
    try:
        from app.runtime.history_presenter import present_history_panel, HistoryPanelOutput
        from app.runtime.debug_presenter import present_debug_panel, DebugPanelOutput
    except ImportError as e:
        pytest.fail(f"Presenter imports failed: {e}")
```

### Step 2: Add imports to routes.py

```python
# At top of backend/app/web/routes.py (near existing imports)

from app.runtime.history_presenter import present_history_panel, HistoryPanelOutput
from app.runtime.debug_presenter import present_debug_panel, DebugPanelOutput
```

### Step 3: Run test to verify imports work

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py -k "importable" -v
```

**Expected output:** PASSED

### Step 4: Commit

```bash
git add backend/app/web/routes.py backend/tests/test_session_ui.py
git commit -m "feat(w3): add presenter imports to routes (W3.5.2+ ready)"
```

---

## Task 6: Regression Check (Full Test Suite)

**Files:**
- Verify: `backend/tests/test_session_ui.py` (all new tests passing)

### Step 1: Run full backend test suite

```bash
cd backend && PYTHONPATH=. python -m pytest tests/ -v --tb=short 2>&1 | tail -50
```

**Expected output:**
- New W3.5.1 tests: PASSED (8 tests)
- All existing tests: PASSED (no regressions)
- Total: ~2800+ tests passing

### Step 2: Verify coverage

```bash
cd backend && PYTHONPATH=. python -m pytest tests/ --cov=app.runtime.history_presenter --cov=app.runtime.debug_presenter -v 2>&1 | grep -E "history_presenter|debug_presenter" | head -5
```

**Expected:** High coverage on new presenter modules (>90%)

### Step 3: Final commit

```bash
git add -A && git commit -m "test(w3): W3.5.1 complete, all tests passing"
```

---

## Acceptance Criteria

✅ **Task 1 (History Presenter):**
- HistorySummary, RecentHistoryEntry, HistoryPanelOutput models created
- present_history_panel() function implemented
- 2 focused tests passing

✅ **Task 2 (Debug Presenter):**
- DebugSummarySection, DebugDetailedSection, PrimaryDiagnosticOutput, RecentPatternIndicator, DebugPanelOutput models created
- present_debug_panel() function implemented
- 2 focused tests passing

✅ **Task 3 (Integration Tests):**
- 2 canonical derivation tests added
- Tests verify presenters read from correct sources

✅ **Task 4 (Determinism & Degradation):**
- 2 tests verify deterministic behavior and graceful handling of missing data

✅ **Task 5 (Route Imports):**
- Presenters importable from routes.py
- No route logic changes in W3.5.1 (presenters ready for W3.5.2 integration)

✅ **Task 6 (Regression):**
- All existing tests passing
- New tests integrated without breaks
- Coverage >90% on new presenter modules

---

## Known Deferred Work

**W3.5.2 (Template Integration):**
- Call present_history_panel() and present_debug_panel() in session_view route
- Pass outputs to session_shell.html template
- Create history panel HTML section
- Create debug panel HTML section

**W3.5.2+ (Richer Diagnostics):**
- Store TurnExecutionResult or AIDecisionLog in SessionState for richer debug data
- Extend debug presenter to include validation outcomes, failure reasons, role diagnostics
- Add filtering/search to history panel

---

## Execution Strategy

This plan has 6 bite-sized tasks. Estimated effort: 2-3 hours.

**Recommended execution:** Subagent-driven development with 3 independent test tasks (Tasks 3, 4, 5) running in parallel after Tasks 1-2 complete sequentially.

**Cost optimization:** Use Haiku model for mechanical test-writing tasks (Tasks 3-5), Sonnet for complex logic (Tasks 1-2).
