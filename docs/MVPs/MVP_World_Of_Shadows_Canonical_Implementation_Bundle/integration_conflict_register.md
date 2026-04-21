# integration_conflict_register

## Global reconciliation policy

Rows record **byte-level divergence** between `MVP/<domain>/...` snapshots and the active repository. Until a row is individually reviewed, the **active tree remains authoritative** for shipped runtime and docs; `merge_after_reconciliation` forbids blind overwrite, not automatic MVP adoption.

Validation status `pending` means no owner has signed merge, selective cherry-pick, or explicit MVP replacement for that path yet.

## Paths excluded from comparison

The following are **not** compared and do not appear as reconciliation or conflict rows: cache and tool output (`.pytest_cache/`, `__pycache__/`, `.egg-info/`, `.fydata/`, `node_modules/`), local/runtime trees (`var/`, `runtime_data/`, `evidence/`, `instance/`), generated bundles (`generated/`), and coverage marker files named `.coverage`. Treat MVP copies of those paths as non-authoritative snapshot noise.

Total meaningful conflicts: 0

| conflict ID | affected source files | affected active destination files | conflict type | chosen resolution | justification | validation status |
|---|---|---|---|---|---|---|

## Current status

No byte-level divergences remain among compared paths (`backend`, `world-engine`, `ai_stack`, `frontend`, `administration-tool`, `docs`). Re-run `python scripts/mvp_reconcile.py` after substantive edits on either side of a compared pair.
