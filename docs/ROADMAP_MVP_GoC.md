# World of Shadows — God of Carnage MVP Closure Roadmap

## Status
- **Document type:** Final MVP closure roadmap
- **Primary target module:** God of Carnage
- **Purpose:** Define the fully closable target state for the current MVP without leaving architectural, semantic, diagnostic, retrieval, governance, or experience ambiguities open
- **Planning mode:** final target-state plan, execution-ready, no open architectural placeholders
- **Closure model:** explicitly **Level A / Level B aware**

---

## Terminology note

The following phrases are canonical terms in this roadmap and not merely audit-task inventions:
- `canonical-to-repo mapping`
- `dual-status reporting`
- `qualitative gate handling`
- `closure-level classification`

They are part of the roadmap’s audit and execution semantics and must be used consistently by later audit and implementation planning.

---

---

## 1. Executive intent

This roadmap upgrades the current MVP from a strong architectural design into a **fully closable operating contract**.

The target is not merely:
- multi-model support
- runtime routing
- bounded scene direction
- diagnostics visibility

The target is:
- one authoritative runtime truth system
- one shared semantic language across runtime, Writers' Room, Improvement, Admin, and AI stack
- one diagnosable per-turn operating truth
- one governed retrieval model
- one operational Writers' Room and Improvement loop
- one testable quality bar for dramatic experience
- one explicit definition of done

This roadmap removes the remaining ambiguity that would otherwise allow “green enough” implementation without true closure.

---

## 2. Closure levels

This roadmap distinguishes two valid closure levels.

### 2.1 Level A — MVP operational closure
Level A is the valid closure target for the current MVP phase.

Level A is achieved only when:
- Gates **G1–G10** pass
- Gate **G9** passes
- evaluator mode is **single-evaluator**
- the evaluator limitation is declared explicitly in the closure report

### 2.2 Level B — full 10/10 closure
Level B is the full closure state.

Level B is achieved only when:
- Gates **G1–G10** pass
- Gate **G9** passes
- Gate **G9B** passes
- evaluator independence evidence is present

### 2.3 Rule
This roadmap must never be read as “everything is always measured against 10/10 only.”

It is **Level A / Level B aware by design**.

- Level A = valid MVP operational closure
- Level B = full 10/10 closure

Gate **G9B** is always part of the roadmap and always auditable.
It is not optional.
It only changes whether closure qualifies as Level A or Level B.

---

## 3. Non-negotiable center

The following remain absolute:

1. **The engine owns truth.**
2. **Validation and commit remain authoritative.**
3. **Visible output remains commit-backed.**
4. **Scene direction remains bounded and deterministic-first.**
5. **Routing does not create a second semantic universe.**
6. **Retrieval augments authored truth; it does not redefine it.**
7. **Admin manages policy and operations, not semantic truth.**
8. **Writers' Room proposes and analyzes; it does not become a second runtime.**

Any implementation that violates one of these principles fails the roadmap, even if other tests pass.

---

## 4. Final target architecture

The final MVP must converge into the following canonical surfaces.

### 4.1 Module Substrate Surface
Defines the canonical module package.

Required fields:
- `module_id`
- `module_version`
- `module_title`
- `module_kind`
- `authored_content_artifacts`
- `derived_content_artifacts`
- `semantic_contract_ref`
- `runtime_manifest`
- `publication_state`

### 4.2 Shared Semantic Surface
Defines the only valid shared semantic vocabulary.

Required artifacts:
- `task_types`
- `model_roles`
- `fallback_classes`
- `decision_classes`
- `routing_labels`
- `scene_direction_subdecision_labels`
- `runtime_profile_labels`
- `controlled_reason_codes`

### 4.3 Capability Surface
Defines technical model/provider/adapter truth only.

### 4.4 Policy Surface
Defines project-approved usage, priorities, constraints, and profile eligibility.

### 4.5 Turn Record Surface
Defines exactly one canonical dramatic turn record per executed turn.

### 4.6 Retrieval Governance Surface
Defines how authored truth, derived retrieval substrate, retrieval lanes, and visibility constraints interact.

### 4.7 Experience Acceptance Surface
Defines the user-facing success criteria for God of Carnage.

Everything else is a projection, consumer, cache, or helper.

---

## 5. Gate taxonomy

Not all gates are of the same kind.

The closure model therefore distinguishes four gate classes:

### 5.1 Structural gates
Verify canonical structures, contracts, imports, mappings, and separations.

Structural gates:
- G1
- G2
- G3
- G4
- G5
- G6

### 5.2 Operational gates
Verify bounded subsystem usefulness, typed flow, approval loop, and runtime behavior.

Operational gates:
- G7
- G8
- G10

### 5.3 Evaluative gates
Verify user-facing dramatic quality through scenarios and scoring.

Evaluative gates:
- G9
- G9B

### 5.4 Mapping rule
Audit and implementation work must respect the gate class.
Structural gates cannot be audited the same way as evaluative gates.
Evaluative gates cannot be reduced to file existence alone.

---

## 6. Gate Pack Specification

The MVP is complete only if all required gates for the relevant closure level pass.

No substitute language is allowed.
- “looks aligned” is not enough
- “routing truth visible” is not enough
- “drift tests green” is not enough

Each gate must define:
- subject under test
- required evidence
- required assertions
- pass rule
- fail rule

### 6.1 Gate G1 — Shared Semantic Contract Gate

#### Subject
The shared semantic surface.

#### Must prove
Runtime, Writers' Room, Improvement, Admin, and AI stack consume the same shared semantics.

#### Required assertions
1. One canonical semantic artifact exists.
2. Runtime imports shared task types from that artifact.
3. Writers' Room imports shared task types from that artifact.
4. Improvement imports shared task types from that artifact.
5. Admin-facing semantic lists are derived from that artifact.
6. No local productive redefinition of shared values exists.

#### Mandatory equality checks
The following sets must be identical everywhere they appear:
- `task_types`
- `model_roles`
- `fallback_classes`
- `decision_classes`
- `routing_labels`
- `scene_direction_subdecision_labels`

#### Pass rule
Pass only if all shared enumerations are identical and no local productive override exists.

#### Fail rule
Fail if any unknown value appears, any local fork exists, or any productive path uses a non-canonical shared label.

---

### 6.2 Gate G2 — Capability / Policy / Observation Separation Gate

#### Subject
Model registration, routing policy, and runtime routing truth.

#### Must prove
Technical capability, project policy, and actual runtime behavior are cleanly separated.

#### Required contract objects
1. `ModelCapabilityRecord`
2. `RoutingPolicyRecord`
3. `RoutingObservationRecord`

#### Mandatory assertions
1. No single structure mixes capability truth and policy truth.
2. No runtime observation is treated as canonical policy.
3. Every routing decision references:
   - capability identity
   - policy identity
   - policy version
4. Every routing observation includes:
   - `route_mode`
   - `route_reason`
   - `fallback_chain`
   - `fallback_stage_reached`
   - `policy_id_used`
   - `policy_version_used`
5. Admin surfaces may edit policy but may not overwrite capability truth.

#### Pass rule
Pass only if separation is structural, runtime-visible, and test-enforced.

#### Fail rule
Fail if any mixed structure remains authoritative or if runtime facts can silently become policy truth.

---

### 6.3 Gate G3 — Canonical Dramatic Turn Record Gate

#### Subject
Per-turn diagnostics and review surfaces.

#### Must prove
Every executed turn yields exactly one canonical dramatic turn record.

#### Required sections in the record
1. Turn Basis
2. Decision Boundary Records
3. Routing Records
4. Retrieval Record
5. Realization Record
6. Outcome Record

#### Minimum fields

##### Turn Basis
- `turn_id`
- `session_id`
- `turn_number`
- `timestamp`
- `initiator_type`
- `input_class`
- `execution_mode`

##### Decision Boundary Record
- `decision_name`
- `decision_class`
- `owner_layer`
- `input_seam_ref`
- `chosen_path`
- `validation_result`
- `failure_seam_used`
- `notes_code`

##### Routing Record
- all fields required by Gate G2

##### Retrieval Record
- `retrieval_used`
- `retrieval_domain`
- `retrieval_lane`
- `retrieval_visibility_class`
- `authored_truth_refs`
- `derived_artifact_refs`
- `retrieval_governance_result`

##### Realization Record
- `selected_responder`
- `selected_scene_function`
- `selected_pacing_label`
- `visibility_class`
- `realization_mode`
- `degraded_wording_used`
- `safe_wording_fallback_used`

##### Outcome Record
- `commit_outcome`
- `guard_outcomes`
- `rejected_reasons`
- `continuity_aftereffects`
- `player_visible_response_class`

#### Projection rule
Compact operator view and expanded dramatic review must be projections of this exact record, not separate structures.

#### Pass rule
Pass only if every executed turn produces exactly one valid record and all UI/log review surfaces derive from it.

#### Fail rule
Fail if any parallel diagnostics truth exists or if any required record section is absent.

---

### 6.4 Gate G4 — Scene Direction Boundary Gate

#### Subject
Scene direction architecture.

#### Must prove
Scene direction remains bounded, deterministic-first, and non-authoritative over truth.

#### Mandatory structure
Scene direction must be split into:
1. Deterministic Core
2. Model-Assisted Bounded Choice
3. Model-Assisted Realization

#### Required subdecision matrix
Every scene-direction subdecision must define:
- `subdecision_label`
- `decision_class`
- `owner_layer`
- `legal_input_seam`
- `legal_output_seam`
- `validation_seam`
- `failure_seam`
- `diagnostics_visibility`

#### Forbidden behaviors
No scene-direction subdecision may:
- invent legal candidates
- mutate committed truth
- bypass validation
- redefine continuity obligations
- silently collapse into generic narrative generation

#### Pass rule
Pass only if every scene-direction subdecision is explicitly classified and every model-assisted seam is bounded.

#### Fail rule
Fail if any scene-direction decision operates without classification or without explicit seams.

---

### 6.5 Gate G5 — Retrieval Governance Gate

#### Subject
RAG / retrieval behavior.

#### Must prove
Retrieval augments authored truth without redefining module truth.

#### Required distinctions
1. Authored Truth
2. Derived Retrieval Substrate
3. Retrieval Output
4. Visibility / Governance Lane

#### Mandatory assertions
1. Authored truth artifacts are explicitly identified.
2. Derived retrieval artifacts are explicitly identified.
3. Retrieval outputs reference their source class.
4. Retrieval cannot replace authored truth with retrieval-time inference.
5. Runtime-relevant retrieval must carry visibility/governance classification.
6. Retrieval used in runtime must be auditable from the dramatic turn record.

#### Pass rule
Pass only if authored truth and retrieval-derived augmentation are structurally separate and governance-visible.

#### Fail rule
Fail if retrieval can silently redefine authored truth or if retrieval provenance is not visible.

---

### 6.6 Gate G6 — Admin Governance Gate

#### Subject
Administration Tool authority.

#### Must prove
Admin is a control plane, not a semantic author.

#### Admin may manage
- routing policies
- runtime profiles
- model attachments
- fallback sequencing
- publication state
- diagnostics access
- review workflows

#### Admin may not directly invent
- shared semantic labels
- new task type meanings
- new fallback class meanings
- new decision classes
- scene-direction authority expansion

#### Mandatory assertions
1. Admin edits policy artifacts, not shared semantic truth.
2. Any semantically relevant change triggers the semantic change discipline.
3. Admin changes are versioned and review-visible.

#### Pass rule
Pass only if admin cannot bypass semantic governance.

#### Fail rule
Fail if productive semantic drift can be created from admin state alone.

---

### 6.7 Gate G7 — Writers' Room Operating Contract Gate

#### Subject
Writers' Room function and semantic discipline.

#### Must prove
Writers' Room is useful, bounded, and semantically aligned.

#### Required Writers' Room functions
1. Analysis
2. Proposal
3. Authoring Support

#### Analysis may
- inspect module structure
- detect semantic inconsistencies
- detect scene coverage gaps
- detect escalation/continuity weaknesses
- inspect retrieval evidence quality

#### Analysis may not
- commit runtime truth changes

#### Proposal may
- create bounded change proposals
- propose scene-function alternatives
- propose pacing alternatives
- propose authored content additions

#### Proposal may not
- directly modify canonical runtime truth

#### Authoring Support may
- draft authored artifacts
- draft missing module structures
- draft bounded variants

#### Authoring Support may not
- redefine shared semantics locally

#### Required artifact classes
All Writers' Room outputs must land in exactly one class:
- `analysis_artifact`
- `proposal_artifact`
- `candidate_authored_artifact`
- `approved_authored_artifact`
- `rejected_artifact`

#### Pass rule
Pass only if the Writers' Room has real bounded utility and no semantic fork.

#### Fail rule
Fail if it is still only a thin concept or if it can act as a second runtime truth surface.

---

### 6.8 Gate G8 — Improvement Path Operating Gate

#### Subject
Improvement path purpose and flow.

#### Must prove
Improvement is not vague “make it better” behavior, but a bounded operating loop.

#### Required improvement classes
1. `runtime_issue_improvement`
2. `module_completeness_improvement`
3. `semantic_quality_improvement`

#### Allowed outputs
- `analysis_artifact`
- `proposal_artifact`
- `approved_authored_artifact`
- `rejected_artifact`

#### Required loop
1. issue selection
2. evidence collection
3. bounded proposal generation
4. semantic compliance validation
5. approval / rejection
6. publication if approved
7. post-change verification

#### Pass rule
Pass only if improvement work is bounded, typed, and reviewable.

#### Fail rule
Fail if improvement remains untyped or cannot be distinguished from unrestricted generation.

---

### 6.9 Gate G9 — User-Facing Experience Acceptance Gate

#### Subject
God of Carnage player-facing runtime quality.

#### Must prove
The system is not only technically correct but dramatically good enough.

#### Required scored criteria
Each acceptance scenario must be scored from 1 to 5 on:
1. Dramatic responsiveness
2. Truth consistency
3. Character credibility
4. Conflict continuity
5. Graceful degradation

#### Required scenario set
At minimum, define and run:
1. Direct provocation scenario
2. Deflection / brevity scenario
3. Pressure escalation scenario
4. Misinterpretation / correction scenario
5. Primary model failure + fallback scenario
6. Retrieval-heavy context scenario

#### Minimum pass thresholds
- no criterion may score below 3/5 on any required scenario
- average score per scenario must be >= 4.0/5
- average score per criterion across all scenarios must be >= 4.0/5
- graceful degradation in failure scenarios must be >= 3.5/5

#### Pass rule
Pass only if technical correctness and user-facing dramatic quality both meet threshold.

#### Fail rule
Fail if technical gates are green but the experience layer remains weak.

---

### 6.10 Gate G9B — Evaluator Independence Gate

#### Subject
Experience Acceptance evaluation independence.

#### Must prove
Closure-level classification is explicit and evaluator independence is evidenced when claiming full closure.

#### Required assertions
1. At least one evaluator scores the fixed scenario set.
2. The gate report explicitly declares evaluator mode:
   - single-evaluator Level A mode
   - or independent-evaluator Level B mode
3. If Level B is claimed, at least two independent evaluators score the same required scenario set.
4. Raw scores are stored separately.
5. Score deltas between evaluators are preserved.
6. Final reconciled score does not replace raw evidence.

#### Pass rule
- For **Level A**: pass only if single-evaluator mode is explicitly declared as a known limitation.
- For **Level B**: pass only if two independent evaluators are evidenced.

#### Fail rule
Fail if a Level B closure claim is made without evaluator independence evidence, or if evaluator mode is undeclared.

---

### 6.11 Gate G10 — End-to-End Closure Gate

#### Subject
The entire God of Carnage MVP slice.

#### Required end-to-end proof
The following complete chain must work and be evidenced:
1. module load from canonical package
2. runtime turn execution
3. bounded retrieval when appropriate
4. task-aware routing
5. structured model output
6. validation and commit
7. dramatic turn record emission
8. operator-visible routing truth
9. fallback correctness when primary path fails
10. Writers' Room semantic compatibility remains intact
11. experience acceptance threshold remains green

#### Pass rule
Pass only if the full stack works as one system.

#### Fail rule
Fail if any layer is green in isolation but closure is not end-to-end.

---

## 7. Writers' Room / Improvement Operating Contract

### 7.1 Writers' Room is mandatory and bounded
Writers' Room is a required bounded operating subsystem.

### 7.2 Writers' Room responsibilities

#### A. Module analysis
The Writers' Room must be able to:
- inspect authored content structure
- inspect semantic contract alignment
- detect scene coverage gaps
- detect weak escalation ladders
- detect character consistency risks
- inspect retrieval coverage and relevance gaps

#### B. Proposal generation
The Writers' Room must be able to:
- produce bounded proposals for authored change
- produce bounded proposals for scene / pacing / responder improvements
- produce bounded proposals for retrieval corpus improvement
- attach rationale and evidence references

#### C. Authoring support
The Writers' Room must be able to:
- draft authored content additions
- draft missing authored connective material
- draft corrected artifacts after approved semantic or module fixes

### 7.3 Writers' Room output rules
Every Writers' Room output must contain:
- `artifact_id`
- `artifact_class`
- `source_module_id`
- `shared_semantic_contract_version`
- `evidence_refs`
- `proposal_scope`
- `approval_state`

### 7.4 Writers' Room approval model
No Writers' Room output may become canonical unless it is explicitly approved into authored truth.

### 7.5 Improvement Path responsibilities
Improvement Path is an operating function with three bounded entry points:

#### A. Runtime issue improvement
Triggered by:
- degraded turns
- failed experience scenarios
- fallback overuse
- poor responsiveness
- poor character credibility

#### B. Module completeness improvement
Triggered by:
- scene coverage gaps
- missing authored connective material
- missing escalation hooks
- missing retrieval coverage

#### C. Semantic quality improvement
Triggered by:
- shared label inconsistency
- weak seam specification
- ambiguous decision class mapping
- governance drift

### 7.6 Improvement artifacts
Every improvement action must yield one of:
- `analysis_artifact`
- `proposal_artifact`
- `approved_authored_artifact`
- `rejected_artifact`

### 7.7 Improvement closure loop
Every improvement must follow this exact loop:
1. select issue
2. attach evidence
3. generate bounded proposal
4. validate semantic compliance
5. approve or reject
6. publish if approved
7. rerun affected gates

There is no free-form improvement outside this loop.

---

## 8. User-Facing Experience Acceptance Layer

### 8.1 Why this layer is mandatory
A technically green dramatic runtime can still feel weak, wooden, generic, or inert.

Technical correctness alone is insufficient.

### 8.2 Required acceptance scenarios
These scenarios must exist as explicit scenario artifacts.

#### Scenario S1 — Direct provocation
The player makes a sharp confrontational move.

Expected quality:
- the scene reacts dramatically
- committed truth remains correct
- conflict pressure becomes tangible

#### Scenario S2 — Deflection / brevity
The player minimizes, evades, or gives very short input.

Expected quality:
- the runtime reacts meaningfully
- the scene does not go dead
- brevity is handled as a dramatic event, not a null event

#### Scenario S3 — Pressure escalation
The player pushes tension across multiple turns.

Expected quality:
- continuity carries pressure forward
- escalation remains coherent
- pacing shifts are legible

#### Scenario S4 — Misunderstanding / correction
The runtime initially interprets something imperfectly and the player corrects it.

Expected quality:
- correction is incorporated plausibly
- truth remains stable
- the exchange still feels dramatically alive

#### Scenario S5 — Primary model failure
Primary model path fails.

Expected quality:
- fallback activates correctly
- degradation remains graceful
- scene remains usable, not inert or obviously broken

#### Scenario S6 — Retrieval-heavy context use
A turn depends on retrieval of authored / derived module context.

Expected quality:
- retrieval improves relevance
- authored truth is not contradicted
- retrieval provenance is operator-visible

### 8.3 Scoring rubric
Each scenario is scored on:
- dramatic responsiveness
- truth consistency
- character credibility
- conflict continuity
- graceful degradation

Each dimension uses a 1–5 rubric:
- 1 = unacceptable
- 2 = materially weak
- 3 = acceptable minimum
- 4 = strong
- 5 = excellent

### 8.4 Hard thresholds
The MVP fails if:
- any scenario contains a score below 3 in any dimension
- any criterion averages below 4.0 across the required scenario set
- graceful degradation in failure scenarios averages below 3.5

### 8.5 Acceptance evidence
Each scenario must produce:
- transcript excerpt
- dramatic turn records
- route / fallback evidence
- retrieval evidence if applicable
- score sheet with reasons

---

## 9. Retrieval governance and RAG finalization

### 9.1 RAG role
RAG may:
- retrieve authored context
- retrieve derived context
- improve relevance
- improve context packing
- support Writers' Room and Improvement evidence

RAG may not:
- redefine authored truth
- create canonical module meaning at retrieval time
- bypass visibility doctrine
- replace validation or commit

### 9.2 Retrieval lanes
Every retrieval must be assigned a lane:
- `runtime_commit_support`
- `runtime_context_support`
- `writers_room_analysis`
- `improvement_evidence`
- `operator_review`

### 9.3 Retrieval visibility
Every retrieval output must declare:
- `lane`
- `visibility_class`
- `source_class`
- `governance_result`

### 9.4 Retrieval closure rule
If retrieval is used in runtime, the dramatic turn record must show:
- that retrieval happened
- what domain / lane was used
- what source class was involved
- whether governance allowed it

---

## 10. Canonical-to-repo mapping rule

This roadmap uses canonical contract names.
The repository may use different file names, module names, or service names.

Therefore every audit and implementation phase must begin by creating a **canonical-to-repo mapping table**.

### 10.1 Required mapping fields
Each mapping row must include:
- `canonical_name`
- `repo_path`
- `repo_owner_surface`
- `mapping_confidence`
- `notes`
- `evidence_ref`

### 10.2 Rule
No gate may be claimed green merely because a concept exists in prose.
A gate becomes auditable only when its canonical objects are mapped to repo reality.

### 10.3 Repo mapping phase
All later command finalization, test selection, and audit scope depend on this mapping.

---

## 11. Audit and execution semantics

### 11.1 Dual status model
All gate reporting must use two dimensions:

#### A. Structural status
- `green`
- `yellow`
- `red`
- `not_auditable_yet`

#### B. Closure-level status
- `none`
- `level_a_capable`
- `level_b_capable`

### 11.2 Rule
A single green structural status does not automatically imply Level B capability.
This is especially important for G9B.

### 11.2B Closure-level aggregation rule
Closure-level classification is primarily a **global aggregation outcome**, not a fully independent per-gate property.

Therefore:
- for many structural gates, `level_b_capable` will be the same as `level_a_capable`
- or may be recorded as `n/a; Level B determined by global aggregation through G9, G9B, and G10`
- no structural gate may imply Level B on its own unless that implication is explicitly justified

This prevents artificial precision in per-gate closure-level reporting.


### 11.2A Evaluative sequencing rule
For audit and closure execution, **G9B follows G9**.

This means:
- G9 scenario execution and score evidence come first
- G9B then audits evaluator mode and evaluator independence against that score evidence

G9B may be planned in parallel, but it may not be concluded before G9 evidence exists.

### 11.3 Qualitative gate rule
G7, G8, G9, and G9B cannot be reduced to file existence or static inspection only.

They require a combination of:
- structural checks
- artifact checks
- flow checks
- scenario checks
- evaluator or score handling where applicable

---

## 12. Mandatory implementation order

The following order is mandatory because it prevents rework and semantic drift:

1. create the shared semantic contract and bind all productive paths to it
2. create or harden the canonical module package contract
3. separate capability, policy, and observation structures
4. define the full scene-direction subdecision matrix
5. define and emit the canonical dramatic turn record
6. bind retrieval to explicit governance lanes and turn-record visibility
7. harden admin governance boundaries
8. implement the Writers' Room operating contract
9. implement the Improvement Path operating contract
10. implement the user-facing experience acceptance scenarios and score layer
11. run all named gates and collect evidence

---

## 13. Required evidence artifacts

The MVP is not complete without the following evidence artifacts:

1. `shared_semantic_contract.*`
2. `module_package_contract.*`
3. `capability_contract.*`
4. `routing_policy_contract.*`
5. `routing_observation_contract.*`
6. `dramatic_turn_record_contract.*`
7. `scene_direction_subdecision_matrix.*`
8. `retrieval_governance_contract.*`
9. `writers_room_operating_contract.*`
10. `improvement_operating_contract.*`
11. `experience_acceptance_matrix.*`
12. `gate_results_report.*`
13. `final_closure_report.*`

### 13.1 Mapping rule
Every evidence artifact must be mapped to:
- one or more gates
- one or more implementation steps
- one or more canonical surfaces

No artifact may remain “generally relevant” only.

---

## 13A. Audit-output interpretation rule

Any later audit or planning output may include a recommendation such as:
- `ready for implementation closure work`
- `not ready for implementation closure work`

This recommendation must be treated only as a **transition recommendation**.

It is not:
- a closure claim
- a substitute for gate pass
- a substitute for closure-level classification

A repository may be “ready for implementation closure work” while still having yellow or red gates.
Only the full gate logic determines closure.

---
## 14. Definition of done

The MVP is done only if all of the following are true:

1. all required gates for the claimed closure level pass
2. no unresolved semantic drift remains
3. no parallel diagnostics truth remains
4. no parallel routing truth remains authoritative
5. Writers' Room and Improvement Path are operationally useful, not just conceptually protected
6. retrieval is governed and auditable
7. the experience acceptance layer is green at the claimed closure level
8. the full God of Carnage slice works end-to-end under normal and degraded conditions

If any one of the above is false, the MVP is not done.

---

## 15. Final interpretation

A system that satisfies this roadmap is not merely:
- architecturally thoughtful
- multi-model
- retrieval-aware
- diagnostically rich

It is:
- semantically closed
- operationally governable
- experientially testable
- resistant to silent drift
- and closure-classified correctly as either Level A or Level B
