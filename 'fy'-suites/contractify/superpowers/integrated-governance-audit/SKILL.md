---
name: integrated-governance-audit
description: Use when running comprehensive governance health checks, detecting cross-suite drift, verifying coherence before major merges, or synthesizing findings across contractify, docify, and despaghettify audits
---

# Integrated Governance Audit

## Overview

Run contractify, docify, despaghettify audits in parallel and synthesize findings into integrated report. Detects cross-suite coherence issues: contracts without code, code without tests, docstrings out of sync with implementations.

## When to Use

Trigger when:
- Periodic health check (daily/weekly)
- Before major merges or releases
- Verifying cross-suite coherence required
- New contracts, code, or docs added
- Governance baseline update needed

**When NOT to use:**
- Single-suite audit (use individual suite audits)
- Debugging single test failure (use systematic-debugging)
- Implementing new governance rules (requires design)

## Structured Approach

### Phase 1: Parallel Audit Runners

Run all 3 audits simultaneously (parallel saves time):

```bash
# Terminal 1
contractify audit > contractify_report.json &

# Terminal 2
docify audit > docify_report.json &

# Terminal 3
despaghettify check > despaghettify_report.json &

# Wait for all to complete
wait
```

Collect outputs:
- `contractify_report.json`: Contracts, coverage, relationships
- `docify_report.json`: Docstring coverage, module structure
- `despaghettify_report.json`: Function length, complexity, coupling

### Phase 2: Synthesis

Combine findings across suites:

**Coherence checks:**

| Check | What to look for |
|-------|------------------|
| **Contract → Code** | New contract exists in codebase? Matches contract signature? |
| **Code → Tests** | New code has tests? Tests cover contract? |
| **Docstring Sync** | Docstring matches code implementation? Return values documented? |
| **Complexity Growth** | New code longer than existing baseline? |
| **Coupling** | New code tightly coupled to uncontracted dependencies? |

For each change (new contract, new code, new docstring):
- Find it in contractify output
- Find matching code in docify output
- Find corresponding tests in despaghettify output
- Flag if any piece missing

### Phase 3: Cross-Suite Drift Detection

Identify these drift patterns:

```
DRIFT PATTERN 1: Orphaned Contracts
  - Contract in contractify_report
  - NO corresponding code in codebase
  - Action: Remove contract or add implementation

DRIFT PATTERN 2: Untested Code
  - Code in despaghettify_report
  - NO corresponding test in test suite
  - Action: Add tests or remove code

DRIFT PATTERN 3: Stale Docstrings
  - Docstring in docify_report says X
  - Code in contractify_report does Y
  - Action: Update docstring to match code

DRIFT PATTERN 4: Contract Violation
  - Contract specifies signature/behavior
  - Code implements differently
  - Action: Fix code or renegotiate contract
```

### Phase 4: Report Generation

Generate Markdown report with sections:

**Section 1: Executive Summary**
- Total findings across suites
- Critical issues (must fix before merge): count
- Advisory issues (fix next week): count
- Overall coherence score (0-100%)

**Section 2: Suite-by-Suite Results**
- Contractify audit results (contracts added, modified, coverage %)
- Docify audit results (docstring coverage %, modules undocumented)
- Despaghettify audit results (new functions, complexity, violations)

**Section 3: Cross-Suite Findings**
- Coherence issues discovered (drift patterns found)
- Contract ↔ Code ↔ Test mismatches
- Stale docstring detections

**Section 4: Severity Ranking**

| Severity | Examples | Action |
|----------|----------|--------|
| **Critical** | Orphaned contract, untested code, code violates contract | Must fix before merge |
| **Advisory** | Docstring slightly stale, code could be shorter, new module needs docstring | Fix in next pass |

### Phase 5: Severity Ranking

Assign severity per finding:

- **Critical (must fix before merge):**
  - New contracts without implementation
  - New code without tests
  - Code violates contract definition
  - Docstring contradicts implementation

- **Advisory (fix next week):**
  - Docstring could be clearer
  - Function slightly longer than baseline
  - New module underdocumented
  - Unused contracts (old, not new)

## Required Inputs

- Access to contractify, docify, despaghettify commands
- Recent baseline audit reports
- Codebase to audit
- Test suite results
- Recent commits to track what changed

## Outputs

**Integrated Governance Audit Report (Markdown):**
- Executive summary (findings count, coherence score)
- Suite-by-suite results (contractify, docify, despaghettify)
- Cross-suite drift findings (patterns detected)
- Severity-ranked action items
- Evidence snapshots (links to specific files/commits)

## Example Usage

**Scenario:** Before merging new world-engine features

You:
1. Run parallel audits: contractify, docify, despaghettify simultaneously
2. Synthesize: Check each new contract has code, code has tests, docstring matches
3. Detect drift: Find orphaned contract (implementation missing), untested code
4. Report: "Coherence: 88%. Critical issues: 2 (missing implementation, untested code). Advisory: 1 (docstring stale). Recommend: add implementation, add tests, update docstring before merge."

## Related Project Docs

- fy_governance_enforcement.yaml (audit thresholds)
- CANONICAL_REPO_ROOT_AUDIT.md (contractify baseline)
- Docify baseline (location TBD)
- Despaghettify baseline (location TBD)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Running audits sequentially (slow) | Run all 3 in parallel, wait for results |
| Missing cross-suite links | For each new item, trace through all 3 suites |
| Confusing advisory with critical | Critical = blocks merge. Advisory = fix later |
| Not checking coherence direction | Check contract→code AND code→tests |
| Ignoring stale docstrings | Docstring != code = drift, must fix |

## Real-World Impact

Prevents "the contract exists but code doesn't" bugs. Catches untested code before it ships. Keeps governance baselines synchronized. Moves from "suites working independently" to "system coherent end-to-end".
