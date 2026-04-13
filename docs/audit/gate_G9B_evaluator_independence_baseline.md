# Gate G9B Baseline: Evaluator Independence

## Gate

- Gate name: G9B Evaluator Independence
- Gate class: evaluative
- Audit subject: evaluator mode declaration, raw-score and delta discipline, optional reconciliation, and consistency with the G9 evidence package from the **same** audit run (`docs/MVPs/MVP_VSL_And_GoC_Contracts/ROADMAP_MVP_GoC.md` §6.10, §11.2A)

## Sequencing Rule

**G9 evidence for the same audit run:** `tests/reports/evidence/g9_level_a_fullsix_20260410/` was produced first (pytest + capture + complete score matrix + threshold validator output). This G9B record applies to **`audit_run_id: g9_level_a_fullsix_20260410`** as the authoritative package.

**Historical runs:** `g9_level_a_20260408` had an incomplete G9 matrix (S4 null). `g9_level_a_fullsix_20260409` had a complete matrix with `pass_all: false`. Neither is the current §6.9 threshold story. Do not treat those bundles as authoritative without explicit `audit_run_id` labeling.

**Additive Level B on the same `audit_run_id`:** A second evaluator does **not** require a new `audit_run_id` when scenario JSONs and the authoritative Evaluator A matrix stay frozen. Add separate Evaluator B matrix + raw sheet + delta + independence narrative **in the same bundle directory**; do not mutate archived scenario evidence or `g9_experience_score_matrix.json` (Evaluator A).

## Prerequisites Consumed from G9 (same run)

- Pytest bundle log: `tests/reports/evidence/g9_level_a_fullsix_20260410/pytest_g9_roadmap_bundle.txt`
- Score matrix (Evaluator A): `tests/reports/evidence/g9_level_a_fullsix_20260410/g9_experience_score_matrix.json` (complete 6×5 grid)
- Threshold output: `tests/reports/evidence/g9_level_a_fullsix_20260410/g9_threshold_validator_output.json` (`complete: true`, `pass_all: true`)
- Run metadata: `tests/reports/evidence/g9_level_a_fullsix_20260410/run_metadata.json`

## Evaluator mode declaration

**Declared mode (`g9b_evaluator_record.json`):** **`level_b_attempt_insufficient_independence`** — Evaluator A and Evaluator B each have a **separate** frozen 6×5 matrix and raw-score sheet pointers; full **per-cell delta** is computed from those matrices. **Independence** remains **below** the roadmap Level B bar (`g9b_evaluator_b_declaration.json`: automated second pass; not a second human adjudicator).

- **evaluator_id (A):** `single_evaluator_g9_level_a_repo_audit` (also recorded in `run_metadata.json` and G9B manifest).
- **evaluator_id (B):** `evaluator_b_claude_system_20260409` — matrix `g9_experience_score_matrix_evaluator_b.json`, raw sheet `g9b_raw_score_sheet_evaluator_b.json` (ingested from strict-blind external handoff return; supersedes prior internal B id `evaluator_b_repo_second_pass_20260411`).
- **Manifest mirror fields:** `evaluator_b_present: true`, `closure_level_status_gate_g9b_reported: level_a_capable`.
- **Level B closure claim:** **Not** asserted. `closure_level_status` for G9B remains **`level_a_capable`**.

## Level B attempt (documented; failed insufficient independence)

A **Level B independence attempt** is recorded **with** a second score set and **honest** non-upgrade:

- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_evaluator_independence_declaration.md` — English narrative: A and B sourcing, delta, limitation, requirements for truthful `level_b_capable`, reconciliation rules.
- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_level_b_attempt_record.json` — `level_b_attempt_status: failed_insufficient_independence`; `reason_codes` include `independence_evidence_insufficient_for_level_b`, `assistant_mediated_not_second_human_adjudicator`, `insufficient_process_separation`, `insufficient_authorship_separation`, `failed_or_incomplete_independence_evidence`. **`independence_classification_primary`:** `insufficient_process_separation`; **`independence_classification_secondary`:** [`failed_or_incomplete_independence_evidence`] (richer Task B review; no forced `task_b_independence_class` in declaration JSON — schema enum would misrepresent the evidence).
- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_evaluator_b_declaration.json` — return left top-level `evaluator_a_matrix_ref` / `score_delta_record_ref` empty; repository Task B added **`repository_task_b_post_return_bundle_linkage`** only for bundle traceability (not supplied by the external return).
- **Historical:** Earlier baseline text stated Evaluator B was absent; that is **superseded** by the current bundle. **`level_b_capable` is still not** used.

**`level_b_capable` bar (strict):** G9B may be marked `level_b_capable` only if the package demonstrates **actual** independence in **process**, **authorship**, and **score generation** — not merely that two files exist. Evaluator B’s scores and `cell_rationale` texts must be produced **before** reconciliation or delta-driven alignment, with **no** post-hoc harmonization of A or B prior to freezing raw sheets and computing deltas. If the independence declaration is **weak, contradictory, or evidentially insufficient**, the baseline must record a **failed** Level B attempt and **must not** upgrade G9B (or gate summary / closure aggregation) to `level_b_capable`.

## Known limitation

Roadmap **Level B** evaluator independence is **not** met: separate matrices and deltas are **not** sufficient when process/authorship evidence remains limited as declared. §6.9 **pass** for G9 remains tied to **Evaluator A** only.

## Raw score preservation

**Evaluator A:** Immutable-style pointer artifact:

- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_raw_score_sheet.json` → references `g9_experience_score_matrix.json` via `frozen_g9_matrix_file_ref`.

**Evaluator B:**

- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_raw_score_sheet_evaluator_b.json` → references `g9_experience_score_matrix_evaluator_b.json`.

Both matrices are **complete** (six scenarios, five criteria). G9 §6.9 threshold **pass** for the roadmap story remains on Evaluator A’s validator output (`pass_all: true`).

## Score delta preservation

**Status:** **Present.** Computed from frozen A and B matrices (authoritative: `scripts/g9b_compute_score_delta.py`).

- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_score_delta_record.json` — `not_applicable_level_a: false`, full `per_cell_delta` (semantics: score_a minus score_b), additive `disagreement_summary` (does not replace the grid).
- Closure rerun check (no regeneration required): `tests/reports/evidence/all_gates_closure_20260409/g9b_delta_recompute_check.json` recomputes the same `per_cell_delta` from preserved A/B matrices.

## Reconciliation evidence

**Optional per roadmap:** None produced. Raw matrices and delta remain primary. Any future reconciliation must keep `must_not_replace_raw: true` and must not supplant raw sheets or deltas.

## Level A vs Level B (Roadmap §6.10)

| Mode | Requirement | This run (`g9_level_a_fullsix_20260410`) |
|------|-------------|------------------------------------------|
| Level A (evaluator discipline + §6.9 anchor) | Raw A preserved; limitation explicit; no false Level B | **Yes** — Evaluator A complete matrix + validator pass; G9B does not falsify independence |
| Level B | Two **independent** evaluators; raw scores; deltas; evidentiary independence | **Not claimed** — `failed_insufficient_independence`; `evaluator_mode_declared` = `level_b_attempt_insufficient_independence` |

## Consistency checks

- **G9 matrix vs G9B raw sheet ref:** Points to the same-path matrix file in the evidence bundle.
- **G9 complete scores:** G9B references the frozen matrix as authoritative for Evaluator A; G9 §6.9 **pass** on the same run is consistent with evaluator-discipline artifacts.
- **Attempt record vs declaration vs manifest:** Align on dual matrices + delta + **no** `level_b_capable`.
- **Delta traceability:** `per_cell_delta` matches arithmetic on `g9_experience_score_matrix.json` vs `g9_experience_score_matrix_evaluator_b.json`.

## Artifact manifest

- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_evaluator_record.json`
- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_level_b_attempt_record.json`
- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_evaluator_independence_declaration.md`
- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_evaluator_b_declaration.json`
- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_score_delta_record.json`
- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_raw_score_sheet.json`
- `tests/reports/evidence/g9_level_a_fullsix_20260410/g9b_raw_score_sheet_evaluator_b.json`

## Status baseline (updated)

- structural_status: `green` *(evaluator-discipline artifacts: dual raw pointers, full delta from frozen matrices, manifest mode `level_b_attempt_insufficient_independence`, failed independence attempt documented without false `level_b_capable`)*
- closure_level_status: `level_a_capable` *(complete G9 grid passes §6.9 on Evaluator A; Level B independence not evidenced; program-wide closure still governed by G10 and global aggregation — not asserted here.)*

**Rationale:** Roadmap §6.10 Level A discipline for G9B is satisfied with **honest** dual-artifact and delta hygiene. **`level_b_capable` is not** used because independence is **insufficient** per declaration. **No** Level B or program closure language is implied.

**Preservation policy applied:** Existing authoritative G9B artifacts under `g9_level_a_fullsix_20260410` remain authoritative because closure rerun validation did not contradict them; no cosmetic regeneration was performed.

## Evidence quality

- evidence_quality: `high` for artifact discipline (separate raw sheets, computed delta, no sham second human).
- justification: Full 6×5 grids for A and B, archived validator output for A (`pass_all: true`), explicit failed Level B attempt with traceable deltas.

## Execution risks carried forward

- Strengthening independence: would require evidential process/authorship separation meeting the **Level B** bar; only then set `evaluator_mode_declared` to `level_b_independent_evaluators` and `closure_level_status_gate_g9b_reported` to `level_b_capable` if appropriate.
- G9B must always reference the **same** G9 bundle by `audit_run_id` to avoid cross-run mixing.
