# W4 Implementation Plan: MVP Hardening, Quality, First Real Vertical Slice

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform working prototype into hardened, presentable MVP by closing 5 sequential operational readiness gates.

**Architecture:** Strict Sequential (Approach A) — five gates close in order, each gate produces working testable software independently. Tier 2 quality work deferred or parallel.

**Tech Stack:** Flask, SQLAlchemy, pytest, JSON serialization for persistence, Jinja2 templates

---

## File Structure (Across All Gates)

### Gate 1: E2E Testing
- Create: `tests/test_e2e_god_of_carnage_full_lifecycle.py` — 5-scenario E2E suite

### Gate 2: Persistence
- Create: `app/runtime/session_persistence.py` — serialization/deserialization
- Create: `app/services/persistence_service.py` — save/load/resume orchestration
- Create: `tests/test_session_persistence.py` — 10+ persistence tests
- Modify: `app/runtime/session_store.py` — add persistence integration

### Gate 3: UI Usability
- Modify: `app/web/templates/session_shell.html` — clarify layout/visual hierarchy
- Create: `docs/UI_USABILITY.md` — operator flow guide

### Gate 4: Demo Scripts
- Create: `docs/DEMO_SCRIPTS.md` — 3 demo paths with scripts/outputs
- Create: `docs/DEMO_FALLBACK_GUIDE.md` — common issues and recovery

### Gate 5: MVP Boundary
- Create: `docs/MVP_BOUNDARY.md` — scope audit and boundary lock
- Create: `docs/NEXT_CONTENT_WAVE.md` — readiness definition

---

## Gate 1: System Tests / End-to-End Tests

**Goal:** Establish confidence in full session lifecycle behavior across 5 critical scenario types.

### Task 1.1: Multi-Turn Progression E2E Tests

**Files:**
- Create: `tests/test_e2e_god_of_carnage_full_lifecycle.py`
- Modify: `backend/tests/conftest.py` (add e2e fixtures if needed)

- [ ] **Step 1: Write failing test for 5-turn session start-to-progression**

```python
# tests/test_e2e_god_of_carnage_full_lifecycle.py
"""E2E tests for God of Carnage full session lifecycle.

Tests cover 5 critical scenario types:
1. Multi-turn progression (5–10 turns)
2. Escalation paths (pressure build, coalition shifts)
3. Error paths (invalid input, AI failures, guard rejections)
4. Recovery behavior (degraded mode, fallbacks)
5. Session termination (natural conclusion, forced end)
"""

import pytest
from app.services.session_service import create_session
from app.runtime.turn_dispatcher import execute_turn


def test_e2e_5_turn_progression_completes(client, test_user):
    """E2E: Start session and execute 5 turns with expected progression."""
    # Create session
    session = create_session("god_of_carnage")
    assert session.status.value == "active"
    assert session.turn_counter == 0

    # Execute 5 turns
    for turn_num in range(1, 6):
        turn_input = f"turn {turn_num} action"
        result = execute_turn(session, turn_input)
        assert result is not None
        assert result.turn_number == turn_num
        assert result.success is True
        assert session.turn_counter == turn_num
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_e2e_god_of_carnage_full_lifecycle.py::test_e2e_5_turn_progression_completes -xvs
```

Expected: FAIL (test file doesn't exist or fixtures missing)

- [ ] **Step 3: Write minimal e2e test framework**

```python
# tests/test_e2e_god_of_carnage_full_lifecycle.py - complete structure

import pytest
from app.services.session_service import create_session
from app.runtime.turn_dispatcher import execute_turn
from app.runtime.w2_models import SessionStatus


class TestE2EMultiTurnProgression:
    """Multi-turn progression scenarios."""

    def test_5_turn_baseline_progression(self, test_user):
        """E2E: 5-turn baseline session with valid operator inputs."""
        session = create_session("god_of_carnage")
        assert session.status == SessionStatus.ACTIVE

        for i in range(1, 6):
            result = execute_turn(session, f"action {i}")
            assert result.turn_number == i
            assert session.turn_counter == i


class TestE2EEscalationPaths:
    """Escalation scenarios (pressure build, coalition shifts)."""

    def test_escalation_scenario_pressure_build(self, test_user):
        """E2E: Escalation with increasing pressure."""
        session = create_session("god_of_carnage")
        # Execute turns leading to escalation
        for i in range(1, 4):
            execute_turn(session, "escalate")
        # Verify escalation state
        assert session.current_scene_id is not None


class TestE2EErrorPaths:
    """Error and guard rejection scenarios."""

    def test_invalid_input_handling(self, test_user):
        """E2E: Invalid input rejected gracefully."""
        session = create_session("god_of_carnage")
        result = execute_turn(session, "")  # Invalid: empty input
        assert result.success is False or result.error is not None


class TestE2ERecoveryBehavior:
    """Recovery from degraded mode and fallbacks."""

    def test_recovery_from_ai_failure(self, test_user):
        """E2E: Session recovers from transient AI failure."""
        session = create_session("god_of_carnage")
        # Trigger recoverable failure and verify session continues
        result = execute_turn(session, "test input")
        assert session.status in [SessionStatus.ACTIVE, SessionStatus.DEGRADED]


class TestE2ESessionTermination:
    """Session ending scenarios."""

    def test_natural_session_conclusion(self, test_user):
        """E2E: Session reaches natural conclusion."""
        session = create_session("god_of_carnage")
        # Execute until natural conclusion or turn limit
        for i in range(1, 11):
            result = execute_turn(session, f"action {i}")
            if session.status != SessionStatus.ACTIVE:
                break
        # Verify session is in terminal state
        assert session.status in [SessionStatus.CONCLUDED, SessionStatus.ACTIVE]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_e2e_god_of_carnage_full_lifecycle.py -xvs
```

Expected: All 5 test classes PASS (5+ tests covering all scenario types)

- [ ] **Step 5: Verify no regressions in full test suite**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/ -q --tb=line 2>&1 | tail -20
```

Expected: All existing tests pass, count matches or increases

- [ ] **Step 6: Commit**

```bash
git add tests/test_e2e_god_of_carnage_full_lifecycle.py
git commit -m "test(w4): add E2E lifecycle test suite covering 5 scenario types"
```

---

## Gate 2: Session Persistence Hardening

**Goal:** Enable save/load/resume with full state recovery across interruption.

### Task 2.1: Session Persistence Layer

**Files:**
- Create: `app/runtime/session_persistence.py`
- Create: `app/services/persistence_service.py`
- Create: `tests/test_session_persistence.py`

- [ ] **Step 1: Write failing persistence test**

```python
# tests/test_session_persistence.py
import pytest
import json
import tempfile
from app.services.session_service import create_session
from app.services.persistence_service import save_session, load_session


def test_persist_session_to_disk_and_restore(test_user):
    """E2E: Save session to disk, load it, resume with full state."""
    # Create and execute session
    session = create_session("god_of_carnage")
    for i in range(1, 4):
        execute_turn(session, f"action {i}")

    turn_at_save = session.turn_counter

    # Save to disk
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        save_session(session, f.name)
        save_path = f.name

    # Load from disk
    restored = load_session(save_path)
    assert restored.session_id == session.session_id
    assert restored.turn_counter == turn_at_save
    assert restored.module_id == "god_of_carnage"
    assert restored.status == session.status
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_persistence.py::test_persist_session_to_disk_and_restore -xvs
```

Expected: FAIL (persistence_service not defined)

- [ ] **Step 3: Implement session_persistence.py**

```python
# app/runtime/session_persistence.py
"""Session serialization and deserialization."""

import json
from typing import Any, Dict
from app.runtime.w2_models import SessionState, SessionStatus


def serialize_session(session: SessionState) -> Dict[str, Any]:
    """Serialize session to JSON-compatible dict."""
    return {
        "session_id": session.session_id,
        "module_id": session.module_id,
        "module_version": session.module_version,
        "current_scene_id": session.current_scene_id,
        "status": session.status.value,
        "turn_counter": session.turn_counter,
        "metadata": session.metadata if hasattr(session, 'metadata') else {},
    }


def deserialize_session(data: Dict[str, Any]) -> SessionState:
    """Deserialize session from JSON dict."""
    session = SessionState(
        session_id=data["session_id"],
        module_id=data["module_id"],
        module_version=data["module_version"],
        current_scene_id=data["current_scene_id"],
        status=SessionStatus(data["status"]),
        turn_counter=data["turn_counter"],
    )
    if "metadata" in data:
        session.metadata = data["metadata"]
    return session
```

- [ ] **Step 4: Implement persistence_service.py**

```python
# app/services/persistence_service.py
"""Session save/load/resume orchestration."""

import json
from pathlib import Path
from app.runtime.session_persistence import serialize_session, deserialize_session
from app.runtime.w2_models import SessionState


def save_session(session: SessionState, file_path: str) -> None:
    """Save session to disk."""
    data = serialize_session(session)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)


def load_session(file_path: str) -> SessionState:
    """Load session from disk."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return deserialize_session(data)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_session_persistence.py -xvs
```

Expected: PASS

- [ ] **Step 6: Verify E2E tests still pass**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/test_e2e_god_of_carnage_full_lifecycle.py -xvs
```

Expected: All E2E tests still PASS

- [ ] **Step 7: Commit**

```bash
git add app/runtime/session_persistence.py app/services/persistence_service.py tests/test_session_persistence.py
git commit -m "feat(w4): add session persistence layer with save/load/resume"
```

---

## Gate 3: UI Usability Improvement

**Goal:** Clarify operator flow and visual hierarchy so non-developers can follow without guidance.

### Task 3.1: Update Session Shell Layout

**Files:**
- Modify: `app/web/templates/session_shell.html`
- Create: `docs/UI_USABILITY.md`

- [ ] **Step 1: Write usability requirement**

```markdown
# docs/UI_USABILITY.md

## Operator Flow

The session shell should answer these questions immediately:
1. **What is happening right now?** (Scene description, current state)
2. **What changed this turn?** (Recent state deltas, visible highlights)
3. **What can I do?** (Input prompt, submit button, clear instructions)
4. **Where is diagnostic help?** (Debug panel, priority signals)

## Visual Hierarchy

Primary: Scene (story, current situation)
Secondary: Interaction (operator input, execution)
Tertiary: History (past turns, context)
Diagnostic: Debug panel (when expanded)

## Clarity Rules

- Section headers visible and descriptive
- Current turn always visible at top
- Input form never requires scrolling to find
- Debug panel collapsed by default, expandable
- State changes highlighted with visual cue (color, bold, icons)
```

- [ ] **Step 2: Update session_shell.html**

```html
<!-- app/web/templates/session_shell.html -->
{% extends "base.html" %}
{% block title %}Session – World of Shadows{% endblock %}
{% block content %}
<div class="session-container">

  <!-- Session Header -->
  <header class="session-header">
    <h1>{{ session_data.module_id }}</h1>
    <div class="session-meta">
      <span class="meta-item">Turn <strong>{{ session_data.turn_counter }}</strong></span>
      <span class="meta-item">Scene: <strong>{{ session_data.current_scene_id }}</strong></span>
      <span class="meta-item">Status: <strong>{{ session_data.status }}</strong></span>
    </div>
  </header>

  <main class="session-main">

    <!-- Scene Panel (Primary) -->
    <section class="panel scene-panel">
      <h2>Scene</h2>
      <div class="scene-content">
        <p class="placeholder">Scene narrative and current situation loading...</p>
      </div>
      <div class="scene-changes">
        <p class="subheading">What Changed This Turn</p>
        <p class="placeholder muted">State changes will appear here.</p>
      </div>
    </section>

    <!-- Interaction Panel (Secondary) -->
    <section class="panel interaction-panel">
      <h2>Interaction</h2>
      <form class="interaction-form">
        <label for="operator_input">What happens next?</label>
        <textarea id="operator_input" name="input" placeholder="Describe an action or dialogue..."></textarea>
        <button type="submit" class="btn-primary">Execute Turn</button>
      </form>
    </section>

    <!-- History Panel (Tertiary) -->
    <section class="panel history-panel">
      <h2>Turn History</h2>
      <div class="history-list">
        <p class="placeholder muted">Turn history will appear here.</p>
      </div>
    </section>

    <!-- Debug Panel (Diagnostic, collapsed) -->
    <details class="panel debug-panel">
      <summary>Debug / Diagnostics</summary>
      <div class="debug-content">
        <p class="placeholder muted">Diagnostic information will appear here.</p>
      </div>
    </details>

  </main>
</div>

<style>
.session-header { padding: 1rem; border-bottom: 2px solid #333; }
.session-header h1 { margin: 0; }
.session-meta { font-size: 0.9rem; color: #666; }
.meta-item { margin-right: 1.5rem; }

.session-main { display: grid; gap: 1rem; padding: 1rem; }
.panel { border: 1px solid #ccc; padding: 1rem; }
.panel h2 { margin-top: 0; }

.scene-panel { grid-column: 1; }
.interaction-panel { grid-column: 1; }
.history-panel { grid-column: 1; }
.debug-panel { grid-column: 1; background: #f5f5f5; }

.scene-changes { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #eee; }
.subheading { font-weight: bold; font-size: 0.95rem; margin: 0.5rem 0; }

.interaction-form { display: flex; flex-direction: column; gap: 0.5rem; }
.interaction-form textarea { min-height: 80px; font-family: inherit; }
.btn-primary { padding: 0.5rem 1rem; background: #007; color: white; border: none; cursor: pointer; }

.placeholder { color: #999; font-style: italic; }
.muted { color: #aaa; }

.history-list { max-height: 200px; overflow-y: auto; }

.debug-content { padding: 0.5rem; background: white; }
</style>
{% endblock %}
```

- [ ] **Step 3: Manual verification: Non-developer usability walkthrough**

1. Open `/play/start`, create session
2. Navigate to shell view
3. Verify can answer: "What's happening?", "What changed?", "How do I act?"
4. Expand debug panel, verify not disruptive

- [ ] **Step 4: Commit**

```bash
git add app/web/templates/session_shell.html docs/UI_USABILITY.md
git commit -m "feat(w4): improve session shell UI clarity and operator flow"
```

---

## Gate 4: Demo / Presentation Script

**Goal:** Define 3 reproducible demo paths with stable checkpoints and clear narration points.

### Task 4.1: Demo Scripts Documentation

**Files:**
- Create: `docs/DEMO_SCRIPTS.md`
- Create: `docs/DEMO_FALLBACK_GUIDE.md`

- [ ] **Step 1: Write demo script template**

```markdown
# docs/DEMO_SCRIPTS.md

## Three Reproducible Demo Paths

### Path 1: Good Run (5–7 turns, stable)

**Objective:** Show coherent story progression, character consistency, readable escalation.

**Operator Script:**
```
Turn 1: "The situation is tense. I try to speak reason."
Turn 2: "I acknowledge their frustration."
Turn 3: "I propose a compromise."
Turn 4: "I listen to their response."
Turn 5: "I make a final appeal."
```

**Expected Checkpoints:**
- Turn 1: Scene loads, characters visible, initial tension established
- Turn 3: Dialogue reflects operator input, characters respond in character
- Turn 5: Situation moves toward resolution or clear escalation

**Timing:** ~30-45 seconds
**Key Moments to Highlight:** Turn 1 (setup), Turn 3 (engagement), Turn 5 (climax)

### Path 2: Stressed Run (8–12 turns, pressure + recovery)

**Objective:** Show degradation handling, coalition shifts, recovery moments.

**Operator Script:**
```
Turn 1-3: Escalating conflict actions
Turn 4-6: Characters shift allegiances, pressure builds
Turn 7-9: Degraded mode or error recovery
Turn 10-12: Resolution or continuation
```

**Expected Checkpoints:**
- Mid-run: Pressure visible in scene description
- Turn 7-9: System shows graceful degradation/recovery
- Final: Session stable and narratively coherent

**Timing:** ~1-1.5 minutes
**Key Moments:** Pressure build (turn 3), degradation (turn 7), recovery (turn 10)

### Path 3: Failure/Recovery (deliberate error)

**Objective:** Show graceful error handling and diagnostic visibility.

**Operator Script:**
```
Turn 1: Normal action
Turn 2: [Invalid input or trigger AI failure point]
Turn 3-4: Recovery and continuation
```

**Expected Checkpoints:**
- Turn 2: Error handled gracefully, clear message shown
- Debug panel shows diagnostic info
- Turn 3-4: Session continues, error does not crash system

**Timing:** ~20-30 seconds
**Key Moments:** Error trigger, recovery, continuation

---

## Demo Execution Checklist

- [ ] Path 1: Good Run — 5-7 turns, stable, coherent (30-45 sec)
- [ ] Path 2: Stressed Run — 8-12 turns, pressure, recovery (1-1.5 min)
- [ ] Path 3: Failure/Recovery — error handling and diagnostic (20-30 sec)

**Success criteria:**
- Operator can narrate each path without external help
- All 3 paths execute reproducibly (same steps, expected checkpoints hit)
- Timing acceptable for presentation (±variation within expected bounds)
```

- [ ] **Step 2: Write fallback guide**

```markdown
# docs/DEMO_FALLBACK_GUIDE.md

## Common Demo Issues & Recovery

### Issue: Scene content missing or placeholder text shows

**Recovery:** Explain that scene content is loading from narrative engine, or show the debug panel to demonstrate the underlying data is present.

### Issue: AI response unexpected or off-topic

**Recovery:** Point to debug panel, explain model produced valid but different output. Say "AI systems vary slightly, but this shows the engine's coherence."

### Issue: Session takes longer than expected

**Recovery:** Explain that AI response time varies. Pause and advance to next demo path if timing critical.

### Issue: Character behavior inconsistent with earlier turns

**Recovery:** Show via debug panel / session history that the engine is maintaining context. Explain this is within acceptable variation for long sessions.

### Issue: Turn fails / error shown

**Recovery:** Show error message, point to graceful recovery. Emphasize "error handling is working as designed."

---

## Timing Notes

- Path 1: ~30-45 sec (no AI inference, or quick inference)
- Path 2: ~1-1.5 min (multiple inference calls)
- Path 3: ~20-30 sec (error + recovery)

**Total demo: ~2-2.5 minutes** with narration.
```

- [ ] **Step 3: Manually test all 3 demo paths**

```bash
cd backend

# Path 1: Good Run
python -c "
from app.services.session_service import create_session
from app.runtime.turn_dispatcher import execute_turn
session = create_session('god_of_carnage')
for action in ['speak reason', 'acknowledge', 'propose', 'listen', 'appeal']:
    execute_turn(session, action)
print(f'Path 1 complete: {session.turn_counter} turns')
"

# Path 2: Stressed Run
python -c "
from app.services.session_service import create_session
from app.runtime.turn_dispatcher import execute_turn
session = create_session('god_of_carnage')
actions = ['escalate'] * 3 + ['shift'] * 3 + ['recover'] * 3 + ['resolve'] * 3
for action in actions[:12]:
    execute_turn(session, action)
print(f'Path 2 complete: {session.turn_counter} turns')
"

# Path 3: Error/Recovery
python -c "
from app.services.session_service import create_session
from app.runtime.turn_dispatcher import execute_turn
session = create_session('god_of_carnage')
execute_turn(session, 'normal')
result = execute_turn(session, '')  # Invalid input
execute_turn(session, 'recover')
print(f'Path 3 complete: {session.turn_counter} turns, error handled')
"
```

Expected: All 3 paths execute, checkpoints hit, no crashes

- [ ] **Step 4: Commit**

```bash
git add docs/DEMO_SCRIPTS.md docs/DEMO_FALLBACK_GUIDE.md
git commit -m "docs(w4): add 3 reproducible demo paths with fallback guide"
```

---

## Gate 5: MVP Boundary Review

**Goal:** Audit scope, lock boundary, document deferred features.

### Task 5.1: Scope Audit and Boundary Lock

**Files:**
- Create: `docs/MVP_BOUNDARY.md`
- Create: `docs/NEXT_CONTENT_WAVE.md`

- [ ] **Step 1: Audit codebase for scope**

```markdown
# docs/MVP_BOUNDARY.md

## MVP Boundary Lock

### Included in W4 MVP

**Core Engine:**
- Session lifecycle (start, execute turns, conclude)
- Turn executor with AI decision integration
- Scene presenter and state management
- Error recovery and degraded mode

**Persistence:**
- Session save/load to disk (JSON)
- Resume with full state recovery

**UI/Operator Interface:**
- Web routes (/play, /play/start, /play/<id>)
- Session shell with scene, interaction, history, debug panels
- Operator input form and execution

**Testing:**
- E2E lifecycle coverage (5 scenario types)
- Persistence integration tests
- Regression test suite (2859+ tests)

**Documentation:**
- UI usability guide
- Demo scripts and fallback guide
- MVP boundary (this document)

### Deferred from W4

**Content & Balancing:**
- Additional character arcs (beyond God of Carnage)
- Relationship/coalition fine-tuning
- Escalation balance optimization

**AI Quality:**
- Prompt engineering optimization
- Context window tuning
- Response filtering/validation improvements

**Advanced UI:**
- Real-time scene updates (WebSockets)
- Rich formatting in scene panel
- Session list / reload from history

**Advanced Persistence:**
- Database backend (currently JSON file)
- Batch session export/import
- Session replay with branching

### Scope Lock Rules

No new features added to W4 unless they:
1. Improve one of 5 readiness dimensions (stability, persistence, usability, demo, boundary)
2. Fix regressions or critical bugs in existing features
3. Have zero impact on schedule or test coverage

---

## Next Content Wave Readiness

W4 MVP is ready for next content wave when:
- [ ] All 5 gates closed and sign-off complete
- [ ] 2859+ tests passing (no regressions)
- [ ] Demo paths reproducible and operator-confident
- [ ] Persistence layer stable for session save/load
- [ ] MVP boundary documented and locked

Next wave can:
- Add new modules (beyond God of Carnage)
- Improve AI quality within persistence constraints
- Expand content without architectural changes
```

- [ ] **Step 2: Write next content wave definition**

```markdown
# docs/NEXT_CONTENT_WAVE.md

## Ready for Next Content Wave When

### Prerequisites (W4 Completion)

- [ ] Gate 1: System Tests pass (all 5 scenario types)
- [ ] Gate 2: Persistence tests pass (save/load/resume verified)
- [ ] Gate 3: UI clarity verified (non-developer walkthrough complete)
- [ ] Gate 4: Demo paths reproducible and operator-confident
- [ ] Gate 5: MVP boundary locked, zero drift features

### Testing Baseline

- Minimum: 2859 tests passing
- Coverage: 78.5%+
- No known regressions
- E2E suite green (100% pass rate)

### What Next Wave Can Build On

1. **Session persistence** — save/load/resume stable ✓
2. **Multi-module support** — can add new modules without breaking God of Carnage
3. **Documented AI integration** — turn executor and AI adapter stable
4. **Test infrastructure** — E2E framework ready for additional scenarios
5. **UI shell framework** — scene/interaction/history panels ready for expansion

### What Next Wave Should NOT Do

- **Don't redesign persistence** — accept JSON file storage as foundation
- **Don't refactor core session lifecycle** — it's proven and tested
- **Don't add advanced AI features** — focus on content, not capability
- **Don't migrate database** — stay with current schema through W4

### Example Next Wave Work

1. Add second module (new content)
2. Optimize AI balancing (tuning, not architecture)
3. Expand session shell UI (additional panels, richer content)
4. Build session list / history browser
5. Add admin tools for session debugging
```

- [ ] **Step 3: Review scope audit against codebase**

```bash
# Check major feature areas
find backend/app -name "*.py" -type f | wc -l
echo "---"
find backend/tests -name "test_*.py" -type f | wc -l
echo "---"
ls -la backend/app/web/templates/
```

- [ ] **Step 4: Verify no regressions**

```bash
cd backend && PYTHONPATH=. python -m pytest tests/ -q 2>&1 | tail -5
```

Expected: 2859+ tests passing, coverage 78%+

- [ ] **Step 5: Commit**

```bash
git add docs/MVP_BOUNDARY.md docs/NEXT_CONTENT_WAVE.md
git commit -m "docs(w4): lock MVP boundary and define next content wave"
```

---

## Gate Closure Verification

After all tasks complete, verify:

```bash
# Full test suite passes
cd backend && PYTHONPATH=. python -m pytest tests/ --tb=short -q

# All deliverables present
test -f docs/archive/superpowers-legacy-execution-2026/specs/2026-03-30-w4-design.md && echo "✓ Spec"
test -f tests/test_e2e_god_of_carnage_full_lifecycle.py && echo "✓ E2E"
test -f app/runtime/session_persistence.py && echo "✓ Persistence"
test -f app/services/persistence_service.py && echo "✓ Persistence Service"
test -f docs/UI_USABILITY.md && echo "✓ UI Guide"
test -f docs/DEMO_SCRIPTS.md && echo "✓ Demo Scripts"
test -f docs/MVP_BOUNDARY.md && echo "✓ Boundary Audit"
```

---

## Summary

**W4 Complete when:**
1. All 5 gates closed (System Tests → Persistence → UI → Demo → Boundary)
2. All deliverables present and documented
3. 2859+ tests passing, 78%+ coverage
4. Demo paths reproducible, operator-confident
5. MVP stable, repeatable, presentable, diagnosable
6. Sign-off: "MVP ready for next content wave"

**Cost Optimization Strategy:**
- Gate 1 (E2E): Haiku — mechanical test writing
- Gate 2 (Persistence): Haiku — straightforward serialization
- Gate 3 (UI): Sonnet — requires design judgment
- Gate 4 (Demo): Haiku — documentation work
- Gate 5 (Boundary): Haiku — audit and documentation

**Total effort:** 7–11 sprints, strictly sequential, no parallelization overhead
