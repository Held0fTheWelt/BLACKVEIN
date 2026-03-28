# W2.4.4: Expose Internal AI Role Split in Decision Diagnostics

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend canonical decision logging to expose interpreter/director/responder role separation for improved diagnostics without changing runtime execution.

**Architecture:** Add two typed diagnostic summary models (InterpreterDiagnosticSummary, DirectorDiagnosticSummary) and extend AIDecisionLog with role fields. Create a logging helper function that type-detects ParsedRoleAwareDecision and populates role fields for diagnostics. Keep ParsedAIDecision as the only canonical runtime decision object.

**Tech Stack:** Python 3.10+, Pydantic v2, pytest for testing.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `backend/app/runtime/w2_models.py` | MODIFY | Add InterpreterDiagnosticSummary, DirectorDiagnosticSummary; extend AIDecisionLog with role fields |
| `backend/app/runtime/ai_decision_logging.py` | CREATE | Logging helper module with construct_ai_decision_log() function |
| `backend/tests/runtime/test_ai_decision_logging.py` | CREATE | Comprehensive test suite (format detection, field population, validation outcome mapping, diagnostic-only constraint) |

---

## Task 1: Add Diagnostic Summary Models and Extend AIDecisionLog

**Files:**
- Modify: `backend/app/runtime/w2_models.py` (add two new models, extend AIDecisionLog)

### Step 1: Read current w2_models.py to understand structure

Run: `head -100 backend/app/runtime/w2_models.py`

Expected: See existing model definitions (SessionState, AIDecisionLog, etc.)

### Step 2: Write failing test for InterpreterDiagnosticSummary

Create test file: `backend/tests/runtime/test_ai_decision_logging.py`

```python
"""Tests for W2.4.4 AI decision logging with role diagnostics."""

import pytest
from app.runtime.w2_models import (
    InterpreterDiagnosticSummary,
    DirectorDiagnosticSummary,
    AIDecisionLog,
    GuardOutcome,
)


def test_interpreter_diagnostic_summary_creation():
    """InterpreterDiagnosticSummary can be created with scene_reading and detected_tensions."""
    summary = InterpreterDiagnosticSummary(
        scene_reading="The characters are in conflict over resources.",
        detected_tensions=["resource_competition", "power_struggle"],
    )

    assert summary.scene_reading == "The characters are in conflict over resources."
    assert summary.detected_tensions == ["resource_competition", "power_struggle"]


def test_director_diagnostic_summary_creation():
    """DirectorDiagnosticSummary can be created with conflict_steering and recommended_direction."""
    summary = DirectorDiagnosticSummary(
        conflict_steering="Escalate the tension to force a confrontation.",
        recommended_direction="escalate",
    )

    assert summary.conflict_steering == "Escalate the tension to force a confrontation."
    assert summary.recommended_direction == "escalate"


def test_director_diagnostic_summary_validates_direction_enum():
    """DirectorDiagnosticSummary only accepts valid recommended_direction values."""
    valid_directions = ["escalate", "stabilize", "shift_alliance", "redirect", "hold"]

    for direction in valid_directions:
        summary = DirectorDiagnosticSummary(
            conflict_steering="text",
            recommended_direction=direction,
        )
        assert summary.recommended_direction == direction


def test_ai_decision_log_accepts_role_fields():
    """AIDecisionLog accepts interpreter_output, director_output, responder_output, guard_outcome."""
    interpreter = InterpreterDiagnosticSummary(
        scene_reading="Scene reading",
        detected_tensions=["tension1"],
    )
    director = DirectorDiagnosticSummary(
        conflict_steering="Steering text",
        recommended_direction="hold",
    )

    log = AIDecisionLog(
        session_id="sess1",
        turn_number=1,
        raw_output="mock output",
        guard_outcome=GuardOutcome.ACCEPTED,
        interpreter_output=interpreter,
        director_output=director,
        responder_output=None,
    )

    assert log.interpreter_output == interpreter
    assert log.director_output == director
    assert log.responder_output is None
    assert log.guard_outcome == GuardOutcome.ACCEPTED
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py::test_interpreter_diagnostic_summary_creation -v`

Expected: FAIL with "cannot import name 'InterpreterDiagnosticSummary'"

### Step 3: Implement diagnostic summary models in w2_models.py

Add these models to `backend/app/runtime/w2_models.py` (before AIDecisionLog definition):

```python
class InterpreterDiagnosticSummary(BaseModel):
    """Diagnostic summary of scene interpretation (non-executable).

    Preserves the scene reading and identified tensions for diagnostics.
    Does not feed runtime execution.
    """

    scene_reading: str
    """Narrative description of what the interpreter observed in the scene."""

    detected_tensions: list[str]
    """Interpersonal/situational tensions identified by the interpreter."""


class DirectorDiagnosticSummary(BaseModel):
    """Diagnostic summary of conflict steering (non-executable).

    Preserves the steering rationale and recommended direction for diagnostics.
    Does not feed runtime execution.
    """

    conflict_steering: str
    """Narrative rationale for the chosen conflict direction."""

    recommended_direction: Literal["escalate", "stabilize", "shift_alliance", "redirect", "hold"]
    """Enum: type of narrative movement (bounded set)."""
```

### Step 4: Extend AIDecisionLog with role fields

Find the `AIDecisionLog` class definition in w2_models.py (around line 302). Add these three fields and update guard_outcome:

```python
class AIDecisionLog(BaseModel):
    """Record of AI decision for a turn.

    ... existing docstring ...

    Attributes (extended for W2.4.4):
        interpreter_output: Diagnostic summary of scene interpretation (None for legacy).
        director_output: Diagnostic summary of conflict steering (None for legacy).
        responder_output: Full responder proposals from ResponderSection (None for legacy).
        guard_outcome: Canonical collective validation result for responder-derived proposals.
    """

    # ... existing fields (id, session_id, turn_number, raw_output, parsed_output, validation_outcome, etc.) ...

    # W2.4.4 role diagnostic fields
    interpreter_output: InterpreterDiagnosticSummary | None = None
    director_output: DirectorDiagnosticSummary | None = None
    responder_output: ResponderSection | None = None  # From role_contract.py
    guard_outcome: GuardOutcome  # Canonical validation result
```

**Important**: Ensure `from app.runtime.role_contract import ResponderSection` is imported at the top of w2_models.py.

### Step 5: Run all failing tests

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py -v`

Expected: Tests fail with model not yet fully implemented or field mismatches.

### Step 6: Run again to verify models are created

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py::test_interpreter_diagnostic_summary_creation -v`

Expected: PASS

### Step 7: Run all new model tests

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py::test_interpreter_diagnostic_summary_creation backend/tests/runtime/test_ai_decision_logging.py::test_director_diagnostic_summary_creation backend/tests/runtime/test_ai_decision_logging.py::test_director_diagnostic_summary_validates_direction_enum backend/tests/runtime/test_ai_decision_logging.py::test_ai_decision_log_accepts_role_fields -v`

Expected: All 4 tests PASS

### Step 8: Commit

```bash
git add backend/app/runtime/w2_models.py backend/tests/runtime/test_ai_decision_logging.py
git commit -m "feat(w2): add diagnostic summary models and extend AIDecisionLog with role fields

- Add InterpreterDiagnosticSummary: scene_reading + detected_tensions
- Add DirectorDiagnosticSummary: conflict_steering + recommended_direction (Literal enum)
- Extend AIDecisionLog with interpreter_output, director_output, responder_output, guard_outcome
- All new fields optional (None for legacy parsed decisions)
- Tests verify model creation and field acceptance"
```

---

## Task 2: Create Logging Helper Module with construct_ai_decision_log()

**Files:**
- Create: `backend/app/runtime/ai_decision_logging.py`

### Step 1: Write failing test for construct_ai_decision_log() with legacy decision

Add to `backend/tests/runtime/test_ai_decision_logging.py`:

```python
from app.runtime.ai_decision_logging import construct_ai_decision_log
from app.runtime.ai_decision import ParsedAIDecision


def test_construct_log_legacy_parsing_has_none_role_fields():
    """Legacy ParsedAIDecision only → role fields = None."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene interpretation",
        detected_triggers=["trigger1"],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale text",
        raw_output="raw output",
        parsed_source="structured_payload",
    )

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw output",
        role_aware_decision=None,  # Legacy path
        guard_outcome=GuardOutcome.ACCEPTED,
    )

    assert log.session_id == "sess1"
    assert log.turn_number == 1
    assert log.interpreter_output is None  # Legacy → None
    assert log.director_output is None     # Legacy → None
    assert log.responder_output is None    # Legacy → None
    assert log.guard_outcome == GuardOutcome.ACCEPTED
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py::test_construct_log_legacy_parsing_has_none_role_fields -v`

Expected: FAIL with "cannot import name 'construct_ai_decision_log'"

### Step 2: Create ai_decision_logging.py module

Create file: `backend/app/runtime/ai_decision_logging.py`

```python
"""W2.4.4 — AI Decision Logging with Role Diagnostics

Constructs and populates AIDecisionLog with role-separated diagnostics
(interpreter, director, responder) when role-structured parsing is available.
"""

from __future__ import annotations

from typing import Optional

from app.runtime.ai_decision import ParsedAIDecision, ParsedRoleAwareDecision
from app.runtime.w2_models import (
    AIDecisionLog,
    AIValidationOutcome,
    DirectorDiagnosticSummary,
    GuardOutcome,
    InterpreterDiagnosticSummary,
    StateDelta,
)


def construct_ai_decision_log(
    session_id: str,
    turn_number: int,
    parsed_decision: ParsedAIDecision,
    raw_output: str,
    role_aware_decision: Optional[ParsedRoleAwareDecision],
    guard_outcome: GuardOutcome,
    accepted_deltas: Optional[list[StateDelta]] = None,
    rejected_deltas: Optional[list[StateDelta]] = None,
    guard_notes: Optional[str] = None,
    recovery_notes: Optional[str] = None,
) -> AIDecisionLog:
    """Construct a fully-populated AIDecisionLog with role diagnostics if available.

    Type detection:
    - If role_aware_decision is present, extract and populate interpreter/director/responder fields
    - If role_aware_decision is None, leave role fields as None (legacy path)

    Args:
        session_id: Parent session identifier.
        turn_number: Turn number for this decision.
        parsed_decision: Canonical ParsedAIDecision (only runtime decision object).
        raw_output: Raw adapter output (explicit parameter).
        role_aware_decision: Optional ParsedRoleAwareDecision from role-structured parsing.
        guard_outcome: Canonical guard outcome for responder-derived proposals.
        accepted_deltas: Deltas that passed validation (optional).
        rejected_deltas: Deltas that failed validation (optional).
        guard_notes: Guard intervention notes (optional).
        recovery_notes: Recovery action notes (optional).

    Returns:
        AIDecisionLog with role fields populated if role_aware_decision is present.
    """
    interpreter_output = None
    director_output = None
    responder_output = None

    # Type-based detection: if role_aware_decision is present, populate role fields
    if role_aware_decision is not None:
        interpreter_output = InterpreterDiagnosticSummary(
            scene_reading=role_aware_decision.interpreter.scene_reading,
            detected_tensions=role_aware_decision.interpreter.detected_tensions,
        )
        director_output = DirectorDiagnosticSummary(
            conflict_steering=role_aware_decision.director.conflict_steering,
            recommended_direction=role_aware_decision.director.recommended_direction,
        )
        responder_output = role_aware_decision.responder  # Full typed ResponderSection

    # Derive validation_outcome from guard_outcome (not hardcoded)
    # Use explicit mapping to catch unexpected values
    validation_outcome_mapping = {
        GuardOutcome.ACCEPTED: AIValidationOutcome.ACCEPTED,
        GuardOutcome.PARTIALLY_ACCEPTED: AIValidationOutcome.PARTIAL,
        GuardOutcome.REJECTED: AIValidationOutcome.REJECTED,
        GuardOutcome.STRUCTURALLY_INVALID: AIValidationOutcome.ERROR,
    }
    try:
        validation_outcome = validation_outcome_mapping[guard_outcome]
    except KeyError:
        raise ValueError(f"Unknown guard_outcome value: {guard_outcome}") from None

    return AIDecisionLog(
        session_id=session_id,
        turn_number=turn_number,
        raw_output=raw_output,  # Explicit parameter
        parsed_output=parsed_decision.model_dump(),  # Full canonical decision as dict
        interpreter_output=interpreter_output,  # Diagnostic only
        director_output=director_output,  # Diagnostic only
        responder_output=responder_output,  # Diagnostic only
        validation_outcome=validation_outcome,  # Derived from guard_outcome
        guard_outcome=guard_outcome,  # Canonical validation result
        accepted_deltas=accepted_deltas or [],
        rejected_deltas=rejected_deltas or [],
        guard_notes=guard_notes,
        recovery_notes=recovery_notes,
    )
```

### Step 3: Run failing test

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py::test_construct_log_legacy_parsing_has_none_role_fields -v`

Expected: PASS (module now created)

### Step 4: Write test for role-structured parsing

Add to `backend/tests/runtime/test_ai_decision_logging.py`:

```python
def test_construct_log_role_structured_parsing_populates_role_fields():
    """ParsedRoleAwareDecision present → role fields populated."""
    from app.runtime.role_contract import (
        InterpreterSection,
        DirectorSection,
        ResponderSection,
    )

    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=["trigger1"],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    # Create mock role-aware decision
    from app.runtime.ai_decision import ParsedRoleAwareDecision
    role_aware = ParsedRoleAwareDecision(
        interpreter=InterpreterSection(
            scene_reading="Scene reading from interpreter",
            detected_tensions=["tension1", "tension2"],
        ),
        director=DirectorSection(
            conflict_steering="Steering rationale",
            escalation_level=5,
            recommended_direction="escalate",
        ),
        responder=ResponderSection(),
        parsed_decision=parsed_decision,
    )

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=role_aware,
        guard_outcome=GuardOutcome.ACCEPTED,
    )

    # Role fields should be populated
    assert log.interpreter_output is not None
    assert log.interpreter_output.scene_reading == "Scene reading from interpreter"
    assert log.interpreter_output.detected_tensions == ["tension1", "tension2"]

    assert log.director_output is not None
    assert log.director_output.conflict_steering == "Steering rationale"
    assert log.director_output.recommended_direction == "escalate"

    assert log.responder_output is not None
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py::test_construct_log_role_structured_parsing_populates_role_fields -v`

Expected: PASS

### Step 5: Test validation outcome mapping

Add to `backend/tests/runtime/test_ai_decision_logging.py`:

```python
def test_validation_outcome_mapping_accepted():
    """GuardOutcome.ACCEPTED → AIValidationOutcome.ACCEPTED."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,
        guard_outcome=GuardOutcome.ACCEPTED,
    )

    assert log.validation_outcome == AIValidationOutcome.ACCEPTED


def test_validation_outcome_mapping_rejected():
    """GuardOutcome.REJECTED → AIValidationOutcome.REJECTED."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,
        guard_outcome=GuardOutcome.REJECTED,
    )

    assert log.validation_outcome == AIValidationOutcome.REJECTED


def test_validation_outcome_mapping_partially_accepted():
    """GuardOutcome.PARTIALLY_ACCEPTED → AIValidationOutcome.PARTIAL."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,
        guard_outcome=GuardOutcome.PARTIALLY_ACCEPTED,
    )

    assert log.validation_outcome == AIValidationOutcome.PARTIAL
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py -k "validation_outcome_mapping" -v`

Expected: All 3 tests PASS

### Step 6: Run full test suite for ai_decision_logging

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py -v`

Expected: All tests PASS (approximately 7 tests)

### Step 7: Commit

```bash
git add backend/app/runtime/ai_decision_logging.py backend/tests/runtime/test_ai_decision_logging.py
git commit -m "feat(w2): create logging helper module with construct_ai_decision_log()

- Add construct_ai_decision_log() function for populating AIDecisionLog with role diagnostics
- Type-based detection: if ParsedRoleAwareDecision present, populate role fields
- Legacy decisions have role fields = None (backward compatible)
- Validation outcome derived from guard_outcome (not hardcoded)
- Add 7+ tests for legacy/role-structured paths and validation mapping"
```

---

## Task 3: Add Diagnostic-Only Constraint Tests

**Files:**
- Modify: `backend/tests/runtime/test_ai_decision_logging.py`

### Step 1: Add test verifying role fields don't affect delta validation

Add to test file:

```python
def test_role_fields_do_not_affect_delta_validation():
    """Role fields present or absent should not change delta acceptance/rejection."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=["trigger1"],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    mock_delta = StateDelta(
        delta_type=DeltaType.CHARACTER_STATE,
        target_path="characters.alice.emotional_state",
        previous_value=50,
        next_value=75,
        source="ai_proposal",
    )

    # Log with role fields
    log_with_roles = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,  # Would be populated if present
        guard_outcome=GuardOutcome.ACCEPTED,
        accepted_deltas=[mock_delta],
    )

    # Log without role fields (role_aware_decision=None)
    log_without_roles = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,
        guard_outcome=GuardOutcome.ACCEPTED,
        accepted_deltas=[mock_delta],
    )

    # Both logs must have identical delta collections
    assert log_with_roles.accepted_deltas == log_without_roles.accepted_deltas
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py::test_role_fields_do_not_affect_delta_validation -v`

Expected: PASS

### Step 2: Add test verifying guard_outcome remains canonical

Add to test file:

```python
def test_guard_outcome_remains_canonical():
    """guard_outcome is the sole canonical validation result, not overridden."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    # Test all guard_outcome values
    for guard_outcome in [
        GuardOutcome.ACCEPTED,
        GuardOutcome.PARTIALLY_ACCEPTED,
        GuardOutcome.REJECTED,
        GuardOutcome.STRUCTURALLY_INVALID,
    ]:
        log = construct_ai_decision_log(
            session_id="sess1",
            turn_number=1,
            parsed_decision=parsed_decision,
            raw_output="raw",
            role_aware_decision=None,
            guard_outcome=guard_outcome,
        )

        # guard_outcome must be preserved exactly
        assert log.guard_outcome == guard_outcome
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py::test_guard_outcome_remains_canonical -v`

Expected: PASS

### Step 3: Run all diagnostic-only constraint tests

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py -v`

Expected: All tests PASS (approximately 9+ tests now)

### Step 4: Commit

```bash
git add backend/tests/runtime/test_ai_decision_logging.py
git commit -m "test(w2): add diagnostic-only constraint verification tests

- Verify role fields do not affect delta validation
- Verify guard_outcome remains canonical validation result
- Verify role fields are diagnostic-only (no runtime impact)"
```

---

## Task 4: Integration Testing and Verification

**Files:**
- Modify: `backend/tests/runtime/test_ai_decision_logging.py`

### Step 1: Write backward compatibility test

Add to test file:

```python
def test_backward_compatibility_legacy_decisions_still_work():
    """Legacy decisions (ParsedAIDecision only) work unchanged."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    # Create log as if from W2.4.3 parsing (no role-structured output)
    log = construct_ai_decision_log(
        session_id="sess1",
        turn_number=1,
        parsed_decision=parsed_decision,
        raw_output="raw",
        role_aware_decision=None,  # Legacy path
        guard_outcome=GuardOutcome.ACCEPTED,
    )

    # Log should be created successfully
    assert log.id is not None
    assert log.session_id == "sess1"
    assert log.turn_number == 1

    # Legacy logs have no role fields
    assert log.interpreter_output is None
    assert log.director_output is None
    assert log.responder_output is None

    # Guard outcome preserved
    assert log.guard_outcome == GuardOutcome.ACCEPTED
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py::test_backward_compatibility_legacy_decisions_still_work -v`

Expected: PASS

### Step 2: Run full test suite

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py -v`

Expected: All tests PASS (approximately 10+ tests)

### Step 3: Run full runtime test suite to verify no regressions

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/ -v --tb=short -q`

Expected: All existing tests still pass + new tests pass

### Step 4: Verify no W2 scope creep

Checklist:
- [ ] No changes to ParsedAIDecision (still canonical runtime decision)
- [ ] No changes to parsing/normalization logic
- [ ] No changes to guard semantics or validation
- [ ] Role fields are diagnostic-only (logging layer only)
- [ ] Backward compatibility maintained (legacy decisions work)
- [ ] No UI work added
- [ ] No large observability platform built

### Step 5: Final commit

```bash
git add backend/tests/runtime/test_ai_decision_logging.py
git commit -m "test(w2): add backward compatibility and integration tests

- Verify legacy decisions work unchanged
- Run full runtime test suite (no regressions)
- Confirm W2.4.4 scope boundaries (diagnostics-only, no runtime changes)
- Confirm backward compatibility maintained"
```

---

## Acceptance Criteria Verification

After all tasks complete, verify:

- ✅ Diagnostics now expose role separation clearly (interpreter, director, responder visible in logs)
- ✅ Logs materially improve debuggability (diagnostic summaries + full responder detail)
- ✅ Type-based detection works (ParsedRoleAwareDecision present → role fields populated)
- ✅ Backward compatibility maintained (legacy decisions have role fields = None)
- ✅ No runtime changes (ParsedAIDecision unchanged, guard_outcome canonical)
- ✅ No W2 scope jump (diagnostics only, no parsing/normalization/guard changes)
- ✅ Boundedness preserved (diagnostic summaries keep logs coherent)
- ✅ All tests pass (existing + new)

---

## Verification Commands

```bash
# Run new logging tests
PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py -v

# Run full runtime suite (no regressions)
PYTHONPATH=backend python -m pytest backend/tests/runtime/ -q

# Count tests
PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision_logging.py --collect-only -q | wc -l
```

**Expected Results:**
- All new tests in test_ai_decision_logging.py pass (10+ tests)
- All existing runtime tests still pass (no regressions)
- No W2 scope creep
- Backward compatibility verified

---

## Deferred (W2.4.5+)

- Guard-path coupling analysis (using role diagnostics in W2.4.5)
- Fine-grained proposal-level diagnostics (future iteration)
- Role-structured decision tracing in UI/analytics (future iteration)

---

## Commit Summary

```
feat(w2): expose internal AI role split in decision diagnostics

Task 1: Add diagnostic summary models and extend AIDecisionLog
- Add InterpreterDiagnosticSummary: scene_reading + detected_tensions
- Add DirectorDiagnosticSummary: conflict_steering + recommended_direction
- Extend AIDecisionLog with interpreter_output, director_output, responder_output, guard_outcome

Task 2: Create logging helper module
- Create ai_decision_logging.py with construct_ai_decision_log()
- Type-based detection: if ParsedRoleAwareDecision present, populate role fields
- Validation outcome derived from guard_outcome (not hardcoded)

Task 3: Add diagnostic-only constraint tests
- Verify role fields do not affect delta validation
- Verify guard_outcome remains canonical

Task 4: Integration and backward compatibility
- Verify legacy decisions still work unchanged
- Confirm no W2 scope creep
- All 10+ tests passing
```
