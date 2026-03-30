# W3.6: UI Smoke Coverage and Stability Polish

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this spec task-by-task using TDD. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the playable UI survives the critical happy-path workflow and gracefully handles key failure scenarios, with minimal fixes to core survivability issues.

**Architecture:** Add 7 focused smoke tests covering the real routed playable flow (POST /play/start → GET /play/<session_id> → POST /play/<session_id>/execute), with behavior-based failure assertions for graceful degradation. Reuse existing W3.5.4 synchronization coverage as baseline proof of GET/POST state consistency.

**Tech Stack:** Pytest, Flask test client, direct runtime state access via `get_runtime_session()`, behavior-based assertions (non-500, usable response, error feedback visible).

---

## Context

W3.1–W3.5 built the playable Jinja/web UI with session management, history/debug panels, and synchronization verification. W3.6 hardens the UI survivability by proving the core workflow (start → load → execute) is stable and that critical failure paths (invalid session, failed execution) don't break the experience.

**Not in scope:** Performance optimization, broad edge-case expansion, cosmetic polish, module-specific hacks.

**Canonical rule:** W3.6 tests the real routed playable flow and fixes only issues that break survivability, not UX mechanics.

---

## Test Coverage: 7 Focused Smoke Tests

Add new test class `TestW3SmokeAndStability` to `backend/tests/test_session_ui.py`.

### Happy-Path Smoke (4 tests)

#### Test 1: Authenticated Start → Create Session → Load Runtime

**Purpose:** Verify the initial session creation and load flow works end-to-end.

**Steps:**
1. Authenticate as test user
2. POST `/play/start` with `module_id="god_of_carnage"` and CSRF token
3. Extract session_id from redirect response
4. GET `/play/<session_id>` with authenticated context
5. Assert response status == 200
6. Assert response contains session info block (module_id, scene_id visible)
7. Assert both history_panel and debug_panel sections render (no render errors)

**Evidence of success:** Session created, loaded, and rendered without errors.

---

#### Test 2: Execute Turn → Verify Updated Page Renders Key Panels

**Purpose:** Verify turn execution updates canonical state and renders fresh response.

**Steps:**
1. Create and load session (reuse helper from Test 1)
2. Extract CSRF token from GET response
3. POST `/play/<session_id>/execute` with valid `operator_input` and CSRF token
4. Assert response status == 200 (not 5xx)
5. Assert response HTML contains turn-related content (e.g., "Turn 1" or turn counter > 0)
6. Assert history_panel section present in response
7. Assert debug_panel section present in response

**Evidence of success:** Turn executes, page renders with both panels visible.

---

#### Test 3: Panels Render with Meaningful Content After Turn

**Purpose:** Verify panels contain actual data, not empty/broken templates.

**Steps:**
1. Execute turn (from Test 2)
2. Get runtime state via `get_runtime_session(session_id)`
3. Call `present_history_panel(runtime_state)` and `present_debug_panel(runtime_state)`
4. Assert `history_panel.entry_count > 0` (entries exist)
5. Assert `debug_panel.primary_diagnostic.summary` is populated (guard_outcome, triggers, etc.)
6. Assert response HTML contains outcome text (e.g., "accepted", "rejected") from debug panel
7. Assert response HTML contains history summary (turn count, scene info)

**Evidence of success:** Panels contain real data, not degraded/empty state.

---

#### Test 4: Failed Turn Execution Returns Usable Page

**Purpose:** Verify error paths don't return 500 or broken renders.

**Steps:**
1. Create and load session
2. Use input/fixture setup that drives turn flow into a known, handled failure path (e.g., operator_input that triggers a guard rejection, guard timeout, or other canonical failure the code is designed to handle)
3. POST `/play/<session_id>/execute` with this input
4. Assert response status in (200, 400, 422) — not 5xx
5. Assert response contains session shell HTML (not raw error traceback)
6. Assert response contains error message or feedback visible to user
7. Get runtime state via `get_runtime_session(session_id)`
8. Assert session state is still valid (turn_counter, history unchanged or incremented correctly)
9. Verify history_panel and debug_panel still render in error response

**Evidence of success:** Error doesn't break UI; user sees feedback and can continue.

---

### Critical Failure-Path Smoke (3 tests)

#### Test 5: Invalid Session ID → Graceful Failure

**Purpose:** Verify invalid session IDs don't crash, return non-500 response.

**Steps:**
1. Authenticate as test user
2. GET `/play/nonexistent-session-id-xyz`
3. Assert response status in (302, 400, 404) — not 5xx
4. Assert response either:
   - Redirects to `/play` (start page) with redirect status
   - Renders error page with clear message ("Session not found", "Please start a new session")
5. Assert no raw error traceback in response

**Evidence of success:** Invalid session fails gracefully, user is redirected or shown error.

---

#### Test 6: Missing or Mismatched Session Linkage → Graceful Failure

**Purpose:** Verify session cookies or Flask session state mismatches don't crash.

**Steps:**
1. Create session via POST `/play/start` and extract session_id
2. Clear Flask session context (simulate missing `active_session` cookie)
3. GET `/play/<session_id>` without session linkage
4. Assert response status in (302, 400, 401) — not 5xx
5. Assert response either:
   - Redirects to `/play` with status 302
   - Renders login page or session-expired page
6. Assert error message visible if page rendered (not silent redirect)

**Evidence of success:** Missing session state fails gracefully with feedback.

---

#### Test 7: Session Shell Remains Renderable After Error Path

**Purpose:** Verify session shell doesn't break and is still usable after encountering an error.

**Steps:**
1. Create and load session
2. Execute turn with invalid input (triggers error, from Test 4)
3. Verify error response renders shell (step 8 from Test 4 confirms this)
4. Verify error state doesn't prevent subsequent actions
5. GET `/play/<session_id>` again to reload (simulating user refresh)
6. Assert fresh GET still renders valid session shell with current state
7. Verify history_panel and debug_panel are still usable

**Evidence of success:** Error doesn't corrupt session; UI remains usable after recovery.

---

## Coverage Reuse: W3.5.4 Synchronization Tests

The existing `TestSynchronizationRegression` (10 tests in test_session_ui.py) covers:
- Single and multiple turn accumulation
- Outcome tracking and propagation
- Bounded output consistency
- GET-after-POST synchronization persistence
- Degradation marker synchronization

**Reuse pattern:**
- Do NOT duplicate these tests in W3.6
- If all 7 W3.6 smoke tests pass AND W3.5.4 tests still pass, stability area #3 (GET/POST state consistency) is proven
- W3.6 assumes W3.5.4 coverage is baseline evidence

---

## Minimal Fixes Discipline

When smoke tests fail, fix **only:**
- Session continuity bugs (session not stored, session not retrieved, wrong session linked)
- Error path render failures (500s, unhandled exceptions, render errors in error path)
- Missing error messages in response (user feedback in error paths)

**Do NOT fix:**
- Cosmetic UI issues (spacing, colors, typography)
- Performance optimizations (unless blocking smoke test timeout)
- Module-specific behavior or hacks
- Broad edge-case expansion beyond critical paths

---

## Implementation Setup

### Test Isolation Fixture

All tests must use:

```python
@pytest.fixture(autouse=True)
def clear_runtime_sessions(app):
    """Clear runtime session store before each test to prevent state leakage."""
    from app.runtime.session_store import clear_registry
    with app.app_context():
        clear_registry()
    yield
    clear_registry()
```

### Helpers (Reuse from W3.5.4)

```python
def _create_and_setup_session(client, test_user):
    """Create session and return session_id."""
    user, password = test_user
    client.post("/login", data={"username": user.username, "password": password})
    response = client.post(
        "/play/start",
        data={"module_id": "god_of_carnage"},
        follow_redirects=False,
    )
    return response.headers["Location"].split("/play/")[-1]

def _get_csrf_token(client, session_id):
    """Extract CSRF token from GET /play/{session_id}."""
    response = client.get(f"/play/{session_id}")
    import re
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', response.data.decode())
    return match.group(1) if match else ""
```

### Response Assertion Helpers

```python
def _assert_response_not_error(response):
    """Verify response is not a 5xx error."""
    assert response.status_code < 500, f"Got {response.status_code}: {response.data[:500]}"

def _assert_session_shell_renders(response):
    """Verify session shell template rendered (contains key sections)."""
    assert b"session-info-panel" in response.data or b"Session" in response.data
    assert b"history" in response.data.lower() or b"debug" in response.data.lower()

def _assert_panels_present(response):
    """Verify both history and debug panel sections are in response."""
    assert b"history" in response.data.lower(), "History panel missing"
    assert b"debug" in response.data.lower() or b"diagnostic" in response.data.lower(), "Debug panel missing"
```

---

## Files to Modify

| File | Action | Scope |
|------|--------|-------|
| `backend/tests/test_session_ui.py` | Add `TestW3SmokeAndStability` class with 7 tests and helpers | New test class only; no changes to existing W3.5.4 tests |

---

## Acceptance Criteria

✅ All 7 W3.6 smoke tests pass
✅ All 10 W3.5.4 synchronization tests still pass (no regressions)
✅ Happy-path smoke proves: auth → start → load → execute → panels render
✅ Failure-path smoke proves: invalid/missing sessions and errors don't crash
✅ Any bugs discovered are fixed with minimal scope (survivability only, no polish)
✅ No W3 scope jump occurred (no W4 hardening, no module-specific hacks, no redesign)
✅ Final report covers: files changed, smoke paths covered, fixes applied, deferrals, scope confirmation

---

## Out of Scope (W3.6 does not include)

- Performance benchmarking or optimization
- Broad edge-case expansion (only critical failure paths)
- Cosmetic UI polish (only fixes required for smoke stability)
- Module-specific behavior or special handling
- Expansion into W4 hardening
- UI architecture redesign
- New features or functionality beyond smoke coverage

---

## Suggested Commit Message

```
test(w3.6): add smoke coverage for critical playable UI paths

- verify authenticated start → load → execute flow works end-to-end
- verify panels render with meaningful content after turn execution
- verify failed turn execution returns usable page, not 500
- verify invalid/missing sessions fail gracefully with error feedback
- verify session shell remains usable after error recovery
- reuse W3.5.4 synchronization tests as baseline proof of GET/POST consistency
- 7 focused smoke tests proving core workflow survivability
```

---

## Next Step

Write the implementation plan using superpowers:writing-plans, then execute with superpowers:executing-plans or superpowers:subagent-driven-development.
