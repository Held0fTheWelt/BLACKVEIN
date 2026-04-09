# W2.2.2: Field-Level Mutation Whitelist & Protected-State Rules

**Goal:** Harden AI mutation validation by enforcing an explicit deny-by-default whitelist of mutable state fields, protecting runtime/engine/session identity from AI proposals.

**Architecture:** Separate mutation policy concerns from validation plumbing. New `mutation_policy.py` defines semantic domains and path-pattern rules; `validators.py` orchestrates validation and calls policy enforcement.

**Scope:** W2.2.2 subsection only — mutation permission validation. Does not redesign state model, add UI, or introduce module-specific hacks.

---

## Problem Statement

W2.2.1 established a canonical action taxonomy (6 action types). However, **path validity does not imply mutation permission**:
- Current validation checks path syntax and entity existence only
- No protection against mutating session_id, execution_mode, event logs, or engine-owned state
- "Valid path" ≠ "allowed mutation" — the gap this work closes

W2.2.2 closes this gap by:
1. Defining which canonical state fields AI is *allowed* to mutate (whitelist)
2. Defining which fields are *protected* (deny-by-default)
3. Enforcing mutation permission in the validation pipeline, before state application

### Canonical State Structure

The `canonical_state` dict contains game-world state. Example shape:
```python
canonical_state = {
    "characters": {
        "veronique": {
            "emotional_state": 50,          # AI mutable
            "stance": 45,                   # AI mutable
            "tension": 75,                  # AI mutable
            "_internal_cache": {...},       # Protected (internal)
        }
    },
    "relationships": {
        "veronique_catherine": {
            "value": 30,                    # AI mutable
        }
    },
    "scene_state": {
        "kitchen": {
            "pressure": 60,                 # AI mutable
            "conflict": 40,                 # AI mutable
        }
    },
    "conflict_state": {
        "escalation": 70,                   # AI mutable
        "intensity": 0.85,                  # AI mutable
    },
    "metadata": {...},                      # Protected
    "runtime": {...},                       # Protected
}

---

## Design

### Semantic Field Catalog

**Allowed Domains** — AI may mutate these areas:
- `characters` — character emotional state, stance, tension
- `relationships` — relationship axis values
- `scene_state` — scene-level conflict/pressure markers
- `conflict_state` — escalation/intensity trackers

**Protected Domains** — AI may never mutate these areas:
- `metadata` — internal metadata fields
- `runtime` — execution state, mode, adapter configuration
- `system` — engine bookkeeping
- `logs` — event logs, decision logs (immutable audit trail)
- `decision` — AI decision artifacts
- `session` — session_id, created_at, module_id, module_version
- `turn` — turn_number, session_id
- `cache` — derived/computed fields
- Technical patterns: `*._*`, `*.__*`, `*_internal`, `*_derived`

### Path-Pattern Rules

**Whitelist Rules** (patterns AI may mutate, within allowed domains):
```
characters.*.emotional_state
characters.*.stance
characters.*.tension
relationships.*.value
scene_state.*.pressure
scene_state.*.conflict
conflict_state.*.escalation
conflict_state.*.intensity
```

**Blocked Rules** (patterns always protected, global):
```
*.metadata
*._*
*.__*
runtime.*
system.*
logs.*
decision.*
session.*
turn.*
cache.*
*_internal
*_derived
```

### Core Enforcement Functions

**File:** `backend/app/runtime/mutation_policy.py`

```python
class MutationPolicy:
    """Defines canonical AI mutation permission rules."""

    ALLOWED_DOMAINS = {"characters", "relationships", "scene_state", "conflict_state"}
    PROTECTED_DOMAINS = {"metadata", "runtime", "system", "logs", "session", "turn"}

    # Patterns matched using fnmatch-style (glob): * = any single path component, ? = single char
    WHITELIST_PATTERNS = [
        "characters.*.emotional_state",
        "characters.*.stance",
        "characters.*.tension",
        "relationships.*.value",
        "scene_state.*.pressure",
        "scene_state.*.conflict",
        "conflict_state.*.escalation",
        "conflict_state.*.intensity",
    ]

    # Patterns that always block mutations (checked first)
    BLOCKED_PATTERNS = [
        "metadata.*",           # All metadata fields
        "runtime.*",            # All runtime configuration
        "system.*",             # All system fields
        "logs.*",               # All event/decision logs
        "session.*",            # Session identity
        "turn.*",               # Turn metadata
        "*._*",                 # Any field starting with underscore (internal)
        "*.__*",                # Any field starting with double underscore
        "*.cache",              # Any .cache field
        "*.cached_*",           # Any .cached_* field
    ]

    @staticmethod
    def is_mutation_allowed(target_path: str) -> tuple[bool, str | None]:
        """Check if target_path is allowed to be mutated by AI.

        Algorithm (deny-by-default):
        1. Check if path matches ANY blocked pattern (fail immediately)
        2. Check if path matches ANY whitelist pattern (allow)
        3. Otherwise reject (deny by default)

        Args:
            target_path: Dot-notation path (e.g., "characters.veronique.emotional_state")

        Returns:
            (is_allowed, reason_if_blocked)
            If allowed: (True, None)
            If blocked: (False, "reason string describing which rule blocked it")
        """
        # Implementation: use fnmatch to match patterns
        # Return (True, None) if whitelisted, (False, reason) if blocked or not matched
        ...

    @staticmethod
    def get_protection_reason(target_path: str) -> str | None:
        """If path is blocked, return human-readable reason; else None."""
        ...
```

### Pattern Matching Semantics

**Pattern Format:** fnmatch-style glob patterns with dot-separated components.
- `*` = matches any single path component (not recursive)
- Example: `characters.*.emotional_state` matches `characters.veronique.emotional_state` and `characters.catherine.emotional_state`
- Each pattern is split by `.` and matched component-by-component

**Hierarchical Blocking:** Blocked patterns block all descendants.
- `session.*` blocks `session.id`, `session.created_at`, `session.id.value`, etc.
- `metadata.*` blocks all fields under metadata at any nesting depth
- Implementation: pattern is matched as-is; if `session.*` matches, it blocks the path and all longer paths with `session` as root

**Algorithm (order matters):**
1. Check blocked patterns first (fail-fast) — if ANY blocked pattern matches, reject immediately
2. Check whitelist patterns — if ANY whitelist pattern matches, allow
3. Otherwise reject (deny by default)

### Integration into Validation Pipeline

**File:** `backend/app/runtime/validators.py`

New function:
```python
def validate_mutation_permission(target_path: str) -> tuple[bool, str | None]:
    """Validate that AI is permitted to mutate the target path.

    Called after path-existence validation, before state mutation.
    Checks against MutationPolicy whitelist/blocked patterns.

    Args:
        target_path: Dot-notation path (e.g., "characters.veronique.emotional_state")

    Returns:
        (is_allowed, error_message or None)
    """
    from app.runtime.mutation_policy import MutationPolicy
    is_allowed, reason = MutationPolicy.is_mutation_allowed(target_path)
    if is_allowed:
        return True, None
    else:
        return False, f"Mutation blocked: '{target_path}' — {reason}"
```

Updated validation flow in `_validate_delta()`:
```
1. Check target field exists and is string
2. Check path format (dot-notation)
3. Check path exists in canonical_state  ← existing
4. Check mutation permission           ← NEW: validate_mutation_permission()
5. If blocked: add to rejected_deltas, record error
6. If allowed: proceed to state application
```

### Error Handling

Rejected mutations:
- Visible in `TurnExecutionResult.rejected_deltas`
- Error message: `"Mutation blocked: target_path '<path>' is protected (reason: <protection_reason>)"`
- Logged in validation outcome with explicit reason
- Audit trail preserved in `AIDecisionLog`

Example rejection:
```
target_path: "session.status"
error: "Mutation blocked: target_path 'session.status' is protected (protected domain: session)"
result: rejected_delta with explicit reason
```

### Testing Strategy

**File:** `backend/tests/runtime/test_mutation_policy.py`

#### Test Classes and Examples

**1. TestMutationPolicyWhitelist** — verify whitelisted patterns are allowed
```python
def test_characters_emotional_state_allowed():
    """characters.*.emotional_state is in whitelist."""
    assert MutationPolicy.is_mutation_allowed("characters.veronique.emotional_state") == (True, None)

def test_relationships_value_allowed():
    """relationships.*.value is in whitelist."""
    assert MutationPolicy.is_mutation_allowed("relationships.veronique_catherine.value") == (True, None)

def test_conflict_state_escalation_allowed():
    """conflict_state.*.escalation is in whitelist."""
    assert MutationPolicy.is_mutation_allowed("conflict_state.kitchen.escalation") == (True, None)
```

**2. TestMutationPolicyBlocked** — verify blocked patterns are rejected
```python
def test_session_domain_blocked():
    """session.* is in blocked patterns."""
    allowed, reason = MutationPolicy.is_mutation_allowed("session.id")
    assert not allowed
    assert "blocked" in reason.lower()

def test_internal_fields_blocked():
    """*._* pattern blocks fields starting with underscore."""
    allowed, reason = MutationPolicy.is_mutation_allowed("characters.veronique._cache")
    assert not allowed

def test_metadata_domain_blocked():
    """metadata.* is in blocked patterns."""
    allowed, reason = MutationPolicy.is_mutation_allowed("metadata.created_at")
    assert not allowed
```

**3. TestProtectedDomains** — verify protected domains cannot be mutated
```python
def test_runtime_domain_blocked():
    """runtime.* is protected."""
    assert not MutationPolicy.is_mutation_allowed("runtime.execution_mode")[0]
    assert not MutationPolicy.is_mutation_allowed("runtime.adapter_name")[0]

def test_turn_domain_blocked():
    """turn.* is protected."""
    assert not MutationPolicy.is_mutation_allowed("turn.number")[0]
    assert not MutationPolicy.is_mutation_allowed("turn.session_id")[0]

def test_logs_domain_blocked():
    """logs.* is protected."""
    assert not MutationPolicy.is_mutation_allowed("logs.events")[0]
    assert not MutationPolicy.is_mutation_allowed("logs.decision_log")[0]
```

**4. TestPermissionVsPathValidity** — path can exist but mutation still blocked
```python
def test_valid_path_blocked_mutation():
    """session.id is a valid SessionState field but mutation is blocked.

    This verifies the key principle: path validity ≠ mutation permission.
    A field can exist in canonical_state (valid path) but AI cannot mutate it.
    """
    # session.id is a valid field in canonical_state
    # but it's in the protected domain
    allowed, reason = MutationPolicy.is_mutation_allowed("session.id")
    assert not allowed
    assert "protected" in reason.lower() or "blocked" in reason.lower()
```

**5. TestIntegration** — mutations flow through full validation pipeline
```python
def test_rejected_mutation_in_result():
    """Rejected mutations appear in TurnExecutionResult.rejected_deltas.

    End-to-end: delta with blocked path → validation rejects it →
    result captures rejection with reason.
    """
    delta = ProposedStateDelta(
        target="session.status",
        next_value="ended"
    )
    # Validation calls MutationPolicy and rejects
    # Delta appears in rejected_deltas with error message

def test_allowed_mutation_in_result():
    """Allowed mutations appear in TurnExecutionResult.accepted_deltas."""
    delta = ProposedStateDelta(
        target="characters.veronique.emotional_state",
        next_value=75
    )
    # Validation calls MutationPolicy and allows
    # Delta appears in accepted_deltas
```

#### Test Coverage

- ✅ Whitelist patterns: all 8 patterns tested
- ✅ Blocked patterns: all 10 patterns tested
- ✅ Edge cases: hierarchical blocking (`session.*` blocks descendants), internal fields (`_*`), cached fields
- ✅ Permission ≠ Validity: path exists but blocked example
- ✅ Integration: rejected mutations visible in result
- ✅ Error messages: clear and actionable

---

## Implementation Plan

### Phase 1: Define Policy
1. Create `mutation_policy.py` with semantic domains and pattern rules
2. Implement pattern-matching logic (whitelist, blocked rules)
3. Add policy enforcement functions

### Phase 2: Integrate Validation
1. Add `validate_mutation_permission()` to `validators.py`
2. Call policy in `_validate_delta()` validation chain
3. Reject mutations before state application

### Phase 3: Testing
1. Write comprehensive test suite (`test_mutation_policy.py`)
2. Verify whitelist/blocked patterns work correctly
3. Verify integration with full validation pipeline
4. Ensure no regressions in existing tests

### Phase 4: Integration Verification
1. Run full test suite to ensure no regressions
2. Verify `TurnExecutionResult` captures rejected mutations
3. Verify error messages are clear and actionable

---

## Acceptance Criteria

- ✅ New `mutation_policy.py` defines canonical semantic domains
- ✅ Deny-by-default whitelist enforces mutation permission
- ✅ Protected domains cannot be mutated (session, turn, logs, engine metadata)
- ✅ Path validity is checked separately from mutation permission
- ✅ Rejected mutations are visible in validation outcomes
- ✅ Integration tests verify full pipeline works
- ✅ No regressions in existing test suite
- ✅ Implementation stays within W2.2.2 scope

---

## What's Deferred to W2.2.3+

- Role-based mutation permissions (admin vs AI)
- Module-specific mutation policies (God of Carnage custom rules)
- Dynamic policy loading/validation
- Audit logging of rejected mutations to persistent store
- UI for policy visualization
- Mutation audit trail analytics

---

## Files to Create/Modify

**Create:**
- `backend/app/runtime/mutation_policy.py` — Policy definition and enforcement
- `backend/tests/runtime/test_mutation_policy.py` — Comprehensive test suite

**Modify:**
- `backend/app/runtime/validators.py` — Integrate policy validation

---

## Commit Message

```
feat(w2): enforce field-level mutation whitelist and protected state rules

Define canonical semantic domains (characters, relationships, scene_state, conflict_state)
and enforce deny-by-default mutation permission in validation pipeline.

Protected domains (session, turn, logs, runtime, system, metadata) cannot be mutated
by AI proposals. Path validity is checked separately from mutation permission.

Rejected mutations remain visible in validation outcomes for audit trail.
```
