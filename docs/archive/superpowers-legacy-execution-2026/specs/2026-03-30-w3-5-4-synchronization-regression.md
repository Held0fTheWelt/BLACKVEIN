# W3.5.4: History & Debug Panel Synchronization Regression

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task using TDD (test-driven development). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove that history and debug panels remain synchronized with canonical runtime/logging data after real turn execution through comprehensive regression tests.

**Canonical Rule:** W3.5.4 must prove synchronization across canonical state update → presenter re-derivation → rendered UI output on **both** immediate post-turn render and subsequent session render.

**Architecture:** Three test layers (synchronization verification → presenter consumption → HTTP response rendering) covering single/multiple turns, outcome tracking, bounded output consistency, degraded state markers, and GET-after-POST persistence.

**Tech Stack:** Pytest, Flask test client, direct runtime state access via `get_runtime_session()`, presenter calls, HTML response parsing.

---

## Context

W3.5.2 and W3.5.3 added history and debug panel UI. W3.5.4 verifies these panels stay synchronized with canonical data **after real turn execution** and are covered by focused regression tests.

The wiring is already in place (routes call presenters after turn execution), but W3.5.4 proves the **data flow works correctly** through three verification layers:

1. **Layer 1: Synchronization Verification** — Canonical state updated correctly after turn
2. **Layer 2: Presenter Consumption** — Presenters read fresh (not cached) state
3. **Layer 3: HTTP Response Rendering** — Presenter output appears in HTML response

---

## Test Suite: `TestSynchronizationRegression`

Add new test class to `backend/tests/test_session_ui.py` with 10 focused tests covering:

### Test 1: Single Turn Synchronization (Layer 1+2+3)

**Purpose:** Verify one turn updates canonical state, presenter reads it, and response renders it.

**Steps:**
1. Create session via `_create_and_setup_session(client, test_user)` → get `session_id`
2. Execute one turn via POST `/play/{session_id}/execute` with valid `operator_input` and CSRF token
3. Layer 1 - Get updated runtime state:
   ```python
   runtime_session = get_runtime_session(session_id)
   state = runtime_session.current_runtime_state
   assert state.turn_counter == 1
   assert len(state.session_history.entries) >= 1
   ```
4. Layer 2 - Call presenter on fresh state:
   ```python
   debug_panel = present_debug_panel(state)
   assert debug_panel.primary_diagnostic.summary.turn_number == 1
   ```
5. Layer 3 - Assert response HTML contains turn/outcome:
   ```python
   assert b"Turn 1" in response.data or _extract_turn_number_from_html(response.data) == 1
   ```

**Failure signature:** Layer 1 (state not updated) or Layer 2 (presenter reads old state) or Layer 3 (HTML doesn't render it)

---

### Test 2: Multiple Turn Accumulation (Layer 1+2+3)

**Purpose:** Verify panels accumulate correctly across 5 turns.

**Steps:**
1. Create session
2. Loop 5 times:
   - Execute turn via POST
   - Get runtime state
   - Assert `turn_counter == i+1`
   - Assert `session_history.entries` has `i+1` entries
   - Call presenter
   - Assert `entry_count` in output equals `i+1`
3. Assert final response shows all 5 turns in history (or last N if bounded)

**Failure signature:** State doesn't accumulate, presenter doesn't see accumulation, or template doesn't show accumulation

---

### Test 3: Outcome Tracking — Guard Outcome Propagation (Layer 1+2+3)

**Purpose:** Verify guard outcomes (accepted/rejected/etc.) sync through all layers.

**Steps:**
1. Create session, execute turn
2. Get canonical state
3. Read `short_term_context.summary.guard_outcome`
4. Call presenter on state
5. Assert `debug_panel.primary_diagnostic.summary.guard_outcome` matches canonical
6. Assert response contains outcome name (e.g., `b"accepted"`) and outcome CSS class (e.g., `b"outcome-accepted"`)

**Failure signature:** Outcome differs between canonical, presenter, or HTML rendering

---

### Test 4: Outcome Changes Across Turns (Layer 1+2+3)

**Purpose:** Verify different turns can have different outcomes and both are tracked.

**Steps:**
1. Execute turn 1, capture outcome
2. Execute turn 2, capture (possibly different) outcome
3. Get runtime state
4. Call presenter
5. Assert `recent_entries` in history_panel shows both turns with their respective outcomes
6. Assert response renders both outcomes correctly (may be collapsed for older turns)

**Failure signature:** Outcomes overwrite each other or presenter loses prior turn outcomes

---

### Test 5: Bounded Output Consistency (Layer 2+3)

**Purpose:** Verify bounded windows stay bounded when history exceeds limit.

**Steps:**
1. Execute 25 turns (exceeds typical bounded window)
2. Get runtime state
3. Call `present_history_panel(runtime_state)`
4. Assert `len(recent_entries) <= 20` (or configured bounded size)
5. Call `present_debug_panel(runtime_state)`
6. Assert `len(recent_pattern_context) <= 5` (or configured size)
7. Assert total `entry_count` is 25 but output is still bounded
8. Assert response renders cleanly without breaking layout

**Failure signature:** Bounded window overflows, output becomes huge, or template breaks

---

### Test 6: Stale State Detection (Layer 1+2)

**Purpose:** Catch any stale state or caching bugs in immediate POST response.

**Steps:**
1. Execute turn 1
2. Get response HTML
3. Extract turn_number from response (via regex or HTML parsing)
4. Assert extracted turn_number == 1 (not 0)
5. Execute turn 2
6. Get response HTML
7. Assert extracted turn_number == 2 (not 1)

**Failure signature:** Response shows old turn number (stale state in route or presenter)

---

### Test 7: Degraded/Recovery Synchronization (Layer 1+2+3)

**Purpose:** Verify degradation markers sync through all three layers.

**Steps:**
1. Create session, execute turn that triggers degraded state (if available via fixture or mock)
   - Alternative: manually set degraded state on runtime_session.current_runtime_state if needed for testing
2. Get canonical state via `get_runtime_session(session_id)`
3. Assert `degraded_session_state` or `degradation_markers` present in state
4. Call `present_debug_panel(runtime_state)`
5. Assert `degradation_markers` in output matches canonical markers
6. Get response HTML
7. Assert degradation markers render in response (e.g., marker text or recovery status visible)

**Failure signature:** Degradation markers not tracked, presenter ignores them, or HTML doesn't show them

---

### Test 8: GET-After-POST Synchronization (Layer 1+2+3)

**Purpose:** Verify synchronization persists across requests, not just in immediate POST response.

**Steps:**
1. Create session via POST /play/start
2. Execute turn via POST /play/{session_id}/execute
   - Capture updated turn_counter from response
3. Load session again via GET /play/{session_id}
   - **Do not use the POST response; fetch fresh**
4. Get runtime state via `get_runtime_session(session_id)`
5. Assert `turn_counter` still reflects the executed turn
6. Assert response HTML shows same turn_number
7. Call presenters on freshly-loaded state
8. Assert history_panel and debug_panel both show the executed turn

**Failure signature:** Session reverts to prior state on GET, presenter reads stale history, or GET response shows old turn

**Critical:** This test proves synchronization is not just correct in the immediate POST context but also in the full session lifecycle.

---

### Test 9: Multiple Turns with GET Reloads (Layer 1+2+3)

**Purpose:** Verify synchronization is durable across multiple execute→get cycles.

**Steps:**
1. Create session
2. Execute turn 1, assert response shows turn 1
3. GET session, assert response still shows turn 1
4. Execute turn 2, assert response shows turn 2
5. GET session, assert response still shows turn 2
6. Get runtime state directly
7. Assert canonical state has both turns
8. Call presenters
9. Assert both turns appear in presenter output

**Failure signature:** State corrupts on GET, turns are lost, or presenter misses accumulated turns

---

### Test 10: Outcome Tracking with GET-After-POST (Layer 1+2+3)

**Purpose:** Verify outcomes persist correctly across execute→get cycles.

**Steps:**
1. Create session
2. Execute turn with outcome O1, capture from response
3. GET session, assert outcome O1 still visible
4. Execute turn with outcome O2, capture from response
5. GET session, assert both O1 and O2 visible (or latest visible if bounded)
6. Get runtime state
7. Call presenters
8. Assert both outcomes in presenter output

**Failure signature:** Outcomes are lost on GET, only latest visible, or presenter misses prior outcomes

---

## Implementation Setup (Critical for Test Isolation)

### Test Isolation & Fixtures

**All tests must use these fixtures to ensure isolation:**

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

**Session creation helper (reuse from TestCharacterPanel if available):**

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

### Presenter Interface (Critical Clarification)

**All tests calling presenters must extract `current_runtime_state` from `RuntimeSession`:**

```python
from app.runtime.session_store import get_runtime_session
from app.runtime.history_presenter import present_history_panel
from app.runtime.debug_presenter import present_debug_panel

# CORRECT pattern:
runtime_session = get_runtime_session(session_id)
state = runtime_session.current_runtime_state  # Extract SessionState
history_panel = present_history_panel(state)  # Pass SessionState
debug_panel = present_debug_panel(state)      # Pass SessionState
```

### Bounded Window Constants

**Before implementation, verify these values in code:**
- `history_presenter.py`: max `recent_entries` (spec assumes 20, verify actual)
- `debug_presenter.py`: max `recent_pattern_context` (spec assumes 5, verify actual)

Reference in Test 5 assertions once verified.

### Degradation Marker Fixture (Test 7)

**If natural degradation trigger unavailable, use fixture:**

```python
@pytest.fixture
def degraded_runtime_session(app, test_user):
    """Create session with degradation marker for Test 7."""
    from app.runtime.w2_models import DegradedSessionState, DegradedMarker
    from app.runtime.session_store import update_runtime_session, get_runtime_session

    session_id = _create_and_setup_session(client, test_user)
    runtime_session = get_runtime_session(session_id)

    # Manually set degradation marker
    runtime_session.current_runtime_state.degraded_session_state = DegradedSessionState(
        markers=[DegradedMarker.FALLBACK_ACTIVE]
    )
    update_runtime_session(session_id, runtime_session.current_runtime_state)

    return session_id
```

### Helper Functions for HTML Parsing

**Add these helpers to test class:**

```python
def _extract_turn_number_from_html(html_content):
    """Extract turn number from response HTML."""
    import re
    match = re.search(r'Turn\s+(\d+)', html_content.decode())
    return int(match.group(1)) if match else None

def _extract_outcome_from_html(html_content):
    """Extract guard outcome from response HTML."""
    import re
    # Check for outcome class in response
    for outcome in ["accepted", "partially_accepted", "rejected", "structurally_invalid"]:
        if f'outcome-{outcome}'.encode() in html_content or outcome.encode() in html_content:
            return outcome
    return None

def _extract_entry_count_from_html(html_content):
    """Extract entry count from response HTML."""
    import re
    match = re.search(r'(\d+)\s+total entries', html_content.decode())
    return int(match.group(1)) if match else None
```

---

## Files to Modify

| File | Action | Scope |
|------|--------|-------|
| `backend/tests/test_session_ui.py` | Add `TestSynchronizationRegression` class with 10 tests, helper functions, and fixtures above | New test class, helpers, and fixtures only; no changes to existing tests or routes/templates |

---

## Acceptance Criteria

✅ All 10 tests pass
✅ Tests verify synchronization (Layer 1), presenter consumption (Layer 2), and rendering (Layer 3)
✅ No changes needed to routes/templates (wiring already correct)
✅ Regression coverage proves UI stays correct across:
  - Single and multiple turns
  - Different outcomes
  - Bounded output windows
  - Degraded/recovery state markers
  - Both immediate POST responses and subsequent GET loads
✅ Coverage includes edge cases: stale state detection, degradation markers, GET-after-POST persistence

---

## Out of Scope (W3.5.4 does not include)

- Route/template changes (wiring already correct from W3.5.2/W3.5.3)
- Redesign of execution or logging flow
- Module-specific hacks or behavior
- Expansion beyond W3.5 scope (no W3.6 or W4 work)

---

## Suggested Commit Message

```
test(w3.5.4): add synchronization regression tests for history and debug panels

- verify canonical state updates after turn execution
- verify presenters consume fresh (not cached) state
- verify UI renders updated presenter output correctly
- test single and multiple turn accumulation
- test outcome tracking and propagation
- test bounded output consistency
- test degradation markers synchronization
- test GET-after-POST synchronization persistence
- 10 focused tests covering all three verification layers
```

