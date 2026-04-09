# W2.2.2: Field-Level Mutation Whitelist and Protected-State Rules

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce deny-by-default mutation permission validation so AI proposals can only mutate explicitly whitelisted story-state fields, protecting engine/runtime/session identity and internal technical state.

**Architecture:** New `mutation_policy.py` defines semantic domains, whitelist patterns, and blocked patterns using component-by-component matching. Policy is called from `validators.py` during delta validation (step 4 of 7-step pipeline). Mutation permission is checked separately from path existence.

**Tech Stack:** Python 3.10, Pydantic models, pytest for testing, fnmatch-style component matching (not full fnmatch)

---

## Task 1: Define Mutation Policy Data Structures

**Files:**
- Create: `backend/app/runtime/mutation_policy.py` (lines 1-80)

### Steps

- [ ] **Step 1: Write failing test for MutationPolicyDecision**

File: `backend/tests/runtime/test_mutation_policy.py`

```python
import pytest
from app.runtime.mutation_policy import MutationPolicyDecision

def test_mutation_policy_decision_allowed():
    """MutationPolicyDecision represents allowed mutation."""
    decision = MutationPolicyDecision(allowed=True)
    assert decision.allowed is True
    assert decision.reason_code is None
    assert decision.reason_message is None

def test_mutation_policy_decision_blocked():
    """MutationPolicyDecision represents blocked mutation."""
    decision = MutationPolicyDecision(
        allowed=False,
        reason_code="blocked_root_domain",
        reason_message="Protected domain: session"
    )
    assert decision.allowed is False
    assert decision.reason_code == "blocked_root_domain"
    assert decision.reason_message == "Protected domain: session"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/runtime/test_mutation_policy.py::test_mutation_policy_decision_allowed -xvs
```

Expected: `ModuleNotFoundError: No module named 'app.runtime.mutation_policy'`

- [ ] **Step 3: Create mutation_policy.py with MutationPolicyDecision dataclass**

File: `backend/app/runtime/mutation_policy.py`

```python
"""Field-level mutation permission policy for AI proposals.

Enforces deny-by-default whitelist of mutable story-state fields.
Protects engine-owned, runtime-owned, and internal technical state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MutationPolicyDecision:
    """Result of evaluating a path against the mutation policy.

    Attributes:
        allowed: Whether the path is allowed to be mutated by AI
        reason_code: Machine-readable reason code if blocked (e.g., "blocked_root_domain")
        reason_message: Human-readable reason message if blocked
    """

    allowed: bool
    reason_code: Optional[str] = None
    reason_message: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/runtime/test_mutation_policy.py::test_mutation_policy_decision_allowed -xvs
cd backend && python -m pytest tests/runtime/test_mutation_policy.py::test_mutation_policy_decision_blocked -xvs
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/runtime/mutation_policy.py backend/tests/runtime/test_mutation_policy.py
git commit -m "feat(w2): add MutationPolicyDecision data structure"
```

---

## Task 2: Define Canonical Domains and Patterns

**Files:**
- Modify: `backend/app/runtime/mutation_policy.py` (add lines 80-180)

### Steps

- [ ] **Step 1: Write tests for domain definitions**

Add to `backend/tests/runtime/test_mutation_policy.py`:

```python
from app.runtime.mutation_policy import MutationPolicy

class TestMutationPolicyStructure:
    """Test the policy structure and domain definitions."""

    def test_allowed_domains_defined(self):
        """Allowed domains are explicitly defined."""
        assert hasattr(MutationPolicy, 'ALLOWED_DOMAINS')
        assert MutationPolicy.ALLOWED_DOMAINS == {
            "characters", "relationships", "scene_state", "conflict_state"
        }

    def test_protected_domains_defined(self):
        """Protected domains are explicitly defined."""
        assert hasattr(MutationPolicy, 'PROTECTED_DOMAINS')
        assert MutationPolicy.PROTECTED_DOMAINS == {
            "metadata", "runtime", "system", "logs", "decision", "session", "turn", "cache"
        }

    def test_whitelist_patterns_defined(self):
        """Whitelist patterns are defined for allowed domains."""
        assert hasattr(MutationPolicy, 'WHITELIST_PATTERNS')
        assert len(MutationPolicy.WHITELIST_PATTERNS) == 8
        assert "characters.*.emotional_state" in MutationPolicy.WHITELIST_PATTERNS
        assert "conflict_state.escalation" in MutationPolicy.WHITELIST_PATTERNS

    def test_blocked_patterns_defined(self):
        """Blocked patterns prevent mutations of protected/technical fields."""
        assert hasattr(MutationPolicy, 'BLOCKED_PATTERNS')
        assert len(MutationPolicy.BLOCKED_PATTERNS) > 0
        assert "session.*" in MutationPolicy.BLOCKED_PATTERNS
        assert "*._*" in MutationPolicy.BLOCKED_PATTERNS
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/runtime/test_mutation_policy.py::TestMutationPolicyStructure -xvs
```

Expected: Multiple `AssertionError` (attributes don't exist yet)

- [ ] **Step 3: Add domain and pattern definitions to MutationPolicy**

File: `backend/app/runtime/mutation_policy.py` — add after imports:

```python
class MutationPolicy:
    """Canonical mutation permission policy for AI proposals.

    Deny-by-default: only explicitly whitelisted paths are allowed.
    Protected domains cannot be mutated under any circumstances.
    Blocked patterns are checked first and always win.
    """

    # ===== Semantic Domains =====

    ALLOWED_DOMAINS = {
        "characters",      # Character emotional state, stance, tension
        "relationships",   # Relationship axis values
        "scene_state",     # Scene-level conflict/pressure markers
        "conflict_state",  # Escalation/intensity trackers (global, not per-scene)
    }

    PROTECTED_DOMAINS = {
        "metadata",        # Internal metadata
        "runtime",         # Execution state, mode, adapter config
        "system",          # Engine bookkeeping
        "logs",            # Event/decision logs
        "decision",        # AI decision artifacts
        "session",         # Session identity (session_id, created_at, module_id)
        "turn",            # Turn metadata (turn_number, session_id)
        "cache",           # Derived/computed fields
    }

    # ===== Whitelist Patterns =====
    # Patterns allowed within allowed domains.
    # Component-by-component matching: split by ".", "*" matches one component.

    WHITELIST_PATTERNS = [
        # Characters: emotional state, stance, tension
        "characters.*.emotional_state",
        "characters.*.stance",
        "characters.*.tension",
        # Relationships: axis values
        "relationships.*.value",
        # Scene state: pressure and conflict markers
        "scene_state.*.pressure",
        "scene_state.*.conflict",
        # Conflict state: escalation and intensity (global, not per-scene)
        "conflict_state.escalation",
        "conflict_state.intensity",
    ]

    # ===== Blocked Patterns =====
    # Patterns that always block mutations (checked first).
    # Component-by-component matching.

    BLOCKED_PATTERNS = [
        # Protected root domains
        "metadata.*",
        "runtime.*",
        "system.*",
        "logs.*",
        "decision.*",
        "session.*",
        "turn.*",
        "cache.*",
        # Internal/technical fields (any nesting level)
        "*._*",            # Fields starting with underscore
        "*.__*",           # Fields starting with double underscore
        "*_internal",      # Fields ending with _internal
        "*_derived",       # Fields ending with _derived
        "*.cache",         # Any .cache field
        "*.cached_*",      # Any .cached_* field
    ]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/runtime/test_mutation_policy.py::TestMutationPolicyStructure -xvs
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/runtime/mutation_policy.py backend/tests/runtime/test_mutation_policy.py
git commit -m "feat(w2): define canonical mutation policy domains and patterns"
```

---

## Task 3: Implement Policy Evaluation Logic

**Files:**
- Modify: `backend/app/runtime/mutation_policy.py` (add lines 180-320)

### Steps

- [ ] **Step 1: Write tests for policy evaluation**

Add to `backend/tests/runtime/test_mutation_policy.py`:

```python
class TestMutationPolicyEvaluation:
    """Test the core policy evaluation logic."""

    def test_whitelisted_character_emotional_state_allowed(self):
        """characters.*.emotional_state is whitelisted."""
        decision = MutationPolicy.evaluate("characters.veronique.emotional_state")
        assert decision.allowed is True
        assert decision.reason_code is None

    def test_whitelisted_relationship_value_allowed(self):
        """relationships.*.value is whitelisted."""
        decision = MutationPolicy.evaluate("relationships.veronique_alain.value")
        assert decision.allowed is True

    def test_whitelisted_conflict_escalation_allowed(self):
        """conflict_state.escalation (global) is whitelisted."""
        decision = MutationPolicy.evaluate("conflict_state.escalation")
        assert decision.allowed is True

    def test_blocked_session_domain(self):
        """session.* is blocked."""
        decision = MutationPolicy.evaluate("session.id")
        assert decision.allowed is False
        assert decision.reason_code == "blocked_root_domain"
        assert "session" in decision.reason_message.lower()

    def test_blocked_internal_field(self):
        """*._* pattern blocks internal fields."""
        decision = MutationPolicy.evaluate("characters.veronique._cache")
        assert decision.allowed is False
        assert decision.reason_code == "blocked_internal_field"

    def test_valid_path_but_blocked_mutation(self):
        """Path exists but mutation is blocked (valid path ≠ allowed mutation)."""
        # characters is allowed domain, but secret_backstory is not whitelisted
        decision = MutationPolicy.evaluate("characters.veronique.secret_backstory")
        assert decision.allowed is False
        assert decision.reason_code == "not_whitelisted"

    def test_unknown_root_denied_by_default(self):
        """Unknown root domain denied by default."""
        decision = MutationPolicy.evaluate("unknown_domain.field")
        assert decision.allowed is False
        assert decision.reason_code == "out_of_scope_root"

    def test_conflict_state_nested_rejected(self):
        """conflict_state is global, not per-scene (conflict_state.kitchen.escalation rejected)."""
        decision = MutationPolicy.evaluate("conflict_state.kitchen.escalation")
        assert decision.allowed is False
        # Either blocked by pattern mismatch or not whitelisted
        assert decision.reason_code in ["not_whitelisted", "blocked_root_domain"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/runtime/test_mutation_policy.py::TestMutationPolicyEvaluation -xvs
```

Expected: Multiple `AttributeError` (evaluate method doesn't exist)

- [ ] **Step 3: Implement evaluate() method**

File: `backend/app/runtime/mutation_policy.py` — add to MutationPolicy class:

```python
    @staticmethod
    def evaluate(target_path: str) -> MutationPolicyDecision:
        """Evaluate whether a target path is allowed to be mutated.

        Algorithm (deny-by-default):
        1. Check if path matches ANY blocked pattern → REJECT immediately
        2. Check if path matches ANY whitelist pattern → ALLOW
        3. Otherwise → REJECT (deny by default)

        Matching: component-by-component (split by ".", "*" = one component).
        Blocked patterns checked first and always win.

        Args:
            target_path: Dot-notation path (e.g., "characters.veronique.emotional_state")

        Returns:
            MutationPolicyDecision with allowed flag and reason codes
        """
        if not target_path or not isinstance(target_path, str):
            return MutationPolicyDecision(
                allowed=False,
                reason_code="blocked_internal_field",
                reason_message="Invalid target_path: must be non-empty string"
            )

        # Split path into components
        path_parts = target_path.split(".")
        if not path_parts:
            return MutationPolicyDecision(
                allowed=False,
                reason_code="blocked_internal_field",
                reason_message="Invalid target_path: empty after split"
            )

        root_domain = path_parts[0]

        # ===== Step 1: Check Blocked Patterns (fail-fast) =====
        for pattern in MutationPolicy.BLOCKED_PATTERNS:
            if MutationPolicy._matches_pattern(target_path, pattern):
                return MutationPolicy._blocked_decision(pattern, target_path)

        # ===== Step 2: Check Whitelist Patterns =====
        for pattern in MutationPolicy.WHITELIST_PATTERNS:
            if MutationPolicy._matches_pattern(target_path, pattern):
                return MutationPolicyDecision(allowed=True)

        # ===== Step 3: Deny by Default =====
        # Check if root domain is in allowed domains (helps with error message)
        if root_domain in MutationPolicy.ALLOWED_DOMAINS:
            # Root is allowed, but leaf is not whitelisted
            return MutationPolicyDecision(
                allowed=False,
                reason_code="not_whitelisted",
                reason_message=(
                    f"Target path '{target_path}' is not in the mutation whitelist. "
                    f"Root domain '{root_domain}' is allowed, but only specific leaves are mutable."
                )
            )
        elif root_domain in MutationPolicy.PROTECTED_DOMAINS:
            # Root is explicitly protected
            return MutationPolicyDecision(
                allowed=False,
                reason_code="blocked_root_domain",
                reason_message=(
                    f"Target path '{target_path}' is in protected domain '{root_domain}'. "
                    f"Protected domains cannot be mutated by AI proposals."
                )
            )
        else:
            # Root is neither allowed nor protected - out of scope
            return MutationPolicyDecision(
                allowed=False,
                reason_code="out_of_scope_root",
                reason_message=(
                    f"Target path '{target_path}' has unknown root domain '{root_domain}'. "
                    f"Allowed domains: {sorted(MutationPolicy.ALLOWED_DOMAINS)}"
                )
            )

    @staticmethod
    def _matches_pattern(path: str, pattern: str) -> bool:
        """Check if path matches pattern using component-by-component matching.

        Matching rules:
        - Split both path and pattern by "."
        - "*" in pattern matches exactly one path component
        - All other components must match exactly
        - If pattern has fewer components than path, no match (no recursive wildcard)

        Args:
            path: Target path (e.g., "characters.veronique.emotional_state")
            pattern: Pattern (e.g., "characters.*.emotional_state")

        Returns:
            True if path matches pattern, False otherwise
        """
        path_parts = path.split(".")
        pattern_parts = pattern.split(".")

        # Pattern must have same number of components as path
        if len(pattern_parts) != len(path_parts):
            return False

        # Match component by component
        for path_comp, pattern_comp in zip(path_parts, pattern_parts):
            if pattern_comp == "*":
                # Wildcard matches any single component
                continue
            elif path_comp == pattern_comp:
                # Exact match
                continue
            else:
                # No match
                return False

        return True

    @staticmethod
    def _blocked_decision(pattern: str, path: str) -> MutationPolicyDecision:
        """Create a decision for a path blocked by a pattern.

        Determines the appropriate reason code based on which pattern blocked it.
        """
        # Categorize the reason based on pattern type
        if any(pat in pattern for pat in [".*", "system", "logs", "decision", "session", "turn", "metadata", "runtime", "cache"]):
            reason_code = "blocked_root_domain"
        elif "_*" in pattern or "__*" in pattern:
            reason_code = "blocked_internal_field"
        elif "_internal" in pattern or "_derived" in pattern or "cached" in pattern:
            reason_code = "blocked_technical_field"
        else:
            reason_code = "blocked_technical_field"

        return MutationPolicyDecision(
            allowed=False,
            reason_code=reason_code,
            reason_message=(
                f"Target path '{path}' matches blocked pattern '{pattern}' "
                f"and is protected from mutation by AI proposals."
            )
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/runtime/test_mutation_policy.py::TestMutationPolicyEvaluation -xvs
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/runtime/mutation_policy.py backend/tests/runtime/test_mutation_policy.py
git commit -m "feat(w2): implement mutation policy evaluation with component-based matching"
```

---

## Task 4: Add Comprehensive Policy Tests

**Files:**
- Modify: `backend/tests/runtime/test_mutation_policy.py` (add edge case tests)

### Steps

- [ ] **Step 1: Write edge case tests**

Add to `backend/tests/runtime/test_mutation_policy.py`:

```python
class TestMutationPolicyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_characters_metadata_blocked(self):
        """characters.veronique.metadata is blocked (metadata is protected)."""
        decision = MutationPolicy.evaluate("characters.veronique.metadata")
        assert decision.allowed is False
        # Matches *._* pattern? No. Whitelisted? No. → not_whitelisted
        assert decision.reason_code in ["not_whitelisted", "blocked_technical_field"]

    def test_characters_cached_score_blocked(self):
        """*.cached_* pattern blocks cached fields."""
        decision = MutationPolicy.evaluate("characters.veronique.cached_score")
        assert decision.allowed is False
        assert decision.reason_code == "blocked_technical_field"

    def test_characters_cache_field_blocked(self):
        """*.cache pattern blocks .cache fields."""
        decision = MutationPolicy.evaluate("characters.veronique.cache")
        assert decision.allowed is False
        assert decision.reason_code == "blocked_technical_field"

    def test_characters_dunder_field_blocked(self):
        """*.__* pattern blocks double-underscore fields."""
        decision = MutationPolicy.evaluate("characters.veronique.__internal")
        assert decision.allowed is False
        assert decision.reason_code == "blocked_internal_field"

    def test_relationships_complex_path(self):
        """relationships.*.value matches relationships with any character pair."""
        decision = MutationPolicy.evaluate("relationships.veronique_alain.value")
        assert decision.allowed is True

        decision = MutationPolicy.evaluate("relationships.catherine_serge.value")
        assert decision.allowed is True

    def test_scene_state_pressure_allowed(self):
        """scene_state.*.pressure is whitelisted."""
        decision = MutationPolicy.evaluate("scene_state.kitchen.pressure")
        assert decision.allowed is True

        decision = MutationPolicy.evaluate("scene_state.living_room.pressure")
        assert decision.allowed is True

    def test_scene_state_invalid_field_blocked(self):
        """scene_state.*.invalid_field is not whitelisted."""
        decision = MutationPolicy.evaluate("scene_state.kitchen.invalid_field")
        assert decision.allowed is False
        assert decision.reason_code == "not_whitelisted"

    def test_multiple_component_underscores(self):
        """Fields with underscores in the middle (like emotion_state) are ok if whitelisted."""
        # emotional_state is whitelisted, so emotion_state with underscore is ok
        decision = MutationPolicy.evaluate("characters.veronique.emotional_state")
        assert decision.allowed is True

    def test_blocked_rules_win_over_intent(self):
        """If something matches a blocked pattern, it's rejected even if root is allowed."""
        # Example: if somehow a whitelisted leaf had an underscore (hypothetically)
        # the blocked pattern would still apply
        decision = MutationPolicy.evaluate("characters.veronique._secret")
        assert decision.allowed is False
        assert "blocked" in decision.reason_message.lower() or "internal" in decision.reason_message.lower()

    def test_empty_path_rejected(self):
        """Empty path is rejected."""
        decision = MutationPolicy.evaluate("")
        assert decision.allowed is False

    def test_none_path_rejected(self):
        """None path is rejected."""
        decision = MutationPolicy.evaluate(None)
        assert decision.allowed is False

    def test_path_with_empty_components(self):
        """Path with empty components (like a..b) is handled gracefully."""
        # This depends on implementation, but should reject
        decision = MutationPolicy.evaluate("characters..emotional_state")
        # May match "*" or be rejected as malformed - implementation dependent
        # Just verify it's handled without exception
        assert isinstance(decision, MutationPolicyDecision)
```

- [ ] **Step 2: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/runtime/test_mutation_policy.py::TestMutationPolicyEdgeCases -xvs
```

Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/tests/runtime/test_mutation_policy.py
git commit -m "test(w2): add comprehensive edge case tests for mutation policy"
```

---

## Task 5: Integrate Mutation Policy into Validators

**Files:**
- Modify: `backend/app/runtime/validators.py` (add integration in _validate_delta)

### Steps

- [ ] **Step 1: Write test for validator integration**

Add to `backend/tests/runtime/test_mutation_policy.py`:

```python
class TestValidatorsIntegration:
    """Test that mutation policy is integrated into the validation pipeline."""

    def test_validate_delta_rejects_blocked_path(self):
        """_validate_delta rejects paths that fail mutation permission check."""
        from app.runtime.turn_executor import ProposedStateDelta
        from app.runtime.validators import _validate_delta

        # Create a delta with blocked path
        delta = ProposedStateDelta(
            target="session.id",
            next_value="new_session"
        )

        # Mock session and module (minimal)
        class MockModule:
            characters = {}
            relationship_axes = {}
            scene_phases = {}
            phase_transitions = {}

        class MockSession:
            pass

        # Validate - should have error about mutation permission
        errors = _validate_delta(delta, MockSession(), MockModule())
        assert len(errors) > 0
        assert any("mutation" in e.lower() or "blocked" in e.lower() or "protected" in e.lower() for e in errors)

    def test_validate_delta_accepts_allowed_path(self):
        """_validate_delta accepts paths that pass mutation permission check."""
        from app.runtime.turn_executor import ProposedStateDelta
        from app.runtime.validators import _validate_delta

        # Create a delta with allowed path
        delta = ProposedStateDelta(
            target="characters.veronique.emotional_state",
            next_value=75
        )

        class MockModule:
            characters = {"veronique": {}}
            relationship_axes = {}
            scene_phases = {}
            phase_transitions = {}

        class MockSession:
            pass

        # Validate - should have no errors (path/permission valid)
        errors = _validate_delta(delta, MockSession(), MockModule())
        # May have other validation errors, but not mutation permission error
        mutation_errors = [e for e in errors if "mutation" in e.lower() or "blocked" in e.lower()]
        assert len(mutation_errors) == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/runtime/test_mutation_policy.py::TestValidatorsIntegration -xvs
```

Expected: Tests fail (mutation policy not yet integrated)

- [ ] **Step 3: Add mutation permission validation to _validate_delta**

File: `backend/app/runtime/validators.py` — modify `_validate_delta()` function:

Find the section that validates the delta (around lines 201-250). After path existence validation, add:

```python
    # Step 4: Check mutation permission (new in W2.2.2)
    # ===================================================
    from app.runtime.mutation_policy import MutationPolicy

    policy_decision = MutationPolicy.evaluate(target)
    if not policy_decision.allowed:
        errors.append(
            f"Mutation blocked: target '{target}' — {policy_decision.reason_message} "
            f"(reason code: {policy_decision.reason_code})"
        )
        return errors
```

Insert this after the path-existence check (after checking _entity_exists) but before the numeric validation.

Complete updated section (lines ~200-260):

```python
def _validate_delta(delta: Any, session: Any, module: Any) -> list[str]:
    """Validate a single proposed state delta.

    Args:
        delta: ProposedStateDelta to validate.
        session: The current SessionState.
        module: The ContentModule.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    # Step 1: Check target field exists and is string
    if not hasattr(delta, "target"):
        errors.append("Delta missing 'target' field")
        return errors

    target = delta.target
    if not isinstance(target, str):
        errors.append(f"Delta target must be string, got {type(target).__name__}")
        return errors

    # Step 2: Check path format (dot-notation)
    parts = target.split(".")
    if not parts or len(parts) < 2:
        errors.append(f"Invalid target path format: {target}")
        return errors

    # Step 3: Check if entity exists in module
    entity_type = parts[0]
    if entity_type == "characters":
        entity_id = parts[1] if len(parts) > 1 else None
        if entity_id and not _entity_exists(entity_id, module.characters):
            errors.append(f"Unknown character: {entity_id}")
    elif entity_type == "relationships":
        entity_id = parts[1] if len(parts) > 1 else None
        if entity_id and not _entity_exists(entity_id, module.relationship_axes):
            errors.append(f"Unknown relationship axis: {entity_id}")
    elif entity_type not in ["metadata", "scene", "scene_state", "conflict_state", "runtime", "system", "logs", "decision", "session", "turn", "cache"]:
        errors.append(f"Unknown entity type in target: {entity_type}")

    # Step 4: Check mutation permission (W2.2.2)
    # =========================================
    from app.runtime.mutation_policy import MutationPolicy

    policy_decision = MutationPolicy.evaluate(target)
    if not policy_decision.allowed:
        errors.append(
            f"Mutation blocked: target '{target}' — {policy_decision.reason_message} "
            f"(reason: {policy_decision.reason_code})"
        )
        return errors

    # Step 5: Validate next_value if present
    if hasattr(delta, "next_value") and delta.next_value is not None:
        if isinstance(delta.next_value, (int, float)):
            if not (0 <= delta.next_value <= 100):
                errors.append(
                    f"Numeric delta values must be 0-100, got {delta.next_value}"
                )

    return errors
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/runtime/test_mutation_policy.py::TestValidatorsIntegration -xvs
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/runtime/validators.py backend/tests/runtime/test_mutation_policy.py
git commit -m "feat(w2): integrate mutation policy into delta validation pipeline"
```

---

## Task 6: Run Full Test Suite and Verify No Regressions

**Files:**
- No file changes; verification only

### Steps

- [ ] **Step 1: Run mutation policy tests**

```bash
cd backend && python -m pytest tests/runtime/test_mutation_policy.py -v
```

Expected: All mutation policy tests pass (30+ tests)

- [ ] **Step 2: Run runtime tests to check for regressions**

```bash
cd backend && python -m pytest tests/runtime/ -v
```

Expected: All runtime tests pass, including existing tests

- [ ] **Step 3: Run full backend test suite**

```bash
cd backend && python -m pytest tests/ -x
```

Expected: No failures introduced by mutation policy changes

- [ ] **Step 4: Commit (document successful verification)**

```bash
git add -A && git commit -m "chore(w2): verify W2.2.2 implementation with full test suite"
```

---

## Verification Checklist

- ✅ `mutation_policy.py` created with MutationPolicyDecision and MutationPolicy
- ✅ Canonical domains defined (allowed, protected)
- ✅ Whitelist and blocked patterns defined and enforced
- ✅ Component-by-component pattern matching implemented
- ✅ Policy integration in `validators.py` (step 4 of validation pipeline)
- ✅ Comprehensive tests covering all scenarios
- ✅ Edge cases tested (hierarchical blocking, internal fields, out-of-scope roots)
- ✅ No regressions in existing test suite
- ✅ W2.2.2 scope maintained (no scope creep)

---

## Files Modified/Created

| File | Change | Why |
|------|--------|-----|
| `backend/app/runtime/mutation_policy.py` | Create | Canonical mutation policy definition and enforcement |
| `backend/app/runtime/validators.py` | Modify | Integrate mutation permission check (step 4) into validation pipeline |
| `backend/tests/runtime/test_mutation_policy.py` | Create | Comprehensive test suite for policy and integration |

---

## Deferred to W2.2.3+

- Role-based mutation permissions (admin vs AI)
- Module-specific mutation policies
- Dynamic policy loading/configuration
- Mutation audit logging to persistent store
- Policy visualization in UI
- Analytics on rejected mutations
