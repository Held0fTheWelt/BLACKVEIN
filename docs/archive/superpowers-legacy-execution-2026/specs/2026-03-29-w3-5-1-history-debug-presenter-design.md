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

- **PrimaryDiagnosticOutput:** Most recent `ShortTermTurnContext` from `SessionState.context_layers.short_term_context` (W2.3.1 immediate turn context)
- **RecentPatternIndicator:** Last 3-5 entries from `SessionState.context_layers.session_history` (HistoryEntry records)
- **DegradationMarkers:** `SessionState.degraded_state.active_markers` (DegradedSessionState, W2.5.7)

**Rationale:** TurnExecutionResult is not persisted in SessionState. ShortTermTurnContext is the authoritative source for immediate turn diagnostics available to presenters. It provides turn identity, scene info, trigger detection, guard outcome, and scene transitions. More granular diagnostics (validation details, failure classification, recovery actions) are deferred to W3.5.2 pending storage design.

#### Output Models

```python
# Pydantic models in debug_presenter.py

class DebugSummarySection(BaseModel):
    """Summary diagnostics for latest turn."""
    turn_number: int
    scene_id: str  # from ShortTermTurnContext
    guard_outcome: str  # ACCEPTED, PARTIALLY_ACCEPTED, REJECTED, STRUCTURALLY_INVALID
    detected_triggers: list[str]  # from ShortTermTurnContext
    scene_changed: bool  # from ShortTermTurnContext
    prior_scene_id: Optional[str]  # if scene changed
    ending_reached: bool
    ending_id: Optional[str]  # if ending was reached
    conflict_pressure: Optional[float]  # from ShortTermTurnContext
    created_at: datetime  # when this turn was recorded

class DebugDetailedSection(BaseModel):
    """Detailed diagnostics for latest turn."""
    accepted_delta_target_count: int  # count of accepted_delta_targets from ShortTermTurnContext
    rejected_delta_target_count: int  # count of rejected_delta_targets from ShortTermTurnContext
    sample_accepted_targets: list[str]  # first 3 accepted delta target paths
    sample_rejected_targets: list[str]  # first 3 rejected delta target paths

class PrimaryDiagnosticOutput(BaseModel):
    """Typed wrapper for primary (latest turn) diagnostics."""
    summary: DebugSummarySection
    detailed: DebugDetailedSection

class RecentPatternIndicator(BaseModel):
    """Compressed pattern from recent turn (from HistoryEntry)."""
    turn_number: int
    guard_outcome: str  # ACCEPTED, PARTIALLY_ACCEPTED, REJECTED, STRUCTURALLY_INVALID
    scene_id: str
    scene_changed: bool
    ending_reached: bool

class DebugPanelOutput(BaseModel):
    """Complete debug panel presenter output."""
    primary_diagnostic: PrimaryDiagnosticOutput
    recent_pattern_context: list[RecentPatternIndicator]  # last 3-5 turns
    degradation_markers: list[str]  # active DegradedSessionState markers
```

**Removed/Deferred fields:**
- ~~`validation_outcome`~~ — not in ShortTermTurnContext or HistoryEntry; deferred to W3.5.2
- ~~`execution_status`~~ — not in ShortTermTurnContext; deferred to W3.5.2
- ~~`failure_reason`~~ — not in ShortTermTurnContext; deferred to W3.5.2
- ~~`duration_ms`~~ — not in ShortTermTurnContext; deferred to W3.5.2
- ~~`validation_errors`~~ — not in ShortTermTurnContext; deferred to W3.5.2
- ~~`raw_ai_output`~~ — in AIDecisionLog only; deferred to W3.5.2
- ~~`parsed_decision_snippet`~~ — in AIDecisionLog only; deferred to W3.5.2
- ~~`interpreter_reading`~~ — in AIDecisionLog only; deferred to W3.5.2
- ~~`director_steering`~~ — in AIDecisionLog only; deferred to W3.5.2
- ~~`responder_impulses`~~ — in AIDecisionLog only; deferred to W3.5.2
- ~~`guard_notes`~~ — in AIDecisionLog only; deferred to W3.5.2
- ~~`recovery_notes`~~ — in AIDecisionLog only; deferred to W3.5.2
- ~~`recovery_action_taken`~~ — not in accessible canonical sources; deferred to W3.5.2

**Rationale:** W3.5.1 presenter uses only fields that exist in accessible canonical sources from SessionState: ShortTermTurnContext (latest turn), HistoryEntry (recent turns), and DegradedSessionState (degradation markers). TurnExecutionResult and AIDecisionLog are not persisted in SessionState and thus not available to presenters in W3.5.1. More granular diagnostics are deferred to W3.5.2 pending storage/access design.

#### Presenter Function

```python
def present_debug_panel(session_state: SessionState) -> DebugPanelOutput:
    """
    Derive bounded diagnostic view from session's latest ShortTermTurnContext and recent HistoryEntry records.

    Targets the latest turn (from ShortTermTurnContext) as primary diagnostic object.
    Includes recent-pattern context from last 3-5 HistoryEntry records (from SessionHistory).

    Args:
        session_state: Current SessionState with context_layers.short_term_context,
                      context_layers.session_history, and degraded_state populated

    Returns:
        DebugPanelOutput with primary_diagnostic (latest turn from ShortTermTurnContext)
        + recent_pattern_context (last 3-5 from SessionHistory) + degradation_markers

    Determinism:
        - No randomness, no side effects
        - Filtering deterministic (by turn_number, by created_at)
        - Graceful degradation: returns valid output with empty/None values if data missing

    Limitation (W3.5.1):
        - Does not include TurnExecutionResult fields (validation outcomes, failure reasons, timing)
        - Does not include AIDecisionLog fields (raw output, role diagnostics, guard notes)
        - TurnExecutionResult and AIDecisionLog are not persisted in SessionState
        - Deferred to W3.5.2 pending storage design for richer diagnostics
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

**TurnExecutionResult and AIDecisionLog not available in W3.5.1:**
- TurnExecutionResult is not persisted in SessionState (only intermediate during turn execution)
- AIDecisionLog is not persisted in SessionState (only created during turn execution)
- Therefore, granular diagnostics (validation outcomes, failure classification, recovery actions, raw AI output, role diagnostics) are not available to presenters in W3.5.1
- Deferred to W3.5.2 pending design of how/where these rich diagnostics should be stored for presenter access

**W3.5.1 debug presenter scope:**
- Uses only what's immediately available: ShortTermTurnContext (latest turn) + SessionHistory (recent turns)
- Provides turn identity, scene transitions, trigger detection, guard outcomes, conflict pressure
- Does not provide validation details, failure reasons, or AI output snapshots
- This is intentional: presenter gets bounded, stable data; deeper diagnostics require storage design

**History delta counts deferred:**
- Accepted/rejected delta counts require access to delta detail data (not in HistoryEntry)
- Could be added if HistoryEntry extended or if delta tracking is stored separately
- Intentionally excluded from W3.5.1 to keep scope focused on available canonical sources

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
