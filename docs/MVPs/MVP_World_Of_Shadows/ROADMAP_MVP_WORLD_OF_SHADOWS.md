# ROADMAP_MVP_WORLD_OF_SHADOWS

## 1. Document purpose

This document defines the **execution-ready MVP roadmap** for **World of Shadows** based on the current implementation state, the existing slice contracts, and the architectural direction already present in the repository.

It is a **product and delivery roadmap**, not a future-vision document and not a platform-completeness plan.

Its purpose is to:

- define the **fastest credible learning path** for the MVP,
- keep the team focused on the **highest-risk product assumptions first**,
- separate **MVP-critical work** from platform ambition,
- turn the current implementation into a **controlled validation vehicle**,
- and provide a practical route to a first launchable vertical slice.

---

## 2. Executive summary

### Product thesis

**World of Shadows** is not a chatbot and not a generic AI roleplay tool.
It is an **authored interactive dramatic runtime** that turns bounded narrative source material into a playable, truth-governed, scene-led experience.

### MVP thesis

The MVP must prove one thing before further platform build-out:

> users can perceive a meaningful qualitative difference between a truth-bound dramatic runtime and generic LLM chat.

### First MVP slice

The first MVP slice is:

- **Module:** `God of Carnage`
- **Mode:** single guided interactive dramatic experience
- **Runtime posture:** engine-authoritative, AI-proposal-driven, validation-and-commit based

### Core learning goal

The MVP is **not** a broad product launch.
It is a **controlled learning experiment** that must answer these questions early:

1. Do users actually feel the difference?
2. Does free input still feel playable inside a shaped dramatic runtime?
3. Does validation/commit create **visible experiential value**, not just engineering correctness?

If these are not true, additional platform sophistication is not MVP progress.

---

## 3. Current implementation baseline

The repository already contains substantial MVP-relevant infrastructure.
This roadmap assumes those assets are real and must be reused, not replaced.

### 3.1 Already implemented or materially present

- **Authoritative runtime direction** documented in `docs/governance/adr-0001-runtime-authority-in-world-engine.md`
- **LangGraph-based turn runtime** in `ai_stack/langgraph_runtime.py`
- **Bounded dramatic slice contracts** in:
  - `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md`
  - `docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md`
  - `docs/MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md`
- **MCP control-plane surface** in `ai_stack/mcp_canonical_surface.py`
- **Governed retrieval and provenance shaping** in:
  - `ai_stack/rag.py`
  - `ai_stack/retrieval_governance_summary.py`
- **Scene direction and dramatic parameter logic** in:
  - `ai_stack/scene_director_goc.py`
  - `ai_stack/semantic_move_interpretation_goc.py`
  - `ai_stack/dramatic_effect_gate.py`
  - `ai_stack/social_state_goc.py`
  - `ai_stack/character_mind_goc.py`
- **Backend / frontend / administration-tool / world-engine service separation**
- **Existing test and report discipline**, including slice, runtime, MCP, and acceptance-oriented artifacts

### 3.2 Existing complexity warning

The current stack is already **more mature and more complex** than a typical MVP stack.
That is both an asset and a risk.

Asset:
- the system already has serious runtime discipline,
- truth/validation/commit are not hand-wavy,
- the implementation is closer to a real runtime than to a prototype.

Risk:
- the team could continue improving architecture **without learning whether users feel the value**,
- implementation depth could become a substitute for product validation,
- platform completeness could outrun MVP learning speed.

### 3.3 What this means

The project is **past the idea stage**.
The main challenge is no longer “can we wire together LLM calls?”
The main challenge is:

> turning an already serious but partly distributed runtime into the **smallest possible believable product test**.

---

## 4. Core problem, target users, and MVP framing

### 4.1 Core problem

Most AI narrative products fail in one of four ways:

- they produce fluent text without real scene control,
- they lose continuity across turns,
- they allow AI output to act as de facto truth,
- or they cannot be safely inspected, validated, and improved.

World of Shadows addresses this by combining:

- authored content,
- explicit runtime state,
- bounded AI proposals,
- validation and commit seams,
- and operator-visible diagnostics.

### 4.2 Target users for the MVP

The MVP is **not** aimed first at a broad consumer audience.
The first target users are:

1. **Internal operators and builders** who need to verify that the runtime actually works.
2. **Design-sensitive early evaluators** who can judge whether the experience feels like directed drama rather than chat.
3. **Narrative / interactive media stakeholders** who can evaluate whether the runtime has product potential.

### 4.3 MVP user promise

The MVP promise is intentionally narrow:

> “You can enter a live dramatic scene through free input, the system interprets your move as part of the scene, characters respond coherently, the engine preserves truth, and later turns still remember what happened.”

If the MVP cannot do that reliably in one slice, everything broader is premature.

### 4.4 Important framing constraint

`God of Carnage` is a **runtime proof module**, not a proof of broad market pull.

Success in this module validates:
- runtime differentiation,
- dramatic controllability,
- continuity,
- and the feel of truth-bound interaction.

It does **not** automatically validate:
- mainstream genre appeal,
- broad audience demand,
- or general market-scale content attractiveness.

---

## 5. Critical assumptions to validate

The previous roadmap treated the core product assumption too late in the sequence.
That is corrected here.

### 5.1 Core assumption set

The MVP must explicitly validate three assumptions:

#### H1 — Perceived qualitative difference

> Users can perceive materially higher value in a **truth-bound, scene-led, authored dramatic runtime** than in a generic LLM-driven conversational experience.

#### H2 — Free-input acceptability inside shaped drama

> Users do not experience dramatic shaping, scene boundaries, and runtime validation as frustrating loss of freedom.

#### H3 — Validation/commit becomes visible value

> Validation and commit create player-visible benefits such as continuity, consequence, credibility, and remembered actions.

### 5.2 What would falsify the MVP direction

The MVP direction is threatened if testers consistently report that the experience is mainly:

- “just chat with nicer phrasing,”
- “obviously shaped in a restrictive way,”
- “not meaningfully different from generic roleplay,”
- “coherent only for one or two turns,”
- or “engineering-heavy but experientially flat.”

### 5.3 What would count as a positive signal

The MVP has earned the right to continue if testers consistently report things like:

- “it felt like the scene really held together,”
- “what I said mattered later,”
- “characters felt bounded rather than random,”
- “it felt more directed than chat, but not dead,”
- “I understood that the system had rules, but it still felt alive.”

---

## 6. MVP scope definition

### 6.1 In scope

The MVP includes:

- one content slice: **God of Carnage**
- one authoritative runtime path
- free player input inside the bounded slice
- scene-grounded interpretation
- bounded retrieval of canonical slice context
- director-guided turn shaping
- AI proposal generation in structured form
- validation and commit before visible truth claims
- visible turn output for the player
- continuity across turns
- **minimum viable diagnostics** sufficient to inspect runtime behavior
- a minimal usable frontend to play and observe the slice
- a comparison-friendly test setup against a generic LLM baseline

### 6.2 Out of scope

The MVP does **not** include:

- multi-module open platform support
- broad MCP write surfaces
- open-world improvisation
- general-purpose authoring platform
- autonomous canon writing by AI
- research/canon-improvement workflow as part of launch scope
- large-scale multi-agent orchestration as a user-facing requirement
- large content expansion beyond the first slice
- cinematic polish before runtime dependability
- complex monetization or marketplace mechanics

### 6.3 Non-negotiable scope rule

If a feature does not directly improve one of these, it is not MVP work:

- perceived dramatic difference
- scene coherence
- truth safety
- continuity
- playability under free input
- inspectability for rapid iteration
- launchable demonstration value

### 6.4 Freeze rule

Until the core assumptions are tested with real users, the team must **freeze platform expansion** in these areas:

- research/canon-improvement depth
- broader MCP surface area
- generalized content platformization
- non-essential architecture polishing

---

## 7. Architecture mapping for the MVP

The MVP should be treated as a system of **explicit layers with bounded responsibilities**.
Only layers that are launch-critical belong in the MVP architecture map.

### 7.1 Functional architecture

#### A. Content authority layer
Owns:

- authored dramatic truth
- module assets
- slice structure
- scene-relevant narrative constraints
- publication status

Primary implementation anchors:

- backend content/module loading
- GoC authority assets
- vertical-slice contracts and freeze artifacts

#### B. Runtime authority layer
Owns:

- session state
- turn execution
- validation
- commit
- continuity
- failure handling
- replayable runtime truth

Primary implementation anchors:

- `world-engine`
- `ai_stack/langgraph_runtime.py`
- validation / commit / render seams

#### C. Dramatic orchestration layer
Owns:

- interpretation of user move in scene context
- scene assessment
- responder selection
- scene function selection
- pacing / silence / brevity shaping
- bounded dramatic proposal context

Primary implementation anchors:

- `scene_director_goc.py`
- `semantic_move_interpretation_goc.py`
- `social_state_goc.py`
- `character_mind_goc.py`
- `dramatic_effect_gate.py`

#### D. Retrieval and context layer
Owns:

- governed retrieval
- visibility class handling
- provenance shaping
- compact context delivery to the runtime

Primary implementation anchors:

- `rag.py`
- `retrieval_governance_summary.py`

#### E. Player interaction layer
Owns:

- session launch
- text input
- visible scene response
- lightweight session continuity view
- minimal evaluator-friendly observation flow

Primary implementation anchors:

- frontend play surface
- backend/play-service integration path

#### F. Minimum viable diagnostics layer
Owns only:

- what the runtime accepted
- what it rejected
- why a turn failed
- whether continuity is intact
- minimal operator-readable traceability

Primary implementation anchors:

- existing diagnostics seams
- existing runtime reports / projections
- thin read-only inspection surfaces

### 7.2 Explicitly excluded from the MVP architecture map

The following may exist in the repository but are **not part of the MVP architectural commitment**:

- research/canon-improvement workflow
- generalized canon-improvement loops
- broader control-plane expansion beyond MVP operational needs
- non-essential experimentation infrastructure

These should be treated as **parked assets**, not active MVP obligations.

---

## 8. Dependencies and sequence logic

### 8.1 Hard dependency chain

The MVP depends on this execution order:

1. **Runtime path is stable enough to run controlled sessions**
2. **Minimal diagnostics exist to understand runtime behavior**
3. **A comparison-ready baseline test setup exists**
4. **Early evaluator sessions happen before more platform work**
5. **Only validated weaknesses are promoted into the next implementation cycle**

### 8.2 What does not need to be solved before the MVP test

The following do **not** need to be solved before the first real validation round:

- generalized authoring platform maturity
- long-term canon improvement pipeline maturity
- wide MCP surface completeness
- broad content scalability
- highly refined operator workbenches
- generalized multi-module architecture

### 8.3 Sequence correction

The previous sequencing mistake was:

> technical consolidation first, core product differentiation test later.

The corrected sequence is:

> enough runtime stability first, then immediate product differentiation testing, then targeted consolidation based on what users actually felt.

---

## 9. Lean validation strategy

This is the most important correction in the roadmap.

### 9.1 Validation principle

The MVP should not wait for “fully consolidated runtime maturity” before the central product test.

It should run the earliest credible comparison as soon as:

- the slice is playable,
- continuity works well enough for short sessions,
- failures are inspectable,
- and the player can complete a meaningful dramatic interaction.

### 9.2 Earliest credible learning experiment

Run a **controlled comparative test** with:

- the World of Shadows GoC slice
- a generic LLM baseline experience
- the same starting situation
- the same user goal framing
- the same time window or turn budget

### 9.3 Test audience

Use a small but decision-useful sample:

- 5–8 evaluators
- mix of internal operators and design-sensitive external testers
- optionally one or two users without theater affinity to expose false assumptions early

### 9.4 Questions the test must answer

#### Difference perception
- Did this feel meaningfully different from normal AI chat?
- If yes, what was different?

#### Freedom vs shaping
- Did your input feel free enough?
- Did you feel pushed into invisible rails?
- Did the boundaries feel productive or frustrating?

#### Consequence and continuity
- Did your earlier actions matter later?
- Did the system feel like it remembered and enforced consequences?

#### Replay / interest signal
- Would you want to replay or continue?
- Did the system feel alive or merely constrained?

### 9.5 Success threshold

The MVP passes this learning gate if the majority of evaluators can clearly articulate that the runtime felt:

- more coherent than generic chat,
- more consequence-aware than generic chat,
- acceptably bounded rather than frustratingly restricted,
- and worth continuing at least for the slice.

### 9.6 Failure threshold

The MVP must be reconsidered if evaluators mostly report that:

- the difference is weak or unclear,
- the boundaries feel restrictive rather than dramatic,
- the coherence benefit is not perceptible,
- or the setup is impressive architecturally but not compelling experientially.

---

## 10. MVP launch requirements

The MVP should only be considered launch-ready when all of the following are true:

### 10.1 Runtime requirements

- the authoritative runtime path works end-to-end
- validation and commit operate reliably in the slice
- continuity survives short evaluator sessions
- turn failure modes are inspectable without deep debugging

### 10.2 Experience requirements

- users can complete a meaningful short dramatic session
- responses feel scene-grounded rather than generic
- user actions create later-visible consequences
- character behavior feels bounded and coherent enough to sustain the illusion

### 10.3 Product-learning requirements

- the comparison test has been run
- the core assumptions H1–H3 have real evidence behind them
- the next implementation cycle is driven by observed user failure modes, not by architecture instinct alone

---

## 11. Implementation roadmap

The roadmap is intentionally front-loaded toward **learning before platform expansion**.

### Phase 0 — Freeze and refocus

**Objective:** stop accidental scope growth and align the team on the corrected MVP logic.

#### Deliverables
- roadmap updated around H1–H3
- research/canon-improvement removed from MVP core scope
- diagnostics narrowed to minimum viable diagnostics
- platform-expansion freeze communicated

#### Exit criteria
- everyone is aligned on the corrected success condition:
  - not “more architecture,”
  - but “clear evidence of experiential difference.”

---

### Phase 1 — Make the slice testable, not perfect

**Objective:** make the GoC slice stable enough for real evaluator sessions as fast as possible.

#### Deliverables
- one playable end-to-end runtime path
- stable session start and turn flow
- continuity across a short evaluator session
- minimum viable diagnostics for accepted/rejected/failed turns
- minimal frontend surface for evaluator use

#### Implementation priorities
- remove obvious runtime fragility that blocks real sessions
- prioritize user-visible continuity over internal elegance
- avoid building deeper operator tooling than needed
- avoid broadening architecture during this phase

#### Exit criteria
- a tester can play a short session without the system collapsing
- the team can understand obvious failures from the available diagnostics

---

### Phase 2 — Earliest differentiation test

**Objective:** validate H1–H3 before further architecture investment.

#### Deliverables
- generic LLM comparison setup
- evaluator session script
- scoring / feedback form
- 5–8 completed evaluator sessions

**Repository artifacts (comparison setup and facilitator materials):**

- Baseline chat CLI (Arm B): `scripts/mvp_generic_llm_baseline_chat.py`
- Frozen opening brief: `scripts/data/mvp_goc_baseline_opening.json`
- Facilitator script + H1–H3 feedback form: `docs/validation/mvp_comparative_evaluation_playbook.md`
- synthesis of findings by assumption:
  - H1 perceived difference
  - H2 freedom vs shaping
  - H3 visible value of validation/commit

#### Exit criteria
- real evaluator evidence exists
- the team knows whether the runtime advantage is:
  - clear,
  - weak,
  - or currently invisible

#### Decision rule
- if the difference is weak, do **not** expand the platform
- first fix the experiential gap

---

### Phase 3 — Targeted correction pass

**Objective:** respond only to failures that block MVP viability.

#### Examples of valid work
- improve visible consequence carryover
- reduce free-input frustration
- tighten scene-grounded interpretation
- improve character boundedness where users perceived drift
- fix runtime seams that hurt the experience directly

#### Examples of invalid work
- broad canon-improvement workflow expansion
- generalized platform refactors without MVP relevance
- deep research tooling unrelated to evaluator findings
- wide MCP/control-plane growth

#### Exit criteria
- the worst real evaluator failure modes have been reduced
- the slice feels materially more convincing than before

---

### Phase 4 — MVP launch preparation

**Objective:** prepare the slice as a demonstrable MVP once the value signal is real.

#### Deliverables
- stable demo path
- minimum viable operator visibility
- concise narrative framing for the MVP
- documented limitations and known boundaries
- launch-ready evaluator/demo flow

#### Exit criteria
- the team can demonstrate the slice confidently
- the MVP communicates a clear product claim
- the runtime feels intentionally bounded, not merely unfinished

---

## 12. Milestones

### Milestone M1 — Testable slice

A short GoC session can be played end-to-end with inspectable failures.

### Milestone M2 — First differentiation evidence

The team has real evaluator evidence on whether users feel a difference from generic LLM chat.

### Milestone M3 — Corrected experiential weaknesses

The most important failures from the first evaluator round have been addressed.

### Milestone M4 — Launchable MVP

The slice is demonstrable, bounded, and backed by actual evidence rather than internal belief.

---

## 13. Prioritization framework

For every proposed task, ask:

### 13.1 Does it increase learning speed?
If no, it is probably not MVP work.

### 13.2 Does it improve one of the three core assumptions?
If no, deprioritize it.

### 13.3 Does it unblock real evaluator sessions?
If yes, prioritize it.

### 13.4 Is it architecture polishing without immediate product evidence?
If yes, freeze it.

### 13.5 Is it a nice-to-have because the stack already makes it tempting?
If yes, treat it as post-MVP unless proven otherwise.

---

## 14. Risks and responses

### Risk 1 — Users do not feel the difference
**Response:** run the comparison test early, not late.

### Risk 2 — Free input feels falsely free or frustratingly bounded
**Response:** test for this explicitly and tune the interaction contract before broader build-out.

### Risk 3 — Validation/commit remains invisible to players
**Response:** prioritize visible consequence and continuity over additional infrastructure depth.

### Risk 4 — The team keeps building because the architecture is interesting
**Response:** enforce the freeze rule and tie roadmap advancement to user evidence.

### Risk 5 — GoC gives false confidence about market pull
**Response:** treat GoC as runtime proof, not audience proof.

---

## 15. MVP success criteria

The MVP is successful if all of the following are true:

- the slice is playable end-to-end,
- continuity and consequence are visible to players,
- users can perceive a meaningful difference from generic LLM chat,
- dramatic shaping feels acceptable rather than frustrating,
- the experience is strong enough to justify another iteration cycle,
- and the next roadmap step is based on evidence, not intuition.

---

## 16. What comes after the MVP

Only after H1–H3 are positively supported should the roadmap expand toward:

- additional modules
- stronger diagnostics and operator tooling
- broader MCP/control-plane maturity
- authoring workflow maturation
- research/canon-improvement workflow activation
- multi-module and platform generalization

Until then, these remain **post-MVP possibilities**, not active MVP obligations.

---

## 17. Final decision rule

The MVP is not complete when the architecture looks mature.
It is complete when the team has real evidence that:

> users can feel the value of a truth-bound dramatic runtime, tolerate its boundaries, and perceive consequence and continuity as better than generic AI chat.

That is the decision threshold that matters.
