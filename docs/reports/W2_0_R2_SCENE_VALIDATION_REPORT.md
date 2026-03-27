# Repair Report: W2.0-R2 Harden Canonical Scene Transition Validation

**Version**: 0.1.0
**Date**: 2026-03-27
**Status**: ✅ COMPLETE — Scene validation is now graph-aware

---

## Executive Summary

W2.0-R2 hardens scene transition validation so proposed scene movement is only accepted when the target is **reachable** from the current canonical scene under module-defined transition rules.

**Previous behavior**: Existence-only validation (target scene exists in module? → accept)
**New behavior**: Reachability validation (target reachable from current via allowed transitions? → accept)

**Tests**: 5 new focused tests verify all scenarios (valid transitions, illegal jumps, unknown scenes, self-transitions, context-dependent validation).
**Result**: 135/135 tests passing (130 existing + 5 new).

---

## Problem Statement

The validator was checking only if a proposed target scene exists in the module, not whether it's legally reachable from the current scene:

```python
# Old validation (insufficient)
def _validate_scene_transition(scene_id: str, session: Any, module: Any) -> list[str]:
    errors = []
    if not _entity_exists(scene_id, module.scene_phases):
        errors.append(f"Unknown scene/phase: {scene_id}")
    return errors
```

This allowed:
- ❌ Illegal jumps (e.g., phase_1 → phase_3 when only phase_1 → phase_2 is defined)
- ❌ Bypassing the transition graph
- ❌ Violating module-defined narrative structure

---

## Solution

### Enhanced Scene Transition Validation

**File**: `backend/app/runtime/validators.py:171-221`

**New logic** (graph-aware):

1. **Target existence check** — target scene must exist in module
2. **Current scene validity** — current scene must exist and be valid
3. **Self-transition check** — same scene is always allowed (no movement required)
4. **Reachability check** — NEW: target must be reachable via module transitions
   - Search module.phase_transitions for transitions FROM current scene
   - Check if any transition goes TO target scene
   - Verify target is valid (exists in module)

```python
# New validation (graph-aware)
def _validate_scene_transition(scene_id, session, module):
    errors = []

    # Step 1: Target exists?
    if not _entity_exists(scene_id, module.scene_phases):
        errors.append(f"Unknown scene/phase: {scene_id}")
        return errors

    # Step 2: Current scene valid?
    current_scene_id = session.current_scene_id
    if not _entity_exists(current_scene_id, module.scene_phases):
        errors.append(f"Current scene '{current_scene_id}' not in module")
        return errors

    # Step 3: Self-transition? (always allowed)
    if scene_id == current_scene_id:
        return errors

    # Step 4: Reachable via transitions? (NEW)
    reachable = False
    for transition_id, transition in module.phase_transitions.items():
        if transition.from_phase == current_scene_id:
            if transition.to_phase == scene_id:
                if _entity_exists(transition.to_phase, module.scene_phases):
                    reachable = True
                    break

    if not reachable:
        errors.append(
            f"Scene '{scene_id}' is not reachable from current scene '{current_scene_id}'"
        )

    return errors
```

**Key behaviors**:

| Scenario | Old Behavior | New Behavior |
|----------|-------------|--------------|
| Valid transition (phase_1 → phase_2) | Accept | Accept ✓ |
| Illegal jump (phase_1 → phase_3, no direct transition) | Accept ❌ | Reject ✓ |
| Unknown scene (doesn't exist in module) | Reject | Reject ✓ |
| Self-transition (stay in phase_1) | Accept | Accept ✓ |
| Context-dependent (phase_1 can't reach scene_c, phase_2 can) | Ignores context ❌ | Respects context ✓ |

---

## Test Coverage

### New Tests Added

**File**: `backend/tests/runtime/test_turn_executor.py` (new class: `TestSceneReachabilityValidation`)

| Test | Purpose | Validates |
|------|---------|-----------|
| `test_validate_reachable_scene_transition_accepted` | Valid reachable scene | phase_1 → phase_2 accepted (God of Carnage has this transition) |
| `test_validate_unreachable_known_scene_rejected` | Known but unreachable scene | phase_1 → phase_3 rejected (no direct transition) |
| `test_validate_unknown_scene_rejected` | Non-existent scene | Proposing unknown_scene rejected |
| `test_validate_self_transition_allowed` | Self-transition | Staying in phase_1 allowed (context-independent) |
| `test_validate_scene_context_matters` | Context-dependent validation | Custom graph: scene_a→b, b→c shows a can't reach c, b can |

**Test Results**: 5/5 PASSED

### Regression Testing

All existing tests pass without modification (130/130):
- 27 W2.0.1 runtime model tests
- 22 W2.0.2 session start tests
- 48 W2.0.3 turn executor tests
- 19 W2.0.4 event logging tests
- 10 W2.0.5 next situation tests
- 4 W2.0-R1 failure path tests

**Total**: 135/135 PASSED (130 existing + 5 new)

---

## Canonical Rule: Scene Reachability

**The new canonical rule for scene movement validation**:

> A proposed scene transition is valid if and only if:
> 1. Target scene exists in module.scene_phases
> 2. Current scene exists in module.scene_phases
> 3. Target == Current (self-transition), OR
> 4. ∃ transition ∈ module.phase_transitions where from_phase == current AND to_phase == target

This rule is:
- **Module-driven**: Reads transition rules from content module, not hardcoded
- **Graph-aware**: Respects the scenario's defined transition graph
- **Context-sensitive**: Same scene proposal has different validity depending on current position
- **Generic**: Works for any content module (God of Carnage, custom scenarios, etc.)

---

## Module Contract Implications

### God of Carnage Example

```
Transitions defined in module:
  phase_1 → phase_2
  phase_2 → phase_3

Valid scenes from phase_1: [phase_1 (self), phase_2]
Valid scenes from phase_2: [phase_2 (self), phase_3]
Valid scenes from phase_3: [phase_3 (self)]
```

The validator now enforces this graph, rejecting:
- phase_1 → phase_3 (no direct transition)
- phase_2 → phase_1 (backward jump, not defined)
- Any scene → unknown_scene

---

## Design Decisions

| Decision | Rationale | Consequence |
|----------|-----------|-------------|
| Graph-aware validation, not existence-only | Transition rules are explicitly defined; must be enforced | Illegal jumps are blocked |
| Current scene must be valid in module | Can't validate reachability from invalid state | Safety: prevents cascading errors |
| Self-transitions allowed (same scene) | Staying in current scene is always valid | Simplifies logic: no transition required for self |
| Reachability = direct transition | W2.0-R2 scope: single-hop, not pathfinding | Multi-hop paths deferred to W2.1+ coordinator |
| Early return on missing target | Avoid checking reachability for non-existent targets | Cleaner error messages |

---

## Deferred to W2.0.6+

| Feature | Reason | Phase |
|---------|--------|-------|
| Multi-hop pathfinding | W2.0-R2 validates direct transitions only | W2.1 session coordinator |
| Conditional transitions | Requires evaluating trigger_conditions on transitions | W2.1+ decision logic |
| Dynamic transition rules | Rules loaded at runtime based on state | W2.2+ content loading |
| Transition cost/weight | For optimal path selection | W2.2+ pathfinding |

---

## Verification

```bash
PYTHONPATH=backend python -m pytest backend/tests/runtime/ -v
# Result: 135 PASSED
```

**Breakdown**:
- 27 W2.0.1 tests (unchanged)
- 22 W2.0.2 tests (unchanged)
- 48 W2.0.3 tests (unchanged)
- 19 W2.0.4 tests (unchanged)
- 10 W2.0.5 tests (unchanged)
- 4 W2.0-R1 tests (unchanged)
- 5 W2.0-R2 tests (new)

---

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `backend/app/runtime/validators.py` | Enhanced `_validate_scene_transition` function | +35 (new logic), -1 (old check removed), net +34 |
| `backend/tests/runtime/test_turn_executor.py` | Add TestSceneReachabilityValidation class (5 tests) | +150 |

**Total**: 2 files modified, 150 new test lines, 34 code lines changed

---

## Acceptance Criteria Met

✅ Runtime no longer accepts illegal scene jumps
✅ Scene validation is graph-aware (not existence-only)
✅ Reachability validated against module transitions
✅ Invalid transitions rejected explicitly
✅ Generic path maintained (no God of Carnage hardcoding)
✅ All scenario types work correctly
✅ No W2 scope jump occurred
✅ 135/135 tests passing

---

## Next Steps

W2.0-R2 completes scene transition hardening. The next phases are:

- **W2.1**: Session coordinator orchestrates turn execution and applies next-situation logic
- **W2.1+**: Handle conditional transitions (trigger_conditions evaluation)
- **W2.2+**: Implement multi-hop pathfinding for complex narratives

---

**Commit**: `fix(w2): harden canonical scene transition validation`
**Status**: ✅ COMPLETE

