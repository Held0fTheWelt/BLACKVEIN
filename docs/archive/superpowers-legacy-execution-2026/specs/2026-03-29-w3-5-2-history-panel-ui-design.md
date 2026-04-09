# W3.5.2: History Panel UI Design Spec

> **Context:** W3.5.1 delivered canonical presenter/mapping layer (`HistoryPanelOutput`, `present_history_panel()`). W3.5.2 integrates this into the playable session view UI, rendering bounded history with summary + recent entries.

**Goal:** Render `HistoryPanelOutput` in the session shell, showing turn history with important events/state changes in a bounded, readable format.

**Scope:** History panel UI integration only. No changes to presenter logic, session execution, or runtime models.

---

## Requirements

1. **Render bounded history** — Show last 20 turns (from `HistoryPanelOutput.recent_entries`), chronologically oldest-first
2. **Two-tier display** — Summary block for orientation + recent entries table for sequence
3. **Canonical data** — History panel renders only from `HistoryPanelOutput` (derived from `SessionHistory` + `ProgressionSummary`)
4. **Synchronization** — History panel must render correctly on both initial GET and post-turn POST
5. **Graceful degradation** — Return valid output with empty/minimal data if history missing
6. **Readable compact format** — Recent entries display in compact rows, scannable and detailed-on-demand

---

## Architecture

**Pattern:** Route-driven integration (thin routes, pure presenters, bounded template rendering)

**Scope:** W3.5.2 extends W3.3's initial session-shell render with history visibility. Does not degrade existing scene/state rendering on GET path.

**Routes:**
- `session_view()` (GET) — calls `present_history_panel(session_state)`, passes `history_panel` to template alongside existing W3.3 context
- `session_execute()` (POST) — calls `present_history_panel(updated_session_state)`, passes `history_panel` to template

**Presenter:**
- `present_history_panel(session_state: SessionState) → HistoryPanelOutput` (W3.5.1)
- Pure function: no side effects, deterministic, graceful degradation

**Template:**
- Renders `history_panel.history_summary` as summary block
- Renders `history_panel.recent_entries` as compact recent-entries table
- No null checks (presenter guarantees valid output)

---

## Components

### Route Modifications: `backend/app/web/routes.py`

**In `session_view()` function (after loading session):**
```python
from app.runtime.history_presenter import present_history_panel

# Add history panel to existing context (preserves W3.3 scene/state rendering)
history_panel = present_history_panel(session_state)
return render_template(
    "session_shell.html",
    session_data=active,
    history_panel=history_panel,
    # scene, state_summary already present from W3.3 (keep existing context)
    # ... continue with existing context variables
)
```

**Note:** W3.5.2 extends W3.3's initial session-shell render by adding `history_panel`. The existing scene/state context is preserved, not replaced with None values.

**In `session_execute()` function (after turn execution, before rendering response):**
```python
updated_session_state = ... # from dispatcher or context
history_panel = present_history_panel(updated_session_state)
return render_template(
    "session_shell.html",
    session_data=updated,
    history_panel=history_panel,
    # ... other context variables
)
```

### Template Modification: `backend/app/web/templates/session_shell.html`

**Replace placeholder at line 195-199 with:**

```html
<!-- History Panel -->
<section class="panel history-panel">
  <h3>History</h3>

  <!-- Summary Block -->
  <div class="history-summary">
    <dl class="summary-stats">
      <dt>Phase</dt><dd>{{ history_panel.history_summary.session_phase }}</dd>
      <dt>Turns</dt><dd>{{ history_panel.history_summary.first_turn_number }} – {{ history_panel.history_summary.last_turn_number }}</dd>
      <dt>Scenes</dt><dd>{{ history_panel.history_summary.scene_transition_count }} transitions</dd>
      <dt>Triggers</dt><dd>{{ history_panel.history_summary.unique_triggers_detected | length }}</dd>
    </dl>
  </div>

  <!-- Recent Entries Table -->
  <div class="history-recent-entries">
    {% if history_panel.recent_entries %}
      <table class="entries-table">
        <thead>
          <tr>
            <th>Turn</th>
            <th>Scene</th>
            <th>Outcome</th>
            <th>Events</th>
            <th>Changed</th>
          </tr>
        </thead>
        <tbody>
          {% for entry in history_panel.recent_entries %}
            <tr class="entry-row outcome-{{ entry.guard_outcome | lower }}">
              <td class="turn-number">{{ entry.turn_number }}</td>
              <td class="scene-id">{{ entry.scene_id }}</td>
              <td class="guard-outcome">{{ entry.guard_outcome }}</td>
              <td class="detected-triggers">
                {% if entry.detected_triggers %}
                  {{ entry.detected_triggers | join(', ') }}
                {% else %}
                  —
                {% endif %}
              </td>
              <td class="scene-changed">
                {% if entry.scene_changed %}
                  <span class="indicator-changed">✓</span>
                {% else %}
                  —
                {% endif %}
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    {% else %}
      <p class="muted">No turn history yet.</p>
    {% endif %}
  </div>

  <p class="entry-count">{{ history_panel.entry_count }} total entries</p>
</section>
```

**CSS (add to `backend/app/web/static/styles.css`):**

```css
.history-panel {
  /* Inherits .panel styling */
}

.history-summary {
  margin-bottom: 1.5rem;
  padding: 0.75rem;
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
}

.summary-stats {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.5rem 1rem;
  margin: 0;
  font-size: 0.9rem;
}

.summary-stats dt {
  font-weight: 600;
  color: #666;
}

.summary-stats dd {
  margin: 0;
}

.entries-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  margin-bottom: 1rem;
}

.entries-table thead {
  background-color: #f5f5f5;
  border-bottom: 2px solid #ddd;
}

.entries-table th {
  padding: 0.5rem;
  text-align: left;
  font-weight: 600;
  color: #333;
}

.entries-table td {
  padding: 0.5rem;
  border-bottom: 1px solid #e0e0e0;
}

.entry-row:hover {
  background-color: #f9f9f9;
}

.entry-row.outcome-accepted {
  border-left: 3px solid #4caf50;
}

.entry-row.outcome-partially_accepted {
  border-left: 3px solid #ff9800;
}

.entry-row.outcome-rejected {
  border-left: 3px solid #f44336;
}

.entry-row.outcome-structurally_invalid {
  border-left: 3px solid #9c27b0;
}

.turn-number {
  font-weight: 600;
  color: #0066cc;
}

.scene-id {
  font-family: monospace;
  font-size: 0.8rem;
  color: #666;
}

.guard-outcome {
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.75rem;
}

.detected-triggers {
  font-size: 0.8rem;
  color: #555;
}

.scene-changed .indicator-changed {
  color: #4caf50;
  font-weight: bold;
}

.entry-count {
  font-size: 0.85rem;
  color: #999;
  margin-top: 0.5rem;
}

.muted {
  color: #999;
  font-style: italic;
}
```

**Color scheme note:** The CSS uses hardcoded hex colors for dark theme consistency. If the codebase updates its CSS variable theme in the future, these color values may need manual adjustment. Current palette matches existing `.panel` and table styling.



---

## Data Flow

```
SessionState (with context_layers)
  ├─ context_layers.session_history (SessionHistory)
  └─ context_layers.progression_summary (ProgressionSummary)
        ↓
session_view() or session_execute()
        ↓
present_history_panel(session_state)
  ├─ reads session_history.entries (last 20)
  ├─ derives HistorySummary from progression_summary
  └─ returns HistoryPanelOutput { history_summary, recent_entries, entry_count }
        ↓
Template renders:
  ├─ Summary block (session_phase, turn range, scene transitions, trigger count)
  └─ Recent entries table (turn_number, scene_id, guard_outcome, triggers, scene_changed)
        ↓
User sees bounded, chronological turn history
```

**Synchronization:**
- Both GET and POST paths call `present_history_panel()` and pass result to template
- History panel stays synchronized across initial load and post-turn updates

---

## Error Handling

**Route level:** No special error handling.
- `present_history_panel()` guarantees valid `HistoryPanelOutput` (graceful degradation in presenter)
- Template renders `history_panel` directly without null checks

**Presenter level:** Handles all edge cases (W3.5.1 responsibility).
- Missing `session_history` → `recent_entries = []`
- Missing `progression_summary` → minimal valid `history_summary` (zeros, no phase info)
- Always returns valid `HistoryPanelOutput`

**Template level:** Renders what's provided.
- If `recent_entries` empty → shows "No turn history yet."
- If summary fields present → renders them; if not, renders gracefully

---

## Testing

**Route tests** (`backend/tests/test_session_ui.py`):

1. **GET `session_view()` renders history panel**
   - Load session
   - Verify `history_panel` in template context
   - Verify rendered HTML contains `<section class="history-panel">`
   - Verify summary block rendered (phase, turn range, transitions, triggers)
   - Verify recent entries table rendered (if data present)

2. **POST `session_execute()` updates history panel**
   - Execute turn
   - Verify updated `history_panel` in template context
   - Verify rendered HTML includes new entry (turn_number incremented, timestamp updated)
   - Verify entry_count incremented

3. **Graceful degradation**
   - Create session with missing session_history (tests presenter robustness from W3.5.1)
   - Verify history_panel renders with empty recent_entries (presenter returns valid output)
   - Verify "No turn history yet." message displays (template renders gracefully)
   - Verify entry_count = 0 (presenter handles missing data)
   - Note: This test primarily validates the presenter's existing graceful degradation; route/template assume valid presenter output

4. **History panel synchronization**
   - Load session (GET) → verify summary + entries rendered
   - Execute turn (POST) → verify summary updated + new entry visible
   - Verify panel stays synchronized across both paths

**Presenter tests:** Already covered in W3.5.1.

---

## Implementation Steps

1. **Modify `session_view()` route** — Call `present_history_panel()`, pass to template
2. **Modify `session_execute()` route** — Call `present_history_panel()`, pass to template
3. **Create history panel template section** — Summary block + recent entries table
4. **Add CSS styling** — Compact readable format with outcome color indicators
5. **Add route tests** — Verify both GET and POST render history panel with correct content
6. **Commit** — All changes in single commit

---

## Verification

**Manual end-to-end:**
1. Load session → See summary block with phase/turn range/transitions/triggers
2. See recent entries table with last 20 turns (chronological)
3. Execute turn → History panel updates, new entry appears, entry_count increments
4. Verify summary block also updated if progression changed

**Automated tests:**
- Route tests verify history_panel passed to template
- Route tests verify rendered HTML contains summary + entries sections
- Route tests verify history panel updates after turn execution
- Integration tests verify synchronization on both GET and POST paths

---

## Canonical Rules

1. **Route-driven integration** — Routes call presenter, pass bounded output to template
2. **Presenter owns graceful degradation** — Presenter guarantees valid output; routes/template don't need error handling
3. **Synchronization requirement** — Both `session_view()` and `session_execute()` must call presenter
4. **Template renders prepared output** — No logic in template, just render what presenter provides
5. **Generic presenter design** — `HistoryPanelOutput` module-agnostic, extensible for future scenarios
6. **Canonical data sources** — History panel derives only from `SessionHistory` + `ProgressionSummary`
