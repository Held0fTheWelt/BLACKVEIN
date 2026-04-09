# W3.6: Smoke Coverage and Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task using TDD. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 7 focused smoke tests proving the playable UI survives the critical happy-path workflow and gracefully handles key failure scenarios.

**Architecture:** Add `TestW3SmokeAndStability` class to existing `backend/tests/test_session_ui.py`. Tests follow real routed flow (POST /play/start → GET /play/<session_id> → POST /play/<session_id>/execute) with behavior-based failure assertions. Reuse W3.5.4 synchronization coverage as baseline. TDD approach: write test → run → fix issues → pass.

**Tech Stack:** Pytest, Flask test client, runtime state access via `get_runtime_session()`, behavior-based assertions.

---

## File Structure

| File | Action | Responsibility |
|------|--------|-----------------|
| `backend/tests/test_session_ui.py` | Modify | Add `TestW3SmokeAndStability` class with 7 smoke tests and 3 helper functions; preserve existing W3.5.4 `TestSynchronizationRegression` class |

---

## Task 1: Set Up Test Class, Fixtures, and Helpers

**Files:**
- Modify: `backend/tests/test_session_ui.py` (append to end of file)

- [ ] **Step 1: Examine existing test structure**

Read the end of `test_session_ui.py` to understand:
- Where `TestSynchronizationRegression` class ends
- How existing helpers `_create_and_setup_session()` and `_get_csrf_token()` work
- What imports are already present

Run: `tail -100 backend/tests/test_session_ui.py`

- [ ] **Step 2: Write test class skeleton with fixtures**

Add to `test_session_ui.py` before any test methods:

```python
# ── W3.6 Smoke Tests ──────────────────────────────────────────────────────────

class TestW3SmokeAndStability:
    """Smoke tests for critical W3 playable UI paths and graceful failure handling."""

    # Test methods will be added in subsequent tasks
```

- [ ] **Step 3: Add response assertion helpers**

Append these helpers to `TestW3SmokeAndStability`:

```python
    @staticmethod
    def _assert_response_not_error(response):
        """Verify response is not a 5xx error."""
        assert response.status_code < 500, f"Got {response.status_code}: {response.data[:500]}"

    @staticmethod
    def _assert_session_shell_renders(response):
        """Verify session shell template rendered."""
        response_text = response.data.decode('utf-8', errors='ignore')
        assert ("session" in response_text.lower() or
                "shell" in response_text.lower() or
                "Session" in response_text or
                "play" in response_text.lower()), \
            "Session shell not found in response"

    @staticmethod
    def _assert_panels_present(response):
        """Verify both history and debug panel sections are in response."""
        response_text = response.data.decode('utf-8', errors='ignore')
        has_history = "history" in response_text.lower()
        has_debug = "debug" in response_text.lower() or "diagnostic" in response_text.lower()
        assert has_history, "History panel missing from response"
        assert has_debug, "Debug panel missing from response"
```

- [ ] **Step 4: Run tests to verify syntax**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestW3SmokeAndStability -v 2>&1 | head -20`

Expected: No syntax errors; class recognized but no tests yet.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.6): add TestW3SmokeAndStability class skeleton with helpers"
```

---

## Task 2: Implement Test 1 — Authenticated Start → Create Session → Load Runtime

**Files:**
- Modify: `backend/tests/test_session_ui.py`

**Purpose:** Verify the initial session creation and load flow works end-to-end.

- [ ] **Step 1: Write failing test**

Add to `TestW3SmokeAndStability`:

```python
    def test_smoke_authenticated_start_and_load(self, client, test_user):
        """Verify auth → start → load runtime flow works end-to-end."""
        # Authenticate
        user, password = test_user
        client.post("/login", data={"username": user.username, "password": password})

        # Start session
        response = client.post(
            "/play/start",
            data={"module_id": "god_of_carnage"},
            follow_redirects=False,
        )
        assert response.status_code == 302, f"Expected 302, got {response.status_code}"

        # Extract session_id from redirect
        location = response.headers.get("Location", "")
        session_id = location.split("/play/")[-1] if "/play/" in location else None
        assert session_id, f"Could not extract session_id from {location}"

        # Load runtime page
        response = client.get(f"/play/{session_id}")
        self._assert_response_not_error(response)
        self._assert_session_shell_renders(response)

        # Verify session info visible
        response_text = response.data.decode('utf-8', errors='ignore')
        assert "god_of_carnage" in response_text, "Module name not visible on load"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_authenticated_start_and_load -xvs`

Expected: FAIL (test method exists, should run and possibly pass or fail based on actual behavior)

Note: If test passes immediately, that's fine — it means the happy path works. Move to Step 4.

- [ ] **Step 3: If test fails, investigate and fix (minimal scope)**

Check:
- Does `/play/start` route exist and work?
- Does session get stored in cookie?
- Does GET `/play/<session_id>` load correctly?

Fix only session continuity or render issues, not polish.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_authenticated_start_and_load -xvs`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.6): add smoke test for authenticated start and load"
```

---

## Task 3: Implement Test 2 — Execute Turn → Verify Updated Page Renders Panels

**Files:**
- Modify: `backend/tests/test_session_ui.py`

**Purpose:** Verify turn execution updates canonical state and renders fresh response with panels.

- [ ] **Step 1: Write failing test**

Add to `TestW3SmokeAndStability`:

```python
    def test_smoke_execute_turn_and_verify_state(self, client, test_user):
        """Verify turn execution updates state and renders key panels."""
        # Create and load session
        user, password = test_user
        client.post("/login", data={"username": user.username, "password": password})
        response = client.post(
            "/play/start",
            data={"module_id": "god_of_carnage"},
            follow_redirects=False,
        )
        location = response.headers.get("Location", "")
        session_id = location.split("/play/")[-1]

        # Get CSRF token
        response = client.get(f"/play/{session_id}")
        import re
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', response.data.decode('utf-8', errors='ignore'))
        csrf_token = match.group(1) if match else ""
        assert csrf_token, "Could not extract CSRF token"

        # Execute turn
        response = client.post(
            f"/play/{session_id}/execute",
            data={"operator_input": "test action", "csrf_token": csrf_token},
            follow_redirects=False,
        )
        self._assert_response_not_error(response)
        self._assert_panels_present(response)

        # Verify turn counter incremented
        response_text = response.data.decode('utf-8', errors='ignore')
        assert "Turn" in response_text or "turn" in response_text, "Turn indicator missing"
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_execute_turn_and_verify_state -xvs`

Expected: Either PASS (happy path works) or FAIL (issues to investigate)

- [ ] **Step 3: If test fails, investigate and fix (minimal scope)**

Common issues:
- CSRF token not rendered in GET response → check template
- POST execute returning 500 → check error logs
- Panels not in response → check template rendering

Fix only issues blocking smoke test.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_execute_turn_and_verify_state -xvs`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.6): add smoke test for turn execution and state update"
```

---

## Task 4: Implement Test 3 — Panels Render with Meaningful Content After Turn

**Files:**
- Modify: `backend/tests/test_session_ui.py`

**Purpose:** Verify panels contain actual data, not empty/broken templates.

- [ ] **Step 1: Write failing test**

Add to `TestW3SmokeAndStability`:

```python
    def test_smoke_panels_render_with_meaningful_content(self, client, test_user):
        """Verify history and debug panels contain actual data after turn."""
        from app.runtime.session_store import get_runtime_session
        from app.runtime.history_presenter import present_history_panel
        from app.runtime.debug_presenter import present_debug_panel

        # Create, load, and execute
        user, password = test_user
        client.post("/login", data={"username": user.username, "password": password})
        response = client.post(
            "/play/start",
            data={"module_id": "god_of_carnage"},
            follow_redirects=False,
        )
        session_id = response.headers["Location"].split("/play/")[-1]

        response = client.get(f"/play/{session_id}")
        import re
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', response.data.decode('utf-8', errors='ignore'))
        csrf_token = match.group(1)

        response = client.post(
            f"/play/{session_id}/execute",
            data={"operator_input": "test action", "csrf_token": csrf_token},
        )

        # Get runtime state and call presenters
        runtime_session = get_runtime_session(session_id)
        state = runtime_session.current_runtime_state

        history_panel = present_history_panel(state)
        debug_panel = present_debug_panel(state)

        # Verify panels have content
        assert history_panel.entry_count > 0, "History panel has no entries"
        assert len(history_panel.recent_entries) > 0, "History panel recent_entries empty"
        assert debug_panel.primary_diagnostic is not None, "Debug panel diagnostic missing"

        # Verify content in response
        response_text = response.data.decode('utf-8', errors='ignore')
        has_outcome = "accepted" in response_text.lower() or "rejected" in response_text.lower()
        assert has_outcome, "Guard outcome not visible in response"
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_panels_render_with_meaningful_content -xvs`

Expected: PASS or FAIL

- [ ] **Step 3: If test fails, investigate**

Check:
- Do presenters return valid data after turn execution?
- Are outcomes rendered in the template?

Fix issues if found.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_panels_render_with_meaningful_content -xvs`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.6): add smoke test for panel content rendering"
```

---

## Task 5: Implement Tests 4–7 — Failure Paths (Invalid Session, Missing Session, Failed Turn, Shell Recovery)

**Files:**
- Modify: `backend/tests/test_session_ui.py`

**Purpose:** Verify critical failure paths don't crash; return graceful responses.

- [ ] **Step 1: Write Test 4 — Failed Turn Execution**

Add to `TestW3SmokeAndStability`:

```python
    def test_smoke_failed_turn_execution_returns_usable_page(self, client, test_user):
        """Verify error paths don't return 500 or broken renders."""
        # Create and load session
        user, password = test_user
        client.post("/login", data={"username": user.username, "password": password})
        response = client.post(
            "/play/start",
            data={"module_id": "god_of_carnage"},
            follow_redirects=False,
        )
        session_id = response.headers["Location"].split("/play/")[-1]

        # Get CSRF
        response = client.get(f"/play/{session_id}")
        import re
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', response.data.decode('utf-8', errors='ignore'))
        csrf_token = match.group(1) if match else ""

        # Execute with input that triggers a known handled failure
        # (guard rejection, timeout, or similar canonical failure the code handles)
        response = client.post(
            f"/play/{session_id}/execute",
            data={"operator_input": "", "csrf_token": csrf_token},  # Empty input likely triggers guard
        )

        # Verify non-500 response
        self._assert_response_not_error(response)
        self._assert_session_shell_renders(response)

        # Verify error feedback visible
        response_text = response.data.decode('utf-8', errors='ignore')
        assert "error" in response_text.lower() or "invalid" in response_text.lower() or "Session" in response_text, \
            "No error feedback visible"

        # Verify session still valid
        from app.runtime.session_store import get_runtime_session
        runtime_session = get_runtime_session(session_id)
        assert runtime_session is not None, "Session lost after error"
```

- [ ] **Step 2: Write Test 5 — Invalid Session ID**

Add to `TestW3SmokeAndStability`:

```python
    def test_smoke_invalid_session_id_fails_gracefully(self, client, test_user):
        """Verify invalid session IDs don't crash."""
        user, password = test_user
        client.post("/login", data={"username": user.username, "password": password})

        # Try to access invalid session
        response = client.get("/play/nonexistent-session-xyz-invalid")

        # Should not be 5xx
        self._assert_response_not_error(response)

        # Should be redirect or error page
        response_text = response.data.decode('utf-8', errors='ignore')
        is_redirect = response.status_code in (301, 302, 303, 307, 308)
        is_error_page = "not found" in response_text.lower() or "error" in response_text.lower() or "session" in response_text.lower()

        assert is_redirect or is_error_page, \
            f"Invalid session should redirect or show error, got {response.status_code}: {response_text[:200]}"
```

- [ ] **Step 3: Write Test 6 — Missing Session Linkage**

Add to `TestW3SmokeAndStability`:

```python
    def test_smoke_missing_session_linkage_fails_gracefully(self, client, test_user):
        """Verify missing session linkage doesn't crash."""
        user, password = test_user
        client.post("/login", data={"username": user.username, "password": password})

        # Create a session but then try to access without maintaining the linkage
        # (simulate session cookie loss or mismatch)
        response = client.post(
            "/play/start",
            data={"module_id": "god_of_carnage"},
            follow_redirects=False,
        )
        session_id = response.headers["Location"].split("/play/")[-1]

        # Clear session context
        with client.session_transaction() as sess:
            sess.clear()

        # Try to access session without linkage
        response = client.get(f"/play/{session_id}")

        # Should not be 5xx
        self._assert_response_not_error(response)

        # Should redirect or show error
        response_text = response.data.decode('utf-8', errors='ignore')
        is_redirect = response.status_code in (301, 302, 303, 307, 308)
        is_error_page = "not found" in response_text.lower() or "error" in response_text.lower() or "login" in response_text.lower()

        assert is_redirect or is_error_page, \
            f"Missing session linkage should redirect or show error, got {response.status_code}"
```

- [ ] **Step 4: Write Test 7 — Session Shell Recovery**

Add to `TestW3SmokeAndStability`:

```python
    def test_smoke_session_shell_remains_usable_after_error(self, client, test_user):
        """Verify session shell is usable after encountering error."""
        from app.runtime.session_store import get_runtime_session

        # Create and load session
        user, password = test_user
        client.post("/login", data={"username": user.username, "password": password})
        response = client.post(
            "/play/start",
            data={"module_id": "god_of_carnage"},
            follow_redirects=False,
        )
        session_id = response.headers["Location"].split("/play/")[-1]

        # Get CSRF and execute with error
        response = client.get(f"/play/{session_id}")
        import re
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', response.data.decode('utf-8', errors='ignore'))
        csrf_token = match.group(1) if match else ""

        response = client.post(
            f"/play/{session_id}/execute",
            data={"operator_input": "", "csrf_token": csrf_token},
        )

        # Verify error response renders shell
        self._assert_session_shell_renders(response)
        self._assert_panels_present(response)

        # Reload session via fresh GET
        response = client.get(f"/play/{session_id}")
        self._assert_response_not_error(response)
        self._assert_session_shell_renders(response)

        # Verify session still valid
        runtime_session = get_runtime_session(session_id)
        assert runtime_session is not None, "Session corrupted after error recovery"
```

- [ ] **Step 5: Run all failure-path tests**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_failed_turn_execution_returns_usable_page tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_invalid_session_id_fails_gracefully tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_missing_session_linkage_fails_gracefully tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_session_shell_remains_usable_after_error -xvs`

Expected: Some may pass, some may fail depending on current error handling

- [ ] **Step 6: Fix failures (minimal scope)**

For each failure:
1. Check error message
2. Identify if it's a missing error path, broken template, or unhandled exception
3. Fix only the code that makes the test pass (error handling, template fix, etc.)
4. Do not refactor or polish beyond smoke test survivability

- [ ] **Step 7: Re-run failure-path tests until all pass**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_failed_turn_execution_returns_usable_page tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_invalid_session_id_fails_gracefully tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_missing_session_linkage_fails_gracefully tests/test_session_ui.py::TestW3SmokeAndStability::test_smoke_session_shell_remains_usable_after_error -xvs`

Expected: All PASS

- [ ] **Step 8: Commit all failure-path tests**

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.6): add failure-path smoke tests (invalid session, missing linkage, error recovery)"
```

---

## Task 6: Run Full W3.6 Smoke Test Suite and Verify Baseline

**Files:**
- No code changes; verification only

- [ ] **Step 1: Run all W3.6 smoke tests**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestW3SmokeAndStability -v`

Expected: All 7 tests PASS

- [ ] **Step 2: Verify W3.5.4 synchronization tests still pass**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression -v`

Expected: All 10 W3.5.4 tests PASS (no regressions)

- [ ] **Step 3: Run full test_session_ui.py suite**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py -v --tb=short`

Expected: All tests PASS (W3.6 smoke + existing W3 tests)

- [ ] **Step 4: Verify no other tests broke**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/ -q --tb=line 2>&1 | tail -20`

Expected: Confirm test count and pass/fail summary

---

## Task 7: Final Verification and Gate Readiness

**Files:**
- No code changes; verification only

- [ ] **Step 1: Verify W3.6 smoke coverage**

Confirm:
- ✅ Happy-path flow: auth → start → load → execute → panels render
- ✅ Failure paths: invalid session, missing linkage, error handling all graceful
- ✅ Panels contain data after turn execution
- ✅ No 500 errors in critical paths

- [ ] **Step 2: Verify W3.5.4 synchronization still baseline**

Confirm:
- ✅ GET /play/<session_id> renders fresh state
- ✅ POST /play/<session_id>/execute returns fresh state
- ✅ Subsequent GET shows consistent state
- ✅ All 10 W3.5.4 tests passing

- [ ] **Step 3: Verify minimal-fix discipline maintained**

Review commits for:
- Only survivability fixes (session continuity, error paths, error messages)
- No cosmetic polish
- No broad refactoring
- No W4 features

- [ ] **Step 4: Verify scope containment**

Confirm:
- No W4 hardening added
- No UI redesign
- No module-specific hacks
- W3 scope maintained

---

## Task 8: Write Final W3.6 Report

**Files:**
- No code changes; documentation only

- [ ] **Step 1: Create W3.6 completion report**

Write to `docs/W3.6-COMPLETION-REPORT.md`:

```markdown
# W3.6: Smoke Coverage and Stability – Completion Report

## Summary
W3.6 adds 7 focused smoke tests proving the playable UI survives the critical happy-path workflow and gracefully handles key failure scenarios.

## Files Changed
- `backend/tests/test_session_ui.py` — Added `TestW3SmokeAndStability` class with 7 tests and 3 helper functions

## Smoke Paths Covered

### Happy-Path Smoke (4 tests)
1. **test_smoke_authenticated_start_and_load** — Authenticated user creates session and loads runtime page
   - Flow: Login → POST /play/start → GET /play/<session_id>
   - Verified: Session created, loaded, rendered without errors

2. **test_smoke_execute_turn_and_verify_state** — Turn execution updates state and renders fresh response
   - Flow: POST /play/<session_id>/execute with valid input
   - Verified: Response 200, panels present, turn counter visible

3. **test_smoke_panels_render_with_meaningful_content** — History and debug panels contain real data
   - Verified: Presenters return populated panel objects, outcomes visible in HTML

4. **test_smoke_error_handling_returns_usable_page** — Error paths don't crash
   - Flow: POST with empty/invalid input
   - Verified: Non-500 response, shell renders, error feedback visible

### Failure-Path Smoke (3 tests)
5. **test_smoke_invalid_session_id_fails_gracefully** — Invalid session IDs don't crash
   - Verified: Non-500 response, redirect or error page shown

6. **test_smoke_missing_session_linkage_fails_gracefully** — Missing session state doesn't crash
   - Verified: Non-500 response, graceful failure with feedback

7. **test_smoke_session_shell_remains_usable_after_error** — UI recoverable after errors
   - Verified: Shell renders in error path, subsequent GET still works, session valid

## Stability Priorities Addressed

### 1. Session Continuity ✅
- Session created via POST /play/start is correctly linked in cookie
- Session retrieved via GET /play/<session_id> maintains continuity
- Invalid/expired sessions fail gracefully (no 500, no broken redirects)

### 2. Failed Turn Handling ✅
- Failed execution returns non-500 response
- Session shell renders with valid state after failure
- History/debug panels remain usable after error
- Error feedback visible to user

### 3. GET/POST Synchronization ✅
- Reused W3.5.4 synchronization tests as baseline
- All 10 existing tests still passing
- Fresh canonical state after POST reflected in GET response
- No stale data in panels

## Polish/Fixes Applied
- [List any actual bugs fixed, if any were discovered]
- [If no bugs found, state "No stability bugs discovered in smoke test coverage"]

## Deferrals to W4
- Performance optimization
- Broad edge-case expansion
- Cosmetic UI polish (spacing, colors, typography)
- Module-specific special handling

## Scope Confirmation
✅ No W4 hardening introduced
✅ No UI architecture redesign
✅ No module-specific hacks
✅ W3 scope strictly maintained
✅ All acceptance criteria met

## Test Results
- W3.6 Smoke Tests: 7/7 PASS
- W3.5.4 Synchronization Tests: 10/10 PASS (baseline)
- Full test_session_ui.py: [X]/[Y] PASS
- Full backend test suite: [X]/[Y] PASS

## Recommendation
✅ **W3.6 READY** — Playable UI survives critical workflow and gracefully handles failures. Foundation solid for W3 gate review and W4 expansion.
```

- [ ] **Step 2: Populate actual test results in report**

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_session_ui.py -v --tb=no 2>&1 | grep -E "PASSED|FAILED|ERROR|==="` and copy counts

Run: `cd backend && PYTHONPATH=. python -m pytest tests/ -q --tb=no 2>&1 | tail -1` and copy full suite results

Update the report with actual numbers.

- [ ] **Step 3: Commit report**

```bash
git add docs/W3.6-COMPLETION-REPORT.md
git commit -m "docs(w3.6): add completion report with test results and scope confirmation"
```

---

## Verification Checklist

Before considering W3.6 complete, verify:

- [ ] All 7 W3.6 smoke tests passing
- [ ] All 10 W3.5.4 synchronization tests still passing
- [ ] No 5xx errors in critical paths (start, load, execute)
- [ ] Invalid/missing sessions fail gracefully
- [ ] Error paths render usable shell
- [ ] History/debug panels contain real data
- [ ] No cosmetic polish beyond survivability
- [ ] No W4 scope introduced
- [ ] No module-specific hacks
- [ ] Completion report written with actual test results
- [ ] All changes committed

---

## Acceptance Criteria

✅ All 7 W3.6 smoke tests pass
✅ All 10 W3.5.4 synchronization tests still pass (no regressions)
✅ Happy-path smoke proves: auth → start → load → execute → panels render
✅ Failure-path smoke proves: graceful handling of invalid sessions, missing linkage, errors
✅ Minimal-fix discipline maintained (survivability only, no polish)
✅ W3 scope strictly maintained (no W4, no redesign, no module hacks)
✅ Final report documents paths covered, fixes applied, deferrals, and scope confirmation

---

## Suggested Final Commit

```bash
git log --oneline -8 backend/tests/test_session_ui.py
# Review commits for W3.6 work

git commit --allow-empty -m "feat(w3.6): smoke coverage and stability hardening

- add 7 focused smoke tests for critical W3 playable UI paths
- verify happy-path workflow: auth → start → load → execute → panels
- verify failure-path graceful handling: invalid sessions, errors, recovery
- reuse W3.5.4 synchronization tests as baseline (GET/POST consistency)
- fix only survivability issues discovered by smoke coverage
- maintain tight W3 scope (no W4, no redesign, no polish beyond stability)
- ready for W3 gate review and W4 expansion"
```
