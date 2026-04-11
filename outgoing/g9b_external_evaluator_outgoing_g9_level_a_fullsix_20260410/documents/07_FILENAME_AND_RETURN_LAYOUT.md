# Filename conventions and return folder layout

## Canonical return filenames (Evaluator B)

Use **exact** names so repository ingestion and scripts match `docs/goc_evidence_templates/README.md`:

| Role | Filename |
|------|----------|
| Evaluator B experience matrix | `g9_experience_score_matrix_evaluator_b.json` |
| Evaluator B raw score sheet | `g9b_raw_score_sheet_evaluator_b.json` |
| Evaluator B declaration | `g9b_evaluator_b_declaration.json` |

**Do not** rename to `matrix_b_final.json` or similar.

## Recommended return folder (Evaluator B → owner)

```text
evaluator_b_return_g9_level_a_fullsix_20260410/
  g9_experience_score_matrix_evaluator_b.json
  g9b_raw_score_sheet_evaluator_b.json
  g9b_evaluator_b_declaration.json
  04_BLINDNESS_CONTAMINATION_CHECKLIST.md    # optional: if owner required signed copy
```

## Path fields inside JSON

- In `g9b_raw_score_sheet_evaluator_b.json`, `frozen_g9_matrix_file_ref` should reference the matrix **as returned in the same folder**, e.g. `./g9_experience_score_matrix_evaluator_b.json`. Maintainers may rewrite to repo-relative paths during ingestion.  
- `declaration_ref` may point to `./g9b_evaluator_b_declaration.json` for the same reason.

## `evaluator_b_id`

Choose a **stable, unique** id for this pass (e.g. `evaluator_b_human_orgname_20260415`). Use the **same** value in:

- Matrix top-level `evaluator_b_id` (recommended additional property)  
- Raw sheet `evaluator_id`  
- Declaration `evaluator_b_id`

## Helper: package manifest (optional)

Owners may add a one-line manifest when zipping returns:

```text
evaluator_b_return_manifest.txt
  evaluator_b_id: <id>
  scored_at_utc: <iso>
  files_sha256: <optional>
```

Not required by schema; improves traceability for large orgs.
