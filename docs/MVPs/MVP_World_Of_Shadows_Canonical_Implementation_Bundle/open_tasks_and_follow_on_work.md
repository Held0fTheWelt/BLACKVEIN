# Open Tasks and Follow-on Work

## Remaining Obligations

- Byte-level conflicts for domains compared by `scripts/mvp_reconcile.py` are **cleared** (`conflicts=0`); keep the register current on future tree changes.
- Triage [`source_to_destination_mapping_table.md`](./source_to_destination_mapping_table.md): **`pending_verification`** at scale before `MVP/` retirement (see [`retirement_record.md`](./retirement_record.md)).
- Optionally triage [`forward_integration_candidates.md`](./forward_integration_candidates.md): distinguish **application/product** paths from **`'fy'-suites/`** repo tooling (canonical under the active repo) and from other **generated-only** paths before copying from `MVP/` into active. For **governed MVP bundle content** import (normalize + `docs/MVPs/imports/<id>` mirroring), prefer **`mvpify`** — [`'fy'-suites/mvpify/README.md`](../../../'fy'-suites/mvpify/README.md) — over ad-hoc bulk file copies.
- Resolve any runtime-proof claims still marked as target-only.
- Close transport and surface convergence gaps where user experience can drift.
- Keep evaluator independence and evidence discipline explicit for future acceptance expansions.

## Historical and Reference Preservation

- Audit, archive, and generated-evidence families from `MVP/docs/audit/`, `MVP/docs/archive/`, and related generated paths are preserved via mapping records.
- Runtime-generated payloads and governance-tool run artifacts are not canonical implementation docs, but remain traceable through inventory and mapping outputs.

## Deferred Items

- Any source path not yet marked verified in mapping output remains blocked for retirement closure.
- Any path classified as omitted remains subject to explicit justification review.
