---
name: validation-rules-formalization
description: Use when converting GATE_SCORING_POLICY principles into formal testable rules, implementing GoC validation engine, or adding new validation constraints to turn graph
---

# Validation Rules Formalization

## Overview

Convert vague validation policies into formal, testable, operationalized rules. Transforms GATE_SCORING_POLICY_GOC.md principles into executable logic that can be tested, enforced, and debugged.

## When to Use

Trigger when:
- New validation constraint needed (content authority, continuity, escape behavior)
- Vague policy needs to become checkable rule
- Validation engine enhancement required
- Turn graph validation logic unclear or untestable
- Need to add test cases for validation behavior

**When NOT to use:**
- Changing existing validation rules (requires design first)
- Debugging single validation failure (use systematic-debugging)
- Implementing without test cases (use TDD)

## Structured Approach

### Phase 1: Policy Extraction

1. Read GATE_SCORING_POLICY_GOC.md cover to cover
2. Read CANONICAL_TURN_CONTRACT_GOC.md for turn model
3. List every validation principle mentioned:
   - Dramatic vocabulary constraints
   - Character continuity rules
   - Relationship authority rules
   - Content authority rules
   - State consistency rules
   - Escape behavior rules

4. Document each principle verbatim with page reference

### Phase 2: Formalization (Convert to Measurable Rules)

For each principle, convert to rule format:

```
PRINCIPLE (from docs):
"Dramatic vocabulary must match GoC builtin set"

RULE (measurable):
rule_dramatic_vocabulary_in_builtin_set:
  - Input: proposed_action.description (string)
  - Check: Every word in description must match vocabulary_builtin_set
  - Pass condition: len(unknown_words) == 0
  - Fail condition: len(unknown_words) > 0
  - Output: {'status': 'pass'|'fail', 'unknown_words': [...]}

ENFORCEMENT POINT:
  - Called during proposal validation (turn_graph.validate_proposal)
  - Severity: critical (blocks turn if fails)
```

For each rule, document:
- **Rule name:** Unique identifier
- **Input:** What data does it check?
- **Logic:** The measurable condition
- **Pass/fail criteria:** When does it trigger?
- **Output:** Result format
- **Enforcement point:** Where in turn graph called?

### Phase 3: Specification

Write rule logic in pseudo-code or flowchart:

```
RULE: validate_character_continuity

Input: proposed_character_id, current_game_state, YAML_authority

Logic:
  1. Load character from YAML (yaml_char)
  2. Load character from game_state (state_char)
  
  IF yaml_char != state_char:
    Check conflict resolution policy:
    - If YAML authority is higher: state_char = yaml_char (YAML wins)
    - Else: state_char = state_char (state wins)
    - Log conflict resolution
  
  Return: {'status': 'pass', 'applied': applied_state}

IF logic error occurs:
  Return: {'status': 'fail', 'error': error_description}
```

### Phase 4: Test Case Derivation

For each rule, generate 3-5 test cases (pass and fail):

```
RULE: rule_dramatic_vocabulary_in_builtin_set

TEST CASE 1 (pass):
  Input: "The dragon breathes fire across the valley"
  Expected: status='pass', unknown_words=[]
  
TEST CASE 2 (fail):
  Input: "The quixotic dragon breathes fire"
  Expected: status='fail', unknown_words=['quixotic']
  
TEST CASE 3 (edge case):
  Input: "" (empty action)
  Expected: status='pass', unknown_words=[]
  
TEST CASE 4 (edge case):
  Input: "!@#$%^&*()" (special chars only)
  Expected: status='fail', unknown_words=['!@#$%^&*()']
```

### Phase 5: Implementation Guide

Map each rule to code location:

```
RULE: rule_dramatic_vocabulary_in_builtin_set

IMPLEMENTATION LOCATIONS:
  - backend/world_engine/turn_graph.py :: validate_proposal()
  - Location: Line ~250 (proposal validation phase)
  - Call: self.vocabulary_checker.validate(action.description)
  - On fail: raise ValidationError("Unknown words: ...")

CODE SCAFFOLDING NEEDED:
  - vocabulary_checker class (new file? expand existing?)
  - builtin_set loader (load from where?)
  - Error message format (consistent with other rules?)
```

## Required Inputs

- GATE_SCORING_POLICY_GOC.md (policy source)
- CANONICAL_TURN_CONTRACT_GOC.md (turn model)
- Current turn_graph.py implementation
- Existing validation rule examples (patterns to follow)
- Test infrastructure (pytest fixtures, test harness)

## Outputs

**Three deliverables:**

1. **Formal Rules Document** (Markdown):
   - Rule name, input, logic, pass/fail criteria, output
   - Pseudo-code or flowchart for complex logic
   - Enforcement point in turn graph

2. **Test Cases** (Python):
   - 3-5 test cases per rule (pass/fail/edge cases)
   - Clear assertions per test case
   - Ready to add to test suite

3. **Implementation Mapping** (Markdown):
   - Code locations where rules execute
   - Scaffolding needed
   - Integration points

## Example Usage

**Scenario:** Need to formalize "character continuity" validation

You:
1. Extract policy: Read GoC docs, find continuity principles
2. Formalize: Convert to measurable rule (character state consistent between YAML and game_state)
3. Specify: Write flowchart for conflict resolution (YAML vs state authority)
4. Test cases: Generate pass/fail/edge cases for rule
5. Map: Identify where in turn_graph this should run (proposal validation phase)
6. Deliver: Rules doc + test cases + implementation guide

## Related Project Docs

- GATE_SCORING_POLICY_GOC.md (validation policies)
- CANONICAL_TURN_CONTRACT_GOC.md (turn model)
- backend/world_engine/turn_graph.py (implementation location)
- backend/tests/ (test patterns)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Writing rules without policy source | Always extract policy first from docs |
| Rules too vague to test | Make measurable: "input X, check Y, pass if Z" |
| Forgetting edge cases (empty, special chars, nulls) | Generate 5 cases: normal pass, normal fail, 3 edge cases |
| Rules don't match enforcement point | Verify where rule actually runs in turn graph |
| No test cases = untestable rule | Every rule must have 3+ concrete test cases |

## Real-World Impact

Converts "validations should work somehow" into "here's exactly how validation works, here's the test proving it". Enables debugging specific rule failures. Makes turn graph validation testable and maintainable.
