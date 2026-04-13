# Contractify `reports/`

This directory holds **machine-generated JSON** from `discover` / `audit` runs. Only **`.gitkeep`** is committed so local exports do not pollute git history.

## Why it looks empty

Root [`.gitignore`](../../../.gitignore) ignores `**/contractify/reports/*.json`. Treat anything you drop here as **ephemeral evidence** unless you rename it and store it elsewhere (for example a release bundle or ticket attachment).

## Regenerate locally

From the **repository root**:

```bash
python -m contractify.tools discover --json --out "'fy'-suites/contractify/reports/contract_discovery.json"
python -m contractify.tools audit --json --out "'fy'-suites/contractify/reports/contract_audit.json"
```

## Committed shape samples

For **small, stable JSON shapes** used in docs and CI, see [`../examples/`](../examples/) (`*.sample.json`). Refresh those when the payload schema changes; keep `reports/` for full-fidelity local runs only.
