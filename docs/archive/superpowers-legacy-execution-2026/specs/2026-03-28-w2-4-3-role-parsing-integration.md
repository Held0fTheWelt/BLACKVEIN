# W2.4.3: Parse and Normalize Role-Structured AI Output

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate role-structured AI output (AIRoleContract from W2.4.2) into the canonical parse/normalize flow, preserving role sections for diagnostics while feeding the core runtime decision through the existing validation and execution path.

**Architecture:** Strict format detection (all three role keys required) with delegation to a focused role-parsing module. Both legacy and role-structured paths normalize into the same canonical downstream runtime decision object. Role sections are preserved separately for diagnostics without altering runtime behavior.

**Tech Stack:** Python 3.10+, Pydantic v2, existing runtime structures (ParsedAIDecision, ProposedDelta, DialogueImpulse).

---

## 1. Module Architecture

### 1.1 Modified: `backend/app/runtime/ai_decision.py`

**Responsibility:** Canonical parse entry point with strict format detection and delegation.

**Changes:**
- Add `_is_role_structured_payload()` function for strict detection
- Update `parse_adapter_response()` to detect format and delegate appropriately
- Extend `ParseResult` to optionally include `role_aware_decision`
- Keep `ParsedAIDecision` as the sole canonical runtime decision object

**Key constraint:** Detection must be strict—all three role keys (interpreter, director, responder) must be present to treat payload as role-structured. Otherwise, fall back to legacy parsing without exception.

### 1.2 New: `backend/app/runtime/role_structured_decision.py`

**Responsibility:** W2.4-specific role-contract parsing and normalization.

**Exports:**
- `ParsedRoleAwareDecision` — canonical role-preserving parsed decision wrapper
- `parse_role_contract(payload, raw_output)` — Parse and normalize AIRoleContract

**Key constraint:** Return typed role sections, not raw dicts. No partial results or silent downgrades. Explicit errors only.

---

## 2. Data Structures

### 2.1 ParsedRoleAwareDecision (New)

```python
from app.runtime.ai_decision import ParsedAIDecision
from app.runtime.role_contract import (
    InterpreterSection,
    DirectorSection,
    ResponderSection,
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
```

**Critical rule:** `parsed_decision` is the ONLY object that feeds validation, delta construction, and guarded execution. Role sections are preserved alongside for diagnostics and logging only.

### 2.2 Extended: ParseResult

```python
class ParseResult(BaseModel):
    """Result of parse_adapter_response() — inspectable outcome.

    Attributes:
        success: True if parse+normalize+prevalidate all passed
        decision: ParsedAIDecision (canonical runtime decision, always set if successful)
        role_aware_decision: ParsedRoleAwareDecision (optional, only if role-structured input)
        errors: List of error strings (empty if successful)
        raw_output: Original adapter output (always preserved)
    """
    success: bool
    decision: ParsedAIDecision | None = None
    role_aware_decision: ParsedRoleAwareDecision | None = None
    errors: list[str] = []
    raw_output: str

    @field_validator("decision", "role_aware_decision")
    @classmethod
    def validate_consistency(cls, v, info):
        """Ensure no split ownership between decision and role_aware_decision."""
        # If role_aware_decision exists, decision must be identical to role_aware_decision.parsed_decision
        # This is enforced during construction, not after
        return v
```

**Consistency rule:** If both `decision` and `role_aware_decision` are present, they must be semantically identical at the ParsedAIDecision level. No divergence allowed.

**Implementation note:** This consistency is enforced at construction time in `parse_role_contract()`. When returning ParseResult, set `decision = role_aware_decision.parsed_decision` to ensure they point to the same object (no duplicate, no divergence). Field validators are for runtime type safety only, not for post-construction consistency checks.

---

## 3. Canonical Normalization Mapping

### 3.1 Interpreter → Scene Interpretation

| Source | Target | Rule |
|--------|--------|------|
| `interpreter.scene_reading` | `parsed_decision.scene_interpretation` | Strip whitespace, use as-is |

**Rationale:** Interpreter owns scene reading and immediate situation understanding.

### 3.2 Director → Rationale

| Source | Target | Rule |
|--------|--------|------|
| `director.conflict_steering` | `parsed_decision.rationale` | Strip whitespace, use as-is |

**Rationale:** Director owns conflict steering and dramaturgic reasoning. Use the full explanatory text field, not categorical labels.

### 3.3 Responder → Runtime-Relevant Proposals

| Source | Target | Rule |
|--------|--------|------|
| `responder.state_change_candidates` | `parsed_decision.proposed_deltas` | Convert each StateChangeCandidate to ProposedDelta: `target_path` (unchanged), `next_value` (from StateChangeCandidate.proposed_value), `rationale` (unchanged), `delta_type` (None) |
| `responder.trigger_assertions` | `parsed_decision.detected_triggers` | Use as-is |
| `responder.scene_transition_candidate` | `parsed_decision.proposed_scene_id` | Use as-is (or None if not set) |
| `responder.response_impulses` (dialogue_urge only) | `parsed_decision.dialogue_impulses` | Filter response_impulses for impulse_type=="dialogue_urge" only; convert each to DialogueImpulse: `character_id` (unchanged), `impulse_text` (from ResponseImpulse.rationale), `intensity` (scale 0-10 to 0.0-1.0) |
| `responder.dialogue_impulses` | (diagnostic only, not used in normalization) | Preserved in responder section for diagnostics only; does NOT feed parsed_decision |
| All `responder.response_impulses` | `ParsedRoleAwareDecision.responder.response_impulses` | Preserve all (including non-dialogue types) in responder section for diagnostics |

**Critical constraints:**
- Only `dialogue_urge` impulses map to `dialogue_impulses` (emotional_reaction and action_urge stay diagnostic)
- StateChangeCandidate.proposed_value → ProposedDelta.next_value (field rename, not transformation)
- StateChangeCandidate → ProposedDelta always uses delta_type=None (no new information from responder)
- ResponseImpulse.rationale becomes DialogueImpulse.impulse_text (the rationale is the concrete dialogue content)
- Responder's separate dialogue_impulses field is preserved for diagnostics but does NOT feed the normalized decision (responder impulses are the authoritative source)
- StateChangeCandidate is pre-delta format; conversion to ProposedDelta is normalization, not execution
- All normalized responder proposals still go through existing validation and guard path

---

## 4. Parsing Flow

### 4.1 Strict Format Detection

```python
def _is_role_structured_payload(payload: dict[str, Any]) -> bool:
    """Strict detection: all three role keys must be present.

    Only return True if payload is a dict with ALL top-level keys:
    - interpreter
    - director
    - responder

    Anything else (missing any key, wrong type) → False (fall back to legacy).
    """
    if not isinstance(payload, dict):
        return False
    return all(key in payload for key in ["interpreter", "director", "responder"])
```

**Critical rule:** Fuzzy or partial detection is forbidden. Missing even one role key means legacy parsing.

### 4.2 Updated parse_adapter_response() Flow

1. **Check adapter error** — return ParseResult with error if adapter failed (unchanged)
2. **Check structured_payload exists** — return error if None (unchanged)
3. **Strict format detection** — `_is_role_structured_payload(payload)`
4. **If role-structured:**
   - Delegate to `role_structured_decision.parse_role_contract(payload, raw_output)`
   - Return ParseResult with both `decision` (from role_aware_decision.parsed_decision) and `role_aware_decision`
5. **Otherwise (legacy):**
   - Use existing StructuredAIStoryOutput parsing path
   - Return ParseResult with `decision` only
6. **Pre-validate decision** — unchanged (same prevalidation for both paths)
7. **Return ParseResult** — with success flag, decision, errors, raw_output

**Critical rule:** Both paths converge into the same downstream validation/guard/execution flow. No special handling for role-structured decisions at runtime.

### 4.3 role_structured_decision.parse_role_contract()

```python
def parse_role_contract(
    payload: dict[str, Any],
    raw_output: str,
) -> tuple[ParsedRoleAwareDecision | None, list[str]]:
    """Parse role-structured payload into ParsedRoleAwareDecision.

    Steps:
    1. Parse dict → AIRoleContract (Pydantic validation of all three role sections)
    2. Normalize responder section using conversion functions:
       - StateChangeCandidate → ProposedDelta (target_path, next_value←proposed_value, rationale, delta_type=None)
       - Trigger assertions (list of strings) → detected_triggers (unchanged)
       - Scene transition candidate (string or None) → proposed_scene_id (unchanged)
       - Response impulses (dialogue_urge only) → DialogueImpulse (character_id, impulse_text←rationale, intensity 0-10→0.0-1.0)
    3. Extract normalized fields from interpreter, director, responder:
       - scene_interpretation ← interpreter.scene_reading (strip whitespace)
       - rationale ← director.conflict_steering (strip whitespace)
       - proposed_deltas, detected_triggers, proposed_scene_id, dialogue_impulses ← from normalization above
    4. Construct ParsedAIDecision from normalized fields + raw_output
    5. Construct ParsedRoleAwareDecision(parsed_decision=..., interpreter=..., director=..., responder=...)
    6. Pre-validate decision
    7. Return (ParsedRoleAwareDecision, []) or (None, [errors])

    Args:
        payload: Validated dict with interpreter, director, responder keys
        raw_output: Original raw output for diagnostic trace

    Returns:
        (ParsedRoleAwareDecision, []) if successful
        (None, [errors]) if parsing or validation failed

    Critical constraints:
    - No silent downgrades. If this function is called, it means strict detection succeeded. Parse failure must return explicit errors.
    - Set decision = role_aware_decision.parsed_decision when returning to ParseResult (no duplicate, no divergence)
    - Only dialogue_urge impulses map to dialogue_impulses; other response impulses stay diagnostic only
    - Responder's separate dialogue_impulses field is preserved diagnostically but does NOT feed the normalized decision
    """
```

---

## 5. Error Handling

### 5.1 Detection-Level Errors

- **Adapter error** → ParseResult with error (unchanged)
- **No structured_payload** → ParseResult with error (unchanged)
- **Not a dict** → Fall back to legacy parsing
- **Missing role keys** → Fall back to legacy parsing

### 5.2 Parsing-Level Errors (Role-Structured Path)

- **Strict detection succeeds but AIRoleContract validation fails** → Explicit error list, no silent downgrade to legacy
- **Missing required field in any role section** → Validation error, caught and returned
- **Malformed responder candidate** → Validation error, caught and returned
- **Duplicate trigger IDs in responder.trigger_assertions** → Caught by prevalidation
- **Invalid intensity scale in response_impulses** → Validation error

### 5.3 No Silent Failures

**Canonical rule:** If strict detection succeeds (all three role keys present), the parser MUST attempt role parsing. If role parsing fails, return explicit errors. DO NOT silently fall back to legacy parsing.

---

## 6. Testing Strategy

### 6.1 Format Detection Tests (test_ai_decision.py)

- ✅ Valid AIRoleContract (all 3 keys present) → detected as role-structured
- ✅ Missing one role key (e.g., no "responder") → falls back to legacy parsing
- ✅ Missing two role keys → falls back to legacy
- ✅ Empty payload `{}` → falls back to legacy
- ✅ None payload → error (unchanged)
- ✅ Non-dict payload → error (unchanged)
- ✅ Partial role overlap (two keys present) → NOT treated as role-structured, falls back to legacy
- ✅ Legacy StructuredAIStoryOutput format → correctly identified as legacy

### 6.2 Role-Structured Parsing Tests (test_role_structured_decision.py)

- ✅ Valid AIRoleContract parses successfully
- ✅ All three role sections present in ParsedRoleAwareDecision
- ✅ Missing required field in interpreter → clear validation error
- ✅ Missing required field in director → clear validation error
- ✅ Missing required field in responder → clear validation error
- ✅ Normalization: interpreter.scene_reading → parsed_decision.scene_interpretation
- ✅ Normalization: director.conflict_steering → parsed_decision.rationale
- ✅ Normalization: responder.state_change_candidates → proposed_deltas (StateChangeCandidate → ProposedDelta)
- ✅ Normalization: responder.trigger_assertions → detected_triggers
- ✅ Normalization: responder.scene_transition_candidate → proposed_scene_id
- ✅ Normalization: responder.response_impulses (dialogue_urge only) → dialogue_impulses
- ✅ Non-dialogue impulses (emotional_reaction, action_urge) remain diagnostic only
- ✅ Empty responder candidates → valid decision with empty proposal lists

### 6.3 Backward Compatibility Tests (test_ai_decision.py)

- ✅ Legacy StructuredAIStoryOutput still parses correctly
- ✅ Existing tests for ParsedAIDecision still pass
- ✅ No breaking changes to parse_adapter_response() signature
- ✅ ParseResult structure extended but backward compatible

### 6.4 No Silent Downgrade Tests (test_role_structured_decision.py)

- ✅ Strict detection succeeds but role parsing fails → explicit error list
- ✅ DO NOT silently fall back to legacy parsing
- ✅ Clear error messages identify which role section failed

### 6.5 ParseResult Consistency Tests (test_ai_decision.py)

- ✅ If role_aware_decision is present, decision must be semantically identical to role_aware_decision.parsed_decision
- ✅ No divergence between decision and role_aware_decision allowed
- ✅ For legacy parsing, only decision is set; role_aware_decision is None

### 6.6 Responder Boundary Tests (test_role_structured_decision.py)

- ✅ Only dialogue_urge impulses map to dialogue_impulses
- ✅ Emotional_reaction impulses stay diagnostic
- ✅ Action_urge impulses stay diagnostic
- ✅ Responder candidates preserved in responder section regardless of mapping

### 6.7 Integration Tests (test_w2_4_3_integration.py)

- ✅ Role-structured response → ParsedAIDecision → canonical validation path (no special handling)
- ✅ Parsed decision feeds into existing guard/delta construction/execution unchanged
- ✅ MockStoryAIAdapter returns role-structured → parsed correctly → normalized correctly
- ✅ No parallel execution paths created
- ✅ No changes to guard logic or validation behavior

### 6.8 Scope Boundary Tests (test_w2_4_3_integration.py)

- ✅ W2.4.3 only: parsing and normalization
- ✅ No W2.4.4 work (diagnostics/logging display deferred)
- ✅ No changes to guard logic, validation rules, or mutation application
- ✅ Existing runtime behavior unchanged

---

## 7. Scope: What's In and Out

### 7.1 IN SCOPE (W2.4.3)

- ✅ Detect role-structured vs. legacy payloads (strict detection)
- ✅ Parse AIRoleContract from dict
- ✅ Normalize interpreter → scene_interpretation, director → rationale
- ✅ Normalize responder candidates → proposed_deltas, detected_triggers, proposed_scene_id
- ✅ Selectively map dialogue_urge → dialogue_impulses
- ✅ Preserve all role sections typed and separate
- ✅ Converge both legacy and role paths into canonical ParsedAIDecision
- ✅ Full test coverage (detection, parsing, normalization, integration, scope)
- ✅ No silent failures (explicit errors for all issues)

### 7.2 OUT OF SCOPE (Deferred to W2.4.4+)

- ❌ Logging/diagnostics UI display (W2.4.4)
- ❌ Role section integration into audit trails (W2.4.4+)
- ❌ Rendering interpreter/director/responder in runtime output (W2.4.4+)
- ❌ Guard/validation changes (uses existing validated path)
- ❌ Mutation application changes (uses existing execution path)
- ❌ Changes to conflict_vector, confidence, or other ParsedAIDecision fields
- ❌ Responder-only runtime branches (responder proposals go through canonical path)

---

## 8. Canonical Rules (Non-Negotiable)

1. **ParsedAIDecision is the sole canonical runtime decision object.**
   - Validation, guard logic, delta construction, and execution consume only this object.
   - Role sections are diagnostic enrichment, not runtime authorities.

2. **No split ownership in ParseResult.**
   - If both `decision` and `role_aware_decision` are present, they must be semantically identical.
   - No divergence allowed.

3. **No silent downgrades.**
   - If strict detection succeeds and role parsing fails, return explicit errors.
   - DO NOT silently fall back to legacy parsing.

4. **Responder normalization is selective.**
   - Only dialogue_urge impulses normalize into dialogue_impulses.
   - Emotional and action-oriented impulses remain diagnostic only.
   - Responder candidates remain pre-delta until normalized.

5. **W2.4.3 does not alter runtime guard behavior.**
   - Parsing and normalization change.
   - Downstream validation/guard/execution path remains existing and unchanged.

---

## 9. Files to Create/Modify

### 9.1 New Files

- **`backend/app/runtime/role_structured_decision.py`** (new)
  - ParsedRoleAwareDecision
  - parse_role_contract()
  - normalization helpers

- **`backend/tests/runtime/test_role_structured_decision.py`** (new)
  - Role-structured parsing validation
  - Normalization correctness
  - No silent downgrades
  - Error handling

- **`backend/tests/runtime/test_w2_4_3_integration.py`** (new)
  - Integration with canonical flow
  - Both legacy and role paths converge
  - No parallel execution paths

### 9.2 Modified Files

- **`backend/app/runtime/ai_decision.py`** (modify)
  - Add `_is_role_structured_payload()` detection
  - Update `parse_adapter_response()` to detect and delegate
  - Extend `ParseResult` with `role_aware_decision` field
  - Add consistency validation

---

## 10. Acceptance Criteria

- ✅ Role-structured AI output is parsed correctly (strict detection, typed validation)
- ✅ Parsed result is normalized into ParsedAIDecision (sole runtime decision object)
- ✅ Role sections are preserved typed and separate (ParsedRoleAwareDecision)
- ✅ Only responder-derived proposals feed canonical runtime path
- ✅ Responder normalization is selective (dialogue_urge only to dialogue_impulses)
- ✅ Legacy format still works (backward compatible)
- ✅ No parallel parsing or execution pipelines
- ✅ No silent failures (explicit errors throughout)
- ✅ Full test coverage (10+ test groups, 60+ test cases)
- ✅ No W2.4.3 scope jump (diagnostics deferred to W2.4.4)
- ✅ Existing guard/validation/execution flow unchanged

---

## 11. What's Deferred (W2.4.4 and Beyond)

- **Diagnostics display** — Rendering role sections in logs, audit trails, UI (W2.4.4)
- **Guard/validator updates** — Role-aware validation if needed (future)
- **Mutation application** — Changes to how normalized proposals are executed (future)
- **Conflict analysis tools** — Using director/interpreter for narrative tracking (future)

---

## 12. Commit Message

```
feat(w2): parse and normalize role-structured AI output

Integrates role-contract output into canonical parse/normalize flow with:
- Strict format detection (all three role keys required)
- Delegation to role-parsing module for role-specific logic
- Preservation of typed role sections for diagnostics
- Selective normalization of responder into canonical decision form
- Backward compatibility with legacy structured output
- Single downstream validation/guard/execution path

ParsedRoleAwareDecision preserves role sections alongside canonical
ParsedAIDecision. Only ParsedAIDecision feeds runtime execution.
Both legacy and role-structured paths converge into canonical flow.
```

---
