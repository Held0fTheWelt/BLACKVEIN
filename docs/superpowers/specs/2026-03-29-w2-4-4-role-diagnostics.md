# W2.4.4: Expose Internal AI Role Split in Decision Diagnostics

> **Scope**: Diagnostic and logging layer only. No runtime execution changes.

**Goal**: Make the interpreter/director/responder role separation visible in canonical decision logs, enabling diagnostics to trace role-specific failure modes.

**Architecture**: Extend `AIDecisionLog` with typed role diagnostic fields, populate them from `ParsedRoleAwareDecision` when role-structured parsing occurred, leave them None for legacy decisions. Keep `ParsedAIDecision` as the only canonical runtime decision object.

**Tech Stack**: Python 3.10+, Pydantic v2, existing W2.0.1/W2.4.1–W2.4.3 models.

---

## Design Principles

1. **ParsedAIDecision is Canonical for Runtime** — Role fields are diagnostic-only. No changes to runtime execution path.
2. **Type-Based Detection** — If `ParsedRoleAwareDecision` is present, populate role fields. Otherwise leave as None.
3. **Bounded Diagnostics** — Interpreter/director fields are compact summaries; responder is full detail (feeds runtime validation).
4. **Guard Semantics Unchanged** — Existing `guard_outcome` remains canonical collective validation result for responder proposals.
5. **Backward Compatible** — Legacy parsed decisions have role fields as None.

---

## Models

### InterpreterDiagnosticSummary

Compact diagnostic summary of scene interpretation.

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
```

### DirectorDiagnosticSummary

Compact diagnostic summary of conflict steering decision.

```python
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

### Extended AIDecisionLog

Add three new optional fields and guard_outcome to the existing `AIDecisionLog` model in `w2_models.py`:

```python
class AIDecisionLog(BaseModel):
    """Record of AI decision for a turn.

    ... existing docstring ...

    Attributes (extended for W2.4.4):
        interpreter_output: Diagnostic summary of scene interpretation (None for legacy).
        director_output: Diagnostic summary of conflict steering (None for legacy).
        responder_output: Full responder proposals (None for legacy).
        guard_outcome: Canonical collective validation result for responder-derived proposals.
    """

    # ... existing fields ...
    interpreter_output: InterpreterDiagnosticSummary | None = None
    director_output: DirectorDiagnosticSummary | None = None
    responder_output: ResponderSection | None = None
    guard_outcome: GuardOutcome  # Canonical validation result (required, from w2_models)
    # Note: validation_outcome field (existing) maps from guard_outcome
```

### ParsedRoleAwareDecision (from W2.4.3)

`ParsedRoleAwareDecision` is produced by W2.4.3 role-structured parsing when the adapter output contains all three role sections (interpreter, director, responder). It is used **solely as the source for role diagnostics in W2.4.4**; it does not affect runtime execution.

```python
# From app.runtime.ai_decision (W2.4.3 parsing layer)
class ParsedRoleAwareDecision(BaseModel):
    """Role-structured parse output from W2.4.3.

    Produced when role-structured parsing detects AIRoleContract format.
    Used solely for diagnostic population in W2.4.4.
    Does not feed runtime execution (ParsedAIDecision remains canonical).

    Attributes:
        interpreter: InterpreterSection from AIRoleContract
        director: DirectorSection from AIRoleContract
        responder: ResponderSection from AIRoleContract
        parsed_decision: Canonical ParsedAIDecision (runtime-facing)
    """

    interpreter: InterpreterSection
    director: DirectorSection
    responder: ResponderSection
    parsed_decision: ParsedAIDecision  # The canonical runtime decision
```

### Field Selection Rationale

**InterpreterDiagnosticSummary** preserves:
- `scene_reading` (str) — Essential for understanding what the interpreter observed in the scene
- `detected_tensions` (list[str]) — Core diagnostic output showing identified interpersonal/situational conflicts

**Excluded from InterpreterSection**:
- `trigger_candidates` — Not needed for diagnostics; responder's trigger_assertions are the operative candidates
- `uncertainty_markers` — Optional field; not runtime-critical for diagnosing interpretation failures

**DirectorDiagnosticSummary** preserves:
- `conflict_steering` (str) — Narrative rationale for the chosen direction (diagnostic gold)
- `recommended_direction` (Literal) — The steering decision enum (bounded set, essential for tracing director logic)

**Excluded from DirectorSection**:
- `escalation_level` (0-10 int) — Numeric intensity; not essential for diagnostics (direction itself is sufficient)
- `pressure_movement` (str | None) — Optional detail; can be inferred from conflict_steering text

**ResponderSection** is preserved **in full** because:
- Responder is the only role that produces runtime-relevant proposals
- All fields (impulses, state_change_candidates, trigger_assertions, scene_transition_candidate) feed validation
- Full visibility needed for tracing guard decisions and proposal acceptance/rejection

---

## Logging Helper Function

### Location

Create new module: `backend/app/runtime/ai_decision_logging.py`

**Rationale**: Keeps log construction logic separate from schema definitions. Single point of truth for "how to construct a complete decision log".

### Function: construct_ai_decision_log()

```python
from app.runtime.w2_models import AIDecisionLog, AIValidationOutcome
from app.runtime.ai_decision import ParsedAIDecision, ParsedRoleAwareDecision
from app.runtime.ai_decision_logging import construct_ai_decision_log

def construct_ai_decision_log(
    session_id: str,
    turn_number: int,
    parsed_decision: ParsedAIDecision,
    raw_output: str,  # Explicit parameter (do not assume from ParsedAIDecision)
    role_aware_decision: ParsedRoleAwareDecision | None,
    guard_outcome: GuardOutcome,
    accepted_deltas: list[StateDelta] | None = None,
    rejected_deltas: list[StateDelta] | None = None,
    guard_notes: str | None = None,
    recovery_notes: str | None = None,
) -> AIDecisionLog:
    """Construct a fully-populated AIDecisionLog with role diagnostics if available.

    Type detection:
    - If role_aware_decision is present, extract and populate interpreter/director/responder
    - If role_aware_decision is None, leave role fields as None (legacy parsing path)

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

---

## Integration Point

Turn executor (or equivalent decision logging code) calls the helper when logging a decision:

```python
from app.runtime.ai_decision_logging import construct_ai_decision_log

# After decision validation/guard execution:
decision_log = construct_ai_decision_log(
    session_id=session.session_id,
    turn_number=turn_number,
    parsed_decision=parsed_decision,  # Canonical ParsedAIDecision
    raw_output=raw_adapter_output,  # Explicit parameter
    role_aware_decision=role_aware_decision,  # From W2.4.3 parsing (may be None)
    guard_outcome=guard_outcome,  # Canonical collective validation result
    accepted_deltas=accepted,
    rejected_deltas=rejected,
    guard_notes=guard_notes_if_any,
)
# Log is now ready for storage/auditing with full role diagnostics
```

---

## Canonical Rules (Locked)

1. **ParsedAIDecision** remains the only canonical runtime decision object.
   - Role fields in AIDecisionLog do not affect runtime execution.
   - Guard validation uses ParsedAIDecision and guard_outcome, not role fields.

2. **ParsedRoleAwareDecision** is the source for role-aware diagnostics only.
   - Produced by W2.4.3 parsing when role-structured output is detected.
   - Used to populate role fields in AIDecisionLog for diagnostics.

3. **AIDecisionLog** exposes the role split for diagnostics only.
   - interpreter_output, director_output, responder_output are diagnostic fields.
   - They do not affect runtime validation, delta construction, or execution.

4. **guard_outcome** remains the canonical collective validation result.
   - Applies to responder-derived proposals as a whole.
   - Not duplicated or overridden by role field metadata.

5. **Backward Compatibility**
   - Legacy parsed decisions (ParsedAIDecision only) have role fields = None.
   - No changes to existing runtime path; decision logs are append-only.

---

## Testing

### Test Coverage

1. **Format Detection & Population**
   - Decision logs preserve all three role sections when role-structured parsing occurred
   - Decision logs have None role fields for legacy parsed decisions
   - Type detection (presence of ParsedRoleAwareDecision) works correctly

2. **Diagnostic Correctness**
   - interpreter_output contains scene_reading and detected_tensions from role-aware parse
   - director_output contains conflict_steering and recommended_direction
   - responder_output is the full ResponderSection from role-aware parse
   - raw_output is explicit parameter (not assumed from ParsedAIDecision)

3. **Validation Outcome Mapping**
   - validation_outcome is correctly derived from guard_outcome (not hardcoded)
   - All four guard_outcome states map correctly to validation_outcome values

4. **Diagnostic-Only Constraint**
   - Role fields do not affect runtime validation path
   - Role fields do not affect delta acceptance/rejection
   - Role fields do not affect scene transitions or trigger assertions
   - existing guard_outcome and runtime execution unchanged

5. **Boundedness & Coherence**
   - Logs remain bounded (diagnostic summaries, not full objects except responder)
   - Logs are coherent across multiple turns
   - No scope jump to W2.4.5 (diagnostics only)

### Test Structure

```python
# In backend/tests/runtime/test_ai_decision_logging.py

class TestConstructAIDecisionLogBasic:
    """Test log construction with legacy vs role-aware parsing."""

    def test_construct_log_legacy_parsing_has_none_role_fields(self):
        """Legacy ParsedAIDecision only → role fields = None."""

    def test_construct_log_role_structured_parsing_populates_role_fields(self):
        """ParsedRoleAwareDecision present → role fields populated."""

    def test_raw_output_explicit_parameter_not_assumed(self):
        """raw_output is explicit parameter, not derived from ParsedAIDecision."""

class TestValidationOutcomeMapping:
    """Test guard_outcome → validation_outcome mapping."""

    def test_accepted_maps_to_accepted(self):
    def test_partially_accepted_maps_to_partial(self):
    def test_rejected_maps_to_rejected(self):
    def test_structurally_invalid_maps_to_error(self):

class TestDiagnosticOnlyConstraint:
    """Test that role fields do not affect runtime execution or validation."""

    def test_role_fields_do_not_affect_delta_validation(self):
        """Role fields present or absent should not change delta acceptance/rejection."""
        # Create two logs: one with role diagnostics, one without
        parsed_decision = create_mock_parsed_decision()
        role_aware_decision = create_mock_role_aware_decision()

        log_with_roles = construct_ai_decision_log(
            session_id="sess1",
            turn_number=1,
            parsed_decision=parsed_decision,
            raw_output="mock output",
            role_aware_decision=role_aware_decision,  # Role fields populated
            guard_outcome=GuardOutcome.ACCEPTED,
            accepted_deltas=[mock_delta_1, mock_delta_2],
            rejected_deltas=[mock_delta_3],
        )

        log_without_roles = construct_ai_decision_log(
            session_id="sess1",
            turn_number=1,
            parsed_decision=parsed_decision,
            raw_output="mock output",
            role_aware_decision=None,  # Role fields = None
            guard_outcome=GuardOutcome.ACCEPTED,
            accepted_deltas=[mock_delta_1, mock_delta_2],
            rejected_deltas=[mock_delta_3],
        )

        # Both logs must have identical delta collections
        assert len(log_with_roles.accepted_deltas) == len(log_without_roles.accepted_deltas)
        assert len(log_with_roles.rejected_deltas) == len(log_without_roles.rejected_deltas)
        assert log_with_roles.accepted_deltas == log_without_roles.accepted_deltas
        assert log_with_roles.rejected_deltas == log_without_roles.rejected_deltas

    def test_role_fields_do_not_affect_guard_outcome(self):
        """Presence/absence of role fields should not change guard_outcome."""
        parsed_decision = create_mock_parsed_decision()
        role_aware_decision = create_mock_role_aware_decision()

        log_with_roles = construct_ai_decision_log(
            session_id="sess1",
            turn_number=1,
            parsed_decision=parsed_decision,
            raw_output="output",
            role_aware_decision=role_aware_decision,
            guard_outcome=GuardOutcome.PARTIALLY_ACCEPTED,
        )

        log_without_roles = construct_ai_decision_log(
            session_id="sess1",
            turn_number=1,
            parsed_decision=parsed_decision,
            raw_output="output",
            role_aware_decision=None,
            guard_outcome=GuardOutcome.PARTIALLY_ACCEPTED,
        )

        # guard_outcome must be identical
        assert log_with_roles.guard_outcome == log_without_roles.guard_outcome
        # validation_outcome must be identical (derived from guard_outcome)
        assert log_with_roles.validation_outcome == log_without_roles.validation_outcome

    def test_role_fields_do_not_affect_scene_transitions(self):
        """Role fields should not affect parsed_decision (which contains scene transition info)."""
        parsed_decision = create_mock_parsed_decision()
        parsed_decision.proposed_scene_id = "final_scene"
        role_aware_decision = create_mock_role_aware_decision()

        log_with_roles = construct_ai_decision_log(
            session_id="sess1",
            turn_number=1,
            parsed_decision=parsed_decision,
            raw_output="output",
            role_aware_decision=role_aware_decision,
        )

        log_without_roles = construct_ai_decision_log(
            session_id="sess1",
            turn_number=1,
            parsed_decision=parsed_decision,
            raw_output="output",
            role_aware_decision=None,
        )

        # parsed_output (canonical decision) should be identical
        assert log_with_roles.parsed_output == log_without_roles.parsed_output
        # Both should have same proposed_scene_id
        parsed_with = log_with_roles.parsed_output  # dict from model_dump()
        parsed_without = log_without_roles.parsed_output
        assert parsed_with.get("proposed_scene_id") == parsed_without.get("proposed_scene_id")

    def test_guard_outcome_remains_canonical(self):
        """guard_outcome is the sole canonical validation result, not overridden by role fields."""
        parsed_decision = create_mock_parsed_decision()
        role_aware_decision = create_mock_role_aware_decision()

        # Create logs with different guard_outcome values
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
                raw_output="output",
                role_aware_decision=role_aware_decision,
                guard_outcome=guard_outcome,
            )

            # guard_outcome must be preserved exactly as passed
            assert log.guard_outcome == guard_outcome

class TestRoleFieldCorrectness:
    """Test role field population accuracy."""

    def test_interpreter_output_has_scene_reading_and_tensions(self):
    def test_director_output_has_steering_and_direction(self):
    def test_responder_output_is_full_section(self):

class TestBackwardCompatibility:
    """Test backward compatibility with existing logging."""

    def test_legacy_decisions_append_successfully(self):
    def test_no_changes_to_existing_guard_outcome_field(self):
    def test_no_changes_to_existing_delta_models(self):
```

---

## Files Changed

| File | Action |
|---|---|
| `backend/app/runtime/ai_decision_logging.py` | CREATE — logging helper module with construct_ai_decision_log() |
| `backend/app/runtime/w2_models.py` | MODIFY — add InterpreterDiagnosticSummary, DirectorDiagnosticSummary, extend AIDecisionLog with three role fields |
| `backend/tests/runtime/test_ai_decision_logging.py` | CREATE — comprehensive test coverage for log construction and diagnostic correctness |

---

## Acceptance Criteria

- ✅ Diagnostics now expose role separation clearly (interpreter, director, responder visible in logs)
- ✅ Logs materially improve debuggability (compact summaries + full responder detail)
- ✅ Implementation sufficient for guard-path coupling in W2.4.5 (role fields available for future analysis)
- ✅ Type-based detection works (ParsedRoleAwareDecision present → role fields populated)
- ✅ Backward compatibility maintained (legacy decisions have role fields = None)
- ✅ No runtime changes (ParsedAIDecision unchanged, guard_outcome canonical)
- ✅ No W2 scope jump (diagnostics only, no parsing/normalization/guard changes)
- ✅ Boundedness preserved (diagnostic summaries keep logs coherent)

---

## Deferred (W2.4.5+)

- Guard-path coupling analysis (W2.4.5)
- Fine-grained proposal-level diagnostics (future)
- Role-structured decision tracing in UI/analytics (future)

---

## Commit Message

```
feat(w2): expose internal AI role split in decision diagnostics

- Add typed diagnostic summaries for interpreter and director output
- Preserve full responder section for diagnostic visibility
- Extend AIDecisionLog with interpreter/director/responder fields
- Populate role fields only when ParsedRoleAwareDecision is present
- Keep ParsedAIDecision as only canonical runtime decision object
- Improve debuggability without changing guard semantics
```
