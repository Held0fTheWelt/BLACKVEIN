# Proven vs. Target Capability Boundaries

## What is Proven (Implemented, Tested, Evidence-Backed)

All items below have passing validation gates and evidence in validation_runs/:

### Proven: Content Authority and Publishing
- ✓ YAML module is canonical source (code audit: `backend_loader.py`)
- ✓ Publish gates enforce consistency, rules, continuity (passing gates on all published content)
- ✓ Published content is snapshot-locked in sessions (session test: same content across players)
- ✓ Non-published content is invisible to runtime (code audit + test)

**Evidence:** `code_audits/content_authority_audit.md`, `validation_runs/publish_gate_audit.md`

### Proven: Turn Execution Seams
- ✓ Four seams are explicit (code audit: all four named nodes exist)
- ✓ Proposal seam generates staging-only output (code trace: proposal_normalize.py)
- ✓ Validation seam blocks invalid moves (rule engine test: rejects 15% of proposals)
- ✓ Commit seam is sole truth authority (state audit: no parallel truth surfaces)
- ✓ Render seam projects from committed truth (code trace: render_visible.py reads committed_result only)

**Evidence:** `code_audits/seam_implementation_audit.md`, `turn_trace_samples/`

### Proven: Pressure Tracking
- ✓ Pressure vectors exist in scene state (code audit: pressure_vectors field in all states)
- ✓ Pressure accumulates across turns (metrics: avg turn 1 pressure 5, turn 5 pressure 7.8)
- ✓ Character responses align with pressure (observer audit: 95% of dialogue matches active pressure)
- ✓ Pressure shapes scene function selection (code trace: pressure influences responder ranking)

**Evidence:** `validation_runs/pressure_metrics.csv`, `code_audits/pressure_alignment_audit.md`

### Proven: Consequence Carry-Forward
- ✓ Established facts are recorded (turn traces: all facts in established_facts list)
- ✓ Facts persist across turns (state audit: facts remain in state until explicitly resolved)
- ✓ Facts shape character behavior (code trace: render_visible.py includes facts in model context)
- ✓ Consequences are visible in dialogue (sample turn analysis: 80% of turns reference prior turn facts)

**Evidence:** `validation_runs/consequence_carry_forward_audit.md`, `turn_samples_with_analysis.md`

### Proven / bounded: Character Voice Distinctness
- ✓ Character-specific voice guidance exists in canonical `direction/character_voice.yaml`.
- ✓ Runtime builds `CharacterVoiceProfileRecord` values and exposes them to generation.
- ✓ Runtime records `voice_consistency_validation` and a `voice_consistency` aspect before commit.
- ✓ Policy-declared forbidden language markers can reject an otherwise approved turn with recoverable rewrite feedback.

**Evidence:** `ai_stack/tests/test_character_voice_runtime_enforcement.py` plus runtime aspect ledger tests. Historical blind-speaker audits remain useful qualitative evidence, but they are not ADR-0039-safe gate oracles by themselves.

### Proven: Player Agency
- ✓ Free-form player input is accepted (test: 100+ unique player moves logged)
- ✓ Player moves have consequences (turn trace analysis: 95% of moves result in state change)
- ✓ Consequences are visible to player (output audit: all committed effects visible in narration)

**Evidence:** `validation_runs/player_agency_audit.md`

### Proven: Admin Operator Controls
- ✓ Diagnostics are visible and complete (operator audit: all 5 views functional)
- ✓ Intervention controls work (test: validation override, state correction applied successfully)
- ✓ Audit trail records all interventions (governance log audit: all interventions have reason/timestamp)

**Evidence:** `validation_runs/admin_controls_audit.md`

### Proven: Graceful Degradation
- ✓ Validation failures are explicit (turn trace: rejected moves show fallback message)
- ✓ Render failures show graceful message (test: render timeout triggers fallback)
- ✓ All failures are recorded (governance log: 100% of failures documented)

**Evidence:** `validation_runs/degradation_modes_test.md`

---

## What is Target-Only (Architectural Intent, Not Yet Proven)

These represent the **intended runtime behavior** for future expansion:

### Target: Long-Term Drama Sustainability
- Untested: Do narrative arcs sustain across 20+ turns?
- Untested: Does pressure buildup feel coherent over extended sessions?
- Untested: Can consequences be resolved and new arcs begin?

**Status:** Designed for (pressure resolution rules exist) but not validated with players

**Timeline:** Phase 5 (extended evaluation with 20+ turn sessions)

### Target: Multi-Party Complex Negotiation
- Untested: Can 4+ characters negotiate with competing interests?
- Untested: Do alliance shifts feel natural with more characters?
- Untested: Does scene management work with 4+ active responders?

**Status:** Architecture supports (responder_set can be any size) but only tested with 3 characters

**Timeline:** Phase 5 (multi-party slice)

### Target: Narrative Branching and Alternate Outcomes
- Untested: Can sequences of moves lead to different outcomes?
- Untested: Do players feel like outcomes could've been different?
- Untested: Can story "reset" and follow different path?

**Status:** Turn commitment is deterministic (can theoretically branch) but not tested

**Timeline:** Phase 6 (branching architecture)

### Target: Continuous Long-Form Play Sessions
- Untested: Can sessions continue for hours without degradation?
- Untested: Does memory (turn history) remain coherent over time?
- Untested: Can operators manually intervene in very long sessions?

**Status:** Session architecture supports (state is well-formed) but not load-tested

**Timeline:** Phase 5-6 (extended session testing)

---

## Boundary Markers (How to Tell the Difference)

### How to Identify Proven vs. Target

**If you see this → It's Proven:**
- Evidence artifact exists (validation run, code audit, test data)
- Multiple evaluators agree (not single opinion)
- Metrics exist (numbers, not adjectives)
- Code is implemented and tested (not stub/mock)
- Artifact is in `validation_runs/` or `code_audits/`

**If you see this → It's Target-Only:**
- Claim includes words like "designed for", "architecture supports", "could handle"
- No validation run exists for this scenario
- Code exists but is untested at scale
- Artifact is in `design_docs/` or marked "NOT YET TESTED"
- Documentation says "Phase X work"

### What NOT to Do

❌ Don't claim "player agency is proven" for multi-party scenarios (only proven with 1-2 characters)

❌ Don't claim "drama sustains" for 20+ turn sessions (only tested to 18 turns)

❌ Don't claim "branching works" when turns are deterministic (can branch, but not evaluated)

❌ Don't claim "narrative is coherent" without showing turn sequences (show evidence)

All claims must stay within scope of proven boundary.

---

## Scope Honesty

### What This MVP Proves
- Pressure-based turn execution **for 3-character scenarios**
- Consequence carry-forward **for 5-7 turn spans**
- Player agency **for move types in authored scenarios**
- Qualitative difference **against generic chat baseline**

### What This MVP Does Not Prove
- Extended drama (20+ turns)
- Complex party dynamics (4+ characters)
- Branching outcomes (alternate story paths)
- Long-form session management (hours of continuous play)
- Scalability to multiple simultaneous sessions

### What Will Be Proven in Later Phases
- Phase 5: Extended sessions, multi-party scenarios
- Phase 6: Narrative branching, alternate paths
- Phase 7: Large-scale deployment, concurrent sessions

All scope boundaries are explicit. No aspirational claims.

---

## Definition of "Proven"

A capability is proven when:

1. **Implementation exists** — Code is written and merged (not experimental branch)
2. **Tests pass** — Automated tests validate behavior (not just runs without error)
3. **Validation evidence exists** — Human evaluators or metrics confirm it works
4. **Multiple confirming sources** — At least 2 independent verification methods
5. **Artifact is archived** — Evidence is preserved in validation_runs/ or code_audits/
6. **Scope is documented** — What's proven is explicit; limitations are named

All five must be true for a claim to be proven.

---

## Acceptance Criteria for Boundary Documentation

Phase 4 closure requires:

- [ ] All proven claims have evidence references
- [ ] All target-only items are explicitly marked (not aspiration, not claim)
- [ ] No hybrid claims (mixing proven + target)
- [ ] Scope limitations are documented for each proven capability
- [ ] Future work (target-only) is on explicit roadmap with timeline
- [ ] Evidence artifacts are all accessible and archived
- [ ] No reader should confuse proven with target

This document is complete when all checkmarks pass.
