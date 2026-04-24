# G9B evaluator independence declaration — `g9_level_a_fullsix_20260410`

**Project-facing language: English.** This file records the evidentiary status of evaluator discipline and a **Level B (dual-evaluator independence) attempt** against the fixed six-scenario G9 bundle in this directory.

## Fixed scenario and scoring basis (unchanged)

- **audit_run_id:** `g9_level_a_fullsix_20260410`
- **Authoritative G9 scenario JSON + pytest + threshold artifacts:** unchanged; see `gate_G9_experience_acceptance_baseline.md`.
- **§6.9 threshold pass (roadmap):** remains anchored on Evaluator A only: `g9_experience_score_matrix.json` and `g9_threshold_validator_output.json`. Evaluator B’s matrix may be validated separately for transparency; it does **not** replace the authoritative §6.9 pass story for G9.

## Evaluator A (evidenced)

| Field | Value |
|-------|--------|
| **evaluator_id** | `single_evaluator_g9_level_a_repo_audit` |
| **Raw score evidence** | `g9_experience_score_matrix.json` (referenced by `g9b_raw_score_sheet.json`) |
| **Role** | Single-evaluator repository audit session (matrix metadata and `run_metadata.json`). |
| **Scoring basis** | Per-cell scores 1–5 and `cell_rationale` grounded in scenario JSON files in this bundle. |

## Evaluator B (present; independence limited)

- **Status:** `g9_experience_score_matrix_evaluator_b.json` is committed for this `audit_run_id`, with `g9b_raw_score_sheet_evaluator_b.json` as immutable-style pointer. The current matrix is the **ingested return** from the strict-blind external handoff package (`outgoing/g9b_strict_blind_external_evaluator_HANDOFF_g9_level_a_fullsix_20260410/`), scorer identity `evaluator_b_claude_system_20260409`. Rationales are a separate `cell_rationale` set from Evaluator A.
- **Process and limitation:** `g9b_evaluator_b_declaration.json` records an **automated** second pass (`independence_and_process.evaluator_role_type: automated_system_evaluator_second_pass`) and `independence_assessment: automated_system_evaluator_strict_blind_limited_grounding`. That remains **insufficient** for roadmap **Level B** independence (§6.10): not a second human adjudicator, and process/authorship separation does not meet the Level B bar even though the return package **claims** pre-scoring blindness to Evaluator A’s matrix and rationales.
- **Task B review (richer classification, not squeezed into `task_b_independence_class`):** The declaration JSON does **not** set `task_b_independence_class` (schema allows only `strict_blind` \| `documented_exception` \| `contaminated`; forcing a value would misrepresent the evidence). See `g9b_level_b_attempt_record.json` for **`independence_classification_primary`: `insufficient_process_separation`** and **`independence_classification_secondary`**: [`failed_or_incomplete_independence_evidence`] (external return omitted top-level `evaluator_a_matrix_ref` and `score_delta_record_ref`).
- **Repository-only bundle linkage (not part of the external return):** After ingest, repository Task B added **`repository_task_b_post_return_bundle_linkage`** in `g9b_evaluator_b_declaration.json` with relative paths to Evaluator A’s matrix and `g9b_score_delta_record.json` for traceability. **Top-level** `evaluator_a_matrix_ref` and `score_delta_record_ref` remain **empty strings** as in the returned JSON — do **not** read those empty fields as the external evaluator having supplied canonical paths.
- **Delta:** `g9b_score_delta_record.json` holds the full 6×5 grid of `score_a_minus_score_b` (recomputed from frozen A and the ingested B matrix via `scripts/g9b_compute_score_delta.py`), with an additive `disagreement_summary` (11 nonzero cells on the current pair). Disagreement is **not** collapsed out of view.

## Historical note (superseded wording)

Earlier versions of this bundle stated that Evaluator B was absent, or referenced an internal second pass id `evaluator_b_repo_second_pass_20260411`. That is **obsolete**: the strict-blind handoff return is now the on-disk B matrix. **What has not changed** is that **`level_b_capable` is still not asserted** for G9B.

## What would be required for a truthful `level_b_capable` on G9B

Per roadmap §6.10 and repository audit discipline, G9B may be marked **`level_b_capable` only if** the evidence package shows **actual** independence—not merely that two files exist:

1. **Process:** Evaluator B uses a **separate** scoring workflow and rubric/prompt contract from Evaluator A, evidentially documented.
2. **Authorship:** Declared identity of who produced B’s matrix and rationales, with credible separation from A.
3. **Score generation:** B’s numeric scores and `cell_rationale` texts are produced **before** reconciliation or delta-driven alignment; **no** post-hoc harmonization of A or B prior to freezing raw sheets and computing deltas.
4. **Separate raw sheets:** preserved (this bundle satisfies file separation).
5. **Deltas:** full `per_cell_delta` (this bundle satisfies computation from frozen matrices).
6. **Weak or contradictory independence narrative:** If the declaration remains insufficient, the baseline must **not** upgrade G9B to `level_b_capable`. **Current assessment:** insufficient — see `g9b_level_b_attempt_record.json` (`failed_insufficient_independence`).

## Reconciliation

- Optional only; must not replace raw sheets or delta records (`must_not_replace_raw: true` when used). None produced for this run.

## Current gate language (honest)

- **G9B `closure_level_status`:** **`level_a_capable`** — Evaluator A discipline and §6.9 story remain as before; dual matrices and delta are **ingested** but **do not** satisfy Level B independence.
- **`g9b_evaluator_record.json`:** `evaluator_mode_declared` = `level_b_attempt_insufficient_independence` (two scorings present; independence below Level B bar).
- **No G10 or MVP/program closure** is asserted from this G9B update.
