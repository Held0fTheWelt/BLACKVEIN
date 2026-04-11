# Evaluator B — submission checklist

Use before returning files to the package owner.

## Files and names

- [ ] `g9_experience_score_matrix_evaluator_b.json` — exact filename (Evaluator B matrix).  
- [ ] `g9b_raw_score_sheet_evaluator_b.json` — raw score sheet for B.  
- [ ] `g9b_evaluator_b_declaration.json` — declaration with mandatory visibility statement.

## Matrix completeness (6×5)

- [ ] Six scenarios, **exact** `scenario_id` values and order per handout.  
- [ ] `failure_oriented` is `true` **only** for `goc_roadmap_s5_primary_failure_fallback`.  
- [ ] Every score is an **integer 1–5** (no nulls in final submission).  
- [ ] Every criterion has a **non-empty** `cell_rationale` string (6 scenarios × 5 criteria = **30 rationales**).  
- [ ] `criteria` array matches the five roadmap keys, in a sensible fixed order (use the template order).  
- [ ] `schema` = `goc_g9_experience_score_matrix_v1`.  
- [ ] `audit_run_id` = `g9_level_a_fullsix_20260410` (unless owner agreed a different governed run).  
- [ ] `scored_at_utc` set to when **raw** scoring finished (ISO-8601 UTC string).  
- [ ] `evaluator_b_id` and `scorer_role` (or equivalent top-level id) identify **you** / your pass unambiguously.

## Raw score sheet

- [ ] `schema` = `goc_g9b_raw_score_sheet_v1`.  
- [ ] `evaluator_id` matches `evaluator_b_id` from the declaration/matrix.  
- [ ] `frozen_g9_matrix_file_ref` points to your returned matrix (e.g. `./g9_experience_score_matrix_evaluator_b.json`).  
- [ ] `frozen_at_utc` set when you freeze the matrix.  
- [ ] `inline_matrix` is `null` if using file ref only.

## Declaration

- [ ] `schema` = `goc_g9b_evaluator_b_declaration_v1`.  
- [ ] **`pre_scoring_visibility_statement`** is present, non-empty, and **accurate**.  
- [ ] `independence_assessment` and limitation fields are **honest** (no implied Level B pass).  
- [ ] `task_b_independence_class` is **omitted** (Task B assigns after repo review).  
- [ ] `score_delta_record_ref` left empty or omitted **until** maintainers compute delta (do not invent paths).

## Optional validation

- [ ] JSON validates against `docs/goc_evidence_templates/schemas/*.schema.json` (if you have a validator installed).

## Packaging

- [ ] Return folder contains **only** agreed artifacts (no accidental inclusion of Evaluator A matrix or prior B matrix unless documented exception).  
- [ ] [04_BLINDNESS_CONTAMINATION_CHECKLIST.md](04_BLINDNESS_CONTAMINATION_CHECKLIST.md) completed and included if required by owner.
