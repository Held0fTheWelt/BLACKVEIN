# Packaging and assembly — outgoing Evaluator B package

How to build the **outgoing** zip (or folder) from repository materials for a **real external** Evaluator B.

## Default policy (normative)

**Standard outgoing package includes:**

1. All documents from `docs/g9_evaluator_b_external_package/documents/` (or a curated subset if you must minimize size—always include **01** handout, **02** scoring instructions, **03** manifest, **04–05** checklists, and **07** return layout).  
2. Empty JSON templates from `docs/g9_evaluator_b_external_package/templates/`.  
3. **Exactly six** scenario JSON files from `tests/reports/evidence/g9_level_a_fullsix_20260410/` (see [03_FROZEN_SOURCE_MANIFEST.md](03_FROZEN_SOURCE_MANIFEST.md)).

**Standard outgoing package does *not* include by default:**

- `run_metadata.json`  
- `pytest_g9_roadmap_bundle.txt`  

**Rationale:** Keeps the handoff focused on **scoring inputs** (scenario captures), reduces noise for blind scoring, and avoids shipping technical witness material the evaluator does not need to judge dramatic quality. If you add either file, treat it as an **explicit opt-in** and note it in your handoff cover email and/or an `OPTIONAL_WITNESS_FILES_INCLUDED.txt` in the zip.

## Optional opt-in: technical witness files

Add **only** if the package owner **explicitly** chooses to include them (e.g. auditor wants pytest proof alongside the frozen JSON):

| File | Source path |
|------|-------------|
| `run_metadata.json` | `tests/reports/evidence/g9_level_a_fullsix_20260410/run_metadata.json` |
| `pytest_g9_roadmap_bundle.txt` | `tests/reports/evidence/g9_level_a_fullsix_20260410/pytest_g9_roadmap_bundle.txt` |

**When you opt in:** Update [03_FROZEN_SOURCE_MANIFEST.md](03_FROZEN_SOURCE_MANIFEST.md) in your **assembled** copy (or attach a short `ASSEMBLY_NOTES.txt`) listing these files so the handoff is auditable.

## Optional: GoC script PDF

| File | Source path |
|------|-------------|
| `Script-God-Of-Carnage-Script-by-Yazmina-Reza.pdf` | `resources/Script-God-Of-Carnage-Script-by-Yazmina-Reza.pdf` |

Include only if authorized; large binary—confirm licensing/distribution with project owners.

## Must **exclude** (default blind package)

From `tests/reports/evidence/g9_level_a_fullsix_20260410/` (and elsewhere), **do not** copy:

- `g9_experience_score_matrix.json` (Evaluator A)  
- `g9b_raw_score_sheet.json` (A)  
- `g9_experience_score_matrix_evaluator_b.json` (prior B, if present)  
- `g9b_raw_score_sheet_evaluator_b.json` (prior B)  
- `g9b_score_delta_record.json`, `g9b_evaluator_record.json`, `g9b_level_b_attempt_record.json`, reconciliation artifacts  
- Validator outputs (`g9_threshold_validator_*`) — not needed for external scoring

## Recommended folder layout (outgoing zip)

```text
g9_evaluator_b_handoff_g9_level_a_fullsix_20260410/
  README.txt                    # pointer: start with documents/01_EVALUATOR_B_HANDOUT.md
  documents/                    # copy from docs/g9_evaluator_b_external_package/documents/
  templates/                    # copy from docs/g9_evaluator_b_external_package/templates/
  scenarios/                    # six scenario_*.json only (default)
  optional_script/              # only if PDF included
    Script-God-Of-Carnage-Script-by-Yazmina-Reza.pdf
  optional_witness/             # only if run_metadata / pytest log opted in
    run_metadata.json
    pytest_g9_roadmap_bundle.txt
```

## Root README

Copy `docs/g9_evaluator_b_external_package/README.md` to the zip root as `PACKAGE_README.md` **or** add a one-line `README.txt` pointing evaluators to `documents/01_EVALUATOR_B_HANDOUT.md`.

## Versioning

If you revise instructions **without** changing frozen scenarios, bump a **package version string** in your cover note (e.g. `handoff_package_version: 2026-04-09-1`). Do not fork duplicate “v2 final” instruction sets in-repo unless maintainers require it.
