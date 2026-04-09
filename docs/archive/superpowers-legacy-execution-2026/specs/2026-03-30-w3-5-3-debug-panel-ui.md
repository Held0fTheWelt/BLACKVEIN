# W3.5.3: Debug Panel UI Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render bounded debug/diagnostics information into the playable session UI for development and testing visibility.

**Architecture:** Route-driven integration with W3.5.1 presenter. One `present_debug_panel()` call supplies all data. Template uses native HTML `<details>` element for layered visibility: summary always visible, technical diagnostics collapsed on-demand.

**Tech Stack:** Flask routes, Jinja2 templates, native HTML5 `<details>/<summary>`, CSS grid/flexbox.

---

## Context

W3.5.1 established the presenter/mapping layer (`present_debug_panel()` → `DebugPanelOutput`) that transforms canonical diagnostics into bounded output.

W3.5.3 now renders this presenter output into the playable session UI, enabling:
- Players to see turn outcomes and state changes in readable form
- Developers/QA to access detailed diagnostics for test and debug without cluttering the main view

---

## Design Decisions

### Audience & Visibility Model

**Primary Audience:** Both players and developers

**Visibility Layers:**
1. **Summary (Always Visible)**: Guard outcome, triggers, changes, pressure — readable at a glance
2. **Diagnostics (Collapsed)**: Detailed turn info, pattern context, degradation markers — revealed with "Show diagnostics" control

**Rationale:** Keeps the UI usable during normal play/testing while exposing development-critical diagnostics on-demand. Avoids cluttering the main panel with technical data.

### Implementation Pattern

**Collapsible Section with Native HTML:**
- Use semantic `<details>/<summary>` elements (accessible, no JavaScript required)
- Summary always visible
- Diagnostics section collapsed by default
- One `present_debug_panel()` call in route supplies all data
- Template controls visibility through HTML structure

**Why:** Simplest MVP implementation, accessible by default, no custom JS, bounded data (W3.5.1 presenter output).

---

## Canonical Data Contract

**Data Source:** `DebugPanelOutput` from `present_debug_panel(session_state: SessionState)`

**Structure:**
```python
DebugPanelOutput {
  primary_diagnostic: PrimaryDiagnosticOutput {
    summary: DebugSummarySection {
      turn_number: int
      scene_id: str
      guard_outcome: str  # ACCEPTED, PARTIALLY_ACCEPTED, REJECTED, STRUCTURALLY_INVALID
      detected_triggers: list[str]
      scene_changed: bool
      prior_scene_id: Optional[str]
      ending_reached: bool
      ending_id: Optional[str]
      conflict_pressure: Optional[float]
      created_at: datetime
    }
    detailed: DebugDetailedSection {
      accepted_delta_target_count: int
      rejected_delta_target_count: int
      sample_accepted_targets: list[str]
      sample_rejected_targets: list[str]
    }
  }
  recent_pattern_context: list[RecentPatternIndicator] {
    turn_number: int
    guard_outcome: str
    scene_id: str
    scene_changed: bool
    ending_reached: bool
  }
  degradation_markers: list[str]
}
```

**Template Constraint:** Use ONLY these exact fields. No UI-invented diagnostic data.

---

## Files to Modify

| File | Scope |
|------|-------|
| `backend/app/web/routes.py` | Add `debug_panel` to `session_view()` and `session_execute()` context |
| `backend/app/web/templates/session_shell.html` | Add debug panel section with `<details>` collapsible and summary/diagnostics layers |
| `backend/app/web/static/styles.css` | Style debug panel (summary grid, collapsed/expanded states, outcome color indicators) |
| `backend/tests/test_session_ui.py` | Add 6 tests for debug panel rendering and updates |

---

## Component Design

### Route Integration

**In `session_view()`:**
```python
debug_panel = present_debug_panel(runtime_session.current_runtime_state)
return render_template("session_shell.html", ..., debug_panel=debug_panel)
```

**In `session_execute()`:**
```python
debug_panel = present_debug_panel(runtime_session.current_runtime_state)
return render_template("session_shell.html", ..., debug_panel=debug_panel)
```

Both success and error paths include debug panel (shows state at time of error).

### Template Structure

**Summary Layer (always visible):**
- Guard outcome (with outcome-based color: green=accepted, orange=partial, red=rejected, purple=invalid)
- Detected triggers (comma-separated list)
- Accepted/rejected change counts
- Conflict pressure (numeric value or "—" if None)
- Scene changed indicator

**Expanded Diagnostics (collapsed `<details>`):**
- **Primary Diagnostic Detail:**
  - Turn number
  - Scene ID (current and prior if available)
  - Guard outcome (full)
  - Detected triggers (full list)
  - Sample accepted targets (up to 5, or "—")
  - Sample rejected targets (up to 5, or "—")
  - Ending reached + ending ID (if applicable)
- **Recent Pattern Context (Last 3-5 turns):**
  - Turn number, guard outcome, scene ID, scene changed, ending reached status
- **Degradation Markers:**
  - List of active recovery/fallback states from DegradedSessionState

### CSS Styling

- `.debug-panel`: Standard panel container
- `.debug-summary`: Grid layout for quick-scan fields (definition list or grid)
- `details.debug-details`: Native `<details>` element (minimal custom styling)
- `.debug-diagnostics`: Container for expanded sections
- `.diagnostic-section`: Grouped sections with clear headers
- Outcome color indicators: `.outcome-accepted`, `.outcome-partially_accepted`, `.outcome-rejected`, `.outcome-structurally_invalid`

### Graceful Degradation

**Canonical Rule:** `primary_diagnostic` is always present (presenter guarantees valid output).

- `primary_diagnostic` always exists and is rendered (never None)
- Graceful degradation happens via empty/None **fields within** `primary_diagnostic`:
  - Empty `detected_triggers` list → render empty or "—"
  - None `conflict_pressure` → render "—"
  - None `prior_scene_id` → render "—"
  - Empty `sample_accepted_targets` / `sample_rejected_targets` → render "—"
- If `recent_pattern_context` is empty: Skip that section (or show "No recent turns")
- If `degradation_markers` is empty: Skip that section (or show "No degradation markers")
- All Optional fields render as "—" when None; all empty lists render as "—" or omitted

---

## Testing Requirements

Add 6 tests to `TestDebugPanelUI` in `backend/tests/test_session_ui.py`:

1. `test_session_view_includes_debug_panel_in_context` — Verify debug_panel passed to template on GET
2. `test_debug_panel_shows_summary_section` — Verify summary layer always visible (guard outcome, triggers, changes, pressure)
3. `test_debug_panel_diagnostics_initially_collapsed` — Verify expanded section uses `<details>` and starts collapsed
4. `test_debug_panel_updates_after_turn_execution` — Verify debug_panel updates after POST turn execution
5. `test_debug_panel_shows_recent_pattern_when_available` — Verify recent pattern context renders when expanded
6. `test_debug_panel_graceful_degradation` — Verify panel renders with fallback text when diagnostics unavailable

All tests follow TDD pattern: failing test → implementation → passing test.

---

## Acceptance Criteria

- ✓ Debug panel renders on GET `/play/{session_id}`
- ✓ Summary layer always visible (guard outcome, triggers, changes, pressure)
- ✓ Diagnostics section collapsed by default, expandable with "Show diagnostics"
- ✓ Debug panel updates after POST `/play/{session_id}/execute`
- ✓ All data strictly from `DebugPanelOutput` (no UI-invented fields)
- ✓ Graceful handling when diagnostics unavailable
- ✓ All 6 tests passing
- ✓ No W3 scope jump (diagnostics panel only, no observability infrastructure)
- ✓ No regressions in existing tests

---

## Intentionally Deferred

- **Raw AI decision logs** — Requires separate AIDecisionLog persistence (W3.5.2+ scope)
- **Validation failure details** — Requires TurnExecutionResult logging (W3.5.2+ scope)
- **Interactive filtering/search** — Out of W3.5 scope
- **Export/analytics** — Out of W3 scope
- **Module-specific diagnostics** — No module hacks (W3 constraint)

---

## Hard Constraints (Preserved)

- Keep scope tightly limited to debug/diagnostics panel
- Surface bounded canonical diagnostic data only
- Do not redesign the logging system
- Do not add large observability infrastructure
- Do not invent fake diagnostics
- Do not add module-specific hacks
- Stay within W3 scope
