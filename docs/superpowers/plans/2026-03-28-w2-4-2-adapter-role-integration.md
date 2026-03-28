# W2.4.2: Adapter Role-Structured Output Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the canonical AI adapter to request and return role-separated output (interpreter, director, responder) from a single AI call.

**Architecture:** AdapterRequest includes explicit instruction for role-separated output. AdapterResponse.structured_payload returns AIRoleContract-shaped output. MockStoryAIAdapter generates role-structured mock data for deterministic testing.

**Tech Stack:** Python 3.10+, Pydantic v2, W2.4.1 AIRoleContract models.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `backend/app/runtime/ai_adapter.py` | Modify | Add role_structured_output field to AdapterRequest; update MockStoryAIAdapter to return AIRoleContract shape |
| `backend/app/runtime/role_contract.py` | Import | Use AIRoleContract and role models (created in W2.4.1) |
| `backend/tests/runtime/test_ai_adapter.py` | Modify | Add tests for role-structured output request/response |

---

## Task 1: Import AIRoleContract and Create Helper

**Files:**
- Modify: `backend/app/runtime/ai_adapter.py` (lines 1-30)
- Import: `backend/app/runtime/role_contract.py` (from W2.4.1)

### Step 1: Read current ai_adapter.py and verify imports

Run: `head -30 backend/app/runtime/ai_adapter.py`

Expected: Confirm current imports and structure.

### Step 2: Add AIRoleContract import to ai_adapter.py

In `backend/app/runtime/ai_adapter.py`, modify the import section:

```python
# At the very top of the file, before all other imports
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

# NEW: Import role contract (W2.4.1)
from app.runtime.role_contract import AIRoleContract
```

**Critical:** `from __future__ import annotations` MUST be the first import in the file.

### Step 3: Create helper function to generate mock role-structured output

In `backend/app/runtime/ai_adapter.py`, add this function before MockStoryAIAdapter class (around line 103):

```python
def _create_mock_role_contract() -> dict[str, Any]:
    """Create a mock AIRoleContract shape for deterministic testing.

    Constructs and validates a dict matching AIRoleContract structure.

    Returns:
        Dict matching AIRoleContract structure (interpreter, director, responder).
        Validated against AIRoleContract schema for contract correctness.
    """
    # Construct mock contract dict
    mock_contract_dict = {
        "interpreter": {
            "scene_reading": "[mock] Scene interpretation - generic analysis of current state",
            "detected_tensions": ["mock_tension_1"],
            "trigger_candidates": ["mock_trigger_candidate"],
            "uncertainty_markers": None,
        },
        "director": {
            "conflict_steering": "[mock] Recommended conflict direction for this turn",
            "escalation_level": 5,
            "recommended_direction": "hold",
            "pressure_movement": None,
        },
        "responder": {
            "response_impulses": [],
            "state_change_candidates": [],
            "dialogue_impulses": None,
            "trigger_assertions": [],
            "scene_transition_candidate": None,
        },
    }

    # Validate dict conforms to AIRoleContract schema
    validated = AIRoleContract(**mock_contract_dict)

    # Return serialized dict (ensures contract compliance)
    return validated.model_dump()
```

**Contract validation:** This helper constructs an actual AIRoleContract instance and returns `model_dump()`. This ensures the mock output conforms to the contract specification.

### Step 4: Commit

```bash
git add backend/app/runtime/ai_adapter.py
git commit -m "feat(w2): add AIRoleContract import and mock role-structured output helper"
```

---

## Task 2: Add role_structured_output Field to AdapterRequest

**Files:**
- Modify: `backend/app/runtime/ai_adapter.py` (AdapterRequest class, lines 25-44)

### Step 1: Add field to AdapterRequest

Replace AdapterRequest class in `backend/app/runtime/ai_adapter.py`:

```python
class AdapterRequest(BaseModel):
    """Input to an AI adapter from the canonical story runtime.

    Attributes:
        session_id: Session identifier
        turn_number: Current turn number (0-based or 1-based, depends on session start)
        current_scene_id: Active scene/phase identifier
        canonical_state: Complete world state snapshot (dict)
        recent_events: List of recent events as plain dicts (not Pydantic objects)
        operator_input: Optional operator instruction or context
        request_role_structured_output: If True, request output as AIRoleContract shape (W2.4.2+).
                                        Defaults to False for backward compatibility.
                                        W2.4.3 will update default to True when normalization is ready.
        metadata: Extensible metadata dict for future use
    """

    session_id: str
    turn_number: int
    current_scene_id: str
    canonical_state: dict[str, Any]
    recent_events: list[dict[str, Any]] = Field(default_factory=list)
    operator_input: str | None = None
    request_role_structured_output: bool = Field(default=False)
        # W2.4.2+: Request role-separated output (interpreter, director, responder).
        # Defaults to False (maintains backward compatibility).
        # Set to True to receive AIRoleContract shape. W2.4.3 will update default when ready.
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Step 2: Run existing adapter request tests to ensure backward compatibility

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_adapter.py::TestAdapterRequest -v`

Expected: All TestAdapterRequest tests pass (request_role_structured_output defaults to False for backward compatibility).

### Step 3: Commit

```bash
git add backend/app/runtime/ai_adapter.py
git commit -m "feat(w2): add request_role_structured_output field to AdapterRequest"
```

---

## Task 3: Update MockStoryAIAdapter to Return Role-Structured Output

**Files:**
- Modify: `backend/app/runtime/ai_adapter.py` (MockStoryAIAdapter.generate method, lines 121-154)

### Step 1: Update MockStoryAIAdapter.generate to return AIRoleContract shape

Replace the MockStoryAIAdapter.generate method:

```python
def generate(self, request: AdapterRequest) -> AdapterResponse:
    """Generate deterministic mock output from request.

    If request.request_role_structured_output is True, returns output in AIRoleContract shape
    (interpreter, director, responder). Otherwise, returns legacy structure.

    Args:
        request: AdapterRequest (fields used to construct deterministic output)

    Returns:
        AdapterResponse with role-structured or legacy mock data
    """
    raw = (
        f"[mock adapter] turn={request.turn_number} "
        f"scene={request.current_scene_id} "
        f"session={request.session_id[:8]}"
    )

    # If role-structured output requested, return AIRoleContract shape
    if request.request_role_structured_output:
        structured_payload = _create_mock_role_contract()
    else:
        # Legacy fallback for backward compatibility
        structured_payload = {
            "detected_triggers": [],
            "proposed_deltas": [],
            "proposed_scene_id": None,
            "narrative_text": "[mock narrative - no real AI involved]",
            "rationale": "[mock rationale]",
        }

    return AdapterResponse(
        raw_output=raw,
        structured_payload=structured_payload,
        backend_metadata={
            "adapter": "mock",
            "deterministic": True,
            "latency_ms": 0,
            "role_structured": request.request_role_structured_output,
        },
        error=None,
    )
```

### Step 2: Run all adapter tests

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_adapter.py -v`

Expected: All existing tests pass. MockStoryAIAdapter defaults to legacy format (request_role_structured_output=False).

### Step 3: Commit

```bash
git add backend/app/runtime/ai_adapter.py
git commit -m "feat(w2): update MockStoryAIAdapter to return role-structured output"
```

---

## Task 4: Add Tests for Role-Structured Output Request/Response

**Files:**
- Modify: `backend/tests/runtime/test_ai_adapter.py`
- Test: Verify role-structured output is requested and returned

### Step 1: Write test for AdapterRequest with role-structured output flag

Add to `backend/tests/runtime/test_ai_adapter.py`:

```python
class TestAdapterRequestRoleStructured:
    """Test role-structured output request field."""

    def test_adapter_request_role_structured_defaults_to_false(self):
        """AdapterRequest.request_role_structured_output defaults to False (backward compat).

        W2.4.3 will update default to True when normalization is ready.
        """
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
        )
        assert request.request_role_structured_output is False

    def test_adapter_request_role_structured_can_be_set_true(self):
        """AdapterRequest.request_role_structured_output can be set to True to opt-in to new format."""
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            request_role_structured_output=True,
        )
        assert request.request_role_structured_output is True
```

### Step 1.5: Understand W2.4.2 Scope Boundary

**W2.4.2 is request/response only:**
- ✅ AdapterRequest field for signaling role-structured output
- ✅ MockStoryAIAdapter returns AIRoleContract-shaped structured_payload
- ✅ Tests verify request signaling and response shape
- ❌ NO parsing (W2.4.3 work)
- ❌ NO normalization (W2.4.3 work)
- ❌ NO runtime integration (W2.4.3 work)
- ❌ NO guard/validation changes (W2.4.3 work)

This is a signal/response contract update only. The parsing and normalization of role-structured output into the canonical decision path happens in W2.4.3.

### Step 2: Write test for mock adapter role-structured response

Add to `backend/tests/runtime/test_ai_adapter.py`:

```python
class TestMockAdapterRoleStructured:
    """Test MockStoryAIAdapter role-structured output."""

    def test_mock_adapter_returns_role_contract_shape_when_requested(self):
        """MockStoryAIAdapter returns AIRoleContract shape when role_structured_output=True."""
        adapter = MockStoryAIAdapter()
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            request_role_structured_output=True,
        )

        response = adapter.generate(request)

        # Verify structure matches AIRoleContract shape
        payload = response.structured_payload
        assert payload is not None
        assert "interpreter" in payload
        assert "director" in payload
        assert "responder" in payload

        # Verify interpreter section
        assert "scene_reading" in payload["interpreter"]
        assert "detected_tensions" in payload["interpreter"]
        assert "trigger_candidates" in payload["interpreter"]

        # Verify director section
        assert "conflict_steering" in payload["director"]
        assert "escalation_level" in payload["director"]
        assert "recommended_direction" in payload["director"]

        # Verify responder section
        assert "response_impulses" in payload["responder"]
        assert "state_change_candidates" in payload["responder"]
        assert "trigger_assertions" in payload["responder"]

    def test_mock_adapter_returns_legacy_format_when_not_requested(self):
        """MockStoryAIAdapter returns legacy format when role_structured_output=False."""
        adapter = MockStoryAIAdapter()
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            request_role_structured_output=False,
        )

        response = adapter.generate(request)

        # Verify legacy structure
        payload = response.structured_payload
        assert payload is not None
        assert "detected_triggers" in payload
        assert "proposed_deltas" in payload
        assert "proposed_scene_id" in payload
        assert "narrative_text" in payload

    def test_mock_adapter_metadata_reflects_role_structured_flag(self):
        """MockStoryAIAdapter backend_metadata includes role_structured flag."""
        adapter = MockStoryAIAdapter()
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            request_role_structured_output=True,
        )

        response = adapter.generate(request)

        assert response.backend_metadata["role_structured"] is True

    def test_mock_adapter_role_structured_payload_has_canonical_keys(self):
        """MockStoryAIAdapter role-structured output has all three canonical top-level keys.

        When request_role_structured_output=True, structured_payload must contain
        exactly these top-level keys: interpreter, director, responder.
        This ensures the payload is recognized as role-structured format, not legacy.
        """
        adapter = MockStoryAIAdapter()
        request = AdapterRequest(
            session_id="sess1",
            turn_number=1,
            current_scene_id="phase_1",
            canonical_state={},
            recent_events=[],
            request_role_structured_output=True,
        )

        response = adapter.generate(request)
        payload = response.structured_payload

        # Verify all three canonical keys are present
        assert isinstance(payload, dict)
        assert "interpreter" in payload
        assert "director" in payload
        assert "responder" in payload

        # Verify it's not legacy format (no legacy-specific keys as top level)
        assert "detected_triggers" not in payload  # Legacy format has this at top level
        assert "proposed_deltas" not in payload    # Legacy format has this at top level
```

### Step 3: Run new tests

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_adapter.py::TestAdapterRequestRoleStructured -v`

Expected: 2 tests pass (defaults_to_false, can_be_set_true).

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_adapter.py::TestMockAdapterRoleStructured -v`

Expected: 4 tests pass (returns_role_contract_shape, returns_legacy_format, metadata_reflects_flag, has_canonical_keys).

### Step 4: Run full adapter test suite

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_adapter.py -v`

Expected: All tests pass (old + new).

### Step 5: Commit

```bash
git add backend/tests/runtime/test_ai_adapter.py
git commit -m "test(w2): add role-structured output request/response tests"
```

---

## Task 5: Verification and Integration Test

**Files:**
- Verify: Both new and existing tests pass
- Verify: No scope jump to W2.4.3 (normalization deferred)

### Step 1: Run full runtime test suite

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/ -v --tb=short -q`

Expected: All tests pass (no failures, no new warnings).

### Step 2: Verify no W2.4.3 scope creep

Confirm:
- ✅ AdapterRequest has role_structured_output field
- ✅ MockStoryAIAdapter returns AIRoleContract shape
- ✅ Tests verify role-structured output
- ✅ No normalization logic added (deferred to W2.4.3)
- ✅ No guard/validation changes (deferred to W2.4.3)
- ✅ Backward compatibility maintained (can set request_role_structured_output=False)

### Step 3: Final commit summary

The following changes are complete:
1. AdapterRequest.request_role_structured_output field added (defaults to False for backward compatibility)
2. MockStoryAIAdapter.generate returns AIRoleContract shape (validated contract)
3. Tests verify role-structured request/response
4. All existing tests still pass
5. No scope jump to W2.4.3 (request/response only, no parsing or normalization)

### Step 4: Run final verification

Run: `PYTHONPATH=backend python -m pytest backend/tests/runtime/test_ai_adapter.py -v --tb=short`

Expected: All tests pass.

---

## Acceptance Criteria

- ✅ AdapterRequest has request_role_structured_output field (default=False for backward compatibility)
- ✅ MockStoryAIAdapter returns role-structured output in AIRoleContract shape when request_role_structured_output=True
- ✅ MockStoryAIAdapter returns legacy format when request_role_structured_output=False (default)
- ✅ Tests verify role-structured request/response (explicit opt-in testing)
- ✅ Backward compatibility maintained (existing code unaffected, W2.4.3 will update defaults)
- ✅ All existing tests pass
- ✅ No W2.4.3 scope jump (normalization deferred, default update deferred)

---

## What's Deferred (W2.4.3 and Beyond)

- **Normalization logic** — Converting role-structured output to proposals/deltas
- **Guard/validation integration** — Applying existing guards to normalized proposals
- **Real AI adapter integration** — Teaching actual Claude/GPT adapters to emit role-structured output
- **Role output parsing/validation** — Deserializing structured_payload as AIRoleContract (runtime integration)
- **Mutation application** — Using normalized responder proposals in state updates

---

## Commit Messages

```
feat(w2): add AIRoleContract import and mock role-structured output helper

feat(w2): add request_role_structured_output field to AdapterRequest

feat(w2): update MockStoryAIAdapter to return role-structured output

test(w2): add role-structured output request/response tests
```

