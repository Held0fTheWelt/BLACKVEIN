# ROADMAP_MVP_WOS_VSL

## 1. Executive Summary

**Product:** World of Shadows  
**MVP cut:** **WOS_VSL** = *World of Shadows Vertical Slice*  
**Positioning:** An authored dramatic runtime for interactive story experiences, where authored truth, runtime authority, AI-driven realization, and operator control are explicitly separated.

**Core idea:**  
Turn authored dramatic material into a playable, truth-bound interactive runtime in which player input produces meaningful scene consequences, while the system preserves continuity, role integrity, and authorial control.

**Current implementation baseline:**
- `world-engine` as the authoritative runtime
- `ai_stack` with LangGraph-based turn orchestration, retrieval governance, MCP surface, and research scaffolding
- `backend` for API and integration concerns
- `administration-tool` for governance, review, diagnostics, and publishing
- `writers-room` as the authored content path
- `frontend` as the player-facing experience layer
- a first vertical slice currently centered on **God of Carnage** as the proving ground

This is **not** a zero-to-one ideation phase anymore. The job is to cut a disciplined MVP path out of an already ambitious system.

**Hard recommendation:**  
Do **not** build the full platform vision next.  
The MVP must validate that the runtime can deliver a **compelling, inspectable, replayable, authored interactive dramatic experience** for a narrow use case.

---

## 2. Problem, User, and Critical Assumption

### 2.1 Problem

Most AI story systems fail in one or more of the following ways:

- fluent text but weak dramatic progression
- continuity loss across turns
- blurred boundaries between authored truth, retrieved context, and model improvisation
- poor inspectability and poor trustworthiness
- weak authorial control over the resulting experience

World of Shadows exists to solve this by treating interactive drama as a **runtime and governance problem**, not just a prompting problem.

### 2.2 Initial Target User

The MVP should **not** target everyone interested in AI storytelling.

#### Primary MVP user
**Narrative/AI-experiment-friendly advanced users** who are willing to engage with a curated dramatic experience and value:
- coherence over randomness
- inspectability over raw novelty
- authored structure over open-ended chaos
- replayable consequences over generic chatbot conversation

#### Secondary internal user
**Author/operator/admin users** who need to create, review, publish, inspect, and improve modules through a controlled workflow.

### 2.3 Critical Assumption to Validate

**Critical assumption:**  
Users will perceive a tightly bounded, authored, AI-mediated dramatic runtime as meaningfully better than a generic AI roleplay/chat experience.

In practical MVP terms:

> If a player is given a tightly authored, well-governed dramatic module and a stable runtime, they will report that the experience feels more coherent, more consequential, and more worth replaying than ad hoc AI roleplay.

---

## 3. Key Learnings Already Present in the Project

### 3.1 Runtime authority matters
The `world-engine` is already defined as the authoritative runtime. This remains non-negotiable.

### 3.2 AI must not be the source of truth
The stack already leans toward AI as proposal/orchestration rather than truth storage. This is one of the strongest current decisions.

### 3.3 Retrieval requires governance
The presence of retrieval governance, evidence summaries, and visibility distinctions shows that context control is already understood as a system concern.

### 3.4 The product needs authored structure
The current slice demonstrates that the opportunity is not generic sandbox generation. It is authored dramatic structure with controlled runtime interpretation.

### 3.5 Operator visibility is part of product quality
Diagnostics, traces, admin surfaces, MCP shaping, and research artifacts are part of what makes the system improvable.

### 3.6 Scope risk is the biggest current business risk
The implementation is already broad enough that the main danger is not technical impossibility. The danger is trying to operationalize the full platform before validating the narrowest compelling use case.

### 3.7 MCP must be canalized, not merely expanded
The right next move is **not** more undifferentiated MCP surface area.  
The right move is a **suite-based MCP structure** that separates reading, authoring, diagnostics, AI evaluation, and high-risk control paths.

---

## 4. Phase 0 Status and Scope Freeze

This document is itself the **primary Phase 0 scope artifact**.

### 4.1 Completed by this document
This roadmap already completes the following Phase 0 outcomes:
- MVP cut is defined as **WOS_VSL**
- MVP problem, target users, and critical assumption are defined
- in-scope vs out-of-scope boundaries are defined
- initial MCP suite family is defined
- milestone logic is defined
- launch posture is defined
- pilot decision logic is defined

### 4.2 Phase 0 closeout (repository)
The following are recorded in-repo:

1. **Owner table by subsystem** — [ROADMAP_MVP_WOS_VSL_OWNER_TABLE.md](ROADMAP_MVP_WOS_VSL_OWNER_TABLE.md) (role-based owners; named assignees to be filled when staffing is fixed).
2. **Named slice record** — same document: MVP module id `god_of_carnage`, aligned with [VERTICAL_SLICE_CONTRACT_GOC.md](../MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md). Mirror the module id in your external project tracker if used.

### 4.3 Required owner table
Phase 0 is only fully closed when the project records named owners for at least:
- runtime authority (`world-engine`)
- orchestration / AI runtime (`ai_stack`)
- API / integration (`backend`)
- admin / governance (`administration-tool`)
- authored content flow (`writers-room`)
- player experience (`frontend`)
- MCP suite architecture
- pilot evaluation / reporting

If exact people are not yet assigned, a role-based owner table must be recorded before Phase 1 starts — see [ROADMAP_MVP_WOS_VSL_OWNER_TABLE.md](ROADMAP_MVP_WOS_VSL_OWNER_TABLE.md).

### 4.4 Module status for MVP
The selected module posture is:
- **single vertical slice**
- **currently represented by the existing proving-ground material**
- **expected to be replaced later with license-free content**
- **not blocked by that future replacement for purposes of MVP runtime validation**

---

## 5. MVP Definition

### 5.1 What the MVP is

> A single-module, single-session interactive dramatic experience with authored truth, authoritative runtime state, visible turn consequences, basic diagnostics, a minimal publishing/review path, and a bounded MCP surface for operator, author, and AI workflows.

In product terms, this means:
- one curated dramatic module
- one player-facing experience path
- one authoritative runtime path
- one admin/operator path sufficient to inspect and improve it
- one evaluation loop to learn whether this is actually better than generic AI roleplay
- one suite-based MCP cut that improves control and observability without becoming a second product

### 5.2 What the MVP is not
The MVP is **not**:
- a broad multi-world content platform
- a marketplace
- an open-ended narrative sandbox
- a generalized multi-agent storytelling operating system
- a large-scale content authoring suite
- a full MCP ecosystem product
- a multiplayer social platform
- a fully dynamic world simulator

### 5.3 MVP Success Condition
The MVP succeeds if it can demonstrate all of the following:
1. A player can enter a curated module and complete a meaningful dramatic interaction.
2. The runtime maintains stable continuity across turns.
3. The system shows inspectable traces or diagnostics for operator review.
4. A small but real tester group rates the experience as more coherent and consequential than ordinary chatbot roleplay at or above the thresholds defined in Section 10.
5. The team can iterate on the module through a governed authoring/review/publish loop without major manual firefighting.
6. MCP interactions are clearly structured by suite and no longer depend on an undifferentiated tool bucket.

---

## 6. Architecture Mapping for the MVP

### 6.1 MVP Functional Components

#### A. Module Authoring and Publishing
Purpose: Create and govern the authored dramatic module.

**Existing basis:**
- `writers-room`
- `administration-tool`
- backend publishing paths
- content contracts for scenes, relationships, triggers, endings, interventions

**Required MVP outcome:**
- one publishable module in a clean canonical form
- review + approval path
- no draft/published ambiguity at player runtime

#### B. Runtime Authority
Purpose: Hold authoritative session truth and commit legal state changes.

**Existing basis:**
- `world-engine`
- runtime manager
- canonical runtime contract work
- session state / turn execution surfaces

**Required MVP outcome:**
- single source of runtime truth
- deterministic commit boundaries
- legal scene progression
- stable turn outcome structure

#### C. Turn Orchestration
Purpose: Interpret input, retrieve context, build dramatic framing, generate candidate output, validate, and commit.

**Existing basis:**
- `ai_stack/langgraph_runtime.py`
- semantic move interpretation
- dramatic effect gate
- scene director logic
- retrieval governance summary

**Required MVP outcome:**
- one stable turn graph for the MVP slice
- bounded fallback behavior
- structured outputs at key seams
- diagnostics sufficient for debugging

#### D. Retrieval / Context Governance
Purpose: Supply authored and runtime-relevant context without context drift.

**Existing basis:**
- retrieval governance summary
- RAG infrastructure
- evidence controls

**Required MVP outcome:**
- only the necessary retrieval for the selected module
- clear separation between published canon and runtime/session context
- minimal, understandable provenance

#### E. Player Experience Layer
Purpose: Let a user play the module with acceptable friction.

**Existing basis:**
- `frontend`
- launcher/bootstrap/play shell flow
- backend / play-service integration

**Required MVP outcome:**
- login/start/play flow that works consistently
- turn-based or quasi-turn-based interaction
- visible session state cues where useful
- no unnecessary operator complexity in the player experience

#### F. Operator / Admin Experience
Purpose: Review outcomes, inspect failures, publish updates, and classify issues.

**Existing basis:**
- `administration-tool`
- governance, inspection, and workbench patterns

**Required MVP outcome:**
- one clear inspection surface for the MVP module
- enough diagnostics to classify failures
- minimal but usable publishing/review flow

#### G. Evaluation / Research Loop
Purpose: Learn whether the MVP is actually working.

**Existing basis:**
- research contracts / research store / research graph
- reports and test artifacts

**Required MVP outcome:**
- lightweight evaluation runs
- qualitative player feedback capture
- operator classification of runtime issues
- a small closed-loop improvement process

#### H. Suite-based MCP Surface
Purpose: Canalize control, reading, authoring, and AI-facing workflows into distinct suites instead of one overloaded tool surface.

**Required MVP outcome:**
- a bounded set of suites with explicit responsibilities
- a clearer split between resources, prompts, tools, logging, and progress
- fewer read-style tools where resources are the better form
- high-risk writes kept narrow and reviewable

---

## 7. MVP MCP Suite Architecture

### 7.1 MVP principle
For the MVP, MCP should be treated as a **structured control plane**, not as a second runtime and not as a generic tool dump.

### 7.2 MVP suites

#### `wos-admin`
For admin, operations, diagnostics, review, and publishing oversight.

**Use for:**
- session inspection
- runtime diagnostics
- publish state visibility
- review workflows
- audit views

**Capability mix:**
- resources: yes
- prompts: yes
- tools: yes, but narrow
- logging: yes
- progress: yes for long-running diagnostics or audits

#### `wos-author`
For authoring and redaction-facing workflows.

**Use for:**
- draft inspection
- module contract review
- scene and character review
- change proposals
- review requests

**Capability mix:**
- resources: yes
- prompts: yes
- tools: yes, bounded to draft/review operations
- logging: useful
- progress: optional
- roots: deferred unless a concrete workspace flow truly needs them

#### `wos-ai`
For research, evaluation, comparison, and improvement suggestions.

**Use for:**
- continuity analysis
- rejection analysis
- comparison bundles
- proposal/evidence review
- structured evaluation jobs

**Capability mix:**
- resources: yes
- prompts: yes
- tools: very few, mostly bounded evaluation jobs
- logging: yes
- progress: yes

#### `wos-runtime-read`
For read-only access to authoritative runtime truth.

**Use for:**
- session state
- timelines
- turn traces
- continuity projections
- guard outcomes

**Capability mix:**
- resources: primary
- prompts: limited
- tools: minimal
- logging: useful
- subscriptions: optional, only if they materially help operator workflows

#### `wos-runtime-control`
For narrow, high-authority control actions only.

**Use for:**
- controlled session start support
- pause/resume or replay hooks if already justified
- bounded diagnostic triggers
- no broad mutation surface

**Capability mix:**
- tools: very small set
- resources: little to none
- prompts: optional
- logging: yes
- progress: if long-running actions exist

### 7.3 Not prioritized first
- `sampling/createMessage`
- `roots` without a concrete authoring/workspace need
- many write tools

### 7.4 MVP MCP rules
1. Read paths belong in **resources** first.
2. Repeated workflows belong in **prompts**.
3. Tools are for clear actions, not mixed read-think-write bundles.
4. High-risk writes remain rare and highly authorized.
5. Suites map to responsibilities, not to arbitrary technical grouping.
6. MCP must improve trainability, authorization, and traceability rather than complicate them.

---

## 8. Component Dependencies

### 8.1 Dependency chain
1. **Canonical module content**
2. **Publishing and content availability**
3. **Runtime authority and session lifecycle**
4. **Turn graph orchestration**
5. **Frontend play flow**
6. **Operator diagnostics**
7. **Evaluation and improvement**

### 8.2 Hard dependencies
- The player experience depends on a published canonical module.
- The turn graph depends on runtime authority and content availability.
- Diagnostics depend on structured runtime outputs.
- MCP suites depend on stable ownership boundaries, but do **not** block the first playable slice.
- Evaluation depends on usable logs/traces and repeatable sessions.

### 8.3 Non-essential dependencies for MVP
These should be postponed unless they directly unblock the MVP:
- generalized multi-module support
- advanced MCP breadth beyond the suite cut above
- extensive research automation
- deep long-tail content ingestion
- advanced multi-agent decomposition
- broad analytics dashboards
- scalability engineering beyond small pilot loads

---

## 9. Clear MVP Boundary vs Future Phases

### 9.1 In Scope for MVP
- one module
- one player path
- one authoritative runtime execution path
- one minimal review/publish workflow
- one minimal inspection workflow
- one validated learning loop
- one bounded MCP suite family with explicit responsibilities

### 9.2 Explicitly Out of Scope
- multi-tenant content platform
- broad module marketplace
- generalized authoring studio productization
- multiplayer runtime
- broad world simulation
- large-scale personalization
- complex recommendation systems
- full autonomous agent ecosystems
- large roots-based workspace integration
- client-sampling-driven orchestration

---

## 10. Validation Strategy, Thresholds, and Metrics

### 10.1 Validation question

> Does a tightly authored, governed dramatic runtime create a noticeably better player experience than generic AI roleplay for a narrow dramatic use case?

### 10.2 Core experiments

**In-repo instruments:** operator review sheet — [pilot/MVP_OPERATOR_REVIEW_SHEET.md](../../pilot/MVP_OPERATOR_REVIEW_SHEET.md); MCP suite map for misrouting — [mcp/MVP_SUITE_MAP.md](../../mcp/MVP_SUITE_MAP.md); static metrics — `ai_stack/wos_vsl_mcp_metrics.py` and `ai_stack/tests/test_wos_vsl_mvp_closure.py`.

#### Experiment 1 — Internal controlled playtest
Measure:
- perceived coherence
- perceived consequence
- perceived character consistency
- felt dramatic tension
- desire to replay or continue
- comparison against generic AI roleplay

#### Experiment 2 — Operator failure classification
Failures are classified into:
- runtime legality failure
- continuity failure
- retrieval/context failure
- character inconsistency
- pacing/dramatic weakness
- UX friction
- content gap
- MCP surface confusion / control-plane ambiguity

#### Experiment 3 — Comparative benchmark
Compare:
- the curated WoS runtime slice
- a generic chatbot-style roleplay baseline

#### Experiment 4 — Replay/trace review
Check:
- preservation of authorial shape across runs
- acceptable variation bounds
- explainability of weak outcomes from traces
- clean attribution of MCP interactions to the correct suite

#### Experiment 5 — MCP operability review
Check whether operator/author/AI-facing users can understand which suite they should use without guesswork.

### 10.3 Go / no-go thresholds for pilot validation

The pilot is a **Go** for limited MVP launch only if all launch-critical thresholds below are met:

| Metric | Threshold | Measurement method |
|---|---:|---|
| Session start success rate | >= 95% | Automated run log across pilot sessions |
| Turn success rate | >= 90% | Runtime outcome logs |
| Severe continuity break rate | <= 10% of reviewed sessions | Operator manual classification |
| WoS preferred over baseline for coherence | >= 65% of comparative testers | Standardized post-session survey |
| WoS preferred over baseline for consequence | >= 60% of comparative testers | Standardized post-session survey |
| Average coherence rating | >= 4.0 / 5 | Standardized post-session survey |
| Average character consistency rating | >= 4.0 / 5 | Standardized post-session survey |
| Replay interest | >= 50% answer “would replay / continue” | Standardized post-session survey |
| Operator diagnosability of weak runs | >= 80% of weak runs classifiable without engineering deep-dive | Operator review sheet |
| MCP suite misrouting rate | <= 15% of MCP-reviewed interactions | Manual classification against intended suite map |
| High-risk write tool count in MVP | <= 5 exposed write tools total | Static interface inventory |
| Read-via-resource share | >= 70% of stable read surfaces | Interface inventory + logs |

### 10.4 Stretch targets
These do not block MVP launch but indicate strong signal:
- WoS preferred over baseline for coherence >= 75%
- WoS preferred over baseline for consequence >= 70%
- Replay interest >= 65%
- MCP suite misrouting <= 10%

### 10.5 MCP metric definitions

#### Suite misrouting rate
**Definition:**  
The share of reviewed MCP interactions in which the user or operator chose a suite that was not the intended home of the workflow according to the MVP suite map.

**Measurement method:**  
Manual classification during pilot review on a bounded sample of MCP interactions.  
The intended suite map for misrouting classification is the suite responsibility table defined in Section 7.2.  
Formula:

`misrouted_interactions / reviewed_interactions`

#### Read-via-resource share
**Definition:**  
The share of stable read surfaces exposed as resources rather than tools.

**Measurement method:**  
Static inventory of exposed MCP surfaces at release candidate time.  
Formula:

`stable_read_surfaces_exposed_as_resources / all_stable_read_surfaces`

#### High-risk write tool count
**Definition:**  
Count of write-capable tools that can mutate live or publish-relevant state.

**Measurement method:**  
Static interface inventory at release candidate time.

#### Prompt adoption for recurring workflows
**Definition:**  
Share of recurring operator/author/AI workflows that have a dedicated prompt surface instead of free-form repeated tool usage.

**Measurement method:**  
Manual workflow inventory.  
This is tracked as an operational maturity metric, not a launch blocker.

---

## 11. Recommended MVP Architecture Cut

### 11.1 Recommended MVP stack

#### Canonical content path
`writers-room -> administration-tool -> backend published module surface`

#### Runtime path
`frontend -> backend/play integration -> world-engine authoritative session -> ai_stack turn graph -> authoritative commit`

#### Inspection path
`world-engine / ai_stack structured diagnostics -> administration-tool operator view`

#### MCP control-plane path
`wos-admin / wos-author / wos-ai / wos-runtime-read / wos-runtime-control`

#### Evaluation path
`session traces + operator classifications + player feedback + MCP suite usage evidence -> improvement loop`

### 11.2 Architectural principles
1. **One source of runtime truth**
2. **One stable turn execution path**
3. **One published content truth**
4. **One minimal operator inspection surface**
5. **One bounded MCP suite family**
6. **One feedback loop that leads to real iteration**

### 11.3 Technical simplifications
- only one canonical content package
- minimal retrieval surface
- bounded MCP suite cut, not full MCP breadth
- no speculative multi-agent expansion unless already necessary
- no generalized content taxonomy expansion beyond the chosen slice
- no premature scaling infrastructure
- no broad plugin surface

---

## 12. Prioritized Roadmap

### Phase 0 — MVP Cut and Freeze
**Goal:** Stop platform sprawl and define the exact MVP path.

**Deliverables**
- written MVP scope decision
- selected vertical slice module record
- explicit in-scope vs out-of-scope list
- canonical success criteria
- owner list for each core subsystem
- selected MVP MCP suites and responsibilities

**Exit criteria**
- no ambiguity about what the MVP includes
- no ambiguity about what is deferred
- no ambiguity about which suite owns which responsibility

### Phase 1 — Canonical Content and Runtime Contract Hardening
**Goal:** Make the content and runtime seams stable enough to support reliable playtests.

**Deliverables**
- clean published module contract
- stable runtime contract for session start and turn execution
- clearly defined legal scene/state transitions
- removal of ambiguous draft/published runtime paths

**Exit criteria**
- the selected module can be started consistently
- turns return stable structured outcomes
- runtime legality is inspectable

### Phase 2 — End-to-End Playable Slice
**Goal:** Deliver a working player experience for the selected module.

**Deliverables**
- stable launch/start/play flow
- usable player shell
- basic UX for interactive turns
- visible progression through the module

**Exit criteria**
- a user can begin and complete a meaningful session without operator intervention
- obvious UX dead ends are removed

### Phase 3 — MCP Suite Cut for MVP
**Goal:** Replace an overloaded tool surface with a bounded, understandable suite structure.

**Deliverables**
- suite map approved
- read paths migrated to resources where appropriate
- recurring workflows captured as prompts where appropriate
- high-risk write tools reduced and clearly authorized
- logging/progress conventions defined for long-running operations

**Exit criteria**
- each important MCP interaction has a clear suite home
- resources, prompts, and tools are no longer arbitrarily mixed
- operator confusion is materially reduced

### Phase 4 — Operator Inspection and Learning Loop
**Goal:** Make the MVP improvable rather than merely demoable.

**Deliverables**
- one operator inspection surface
- turn/trace review for problematic runs
- failure classification workflow
- publish-fix-retest loop
- suite-usage diagnostics for MCP operations

**Exit criteria**
- weak sessions can be diagnosed
- fixes can be prioritized based on evidence rather than intuition
- suite confusion is visible rather than hidden

### Phase 5 — Controlled Pilot Validation
**Goal:** Test the critical assumption with a small but real user set.

**Deliverables**
- controlled pilot cohort
- feedback instrument
- baseline comparison against generic roleplay
- summary report of findings against explicit thresholds

**Exit criteria**
- threshold-based Go / no-go decision is possible
- top friction points and top delight points are ranked

### Phase 6 — MVP Launch
**Goal:** Release the MVP to a limited audience with a stable operational posture.

**Deliverables**
- launch-ready module
- stable runtime path
- basic monitoring and diagnostics
- operator workflow for triage and fixes
- launch documentation
- stable MVP MCP suite cut

**Exit criteria**
- the MVP can be used without constant engineering intervention
- the team can observe and improve it in short cycles

---

## 13. Concrete Milestones and Dependencies

### Milestone M1 — MVP Scope Locked
**Depends on:** nothing  
**Outcome:** fixed scope, fixed slice, fixed goal, fixed suite map, owner table pending closeout

### Milestone M2 — Canonical Slice Ready
**Depends on:** M1  
**Outcome:** one publishable, canonical module with no runtime ambiguity

### Milestone M3 — Stable Runtime Contract
**Depends on:** M2  
**Outcome:** session start and turn handling are stable and observable

### Milestone M4 — End-to-End Play Experience
**Depends on:** M3  
**Outcome:** player can complete the slice

### Milestone M5 — MVP MCP Suite Cut Ready
**Depends on:** M3  
**Outcome:** bounded suites with clear responsibilities and reduced tool chaos

### Milestone M6 — Inspection Workflow Active
**Depends on:** M4 and M5  
**Outcome:** operators can classify and fix weak runs

### Milestone M7 — Pilot Learning Captured
**Depends on:** M6  
**Outcome:** the critical assumption is validated or falsified against explicit thresholds

### Milestone M8 — Limited MVP Launch
**Depends on:** M7  
**Outcome:** launch with known constraints and a learning roadmap

---

## 14. Concrete Technical Implementation Priorities

### Priority A — Canonical turn path hardening
Focus:
- stable turn envelopes
- stable commit semantics
- legal scene progression
- structured diagnostics at critical seams

### Priority B — End-to-end experience reliability
Focus:
- login/start/play flow
- session creation
- launcher/bootstrap shell
- graceful handling of missing module or invalid state conditions

### Priority C — MCP suite restructuring
Focus:
- explicit suite boundaries
- read-as-resource migration
- prompt-first handling of recurring workflows
- minimal write surfaces
- suite-level logging and progress semantics

### Priority D — Published truth discipline
Focus:
- clear published content path
- no mixed truth sources at playtime
- explicit handling of module-not-found / invalid / no-start-scene cases

### Priority E — Operator visibility
Focus:
- compact operator trace view
- guard outcomes
- validation outcomes
- fallback indicators
- issue classification
- MCP suite usage visibility

### Defer unless they directly unblock learning
- broad MCP feature expansion beyond the suite cut
- broad agent ecosystem work
- large-scale content expansion
- deep business polish
- scalability engineering beyond pilot needs

---

## 15. Risks and Mitigations

### Risk 1 — Scope inflation
**Mitigation:** every task must justify how it improves the single-module MVP.

### Risk 2 — Runtime truth fragmentation
**Mitigation:** keep `world-engine` authoritative, tighten turn contracts, reduce ambiguous surfaces.

### Risk 3 — Great architecture, weak player experience
**Mitigation:** early comparative playtests against generic roleplay.

### Risk 4 — Good sessions but poor inspectability
**Mitigation:** structured diagnostics before wider release.

### Risk 5 — MCP suite proliferation without discipline
**Mitigation:** keep the MVP suite family small and purpose-driven.

### Risk 6 — Tool chaos survives under new names
**Mitigation:** migrate read paths into resources, recurring workflows into prompts, and keep tools action-specific.

### Risk 7 — Premature generalization
**Mitigation:** optimize for one slice first, generalize after validated learning.

---

## 16. Capacity Assumption for MVP Delivery

This roadmap assumes a **small senior core team**, roughly equivalent to:

- 1 technical lead / architect
- 1 runtime / backend engineer
- 1 frontend / UX engineer
- 1 narrative / content / product owner
- shared part-time support for QA / pilot operations

Under that staffing assumption, a realistic sequencing is:

- **Phase 0–1:** short alignment + hardening sprint block
- **Phase 2:** playable slice sprint block
- **Phase 3:** MCP suite restructuring in parallel with late Phase 2 / early Phase 4, not blocking first playability
- **Phase 4:** operator-learning loop sprint block
- **Phase 5:** short controlled pilot
- **Phase 6:** limited launch after threshold review

This is intentionally described in **sequence blocks**, not fake calendar precision.  
The purpose is to force capacity realism, not theater.

---

## 17. MVP Launch Plan

### 17.1 Launch posture
Launch narrow, not loud.  
This is a **limited MVP release**, not a mass-market launch.

### 17.2 Suggested launch framing
Position it as:
- a curated interactive dramatic experience
- not a general AI chat toy
- not an infinite sandbox
- a controlled, replayable, authored runtime experiment

### 17.3 Launch checklist
- module published and locked
- end-to-end flow stable
- operator inspection ready
- feedback capture ready
- incident/rollback runbook ready
- known limitations documented
- MVP MCP suites frozen and documented

---

## 18. Decision Rule After MVP

### Path A — Double down
If pilot thresholds are met and operators can improve the system efficiently:
- invest in runtime hardening
- deepen character/direction quality
- prepare second module
- expand MCP suites only where real workflow pressure exists

### Path B — Refocus
If the experience is promising but too expensive or too fragile:
- simplify architecture around the proven value
- cut low-leverage complexity
- narrow the product promise further
- shrink MCP breadth again if needed

### Path C — Reassess
If users do not clearly prefer the experience over generic roleplay:
- do not expand platform scope
- identify whether the failure is content, UX, runtime differentiation, or control-plane friction
- revise the product thesis before further build-out

---

## 19. Final Recommendation

The MVP should not be “World of Shadows, the full platform.”  
It should be:

> **One authored dramatic runtime slice that proves this architecture creates a better experience than generic AI roleplay, while remaining inspectable, authorizable, trainable, and improvable by a small team.**

The suite-based MCP cut belongs inside this MVP because it directly improves:
- traceability
- authorization
- workflow clarity
- evaluation quality
- long-term operability

That is the right MVP.

Everything else belongs to the next phase.
