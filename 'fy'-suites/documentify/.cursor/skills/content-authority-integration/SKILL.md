---
name: content-authority-integration
description: Use when integrating YAML content authority (God of Carnage builtin roles) into turn execution, testing authority conflict detection, verifying YAML module loads correctly, or ensuring content authority flows through turn graph
---

# Content Authority Integration

## Overview

Systematically integrate YAML content authority (God of Carnage builtin roles, relationships, attributes) into turn execution. Ensures YAML authority is consulted at all decision points, conflicts detected correctly, and YAML definitions override builtins as intended.

## When to Use

Trigger when:
- Integrating YAML authority module into turn graph
- Testing builtin vs YAML conflict detection
- Verifying YAML module loads and caches correctly
- Checking turn validation uses YAML authority
- Testing commit effects respect content authority
- Ensuring visibility renders content authority correctly

**When NOT to use:**
- Creating new YAML authority definitions (requires content design)
- Debugging single rule failure (test in isolation first)
- Modifying YAML schema (requires architecture review)

## Structured Approach

### Phase 1: Authority Mapping

Identify all YAML authority points in system:

```
YAML AUTHORITY SOURCES:
  1. builtin/roles.yaml
     - Defines: God of Carnage roles (deity, shaman, warrior, etc.)
     - Authority over: Character type, abilities, restrictions
  
  2. builtin/relationships.yaml
     - Defines: Allowed relationships (god-mortal, enemy, ally, etc.)
     - Authority over: Relationship creation, modification
  
  3. builtin/attributes.yaml
     - Defines: Character attributes (strength, wisdom, charisma, etc.)
     - Authority over: Attribute validation, ranges, mutations
  
  4. builtin/vocabulary.yaml
     - Defines: Dramatic vocabulary set (allowed action words)
     - Authority over: Action proposal validation
  
  5. builtin/scenes.yaml
     - Defines: Scene templates and rules
     - Authority over: Scene transitions, nesting
```

For each authority source, map to turn graph integration points:

```
INTEGRATION POINT 1: Proposal Generation
  - Action: User proposes action with character
  - Authority check: Is character_role in allowed roles? (check builtin/roles.yaml)
  - Use YAML? YES - validate proposed action against role restrictions

INTEGRATION POINT 2: Validation
  - Action: Validate proposed action
  - Authority check: Does action respect relationships? (check builtin/relationships.yaml)
  - Use YAML? YES - reject if action violates relationship authority

INTEGRATION POINT 3: Commit Effects
  - Action: Apply state changes from validated turn
  - Authority check: Are attribute changes within allowed ranges? (check builtin/attributes.yaml)
  - Use YAML? YES - clamp/reject if changes exceed authority limits

INTEGRATION POINT 4: Visibility Rendering
  - Action: Render turn result to players
  - Authority check: Is vocabulary in approved set? (check builtin/vocabulary.yaml)
  - Use YAML? YES - sanitize or reject rendering if vocabulary not approved
```

### Phase 2: Integration Checklist

For each integration point:

| Point | Question | Check |
|-------|----------|-------|
| **Proposal Gen** | Does code load YAML authority? | Verify builtin/roles.yaml loaded in proposal_generator |
| | Is character role validated? | Check proposal rejects invalid roles |
| | Does code handle YAML missing? | Test fallback if YAML file missing |
| **Validation** | Does validation consult relationships? | Check builtin/relationships.yaml consulted |
| | Does validation detect conflicts? | Test conflict when action violates relationship |
| | Are errors clear? | Verify error messages cite authority conflict |
| **Commit** | Does commit check attributes? | Check builtin/attributes.yaml consulted |
| | Are mutations constrained? | Test attribute change clamped to authority limits |
| | Is atomicity preserved? | Verify all attributes updated together |
| **Visibility** | Does rendering use vocabulary? | Check builtin/vocabulary.yaml consulted |
| | Are non-approved words filtered? | Test vocabulary validation in render |
| | Is output readable? | Verify filtered output is sensible |

### Phase 3: Conflict Detection Design

Design logic for "YAML vs builtin" conflicts:

```
CONFLICT SCENARIO 1: Character Role in Builtin But Not in YAML
  Builtin says: "warrior" is valid role
  YAML says: "warrior" not defined (doesn't exist)
  Resolution: YAML wins (newer definition beats builtin)
  Action: Reject character creation with "warrior" role

CONFLICT SCENARIO 2: Relationship in YAML Contradicts Builtin
  Builtin says: gods can marry mortals
  YAML says: gods cannot marry mortals
  Resolution: YAML wins (overrides builtin)
  Action: Reject god-mortal marriage proposal

CONFLICT SCENARIO 3: Attribute Range Conflict
  Builtin says: strength ranges 1-10
  YAML says: strength ranges 1-20 (extended)
  Resolution: YAML wins (newer limits apply)
  Action: Allow strength values up to 20 per YAML

CONFLICT PRECEDENCE (from highest to lowest):
  1. YAML authority (explicitly defined in YAML)
  2. Builtin authority (default if YAML not present)
  3. Code defaults (fallback if both missing)
```

### Phase 4: Test Scenarios

Generate test scenarios for authority integration:

```
SCENARIO 1: YAML Role Override
  Setup: Create character with role "warrior" in YAML
  Test: Proposal generator loads YAML, accepts "warrior"
  Expected: Proposal valid with "warrior" role
  Assertion: YAML authority applied

SCENARIO 2: YAML Relationship Conflict
  Setup: YAML forbids god-mortal marriage
  Test: Proposal attempts to create god-mortal relationship
  Expected: Validation fails with conflict error
  Assertion: YAML authority prevented invalid relationship

SCENARIO 3: YAML Attribute Range
  Setup: YAML extends strength range to 1-20
  Test: Commit tries to set strength=25 (exceeds YAML limit)
  Expected: Commit rejects or clamps to 20
  Assertion: YAML attribute limits enforced

SCENARIO 4: Missing YAML Fallback
  Setup: YAML file missing or empty
  Test: Proposal uses builtin authority
  Expected: Builtin defaults apply
  Assertion: Graceful fallback if YAML missing

SCENARIO 5: Vocabulary Authority
  Setup: YAML restricts vocabulary to approved set
  Test: Action uses non-approved word
  Expected: Visibility filters or rejects word
  Assertion: Vocabulary authority enforced
```

### Phase 5: Implementation Plan

Document code changes needed:

```
FILE: backend/world_engine/authority_loader.py (NEW)
  - Purpose: Load YAML authority files on startup
  - Functions:
    - load_authority(authority_type) → dict
    - cache_authority(data) → None
    - get_authority(authority_type) → cached dict
  - Error handling: Log if files missing, return empty dict

FILE: backend/world_engine/turn_graph.py (MODIFY)
  - Function: generate_proposal()
    - Add: authority = load_authority('roles')
    - Add: validate(character.role in authority['roles'])
  
  - Function: validate()
    - Add: relationship_authority = load_authority('relationships')
    - Add: validate(relationship in relationship_authority)
  
  - Function: commit()
    - Add: attribute_authority = load_authority('attributes')
    - Add: clamp_attributes(attributes, attribute_authority)
  
  - Function: render_visible()
    - Add: vocabulary_authority = load_authority('vocabulary')
    - Add: filter_vocabulary(output, vocabulary_authority)

FILE: backend/tests/test_authority_integration.py (NEW)
  - Test 5 scenarios above
  - Assert authority loaded correctly
  - Assert conflicts detected
  - Assert fallback works
```

## Required Inputs

- YAML authority files (builtin/roles.yaml, relationships.yaml, etc.)
- Turn graph implementation (turn_graph.py)
- Current proposal/validation/commit logic
- Authority loader infrastructure (if exists)
- Test fixtures and harness

## Outputs

**Three deliverables:**

1. **Authority Integration Map** (Markdown):
   - Authority sources and definitions
   - Integration points in turn graph
   - Conflict resolution policy

2. **Conflict Detection Policy** (Markdown):
   - What constitutes a conflict
   - Precedence rules (YAML > builtin > defaults)
   - Resolution logic

3. **Test Scenarios & Implementation Plan** (Markdown + Python):
   - 5+ test scenarios covering integration
   - Code locations needing changes
   - Scaffolding for new files

## Example Usage

**Scenario:** Integrating YAML role authority into turn graph

You:
1. Map authority: Identify that proposal generation must check YAML roles
2. Design conflicts: Decide YAML role definitions override builtins
3. Test scenarios: Generate case where YAML role works, builtin doesn't
4. Implementation: Map turn_graph.generate_proposal() to load_authority('roles')
5. Deliver: Map + conflict policy + scenarios + code changes needed

## Related Project Docs

- builtin/roles.yaml, relationships.yaml, attributes.yaml (authority sources)
- CANONICAL_TURN_CONTRACT_GOC.md (turn model)
- backend/world_engine/turn_graph.py (integration points)
- backend/tests/ (test patterns)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Forgot to map all integration points | Create checklist: proposal, validation, commit, visibility |
| YAML authority not consulted (code ignores YAML) | Verify code calls load_authority() at each point |
| Conflict resolution unclear (YAML vs builtin ambiguous) | Document precedence rule explicitly |
| Missing YAML fallback (crashes if file missing) | Always provide builtin defaults as fallback |
| Tests only happy path (don't test conflicts) | Include scenarios where YAML overrides builtin |

## Real-World Impact

Enables God of Carnage content authority to flow through entire turn system. Prevents orphaned YAML definitions (defined but never checked). Makes authority decisions explicit and testable.
