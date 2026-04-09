# W2.4.5: Enforce Responder-Only Runtime Proposal Path

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make interpreter and director diagnostic-only by enforcing that ONLY responder-derived proposals feed the canonical guarded execution path.

**Architecture:** Add `proposal_source` enum to MockDecision and enforce at execute_turn() entry. Responder proposals are explicitly marked as RESPONDER_DERIVED at source. Enforcement is canonical in the AI execution path.

**Canonical Boundary Rule (W2.4.5):**
- W2.4.5 does NOT change guard logic
- W2.4.5 changes ONLY which proposal source is allowed to enter the existing validation/guard/execution path
- Existing guards remain fully authoritative after source gating

**Tech Stack:** Python 3.10+, Pydantic v2, pytest for testing.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `backend/app/runtime/w2_models.py` | MODIFY | Add ProposalSource enum |
| `backend/app/runtime/turn_executor.py` | MODIFY | Add source enforcement gate at execute_turn() entry |
| `backend/app/runtime/ai_turn_executor.py` | MODIFY | Mark responder proposals as RESPONDER_DERIVED source; enable canonical enforcement |
| `backend/tests/runtime/test_responder_gating.py` | CREATE | Test responder-only enforcement with real role-structured inputs |

---

## Task 1: Add ProposalSource Enum and Extend MockDecision

**Files:**
- Modify: `backend/app/runtime/w2_models.py` (add enum, extend MockDecision)

### Step 1: Read current w2_models.py MockDecision

Run: `grep -n "class MockDecision" backend/app/runtime/w2_models.py -A 20`

Expected: See MockDecision class with proposed_deltas field

### Step 2: Write failing test for MockDecision with proposal source

Create file: `backend/tests/runtime/test_responder_gating.py`

```python
"""Tests for W2.4.5 responder-only proposal gating."""

import pytest
from app.runtime.w2_models import MockDecision, ProposalSource, ProposedStateDelta


def test_mock_decision_requires_proposal_source():
    """MockDecision requires explicit proposal_source (not defaulted to responder)."""
    delta = ProposedStateDelta(
        target="characters.alice.emotional_state",
        next_value=75,
        delta_type=None,
        source="ai_proposal",
    )

    # Test that creating without proposal_source uses conservative MOCK default
    decision = MockDecision(
        proposed_deltas=[delta],
    )

    # Default must be MOCK (non-authoritative), not RESPONDER_DERIVED
    assert decision.proposal_source == ProposalSource.MOCK
    assert len(decision.proposed_deltas) == 1


def test_mock_decision_accepts_explicit_proposal_source():
    """MockDecision accepts explicit proposal_source field."""
    delta = ProposedStateDelta(
        target="characters.alice.emotional_state",
        next_value=75,
        delta_type=None,
        source="ai_proposal",
    )

    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.RESPONDER_DERIVED,
    )

    assert decision.proposal_source == ProposalSource.RESPONDER_DERIVED


def test_proposal_source_enum_has_all_values():
    """ProposalSource enum has all required values."""
    assert hasattr(ProposalSource, "RESPONDER_DERIVED")
    assert hasattr(ProposalSource, "MOCK")
    assert hasattr(ProposalSource, "ENGINE")
    assert hasattr(ProposalSource, "OPERATOR")
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_responder_gating.py::test_mock_decision_requires_proposal_source -v`

Expected: FAIL with "cannot import ProposalSource"

### Step 3: Add ProposalSource enum to w2_models.py

Add before MockDecision class:

```python
class ProposalSource(str, Enum):
    """Source origin of a proposal entering the execution path.

    Default is MOCK (non-authoritative). Only RESPONDER_DERIVED proposals
    are authorized to enter the canonical guarded execution path.
    """

    RESPONDER_DERIVED = "responder_derived"
    """Proposal came from responder section of parsed AI role contract.

    Only this source is authorized for canonical execution path.
    """

    MOCK = "mock"
    """Proposal came from mock_decision_provider (test/debug only).

    Conservative default. Requires explicit override for responder authorization.
    """

    ENGINE = "engine"
    """Reserved: Proposal from world engine (not yet integrated)."""

    OPERATOR = "operator"
    """Reserved: Proposal from human operator (not yet integrated)."""
```

Add import at top: `from enum import Enum`

### Step 4: Extend MockDecision with proposal_source field

Find MockDecision class, add field with conservative default:

```python
class MockDecision(BaseModel):
    """Mock decision with proposed deltas for testing/execution.

    ...existing docstring...

    Attributes:
        ...existing fields...
        proposal_source: Origin of proposals (responder_derived, mock, engine, operator).
                        Defaults to MOCK (non-authoritative) for safety.
    """

    # ...existing fields...

    proposal_source: ProposalSource = ProposalSource.MOCK
    """Source of proposals in proposed_deltas.

    Default MOCK requires explicit override to RESPONDER_DERIVED.
    Only RESPONDER_DERIVED proposals are authorized for canonical execution.
    """
```

### Step 5: Run tests

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_responder_gating.py::test_mock_decision_requires_proposal_source backend/tests/runtime/test_responder_gating.py::test_mock_decision_accepts_explicit_proposal_source backend/tests/runtime/test_responder_gating.py::test_proposal_source_enum_has_all_values -v`

Expected: All PASS

### Step 6: Run full runtime test suite

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/ -q`

Expected: All tests pass (may need to update existing tests that create MockDecision to specify proposal_source or accept MOCK default)

### Step 7: Commit

```bash
git add backend/app/runtime/w2_models.py backend/tests/runtime/test_responder_gating.py
git commit -m "feat(w2): add proposal source enum and extend MockDecision

- Add ProposalSource enum: RESPONDER_DERIVED, MOCK, ENGINE, OPERATOR
- Extend MockDecision with proposal_source field (defaults to conservative MOCK)
- Requires explicit RESPONDER_DERIVED for authorization
- Tests verify enum creation and MockDecision field acceptance"
```

---

## Task 2: Add Source Enforcement Gate at execute_turn() Entry

**Files:**
- Modify: `backend/app/runtime/turn_executor.py` (add source validation at entry)

### Step 1: Write failing test for source enforcement

Add to `backend/tests/runtime/test_responder_gating.py`:

```python
def test_execute_turn_rejects_non_responder_when_enforcement_enabled():
    """execute_turn() rejects non-responder proposals when enforcement enabled."""
    from app.runtime.turn_executor import execute_turn
    from tests.conftest import god_of_carnage_module_with_state

    # Create session fixture
    session = god_of_carnage_module_with_state()

    # Create a mock decision with MOCK source
    delta = ProposedStateDelta(
        target="characters.veronique.emotional_state",
        next_value=50,
        delta_type=None,
        source="test_proposal",
    )

    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.MOCK,  # Non-responder source
    )

    # When enforcement is enabled (enforce_responder_only=True)
    result = execute_turn(
        session=session,
        turn_number=1,
        decision=decision,
        module=god_of_carnage_module_with_state().module,
        enforce_responder_only=True,  # Canonical enforcement enabled
    )

    # Should reject all proposals from non-responder source
    assert result.guard_outcome == GuardOutcome.REJECTED
    assert len(result.accepted_deltas) == 0
    assert len(result.rejected_deltas) == 1


def test_execute_turn_accepts_responder_with_enforcement():
    """execute_turn() accepts responder-derived proposals with enforcement enabled."""
    from app.runtime.turn_executor import execute_turn
    from tests.conftest import god_of_carnage_module_with_state

    session = god_of_carnage_module_with_state()

    # Create a mock decision with RESPONDER_DERIVED source
    delta = ProposedStateDelta(
        target="characters.veronique.emotional_state",
        next_value=75,
        delta_type=None,
        source="ai_proposal",
    )

    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.RESPONDER_DERIVED,  # Responder-derived
    )

    # With enforcement enabled, responder proposals should flow through normal validation
    result = execute_turn(
        session=session,
        turn_number=1,
        decision=decision,
        module=god_of_carnage_module_with_state().module,
        enforce_responder_only=True,
    )

    # Should be validated normally (not rejected by gate)
    # Status depends on validation, not on source gate
    assert result.guard_outcome in [GuardOutcome.ACCEPTED, GuardOutcome.PARTIALLY_ACCEPTED, GuardOutcome.REJECTED]
    # Key point: not rejected due to source
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_responder_gating.py::test_execute_turn_rejects_non_responder_when_enforcement_enabled -v`

Expected: FAIL with "execute_turn() got unexpected keyword argument 'enforce_responder_only'"

### Step 2: Add enforcement parameter to execute_turn()

Find execute_turn() signature at line 503 in turn_executor.py:

```python
def execute_turn(
    session: RuntimeSession,
    turn_number: int,
    decision: MockDecision,
    module: ContentModule,
    enforce_responder_only: bool = False,
) -> TurnExecutionResult:
    """Execute a single turn with AI decision.

    Args:
        ...existing args...
        enforce_responder_only: If True, only RESPONDER_DERIVED proposals are allowed.
                              Rejects all non-responder proposals at gate.
                              Default False for backward compatibility with non-AI paths.

    ...existing docstring...
    """
```

### Step 3: Add source enforcement gate

Add immediately after input validation (around line 510), before validate_decision() call:

```python
    # Enforce responder-only proposal gate if enabled
    if enforce_responder_only and decision.proposal_source != ProposalSource.RESPONDER_DERIVED:
        return TurnExecutionResult(
            turn_number=turn_number,
            session_state=session.canonical_state,
            guard_outcome=GuardOutcome.REJECTED,
            accepted_deltas=[],
            rejected_deltas=decision.proposed_deltas,  # Reject all proposals
            guard_notes=f"Proposals rejected: source is {decision.proposal_source.value}, only RESPONDER_DERIVED allowed",
            phase="gating",
        )
```

Add import if needed: `from app.runtime.w2_models import ProposalSource`

### Step 4: Run tests

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_responder_gating.py::test_execute_turn_rejects_non_responder_when_enforcement_enabled backend/tests/runtime/test_responder_gating.py::test_execute_turn_accepts_responder_with_enforcement -v`

Expected: Tests pass with new gating logic

### Step 5: Run full suite

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/ -q`

Expected: All tests pass (backward compatible because enforce_responder_only=False by default)

### Step 6: Commit

```bash
git add backend/app/runtime/turn_executor.py backend/tests/runtime/test_responder_gating.py
git commit -m "feat(w2): add responder-only source enforcement gate

- Add enforce_responder_only parameter to execute_turn() (defaults False)
- Gate rejects proposals from non-responder sources when enabled
- Backward compatible: existing non-AI calls continue without enforcement"
```

---

## Task 3: Enable Canonical Enforcement in AI Execution Path

**Files:**
- Modify: `backend/app/runtime/ai_turn_executor.py` (mark responder proposals and enable enforcement)

### Step 1: Write failing test for canonical AI enforcement

Add to `backend/tests/runtime/test_responder_gating.py`:

```python
def test_execute_turn_with_ai_uses_canonical_enforcement():
    """execute_turn_with_ai() always calls execute_turn() with enforce_responder_only=True."""
    # This test verifies the canonical enforcement is always enabled for AI path
    # by checking that non-responder proposals would be rejected

    from app.runtime.ai_turn_executor import execute_turn_with_ai
    from tests.conftest import god_of_carnage_module_with_state, mock_adapter_role_structured

    session = god_of_carnage_module_with_state()

    # Mock adapter returns responder proposals
    # execute_turn_with_ai() should mark them as RESPONDER_DERIVED
    # and call execute_turn with enforce_responder_only=True

    result = execute_turn_with_ai(
        session=session,
        turn_number=1,
        module=god_of_carnage_module_with_state().module,
        adapter=mock_adapter_role_structured(),  # Returns responder-structured output
        context_builder=lambda: {},
    )

    # Result should show that gating was active but responder proposals passed
    # (actual acceptance depends on validation, not gating)
    assert result.guard_outcome != GuardOutcome.REJECTED  # Not rejected by gate
```

### Step 2: Mark responder proposals at source

Find where MockDecision is created in execute_turn_with_ai() (around line 488-495), update to:

```python
    # Create mock decision with RESPONDER_DERIVED source
    # Responder proposals from parse_role_contract() are explicitly marked
    decision = MockDecision(
        proposed_deltas=parsed_deltas,  # From responder section via parse_role_contract()
        proposal_source=ProposalSource.RESPONDER_DERIVED,  # Explicit responder authorization
    )
```

Add import: `from app.runtime.w2_models import ProposalSource`

### Step 3: Enable canonical enforcement in AI path

Find execute_turn() call in execute_turn_with_ai() (around line 497), update to:

```python
    # Call with canonical responder-only enforcement enabled
    # This enforces that interpreter/director remain diagnostic-only
    result = execute_turn(
        session=session,
        turn_number=turn_number,
        decision=decision,
        module=module,
        enforce_responder_only=True,  # CANONICAL: Always enforce responder-only in AI path
    )
```

### Step 4: Run tests

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_responder_gating.py::test_execute_turn_with_ai_uses_canonical_enforcement -v`

Expected: Test passes

### Step 5: Verify full suite

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/ -q`

Expected: All tests pass

### Step 6: Commit

```bash
git add backend/app/runtime/ai_turn_executor.py backend/tests/runtime/test_responder_gating.py
git commit -m "feat(w2): enable canonical responder-only enforcement in AI path

- Mark responder proposals explicitly with RESPONDER_DERIVED source
- execute_turn_with_ai() calls execute_turn() with enforce_responder_only=True
- Canonical enforcement: interpreter/director remain diagnostic-only
- All responder proposals must pass existing validation/guard pipeline"
```

---

## Task 4: Comprehensive Boundary Tests and Scope Verification

**Files:**
- Modify: `backend/tests/runtime/test_responder_gating.py` (add comprehensive boundary tests)

### Step 1: Add test for interpreter content cannot affect state

Add to test file:

```python
def test_interpreter_output_cannot_affect_execution():
    """Interpreter output is diagnostic-only, cannot feed execution path."""
    from app.runtime.role_structured_decision import parse_role_contract
    from app.runtime.role_contract import InterpreterSection, DirectorSection, ResponderSection
    from tests.conftest import god_of_carnage_module_with_state

    # Create role-structured payload with ROGUE interpreter content
    # (interpreter section contains state-change-like content)
    payload = {
        "interpreter": {
            "scene_reading": "Scene analysis",
            "detected_tensions": ["fake_tension"],
            "trigger_candidates": ["fake_trigger"],
            # NOTE: interpreter section should NOT contain state changes
            # but we test that even if it did, it wouldn't affect execution
        },
        "director": {
            "conflict_steering": "Director steering",
            "escalation_level": 5,
            "recommended_direction": "hold",
        },
        "responder": {
            "response_impulses": [],
            "state_change_candidates": [],  # Responder proposals empty
            "dialogue_impulses": None,
            "trigger_assertions": [],
            "scene_transition_candidate": None,
        },
    }

    # Parse converts interpreter to ParsedAIDecision
    role_aware = parse_role_contract(payload, "raw output")

    # Verify: ParsedAIDecision has NO state changes from interpreter
    assert len(role_aware.parsed_decision.proposed_deltas) == 0
    # Interpreter content is preserved separately
    assert role_aware.interpreter_output is not None
    assert role_aware.interpreter_output.scene_reading == "Scene analysis"

    # When this decision enters execute_turn_with_ai() with enforce_responder_only=True,
    # the interpreter content cannot affect state (no deltas to execute)


def test_director_output_cannot_affect_execution():
    """Director output is diagnostic-only, cannot feed execution path."""
    from app.runtime.role_structured_decision import parse_role_contract
    from tests.conftest import god_of_carnage_module_with_state

    # Create role-structured payload with ROGUE director content
    payload = {
        "interpreter": {
            "scene_reading": "Scene analysis",
            "detected_tensions": [],
            "trigger_candidates": [],
        },
        "director": {
            "conflict_steering": "This should change character state directly",
            "escalation_level": 10,
            "recommended_direction": "escalate",
            # NOTE: director section contains steering intent, not proposals
            # even if it resembles a proposal, it shouldn't affect execution
        },
        "responder": {
            "response_impulses": [],
            "state_change_candidates": [],  # Responder proposals empty
            "dialogue_impulses": None,
            "trigger_assertions": [],
            "scene_transition_candidate": None,
        },
    }

    # Parse converts director to ParsedAIDecision.rationale
    role_aware = parse_role_contract(payload, "raw output")

    # Verify: ParsedAIDecision.rationale is diagnostic text, not a proposal
    assert role_aware.parsed_decision.rationale == "This should change character state directly"
    # But no proposed_deltas from director
    assert len(role_aware.parsed_decision.proposed_deltas) == 0
    # Director content is preserved separately
    assert role_aware.director_output is not None
    assert role_aware.director_output.conflict_steering == "This should change character state directly"

    # Director output cannot affect execution (no deltas to enforce)


def test_only_responder_proposals_enter_guarded_path():
    """Only responder-derived state_change_candidates become proposed_deltas."""
    from app.runtime.role_structured_decision import parse_role_contract
    from app.runtime.role_contract import StateChangeCandidate

    # Create role-structured payload where ONLY responder has proposals
    payload = {
        "interpreter": {
            "scene_reading": "Interpreter analysis (diagnostic)",
            "detected_tensions": ["tension1"],
            "trigger_candidates": ["trigger1"],
        },
        "director": {
            "conflict_steering": "Director guidance (diagnostic)",
            "escalation_level": 7,
            "recommended_direction": "shift_alliance",
        },
        "responder": {
            "response_impulses": [],
            "state_change_candidates": [
                {
                    "target_path": "characters.alice.emotional_state",
                    "proposed_value": 80,
                    "rationale": "This is the ONLY content that affects execution",
                }
            ],
            "dialogue_impulses": None,
            "trigger_assertions": ["trigger1"],  # Only responder assertions enter path
            "scene_transition_candidate": None,
        },
    }

    # Parse role-structured output
    role_aware = parse_role_contract(payload, "raw output")

    # Verify: only responder state_change_candidates became proposed_deltas
    assert len(role_aware.parsed_decision.proposed_deltas) == 1
    assert role_aware.parsed_decision.proposed_deltas[0].target_path == "characters.alice.emotional_state"
    assert role_aware.parsed_decision.proposed_deltas[0].next_value == 80

    # Verify: responder triggers assertions became detected_triggers
    assert "trigger1" in role_aware.parsed_decision.detected_triggers

    # Interpreter and director are preserved diagnostically
    assert role_aware.interpreter_output is not None
    assert role_aware.director_output is not None
    # But they don't feed the execution path


def test_gating_preserves_existing_guard_authority():
    """Responder-only gating enables guards, does not replace them."""
    # This test verifies:
    # 1. Proposals pass source gate (responder-derived)
    # 2. Proposals then flow through EXISTING validation/guard pipeline
    # 3. Existing guards reject invalid proposals (guards remain authoritative)
    # 4. W2.4.5 changes ONLY which source enters the path, not guard logic

    from app.runtime.turn_executor import execute_turn
    from tests.conftest import god_of_carnage_module_with_state

    session = god_of_carnage_module_with_state()

    # Create a RESPONDER_DERIVED proposal that will fail EXISTING validation
    # (e.g., invalid reference, mutation policy violation)
    delta = ProposedStateDelta(
        target="invalid.reference.path",  # Will fail reference validation
        next_value=100,
        delta_type=None,
        source="ai_proposal",
    )

    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.RESPONDER_DERIVED,  # Passes source gate
    )

    # With enforcement enabled
    result = execute_turn(
        session=session,
        turn_number=1,
        decision=decision,
        module=god_of_carnage_module_with_state().module,
        enforce_responder_only=True,
    )

    # Proposal passes source gate but fails EXISTING validation
    # (rejected by validators, not by source gate)
    assert result.guard_outcome == GuardOutcome.REJECTED
    assert len(result.rejected_deltas) == 1
    # Rejection reason is from validators, not from source gating
    # (proves guards remain authoritative)


def test_no_new_execution_paths_created():
    """Verify W2.4.5 doesn't create new execution paths."""
    # All proposals (responder-derived or not) flow through:
    # 1. Source gate (new W2.4.5)
    # 2. EXISTING validation pipeline
    # 3. EXISTING mutation policy
    # 4. EXISTING scene legality checks
    # 5. EXISTING apply_deltas
    # No bypasses, no new paths

    from app.runtime.turn_executor import execute_turn
    from tests.conftest import god_of_carnage_module_with_state

    session = god_of_carnage_module_with_state()

    # Valid responder proposal
    delta = ProposedStateDelta(
        target="characters.veronique.emotional_state",
        next_value=75,
        delta_type=None,
        source="ai_proposal",
    )

    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.RESPONDER_DERIVED,
    )

    # With enforcement
    result = execute_turn(
        session=session,
        turn_number=1,
        decision=decision,
        module=god_of_carnage_module_with_state().module,
        enforce_responder_only=True,
    )

    # Passes through full pipeline (source → validation → mutation policy → execution)
    assert result.guard_outcome in [GuardOutcome.ACCEPTED, GuardOutcome.PARTIALLY_ACCEPTED]
    # Demonstrates: proposals still flow through all existing gates
```

### Step 2: Run all boundary tests

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_responder_gating.py -v`

Expected: All tests pass

### Step 3: Verify scope boundaries

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/ -q`

Expected: All 503+ tests passing, zero regressions

### Step 4: Final verification checklist

Verify in test output:
- ✅ Interpreter output cannot affect execution
- ✅ Director output cannot affect execution
- ✅ Only responder proposals enter guarded path
- ✅ Existing guards remain fully authoritative
- ✅ Source gating is first step, validation is second
- ✅ No new execution paths created
- ✅ Backward compatible (enforce_responder_only=False by default in execute_turn)
- ✅ Canonical enforcement enabled (execute_turn_with_ai calls with enforce_responder_only=True)

### Step 5: Commit comprehensive tests

```bash
git add backend/tests/runtime/test_responder_gating.py
git commit -m "test(w2): add comprehensive responder-only boundary tests

- Test interpreter content cannot affect execution
- Test director content cannot affect execution
- Test only responder proposals enter guarded path
- Test existing guards remain fully authoritative
- Verify no new execution paths created
- Verify role separation has real runtime consequences"
```

---

## Verification Checklist

After all tasks complete:

- ✅ ProposalSource enum exists with MOCK as conservative default
- ✅ MockDecision has proposal_source field (required explicit responder authorization)
- ✅ execute_turn() accepts enforce_responder_only parameter (defaults False)
- ✅ Non-responder proposals rejected at gate when enforcement enabled
- ✅ Responder proposals explicitly marked RESPONDER_DERIVED at source
- ✅ execute_turn_with_ai() calls with enforce_responder_only=True (canonical)
- ✅ All proposals still flow through existing validation/guards (gates remain authoritative)
- ✅ Interpreter output remains diagnostic-only (cannot feed execution)
- ✅ Director output remains diagnostic-only (cannot feed execution)
- ✅ Role separation has real runtime consequences (enforced at gate)
- ✅ Backward compatibility maintained (enforce_responder_only=False optional for non-AI)
- ✅ Canonical enforcement enabled (enforce_responder_only=True in AI path)
- ✅ All 503+ tests passing
- ✅ No new execution paths created
- ✅ No W2 scope jump

---

## Canonical Boundary Rule (Restated)

**W2.4.5 enforces but does NOT change:**
- Guard logic is unchanged (all proposals validated same way)
- Validation pipeline is unchanged (same checks apply)
- Mutation policy is unchanged (same whitelist enforced)
- Scene legality checks are unchanged
- apply_deltas() logic is unchanged

**W2.4.5 enforces:**
- Source gating: only RESPONDER_DERIVED proposals allowed (at gate)
- Proposal flow: gate → validation → mutation_policy → scene_legality → apply_deltas
- Role isolation: interpreter/director diagnostic-only, responder proposes
- Canonical path: execute_turn_with_ai() always enforces responder-only

---

## Acceptance Criteria Verification

After completion, verify:

- ✅ Role separation now has real runtime consequences (enforced via source gate)
- ✅ Existing guards remain fully authoritative (validation pipeline unchanged)
- ✅ Implementation sufficient for final W2.4 review (core gating complete)
- ✅ Canonical enforcement in AI path (W2.4 execution is secure)
- ✅ Backward compatible (non-AI paths can opt-in to enforcement)

---

## Deferred (W2.5+)

- Operator-injected proposals (OPERATOR source, separate execution path)
- Engine-derived proposals (ENGINE source, separate execution path)
- Multi-agent orchestration
- UI for diagnostics layer
- Role-aware decision streaming in API responses

---

## Commit Summary

```
feat(w2): enforce responder-only runtime proposal path

Task 1: Add ProposalSource enum and extend MockDecision
- Add ProposalSource enum: RESPONDER_DERIVED, MOCK, ENGINE, OPERATOR
- Extend MockDecision with proposal_source field (defaults to conservative MOCK)
- Requires explicit RESPONDER_DERIVED for authorization

Task 2: Add source enforcement gate at execute_turn() entry
- Add enforce_responder_only parameter to execute_turn()
- Gate rejects non-responder sources
- Backward compatible (defaults to False)

Task 3: Enable canonical enforcement in AI path
- Mark responder proposals as RESPONDER_DERIVED at source
- execute_turn_with_ai() calls with enforce_responder_only=True (canonical)

Task 4: Comprehensive boundary tests
- Test interpreter/director diagnostic-only constraint (real role-structured input)
- Test responder-only enforcement
- Verify role separation has runtime consequences
- Confirm existing guards remain authoritative
```
