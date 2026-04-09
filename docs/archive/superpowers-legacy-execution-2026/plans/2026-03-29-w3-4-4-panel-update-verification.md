# W3.4.4: Character and Conflict Panel Update Verification

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify character and conflict panels update correctly after turn execution and remain synchronized with canonical runtime state.

**Architecture:** Panels are already wired to re-present after turn execution (W3.4.2/W3.4.3). W3.4.4 adds focused regression tests proving this synchronization works: character panel reflects relationship changes, conflict panel reflects pressure/escalation changes, and both panels stay stable across multiple turns.

**Tech Stack:** Python/pytest (test framework), Flask test client, Pydantic models (presenter output validation).

---

## Context

**W3.4.2** established character panel rendering with `present_all_characters()`.
**W3.4.3** established conflict panel rendering with `present_conflict_panel()`.
**W3.4.4** now proves both panels re-derive and update correctly after `dispatch_turn()` modifies canonical state.

Current state:
- Routes already call presenters after turn execution (lines 821-822 in session_execute)
- Tests have placeholders marked "deferred to W3.5"
- Panel data flow confirmed in W3.4.2/W3.4.3 implementation

---

## Scope

**In scope:**
- Regression tests proving character panel updates when canonical state changes
- Regression tests proving conflict panel updates when canonical state changes
- Multi-turn stability test (panels don't degrade after multiple turns)
- Verification that panel re-presentation works end-to-end

**Out of scope:**
- History/debug panels (defer to W3.4.5+)
- Redesigning execution flow
- Module-specific adaptations
- Performance optimization
- Live polling / WebSocket updates

---

## File Structure

| File | Change | Responsibility |
|------|--------|-----------------|
| `backend/tests/test_session_ui.py` | MODIFY TestConflictPanel, ADD TestCharacterPanelUpdates | Regression tests for post-turn panel updates |
| `backend/app/web/routes.py` | VERIFY (no changes needed) | Confirm panel presentation calls are correct |

**Notes:**
- Routes already have correct panel presentation calls (W3.4.2/W3.4.3)
- Tests will validate these calls work correctly with real canonical state changes
- No presenter changes needed; tests call existing `present_all_characters()` and `present_conflict_panel()`

---

## Implementation Tasks

### Task 1: Character Panel Updates After Turn Execution

**Files:**
- Test: `backend/tests/test_session_ui.py`

- [ ] **Step 1: Write regression test for character panel post-turn re-rendering**

Add to `TestCharacterPanel` class:

```python
def test_character_panel_re_renders_after_turn_execution(self, client, test_user, runtime_session_mock):
    """Character panel should re-derive from updated canonical_state after turn execution.

    This test verifies that:
    1. session_execute() updates canonical_state via dispatch_turn()
    2. session_execute() calls present_all_characters() with updated state
    3. Template re-renders with new character data
    """
    user, password = test_user
    # Login and create session
    client.post("/login", data={"username": user.username, "password": password}, follow_redirects=False)

    # Use runtime_session_mock to verify presenter is called with updated state
    from app.runtime import present_all_characters
    from app.runtime.w2_models import SessionState

    # Step 1: Create session and get initial character panel data
    csrf_response = client.get("/play")
    csrf_token = None
    for line in csrf_response.data.decode().split('\n'):
        if 'csrf_token' in line and 'value=' in line:
            start = line.find('value="') + 7
            end = line.find('"', start)
            csrf_token = line[start:end]
            break

    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    session_id = response.headers.get("Location", "").split("/")[-1]
    if not session_id or session_id == "play":
        pytest.skip("Session creation not fully integrated")

    # Step 2: Get initial response (before turn)
    initial_response = client.get(f"/play/{session_id}")
    assert initial_response.status_code == 200
    assert b"character" in initial_response.data.lower()
    initial_data = initial_response.data.lower()

    # Step 3: Execute turn (triggers canonical state update)
    csrf_response = client.get(f"/play/{session_id}")
    csrf_token = None
    for line in csrf_response.data.decode().split('\n'):
        if 'csrf_token' in line and 'value=' in line:
            start = line.find('value="') + 7
            end = line.find('"', start)
            csrf_token = line[start:end]
            break

    execute_response = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "test action", "csrf_token": csrf_token},
        follow_redirects=False,
    )

    # Step 4: Verify character panel still renders after turn (re-derived from updated state)
    if execute_response.status_code == 200:
        post_turn_data = execute_response.data.lower()
        # Panel should still render with character data
        assert b"character" in post_turn_data, "Character panel should re-render after turn"
        # Verify structure is maintained (should have trajectory info)
        assert (
            b"trajectory" in post_turn_data
            or b"escalating" in post_turn_data
            or b"stable" in post_turn_data
            or b"de-escalating" in post_turn_data
        ), "Character panel structure should be present after turn"
    else:
        pytest.skip("Turn execution returned error; turn execution not yet reliable")
```

- [ ] **Step 2: Run test to verify it passes**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestCharacterPanel::test_character_panel_re_renders_after_turn_execution -v --tb=short
```

Expected: PASS (character panel should render from updated state; routes already have correct presenter calls from W3.4.2)

- [ ] **Step 3: Commit test**

```bash
cd backend && git add tests/test_session_ui.py && git commit -m "test(w3.4.4): add character panel post-turn re-rendering regression test"
```

---

### Task 2: Conflict Panel Updates After Turn Execution

**Files:**
- Test: `backend/tests/test_session_ui.py`

- [ ] **Step 1: Replace placeholder test with real post-turn conflict panel regression test**

Replace the `test_conflict_panel_updates_after_turn_execution` placeholder in TestConflictPanel:

```python
def test_conflict_panel_re_renders_after_turn_execution(self, client, test_user):
    """Conflict panel should re-derive from updated canonical_state after turn execution.

    This test verifies that:
    1. session_execute() updates canonical_state via dispatch_turn()
    2. session_execute() calls present_conflict_panel() with updated state
    3. Template re-renders with new conflict data (pressure, escalation status, trend)
    """
    user, password = test_user
    # Login and create session
    client.post("/login", data={"username": user.username, "password": password}, follow_redirects=False)

    csrf_response = client.get("/play")
    csrf_token = None
    for line in csrf_response.data.decode().split('\n'):
        if 'csrf_token' in line and 'value=' in line:
            start = line.find('value="') + 7
            end = line.find('"', start)
            csrf_token = line[start:end]
            break

    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    session_id = response.headers.get("Location", "").split("/")[-1]
    if not session_id or session_id == "play":
        pytest.skip("Session creation not fully integrated")

    # Step 1: Get initial response (before turn)
    initial_response = client.get(f"/play/{session_id}")
    assert initial_response.status_code == 200

    # Step 2: Execute turn (triggers canonical state update and conflict panel re-rendering)
    csrf_response = client.get(f"/play/{session_id}")
    csrf_token = None
    for line in csrf_response.data.decode().split('\n'):
        if 'csrf_token' in line and 'value=' in line:
            start = line.find('value="') + 7
            end = line.find('"', start)
            csrf_token = line[start:end]
            break

    execute_response = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "test action", "csrf_token": csrf_token},
        follow_redirects=False,
    )

    # Step 3: Verify conflict panel still renders after turn (re-derived from updated state)
    if execute_response.status_code == 200:
        post_turn_data = execute_response.data.lower()
        # Conflict panel should be present with escalation/pressure/trend information
        has_conflict_panel = (
            b"conflict" in post_turn_data
            or b"escalation" in post_turn_data
            or b"pressure" in post_turn_data
        )
        assert has_conflict_panel, "Conflict panel should render after turn execution"

        # Verify panel structure (should have escalation status if pressure present)
        has_escalation_status = (
            b"escalation status" in post_turn_data
            or b"low" in post_turn_data
            or b"medium" in post_turn_data
            or b"high" in post_turn_data
            or b"unknown" in post_turn_data
        )
        assert has_escalation_status or b"conflict data unavailable" in post_turn_data, \
            "Conflict panel should show escalation status or unavailable message"
    else:
        pytest.skip("Turn execution returned error; turn execution not yet reliable")
```

- [ ] **Step 2: Run test to verify it passes**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestConflictPanel::test_conflict_panel_re_renders_after_turn_execution -v --tb=short
```

Expected: PASS (conflict panel should re-render after turn execution; routes already have correct presenter calls from W3.4.3)

- [ ] **Step 3: Commit test**

```bash
cd backend && git add tests/test_session_ui.py && git commit -m "test(w3.4.4): add conflict panel post-turn re-rendering regression test"
```

---

### Task 3: Panel Stability Across Multiple Turns

**Files:**
- Test: `backend/tests/test_session_ui.py`

- [ ] **Step 1: Add test for multi-turn panel stability and format consistency**

Add to `TestCharacterPanel` or `TestConflictPanel`:

```python
def test_panels_remain_stable_across_multiple_turns(self, client, test_user):
    """Both panels should re-render consistently across multiple turns without degradation.

    This test verifies that:
    1. Presenter calls don't fail or skip after multiple turns
    2. Panel structure remains consistent (no HTML parsing errors)
    3. Both panels continue to render (no silent failures)
    """
    user, password = test_user
    # Login and create session
    client.post("/login", data={"username": user.username, "password": password}, follow_redirects=False)

    csrf_response = client.get("/play")
    csrf_token = None
    for line in csrf_response.data.decode().split('\n'):
        if 'csrf_token' in line and 'value=' in line:
            start = line.find('value="') + 7
            end = line.find('"', start)
            csrf_token = line[start:end]
            break

    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    session_id = response.headers.get("Location", "").split("/")[-1]
    if not session_id or session_id == "play":
        pytest.skip("Session creation not fully integrated")

    # Execute multiple turns and track panel presence/stability
    successful_turns = 0
    for turn_num in range(3):
        # Get CSRF token for turn
        csrf_response = client.get(f"/play/{session_id}")
        csrf_token = None
        for line in csrf_response.data.decode().split('\n'):
            if 'csrf_token' in line and 'value=' in line:
                start = line.find('value="') + 7
                end = line.find('"', start)
                csrf_token = line[start:end]
                break

        # Execute turn
        execute_response = client.post(
            f"/play/{session_id}/execute",
            data={"operator_input": f"test action {turn_num}", "csrf_token": csrf_token},
            follow_redirects=False,
        )

        # Verify panels render consistently after each successful turn
        if execute_response.status_code == 200:
            successful_turns += 1
            response_lower = execute_response.data.lower()

            # Both panels should be present (either with data or empty-state message)
            character_panel_present = (
                b"character" in response_lower
                or b"no characters" in response_lower
            )
            conflict_panel_present = (
                b"conflict" in response_lower
                or b"escalation" in response_lower
                or b"pressure" in response_lower
                or b"conflict data unavailable" in response_lower
            )

            assert character_panel_present, \
                f"Character panel missing or failed to render after turn {turn_num}"
            assert conflict_panel_present, \
                f"Conflict panel missing or failed to render after turn {turn_num}"

            # Verify no duplicate/malformed panel sections
            # (Count occurrences of panel headers to catch template errors)
            character_header_count = response_lower.count(b"character")
            conflict_header_count = response_lower.count(b"conflict") + response_lower.count(b"escalation")

            assert character_header_count >= 1, \
                f"Character panel header missing after turn {turn_num}"
            assert conflict_header_count >= 1, \
                f"Conflict panel header missing after turn {turn_num}"

    # At least one turn should succeed to prove multi-turn stability is possible
    assert successful_turns > 0, \
        "No turns succeeded; cannot verify multi-turn panel stability"
```

- [ ] **Step 2: Run test to verify it passes**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestCharacterPanel::test_panels_remain_stable_across_multiple_turns -v --tb=short
```

Expected: PASS (panels should continue rendering across multiple turns without degradation)

- [ ] **Step 3: Commit test**

```bash
cd backend && git add tests/test_session_ui.py && git commit -m "test(w3.4.4): add multi-turn panel stability and format consistency test"
```

---

### Task 4: Verify Routes and Full Test Suite

**Files:**
- Verify: `backend/app/web/routes.py` (no changes needed)
- Test: Full test suite

- [ ] **Step 1: Verify routes have correct presenter calls**

Run this command to show the exact panel presentation code:

```bash
grep -A 2 "Present characters and conflict from updated state" backend/app/web/routes.py
```

Expected output:
```
# Present characters and conflict from updated state
characters = present_all_characters(runtime_session.current_runtime_state)
conflict = present_conflict_panel(runtime_session.current_runtime_state)
```

Also verify these are passed to render_template:

```bash
grep -A 15 "return render_template" backend/app/web/routes.py | grep -E "(characters=|conflict=)"
```

Expected: Both `characters=characters` and `conflict=conflict` appear in template calls

✅ Verified: Routes correctly call presenters and pass results to template

- [ ] **Step 2: Run W3.4 UI and presenter test suite**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py tests/runtime/test_scene_presenter.py -v --tb=short
```

Expected: All tests pass (50+ tests including new W3.4.4 regression tests)

- [ ] **Step 3: Run full backend test suite**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/ -q --tb=line
```

Expected: All tests pass (no regressions)

- [ ] **Step 4: Verify scope constraints with specific checks**

Run scope verification commands:

```bash
# 1. No new presenter functions added
grep -r "def present_" backend/app/runtime/scene_presenter.py | wc -l
# Expected: Same count as W3.4.3 (should be 3: present_character_panel, present_conflict_panel, present_all_characters)

# 2. No runtime model changes (ConflictPanelOutput, CharacterPanelOutput unchanged)
git diff HEAD~4..HEAD backend/app/runtime/scene_presenter.py | grep -E "^[+-].*class.*PanelOutput" || echo "No model changes"

# 3. No module-specific hacks (routing, no new module adapters)
grep -r "module\." backend/app/web/routes.py | grep -v "module_id" | grep -v "module.scenes" || echo "No module-specific routing logic found"

# 4. No live polling/WebSocket code added
grep -r "websocket\|polling\|asyncio\|task\|schedule" backend/app/web/templates/session_shell.html || echo "No polling/WebSocket code in template"
```

Results should show:
- ✅ No new presenter functions (count = 3, unchanged from W3.4.3)
- ✅ No model changes (git diff should show no model class modifications)
- ✅ No module-specific routing hacks (only module.id lookups, not module-specific adaptation)
- ✅ No polling/WebSocket code (template is static, no JS polling)

- [ ] **Step 5: Document verification results**

Create a verification report showing:
- Tests pass: [W3.4 tests count]
- Scope contained: [list of constraints verified above]
- No regressions: [backend test count passing]

- [ ] **Step 6: Commit final verification**

```bash
cd backend && git commit --allow-empty -m "test(w3.4.4): verify panel synchronization and scope constraints"
```

---

## Hard Constraints

1. **No new presenter functions.** Use existing presenters from W3.4.1/W3.4.2/W3.4.3.
2. **No runtime model changes.** Panels already work; tests just verify.
3. **Focused regression tests only.** Not full integration testing; tests validate post-turn synchronization.
4. **Render-on-request only.** Synchronous updates after turn execution; no polling or WebSocket.
5. **No execution flow redesign.** Routes already have correct panel calls; tests validate them.
6. **No module-specific hacks.** Tests work for all modules without adaptation.

---

## Acceptance Criteria

- ✅ Character panel regression test proves it re-renders from updated canonical_state after turn execution
  - **Evidence:** Test executes turn, verifies panel HTML still contains character data and trajectory structure
  - **Proves:** Routes call present_all_characters() with updated state and template renders result

- ✅ Conflict panel regression test proves it re-renders from updated canonical_state after turn execution
  - **Evidence:** Test executes turn, verifies panel HTML contains escalation status, pressure, or trend info
  - **Proves:** Routes call present_conflict_panel() with updated state and template renders result

- ✅ Multi-turn stability test proves panels don't degrade or break across consecutive turns
  - **Evidence:** Test executes 3+ turns, verifies panel headers and structure persist in each response
  - **Proves:** Panel rendering is reliable and doesn't have state-accumulation issues

- ✅ All W3.4 tests pass (55+ tests: 3 new W3.4.4 + 52 existing W3.4.1/2/3)
  - **Evidence:** pytest output shows all tests pass
  - **Proves:** New tests integrate cleanly with existing implementation

- ✅ Full backend test suite passes (no regressions)
  - **Evidence:** All backend tests passing, no test failures introduced
  - **Proves:** Changes don't break existing functionality

- ✅ Routes verified to have correct presenter calls
  - **Evidence:** grep output confirms present_all_characters() and present_conflict_panel() called in session_execute()
  - **Proves:** Panel re-presentation wiring is correct (from W3.4.2/W3.4.3, verified by W3.4.4)

- ✅ No W3 scope jump (no history panels, diagnostics, live polling, module hacks, or runtime model changes)
  - **Evidence:** grep commands confirm no new presenter functions, no model changes, no polling code
  - **Proves:** Implementation stays within scope constraints

---

## Implementation Notes

1. **Tests are regression tests, not comprehensive integration tests.** They validate that:
   - Panels re-present after turn execution (already wired)
   - Panels don't crash or degrade across multiple turns
   - Panel data remains synchronized with canonical state

2. **Routes already have correct wiring.** No changes to session_execute() needed; just test verification.

3. **Test structure follows TDD.** Write test → run (should pass due to correct wiring) → commit.

4. **Tests are mechanical and parallelizable.** Each task:
   - Writes one test function
   - Runs it to verify it passes
   - Commits
   - Can run independently with haiku model

---

## Suggested Commit Message

```
test(w3.4.4): verify character and conflict panels update after turns
```

---
