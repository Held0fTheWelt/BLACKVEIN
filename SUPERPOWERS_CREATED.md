# World of Shadows MVP Superpowers

6 custom superpowers created to accelerate MVP completion and governance enforcement.

## Superpowers Overview

### 1. MVP-Readiness-Assessment
**Location:** `'fy'-suites/despaghettify/superpowers/mvp-readiness-assessment/SKILL.md`

**Purpose:** Rapidly assess MVP state against audit criteria across 6 critical domains (runtime authority, validation, commit, visibility, continuity, governance). Provides readiness score, domain maturity matrix, blocker identification, and next-target prioritization.

**When to use:**
- Determining MVP phase readiness
- Understanding preparedness across domains
- Prioritizing next work targets
- Stakeholder readiness reporting

**How it works:**
1. Quick state inspection (git, tests, audit reports)
2. Score 6 domains on readiness (0-100%)
3. Identify blockers per incomplete domain
4. Calculate overall readiness
5. Recommend 3 candidates, pick best by leverage/impact

**Output:** Markdown report with readiness score, domain matrix, blocker list, next-target recommendation

---

### 2. Governance-Enforcement-Operations
**Location:** `'fy'-suites/contractify/superpowers/governance-enforcement-operations/SKILL.md`

**Purpose:** Manage, verify, troubleshoot FY-suite enforcement gates. Ensures contractify, docify, despaghettify gates function correctly, baselines stay current, enforcement config aligns with gate definitions.

**When to use:**
- After merging, verify gates functioning
- Gates failing unexpectedly
- Diagnosing gate false positives
- Adjusting thresholds/severity
- Baseline drift detected

**How it works:**
1. Gate health check (syntax, logic, coverage)
2. Baseline verification (current and valid?)
3. Enforcement config review (aligned?)
4. Simulation (run gates locally, verify behavior)
5. Repair (fix YAML, update baselines, resolve conflicts)

**Output:** Gate health report, baseline sync status, simulation results, repair log

---

### 3. Validation-Rules-Formalization
**Location:** `'fy'-suites/documentify/superpowers/validation-rules-formalization/SKILL.md`

**Purpose:** Convert GATE_SCORING_POLICY principles into formal testable rules. Turns vague validation policies into measurable, operationalized constraints that can be tested and enforced.

**When to use:**
- Implementing GoC validation engine
- Converting policy principles into executable logic
- Adding new validation constraints
- Making validation rules testable

**How it works:**
1. Extract policy from GATE_SCORING_POLICY_GOC.md
2. Formalize into measurable rules (input, check, pass/fail criteria)
3. Write rule logic in pseudo-code/flowchart
4. Derive 3-5 test cases per rule (pass/fail/edge)
5. Map to backend code locations

**Output:** Formal rules document, test cases, implementation mapping

---

### 4. Integrated-Governance-Audit
**Location:** `'fy'-suites/contractify/superpowers/integrated-governance-audit/SKILL.md`

**Purpose:** Run contractify, docify, despaghettify audits in parallel and synthesize findings. Detects cross-suite drift: contracts without code, code without tests, docstrings out of sync.

**When to use:**
- Periodic health checks (daily/weekly)
- Before major merges or releases
- Verifying cross-suite coherence
- New contracts, code, or docs added
- Governance baseline updates

**How it works:**
1. Run all 3 audits in parallel
2. Synthesize findings (contract → code → tests → docs)
3. Detect drift patterns (orphaned contracts, untested code, stale docstrings)
4. Generate integrated report
5. Rank findings by severity (critical vs advisory)

**Output:** Integrated governance audit report, cross-suite drift findings, action items by severity

---

### 5. Turn-Execution-Verification
**Location:** `'fy'-suites/testify/superpowers/turn-execution-verification/SKILL.md`

**Purpose:** Verify turn execution under production conditions through complete seams: proposal→validation→commit→visibility. Tests turn graph end-to-end with diverse scenarios, captures diagnostics, validates state transitions.

**When to use:**
- Testing turn execution after code changes
- Validating new validation rules work
- Verifying commit effects apply correctly
- Testing continuity carry-forward at scale
- Diagnosing turn graph failures

**How it works:**
1. Build test scenarios (8-10 diverse: simple, multi-intent, error, edge cases)
2. Execute each through turn graph (all 4 seams)
3. Verify each seam produces expected outputs
4. Collect diagnostics (state transitions, visibility output, errors)
5. Generate test report with pass/fail per scenario

**Output:** Turn execution test report, per-scenario results, diagnostics bundle, failure analysis

---

### 6. Content-Authority-Integration
**Location:** `'fy'-suites/documentify/superpowers/content-authority-integration/SKILL.md`

**Purpose:** Systematically integrate YAML content authority (God of Carnage builtin roles, relationships, attributes) into turn execution. Ensures YAML authority is consulted at all decision points, conflicts detected correctly.

**When to use:**
- Integrating YAML authority into turn graph
- Testing builtin vs YAML conflict detection
- Verifying YAML module loads correctly
- Ensuring content authority flows through turns
- Testing authority respects YAML definitions

**How it works:**
1. Map authority sources (roles, relationships, attributes, vocabulary)
2. Identify integration points (proposal, validation, commit, visibility)
3. Design conflict detection (YAML vs builtin precedence)
4. Generate test scenarios (authority conflicts, fallbacks)
5. Plan implementation (code changes, new files, scaffolding)

**Output:** Authority integration map, conflict resolution policy, test scenarios, implementation plan

---

## How Superpowers Work Together

These 6 superpowers form an integrated acceleration framework:

```
READINESS → GOVERNANCE → VALIDATION → AUDIT → TESTING → AUTHORITY
   (What's                (Are                 (Is turn     (Does
    ready?)              gates               execution    content
                         working?)           working?)    authority
                                                          flow?)
     ↓                      ↓                    ↓            ↓
  MVP STATUS            GATE HEALTH         SEAM INTEGRITY  YAML AUTHORITY
  ASSESSMENT            ENFORCEMENT         VERIFICATION    INTEGRATION
```

### Workflow Example:

1. **Start:** Use MVP-Readiness-Assessment to determine current state
   - "MVP is 74% ready. Validation 50%. Main blocker: rules not formalized."

2. **Formalize:** Use Validation-Rules-Formalization to convert policy into rules
   - "Created 12 formal rules with test cases. Ready to implement."

3. **Test:** Use Turn-Execution-Verification to validate turn graph works with new rules
   - "8/8 scenarios pass. All seams verified. Continuity working."

4. **Integrate:** Use Content-Authority-Integration to wire YAML authority
   - "Authority integrated. All 4 integration points wired. Conflicts detected."

5. **Verify Gates:** Use Governance-Enforcement-Operations to ensure gates still work
   - "Gates: OK. Baseline: current. Config: aligned. Ready for merge."

6. **Full Audit:** Use Integrated-Governance-Audit for cross-suite coherence check
   - "Coherence: 92%. All contracts have code. All code has tests. Docstrings current."

7. **Reassess:** Use MVP-Readiness-Assessment again to measure progress
   - "MVP now 91% ready. Validation 100%. Commit 95%. Ready for phase transition."

## Installation & Usage

All 6 superpowers are ready to invoke immediately:

```bash
# From Claude Code, invoke any skill:
/skill mvp-readiness-assessment
/skill governance-enforcement-operations
/skill validation-rules-formalization
/skill integrated-governance-audit
/skill turn-execution-verification
/skill content-authority-integration
```

Each skill provides:
- Clear triggering conditions
- Structured approach (steps/phases)
- Decision logic at each point
- Required inputs and outputs
- Common mistakes to avoid
- Real-world impact metrics

## Key Benefits

- **Rapid MVP iteration:** Readiness → Validation → Test → Authority cycle takes 4-6 hours instead of days
- **Governance enforcement:** Gates stay healthy, baselines current, enforcement synchronized
- **Reduced rework:** Cross-suite audits catch coherence issues before merge
- **Testable validation:** Rules formalization makes validation debuggable
- **End-to-end verification:** Turn execution verified through all seams
- **Content authority:** YAML authority integrated systematically, not ad-hoc

## Next Steps

1. Invoke each skill as needed per workflow
2. Each skill generates evidence (reports, test results, diagnostics)
3. Store reports in `'fy'-suites/` appropriate directory
4. Reference in weekly status updates
5. Iterate: skills provide feedback loops for continuous improvement

---

**Created:** April 17, 2026  
**For:** World of Shadows MVP Acceleration  
**Status:** Ready for immediate use
