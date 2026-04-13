# Architecture Decisions

## ADR-001 — Compiled Narrative Package is the only runtime content authority

**Decision**  
Runtime must consume only approved compiled packages.
Raw authored source, research outputs, and draft patches are never read directly by live runtime execution.

**Consequences**
- promotion becomes a formal act
- preview builds are first-class
- rollback becomes feasible
- authored source and runtime stability are cleanly separated

---

## ADR-002 — Package versions are immutable and append-only

**Decision**  
A package version, once built and stored under `versions/<package_version>/`, is immutable.
`active/` is a pointer to a version, never the storage location of mutable content.

**Consequences**
- package promotion is pointer movement plus event log
- rollback is pointer movement to an earlier version
- audit history is lossless
- preview vs active comparisons are reliable

---

## ADR-003 — Scene Packet is the execution contract, not a prompt convenience

**Decision**  
The model call must be built from a typed `NarrativeDirectorScenePacket`.
This is not optional retrieval context and not ad hoc prompt interpolation.

**Consequences**
- runtime model input is inspectable and testable
- policy, legality, actor scope, and constraints are explicit
- generation becomes reproducible enough for regression testing

---

## ADR-004 — Runtime model output is proposal-only until validator approval

**Decision**  
The model may suggest narrative text, triggers, and effects.
No suggestion is authoritative until output validation and engine legality checks pass.

**Consequences**
- the model cannot silently mutate truth
- blocked turns are first-class
- commit logic remains engine authority

---

## ADR-005 — Research may draft change, but may not publish change

**Decision**  
Research outputs may create findings, revision candidates, and draft patch bundles.
Research may never directly modify canonical runtime packages.

**Consequences**
- no AI-to-AI uncontrolled publish loop
- review and evaluation remain mandatory
- writers-room and admin stay meaningful in the content chain

---

## ADR-006 — Revision review uses a state machine, not loose status strings

**Decision**  
Revision lifecycle must be enforced through a formal workflow state machine with role permissions and side effects.

**Consequences**
- multi-operator work is safer
- approval paths become auditable
- system side effects like draft apply and evaluation launch can be attached to transitions

---

## ADR-007 — Revision conflicts are explicit governance objects

**Decision**  
Competing revision candidates targeting overlapping content units must create conflict records before draft apply.

**Consequences**
- no silent last-write-wins behavior
- operators can resolve conflicts deliberately
- revision batches remain inspectable

---

## ADR-008 — Validation strategy must be explicit and configurable

**Decision**  
Output validation must expose a strategy:
`schema_only`, `schema_plus_semantic`, or `strict_rule_engine`.

**Consequences**
- runtime behavior becomes transparent
- environments can trade latency for scrutiny
- test suites can target strategy-specific expectations

---

## ADR-009 — Evaluation is a promotion gate

**Decision**  
A preview package is not promotable only because it exists.
Promotion requires passing evaluation gates and manual approval.

**Consequences**
- quality becomes measurable
- package changes can be compared to active baseline
- regression risk is materially reduced

---

## ADR-010 — Governance workflows are event-driven

**Decision**  
Critical governance events must be emitted and may trigger admin banners, email, Slack, or webhooks.

**Consequences**
- operators do not need to manually poll all pages
- failed evaluations and urgent findings become visible
- async multi-role workflows become operational
---

## ADR-011 — Validation failures in live play must degrade gracefully

**Decision**  
A rejected model output must not produce a player-visible dead end.
Runtime must attempt corrective recovery and, if needed, emit a guaranteed safe fallback response.

**Consequences**
- every playable scene needs fallback content
- runtime needs explicit retry/fallback telemetry
- operator tooling must surface fallback spikes
- degraded quality is acceptable for continuity; broken turns are not

---

## ADR-012 — Corrective retry must provide actionable validation feedback

**Decision**  
Retry is not blind regeneration.
When validation fails, the runtime must produce actionable feedback describing the violation, the violated rule, and legal alternatives where available.

**Consequences**
- retry quality is materially better than blind re-roll
- validation feedback becomes a first-class contract
- semantic and rule-based validators must expose machine-usable violation details
- prompt assembly must support corrective context

---

## ADR-013 — Preview sessions must be isolated from active runtime

**Decision**  
Preview packages are executable only inside explicitly isolated preview sessions.
Active live sessions may never accidentally resolve against a preview package.

**Consequences**
- preview execution must use explicit session namespace or isolated loader
- reload semantics for active and preview paths must stay distinct
- admin actions must show whether a package is active or preview-only

---

## ADR-014 — Player affect uses enum-based signals, not one-off frustration booleans

**Decision**  
Any player-state interpretation seam should use a general affect model with enums and confidence values.
Frustration is one possible affect, not the architecture itself.

**Consequences**
- future adaptive assistance remains extensible
- operators and evaluators can inspect broader player-state signals
- player adaptation can stay bounded by policy instead of ad hoc heuristics
