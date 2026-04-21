# Phase 6 & 7: With FY Governance Integration

**Updated Based On:** world_of_shadows_mvp_v24_lean_finishable enriched package  
**Governance Model:** Audit → Select → Handoff → Implement → Re-audit cycle  
**Timeline:** 2026-06-09 to 2026-09-01 (12 weeks)

---

## Overview: The Audit/Implementation Cycle

The v24 enriched MVP uses a controlled improvement loop:

```
AUDIT (Masterprompt 73)
  ↓ determines maturity, gaps, next field
HANDOFF (Masterprompt 74 template)
  ↓ produces implementation instructions
IMPLEMENT (AI takes handoff, updates MVP)
  ↓ changes code, tests, docs, governance artifacts
RE-AUDIT (Checklist 75)
  ↓ verifies improvement, next cycle begins
```

**Phase 6 & 7 must follow this pattern.** Each phase consists of **3-4 audit/implement cycles**, not linear execution.

---

## Maturity Model: What "Completion" Means

From v24 audit masterprompt, each work field has maturity level:

| Level | Definition | Example |
|---|---|---|
| **A** | Conceptual only | "Branching should exist" |
| **B** | Scoped but not operationalized | "Branching: 3-5 decision points per scenario" |
| **C** | Operationalized in documentation | "Branching system spec written, contracts defined" |
| **D** | Partially implemented | "Decision point system works, consequence filtering incomplete" |
| **E** | Implemented but weakly evidenced | "Code works, but tests minimal or incomplete" |
| **F** | Implemented and evidenced | "Code works, tests comprehensive, validation complete" |
| **G** | Runtime-ready and coherently integrated | "No drift, seamless integration, production-grade" |

**Phase 6 Goal:** Bring branching from F (implemented/evidenced) → G (runtime-ready)  
**Phase 7 Goal:** Bring concurrency/scale from D (partial) → G (runtime-ready)

---

## Phase 6: Branching Architecture (Cycles 1-3)

### Current State: Where Branching Maturity Stands

Based on Phase 5 planning:
- **Current maturity:** C-D (operationalized in docs, partially implemented)
- **Missing:** Runtime integration, determinism proof, replayability validation

### Phase 6 Cycle 1: Audit & Handoff (Week 1-2)

**Step 1: Run Audit Masterprompt on Branching**
- Assess branching maturity using v24 model
- Document: Is code consistent with spec? Are tests comprehensive? Does it integrate?
- Identify gaps: "Missing: outcome divergence measurement", "Missing: determinism test suite"
- Classify maturity: "Currently D/E; needs to reach G"

**Step 2: Generate Handoff for Cycle 1 Implementation**
- Use Masterprompt 74 template
- Selected work field: "Integrate branching into turn execution seams"
- Specify exactly: "Update turn_execution.py to accept and process branch decisions"
- Specify validation: "All Phase 5 scenarios must still work without branching enabled"

**Step 3: Use FY Suites**
- **contractify:** Map decision point contract → turn execution contract → consequence filter contract
- **despaghettify:** Ensure branching changes are isolated in specific files (not sprawling)
- **docify:** Update all branching-adjacent documentation to match code

**Deliverable:** Implementation handoff document + FY governance report

---

### Phase 6 Cycle 2: Implement & Reintegrate (Week 2-3)

**Implementation:**
- Integrate branching into world-engine turn execution
- Update consequence filtering to be branch-aware
- Add determinism test suite (verify same input → same output)
- Update all contracts and documentation

**Testing:**
- Run all Phase 5 smoke tests (ensure no regressions)
- Run new determinism tests (5 identical replays → identical transcripts)
- Run integration tests (branching + turn execution)

**FY Governance:**
- Run contractify (verify all contracts updated)
- Run despaghettify (verify changes are localized, not sprawling)
- Run docify (verify docs match code)

**Deliverable:** Updated MVP package with integrated branching

---

### Phase 6 Cycle 3: Validate & Prepare Phase 5 Revalidation (Week 3-4)

**Re-Audit:**
- Confirm branching is now maturity F (implemented and evidenced)
- Verify no drift introduced (FY suites confirm)
- Check readiness for Phase 5 revalidation

**Revalidation Preparation:**
- Prepare Phase 5 Scenario C data analysis (3 paths: A→A2, B→B2, C→C2)
- Design outcome divergence metrics (what = "60% different"?)
- Plan evaluator replayability testing (Phase 5 Scenario E)

**Deliverable:** Branching ready for evaluation, metrics designed, evaluator briefing prepared

---

### Phase 6 Cycle 4: Evaluation & Analysis (Week 4-5)

**Evaluate:**
- Run Phase 5 Scenario C with branching (measure outcome divergence)
- Run Phase 5 Scenario E with branching (measure replayability)
- Collect evaluator perception of branch coherence

**Analyze:**
- Outcome divergence: ≥ 60%? (if not, redesign decision points)
- Replayability: ≥ 70%? (if not, analyze which branches feel hollow)
- Determinism: 5/5 identical replays? (if not, find randomness leak)

**Final Re-Audit:**
- Confirm branching is maturity G (runtime-ready)
- Sign-off: "Branching system proved to work, outcomes diverge, players want to replay"

**Deliverable:** Phase 6 completion report + branching validation evidence

---

## Phase 7: Large-Scale Deployment (Cycles 1-3)

### Current State: Where Concurrency/Scale Maturity Stands

- **Current maturity:** B-C (scoped in docs, minimal implementation)
- **Missing:** Concurrency architecture, isolation proofs, performance optimization, deployment automation

### Phase 7 Cycle 1: Audit, Design & Handoff (Week 1-2)

**Step 1: Run Audit Masterprompt on Concurrency/Scale**
- Assess isolation maturity: Are there tests? Is session isolation documented or proven?
- Assess performance maturity: Are there baselines? Load tests? Optimization opportunities?
- Assess ops maturity: Is deploy automated? Is monitoring instrumented?
- Classify: "Currently B/C; needs to reach G"

**Step 2: Design Concurrency Architecture**
- Session isolation layer (how to ensure Session A ≠ Session B?)
- Lock strategy (minimal locks? lock-free? distributed?
- Performance budget (what's acceptable turn latency?)
- Cost tracking (what should we measure?)

**Step 3: Generate Handoffs for Phase 7**
- Cycle 1.5: "Implement session isolation with comprehensive tests"
- Cycle 2: "Optimize for performance; measure latency at 10, 50, 100 sessions"
- Cycle 3: "Implement deploy automation and incident response"

**FY Governance:**
- contractify: Map session isolation contract → backend API contract → monitoring contract
- despaghettify: Structural plan (isolation layer here, performance optimization there, ops automation here)
- docify: Concurrency documentation baseline

**Deliverable:** Concurrency architecture + 3 implementation handoffs + FY governance report

---

### Phase 7 Cycle 1.5: Isolation Implementation (Week 2-3)

**Implement:**
- Session isolation layer (guarantee no fact leakage between sessions)
- Comprehensive unit + integration tests (20 concurrent sessions, verify isolation)
- Error handling for isolation failures

**Test:**
- Unit test isolation (Session A fact doesn't appear in Session B)
- Integration test with 10 concurrent branching sessions
- Failure recovery test (if isolation fails, session rolls back cleanly)

**FY Governance:**
- contractify: Verify session isolation contract is honored
- despaghettify: Confirm isolation code is clean and isolated (meta!)
- docify: Isolation behavior documented

**Deliverable:** Isolation implementation + test evidence

---

### Phase 7 Cycle 2: Performance Optimization (Week 3-4)

**Measure Baseline:**
- Turn latency with 1 session (baseline)
- Turn latency with 10 sessions (identify overhead)
- Identify bottleneck (profiler: where's the time spent?)

**Optimize:**
- If bottleneck is LLM calls: implement call batching/caching
- If bottleneck is database: implement connection pooling or caching
- If bottleneck is compute: identify hot paths and optimize

**Load Test:**
- Latency at 50 concurrent sessions
- Latency at 100 concurrent sessions
- Verify SLA met: median ≤ 2s, 99th ≤ 5s

**Cost Analysis:**
- Cost per turn (LLM calls, storage, compute)
- Cost per 1-hour session (extrapolate)
- Cost scaling (1 session vs 100 sessions, is it linear?)

**Deliverable:** Performance optimization + cost analysis

---

### Phase 7 Cycle 3: Deployment Automation & Ops (Week 4-5)

**Implement Automation:**
- CI/CD pipeline for multi-session deploy
- Automated health monitoring (all sessions visible, status clear)
- Automated incident response (detect failure, execute recovery)
- Rollback automation (restore previous version without downtime)

**Test Operations:**
- Deploy automation (deploy new version to 100 sessions, verify no downtime)
- Health monitoring (100 sessions running, all visible in dashboard)
- Incident response (trigger failure, follow runbook, measure recovery <5s)
- Rollback (deploy old version, all sessions recover)

**Documentation:**
- Operations runbook (how to operate the system)
- Scaling playbook (how to add more capacity)
- Incident response procedures (step-by-step recovery)

**FY Governance:**
- contractify: Deploy automation contract, monitoring contract, ops contract
- despaghettify: Ops code is clean and modular
- docify: Ops procedures match code behavior

**Deliverable:** Deployment automation + operations runbooks + tested procedures

---

### Phase 7 Cycle 4: Stress Testing & Closure (Week 5-6)

**Stress Test (100 Sessions × 4 Hours):**
- All 5 scenarios running with branching enabled
- Measure: success rate, latency, cost, memory usage
- Verify: zero cross-session leakage, determinism holds, SLA maintained

**Failure Recovery:**
- Inject failures during stress test (crash a session, lose a connection)
- Measure: detection time, recovery time, impact on other sessions
- Verify: <5 second recovery, no cascading failures

**Final Re-Audit:**
- Confirm concurrency/scale is maturity G
- Verify all FY governance artifacts are updated
- Sign-off: "System proved production-ready at 100 concurrent sessions"

**Deliverable:** Phase 7 completion report + stress test evidence + scale limits documentation

---

## Integration: FY Suites at Each Step

### Contractify Usage (Throughout Both Phases)

**Track:**
- Decision point contract (decision point registry schema)
- Branch state contract (path state data structure)
- Outcome divergence contract (how to measure "different")
- Session isolation contract (guarantee no fact leakage)
- Performance contract (latency SLA: median ≤ 2s)
- Deployment contract (deploy procedure, zero downtime)

**Validate:**
- Does code match documented contracts?
- Are there any drift relationships? (contract says X, code does Y?)
- What implemented_by / validated_by / documented_in relationships exist?

**Output:**
- Contractify report showing: "All 8 major contracts up-to-date, 0 drift detected"

---

### Despaghettify Usage (Throughout Both Phases)

**Structure Discipline:**
- Phase 6 branching changes isolated to: `world-engine/branching/`, `story_runtime_core/consequence_*.py`, `tests/branching/`
- Phase 7 concurrency changes isolated to: `backend/concurrency/`, `world-engine/isolation/`, `tests/concurrency/`
- No sprawling changes (no touching frontend unless absolutely necessary)

**Output:**
- Despaghettify report showing: "Phase 6 changes are 100% localized to branching modules"
- Despaghettify report showing: "Phase 7 changes are 100% localized to concurrency/isolation modules"

---

### Docify Usage (Throughout Both Phases)

**Documentation Quality:**
- Every new module has docstrings
- Every new class has contract documentation
- Every decision point is documented (why this decision at this turn?)
- Every contract change has corresponding doc update

**Output:**
- Docify report showing: "Documentation 95%+ aligned with code"
- Identify any drift: "This doc mentions 3 decision points, code supports 5; doc is stale"

---

## Timeline with FY Cycles

```
PHASE 6: BRANCHING (6 weeks, 4 cycles)
├─ Cycle 1 (W1-2): Audit branching maturity, generate handoff
│  ├─ Audit masterprompt run
│  ├─ Handoff generated
│  └─ FY governance baseline (contractify, despaghettify, docify)
├─ Cycle 2 (W2-3): Implement integration, run FY suites
│  ├─ Turn execution integration
│  ├─ Determinism test suite
│  ├─ FY suites validate coherence
│  └─ All Phase 5 smoke tests pass
├─ Cycle 3 (W3-4): Re-audit, prepare evaluation
│  ├─ Re-audit (maturity F confirmed)
│  ├─ Phase 5 Scenario C prepared
│  └─ Evaluator briefing ready
└─ Cycle 4 (W4-5): Evaluate, analyze, close
   ├─ Phase 5 Scenario C + E evaluation
   ├─ Outcome divergence measured (≥60%?)
   ├─ Replayability measured (≥70%?)
   └─ Phase 6 completion report

PHASE 7: SCALE (6 weeks, 4 cycles)
├─ Cycle 1 (W1-2): Audit scale maturity, design, generate 3 handoffs
│  ├─ Concurrency audit (isolation, performance, ops)
│  ├─ Architecture design
│  ├─ 3 handoffs for cycles 1.5, 2, 3
│  └─ FY governance baseline
├─ Cycle 1.5 (W2-3): Implement isolation, verify with 10 concurrent sessions
│  ├─ Session isolation layer
│  ├─ Isolation tests (unit + integration)
│  ├─ FY suites confirm isolation coherence
│  └─ 10 concurrent session test passes
├─ Cycle 2 (W3-4): Optimize performance, verify with 100 concurrent sessions
│  ├─ Baseline latency measurement
│  ├─ Bottleneck identification
│  ├─ Performance optimization
│  ├─ Load test at 100 sessions (verify SLA)
│  └─ Cost analysis
├─ Cycle 3 (W4-5): Deploy automation, test operations
│  ├─ CI/CD automation
│  ├─ Health monitoring
│  ├─ Incident response procedures
│  ├─ Test all ops procedures (deploy, rollback, recovery)
│  └─ Operations runbooks
└─ Cycle 4 (W5-6): Stress test, close
   ├─ 100 session stress test × 4 hours
   ├─ Failure recovery verification
   ├─ Re-audit (maturity G confirmed)
   └─ Phase 7 completion report
```

---

## Success Criteria: FY Governance Integration

For Phase 6 & 7 to succeed:

**Contract Coherence:**
- ✓ All major contracts (branching, isolation, performance, deployment) up-to-date
- ✓ No drift detected by contractify
- ✓ All implemented_by / validated_by / documented_in relationships clear

**Structural Discipline:**
- ✓ Phase 6 changes localized (despaghettify confirms)
- ✓ Phase 7 changes localized (despaghettify confirms)
- ✓ No hidden or sprawling modifications

**Documentation Quality:**
- ✓ Code and docs stay in sync (docify confirms 95%+ alignment)
- ✓ All new features documented with contracts
- ✓ All decisions documented with rationale

**Maturity Progression:**
- ✓ Phase 6 branching: C-D → F → G (from partial/weak evidence → runtime-ready)
- ✓ Phase 7 scale: B-C → D-E → F-G (from scoped → partial → evidenced → runtime-ready)

**Re-Audit Readiness:**
- ✓ Each cycle produces re-audit checklist (Masterprompt 75)
- ✓ Next cycle uses previous cycle's re-audit outputs
- ✓ Final re-audit confirms system is production-ready

---

## FY Governance Handoff to Production

When Phase 7 completes:

**Production Receives:**
- ✓ Updated MVP with all changes integrated
- ✓ Contractify report: "All contracts coherent, 0 drift"
- ✓ Despaghettify report: "All changes localized and disciplined"
- ✓ Docify report: "Documentation 95%+ aligned with code"
- ✓ Final maturity assessment: "System G (runtime-ready, coherently integrated)"

**Production Must Verify:**
- User account system (required before real players)
- Content moderation (required for safety)
- Legal/compliance (required for business)

**Then:** Deploy with confidence that system is architecturally sound, properly evidenced, and operationally ready.

---

## Conclusion

**Phases 6 & 7 use the v24 audit/implement/re-audit cycle,** not waterfall planning.

Each phase consists of 3-4 cycles:
1. **Audit:** Assess current maturity, identify gaps, determine next work field
2. **Handoff:** Generate implementation instructions using Masterprompt 74
3. **Implement:** Make changes, update tests, update docs, use FY suites
4. **Re-audit:** Verify maturity improved, prepare next cycle

By end of Phase 7:
- ✓ Branching is maturity G (runtime-ready)
- ✓ Scale is maturity G (runtime-ready)
- ✓ All contracts coherent (contractify confirms)
- ✓ All changes disciplined (despaghettify confirms)
- ✓ All docs aligned (docify confirms)
- ✓ System ready for production deployment

**This approach ensures:** Low drift, high coherence, production-grade evidence, and controlled hand-offs between audit and implementation cycles.
