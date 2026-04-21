# Retirement Record (`MVP/` tree)

## Current Decision

**`MVP/` is retained** in the workspace as the intake snapshot source. It has **not** been removed.

## Why Deletion Is Blocked

Per [`Plan.md`](../../../Plan.md) deletion gate and this bundle’s verification posture:

- **Byte reconcile gate (compared domains):** [`integration_conflict_register.md`](./integration_conflict_register.md) now shows **0** divergences for `backend`, `world-engine`, `ai_stack`, `frontend`, `administration-tool`, and `docs` after the snapshot alignment pass (see [`migration_report.md`](./migration_report.md)).
- **Runtime validation gate:** commands in [`domain_validation_matrix.md`](./domain_validation_matrix.md) are not fully **pass** (pytest-backed suites were not executed to completion in-session).
- **Mapping-table verification:** intake heuristics still leave most mapping rows at `pending_verification` until reviewed independently of byte reconcile.

Until those gates close, **no** destructive removal of `MVP/` is permitted.

## When Retirement Would Become Safe

- Mapping and inventory remain complete for every `MVP/` file (refresh intake if the tree changes).
- `integration_conflict_register.md`: either remains empty at the byte layer after reconcile, or each listed conflict has an explicit resolution plus non-`pending` validation status if divergences reappear.
- `domain_validation_matrix.md`: each touched domain shows executed commands with recorded evidence.
- Navigation audit: no **required** operator path depends on raw `MVP/` (only canonical bundle and active code).

## Legacy Remainder

The full `MVP/` directory remains available for diff-backed reconciliation and optional future intake refreshes.
