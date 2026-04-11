# Workstream state: Backend Runtime and Services

## Current objective

Run backend runtime and service changes under [`EXECUTION_GOVERNANCE.md`](EXECUTION_GOVERNANCE.md). Structural refactors: [`despaghettify/despaghettification_implementation_input.md`](../despaghettification_implementation_input.md) (input list, structure scan, optional work log). Keep orientation numbers and hotspots only there — do not duplicate here.

## Current repository status

- Typical scope: `backend/app/runtime`, `backend/app/services`, `backend/app/api/v1`, related tests.
- After the next **wave**: place a scope snapshot under `artifacts/workstreams/backend_runtime_services/pre/` (see naming convention in the input list).

## Hotspot / target status

- — *(Short note after review/scan if needed.)*

## Last completed wave/session

- — *(Date, **DS-ID(s)**, summary; links to `pre|post` artefacts relative to `despaghettify/state/`.)*

## Pre-work baseline reference

Canonical pattern (create files only when a wave runs):

- `artifacts/workstreams/backend_runtime_services/pre/git_status_scope.txt` *(optional)*
- `artifacts/workstreams/backend_runtime_services/pre/session_YYYYMMDD_DS-xxx_*` *(claim, snapshot, collect, … — see governance)*

## Post-work verification reference

- `artifacts/workstreams/backend_runtime_services/post/session_YYYYMMDD_DS-xxx_*`
- Pre→post comparison and `pre_post_comparison.json` where required.

## Known blockers

- —

## Next recommended wave

- Next **DS-*** row from the information input list; claim **DS-ID + owner** before large changes.

## Contradictions / caveats

- Closure claims only with linked, versioned artefacts; missing old paths do not replace Git history or CI.
