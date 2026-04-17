---
name: turn-execution-verification
description: Use when testing turn execution under production conditions, validating seams between proposal-validation-commit-visibility, verifying continuity carry-forward at scale, or diagnosing turn graph failures
---

# Turn Execution Verification

## Overview

Verify turn execution through complete seams: proposal generation, validation, commit application, visibility rendering. Tests turn graph end-to-end with diverse scenarios, captures diagnostics, validates state transitions.

## When to Use

Trigger when:
- Testing turn execution after code changes
- Validating new validation rules work correctly
- Verifying commit effects apply correctly
- Testing continuity carry-forward at scale
- Diagnosing mysterious turn failures

**When NOT to use:**
- Single validation rule testing (test in isolation first)
- Unit testing individual functions (use pytest)
- Debugging backend unrelated to turns (use systematic-debugging)

## Structured Approach

### Phase 1: Test Scenario Builder

Generate 5-10 diverse turn scenarios covering:

```
SCENARIO 1: Simple Intent (Happy Path)
  Input: Simple action (e.g., "dragon moves west")
  Expected: Proposal valid → Validation passes → Commit applies → Visibility renders
  Assertions: state_before != state_after, action_visible_to_players

SCENARIO 2: Multi-Intent
  Input: Multiple intents (e.g., "cast spell AND move AND speak")
  Expected: All intents validated, committed in order, visible correctly
  Assertions: All intents in final state, order preserved

SCENARIO 3: Authority Conflict
  Input: Action violates content authority (e.g., character does impossible thing)
  Expected: Proposal valid → Validation FAILS (authority constraint)
  Assertions: Turn rejected before commit, state unchanged

SCENARIO 4: Continuity Test
  Input: Two turns in sequence (turn N, then turn N+1)
  Expected: Turn N state carries forward to turn N+1 initialization
  Assertions: N+1 sees state from N, no reset or drift

SCENARIO 5: Edge Case (Empty Action)
  Input: Empty action string
  Expected: Proposal valid → Validation FAILs (empty constraint) OR generates no-op
  Assertions: Either rejected or committed as no-op, visible correctly

SCENARIO 6: Error Case (Invalid Input)
  Input: Malformed action (null, garbage, oversized)
  Expected: Proposal FAILS with clear error
  Assertions: Error caught early, no state corruption

SCENARIO 7: Rendering Edge Case
  Input: Action that generates complex render output
  Expected: Render produces valid visible text, no corruption
  Assertions: Render output is sensible, parseable

SCENARIO 8: State Consistency
  Input: Turn that modifies multiple state fields
  Expected: All fields updated atomically, no partial state
  Assertions: Before/after state complete, no orphaned fields
```

### Phase 2: Execution Runner

Execute each scenario through turn graph:

```python
for scenario in test_scenarios:
  # PHASE 1: PROPOSAL
  try:
    proposal = turn_graph.generate_proposal(scenario.input)
    assert proposal.valid, f"Proposal generation failed for {scenario.name}"
    capture_diagnostic("proposal_output", proposal)
  except Exception as e:
    capture_diagnostic("proposal_error", e)
    mark_scenario_failed(scenario.name, "proposal")
    continue
  
  # PHASE 2: VALIDATION
  try:
    validation_result = turn_graph.validate(proposal)
    capture_diagnostic("validation_result", validation_result)
    if validation_result.passes != scenario.expect_validation_pass:
      mark_scenario_failed(scenario.name, "validation_mismatch")
  except Exception as e:
    capture_diagnostic("validation_error", e)
    mark_scenario_failed(scenario.name, "validation")
    continue
  
  # PHASE 3: COMMIT (if validation passed)
  if validation_result.passes:
    try:
      state_before = capture_state(turn_graph.world_state)
      turn_graph.commit(proposal)
      state_after = capture_state(turn_graph.world_state)
      capture_diagnostic("state_transition", {'before': state_before, 'after': state_after})
      assert state_before != state_after, "State unchanged after commit"
    except Exception as e:
      capture_diagnostic("commit_error", e)
      mark_scenario_failed(scenario.name, "commit")
      continue
  
  # PHASE 4: VISIBILITY (render)
  try:
    visible_output = turn_graph.render_visible(scenario.actor_id)
    capture_diagnostic("visibility_output", visible_output)
    assert scenario.input in visible_output or scenario.expect_visible_representation in visible_output, \
      f"Action not visible in output for {scenario.name}"
  except Exception as e:
    capture_diagnostic("visibility_error", e)
    mark_scenario_failed(scenario.name, "visibility")
    continue
  
  mark_scenario_passed(scenario.name)
```

### Phase 3: Seam Verification

Verify each seam produces expected outputs:

| Seam | Verification |
|------|--------------|
| **Proposal → Validation** | Validation receives valid proposal format? Invalid proposals rejected? |
| **Validation → Commit** | Passing validations can commit? Failing validations block commit? |
| **Commit → Visibility** | Committed state visible to players? Visibility reflects committed changes? |
| **Visibility → Continuity** | Current visibility feeds into next turn proposal? State carries forward? |

### Phase 4: Evidence Collection

Capture for each scenario:
- Scenario name, input, expected outcome
- Proposal output (success/failure, format)
- Validation result (pass/fail, reason if fail)
- State transition (before → after snapshot)
- Visibility output (rendered text)
- Any errors/exceptions with full traceback
- Timing (how long did each phase take)

### Phase 5: Report

Generate test report:

```
TURN EXECUTION TEST REPORT
==========================

Scenarios run: 8
Passed: 7
Failed: 1

RESULTS BY SCENARIO:
  ✓ Scenario 1: Simple Intent (0.34s)
  ✓ Scenario 2: Multi-Intent (0.41s)
  ✓ Scenario 3: Authority Conflict (0.28s)
  ✗ Scenario 4: Continuity Test (FAILED at continuity carry-forward)
  ✓ Scenario 5: Edge Case Empty (0.19s)
  ✓ Scenario 6: Error Case Invalid (0.22s)
  ✓ Scenario 7: Rendering Edge Case (0.38s)
  ✓ Scenario 8: State Consistency (0.35s)

FAILURE DETAILS:
  Scenario 4: Continuity Test
  Error: Turn N+1 state missing field 'player_position' from turn N
  Location: turn_graph.py :: initialize_turn_state() line 312
  Evidence: state_before = {player_position: (10,20)}, state_after = {player_position: None}

SEAM VERIFICATION:
  ✓ Proposal → Validation: All seams correct
  ✓ Validation → Commit: All seams correct
  ✓ Commit → Visibility: All seams correct
  ✗ Visibility → Continuity: Carry-forward missing field

DIAGNOSTICS:
  Total execution time: 2.17s
  Average seam latency: 0.27s per turn
  State corruption incidents: 1
```

## Required Inputs

- Turn graph implementation (turn_graph.py)
- World state model (world_state.py)
- Validation engine
- Render/visibility functions
- Test fixtures (test_user, game_state, etc.)
- Expected validation rules and constraints

## Outputs

**Turn Execution Test Report (Markdown + JSON):**
- Scenarios run, passed/failed count
- Per-scenario results with diagnostics
- Seam verification checklist (all seams OK?)
- Failure analysis (which seams failed, why)
- Timing metrics and diagnostics bundle

## Example Usage

**Scenario:** Testing turn execution after validation engine changes

You:
1. Build scenarios: 8 diverse cases (simple, multi-intent, error, edge cases)
2. Execute: Run each through proposal→validation→commit→visibility
3. Verify seams: Check each transition works correctly
4. Collect evidence: Capture state transitions, visibility output, errors
5. Report: "8 scenarios, 7 passed, 1 failed. Failure: continuity carry-forward missing 'player_position' field. Location: turn_graph.py:312. Recommended fix: update initialize_turn_state() to preserve all fields."

## Related Project Docs

- backend/world_engine/turn_graph.py (turn execution)
- backend/world_engine/world_state.py (state model)
- CANONICAL_TURN_CONTRACT_GOC.md (turn model)
- backend/tests/conftest.py (test fixtures)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Testing proposal in isolation (misses seam failures) | Always test full flow: proposal → validation → commit → visibility |
| Forgetting error scenarios (only test happy path) | Include at least 2 error cases in scenarios |
| Not capturing state transitions (can't debug failures) | Always snapshot state before/after commit |
| Missing continuity test (carry-forward breaks silently) | Always test turn N → turn N+1 sequence |
| Unclear failure diagnostics (hard to debug) | Capture full traceback, state snapshots, timing |

## Real-World Impact

Catches turn execution bugs before production. Verifies seams work correctly (proposal, validation, commit, visibility all together). Validates continuity carry-forward. Provides clear diagnostics for failures.
