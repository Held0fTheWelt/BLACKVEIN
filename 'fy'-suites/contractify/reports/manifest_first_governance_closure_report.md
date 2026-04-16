# Manifest-first Contractify governance closure report

## What changed

- Added repo-root `fy-manifest.yaml`.
- Pinned `suites.contractify.openapi` to `docs/api/openapi.yaml`.
- Pinned `suites.contractify.max_contracts` to `60` so the runtime/MVP spine is reproducible from the default repo-root CLI.
- Updated `contractify.tools.hub_cli` so `discover` / `audit` read the manifest-backed ceiling when `--max-contracts` is omitted.
- Added `execution_profile` to Contractify discover/audit payloads.
- Refreshed tracked artifacts:
  - `reports/contract_audit.json`
  - `reports/contract_discovery.json`
  - `reports/runtime_mvp_attachment_report.md`
  - `state/RUNTIME_MVP_SPINE_ATTACHMENT.md`
- Added manifest-first regression tests for repo-root validation, non-fallback audit execution, and tracked-audit reproducibility.

## Canonical audit execution

Run from repository root:

```bash
python -m contractify.tools audit --json --out "'fy'-suites/contractify/reports/contract_audit.json"
```

Because `fy-manifest.yaml` now defines `suites.contractify.max_contracts = 60`, the canonical runtime/MVP attachment wave is reproduced without hidden extra CLI flags.

## Commands run

```bash
PYTHONPATH="$(pwd)/'fy'-suites" python -m fy_platform.tools validate-manifest --project-root .
PYTHONPATH="$(pwd)/'fy'-suites" python -m contractify.tools audit --json --out "'fy'-suites/contractify/reports/contract_audit.json" --quiet
PYTHONPATH="$(pwd)/'fy'-suites" python -m contractify.tools discover --json --out "'fy'-suites/contractify/reports/contract_discovery.json" --quiet
PYTHONPATH="$(pwd)/'fy'-suites" python -m pytest "'fy'-suites/contractify/tools/tests" -q
PYTHONPATH="$(pwd)/'fy'-suites" python -m pytest "'fy'-suites/fy_platform/tests" -q
```

## Results

- Manifest validation: `ok: true`
- Canonical audit stats: `43 contracts`, `19 projections`, `239 relations`, `8 drifts`, `5 conflicts`, `2 manual unresolved areas`
- Contractify tests: passing
- fy-platform tests: passing
- Legacy fallback deprecation: not emitted on canonical repo-root Contractify audit run

## Intentionally unresolved

- Backend transitional session retirement timeline remains unresolved.
- Writers’ Room vs RAG overlap remains explicitly reviewable.
- OpenAPI -> Postman drift remains visible and was not falsely claimed as fixed in this closure pass.
