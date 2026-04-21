# Retirement Record (`MVP/` tree)

## Current Decision

**`MVP/` is retained** in the workspace as the intake snapshot source. It has **not** been removed.

## Why Deletion Is Blocked

Per [`Plan.md`](../../../Plan.md) deletion gate and this bundle’s verification posture:

- **Byte reconcile gate (compared domains):** [`integration_conflict_register.md`](./integration_conflict_register.md) now shows **0** divergences for `backend`, `world-engine`, `ai_stack`, `frontend`, `administration-tool`, and `docs` after the snapshot alignment pass (see [`migration_report.md`](./migration_report.md)).
- **Runtime validation gate:** commands in [`domain_validation_matrix.md`](./domain_validation_matrix.md) are not fully **pass** because backend remains partial/user-skipped; `world-engine`, `ai_stack`, `frontend`, `administration-tool`, and canonical docs now have recorded pass outcomes.
- **Mapping-table verification:** no rows remain `pending_verification`, but [`mapping_verification_report.md`](./mapping_verification_report.md) records **7,843** follow-up rows (**7,755** `blocked_missing_active_target`; **88** `needs_reconcile_bytes`). Current triage separates the follow-up surface into **5,480** generated-output rows, **1,360** nested `repo/` snapshot rows, **431** runtime state/database rows, **191** legacy MVP/governance reference rows, **210** fy suite source/docs candidates, **128** validation-evidence rows, **42** active source/config candidates, and **1** duplicate nested suite snapshot row. The report’s **Prioritized Reconciliation Candidate Index** lists the **252** source/config and fy suite source/docs rows that should be reviewed before any generated/runtime/evidence waiver. **59** rows are mechanically verified as text-equivalent after normalized line endings.
- **Mapping closure decision gate:** [`mapping_closure_decisions.md`](./mapping_closure_decisions.md) records class-level treatment for generated output, nested snapshots, runtime state, validation evidence, and legacy MVP/governance reference material. That record is a no-loss rationale, not a deletion authorization; explicit sign-off is still required before destructive retirement.

Until those gates close, **no** destructive removal of `MVP/` is permitted.

## When Retirement Would Become Safe

- Mapping and inventory remain complete for every `MVP/` file (refresh intake if the tree changes).
- `integration_conflict_register.md`: either remains empty at the byte layer after reconcile, or each listed conflict has an explicit resolution plus non-`pending` validation status if divergences reappear.
- `domain_validation_matrix.md`: each touched domain shows executed commands with recorded evidence.
- `source_to_destination_mapping_table.md`: every row has a final non-pending status and no `blocked_*` or `needs_*` rows remain, or each remaining row has an explicit recorded waiver/sign-off.
- Navigation audit: no **required** operator path depends on raw `MVP/` (only canonical bundle and active code).

## Legacy Remainder

The full `MVP/` directory remains available for diff-backed reconciliation and optional future intake refreshes.
