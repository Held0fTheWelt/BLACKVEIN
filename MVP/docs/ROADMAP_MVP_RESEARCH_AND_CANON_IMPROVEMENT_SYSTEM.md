# Research-and-Canon-Improvement System MVP

## 1. Purpose

This document defines a **fully bounded, evidence-first, review-safe MVP** for a **Research-and-Canon-Improvement System** in **World of Shadows**.

The system exists to do more than collect notes, summarize scenes, or store vague analysis. Its purpose is to:

1. ingest approved resources,
2. extract dramatic and narrative aspects from multiple professional perspectives,
3. explore non-obvious interpretations and adjacent ideas in a bounded thinking mode,
4. validate, reject, or leave unresolved those findings against evidence and counter-readings,
5. store structured research knowledge with provenance,
6. inspect canonical material for weaknesses, gaps, and underused dramatic opportunities,
7. generate concrete canon-improvement proposals,
8. assemble review-safe research and improvement bundles,
9. and prevent silent canon mutation.

This MVP is explicitly designed as a **bounded dramatic intelligence system**, not as an autonomous canon writer and not as an unbounded self-learning crawler.

---

## 2. Strategic Intent

The strategic intent is to turn dramatic works, scenes, notes, transcripts, and related project material into **structured dramatic intelligence**.

The system should be able to learn from material in the following sense:

- discover what is dramatically meaningful,
- separate direct source observations from inferred interpretations,
- examine competing readings,
- surface reusable dramatic principles,
- detect weaknesses in current canonical modules,
- derive actionable improvement proposals,
- and preserve review control, provenance, and boundedness throughout.

The MVP must support not only direct extraction, but also a dedicated **Thinking / Exploration Mode** in which the system can follow adjacent aspects, test alternate readings, stress hypotheses, and search for insights that are not immediately obvious from a linear analysis pass.

---

## 3. MVP Goals

The MVP must support the following end-to-end loop:

1. **Read a resource**
2. **Extract dramatic aspects** from multiple perspectives
3. **Explore** related hypotheses, alternate readings, and adjacent lines of thought
4. **Verify** promising findings against evidence and counter-readings
5. **Store** structured research records
6. **Inspect canonical material** for weaknesses or underdeveloped opportunities
7. **Generate canon-improvement proposals**
8. **Assemble review bundles**
9. **Prevent silent canon mutation**

The MVP is successful when it proves that the project can move from source material to structured insights to bounded improvement proposals in a controlled, inspectable way.

---

## 4. MVP Non-Goals

The MVP does **not** aim to provide:

- unbounded autonomous self-learning,
- uncontrolled ingestion of arbitrary external internet sources,
- direct automatic canon adoption,
- unrestricted patch application,
- full free-form authoring replacement,
- or a claim that the system fully “understands” a work.

The MVP is not a replacement for editorial, dramaturgical, directorial, or authorial judgment. It is a system for producing structured, reviewable, evidence-linked research and improvement proposals.

---

## 5. Core Principles

### 5.1 Evidence First
No meaningful claim or proposal may exist without evidence anchors.

### 5.2 Truth Separation
The system must always distinguish between:

- source-derived observations,
- exploratory hypotheses,
- candidate claims,
- validated insights,
- approved research,
- canon-applicable proposals,
- and canon-adopted changes.

### 5.3 Bounded Exploration
Thinking and exploration are allowed and required, but they must be bounded by explicit budgets and stop conditions.

### 5.4 Review Safety
The system may propose, preview, and bundle, but must not silently publish or mutate canon.

### 5.5 Perspective Awareness
Different dramatic perspectives must remain distinct rather than collapsing into a single vague analysis layer.

### 5.6 Provenance and Traceability
Every stored insight must preserve where it came from, how it was derived, what evidence supports it, what contradictions exist, and what was promoted or rejected.

### 5.7 Deterministic Governance
Even when model outputs contain interpretive language, the MVP must preserve deterministic behavior for classification, budgets, state transitions, pruning, contradiction handling, promotion, and proposal typing.

---

## 6. Professional Perspective Coverage

The MVP must support four mandatory research perspectives.

### 6.1 Playwright Perspective
Questions addressed by this perspective include:

- What is the dramatic function of the scene?
- What drives the conflict?
- What do the characters want?
- What is being set up or paid off?
- What is explicit versus implicit?
- What is structurally strong or weak?

### 6.2 Director Perspective
Questions addressed by this perspective include:

- What power dynamics or spatial tensions are active?
- What staging possibilities are implied?
- What tempo or contrast levers exist?
- What is visually or rhythmically interesting?
- Which interpretive staging choices could change the perceived meaning?

### 6.3 Actor Perspective
Questions addressed by this perspective include:

- What is the character objective?
- What blocks that objective?
- Which tactics are used or changed?
- Where are the beats?
- Where do status shifts occur?
- What playable actions are available?

### 6.4 Dramaturg Perspective
Questions addressed by this perspective include:

- What is redundant, unclear, or imbalanced?
- Where does the scene lose pressure?
- Is the thematic line coherent?
- Is a function underdeveloped or overexplained?
- Which parts serve the work and which parts weaken it?

These perspectives must be modeled explicitly in the data model and the extraction, exploration, verification, and improvement flows.

---

## 7. Required Modes

The MVP must implement five explicit operating modes.

### 7.1 Resource Analysis Mode
This is the first-pass analytical mode.

It reads a resource and extracts structured dramatic aspects such as:

- scene functions,
- conflicts,
- character motives,
- tactics,
- beats,
- subtext indicators,
- thematic nodes,
- dramatic devices,
- staging opportunities,
- and apparent weaknesses.

Outputs of this mode are structured aspect records with source anchors.

### 7.2 Thinking / Exploration Mode
This is the non-canonical discovery and hypothesis mode.

It must allow the system to:

- follow adjacent aspects,
- form hypotheses,
- test alternate readings,
- generate counter-readings,
- branch from motifs or tensions,
- connect themes across segments,
- explore staging implications,
- and search for improvement opportunities that would not emerge from a purely linear pass.

All outputs of this mode must begin as **exploratory** rather than canonical truth.

### 7.3 Verification Mode
This mode checks exploratory results and candidate claims against:

- the same segment,
- other segments of the same resource,
- related resources,
- existing stored claims,
- and explicit counter-readings.

The purpose is to promote, merge, reject, or mark unresolved insights.

### 7.4 Canon Improvement Mode
This mode maps validated research findings onto weaknesses or opportunities within existing canonical material.

Its outputs are structured canon issues and improvement proposals.

### 7.5 Review / Publish Preparation Mode
This mode assembles results into review-safe bundles, including evidence, branch summaries, contradictions, rationale, and proposal previews.

This mode prepares decisions but does not directly mutate canon.

---

## 8. Thinking / Exploration Mode Requirements

The Thinking / Exploration Mode is a core feature, not an optional extra.

Without it, the system would remain overly linear and would mostly capture the obvious. The MVP therefore needs a dedicated bounded exploration layer.

### 8.1 Purpose of Exploration
Exploration exists to:

- discover non-obvious dramatic aspects,
- test alternate interpretations,
- surface hidden mechanisms,
- identify adjacent artistic or structural levers,
- examine whether an intuition holds under pressure,
- and find improvement avenues that are not directly stated in the source.

### 8.2 Exploration Must Not Equal Truth
Exploration outputs are not canon and not approved research by default.

Exploration must produce objects such as:

- exploratory hypotheses,
- alternate readings,
- unresolved tensions,
- candidate insights,
- rejected branches,
- and improvement leads.

### 8.3 Boundedness Rules
Each exploration run must carry budgets such as:

- maximum depth,
- maximum branches per node,
- maximum total nodes,
- maximum low-evidence expansions,
- model-call budget,
- token budget,
- and stop conditions for redundancy, drift, or weak support.

### 8.4 Exploration Operations
The MVP must support at least the following branching relations:

- `extend`
- `contrast`
- `counterread`
- `staging_implication`
- `theme_link`
- `character_motive_link`
- `structural_analogy`
- `tension_source_probe`
- `improvement_probe`

### 8.5 Exploration Outcomes
Each branch must end in one of the following states:

- kept for validation,
- rejected,
- unresolved,
- merged into an existing pattern,
- or promoted to research claim candidate.

### 8.6 Exploration Abort Reasons
The MVP must emit stable abort reasons for bounded runs. At minimum:

- `depth_limit_reached`
- `node_budget_exhausted`
- `branch_budget_exhausted`
- `llm_budget_exhausted`
- `token_budget_exhausted`
- `low_evidence_limit_reached`
- `redundancy_abort`
- `speculative_drift_abort`

---

## 9. Truth and Status Model

A strict status model is mandatory. Every significant research object must clearly indicate where it sits in the truth pipeline.

The MVP must implement at least these statuses:

- `exploratory`
- `candidate`
- `validated`
- `approved_research`
- `canon_applicable`
- `canon_adopted`

### 9.1 Promotion Rules
Promotion rules must be explicit and testable.

#### `exploratory -> candidate`
Allowed only when:

- the node has at least one linked evidence anchor,
- the branch did not end in a hard contradiction,
- the node survived pruning,
- and the hypothesis has a recognized claim shape.

#### `candidate -> validated`
Allowed only when:

- evidence support is sufficient under the configured support rule,
- contradiction scan does not classify the claim as blocked,
- and the verification phase resolves the claim to a stable outcome.

#### `validated -> approved_research`
Allowed only when:

- the claim passes review-bound acceptance for research storage,
- provenance is complete,
- and no unresolved critical contradiction remains.

#### `approved_research -> canon_applicable`
Allowed only when:

- the finding maps to a known canon issue or proposal pathway,
- the improvement engine can express the proposal in an allowed proposal type,
- and the output remains review-safe and non-mutating.

#### `canon_applicable -> canon_adopted`
Out of direct MVP scope. This transition belongs to downstream explicit approval and canon publish flow.

### 9.2 Contradiction Statuses
The MVP must use stable contradiction statuses. At minimum:

- `none`
- `counterview_present`
- `soft_conflict`
- `hard_conflict`
- `unresolved`

---

## 10. Data Model

The MVP must store structured records rather than loose text blobs.

### 10.1 ResearchSource
Represents an ingested resource.

Required fields:

- `source_id`
- `work_id`
- `source_type`
- `title`
- `provenance`
- `visibility`
- `copyright_posture`
- `segment_index_status`
- `metadata`

### 10.2 Copyright Posture Semantics
The `copyright_posture` field is operational in the MVP and must not be a placeholder.

Allowed values for MVP resources:

- `internal_approved`
- `internal_restricted`
- `external_blocked`
- `external_whitelisted_future`

MVP enforcement rules:

- `internal_approved` resources may be ingested, segmented, anchored, retrieved, and used for claim and proposal generation.
- `internal_restricted` resources may be ingested and analyzed, but must not be promoted into broader general retrieval domains without explicit later policy support.
- `external_blocked` resources are not ingestible in the MVP.
- `external_whitelisted_future` is reserved for later phases and must behave as blocked in the MVP.

For MVP-supported resources, the expected default is `internal_approved` unless a narrower internal restriction is explicitly set.

### 10.3 EvidenceAnchor
Represents a concrete anchor into a resource.

Required fields:

- `anchor_id`
- `source_id`
- `segment_ref`
- `span_ref`
- `paraphrase_or_excerpt`
- `confidence`
- `notes`

### 10.4 AspectRecord
Represents a source-derived aspect from a given perspective.

Required fields:

- `aspect_id`
- `source_id`
- `perspective`
- `aspect_type`
- `statement`
- `evidence_anchor_ids`
- `tags`
- `status`

### 10.5 ExplorationNode
Represents one node in the exploration graph.

Required fields:

- `node_id`
- `parent_node_id`
- `seed_aspect_id`
- `perspective`
- `hypothesis`
- `rationale`
- `speculative_level`
- `evidence_anchor_ids`
- `novelty_score`
- `status`

### 10.6 ExplorationEdge
Represents the relationship between two exploration nodes.

Required fields:

- `edge_id`
- `from_node_id`
- `to_node_id`
- `relation_type`

### 10.7 ResearchClaim
Represents a structured insight that may originate from extraction or exploration and has entered the validation pipeline.

Required fields:

- `claim_id`
- `work_id`
- `perspective`
- `claim_type`
- `statement`
- `evidence_anchor_ids`
- `support_level`
- `contradiction_status`
- `status`
- `notes`

### 10.8 CanonIssue
Represents a weakness, gap, or underused opportunity in canonical material.

Required fields:

- `issue_id`
- `module_id`
- `issue_type`
- `severity`
- `description`
- `supporting_claim_ids`
- `status`

### 10.9 ImprovementProposal
Represents a structured proposal to improve canonical material.

Required fields:

- `proposal_id`
- `module_id`
- `proposal_type`
- `rationale`
- `expected_effect`
- `supporting_claim_ids`
- `preview_patch_ref`
- `status`

### 10.10 ResearchRun
Represents a single tracked research execution.

Required fields:

- `run_id`
- `mode`
- `source_ids`
- `seed_question`
- `budget`
- `outputs`
- `audit_refs`
- `created_at`

---

## 11. Canon Issue Taxonomy

The MVP must support a minimal but meaningful issue taxonomy for canon inspection.

Allowed initial issue classes:

- `weak_escalation`
- `unclear_scene_function`
- `insufficient_subtext`
- `redundant_dialogue`
- `missing_payoff_preparation`
- `underpowered_status_shift`
- `narrow_action_space`
- `theme_not_embodied`
- `motivation_gap`
- `unused_staging_potential`

This taxonomy may grow later, but the MVP must already provide enough structure to turn findings into actionable improvement work.

---

## 12. Improvement Proposal Taxonomy

The MVP must produce concrete proposal classes rather than generic “make it better” outputs.

Allowed proposal types in the MVP:

- `tighten_conflict_core`
- `introduce_earlier_tactic_shift`
- `strengthen_status_reversal`
- `convert_exposition_to_playable_action`
- `improve_payoff_preparation`
- `sharpen_subtext`
- `widen_action_space`
- `embody_theme_through_friction`
- `restructure_pressure_curve`
- `activate_staging_leverage`

Each proposal must include rationale, expected effect, and supporting claims.

No ad hoc proposal type outside this enumeration is permitted in the MVP.

---

## 13. LangGraph Flow

The MVP should be orchestrated as a bounded graph rather than a monolithic free-form pass.

### Phase 1: Intake
- normalize resource
- segment source
- identify anchors
- enforce copyright posture

### Phase 2: Aspect Extraction
- extract perspective-separated aspect candidates
- attach evidence anchors
- deduplicate
- classify into stable aspect shapes

### Phase 3: Exploration
- choose seed aspects or seed questions
- build exploration nodes
- generate alternate readings and related branches
- score support and novelty
- prune weak or redundant branches
- stop on budget or abort reasons

### Phase 4: Verification
- cross-check claims against source anchors
- search for intra-resource support or contradiction
- compare against existing research claims
- merge, reject, or promote candidates

### Phase 5: Canon Improvement
- inspect canonical module
- identify canon issues
- map validated claims to issue classes
- generate improvement proposals
- optionally generate preview payloads

### Phase 6: Review Bundle
- assemble research bundle
- include provenance, evidence, contradictions, branch summary, and proposals

---

## 14. MCP Surface

The MVP must expose a controlled MCP surface for research and canon improvement work.

### 14.1 Read-Only Tools
- `wos.research.source.inspect`
- `wos.research.aspect.extract`
- `wos.research.claim.list`
- `wos.research.run.get`
- `wos.research.exploration.graph`
- `wos.canon.issue.inspect`

### 14.2 Review-Bound Tools
- `wos.research.explore`
- `wos.research.validate`
- `wos.research.bundle.build`
- `wos.canon.improvement.propose`
- `wos.canon.improvement.preview`

### 14.3 Explicitly Out of MVP Scope
- direct `canon.apply`
- direct automatic `publish.auto_approve`
- unrestricted self-commit into canon

### 14.4 Budgeted Tool Contract Requirement
`wos.research.explore` must never run unbudgeted.

Any invocation of `wos.research.explore` must include either explicit values or enforced defaults for:

- `max_depth`
- `max_branches_per_node`
- `max_total_nodes`
- `max_low_evidence_expansions`
- `llm_call_budget`
- `token_budget`
- `time_budget_ms`
- `abort_on_redundancy`
- `abort_on_speculative_drift`
- `model_profile`

Unbudgeted exploration is invalid in the MVP.

### 14.5 MCP Result Requirements
The result payload of `wos.research.explore` must include:

- effective budget,
- consumed budget,
- abort reason if stopped early,
- node count,
- edge count,
- promoted candidate count,
- rejected branch count,
- unresolved branch count.

The MCP layer should provide controlled access, observability, and composability without bypassing governance.

---

## 15. Role of RAG

RAG should support the MVP, but it must not become a truth engine.

The role of retrieval is to:

- recover earlier claims,
- find similar scenes, themes, motives, or conflicts,
- avoid duplicate research,
- provide context for exploration and validation,
- and compare current findings against previously stored knowledge.

Recommended retrieval domains for the MVP:

- `research`
- optionally later `canon_improvement`

Research retrieval must remain separated from runtime truth and live world-engine authority.

---

## 16. Governance Requirements

The MVP must obey explicit governance rules.

### 16.1 Mandatory Evidence
No claim or proposal may exist without linked evidence anchors.

### 16.2 Review Boundary
No canon-affecting change may be silently published.

### 16.3 Contradiction Visibility
Conflicting claims must remain visible rather than being silently overwritten.

### 16.4 Perspective Separation
Claims must preserve perspective rather than collapsing distinct views into a single blended conclusion.

### 16.5 Provenance Preservation
The system must preserve source provenance, derivation path, validation status, and contradiction status.

### 16.6 Bounded Exploration Enforcement
Exploration must be budgeted, auditable, and abort-reason legible.

### 16.7 Proposal Type Governance
Proposal generation must remain inside the MVP proposal enumeration and may not generate arbitrary free-form proposal classes.

---

## 17. Initial Resource Scope

To keep the MVP realistic and controlled, the initial supported resource classes must be limited to internal or already approved material.

Supported MVP resource types:

- canonical module material,
- structured scene-level artifacts,
- review notes,
- existing transcripts,
- internal evaluation or policy artifacts,
- existing project knowledge records.

External literature, public essays, production notes, interviews, or broader corpora may be added later only after legal, provenance, copyright posture, and policy handling are explicitly extended.

---

## 18. Initial World of Shadows Slice

The MVP should be cut against a single concrete module first.

### Initial Target Module
**God of Carnage**

### Initial Research Inputs
- canonical module representation,
- scene-level structured content,
- transcript material,
- review notes,
- evaluation artifacts.

### Initial Deliverables
- perspective-separated aspect records,
- exploration graph,
- validated insight candidates,
- canon issue list,
- improvement proposal bundle,
- review bundle with provenance and contradictions.

This keeps the MVP narrow enough to execute while still demonstrating the full research-to-improvement loop.

---

## 19. Suggested Module Layout

A practical initial module layout inside the AI stack could look like this:

- `research_contract.py`
- `research_perspectives.py`
- `research_store.py`
- `research_exploration.py`
- `research_validation.py`
- `research_claims.py`
- `canon_improvement_contract.py`
- `canon_improvement_engine.py`
- `research_langgraph.py`
- `research_mcp_surface.py`
- `research_fixtures.py`
- `research_golden_cases.py`

Optional later extension:

- `research_rag_bridge.py`

This should be adapted to the repo’s established naming and organization conventions, but the logical separation should remain.

---

## 20. Acceptance Gates

The MVP must not be considered complete until all named gates pass.

### Gate 1 — Truth Separation
Exploration, candidate insight, validated research, approved research, and canon adoption are systemically distinct.

### Gate 2 — Provenance
All meaningful claims and proposals carry evidence anchors and source provenance.

### Gate 3 — Bounded Exploration
The exploration loop enforces depth, branching, pruning, budget, and stop rules.

### Gate 4 — Counterview Support
The MVP can represent alternative readings or contradictions rather than forcing a single flattening interpretation.

### Gate 5 — Canon Improvement
The system can derive structured canon issues and improvement proposals from validated findings.

### Gate 6 — Reviewability
Results can be assembled into a review-safe, operator-legible bundle.

### Gate 7 — No Silent Mutation
No canon-affecting change is automatically applied without explicit downstream approval flow.

### Gate 8 — Deterministic Testability
State transitions, pruning, contradiction handling, promotion logic, proposal generation, and budget handling are testable and reproducible through golden fixtures.

---

## 21. Determinism Envelope

Because the system includes exploration, the MVP must define what determinism means.

### 21.1 Deterministic Layers
The following must be deterministic under fixed inputs, fixed fixtures, fixed budgets, and fixed configuration:

- state-machine transitions,
- pruning decisions,
- contradiction classification,
- promotion eligibility,
- proposal type selection,
- issue type selection,
- abort reasons,
- effective and consumed budget accounting,
- result schema shape,
- and review-bundle structure.

### 21.2 Allowed Non-Deterministic Surface
The following may vary within bounded tolerances if schema, class, and status outputs stay stable:

- explanatory phrasing,
- rationale wording,
- summary wording,
- tie-order among explicitly equivalent same-score nodes, if the tie rule is documented.

### 21.3 Non-Negotiable Rule
The MVP may permit bounded textual variance, but it may not permit variance in status, class, abort reason, or proposal type under the same deterministic test fixture.

---

## 22. Golden Test Specification

Gate 8 requires concrete golden cases, not only general intent.

The MVP must include at least one **golden fixture pack** per pipeline phase.

### 22.1 Fixture A — Intake Fixture
Purpose: validate resource normalization and policy enforcement.

Fixture shape:

- 1 approved internal source,
- 2–3 deterministic segments,
- fixed metadata,
- explicit `copyright_posture`.

Must assert:

- segment indexing outcome,
- anchor extraction shape,
- copyright posture enforcement,
- stable normalized source record.

### 22.2 Fixture B — Aspect Extraction Fixture
Purpose: validate extraction shape and evidence attachment.

Fixture shape:

- one short scene or segment set,
- fixed expected aspect categories,
- at least two perspectives.

Must assert:

- expected aspect record count or bounded count range if explicitly specified,
- stable perspective labeling,
- evidence-anchor attachment,
- status initialization.

### 22.3 Fixture C — Exploration Fixture
Purpose: validate bounded branching.

Fixture shape:

- fixed seed aspect,
- fixed exploration budget,
- expected branching relations,
- at least one low-evidence branch.

Must assert:

- stable node count,
- stable edge count,
- stable pruned branch count,
- stable abort or completion reason,
- stable candidate promotion eligibility,
- stable budget consumption summary.

### 22.4 Fixture D — Verification Fixture
Purpose: validate support and contradiction handling.

Fixture shape:

- one supported claim,
- one contradicted claim,
- one unresolved claim.

Must assert:

- stable contradiction status per claim,
- stable merge, reject, or retain outcome,
- stable promotion or block result.

### 22.5 Fixture E — Canon Improvement Fixture
Purpose: validate issue mapping and proposal generation.

Fixture shape:

- one or more validated claims,
- one module snapshot,
- issue and proposal candidates.

Must assert:

- stable issue type classification,
- stable proposal type selection,
- supporting claim linkage,
- preview payload shape.

### 22.6 Fixture F — Review Bundle Fixture
Purpose: validate the final review-safe artifact.

Fixture shape:

- complete bounded run output,
- evidence anchors,
- contradictions,
- proposals.

Must assert:

- stable bundle sections,
- stable inclusion of evidence and contradiction summaries,
- stable promotion summary,
- stable proposal listing.

### 22.7 Fixture Output Rules
For all golden fixtures, the specification must explicitly state:

- which fields must match exactly,
- which fields may be ignored,
- which fields may vary in bounded ways,
- and which statuses, classes, and abort reasons are mandatory.

---

## 23. Test Expectations

The MVP must include tests for at least the following:

- perspective-specific aspect extraction shape,
- evidence-anchor attachment,
- copyright posture enforcement,
- exploration branching limits,
- exploration pruning,
- budget enforcement and abort reasons,
- promotion from exploratory to candidate,
- contradiction detection,
- validation merge and reject behavior,
- canon issue generation,
- proposal generation,
- review-bundle assembly,
- and deterministic fixture reproduction.

Tests must prefer deterministic fixtures and bounded graph expectations over vague qualitative assertions.

---

## 24. Why This MVP Matters

This MVP is the difference between:

- a repository of notes,
- a generic analysis helper,
- and an actual dramatic research and improvement system.

It creates the minimum viable structure needed for the project to:

- learn from dramatic material,
- reason across viewpoints,
- explore adjacent possibilities,
- separate hypothesis from truth,
- and convert dramatic understanding into safer, stronger, more intentional canonical improvement work.

For World of Shadows, this is especially valuable because the long-term goal is not merely to store authored material, but to develop systems that can understand, refine, and strengthen narrative material without losing authority, provenance, or review control.

---

## 25. Final MVP Definition

The **Research-and-Canon-Improvement System MVP** is complete when the project has a controlled system that can:

- ingest approved internal resources,
- enforce operational copyright posture,
- extract perspective-specific dramatic aspects,
- explore non-obvious lines of thought in a bounded mode,
- validate or reject findings,
- store structured insights with provenance,
- detect weaknesses in canonical material,
- generate evidence-backed improvement proposals from an allowed proposal taxonomy,
- produce review-safe bundles,
- and reproduce its key classification and state outcomes through deterministic golden fixtures,
- without silently altering canon.

That is the correct MVP boundary.
