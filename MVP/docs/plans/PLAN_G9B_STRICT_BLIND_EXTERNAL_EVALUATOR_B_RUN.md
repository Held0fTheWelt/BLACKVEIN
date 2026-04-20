# PLAN_G9B_STRICT_BLIND_EXTERNAL_EVALUATOR_B_RUN

## 1. Scope
- In scope: this document defines an execution-ready plan for a real strict-blind external Evaluator B run.
- Out of scope in this task: scoring, repo ingestion, delta computation, any G9B upgrade, any G10 upgrade, and any Level B or program-closure claim.
- This plan will only define controls, artifacts, validation gates, and handoff boundaries for a later execution.

## 2. Why a new strict-blind run is still needed
- Current materials are materially stronger than earlier evidence because they already include Evaluator B presence, raw Evaluator B artifacts, and delta artifacts.
- The current package still does not satisfy the strict-blind independence bar because documented authorship/process separation remains limited.
- A new strict-blind run is therefore required to produce cleaner independence evidence before any later independence decision.
- This plan is grounded in: `docs/ROADMAP_MVP_GoC.md`, `docs/GoC_Gate_Baseline_Audit_Plan.md`, `docs/audit/gate_G9_experience_acceptance_baseline.md`, `docs/audit/gate_G9B_evaluator_independence_baseline.md`, `docs/audit/gate_G10_end_to_end_closure_baseline.md`, `docs/audit/gate_summary_matrix.md`, `docs/audit/closure_level_classification_summary.md`, `docs/audit/master_goc_baseline_audit_report.md`, `docs/audit/repo_evidence_index.md`, `docs/goc_evidence_templates/`, `docs/plans/PLAN_G9B_REAL_INDEPENDENT_EVALUATOR_B.md`, `docs/g9_evaluator_b_external_package/`, and `tests/reports/evidence/g9_level_a_fullsix_20260410/`.

## 3. Strict-blind external evaluator definition
- A strict-blind external evaluator run will mean scoring is produced in a separate evaluator process with no pre-scoring access to Evaluator A scores or Evaluator A rationales.
- Acceptable examples:
  - a second human evaluator with no prior access to Evaluator A scores/rationales,
  - an external evaluator workflow with separate authorship evidence and visibility logging,
  - an isolated alternate process with documented separation sufficient for audit review.
- Unacceptable examples:
  - same assistant with the same hidden context,
  - prior access to Evaluator A raw matrix without a documented pre-approved exception,
  - post-hoc claims that reinterpret non-blind scoring as blind scoring,
  - derived or tuned scoring based on Evaluator A outputs,
  - copied rationale language from Evaluator A artifacts or prompts.

## 4. Fixed frozen scoring basis
- The run will score only the authoritative frozen six-scenario basis anchored to `tests/reports/evidence/g9_level_a_fullsix_20260410/`.
- Scenario IDs will be fixed to the canonical order in `ai_stack/goc_g9_roadmap_scenarios.py`:
  1. `goc_roadmap_s1_direct_provocation`
  2. `goc_roadmap_s2_deflection_brevity`
  3. `goc_roadmap_s3_pressure_escalation`
  4. `goc_roadmap_s4_misinterpretation_correction`
  5. `goc_roadmap_s5_primary_failure_fallback`
  6. `goc_roadmap_s6_retrieval_heavy`
- Evaluator B will not alter, substitute, merge, rerun, or re-author scenario content in this plan scope.

## 5. Blind outgoing package rules
- The outgoing package will include only:
  - handoff documents from `docs/g9_evaluator_b_external_package/documents/`,
  - templates from `docs/g9_evaluator_b_external_package/templates/`,
  - the six frozen scenario JSON artifacts,
  - optional authorized grounding material only when package policy explicitly allows it.
- The outgoing package will exclude by default:
  - Evaluator A matrix artifacts,
  - Evaluator A rationales,
  - delta artifacts,
  - reconciliation artifacts,
  - G9B internal attempt records,
  - repo-internal notes that can contaminate blind scoring.
- Any exception will require pre-approval and documentation before scoring starts.
- If any documented exception is granted, the exception record will be returned with the evaluator package and treated as part of independence evidence.

## 6. External evaluator identity and process requirements
- The returned package will record:
  - `evaluator_b_id`,
  - evaluator role/type,
  - authorship/process separation statement,
  - `scored_at_utc`,
  - package preparer identity,
  - score generator identity (person/system),
  - visibility scope before scoring,
  - explicit limitations.
- External affiliation alone will not qualify as strict blind; process evidence and authorship separation evidence will be mandatory.

## 7. Required return artifacts
- The returned package will include exactly:
  - `g9_experience_score_matrix_evaluator_b.json`,
  - `g9b_raw_score_sheet_evaluator_b.json`,
  - `g9b_evaluator_b_declaration.json`.
- Required content:
  - all 30 scores required (6 scenarios x 5 criteria; no missing cells),
  - all 30 cell rationales required (one rationale per scored cell),
  - rationales must be independent and must not copy Evaluator A language,
  - complete declaration fields,
  - no omission of visibility statements.
- Artifact structures will follow `docs/goc_evidence_templates/` and `docs/g9_evaluator_b_external_package/templates/`.

## 8. Blindness verification and contamination rules
- Later verification will require:
  - `pre_scoring_visibility_statement`,
  - `visibility_before_scoring` when relevant,
  - explicit statement whether Evaluator A matrix was seen before scoring,
  - explicit statement whether Evaluator A rationales were seen before scoring,
  - explicit statement whether delta/reconciliation artifacts were seen before scoring,
  - explicit statement of any approved exceptions.
- Candidate independence classes for later Task B review:
  - `strict_blind`
  - `documented_exception`
  - `contaminated`
  - `insufficient_authorship_separation`
  - `insufficient_process_separation`
  - `failed_or_incomplete_independence_evidence`
- Raw scoring will be complete and frozen before any later delta or reconciliation activity starts.

## 9. Acceptance criteria for a strict-blind submission
- A later returned package will qualify as a serious strict-blind candidate only if all of the following are true:
  - complete 6x5 matrix with 30/30 scored cells,
  - exact six scenario IDs in canonical scope,
  - exact five criteria per scenario,
  - 30/30 present cell rationales,
  - no visible copying from Evaluator A rationale language,
  - explicit visibility metadata and process metadata,
  - no contradictions between declaration content and package trail.

## 10. Rejection and downgrade rules
- A later submission will be rejected or downgraded from strict blind if any of the following occurs:
  - missing score cells,
  - wrong scenario IDs,
  - wrong criteria set,
  - missing declaration fields,
  - copied Evaluator A rationale language,
  - contradiction between blindness claim and evidence trail,
  - no meaningful authorship separation,
  - undocumented pre-scoring exposure to Evaluator A artifacts,
  - structural mismatch with the fixed frozen basis.

## 11. Handoff-to-ingestion boundary
- This plan covers only the strict-blind external run and return-package expectations.
- A later repo task will ingest returned Evaluator B artifacts, compute A-vs-B delta, evaluate independence sufficiency, update G9B audit artifacts, and decide whether G9B reaches `level_b_capable`.
- This planning task performs none of those later actions.

## 12. Recommended execution sequence
1. Freeze the authoritative G9 basis for this run scope.
2. Assemble the blind outgoing package under strict include/exclude rules.
3. Hand off to a strict-blind external evaluator process.
4. Receive returned Evaluator B artifacts.
5. Validate the returned package structurally and for completeness.
6. Run a later repo task for ingestion, delta, and independence decision.
7. Only after that later task, reconsider G9B status and subsequent aggregation steps.

## 13. Non-goals and disclaimers
- This planning task will not create evaluator B scores.
- This planning task will not upgrade G9B.
- This planning task will not upgrade G10.
- This planning task will not create Level B.
- This planning task will not create MVP or program closure.
- This document defines execution controls for a future strict-blind run only.
