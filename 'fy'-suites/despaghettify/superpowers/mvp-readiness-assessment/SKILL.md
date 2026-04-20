---
name: mvp-readiness-assessment
description: Use when determining MVP readiness status across domains, identifying blockers preventing completion, assessing domain maturity levels, or prioritizing next work targets
---

# MVP Readiness Assessment

## Overview

Rapidly assess current MVP state against audit criteria and identify blockers. Provides structured readiness scoring, domain maturity analysis, and prioritized next-target recommendations based on leverage and impact.

## When to Use

Trigger when:
- MVP phase transition decisions needed
- Current state of preparedness unclear across domains
- Prioritization of next work target required
- Stakeholder readiness reporting needed
- After major commits to verify progress

**When NOT to use:**
- Detailed code review (use verification-before-completion)
- Architectural redesign (requires design skill)
- Individual test debugging (use systematic-debugging)

## Structured Approach

### Phase 1: Quick State Inspection

1. Run `git status` to identify recent changes
2. Check test results: `python run_tests.py --suite all`
3. Review recent commits (last 5-10) for scope
4. Scan `'fy'-suites/` directories for audit reports
5. Identify latest blockers from git history

### Phase 2: Domain Checklist

Assess 6 critical domains (score: 0% = not started, 50% = partial, 100% = complete):

| Domain | Meaning | Status Check |
|--------|---------|--------------|
| **Runtime Authority** | Turn execution framework complete, seams verified | Check turn_graph.py, validation logic, commit effects |
| **Validation Rules** | GoC validation engine formalized and testable | Check GATE_SCORING_POLICY_GOC.md, rule specifications |
| **Commit Effects** | State transitions apply correctly, persistence works | Check world_state.py updates, database migrations |
| **Evidence Visibility** | Render/visibility pipeline complete and correct | Check render functions, observer pattern implementation |
| **Continuity** | Turn carry-forward logic correct, no state drift | Check state initialization, reset functions |
| **Governance** | Gates passing, baselines current, enforcement working | Check fy_governance_enforcement.yaml, audit reports |

### Phase 3: Blocker Identification

For each domain scoring <100%, document:
- What's preventing completion? (missing code, failing tests, spec gap)
- Is it a hard blocker (other domains depend) or soft blocker (independent)?
- Effort estimate (hours)
- Risk level (low/medium/high)

### Phase 4: Maturity Scoring

Current score: `(domain1% + domain2% + ... + domain6%) / 6`

Target: 100% across all domains

Gap analysis: `100% - current_score = work_remaining`

### Phase 5: Next-Target Intelligence

Identify 3 candidate targets:

1. **Highest leverage:** Unlocks other work, reduces wait times
2. **Lowest risk:** Can be completed independently, high confidence
3. **Fastest to complete:** Quick win, builds momentum

Recommend best based on: leverage + confidence + time available

## Required Inputs

- Access to git history and current status
- Test suite results (backend tests minimum)
- Audit reports from fy-suite directories
- Project documentation (GATE_SCORING_POLICY, turn graph specs)

## Outputs

**Markdown report with:**
- Current readiness score (0-100%)
- Domain maturity matrix with scores and status
- Blocker list (what's preventing each incomplete domain)
- Recommended next target (with justification)
- Evidence snapshot (recent commits, test status)

## Example Usage

**Scenario:** Ready to assess MVP before phase transition

User: "Is MVP ready for stakeholder review?"

You:
1. Run quick state inspection (git, tests, audit reports)
2. Score each domain against checklist
3. Identify blockers per domain
4. Calculate overall readiness score
5. Recommend 3 targets, pick best
6. Report: "MVP is 74% ready (runtime 100%, validation 50%, commit 85%, visibility 90%, continuity 60%, governance 80%). Primary blocker: validation engine not formalized. Recommend next: formalize validation rules (leverage: unblocks testing, risk: low, time: 8 hours)."

## Related Project Docs

- GATE_SCORING_POLICY_GOC.md (validation principles)
- CANONICAL_TURN_CONTRACT_GOC.md (turn graph contract)
- fy_governance_enforcement.yaml (gate thresholds)
- test_reports/ (audit results)
- backend/tests/conftest.py (fixture definitions)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Scoring without checking code (opinion-based) | Always inspect: tests, audit reports, source files |
| Confusing "complete" with "perfect" | 100% means minimum viable, not fully optimized |
| Ignoring hard blocker dependencies | Check which domains other domains depend on |
| Picking next target by interest not leverage | Use leverage matrix to prioritize impact |
| Not documenting blocker evidence | Always capture "what prevents this" with specifics |

## Real-World Impact

Saves 2-3 hours of stakeholder/team sync time per readiness check. Moves MVP decisions from ambiguous ("is it ready?") to data-driven ("here's the gap"). Enables prioritization by actual impact, not noise.
