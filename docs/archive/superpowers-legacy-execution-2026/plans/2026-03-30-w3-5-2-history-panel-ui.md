# W3.5.2: History Panel UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate `HistoryPanelOutput` into the playable session shell UI, rendering bounded turn history with summary and recent entries on both initial GET and post-turn POST paths.

**Architecture:** Route-driven integration where `session_view()` and `session_execute()` call `present_history_panel()` and pass result to template. Template renders summary block + recent entries table. No changes to presenter logic or runtime models.

**Tech Stack:** Flask routes, Jinja2 templates, CSS styling, pytest for testing.

---

## File Structure

| File | Responsibility |
|------|-----------------|
| `backend/app/web/routes.py` | Add presenter call and pass `history_panel` to template in both `session_view()` and `session_execute()` |
| `backend/app/web/templates/session_shell.html` | Replace history placeholder with actual panel (summary block + entries table) |
| `backend/app/web/static/styles.css` | Add history panel CSS (layout, colors, responsive) |
| `backend/tests/test_session_ui.py` | Add tests verifying history_panel in template context and HTML rendering |

---

## Task 1: Add Route Tests for History Panel

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add new test functions)
- Reference: `backend/app/web/routes.py` (session_view, session_execute signatures)
- Reference: `backend/app/runtime/history_presenter.py` (HistoryPanelOutput structure)

### Step 1: Write failing tests for session_view() history panel

```python
def test_session_view_includes_history_panel_in_context(client, test_user):
    """Verify session_view() passes history_panel to template context"""
    user, password = test_user

    # Login and create a session
    client.post("/login", data={"username": user.username, "password": password})
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage"},
        follow_redirects=False,
    )

    # Extract session_id from redirect
    session_id = response.headers["Location"].split("/play/")[-1]

    # Load session view
    response = client.get(f"/play/{session_id}")
    assert response.status_code == 200
    # Template renders history panel with summary block
    assert b"history-summary" in response.data

def test_session_view_history_panel_shows_summary_block(client, test_user):
    """Verify history panel summary block renders on GET"""
    user, password = test_user

    client.post("/login", data={"username": user.username, "password": password})
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage"},
        follow_redirects=False,
    )
    session_id = response.headers["Location"].split("/play/")[-1]

    response = client.get(f"/play/{session_id}")
    assert response.status_code == 200
    # Summary block structure visible (specific class, not just text)
    assert b"summary-stats" in response.data

def test_session_view_history_panel_shows_entries_table(client, test_user):
    """Verify history panel entries table renders on GET"""
    user, password = test_user

    client.post("/login", data={"username": user.username, "password": password})
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage"},
        follow_redirects=False,
    )
    session_id = response.headers["Location"].split("/play/")[-1]

    response = client.get(f"/play/{session_id}")
    assert response.status_code == 200
    # Entries table structure visible (specific class)
    assert b"entries-table" in response.data or b"No turn history yet" in response.data
```

### Step 2: Run tests to verify they fail

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend
PYTHONPATH=. python -m pytest tests/test_session_ui.py::test_session_view_includes_history_panel_in_context -v
PYTHONPATH=. python -m pytest tests/test_session_ui.py::test_session_view_history_panel_shows_summary_block -v
PYTHONPATH=. python -m pytest tests/test_session_ui.py::test_session_view_history_panel_shows_entries_table -v
```

**Expected:** FAIL - `history_panel` not in template context (template still shows placeholder)

### Step 3: Write tests for session_execute() history panel update

```python
def test_session_execute_includes_history_panel_after_turn(client, test_user):
    """Verify session_execute() passes updated history_panel to template after turn"""
    user, password = test_user

    client.post("/login", data={"username": user.username, "password": password})
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage"},
        follow_redirects=False,
    )
    session_id = response.headers["Location"].split("/play/")[-1]

    with client.session_transaction() as sess:
        sess["active_session"] = {
            "session_id": session_id,
            "module_id": "god_of_carnage",
            "status": "active",
        }

    # Execute a turn (POST to session_execute route)
    response = client.post(
        f"/play/{session_id}/execute",
        data={"action": "test_action"},
        follow_redirects=True,
    )
    # After turn, history panel should be rendered with summary block
    assert b"history-summary" in response.data

def test_session_execute_history_panel_shows_entries_table_after_turn(client, test_user):
    """Verify history panel entries table updates after turn execution"""
    user, password = test_user

    client.post("/login", data={"username": user.username, "password": password})
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage"},
        follow_redirects=False,
    )
    session_id = response.headers["Location"].split("/play/")[-1]

    with client.session_transaction() as sess:
        sess["active_session"] = {
            "session_id": session_id,
            "module_id": "god_of_carnage",
            "status": "active",
        }

    # Execute turn
    response = client.post(
        f"/play/{session_id}/execute",
        data={"action": "test_action"},
        follow_redirects=True,
    )
    # Entries table visible (specific class, not generic text)
    assert b"entries-table" in response.data or b"No turn history yet" in response.data
```

### Step 4: Run tests to verify they fail

```bash
PYTHONPATH=. python -m pytest tests/test_session_ui.py::test_session_execute_includes_history_panel_after_turn -v
PYTHONPATH=. python -m pytest tests/test_session_ui.py::test_session_execute_history_panel_shows_entries_table_after_turn -v
```

**Expected:** FAIL - `history_panel` not in template context on POST response

### Step 5: Commit test file with failing tests

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.2): add failing tests for history panel rendering on GET and POST"
```

---

## Task 2: Modify session_view() Route to Call Presenter

**Files:**
- Modify: `backend/app/web/routes.py` (session_view function)
- Reference: `backend/app/runtime/history_presenter.py` (present_history_panel signature)

### Step 1: Read current session_view() implementation

```bash
# View session_view() function starting at line 683
sed -n '683,710p' /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend/app/web/routes.py
```

**Expected output:** Function definition without `history_panel = present_history_panel(...)` call

### Step 2: Add import for present_history_panel

In `backend/app/web/routes.py`, find the imports section and add:

```python
from app.runtime.history_presenter import present_history_panel, HistoryPanelOutput
```

(This may already exist from W3.5.1, verify with grep)

```bash
grep "present_history_panel" /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend/app/web/routes.py
```

If not present, add to imports at top of routes.py.

### Step 3: Modify session_view() to call presenter

In `session_view()` function, after loading the session state, add:

```python
# Call presenter to get bounded history panel output
history_panel = present_history_panel(session_state)
```

Then in the `render_template()` call for session_shell.html, add:

```python
history_panel=history_panel,
```

**Exact modification:** Find the `render_template("session_shell.html", ...` line in session_view() and add `history_panel=history_panel,` to the arguments.

### Step 4: Run tests to verify they pass

```bash
PYTHONPATH=. python -m pytest tests/test_session_ui.py::test_session_view_includes_history_panel_in_context -v
PYTHONPATH=. python -m pytest tests/test_session_ui.py::test_session_view_history_panel_shows_summary_block -v
PYTHONPATH=. python -m pytest tests/test_session_ui.py::test_session_view_history_panel_shows_entries_table -v
```

**Expected:** PASS (3/3 tests pass)

### Step 5: Commit route modification

```bash
git add backend/app/web/routes.py
git commit -m "feat(w3.5.2): add history_panel to session_view() context"
```

---

## Task 3: Modify session_execute() Route to Call Presenter

**Files:**
- Modify: `backend/app/web/routes.py` (session_execute function)

### Step 1: Read current session_execute() implementation

```bash
# View the session_execute() function starting at line 778
sed -n '778,850p' /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend/app/web/routes.py
```

**Expected output:** Function that executes turn and renders response (likely has success path around line 831 and error path around line 879)

### Step 2: Add presenter call in session_execute()

In `session_execute()`, AFTER turn execution but BEFORE rendering the response, add:

```python
# Call presenter to get bounded history panel output (with updated turn data)
history_panel = present_history_panel(runtime_session.current_runtime_state)
```

**Important:** Add this call BEFORE any `render_template()` calls, so it's available to both success and error paths.

Then find ALL `render_template("session_shell.html", ...` calls in session_execute() (there are typically 2: success path around line 831, error path around line 879) and add `history_panel=history_panel,` to EACH one.

### Step 3: Run tests to verify they pass

```bash
PYTHONPATH=. python -m pytest tests/test_session_ui.py::test_session_execute_includes_history_panel_after_turn -v
PYTHONPATH=. python -m pytest tests/test_session_ui.py::test_session_execute_history_panel_shows_entries_table_after_turn -v
```

**Expected:** PASS (2/2 tests pass)

### Step 4: Run all history panel tests together

```bash
PYTHONPATH=. python -m pytest tests/test_session_ui.py -k "history_panel" -v
```

**Expected:** PASS (5/5 tests pass)

### Step 5: Commit route modification

```bash
git add backend/app/web/routes.py
git commit -m "feat(w3.5.2): add history_panel to session_execute() context on POST"
```

---

## Task 4: Create History Panel Template Section

**Files:**
- Modify: `backend/app/web/templates/session_shell.html` (replace placeholder at line 195-199)

### Step 1: Verify placeholder location

```bash
sed -n '195,199p' /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend/app/web/templates/session_shell.html
```

**Expected:** Find `<!-- History Panel Placeholder (deferred to W3.4+) -->` at lines 195-199

### Step 2: Replace placeholder with history panel template

Replace lines 195-199 with the complete history panel section from the spec:

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

### Step 3: Run tests to verify template renders

```bash
PYTHONPATH=. python -m pytest tests/test_session_ui.py -k "history_panel" -v
```

**Expected:** All history panel tests still pass (template now renders correctly)

### Step 4: Verify no template syntax errors

```bash
# Load a session view page and check for template errors
PYTHONPATH=. python -m pytest tests/test_session_ui.py::test_session_view_includes_history_panel_in_context -v
```

**Expected:** PASS - Template renders without Jinja2 syntax errors

### Step 5: Commit template modification

```bash
git add backend/app/web/templates/session_shell.html
git commit -m "feat(w3.5.2): add history panel template section with summary and entries"
```

---

## Task 5: Add CSS Styling

**Files:**
- Modify: `backend/app/web/static/styles.css` (append history panel styles)

### Step 1: Verify CSS file and read end of styles.css

```bash
# Verify file exists
ls -l /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend/app/web/static/styles.css

# Check end of file
tail -20 /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend/app/web/static/styles.css

# Verify no history panel CSS exists yet
grep -c ".history-panel" /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend/app/web/static/styles.css || echo "0 matches"
```

**Expected:** File exists, last CSS rule visible, no `.history-panel` CSS yet

### Step 2: Add history panel CSS rules

Append to end of `backend/app/web/static/styles.css`:

```css
/* ── History Panel ────────────────────────────────────────────────────────── */

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

### Step 3: Run visual test (manually load a session page)

```bash
# Start test server and manually load session page to verify CSS renders correctly
# OR run automated tests that check for CSS classes
PYTHONPATH=. python -m pytest tests/test_session_ui.py -k "history_panel" -v
```

**Expected:** History panel renders with proper styling (summary block has background color, table has borders, outcomes have colored indicators)

### Step 4: Commit CSS addition

```bash
git add backend/app/web/static/styles.css
git commit -m "style(w3.5.2): add history panel CSS (summary, table, outcome colors)"
```

---

## Task 6: Regression Test & Verification

**Files:**
- Test: `backend/tests/test_session_ui.py` (verify all existing tests still pass)

### Step 1: Run all backend tests

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend
PYTHONPATH=. python -m pytest tests/ -q --tb=short
```

**Expected:** All tests pass. Check for:
- No new failures introduced
- W3.5.2 history panel tests pass (5 new tests)
- W3.5.1 presenter tests pass (8 existing tests from task 1)
- W3.3/W3.4 session tests still pass (existing tests)

### Step 2: Verify no console warnings

```bash
# Re-run with verbose output to catch any deprecation warnings
PYTHONPATH=. python -m pytest tests/test_session_ui.py -v --tb=short
```

**Expected:** No warnings about missing `history_panel` variable in template

### Step 3: Spot-check manual test scenario

Manual verification (optional, helpful for confidence):
1. Start test server
2. Log in
3. Load `/play/<session_id>` (GET)
4. Verify history panel renders with:
   - Summary block showing session phase, turn range, scene transitions, trigger count
   - Recent entries table showing turn history (if any turns executed)
   - Message "No turn history yet." if no history
5. Execute a turn (if applicable)
6. Verify history panel updates with new entry

### Step 4: Final commit summary

```bash
# Verify all changes are committed
git status
```

**Expected:** Clean working directory (no unstaged changes)

### Step 5: Review implementation against spec

- ✓ Routes call presenter and pass `history_panel` to template
- ✓ Template renders summary block with session phase, turn range, scene transitions, trigger count
- ✓ Template renders recent entries table with turn_number, scene_id, guard_outcome, detected_triggers, scene_changed
- ✓ CSS provides compact readable format with outcome color indicators
- ✓ History panel synchronizes on both GET and POST paths
- ✓ Graceful degradation handled (empty history shows "No turn history yet.")
- ✓ W3.3 scene/state rendering preserved (not degraded)

---

## Notes for Implementer

1. **Preserve W3.3 Context:** When modifying `session_view()`, do NOT replace existing `scene`, `state_summary` variables with None. Keep them as they are. Only ADD `history_panel` to the context.

2. **Template Synchronization:** Both `session_view()` GET and `session_execute()` POST render the same `session_shell.html` template. Both must pass `history_panel` to ensure consistent history rendering on both paths.

3. **Presenter Handles Errors:** The `present_history_panel()` function (W3.5.1) already handles graceful degradation. Routes don't need error handling—presenter guarantees valid output.

4. **CSS Color Scheme:** Colors are hardcoded for dark theme consistency. If theme changes, these CSS values may need manual adjustment.

5. **Test Data:** Tests use existing test fixtures (test_user, test_session). No special test data setup needed.

6. **Commit Discipline:** Each task should be committed separately (TDD: test → implement → commit pattern). Final regression check happens after all tasks are complete.
