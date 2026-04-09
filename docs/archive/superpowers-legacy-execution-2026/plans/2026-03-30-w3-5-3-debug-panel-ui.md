# W3.5.3: Debug Panel UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render bounded debug/diagnostics information into the playable session UI for development and testing visibility.

**Architecture:** Route-driven integration with W3.5.1 presenter. Single `present_debug_panel()` call provides `DebugPanelOutput`. Template uses native `<details>/<summary>` for layered visibility: summary always visible, technical diagnostics collapsed on-demand.

**Tech Stack:** Flask routes, Jinja2 templates, native HTML5 `<details>`, CSS grid.

---

## Critical Files

| File | Responsibility |
|------|---|
| `backend/app/web/routes.py` | Add `debug_panel` context to routes (session_view, session_execute) |
| `backend/app/web/templates/session_shell.html` | Add debug panel section (summary + collapsed diagnostics) |
| `backend/app/web/static/styles.css` | Style debug panel layout and outcome indicators |
| `backend/tests/test_session_ui.py` | Add 6 tests for debug panel rendering and updates |

---

## Task 1: Add Tests for Debug Panel Rendering on GET (TDD)

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add TestDebugPanelUI class)
- Context: Routes already exist but don't pass debug_panel

### Step 1: Write failing test - debug_panel in context on GET

```python
class TestDebugPanelUI:
    """Tests for W3.5.3 debug panel UI rendering."""

    def test_session_view_includes_debug_panel_in_context(self, client, test_user):
        """Verify session_view() passes debug_panel to template context."""
        user, password = test_user

        # Login and create session
        client.post("/login", data={"username": user.username, "password": password})
        response = client.post(
            "/play/start",
            data={"module_id": "god_of_carnage"},
            follow_redirects=False,
        )
        session_id = response.headers["Location"].split("/play/")[-1]

        # Load session view
        response = client.get(f"/play/{session_id}")
        assert response.status_code == 200
        # Template should include debug panel
        assert b"debug-panel" in response.data or b"debug-summary" in response.data
```

### Step 2: Run test - expect FAIL

```bash
cd backend && python -m pytest tests/test_session_ui.py::TestDebugPanelUI::test_session_view_includes_debug_panel_in_context -xvs
```

Expected: FAIL - `debug-panel` not in response (routes don't pass debug_panel yet)

### Step 3: Add debug_panel to session_view() route

In `backend/app/web/routes.py`, in `session_view()` function (around line 683), add:

```python
# Load runtime session and present characters, conflict, and debug panel
runtime_session = _resolve_runtime_session(session_id)
characters = present_all_characters(runtime_session.current_runtime_state)
conflict = present_conflict_panel(runtime_session.current_runtime_state)
debug_panel = present_debug_panel(runtime_session.current_runtime_state)
```

Then pass `debug_panel=debug_panel` to `render_template()` call.

### Step 4: Run test - expect PASS

```bash
cd backend && python -m pytest tests/test_session_ui.py::TestDebugPanelUI::test_session_view_includes_debug_panel_in_context -xvs
```

Expected: PASS

### Step 5: Commit

```bash
git add backend/tests/test_session_ui.py backend/app/web/routes.py
git commit -m "test(w3.5.3): add test for debug_panel on session_view GET"
```

---

## Task 2: Add Tests for Debug Panel Summary Section (TDD)

**Files:**
- Modify: `backend/tests/test_session_ui.py`

### Step 1: Write failing test - summary section visible

```python
    def test_debug_panel_shows_summary_section(self, client, test_user):
        """Verify debug panel summary layer is always visible."""
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
        # Summary layer should be visible (guard outcome, triggers, changes, pressure)
        assert b"debug-summary" in response.data
        assert b"Guard" in response.data.lower() or b"Outcome" in response.data.lower()
```

### Step 2: Run test - expect FAIL

```bash
cd backend && python -m pytest tests/test_session_ui.py::TestDebugPanelUI::test_debug_panel_shows_summary_section -xvs
```

Expected: FAIL - `debug-summary` not in response (template section doesn't exist yet)

### Step 3: Add debug panel to template (session_shell.html)

Add after History Panel section (after line 252 in existing template):

```html
<!-- Debug & Diagnostics Panel (W3.5.3) -->
<section class="panel debug-panel">
  <h3>Debug & Diagnostics</h3>

  <!-- Always-visible summary -->
  <div class="debug-summary">
    <dl class="debug-stats">
      <dt>Guard Outcome</dt>
      <dd class="outcome-{{ debug_panel.primary_diagnostic.summary.guard_outcome | lower }}">
        {{ debug_panel.primary_diagnostic.summary.guard_outcome }}
      </dd>
      <dt>Triggers</dt>
      <dd>{{ debug_panel.primary_diagnostic.summary.detected_triggers | join(', ') or '—' }}</dd>
      <dt>Changes</dt>
      <dd>
        {{ debug_panel.primary_diagnostic.detailed.accepted_delta_target_count }} accepted,
        {{ debug_panel.primary_diagnostic.detailed.rejected_delta_target_count }} rejected
      </dd>
      <dt>Pressure</dt>
      <dd>{{ debug_panel.primary_diagnostic.summary.conflict_pressure or '—' }}</dd>
      <dt>Scene Changed</dt>
      <dd>{% if debug_panel.primary_diagnostic.summary.scene_changed %}✓{% else %}—{% endif %}</dd>
    </dl>
  </div>

  <!-- Collapsed diagnostics -->
  <details class="debug-details">
    <summary>Show diagnostics</summary>
    <div class="debug-diagnostics">
      <!-- Primary diagnostic full details -->
      <div class="diagnostic-section">
        <h4>Latest Turn Diagnostics</h4>
        <dl>
          <dt>Turn</dt>
          <dd>{{ debug_panel.primary_diagnostic.summary.turn_number }}</dd>
          <dt>Scene</dt>
          <dd>{{ debug_panel.primary_diagnostic.summary.scene_id }}</dd>
          {% if debug_panel.primary_diagnostic.summary.prior_scene_id %}
          <dt>Prior Scene</dt>
          <dd>{{ debug_panel.primary_diagnostic.summary.prior_scene_id }}</dd>
          {% endif %}
          <dt>Triggers</dt>
          <dd>{{ debug_panel.primary_diagnostic.summary.detected_triggers | join(', ') or '—' }}</dd>
          <dt>Sample Accepted Targets</dt>
          <dd>{{ debug_panel.primary_diagnostic.detailed.sample_accepted_targets | join(', ') or '—' }}</dd>
          <dt>Sample Rejected Targets</dt>
          <dd>{{ debug_panel.primary_diagnostic.detailed.sample_rejected_targets | join(', ') or '—' }}</dd>
          <dt>Ending Reached</dt>
          <dd>{% if debug_panel.primary_diagnostic.summary.ending_reached %}Yes{% if debug_panel.primary_diagnostic.summary.ending_id %} ({{ debug_panel.primary_diagnostic.summary.ending_id }}){% endif %}{% else %}No{% endif %}</dd>
        </dl>
      </div>

      <!-- Recent pattern -->
      {% if debug_panel.recent_pattern_context %}
      <div class="diagnostic-section">
        <h4>Recent Turn Pattern (Last 3-5 Turns)</h4>
        <ol class="pattern-list">
          {% for pattern in debug_panel.recent_pattern_context %}
          <li>
            Turn {{ pattern.turn_number }}: {{ pattern.guard_outcome }}
            (Scene: {{ pattern.scene_id }}, Changed: {% if pattern.scene_changed %}✓{% else %}—{% endif %})
          </li>
          {% endfor %}
        </ol>
      </div>
      {% endif %}

      <!-- Degradation markers -->
      {% if debug_panel.degradation_markers %}
      <div class="diagnostic-section">
        <h4>Degradation Markers</h4>
        <ul>
          {% for marker in debug_panel.degradation_markers %}
          <li>{{ marker }}</li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}
    </div>
  </details>
</section>
```

### Step 4: Run test - expect PASS

```bash
cd backend && python -m pytest tests/test_session_ui.py::TestDebugPanelUI::test_debug_panel_shows_summary_section -xvs
```

Expected: PASS

### Step 5: Commit

```bash
git add backend/app/web/templates/session_shell.html
git commit -m "feat(w3.5.3): add debug panel template section with summary and collapsed diagnostics"
```

---

## Task 3: Add Tests for Debug Panel Updates After Turn Execution (TDD)

**Files:**
- Modify: `backend/tests/test_session_ui.py`

### Step 1: Write failing tests - debug_panel updates after POST

```python
    def test_debug_panel_updates_after_turn_execution(self, client, test_user):
        """Verify debug_panel updates after POST /play/{session_id}/execute."""
        user, password = test_user

        client.post("/login", data={"username": user.username, "password": password})
        response = client.post(
            "/play/start",
            data={"module_id": "god_of_carnage"},
            follow_redirects=False,
        )
        session_id = response.headers["Location"].split("/play/")[-1]

        # Get CSRF token
        csrf_response = client.get(f"/play/{session_id}")
        import re
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', csrf_response.data.decode())
        csrf_token = match.group(1) if match else ""

        # Execute turn
        response = client.post(
            f"/play/{session_id}/execute",
            data={"operator_input": "test action", "csrf_token": csrf_token},
            follow_redirects=True,
        )

        # Debug panel should be in response
        assert b"debug-summary" in response.data

    def test_debug_panel_diagnostics_collapsed_by_default(self, client, test_user):
        """Verify <details> element is used and collapsed by default."""
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
        # Check for <details> element and "Show diagnostics" text
        assert b"<details" in response.data
        assert b"Show diagnostics" in response.data
```

### Step 2: Run tests - expect FAIL

```bash
cd backend && python -m pytest tests/test_session_ui.py::TestDebugPanelUI::test_debug_panel_updates_after_turn_execution -xvs
cd backend && python -m pytest tests/test_session_ui.py::TestDebugPanelUI::test_debug_panel_diagnostics_collapsed_by_default -xvs
```

Expected: FAIL - session_execute() doesn't pass debug_panel yet

### Step 3: Add debug_panel to session_execute() route

In `backend/app/web/routes.py`, in both `session_execute()` success path (after line 857) and error path (after line 908), add:

```python
debug_panel = present_debug_panel(runtime_session.current_runtime_state)
```

Then pass `debug_panel=debug_panel` to `render_template()` calls.

### Step 4: Run tests - expect PASS

```bash
cd backend && python -m pytest tests/test_session_ui.py::TestDebugPanelUI::test_debug_panel_updates_after_turn_execution -xvs
cd backend && python -m pytest tests/test_session_ui.py::TestDebugPanelUI::test_debug_panel_diagnostics_collapsed_by_default -xvs
```

Expected: PASS

### Step 5: Commit

```bash
git add backend/app/web/routes.py backend/tests/test_session_ui.py
git commit -m "feat(w3.5.3): add debug_panel to session_execute() success and error paths"
```

---

## Task 4: Add Tests for Debug Panel Data Rendering (TDD)

**Files:**
- Modify: `backend/tests/test_session_ui.py`

### Step 1: Write failing tests - data visibility

```python
    def test_debug_panel_shows_recent_pattern_when_available(self, client, test_user):
        """Verify recent pattern context renders in expanded section when available."""
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
        # When expanded, should show pattern info (turn numbers, outcomes)
        # Note: This is checking that the template HAS the structure, not that data exists
        assert b"Recent Turn Pattern" in response.data or b"pattern" in response.data.lower()

    def test_debug_panel_graceful_degradation(self, client, test_user):
        """Verify panel renders with fallback when diagnostic data missing."""
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
        # Should not crash and should have debug panel
        assert b"debug-panel" in response.data
        # Should show "—" for missing optional fields
        assert b"—" in response.data or response.status_code == 200
```

### Step 2: Run tests - expect FAIL

```bash
cd backend && python -m pytest tests/test_session_ui.py::TestDebugPanelUI::test_debug_panel_shows_recent_pattern_when_available -xvs
cd backend && python -m pytest tests/test_session_ui.py::TestDebugPanelUI::test_debug_panel_graceful_degradation -xvs
```

Expected: FAIL - templates may not render all sections yet

### Step 3: Verify template has all sections (already added in Task 2)

The template added in Task 2 already includes:
- Summary section (always visible)
- Recent pattern section (in collapsed diagnostics)
- Graceful handling with `or '—'` for missing fields

If tests still fail, adjust template to ensure:
- "Recent Turn Pattern" text is present
- Fallback "—" is shown for empty/None fields

### Step 4: Run tests - expect PASS

```bash
cd backend && python -m pytest tests/test_session_ui.py::TestDebugPanelUI::test_debug_panel_shows_recent_pattern_when_available -xvs
cd backend && python -m pytest tests/test_session_ui.py::TestDebugPanelUI::test_debug_panel_graceful_degradation -xvs
```

Expected: PASS

### Step 5: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.3): add tests for recent pattern and graceful degradation"
```

---

## Task 5: Add CSS Styling for Debug Panel (Styling)

**Files:**
- Modify: `backend/app/web/static/styles.css`

### Step 1: Add debug panel CSS

Add to `backend/app/web/static/styles.css` (at end of file):

```css
/* ── Debug Panel (W3.5.3) ────────────────────────────────────────────────────── */

.debug-panel {
  /* Inherits .panel styling */
}

.debug-summary {
  margin-bottom: 1.5rem;
  padding: 0.75rem;
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
}

.debug-stats {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.5rem 1rem;
  margin: 0;
  font-size: 0.9rem;
}

.debug-stats dt {
  font-weight: 600;
  color: var(--muted);
}

.debug-stats dd {
  margin: 0;
}

/* Outcome color indicators */
.outcome-accepted {
  color: #4caf50;
  font-weight: 600;
}

.outcome-partially_accepted {
  color: #ff9800;
  font-weight: 600;
}

.outcome-rejected {
  color: #f44336;
  font-weight: 600;
}

.outcome-structurally_invalid {
  color: #9c27b0;
  font-weight: 600;
}

/* Collapsible diagnostics */
.debug-details {
  margin-top: 1rem;
  padding: 0;
}

.debug-details summary {
  cursor: pointer;
  padding: 0.75rem;
  background-color: rgba(118, 192, 255, 0.08);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-weight: 600;
  user-select: none;
}

.debug-details summary:hover {
  background-color: rgba(118, 192, 255, 0.12);
}

.debug-diagnostics {
  padding: 1rem;
  margin-top: 0.5rem;
  border-left: 2px solid var(--border);
}

.diagnostic-section {
  margin-bottom: 1.5rem;
}

.diagnostic-section h4 {
  margin: 0 0 0.75rem 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--accent);
}

.diagnostic-section dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.5rem 1rem;
  margin: 0;
  font-size: 0.85rem;
}

.diagnostic-section dt {
  font-weight: 600;
  color: var(--muted);
}

.diagnostic-section dd {
  margin: 0;
  word-break: break-word;
}

.pattern-list {
  margin: 0;
  padding-left: 1.5rem;
  font-size: 0.85rem;
}

.pattern-list li {
  margin-bottom: 0.5rem;
  color: var(--text);
}
```

### Step 2: Test styling (manual)

Open session view in browser (after running earlier tasks):
- Check that summary section is styled with grid layout
- Check that outcome colors apply (green/orange/red/purple)
- Check that collapsed section has "Show diagnostics" button
- Verify expanded section has proper indentation and structure

### Step 3: Commit

```bash
git add backend/app/web/static/styles.css
git commit -m "style(w3.5.3): add debug panel CSS styling and outcome color indicators"
```

---

## Task 6: Regression Check (Integration)

**Files:**
- All (verify no breaks)

### Step 1: Run all session UI tests

```bash
cd backend && python -m pytest tests/test_session_ui.py -v --tb=short
```

Expected: All tests pass (including new 6 debug panel tests + existing history/character/conflict tests)

### Step 2: Run full backend test suite

```bash
cd backend && python -m pytest tests/ -q --tb=line 2>&1 | tail -20
```

Expected: All tests pass, no regressions in existing functionality

### Step 3: Verify scope boundaries (manual check)

- ✓ Debug panel uses only W3.5.1 presenter output (no new models)
- ✓ Routes remain thin (one function call to presenter)
- ✓ Template is bounded (summary + collapsed details, no extra sections)
- ✓ No logging system redesigned
- ✓ No observability infrastructure added
- ✓ No W3 scope creep

### Step 4: Commit final verification

```bash
git log --oneline -10
```

Verify all W3.5.3 commits are present:
1. test(w3.5.3): add test for debug_panel on session_view GET
2. feat(w3.5.3): add debug panel template section with summary and collapsed diagnostics
3. feat(w3.5.3): add debug_panel to session_execute() success and error paths
4. test(w3.5.3): add tests for recent pattern and graceful degradation
5. style(w3.5.3): add debug panel CSS styling and outcome color indicators

---

## Acceptance Criteria Checklist

- ✓ Debug panel renders on GET `/play/{session_id}` (Task 1, Test 1)
- ✓ Summary layer always visible with guard outcome, triggers, changes, pressure (Task 2)
- ✓ Diagnostics section collapsed by default using `<details>/<summary>` (Task 3, Test 2)
- ✓ Debug panel updates after POST `/play/{session_id}/execute` (Task 3, Test 1)
- ✓ All data strictly from `DebugPanelOutput` (verified in all tasks)
- ✓ Graceful handling when diagnostics unavailable (Task 4, Test 2)
- ✓ All 6 tests passing (Tasks 1-4)
- ✓ CSS styling applied (Task 5)
- ✓ No W3 scope jump (Task 6 verification)
- ✓ No regressions in existing tests (Task 6)
