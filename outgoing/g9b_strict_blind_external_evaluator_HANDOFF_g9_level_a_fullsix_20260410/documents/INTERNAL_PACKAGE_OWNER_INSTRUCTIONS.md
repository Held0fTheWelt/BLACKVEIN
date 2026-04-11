# Internal instructions — package owner (handoff to Evaluator B)

**Audience:** Repository maintainer or audit owner assembling the **outgoing** package and receiving the **return** package. Not for external publication as the primary scoring brief (use **01_EVALUATOR_B_HANDOUT** for Evaluator B).

## What to include (default)

1. **Instructions and checklists** from `docs/g9_evaluator_b_external_package/documents/`.  
2. **Templates** from `docs/g9_evaluator_b_external_package/templates/`.  
3. **Six** frozen `scenario_goc_roadmap_s*.json` files from `tests/reports/evidence/g9_level_a_fullsix_20260410/`.  
4. Optional PDF from `resources/Script-God-Of-Carnage-Script-by-Yazmina-Reza.pdf` if policy allows.  
5. Optional module/contract excerpts **only** if you deliberately add them (zip subfolder); stay within the allowlist in [03_FROZEN_SOURCE_MANIFEST.md](03_FROZEN_SOURCE_MANIFEST.md).

## What **not** to include (default — preserve blindness)

- Evaluator A matrix and rationales (`g9_experience_score_matrix.json`).  
- Any **prior** Evaluator B matrix / raw sheet / delta from the repo.  
- `g9b_score_delta_record.json`, reconciliation drafts, `g9b_evaluator_record.json`, `g9b_level_b_attempt_record.json`.  
- **By default:** `run_metadata.json` and `pytest_g9_roadmap_bundle.txt` — see [06_PACKAGING_AND_ASSEMBLY.md](06_PACKAGING_AND_ASSEMBLY.md); add only with explicit opt-in and documentation.

## Blindness by default

Assume Evaluator B **must not** see A’s scores or rationales until B’s raw grid is frozen. If you **must** expose A (e.g. training calibration—discouraged for strict G9B), obtain **written** pre-scoring approval and have B record it in `pre_scoring_visibility_statement` **before** scoring.

## Documenting exceptions

If you deviate from the default file list:

1. Date and sign (or email thread id) **who** approved the deviation.  
2. List **exact files** B was allowed to see **before** scoring.  
3. Store that note with the return bundle for Task B (`strict_blind` vs `documented_exception` vs `contaminated` classification).

## Collecting returned artifacts without contamination

- Prefer a **clean** return folder: only the three JSON files from [07_FILENAME_AND_RETURN_LAYOUT.md](07_FILENAME_AND_RETURN_LAYOUT.md).  
- Do **not** merge B’s return into a working tree that already has A open in the same editor session in a way that overwrites paths—use a **separate** `return_from_evaluator_b/` directory.  
- Compute **deltas** and update G9B records **only** in **Task B** after structural validation—see `docs/plans/PLAN_G9B_REAL_INDEPENDENT_EVALUATOR_B.md`.

## Hand back to maintainers (Task B)

1. Verify [05_SUBMISSION_CHECKLIST.md](05_SUBMISSION_CHECKLIST.md).  
2. Ingest into `tests/reports/evidence/g9_level_a_fullsix_20260410/` **or** a successor directory per project policy—**do not** overwrite frozen Evaluator A matrix or scenario JSONs.  
3. Run `scripts/g9b_compute_score_delta.py` when two frozen matrices exist.  
4. Set `task_b_independence_class` and related records **only** after independence review.

## Non-claims

Sending this package does **not** upgrade G9B, G10, or assert MVP closure. A second JSON file set does **not** imply Level B independence.
