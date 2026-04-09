# A1 Refocus: Natural Input Dominance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `player_input` the canonical form field name in the frontend play shell, eliminating the `operator_input` naming that implies command-first UX.

**Architecture:** The frontend `session_shell.html` still uses `operator_input` as the HTML form field name, and `frontend/app/routes.py` reads it by that name. Despite the template note saying "Natural language is the primary input path", the field name contradicts that. The fix is a name-only refactor: rename the form field and its reader to `player_input`, matching the API payload field already sent downstream.

**Tech Stack:** Flask (frontend), Jinja2 templates, pytest

---

### Task 1: Fix form field naming in template and route

**Files:**
- Modify: `frontend/templates/session_shell.html` (line 28)
- Modify: `frontend/app/routes.py` (line ~343)
- Test: `frontend/tests/test_routes_extended.py`

- [ ] **Step 1: Write failing test for player_input form field**

```python
def test_play_shell_form_uses_player_input_field(client, logged_in_session):
    """The play shell form must use player_input, not operator_input."""
    response = client.get("/play/test-run-id", ...)
    assert b'name="player_input"' in response.data
    assert b'name="operator_input"' not in response.data
```

- [ ] **Step 2: Run test to verify it fails**

```
cd frontend && python -m pytest tests/test_routes_extended.py::test_play_shell_form_uses_player_input_field -v
```
Expected: FAIL (form still has `operator_input`)

- [ ] **Step 3: Rename form field in session_shell.html**

Change `name="operator_input"` → `name="player_input"`

- [ ] **Step 4: Update routes.py to read player_input**

Change `request.form.get("operator_input")` → `request.form.get("player_input")`

- [ ] **Step 5: Run tests to verify pass**

```
cd frontend && python -m pytest tests/test_routes_extended.py -v
```

- [ ] **Step 6: Write A1_REFOCUS_GATE_REPORT.md**

Create `docs/reports/ai_stack_gates/A1_REFOCUS_GATE_REPORT.md`

- [ ] **Step 7: Commit**

```
git add frontend/templates/session_shell.html frontend/app/routes.py frontend/tests/test_routes_extended.py docs/reports/ai_stack_gates/A1_REFOCUS_GATE_REPORT.md
git commit -m "repair(a1): make natural input the dominant story play path"
```
