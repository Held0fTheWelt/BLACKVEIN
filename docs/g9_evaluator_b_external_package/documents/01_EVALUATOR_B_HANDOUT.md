# Evaluator B — external handout (G9 frozen six)

## Purpose

You are asked to perform an **independent** scoring pass on **six fixed** God of Carnage (GoC) experience-acceptance scenarios for audit run **`g9_level_a_fullsix_20260410`**. Your output supports later **Gate G9B** independence review. It does **not**, by itself, establish roadmap Level B or any program closure.

## Fixed scenario IDs (normative order)

Score **exactly** these six scenarios, in this order, with **no substitutions**:

1. `goc_roadmap_s1_direct_provocation` — Direct provocation  
2. `goc_roadmap_s2_deflection_brevity` — Deflection / brevity  
3. `goc_roadmap_s3_pressure_escalation` — Pressure escalation  
4. `goc_roadmap_s4_misinterpretation_correction` — Misinterpretation / correction  
5. `goc_roadmap_s5_primary_failure_fallback` — Primary model failure + fallback (**`failure_oriented: true`**)  
6. `goc_roadmap_s6_retrieval_heavy` — Retrieval-heavy context  

## Five scoring criteria (roadmap §6.9)

For **each** scenario, assign an integer **1–5** for:

1. `dramatic_responsiveness`  
2. `truth_consistency`  
3. `character_credibility`  
4. `conflict_continuity`  
5. `graceful_degradation`  

Detailed guidance: [02_SCORING_INSTRUCTIONS_CRITERIA.md](02_SCORING_INSTRUCTIONS_CRITERIA.md).

**S5 note:** Only scenario 5 is **`failure_oriented: true`** in the matrix. For roadmap semantics, **graceful degradation** on that row is especially important (validator applies a stricter floor to failure-oriented rows when maintainers run `scripts/g9_threshold_validator.py`). Your job is to **score honestly** per the rubric; you are **not** required to run the repo validator unless your engagement explicitly says so.

## Blindness and default contamination rules

**Default (recommended for strict independence evidence):**

- Do **not** view **Evaluator A’s** matrix (`g9_experience_score_matrix.json`) or **Evaluator A’s per-cell rationales** before your **raw** scoring is complete and frozen.  
- Do **not** view **A-vs-B deltas**, **reconciliation** drafts, or **Evaluator B** artifacts from a **prior** repo pass before your raw scoring, unless your engagement defines a documented exception **before** you begin.

**If you are allowed to see A’s scores or rationales before scoring:** that must be **written down before scoring starts** (who approved, what you saw). The submission may be treated as **`documented_exception`** or **`contaminated`** for strict blind review—see [04_BLINDNESS_CONTAMINATION_CHECKLIST.md](04_BLINDNESS_CONTAMINATION_CHECKLIST.md).

## What you may use

- The **six** frozen scenario JSON files listed in [03_FROZEN_SOURCE_MANIFEST.md](03_FROZEN_SOURCE_MANIFEST.md).  
- Optional dramatic grounding **only if** the package owner included it in your handoff: e.g. `resources/Script-God-Of-Carnage-Script-by-Yazmina-Reza.pdf`.  
- Optional canonical repo references **only if** explicitly included or authorized in your handoff (e.g. `content/modules/god_of_carnage/`, `docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md`). Do **not** treat the whole repository as automatically in scope.

## What you must not do

- Do **not** change scenario IDs, merge scenarios, or substitute fixtures.  
- Do **not** copy or lightly paraphrase **Evaluator A** `cell_rationale` text. Rationales must be **your** reasoning, grounded in the scenario JSON (and authorized grounding).  
- Do **not** edit or replace Evaluator A’s archived matrix file in the repo (that is the maintainer’s policy; you typically never receive it in a blind package).  
- Do **not** cite non-archived hidden model “chain of thought” as evidence—only what you put in the declared JSON fields.  
- Do **not** set `task_b_independence_class` in your declaration; repository Task B assigns that after review.

## Deliverables (return to package owner)

Return **three** completed JSON files using the **canonical names**:

1. `g9_experience_score_matrix_evaluator_b.json` — full **6×5** grid, integers 1–5, **every** `cell_rationale` filled (non-empty strings).  
2. `g9b_raw_score_sheet_evaluator_b.json` — pointer to your matrix file (see template).  
3. `g9b_evaluator_b_declaration.json` — includes mandatory **`pre_scoring_visibility_statement`** (exactly what you were/were not allowed to see before scoring), process and grounding notes, and an honest independence/limitation assessment.

Start from the templates in `../templates/` and follow [05_SUBMISSION_CHECKLIST.md](05_SUBMISSION_CHECKLIST.md).

## What repository ingestion will do later (Task B)

Maintainers **validate** structure (schemas, completeness), **ingest** files into the governed evidence directory, may run `scripts/g9b_compute_score_delta.py` against **frozen** A and B matrices, and update G9B-related records **only** if independence evidence warrants it. **You** do not perform Task B in this engagement unless explicitly contracted.

## What this task / package does not claim

- **No** claim that this package or your scores upgrade Gate **G9B** to `level_b_capable`.  
- **No** claim of Gate **G10** or **MVP** closure.  
- **No** claim that a prior internal “Evaluator B” pass in the repo was independent; your pass is evaluated on **your** process and artifacts.  
- **No** fabricated scores: templates are empty until **you** fill them.

## Questions

Direct operational questions to the **package owner** (see [INTERNAL_PACKAGE_OWNER_INSTRUCTIONS.md](INTERNAL_PACKAGE_OWNER_INSTRUCTIONS.md)). Technical schema questions: `docs/goc_evidence_templates/schemas/` and `docs/plans/PLAN_G9B_REAL_INDEPENDENT_EVALUATOR_B.md`.
