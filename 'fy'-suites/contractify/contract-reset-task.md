# Contractify — reset / recovery task

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language) — procedure only here.

## When to use

- The governance backlog was corrupted or duplicated beyond practical merge.
- You need a **clean slate** for `contract_governance_input.md` while keeping suite code intact.

## Procedure

1. Archive the current backlog (copy `contract_governance_input.md` to a dated path under `state/` if valuable).
2. Replace contents from [`templates/contract_governance_input.EMPTY.md`](templates/contract_governance_input.EMPTY.md).
3. Re-run audit JSON and rebuild CG rows from `actionable_units` only.

## Do **not** use reset for

- Avoiding triage of deterministic drift (fix or document waiver instead).
- Deleting `reports/*.json` that CI or reviewers rely on without replacement evidence.
