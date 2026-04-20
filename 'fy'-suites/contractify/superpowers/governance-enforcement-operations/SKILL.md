---
name: governance-enforcement-operations
description: Use when verifying gate health after merges, diagnosing gate failures, troubleshooting false positives, adjusting thresholds, or syncing enforcement config with baseline updates
---

# Governance Enforcement Operations

## Overview

Manage, verify, and troubleshoot FY-suite enforcement gates. Ensures contractify, docify, despaghettify gates function correctly, baselines stay current, and enforcement config accurately reflects gate definitions.

## When to Use

Trigger when:
- Gates behaving unexpectedly (failing when shouldn't, passing when shouldn't)
- After major code merges, verify gates still work
- Baseline drift detected (old vs new audit results)
- Gate thresholds need adjustment
- Enforcement config out of sync with gate definitions

**When NOT to use:**
- Running gates first time (check documentation)
- Implementing new gate logic (requires governance skill)
- General test failures unrelated to gates (use systematic-debugging)

## Structured Approach

### Phase 1: Gate Health Check

For each gate file (contractify, docify, despaghettify):

1. Syntax validation: Parse YAML, check for malformed entries
2. Logic review: Condition operators correct? Thresholds sensible?
3. Coverage: Does gate cover all critical checks?
4. Dependencies: Does gate depend on missing baseline files?

Example check:
```yaml
# Check gate file exists and valid
fy_governance_enforcement.yaml:
  - contractify-gate.yml: [YAML valid? Conditions clear?]
  - docify-gate.yml: [YAML valid? Conditions clear?]
  - despaghettify-gate.yml: [YAML valid? Conditions clear?]
```

### Phase 2: Baseline Verification

1. Confirm baselines exist and current:
   - CANONICAL_REPO_ROOT_AUDIT.md (contractify baseline)
   - docify baseline (location TBD)
   - despaghettify baseline (location TBD)

2. Check baseline timestamps: Are they from today's commits?

3. Run audit commands to regenerate baselines:
   ```bash
   # Contractify
   contractify audit > latest_audit.json
   diff CANONICAL_REPO_ROOT_AUDIT.md latest_audit.json
   
   # Docify
   docify audit > latest_docify.json
   
   # Despaghettify
   despaghettify check > latest_despaghettify.json
   ```

4. If baselines stale: Update them (coordinate with team)

### Phase 3: Enforcement Config Review

1. Open fy_governance_enforcement.yaml
2. Verify all gates declared:
   - contractify gate referenced? Thresholds match gate file?
   - docify gate referenced? Thresholds match?
   - despaghettify gate referenced? Thresholds match?
3. Check severity levels (critical vs advisory) match intent
4. Verify gate firing conditions are correct

### Phase 4: Simulation (Local Gate Run)

1. Create test commit (small change)
2. Run gates locally before pushing:
   ```bash
   # Simulate each gate
   contractify audit && contractify gate-check
   docify audit && docify gate-check
   despaghettify check && despaghettify gate-check
   ```
3. Verify expected behavior:
   - Does gate pass/fail correctly?
   - Error messages clear?
   - No false positives?

### Phase 5: Repair (If Issues Found)

**Fix malformed YAML:**
- Correct syntax errors
- Re-validate parsing
- Test gate again

**Update stale baselines:**
- Regenerate baseline files
- Commit with clear message
- Note why baseline changed

**Resolve gate conflicts:**
- If gates disagree (one passes, one fails for same code)
- Review gate logic, identify conflict
- Align thresholds or logic
- Document resolution

## Required Inputs

- Access to gate definition files (contractify, docify, despaghettify)
- Baseline audit files (CANONICAL_REPO_ROOT_AUDIT.md, etc.)
- fy_governance_enforcement.yaml config
- Permission to run audit/gate commands locally
- Recent test/audit results for comparison

## Outputs

**Gate Health Report (Markdown):**
- Gate syntax status (OK, errors found)
- Baseline sync status (current, stale, missing)
- Enforcement config review (aligned, mismatches)
- Simulation results (pass/fail per gate)
- Repair log (if fixes applied)

## Example Usage

**Scenario:** Gate unexpectedly failed after merge

You:
1. Check gate syntax: `Parse contractify-gate.yml` → OK
2. Verify baseline: `CANONICAL_REPO_ROOT_AUDIT.md` → Updated today
3. Review enforcement config: Thresholds match gate definition
4. Simulate: Run gate on latest commit → Passes
5. Diagnose: Gate was correct, commit was the blocker
6. Report: "Gate health: OK. Baseline: current. Config: aligned. Simulation: passed. Likely false positive resolved by baseline update."

## Related Project Docs

- fy_governance_enforcement.yaml (enforcement config)
- fy-suite gate definition files (*-gate.yml)
- CANONICAL_REPO_ROOT_AUDIT.md (contractify baseline)
- Audit command documentation

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Checking gate without checking baseline first | Always verify baseline is current before gate logic |
| Assuming gate logic is correct without simulation | Simulate locally before trusting gate |
| Fixing gate without updating enforcement config | Config must match gate definition always |
| Not documenting why baseline changed | Always note baseline changes in commit |
| Running gates on stale code | Always test gates on latest commit |

## Real-World Impact

Prevents "ghost" gate failures (gates broken but undetected). Catches false positives before PR merges. Keeps enforcement synchronized and trustworthy.
