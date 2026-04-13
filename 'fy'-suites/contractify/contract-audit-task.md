# Contractify — contract audit task (analysis track)

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language) — procedure only here.

## Purpose

Produce **evidence-backed** contract state: **discovery** (A–E heuristics), **anchoring** hints, **projection** edges, **drift** signals (including deterministic Postman/OpenAPI checks), and **actionable units** suitable for backlog rows in [`contract_governance_input.md`](contract_governance_input.md).

This is the **analysis** counterpart to [`contract-solve-task.md`](contract-solve-task.md).

## Preconditions

- Repository root as current working directory.
- Python 3.10+.
- Optional: `pip install -e .` so the `contractify` console script resolves.

## Procedure

1. **Read scope ceilings** — [`CONTRACT_GOVERNANCE_SCOPE.md`](CONTRACT_GOVERNANCE_SCOPE.md) (automation thresholds, projection rule).
2. **Pre-work context (human)** — skim [`state/PREWORK_REPOSITORY_CONTRACT_REALITY.md`](state/PREWORK_REPOSITORY_CONTRACT_REALITY.md) for repository-specific anchors already known.
3. **Run machine audit** — emit JSON under `reports/`:

   ```bash
   python -m contractify.tools audit --json --out "'fy'-suites/contractify/reports/contract_audit.json"
   ```

4. **Interpret** — treat `drift_findings` as **evidence**:
   - `deterministic: true` → fix or acknowledge promptly when severity ≥ medium.
   - `deterministic: false` → human triage; do not auto-rewrite normative docs from heuristics.
5. **Backlog** — translate `actionable_units` into **one row per coherent slice** in [`contract_governance_input.md`](contract_governance_input.md) (prefer concrete scopes, not counts).
6. **Cursor skill sync** — if `superpowers/*/SKILL.md` changed:

   ```bash
   python "./'fy'-suites/contractify/tools/sync_contractify_skills.py"
   ```

## Outputs (verification artefacts)

- `reports/contract_audit.json` (or slice-local path).
- Updated **CG-*** rows in `contract_governance_input.md` when work is scheduled.

## Completion (analysis slice)

Done when JSON is reviewed, high-severity deterministic drifts are triaged, and the backlog lists the next **solve** slices with owners or ordering notes.

## References

- Drift methods: [`README.md`](README.md) section **Drift detection (implemented methods)**.
- Solve track: [`contract-solve-task.md`](contract-solve-task.md)
- Reset: [`contract-reset-task.md`](contract-reset-task.md)
