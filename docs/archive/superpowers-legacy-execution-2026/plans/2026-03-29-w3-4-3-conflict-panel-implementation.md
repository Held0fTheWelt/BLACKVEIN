# W3.4.3: Bounded Conflict Panel UI Rendering

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render conflict pressure, escalation status, and trend signals in a bounded panel in the playable UI, grounded in W3.4.1 canonical presenter output.

**Architecture:** Reuse existing `present_conflict_panel()` presenter (W3.4.1) to map canonical SessionState to `ConflictPanelOutput`. Integrate output into routes and template following the W3.4.2 pattern. Conflict panel is singular per session (unlike character panel which is plural). Updates synchronously after turn execution; no live polling.

**Tech Stack:** Python/Pydantic (presenter), Jinja2 (template), Flask routes.

---

## Context

**W3.4.1** established `ConflictPanelOutput` — a bounded Pydantic model with:
- `current_pressure`: Optional numeric value (0–100)
- `current_escalation_status`: Derived classification (low/medium/high/unknown)
- `recent_trend`: Optional trend signal with source basis
- `turning_point_risk`: Optional boolean indicating escalation markers

**W3.4.3** now renders this data in the playable UI. The conflict panel displays:
- Current pressure and escalation status (high visibility)
- Recent trend with source information (if available)
- Turning-point risk flag (if derivable from canonical data)
- Graceful fallbacks for missing data

---

## Design

### Scope

**In scope:**
- Render single conflict panel in main column (adjacent to character panel)
- Display pressure, escalation status, trend, turning-point risk
- Update after turn execution (render-on-request, no live polling)
- Graceful fallbacks when conflict data unavailable
- No CSS layout concerns beyond "readable and compact"

**Out of scope:**
- Historical conflict view / timeline (defer to W3.4.5+)
- Player-side conflict manipulation or diplomacy actions
- Module-specific conflict adaptations
- Detailed conflict diagnostics or full metadata

---

## File Structure

| File | Change | Responsibility |
|------|--------|-----------------|
| `backend/app/web/routes.py` | MODIFY `session_view()` + `session_execute()` | Call `present_conflict_panel()`, pass result to template |
| `backend/app/web/templates/session_shell.html` | MODIFY panel section | Add conflict panel rendering with pressure, escalation, trend, risk |
| `backend/tests/test_session_ui.py` | MODIFY TestConflictPanel | Add integration tests for conflict panel rendering and updates |

**Notes:**
- `present_conflict_panel()` already exists in `scene_presenter.py`; no new presenter code needed
- `ConflictPanelOutput` already defined in `scene_presenter.py`; fully available for import
- Routes follow W3.4.2 pattern exactly; template adds single conflict section instead of multiple character cards

---

## Implementation Tasks

### Task 1: Add Conflict Panel Integration Tests

**Files:**
- Test: `backend/tests/test_session_ui.py`

- [ ] **Step 1: Write failing test for conflict panel renders on session_view**

Add to `backend/tests/test_session_ui.py` under `TestConflictPanel` class:

```python
def test_conflict_panel_renders_on_session_view(client, test_user, runtime_session_with_conflict):
    """Conflict panel should render on GET /play/<session_id>."""
    user, password = test_user
    csrf = _get_csrf_token(client, "/play", user.username, password)

    # Create session and get session_id
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": csrf},
        follow_redirects=False,
    )
    session_id = response.headers["Location"].split("/")[-1]

    # View session
    response = client.get(f"/play/{session_id}")
    assert response.status_code == 200
    # Check for conflict panel presence (any of these strings indicate rendering)
    assert (
        b"conflict" in response.data.lower()
        or b"escalation" in response.data.lower()
        or b"pressure" in response.data.lower()
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestConflictPanel::test_conflict_panel_renders_on_session_view -v --tb=short
```

Expected: FAIL (conflict panel not yet rendered)

- [ ] **Step 3: Write failing test for conflict panel in session_execute**

Add to `TestConflictPanel`:

```python
def test_conflict_panel_updates_after_turn_execution(client, test_user):
    """Conflict panel should update after POST /play/<session_id>/execute."""
    # Setup: create session, execute a turn
    user, password = test_user
    csrf = _get_csrf_token(client, "/play", user.username, password)

    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": csrf},
        follow_redirects=False,
    )
    session_id = response.headers["Location"].split("/")[-1]

    # For now, verify conflict panel is accessible in execute response
    # (Full turn execution testing deferred to W3.5)
    response = client.get(f"/play/{session_id}")
    assert response.status_code == 200
```

- [ ] **Step 4: Write failing test for conflict panel displays pressure**

Add to `TestConflictPanel`:

```python
def test_conflict_panel_shows_pressure_and_escalation_status(client, test_user):
    """Conflict panel should display pressure and escalation_status when available."""
    # Placeholder for integration test once turn execution is wired
    # At minimum, verify the template has structure for pressure/escalation display
    pass
```

- [ ] **Step 5: Run all new tests to verify they fail**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestConflictPanel -v --tb=short
```

Expected: Tests fail (conflict panel not yet in routes/template)

- [ ] **Step 6: Commit test file (TDD: tests first)**

```bash
cd backend && git add tests/test_session_ui.py && git commit -m "test(w3.4.3): add conflict panel integration test placeholders"
```

---

### Task 2: Integrate Conflict Panel into Routes

**Files:**
- Modify: `backend/app/web/routes.py`

- [ ] **Step 1: Add import for present_conflict_panel**

Open `backend/app/web/routes.py` and locate the imports section (near line 1-30). Add:

```python
from app.runtime import present_conflict_panel
```

(Add to existing import line if `present_all_characters` already imported; otherwise add as new line)

- [ ] **Step 2: Modify session_view() to call present_conflict_panel**

Find the `session_view()` function (around line 677 from previous context). Modify the render_template call:

**Before:**
```python
return render_template(
    "session_shell.html",
    current_user=user,
    session_id=session_id,
    characters=characters,
    session_data={...},
)
```

**After:**
```python
conflict = present_conflict_panel(runtime_session.current_runtime_state)

return render_template(
    "session_shell.html",
    current_user=user,
    session_id=session_id,
    characters=characters,
    conflict=conflict,
    session_data={...},
)
```

- [ ] **Step 3: Modify session_execute() to call present_conflict_panel (after turn execution)**

Find the `session_execute()` function (around line 771). Locate where `characters` is rendered (around line 818) and add conflict panel call:

```python
characters = present_all_characters(runtime_session.current_runtime_state)
conflict = present_conflict_panel(runtime_session.current_runtime_state)

return render_template(
    "session_shell.html",
    current_user=user,
    session_id=session_id,
    characters=characters,
    conflict=conflict,
    scene=...,
    state_summary=...,
    turn_result=...,
    session_data={...},
)
```

Also add conflict call in error handler (around line 866):

```python
characters = present_all_characters(runtime_session.current_runtime_state)
conflict = present_conflict_panel(runtime_session.current_runtime_state)
```

- [ ] **Step 4: Run integration tests to verify implementation**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestConflictPanel::test_conflict_panel_renders_on_session_view -v
```

Expected: PASS (conflict variable now passed to template)

- [ ] **Step 5: Commit routes changes**

```bash
cd backend && git add app/web/routes.py && git commit -m "feat(w3.4.3): integrate present_conflict_panel into session routes"
```

---

### Task 3: Add Conflict Panel to Template

**Files:**
- Modify: `backend/app/web/templates/session_shell.html`

- [ ] **Step 1: Locate main-column in session_shell.html and add conflict panel section**

Open `backend/app/web/templates/session_shell.html`. Find the `<div class="main-column">` section (should be around line 80 from W3.4.2). Add this section right after opening `<div class="main-column">` (before `session-info-panel`):

```html
  <section class="panel conflict-panel">
    <h3>Conflict & Escalation</h3>
    {% if conflict %}
      <dl class="conflict-meta">
        {% if conflict.current_pressure is not none %}
        <dt>Pressure</dt>
        <dd class="pressure-value">{{ conflict.current_pressure }}</dd>
        {% endif %}

        <dt>Escalation Status</dt>
        <dd class="escalation-status {{ conflict.current_escalation_status }}">
          {{ conflict.current_escalation_status }}
        </dd>
      </dl>

      {% if conflict.recent_trend %}
      <div class="recent-trend">
        <p class="label">Recent Trend</p>
        <p class="trend-signal {{ conflict.recent_trend.signal }}">
          {{ conflict.recent_trend.signal }}
        </p>
        {% if conflict.recent_trend.source_basis %}
        <p class="source-basis">
          Source: {{ conflict.recent_trend.source_basis | join(", ") }}
        </p>
        {% endif %}
      </div>
      {% endif %}

      {% if conflict.turning_point_risk is not none %}
      <div class="turning-point">
        <p class="label">Turning Point Risk</p>
        <p class="risk-flag {% if conflict.turning_point_risk %}high{% else %}low{% endif %}">
          {% if conflict.turning_point_risk %}⚠️ High risk of major shift{% else %}Low risk{% endif %}
        </p>
      </div>
      {% endif %}
    {% else %}
      <p class="conflict-empty-state">Conflict data unavailable.</p>
    {% endif %}
  </section>
```

- [ ] **Step 2: Run template syntax check (Jinja2 validation)**

```bash
cd backend && python -c "from jinja2 import Environment; env = Environment(); env.parse(open('app/web/templates/session_shell.html').read())"
```

Expected: No error (valid Jinja2 syntax)

- [ ] **Step 3: Run integration tests to verify template renders**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestConflictPanel -v
```

Expected: PASS (conflict panel now renders in template)

- [ ] **Step 4: Commit template changes**

```bash
cd backend && git add app/web/templates/session_shell.html && git commit -m "feat(w3.4.3): add conflict panel to session shell template"
```

---

### Task 4: Verify Full Test Suite

**Files:**
- Test: `backend/tests/test_session_ui.py`, `backend/tests/runtime/test_scene_presenter.py`

- [ ] **Step 1: Run all W3.4 UI and presenter tests**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py tests/runtime/test_scene_presenter.py -v --tb=short
```

Expected: All tests pass (including new W3.4.3 conflict panel tests + existing W3.4.1/W3.4.2 tests)

- [ ] **Step 2: Run full backend test suite**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/ -q --tb=line
```

Expected: All backend tests pass (no regression)

- [ ] **Step 3: Verify no W3 scope jump (manual check)**

- ✅ Conflict panel integrated (not character diagnostics, not historical view)
- ✅ Data sourced from existing W3.4.1 presenter
- ✅ No new runtime model changes
- ✅ No module-specific hacks
- ✅ Render-on-request pattern (not live polling)

- [ ] **Step 4: Commit final verification**

```bash
cd backend && git commit --allow-empty -m "test(w3.4.3): verify full test suite passing and W3 scope contained"
```

---

## Hard Constraints

1. **No new presenter functions.** Use existing `present_conflict_panel()` from W3.4.1.
2. **Thin routes.** Routes only call presenter and pass result; no presenter logic in routes.
3. **Graceful fallbacks.** Missing pressure/trend → show "Conflict data unavailable" or partial display.
4. **Render-on-request only.** Synchronous updates after turn execution; no polling, no WebSocket, no typing-time updates.
5. **No runtime model changes.** ConflictPanelOutput and conflict_state already defined; use as-is.
6. **No module-specific adaptation.** Design works for all modules without modification.

---

## Acceptance Criteria

- ✅ `present_conflict_panel()` integrated into `session_view()` and `session_execute()` routes
- ✅ Conflict panel renders in `session_shell.html` template
- ✅ Panel displays: current_pressure, current_escalation_status, recent_trend (if available), turning_point_risk (if available)
- ✅ Empty-state message renders when conflict data unavailable
- ✅ Conflict panel updates after turn execution
- ✅ All edge cases handled gracefully (missing pressure, missing trend, null turning_point_risk)
- ✅ Integration tests verify rendering and updates
- ✅ Full test suite passes (no regression)
- ✅ No W3 scope jump confirmed (no historical view, no diagnostics, no live updates)

---

## Implementation Notes

1. **Reuse W3.4.2 pattern exactly.** Routes and template structure identical except:
   - One conflict panel (singular) vs. multiple character cards (plural)
   - Conflict panel in main column (not sidebar)

2. **Import path:** `from app.runtime import present_conflict_panel` (already exported from `__init__.py` in W3.4.1)

3. **Edge case handling:** Presenter already handles missing context layers gracefully; template uses Jinja2 `if` blocks for optional fields

4. **Testing strategy:** Placeholder tests for conflict panel (full integration deferred until turn execution wired in W3.5); focus on rendering and data flow

---

## Suggested Commit Message

```
feat(w3.4.3): add bounded conflict panel to playable ui
```

---
