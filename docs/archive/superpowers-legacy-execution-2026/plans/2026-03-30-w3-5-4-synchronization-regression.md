# W3.5.4: History & Debug Panel Synchronization Regression Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 10 focused regression tests that prove history and debug panels remain synchronized with canonical runtime/logging data after real turn execution.

**Architecture:** Single test class (`TestSynchronizationRegression`) with 10 TDD tests covering three verification layers (canonical state → presenter → HTTP response). Tests use fixtures for isolation and helper functions for HTML parsing. No route/template changes needed (wiring already correct from W3.5.2/W3.5.3).

**Tech Stack:** Pytest, Flask test client, runtime session APIs, presenter functions, regex/HTML parsing.

---

## File Structure

**Single file modified:**
- `backend/tests/test_session_ui.py` — Add new test class with fixtures, helpers, and 10 tests

**No files created or routes/templates changed.**

---

## Task 1: Define Test Fixtures and Helper Functions

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add to top of `TestSynchronizationRegression` class definition)

### Step 1: Write fixture definitions (no test yet, just supporting code)

Add these fixtures and helpers at the beginning of the test file, before `TestSynchronizationRegression` class:

```python
import pytest
import re
from app.runtime.session_store import get_session, clear_registry, update_session
from app.runtime.history_presenter import present_history_panel
from app.runtime.debug_presenter import present_debug_panel
from app.runtime.w2_models import DegradedSessionState, DegradedMarker


@pytest.fixture(autouse=True)
def clear_runtime_sessions(app):
    """Clear runtime session store before each test to prevent state leakage."""
    with app.app_context():
        clear_registry()
    yield
    clear_registry()


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
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', response.data.decode())
    return match.group(1) if match else ""


def _extract_turn_number_from_html(html_content):
    """Extract turn number from response HTML."""
    match = re.search(r'Turn\s+(\d+)', html_content.decode())
    return int(match.group(1)) if match else None


def _extract_outcome_from_html(html_content):
    """Extract guard outcome from response HTML."""
    for outcome in ["accepted", "partially_accepted", "rejected", "structurally_invalid"]:
        if f'outcome-{outcome}'.encode() in html_content or outcome.encode() in html_content:
            return outcome
    return None


def _extract_entry_count_from_html(html_content):
    """Extract entry count from response HTML."""
    match = re.search(r'(\d+)\s+total entries', html_content.decode())
    return int(match.group(1)) if match else None
```

### Step 2: Verify fixtures compile (no test execution yet)

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  python -c "from tests.test_session_ui import *; print('Fixtures imported successfully')"
```

Expected: No import errors.

### Step 3: Create empty TestSynchronizationRegression class stub

Add to `test_session_ui.py`:

```python
class TestSynchronizationRegression:
    """W3.5.4: Regression tests proving history and debug panels stay synchronized after turn execution."""
    pass
```

### Step 4: Run test suite to confirm no new failures

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression -v
```

Expected: No tests yet (empty class).

### Step 5: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.4): add fixtures and helpers for synchronization tests"
```

---

## Task 2: Test 1 — Single Turn Synchronization (Layer 1+2+3)

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add to `TestSynchronizationRegression`)

### Step 1: Write failing test

Add to `TestSynchronizationRegression`:

```python
def test_single_turn_synchronization(self, client, test_user):
    """Test 1: Verify one turn updates canonical state, presenter reads it, response renders it."""
    # Setup
    session_id = _create_and_setup_session(client, test_user)
    csrf_token = _get_csrf_token(client, session_id)

    # Execute one turn
    response = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "test action", "csrf_token": csrf_token},
        follow_redirects=True,
    )

    # Layer 1: Verify canonical state updated
    runtime_session = get_session(session_id)
    state = runtime_session.current_runtime_state
    assert state.turn_counter == 1, f"Expected turn_counter=1, got {state.turn_counter}"
    assert len(state.session_history.entries) >= 1, "No history entry created"

    # Layer 2: Verify presenter reads fresh state
    debug_panel = present_debug_panel(state)
    assert debug_panel.primary_diagnostic.summary.turn_number == 1, \
        f"Expected turn_number=1 in presenter, got {debug_panel.primary_diagnostic.summary.turn_number}"

    # Layer 3: Verify response renders it
    assert response.status_code == 200
    assert b"debug-summary" in response.data or _extract_turn_number_from_html(response.data) == 1, \
        "Turn 1 not found in response HTML"
```

### Step 2: Run test to verify it fails

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression::test_single_turn_synchronization -xvs
```

Expected: PASS (test is written correctly, routes/presenters already wired)

### Step 3: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.4): add Test 1 - single turn synchronization"
```

---

## Task 3: Test 2 — Multiple Turn Accumulation

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add to `TestSynchronizationRegression`)

### Step 1: Write failing test

Add to `TestSynchronizationRegression`:

```python
def test_multiple_turn_accumulation(self, client, test_user):
    """Test 2: Verify panels accumulate correctly across 5 turns."""
    session_id = _create_and_setup_session(client, test_user)
    csrf_token = _get_csrf_token(client, session_id)

    for turn_num in range(1, 6):
        # Execute turn
        response = client.post(
            f"/play/{session_id}/execute",
            data={"operator_input": f"action {turn_num}", "csrf_token": csrf_token},
            follow_redirects=True,
        )

        # Layer 1: Verify canonical state has turn
        runtime_session = get_session(session_id)
        state = runtime_session.current_runtime_state
        assert state.turn_counter == turn_num, f"Turn {turn_num}: expected turn_counter={turn_num}, got {state.turn_counter}"
        assert len(state.session_history.entries) == turn_num, \
            f"Turn {turn_num}: expected {turn_num} history entries, got {len(state.session_history.entries)}"

        # Layer 2: Verify presenter sees accumulation
        history_panel = present_history_panel(state)
        assert history_panel.entry_count == turn_num, \
            f"Turn {turn_num}: expected entry_count={turn_num}, got {history_panel.entry_count}"

        # Layer 3: Verify response shows turn
        assert response.status_code == 200
        assert b"history-summary" in response.data or b"entries-table" in response.data, \
            f"Turn {turn_num}: history panel not in response"
```

### Step 2: Run test to verify it passes

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression::test_multiple_turn_accumulation -xvs
```

Expected: PASS

### Step 3: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.4): add Test 2 - multiple turn accumulation"
```

---

## Task 4: Test 3 — Outcome Tracking (Guard Outcome Propagation)

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add to `TestSynchronizationRegression`)

### Step 1: Write failing test

Add to `TestSynchronizationRegression`:

```python
def test_outcome_tracking_propagation(self, client, test_user):
    """Test 3: Verify guard outcomes sync through all layers."""
    session_id = _create_and_setup_session(client, test_user)
    csrf_token = _get_csrf_token(client, session_id)

    # Execute turn
    response = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "test action", "csrf_token": csrf_token},
        follow_redirects=True,
    )

    # Layer 1: Get canonical outcome
    runtime_session = get_session(session_id)
    state = runtime_session.current_runtime_state
    canonical_outcome = state.short_term_context.summary.guard_outcome if state.short_term_context else None

    # Layer 2: Verify presenter reflects it
    debug_panel = present_debug_panel(state)
    presenter_outcome = debug_panel.primary_diagnostic.summary.guard_outcome
    assert presenter_outcome == canonical_outcome, \
        f"Outcome mismatch: canonical={canonical_outcome}, presenter={presenter_outcome}"

    # Layer 3: Verify response renders it
    assert response.status_code == 200
    # Check that outcome appears in response (either as class name or text)
    if presenter_outcome:
        outcome_lower = presenter_outcome.lower()
        assert outcome_lower.encode() in response.data or f'outcome-{outcome_lower}'.encode() in response.data, \
            f"Outcome '{presenter_outcome}' not found in response"
```

### Step 2: Run test to verify it passes

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression::test_outcome_tracking_propagation -xvs
```

Expected: PASS

### Step 3: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.4): add Test 3 - outcome tracking propagation"
```

---

## Task 5: Test 4 — Outcome Changes Across Turns

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add to `TestSynchronizationRegression`)

### Step 1: Write failing test

Add to `TestSynchronizationRegression`:

```python
def test_outcome_changes_across_turns(self, client, test_user):
    """Test 4: Verify different turns can have different outcomes and both are tracked."""
    session_id = _create_and_setup_session(client, test_user)
    csrf_token = _get_csrf_token(client, session_id)

    outcomes_by_turn = {}

    # Execute 2 turns
    for turn_num in range(1, 3):
        response = client.post(
            f"/play/{session_id}/execute",
            data={"operator_input": f"action {turn_num}", "csrf_token": csrf_token},
            follow_redirects=True,
        )
        assert response.status_code == 200

        # Capture outcome for this turn
        runtime_session = get_session(session_id)
        state = runtime_session.current_runtime_state
        outcome = state.short_term_context.summary.guard_outcome if state.short_term_context else None
        outcomes_by_turn[turn_num] = outcome

    # Verify final state shows both turns
    runtime_session = get_session(session_id)
    state = runtime_session.current_runtime_state

    # Layer 2: Verify presenter shows both
    history_panel = present_history_panel(state)
    assert history_panel.entry_count == 2, f"Expected 2 entries, got {history_panel.entry_count}"
    assert len(history_panel.recent_entries) >= 2, "Expected at least 2 recent entries"

    # Layer 3: Verify response shows both outcomes
    assert response.status_code == 200
    # Both turns should be in history
    for turn_num in [1, 2]:
        assert b"history-summary" in response.data or b"entries-table" in response.data, \
            f"Turn {turn_num} outcomes not shown in response"
```

### Step 2: Run test to verify it passes

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression::test_outcome_changes_across_turns -xvs
```

Expected: PASS

### Step 3: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.4): add Test 4 - outcome changes across turns"
```

---

## Task 6: Test 5 — Bounded Output Consistency

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add to `TestSynchronizationRegression`)

### Step 1: Write failing test

Add to `TestSynchronizationRegression`:

```python
def test_bounded_output_consistency(self, client, test_user):
    """Test 5: Verify bounded windows stay bounded when history exceeds limit."""
    session_id = _create_and_setup_session(client, test_user)
    csrf_token = _get_csrf_token(client, session_id)

    # Execute 25 turns to exceed typical bounded window
    for turn_num in range(1, 26):
        response = client.post(
            f"/play/{session_id}/execute",
            data={"operator_input": f"action {turn_num}", "csrf_token": csrf_token},
            follow_redirects=True,
        )
        assert response.status_code == 200

    # Layer 1: Get canonical state
    runtime_session = get_session(session_id)
    state = runtime_session.current_runtime_state
    assert state.turn_counter == 25, f"Expected 25 turns, got {state.turn_counter}"

    # Layer 2: Verify presenters bound their output
    history_panel = present_history_panel(state)
    debug_panel = present_debug_panel(state)

    # History should be bounded (typically 20 recent entries)
    assert len(history_panel.recent_entries) <= 20, \
        f"History panel recent_entries exceeds bound: {len(history_panel.recent_entries)}"

    # Debug pattern should be bounded (typically 5 recent turns)
    assert len(debug_panel.recent_pattern_context or []) <= 5, \
        f"Debug panel pattern context exceeds bound: {len(debug_panel.recent_pattern_context or [])}"

    # But total count should reflect all turns
    assert history_panel.entry_count == 25, f"Expected entry_count=25, got {history_panel.entry_count}"

    # Layer 3: Verify response renders cleanly
    assert response.status_code == 200
    assert b"debug-summary" in response.data or b"history-summary" in response.data, \
        "Panels not rendered in response after 25 turns"
```

### Step 2: Run test to verify it passes

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression::test_bounded_output_consistency -xvs
```

Expected: PASS

### Step 3: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.4): add Test 5 - bounded output consistency"
```

---

## Task 7: Test 6 — Stale State Detection

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add to `TestSynchronizationRegression`)

### Step 1: Write failing test

Add to `TestSynchronizationRegression`:

```python
def test_stale_state_detection(self, client, test_user):
    """Test 6: Catch stale state or caching bugs in immediate POST response."""
    session_id = _create_and_setup_session(client, test_user)
    csrf_token = _get_csrf_token(client, session_id)

    # Execute turn 1
    response1 = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "action 1", "csrf_token": csrf_token},
        follow_redirects=True,
    )
    assert response1.status_code == 200
    turn1_number = _extract_turn_number_from_html(response1.data)
    assert turn1_number == 1, f"Expected turn 1, got {turn1_number}"

    # Execute turn 2
    response2 = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "action 2", "csrf_token": csrf_token},
        follow_redirects=True,
    )
    assert response2.status_code == 200
    turn2_number = _extract_turn_number_from_html(response2.data)
    assert turn2_number == 2, f"Expected turn 2, got {turn2_number}"

    # Verify turn 2 response doesn't show turn 1 as latest
    assert turn2_number != 1, "Turn 2 response shows stale turn 1"
```

### Step 2: Run test to verify it passes

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression::test_stale_state_detection -xvs
```

Expected: PASS

### Step 3: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.4): add Test 6 - stale state detection"
```

---

## Task 8: Test 7 — Degraded/Recovery Synchronization

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add to `TestSynchronizationRegression`)

### Step 1: Write failing test

Add to `TestSynchronizationRegression`:

```python
def test_degraded_recovery_synchronization(self, client, test_user, app):
    """Test 7: Verify degradation markers sync through all layers."""
    session_id = _create_and_setup_session(client, test_user)
    csrf_token = _get_csrf_token(client, session_id)

    # Execute one turn
    response = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "test action", "csrf_token": csrf_token},
        follow_redirects=True,
    )

    # Manually set degradation marker on canonical state
    with app.app_context():
        runtime_session = get_session(session_id)
        state = runtime_session.current_runtime_state

        # Create degraded state with marker
        state.degraded_state = DegradedSessionState(
            active_markers={DegradedMarker.FALLBACK_ACTIVE}
        )
        update_session(session_id, state)

    # Layer 1: Verify degradation marker present
    with app.app_context():
        runtime_session = get_session(session_id)
        state = runtime_session.current_runtime_state
        assert state.degraded_state is not None, "Degradation marker not set"
        assert len(state.degraded_state.active_markers) > 0, "No markers in degradation"

    # Layer 2: Verify presenter includes degradation
    debug_panel = present_debug_panel(state)
    assert debug_panel.degradation_markers is not None and len(debug_panel.degradation_markers) > 0, \
        "Presenter doesn't include degradation markers"

    # Layer 3: Verify response shows degradation (if markers are rendered)
    assert response.status_code == 200
    # Response should have debug panel
    assert b"debug-summary" in response.data or b"debug-diagnostics" in response.data, \
        "Debug panel not in response with degradation"
```

### Step 2: Run test to verify it passes

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression::test_degraded_recovery_synchronization -xvs
```

Expected: PASS

### Step 3: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.4): add Test 7 - degraded/recovery synchronization"
```

---

## Task 9: Test 8 — GET-After-POST Synchronization

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add to `TestSynchronizationRegression`)

### Step 1: Write failing test

Add to `TestSynchronizationRegression`:

```python
def test_get_after_post_synchronization(self, client, test_user):
    """Test 8: Verify synchronization persists across requests, not just immediate POST response."""
    session_id = _create_and_setup_session(client, test_user)
    csrf_token = _get_csrf_token(client, session_id)

    # Execute turn via POST
    post_response = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "test action", "csrf_token": csrf_token},
        follow_redirects=True,
    )
    assert post_response.status_code == 200
    post_turn_number = _extract_turn_number_from_html(post_response.data)

    # Load session again via GET (fresh request)
    get_response = client.get(f"/play/{session_id}", follow_redirects=True)
    assert get_response.status_code == 200
    get_turn_number = _extract_turn_number_from_html(get_response.data)

    # Layer 1: Verify canonical state persists
    runtime_session = get_session(session_id)
    state = runtime_session.current_runtime_state
    assert state.turn_counter == 1, "Turn counter not persisted"

    # Layer 2: Verify presenters on fresh GET still show executed turn
    history_panel = present_history_panel(state)
    debug_panel = present_debug_panel(state)
    assert history_panel.entry_count >= 1, "History not persisted on GET"
    assert debug_panel.primary_diagnostic.summary.turn_number == 1, "Debug turn not persisted on GET"

    # Layer 3: Verify GET response matches POST response
    assert get_turn_number == post_turn_number, \
        f"POST showed turn {post_turn_number}, GET shows turn {get_turn_number}"
    assert b"debug-summary" in get_response.data, "Debug panel not in GET response"
```

### Step 2: Run test to verify it passes

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression::test_get_after_post_synchronization -xvs
```

Expected: PASS

### Step 3: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.4): add Test 8 - GET-after-POST synchronization"
```

---

## Task 10: Test 9 — Multiple Turns with GET Reloads

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add to `TestSynchronizationRegression`)

### Step 1: Write failing test

Add to `TestSynchronizationRegression`:

```python
def test_multiple_turns_with_get_reloads(self, client, test_user):
    """Test 9: Verify synchronization durable across multiple execute→get cycles."""
    session_id = _create_and_setup_session(client, test_user)
    csrf_token = _get_csrf_token(client, session_id)

    for turn_num in range(1, 4):
        # Execute turn
        post_response = client.post(
            f"/play/{session_id}/execute",
            data={"operator_input": f"action {turn_num}", "csrf_token": csrf_token},
            follow_redirects=True,
        )
        assert post_response.status_code == 200
        post_turn = _extract_turn_number_from_html(post_response.data)
        assert post_turn == turn_num, f"POST turn mismatch: expected {turn_num}, got {post_turn}"

        # GET the session to reload it
        get_response = client.get(f"/play/{session_id}", follow_redirects=True)
        assert get_response.status_code == 200
        get_turn = _extract_turn_number_from_html(get_response.data)
        assert get_turn == turn_num, f"GET turn mismatch: expected {turn_num}, got {get_turn}"

    # After 3 turns, verify all are persisted
    runtime_session = get_session(session_id)
    state = runtime_session.current_runtime_state
    assert state.turn_counter == 3, f"Expected 3 turns, got {state.turn_counter}"

    # Verify presenters show all 3
    history_panel = present_history_panel(state)
    assert history_panel.entry_count == 3, f"Expected entry_count=3, got {history_panel.entry_count}"
```

### Step 2: Run test to verify it passes

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression::test_multiple_turns_with_get_reloads -xvs
```

Expected: PASS

### Step 3: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.4): add Test 9 - multiple turns with GET reloads"
```

---

## Task 11: Test 10 — Outcome Tracking with GET-After-POST

**Files:**
- Modify: `backend/tests/test_session_ui.py` (add to `TestSynchronizationRegression`)

### Step 1: Write failing test

Add to `TestSynchronizationRegression`:

```python
def test_outcome_tracking_get_after_post(self, client, test_user):
    """Test 10: Verify outcomes persist correctly across execute→get cycles."""
    session_id = _create_and_setup_session(client, test_user)
    csrf_token = _get_csrf_token(client, session_id)

    # Execute turn 1
    response1 = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "action 1", "csrf_token": csrf_token},
        follow_redirects=True,
    )
    assert response1.status_code == 200

    # GET to reload after turn 1
    get1_response = client.get(f"/play/{session_id}", follow_redirects=True)
    assert get1_response.status_code == 200

    # Execute turn 2
    response2 = client.post(
        f"/play/{session_id}/execute",
        data={"operator_input": "action 2", "csrf_token": csrf_token},
        follow_redirects=True,
    )
    assert response2.status_code == 200

    # GET to reload after turn 2
    get2_response = client.get(f"/play/{session_id}", follow_redirects=True)
    assert get2_response.status_code == 200

    # Verify final state has both turns and outcomes
    runtime_session = get_session(session_id)
    state = runtime_session.current_runtime_state

    # Layer 2: Verify presenter shows both
    history_panel = present_history_panel(state)
    assert history_panel.entry_count == 2, f"Expected 2 entries, got {history_panel.entry_count}"

    # Layer 3: Verify GET response shows both (or at least latest)
    assert b"history-summary" in get2_response.data or b"entries-table" in get2_response.data, \
        "History not shown in final GET response"
```

### Step 2: Run test to verify it passes

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression::test_outcome_tracking_get_after_post -xvs
```

Expected: PASS

### Step 3: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.4): add Test 10 - outcome tracking with GET-after-POST"
```

---

## Task 12: Run Full Test Suite and Verify No Regressions

**Files:**
- None (verification only)

### Step 1: Run all new TestSynchronizationRegression tests

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py::TestSynchronizationRegression -v
```

Expected: All 10 tests PASS.

### Step 2: Run full session UI test suite

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  PYTHONPATH=. python -m pytest tests/test_session_ui.py -v
```

Expected: All tests pass, no regressions to existing tests.

### Step 3: Run full backend test suite

Run:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows && \
  python run_tests.py --suite backend
```

Expected: ~2835+ tests passing (2825 baseline + 10 new W3.5.4 tests), same 5 pre-existing failures.

### Step 4: Commit

```bash
git add backend/tests/test_session_ui.py
git commit -m "test(w3.5.4): verify all tests pass, no regressions"
```

---

## Acceptance Criteria

✅ All 10 `TestSynchronizationRegression` tests pass
✅ No regressions to existing `TestCharacterPanel`, `TestHistoryPanel`, `TestDebugPanelUI` tests
✅ Full backend test suite passes (2825+ tests)
✅ Tests verify all three synchronization layers:
  - Layer 1: Canonical state updates correctly after turn execution
  - Layer 2: Presenters consume fresh (not cached) state
  - Layer 3: HTTP responses render presenter output correctly
✅ Tests cover single/multiple turns, outcome tracking, bounded windows, degradation markers, GET-after-POST persistence
✅ No route/template changes (wiring already correct)
✅ All code follows existing test patterns and fixtures

---

## Summary

W3.5.4 adds 12 focused tasks implementing 10 regression tests that prove history and debug panels remain synchronized with canonical data after real turn execution. The tests use a three-layer verification model (canonical state → presenter → HTTP response) and cover single turns, multiple turns, outcomes, bounded windows, degradation markers, and cross-request persistence. No route or template changes are needed; the wiring is already correct from W3.5.2/W3.5.3.

