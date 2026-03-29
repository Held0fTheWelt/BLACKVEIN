# W3.5.1: History and Debug Presenter Mapping Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define bounded, canonical presenter outputs for history and debug panel data, derived strictly from existing runtime/logging models.

**Architecture:** Two independent presenters (history + debug) that transform raw session/logging models into UI-ready Pydantic outputs. Both are pure, deterministic, and handle missing data gracefully.

**Tech Stack:** Pydantic models, Python asyncio (existing), SQLAlchemy models (existing).

---

## Design

### File Architecture

**Files to create:**
- `backend/app/runtime/history_presenter.py` (~150 lines)
  - Pydantic models: `HistorySummary`, `RecentHistoryEntry`, `HistoryPanelOutput`
  - Presenter function: `present_history_panel(session_state: SessionState) → HistoryPanelOutput`

- `backend/app/runtime/debug_presenter.py` (~200 lines)
  - Pydantic models: `DebugSummarySection`, `DebugDetailedSection`, `PrimaryDiagnosticOutput`, `RecentPatternIndicator`, `DebugPanelOutput`
  - Presenter function: `present_debug_panel(session_state: SessionState) → DebugPanelOutput`

**Files to modify:**
- `backend/app/web/routes.py` — add presenter imports, optional test integration
- `backend/tests/test_session_ui.py` or new `backend/tests/test_presenters.py` — focused presenter tests

---

### History Presenter

#### Canonical Sources

- **HistorySummary:** `SessionState.context_layers.progression_summary` (ProgressionSummary model)
- **RecentHistoryEntry:** `SessionState.context_layers.session_history` (SessionHistory model, max 100 entries)
- **Fallback derivation:** If ProgressionSummary missing, derive from SessionHistory on-demand

#### Output Models

```python
# Pydantic models in history_presenter.py

class HistorySummary(BaseModel):
    """Compressed session progression summary."""
    session_phase: str  # "early", "middle", "late", "ended"
    total_turns_covered: int
    first_turn_number: int
    last_turn_number: int
    scene_transition_count: int
    recent_scene_ids: list[str]  # last 3-5 most recent scenes
    unique_triggers_detected: list[str]  # up to 10 most common triggers
    guard_outcome_summary: dict[str, int]  # {"ACCEPTED": 15, "REJECTED": 2, ...}
    ending_reached: bool
    ending_id: Optional[str]

class RecentHistoryEntry(BaseModel):
    """Single bounded turn history entry."""
    turn_number: int
    scene_id: str
    guard_outcome: str  # ACCEPTED, PARTIALLY_ACCEPTED, REJECTED, STRUCTURALLY_INVALID
    detected_triggers: list[str]  # triggers detected this turn
    scene_changed: bool
    prior_scene_id: Optional[str]  # if scene changed
    ending_reached: bool
    ending_id: Optional[str]  # if ending was reached
    created_at: datetime

class HistoryPanelOutput(BaseModel):
    """Complete history panel presenter output."""
    history_summary: HistorySummary
    recent_entries: list[RecentHistoryEntry]  # last 20 entries, chronological (oldest first)
    entry_count: int  # total entries in source SessionHistory (up to 100)
```

**Removed fields (not in HistoryEntry canonical source):**
- ~~`accepted_delta_count`~~ — not in HistoryEntry; dropped for W3.5.1
- ~~`rejected_delta_count`~~ — not in HistoryEntry; dropped for W3.5.1

**Rationale:** HistoryEntry carries only essential turn record (guard outcome, triggers, scene transitions, endings), not state delta counts. To include delta counts would require presenter to access AIDecisionLog separately, which is outside W3.5.1 scope.

#### Presenter Function

```python
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
```

---

### Debug Presenter

#### Canonical Sources

- **PrimaryDiagnosticOutput:** Most recent `TurnExecutionResult` from last turn execution
- **RecentPatternIndicator:** Last 3-5 entries from `SessionState.context_layers.session_history` (for turn status pattern)
- **DegradationMarkers:** `SessionState.degraded_state.active_markers` (DegradedSessionState)

**Constraint:** The presenter reads from SessionState, which must contain sufficient context. If TurnExecutionResult is not persisted in SessionState, the presenter scope is limited to HistoryEntry-derived patterns.

#### Output Models

```python
# Pydantic models in debug_presenter.py

class DebugSummarySection(BaseModel):
    """Summary diagnostics for latest turn."""
    turn_number: int
    guard_outcome: str  # ACCEPTED, PARTIALLY_ACCEPTED, REJECTED, STRUCTURALLY_INVALID
    validation_outcome: str  # from TurnExecutionResult.validation_outcome
    detected_triggers: list[str]  # from TurnExecutionResult.events or HistoryEntry
    accepted_delta_count: int  # len(TurnExecutionResult.accepted_deltas)
    rejected_delta_count: int  # len(TurnExecutionResult.rejected_deltas)
    execution_status: str  # "success", "validation_failed", "system_error"
    failure_reason: Optional[str]  # ExecutionFailureReason enum value, if failed
    duration_ms: int  # from TurnExecutionResult

class DebugDetailedSection(BaseModel):
    """Detailed diagnostics for latest turn."""
    validation_errors: Optional[list[str]]  # from TurnExecutionResult.validation_errors
    # Note: raw_ai_output, interpreter_reading, director_steering, responder_impulses
    # are in AIDecisionLog but not necessarily in TurnExecutionResult.
    # Deferred to W3.5.2 if full AIDecisionLog access is available.

class PrimaryDiagnosticOutput(BaseModel):
    """Typed wrapper for primary (latest turn) diagnostics."""
    summary: DebugSummarySection
    detailed: DebugDetailedSection

class RecentPatternIndicator(BaseModel):
    """Compressed pattern from recent turn."""
    turn_number: int
    guard_outcome: str  # last 3-5 turns' guard outcomes
    scene_changed: bool

class DebugPanelOutput(BaseModel):
    """Complete debug panel presenter output."""
    primary_diagnostic: PrimaryDiagnosticOutput
    recent_pattern_context: list[RecentPatternIndicator]  # last 3-5 turns
    degradation_markers: list[str]  # active DegradedSessionState markers
```

**Removed/Deferred fields:**
- ~~`raw_ai_output`~~ — in AIDecisionLog, not TurnExecutionResult; deferred to W3.5.2
- ~~`parsed_decision_snippet`~~ — in AIDecisionLog, not TurnExecutionResult; deferred to W3.5.2
- ~~`interpreter_reading`~~ — in AIDecisionLog (W2.4.4), not TurnExecutionResult; deferred to W3.5.2
- ~~`director_steering`~~ — in AIDecisionLog (W2.4.4), not TurnExecutionResult; deferred to W3.5.2
- ~~`responder_impulses`~~ — in AIDecisionLog, not TurnExecutionResult; deferred to W3.5.2
- ~~`guard_notes`~~ — in AIDecisionLog, not TurnExecutionResult; deferred to W3.5.2
- ~~`recovery_notes`~~ — in AIDecisionLog, not TurnExecutionResult; deferred to W3.5.2
- ~~`recovery_action_taken`~~ — in DegradedSessionState.marker but not TurnExecutionResult; deferred to W3.5.2
- ~~`failure_class`~~ — AIFailureClass enum, not in TurnExecutionResult; deferred to W3.5.2

**Rationale:** W3.5.1 presenter targets fields that exist in accessible canonical sources (TurnExecutionResult, HistoryEntry, DegradedSessionState). Full AIDecisionLog diagnostic fields (raw output, role diagnostics, detailed notes) are deferred to W3.5.2 pending clarification of how AIDecisionLog entries are persisted/accessed in SessionState.

#### Presenter Function

```python
def present_debug_panel(session_state: SessionState) -> DebugPanelOutput:
    """
    Derive bounded diagnostic view from session's TurnExecutionResult history and degradation state.

    Targets the latest turn as primary diagnostic object.
    Includes small recent-pattern context from last 3-5 HistoryEntry records.

    Args:
        session_state: Current SessionState with context_layers.session_history and degraded_state

    Returns:
        DebugPanelOutput with primary_diagnostic (latest) + recent_pattern_context (3-5 turns)

    Determinism:
        - No randomness, no side effects
        - Filtering deterministic (by turn_number DESC)
        - Graceful degradation: returns valid output with None values if data missing

    Limitation (W3.5.1):
        - Does not include AIDecisionLog diagnostic fields (raw output, role diagnostics, notes)
        - Those require separate persistence of AIDecisionLog entries in SessionState
        - Deferred to W3.5.2 pending design review
    """
```

---

### Error Handling & Graceful Degradation

**Pattern (consistent with W3.4):**

- Missing `SessionHistory` → return `HistoryPanelOutput` with `recent_entries: []` and `entry_count: 0` (not error)
- Missing `ProgressionSummary` → derive it on-demand from `SessionHistory`
- Missing `TurnExecutionResult` data → return `None` for that field (template checks `is not none`)
- Empty `DegradedSessionState` markers → return empty `degradation_markers: []`

**Example:**
```python
def present_history_panel(session_state: SessionState) -> HistoryPanelOutput:
    history = session_state.context_layers.session_history
    if not history or history.size == 0:
        # Graceful: return valid but empty output
        return HistoryPanelOutput(
            history_summary=HistorySummary(
                session_phase="early",
                total_turns_covered=0,
                # ... other fields
            ),
            recent_entries=[],
            entry_count=0
        )
    # ... normal flow
```

---

### Testing Strategy

**Tests to add (in `test_session_ui.py` or new `test_presenters.py`):**

1. `test_history_presenter_derives_from_canonical_sources()`
   - Verify HistoryPanelOutput fields come from ProgressionSummary and SessionHistory only

2. `test_history_presenter_bounds_recent_entries_to_20()`
   - Verify `recent_entries` is exactly last 20, in chronological order (oldest first)

3. `test_history_presenter_handles_empty_session_history()`
   - Verify graceful return (valid output, empty entries) when SessionHistory missing

4. `test_debug_presenter_primary_uses_latest_turn_result()`
   - Verify PrimaryDiagnosticOutput reflects most recent turn's TurnExecutionResult

5. `test_debug_presenter_recent_pattern_bounded_to_5()`
   - Verify `recent_pattern_context` is last 3-5 turns from SessionHistory, not all

6. `test_debug_presenter_degradation_markers_from_state()`
   - Verify `degradation_markers` comes from DegradedSessionState.active_markers

7. `test_presenter_outputs_are_deterministic()`
   - Call presenter twice with identical input, verify byte-for-byte identical output

8. `test_presenters_handle_none_gracefully()`
   - Verify no KeyError/AttributeError when optional fields missing; return None instead

---

## Acceptance Criteria

✅ **Canonical sources explicitly declared:**
- History: ProgressionSummary + SessionHistory
- Debug: TurnExecutionResult + DegradedSessionState
- No "via some mechanism" vagueness

✅ **Only fields from declared sources included:**
- Removed delta counts from history (not in HistoryEntry)
- Removed AIDecisionLog fields from debug (deferred to W3.5.2)
- Removed invented metrics

✅ **Typed bounded output:**
- PrimaryDiagnosticOutput wraps summary + detailed (not untyped dict)
- All models are Pydantic with explicit field types and Optional annotations

✅ **Pure, deterministic presenters:**
- No side effects
- Same input → same output always
- Graceful degradation for missing data

✅ **Ready for W3.5.2 and W3.5.3:**
- History presenter output ready for history panel template
- Debug presenter output ready for debug panel template
- Bounded outputs suitable for direct JSON serialization/API exposure

---

## Known Limitations & Deferred Work (W3.5.2+)

**AIDecisionLog diagnostic fields deferred:**
- Raw AI output, parsed decision, role diagnostics (interpreter/director/responder)
- Guard notes, recovery notes, failure classification
- Requires clarification of how AIDecisionLog entries are persisted in SessionState
- Can be added to debug presenter once access pattern is established

**History delta counts deferred:**
- Accepted/rejected delta counts require AIDecisionLog lookup
- Could be added to history presenter if HistoryEntry extended or AIDecisionLog integrated
- Intentionally excluded from W3.5.1 to keep scope focused

---

## Commit Message

```
feat(w3): add canonical history and debug presenter mapping

- define HistoryPanelOutput from ProgressionSummary + SessionHistory
- define DebugPanelOutput from TurnExecutionResult + DegradedSessionState
- both presenters are pure, deterministic, handle missing data gracefully
- bounded outputs ready for W3.5.2/3 template rendering
- explicit canonical source declaration, no invented metrics
- deferred AIDecisionLog diagnostics to W3.5.2 pending design review
```
