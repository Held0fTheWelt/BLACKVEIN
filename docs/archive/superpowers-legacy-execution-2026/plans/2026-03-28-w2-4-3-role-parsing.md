# W2.4.3: Parse and Normalize Role-Structured AI Output

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate role-structured AI output (AIRoleContract) into the canonical parse/normalize flow, preserving role sections for diagnostics while maintaining ParsedAIDecision as the sole runtime decision object.

**Architecture:** Strict format detection (all three role keys required) with delegation to a focused role-parsing module. Both legacy and role-structured paths normalize into ParsedAIDecision. Role sections preserved in ParsedRoleAwareDecision for diagnostics only.

**Tech Stack:** Python 3.10+, Pydantic v2, existing runtime structures.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `backend/app/runtime/ai_decision.py` | MODIFY | Add format detection and ParseResult extension |
| `backend/app/runtime/role_structured_decision.py` | CREATE | Role parsing and normalization module |
| `backend/tests/runtime/test_role_structured_decision.py` | CREATE | Role parsing tests |

---

## Task 1: Create ParsedRoleAwareDecision and Role Module Infrastructure

**Files:**
- Create: `backend/app/runtime/role_structured_decision.py`
- Modify: `backend/app/runtime/ai_decision.py` (extend ParseResult)

### Step 1: Write failing test for ParsedRoleAwareDecision

Create test file: `backend/tests/runtime/test_role_structured_decision.py`

```python
"""Tests for W2.4.3 role-structured parsing and normalization."""

import pytest
from app.runtime.ai_decision import ParsedAIDecision
from app.runtime.role_structured_decision import ParsedRoleAwareDecision
from app.runtime.role_contract import (
    InterpreterSection,
    DirectorSection,
    ResponderSection,
)


def test_parsed_role_aware_decision_creation():
    """ParsedRoleAwareDecision wraps ParsedAIDecision with role sections."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    interpreter = InterpreterSection(
        scene_reading="Reading",
        detected_tensions=[],
        trigger_candidates=[],
    )
    director = DirectorSection(
        conflict_steering="Steering",
        escalation_level=5,
        recommended_direction="hold",
    )
    responder = ResponderSection()

    role_aware = ParsedRoleAwareDecision(
        parsed_decision=parsed_decision,
        interpreter=interpreter,
        director=director,
        responder=responder,
    )

    assert role_aware.parsed_decision == parsed_decision
    assert role_aware.interpreter == interpreter
    assert role_aware.director == director
    assert role_aware.responder == responder
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_role_structured_decision.py::test_parsed_role_aware_decision_creation -v`

Expected: FAIL with "cannot import name 'ParsedRoleAwareDecision'"

### Step 2: Create role_structured_decision.py module

Create file: `backend/app/runtime/role_structured_decision.py`

```python
"""W2.4.3 — Parse and normalize role-structured AI output.

Handles conversion of AIRoleContract into canonical ParsedAIDecision
while preserving role sections for diagnostics.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.runtime.ai_decision import ParsedAIDecision
from app.runtime.ai_output import DialogueImpulse, ProposedDelta
from app.runtime.role_contract import (
    DirectorSection,
    InterpreterSection,
    ResponderSection,
    ResponseImpulse,
    StateChangeCandidate,
)


class ParsedRoleAwareDecision(BaseModel):
    """Canonical parsed decision with role sections preserved for diagnostics.

    This is a composition structure that wraps the core runtime decision
    with diagnostic role sections. Only ParsedAIDecision feeds runtime execution.

    Attributes:
        parsed_decision: Core runtime decision object (sole runtime authority)
        interpreter: Preserved interpreter section (diagnostic only)
        director: Preserved director section (diagnostic only)
        responder: Preserved responder section (diagnostic only)
    """

    parsed_decision: ParsedAIDecision
    interpreter: InterpreterSection
    director: DirectorSection
    responder: ResponderSection


def parse_role_contract(
    payload: dict[str, Any],
    raw_output: str,
) -> ParsedRoleAwareDecision:
    """Parse and normalize AIRoleContract into ParsedRoleAwareDecision.

    Converts role-structured output into canonical ParsedAIDecision while
    preserving all role sections for diagnostics.

    Args:
        payload: Structured payload dict with interpreter/director/responder keys
        raw_output: Original raw output text

    Returns:
        ParsedRoleAwareDecision with normalized ParsedAIDecision and role sections

    Raises:
        ValueError: If required role sections are missing or malformed
    """
    # Import here to avoid circular imports
    from app.runtime.role_contract import AIRoleContract

    # Validate payload is AIRoleContract-shaped
    try:
        role_contract = AIRoleContract(**payload)
    except Exception as e:
        raise ValueError(f"Failed to parse AIRoleContract: {e}") from None

    # Extract role sections
    interpreter = role_contract.interpreter
    director = role_contract.director
    responder = role_contract.responder

    # Normalize to ParsedAIDecision (canonical runtime decision)
    parsed_decision = _normalize_role_contract(
        interpreter, director, responder, raw_output
    )

    # Return composition with role sections preserved
    return ParsedRoleAwareDecision(
        parsed_decision=parsed_decision,
        interpreter=interpreter,
        director=director,
        responder=responder,
    )


def _normalize_role_contract(
    interpreter: InterpreterSection,
    director: DirectorSection,
    responder: ResponderSection,
    raw_output: str,
) -> ParsedAIDecision:
    """Normalize role sections into canonical ParsedAIDecision.

    Mapping rules (from spec section 3):
    - interpreter.scene_reading → scene_interpretation
    - director.conflict_steering → rationale
    - responder.state_change_candidates → proposed_deltas
    - responder.trigger_assertions → detected_triggers
    - responder.scene_transition_candidate → proposed_scene_id
    - responder.response_impulses (dialogue_urge only) → dialogue_impulses
    """
    # Map interpreter
    scene_interpretation = interpreter.scene_reading.strip()

    # Map director
    rationale = director.conflict_steering.strip()

    # Map responder state changes
    proposed_deltas = [
        ProposedDelta(
            target_path=candidate.target_path,
            next_value=candidate.proposed_value,
            rationale=candidate.rationale,
            delta_type=None,
        )
        for candidate in responder.state_change_candidates
    ]

    # Map responder triggers
    detected_triggers = responder.trigger_assertions

    # Map responder scene transition
    proposed_scene_id = responder.scene_transition_candidate

    # Map responder dialogue impulses (dialogue_urge only)
    dialogue_impulses = [
        DialogueImpulse(
            character_id=impulse.character_id,
            impulse_text=impulse.rationale,  # ResponseImpulse.rationale → DialogueImpulse.impulse_text
            intensity=impulse.intensity / 10.0 if impulse.intensity else 0.0,  # Scale 0-10 → 0.0-1.0
        )
        for impulse in responder.response_impulses
        if impulse.impulse_type == "dialogue_urge"
    ]

    return ParsedAIDecision(
        scene_interpretation=scene_interpretation,
        detected_triggers=detected_triggers,
        proposed_deltas=proposed_deltas,
        proposed_scene_id=proposed_scene_id,
        rationale=rationale,
        dialogue_impulses=dialogue_impulses,
        raw_output=raw_output,
        parsed_source="role_structured_payload",
    )
```

### Step 3: Extend ParseResult in ai_decision.py

In `backend/app/runtime/ai_decision.py`, update the ParseResult class:

```python
class ParseResult(BaseModel):
    """Result of parse_adapter_response() — inspectable outcome.

    Attributes:
        success: True if parse+normalize+prevalidate all passed
        decision: ParsedAIDecision if successful, None otherwise
        role_aware_decision: ParsedRoleAwareDecision (optional, only if role-structured input)
        errors: List of errors encountered (empty if successful)
        raw_output: Original adapter output (always preserved)
    """

    success: bool
    decision: ParsedAIDecision | None = None
    role_aware_decision: Any | None = None  # ParsedRoleAwareDecision from W2.4.3
    errors: list[str] = []
    raw_output: str
```

### Step 4: Run failing test

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_role_structured_decision.py::test_parsed_role_aware_decision_creation -v`

Expected: PASS (module now created)

### Step 5: Commit

```bash
git add backend/app/runtime/role_structured_decision.py backend/app/runtime/ai_decision.py backend/tests/runtime/test_role_structured_decision.py
git commit -m "feat(w2): create role-structured parsing module and ParsedRoleAwareDecision

- Add ParsedRoleAwareDecision: composition of ParsedAIDecision + role sections
- Create role_structured_decision.py with parse_role_contract() function
- Implement normalization mapping (interpreter/director/responder → canonical decision)
- Extend ParseResult with role_aware_decision field
- Add test for ParsedRoleAwareDecision creation"
```

---

## Task 2: Implement Format Detection and Parsing Flow

**Files:**
- Modify: `backend/app/runtime/ai_decision.py`

### Step 1: Write failing test for format detection

Add to `backend/tests/runtime/test_role_structured_decision.py`:

```python
def test_is_role_structured_payload_detects_role_format():
    """Format detection returns True only when all three roles present."""
    from app.runtime.role_structured_decision import _is_role_structured_payload

    # Valid role-structured payload
    valid_payload = {
        "interpreter": {
            "scene_reading": "Reading",
            "detected_tensions": [],
            "trigger_candidates": [],
        },
        "director": {
            "conflict_steering": "Steering",
            "escalation_level": 5,
            "recommended_direction": "hold",
        },
        "responder": {
            "response_impulses": [],
            "state_change_candidates": [],
            "trigger_assertions": [],
        },
    }

    assert _is_role_structured_payload(valid_payload) is True


def test_is_role_structured_payload_rejects_legacy_format():
    """Format detection returns False for legacy format (no all three roles)."""
    from app.runtime.role_structured_decision import _is_role_structured_payload

    # Legacy format (no roles)
    legacy_payload = {
        "scene_interpretation": "Scene",
        "detected_triggers": [],
        "proposed_deltas": [],
    }

    assert _is_role_structured_payload(legacy_payload) is False


def test_is_role_structured_payload_rejects_incomplete_roles():
    """Format detection returns False if not all three roles present."""
    from app.runtime.role_structured_decision import _is_role_structured_payload

    # Only interpreter and director, no responder
    incomplete = {
        "interpreter": {"scene_reading": "", "detected_tensions": [], "trigger_candidates": []},
        "director": {"conflict_steering": "", "escalation_level": 0, "recommended_direction": "hold"},
    }

    assert _is_role_structured_payload(incomplete) is False
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_role_structured_decision.py -k "format_detection" -v`

Expected: FAIL with "cannot import name '_is_role_structured_payload'"

### Step 2: Implement format detection in role_structured_decision.py

Add to `backend/app/runtime/role_structured_decision.py`:

```python
def _is_role_structured_payload(payload: dict[str, Any]) -> bool:
    """Strict format detection: all three role keys must be present.

    Returns True only if payload has all of:
    - "interpreter" (dict)
    - "director" (dict)
    - "responder" (dict)

    Otherwise returns False (no exception).
    """
    if not isinstance(payload, dict):
        return False

    required_keys = {"interpreter", "director", "responder"}
    present_keys = set(payload.keys())

    return required_keys.issubset(present_keys)
```

### Step 3: Update parse_adapter_response() to use role detection

In `backend/app/runtime/ai_decision.py`, modify `parse_adapter_response()`:

```python
def parse_adapter_response(response: AdapterResponse) -> ParseResult:
    """Parse raw or structured adapter output into ParseResult.

    Detects format (role-structured vs legacy) and delegates appropriately.
    Both paths normalize into ParsedAIDecision.

    Args:
        response: AdapterResponse from AI adapter

    Returns:
        ParseResult with success flag, decision, role_aware_decision (if applicable), errors, raw output
    """
    from app.runtime.role_structured_decision import (
        _is_role_structured_payload,
        parse_role_contract,
    )

    raw_output = response.raw_output

    # Step 1: Check adapter error
    if response.is_error:
        return ParseResult(
            success=False,
            decision=None,
            role_aware_decision=None,
            errors=[f"Adapter error: {response.error}"],
            raw_output=raw_output,
        )

    # Step 2: Check structured_payload exists
    if response.structured_payload is None:
        return ParseResult(
            success=False,
            decision=None,
            role_aware_decision=None,
            errors=["No structured_payload in adapter response"],
            raw_output=raw_output,
        )

    # Check structured_payload is dict
    if not isinstance(response.structured_payload, dict):
        return ParseResult(
            success=False,
            decision=None,
            role_aware_decision=None,
            errors=[
                f"structured_payload must be dict, got {type(response.structured_payload).__name__}"
            ],
            raw_output=raw_output,
        )

    # Step 3: Detect format and delegate
    if _is_role_structured_payload(response.structured_payload):
        # Role-structured path (W2.4.3)
        try:
            role_aware = parse_role_contract(response.structured_payload, raw_output)
            return ParseResult(
                success=True,
                decision=role_aware.parsed_decision,
                role_aware_decision=role_aware,
                errors=[],
                raw_output=raw_output,
            )
        except Exception as e:
            return ParseResult(
                success=False,
                decision=None,
                role_aware_decision=None,
                errors=[str(e)],
                raw_output=raw_output,
            )
    else:
        # Legacy path (W2.1.3)
        # ... existing legacy parsing code ...
```

### Step 4: Run tests

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_role_structured_decision.py -v`

Expected: All tests PASS

### Step 5: Run full ai_decision tests

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_decision.py -v`

Expected: All existing tests still PASS

### Step 6: Commit

```bash
git add backend/app/runtime/role_structured_decision.py backend/app/runtime/ai_decision.py backend/tests/runtime/test_role_structured_decision.py
git commit -m "feat(w2): implement role format detection and parsing delegation

- Add _is_role_structured_payload(): strict detection (all three roles required)
- Update parse_adapter_response() to detect format and delegate
- Role-structured path calls parse_role_contract() from W2.4.3 module
- Legacy path continues unchanged
- Both paths return ParseResult with role_aware_decision (if applicable)"
```

---

## Task 3: Add Comprehensive Role Parsing Tests

**Files:**
- Modify: `backend/tests/runtime/test_role_structured_decision.py`

### Step 1: Test normalization mapping

Add to test file:

```python
def test_normalization_scene_reading_to_interpretation():
    """interpreter.scene_reading → scene_interpretation (stripped)."""
    from app.runtime.role_structured_decision import _normalize_role_contract

    interpreter = InterpreterSection(
        scene_reading="  Scene with whitespace  ",
        detected_tensions=[],
        trigger_candidates=[],
    )
    director = DirectorSection(
        conflict_steering="Steering",
        escalation_level=5,
        recommended_direction="hold",
    )
    responder = ResponderSection()

    decision = _normalize_role_contract(interpreter, director, responder, "raw")

    assert decision.scene_interpretation == "Scene with whitespace"


def test_normalization_director_to_rationale():
    """director.conflict_steering → rationale (stripped)."""
    from app.runtime.role_structured_decision import _normalize_role_contract

    interpreter = InterpreterSection(
        scene_reading="Scene",
        detected_tensions=[],
        trigger_candidates=[],
    )
    director = DirectorSection(
        conflict_steering="  Steering rationale  ",
        escalation_level=5,
        recommended_direction="escalate",
    )
    responder = ResponderSection()

    decision = _normalize_role_contract(interpreter, director, responder, "raw")

    assert decision.rationale == "Steering rationale"


def test_normalization_responder_state_changes():
    """responder.state_change_candidates → proposed_deltas."""
    from app.runtime.role_structured_decision import _normalize_role_contract
    from app.runtime.role_contract import StateChangeCandidate

    interpreter = InterpreterSection(
        scene_reading="Scene",
        detected_tensions=[],
        trigger_candidates=[],
    )
    director = DirectorSection(
        conflict_steering="Steering",
        escalation_level=5,
        recommended_direction="hold",
    )
    responder = ResponderSection(
        state_change_candidates=[
            StateChangeCandidate(
                target_path="characters.alice.emotional_state",
                proposed_value=75,
                rationale="Increase emotion",
            )
        ]
    )

    decision = _normalize_role_contract(interpreter, director, responder, "raw")

    assert len(decision.proposed_deltas) == 1
    assert decision.proposed_deltas[0].target_path == "characters.alice.emotional_state"
    assert decision.proposed_deltas[0].next_value == 75
    assert decision.proposed_deltas[0].delta_type is None
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_role_structured_decision.py -v`

Expected: All tests PASS

### Step 2: Commit

```bash
git add backend/tests/runtime/test_role_structured_decision.py
git commit -m "test(w2): add comprehensive normalization mapping tests

- Test scene_reading → scene_interpretation (whitespace stripped)
- Test conflict_steering → rationale (whitespace stripped)
- Test state_change_candidates → proposed_deltas conversion
- Verify delta_type=None for responder-derived deltas"
```

---

## Task 4: Integration Testing and Verification

**Files:**
- Modify: `backend/tests/runtime/test_role_structured_decision.py`

### Step 1: Integration test

Add to test file:

```python
def test_full_role_contract_parsing_integration():
    """End-to-end: AIRoleContract → ParsedRoleAwareDecision → ParsedAIDecision."""
    from app.runtime.role_structured_decision import parse_role_contract
    from app.runtime.role_contract import ResponseImpulse

    # Create realistic role-structured payload
    payload = {
        "interpreter": {
            "scene_reading": "Characters in conflict",
            "detected_tensions": ["power_struggle"],
            "trigger_candidates": ["escalation_trigger"],
        },
        "director": {
            "conflict_steering": "Escalate the confrontation",
            "escalation_level": 7,
            "recommended_direction": "escalate",
        },
        "responder": {
            "response_impulses": [
                {
                    "character_id": "alice",
                    "impulse_type": "dialogue_urge",
                    "intensity": 8,
                    "rationale": "Confront directly",
                }
            ],
            "state_change_candidates": [
                {
                    "target_path": "characters.alice.emotional_state",
                    "proposed_value": 85,
                    "rationale": "Heightened emotion",
                }
            ],
            "dialogue_impulses": None,
            "trigger_assertions": ["escalation_trigger"],
            "scene_transition_candidate": None,
        },
    }

    # Parse
    role_aware = parse_role_contract(payload, "raw output")

    # Verify composition
    assert role_aware.parsed_decision is not None
    assert role_aware.interpreter is not None
    assert role_aware.director is not None
    assert role_aware.responder is not None

    # Verify canonical decision normalization
    parsed = role_aware.parsed_decision
    assert parsed.scene_interpretation == "Characters in conflict"
    assert parsed.rationale == "Escalate the confrontation"
    assert "escalation_trigger" in parsed.detected_triggers
    assert len(parsed.proposed_deltas) == 1
    assert len(parsed.dialogue_impulses) == 1

    # Verify role sections preserved
    assert role_aware.interpreter.scene_reading == "Characters in conflict"
    assert role_aware.director.recommended_direction == "escalate"
    assert len(role_aware.responder.response_impulses) == 1
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_role_structured_decision.py::test_full_role_contract_parsing_integration -v`

Expected: PASS

### Step 2: Backward compatibility check

Add to test file:

```python
def test_legacy_parsing_still_works():
    """Legacy (non-role-structured) parsing unchanged."""
    from app.runtime.ai_decision import parse_adapter_response
    from app.runtime.ai_adapter import AdapterResponse
    from app.runtime.ai_output import StructuredAIStoryOutput

    legacy_payload = StructuredAIStoryOutput(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_state_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
    )

    response = AdapterResponse(
        raw_output="raw",
        structured_payload=legacy_payload.model_dump(),
    )

    result = parse_adapter_response(response)

    assert result.success is True
    assert result.decision is not None
    assert result.role_aware_decision is None  # Legacy path doesn't populate
```

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_role_structured_decision.py::test_legacy_parsing_still_works -v`

Expected: PASS

### Step 3: Run full test suite

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/ -q`

Expected: All tests PASS (no regressions)

### Step 4: Commit

```bash
git add backend/tests/runtime/test_role_structured_decision.py
git commit -m "test(w2): add integration and backward compatibility tests

- Full end-to-end: AIRoleContract → ParsedRoleAwareDecision → ParsedAIDecision
- Verify legacy parsing unchanged and backward compatible
- All runtime tests passing (no regressions)"
```

---

## Verification Commands

```bash
# Run W2.4.3 tests
PYTHONPATH=backend python -m pytest backend/tests/runtime/test_role_structured_decision.py -v

# Run full runtime suite
PYTHONPATH=backend python -m pytest backend/tests/runtime/ -q

# Verify ParsedRoleAwareDecision exists
grep -n "class ParsedRoleAwareDecision" backend/app/runtime/role_structured_decision.py
```

**Expected Results:**
- All W2.4.3 tests pass
- All runtime tests pass (no regressions)
- ParsedRoleAwareDecision defined and importable

---

## Acceptance Criteria

- ✅ ParsedRoleAwareDecision defined (composition of ParsedAIDecision + role sections)
- ✅ Strict format detection (all three roles required)
- ✅ Role parsing delegation implemented
- ✅ Normalization mapping complete (spec section 3)
- ✅ Both legacy and role-structured paths work
- ✅ Backward compatibility maintained
- ✅ All tests passing (no regressions)
- ✅ Ready for W2.4.4 diagnostics layer
