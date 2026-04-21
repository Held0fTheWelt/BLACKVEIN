# Mapping Closure Decisions

Generated during the Full MVP Re-Integration continuation on 2026-04-21.

This record interprets the remaining non-`verified_*` rows from [`mapping_verification_report.md`](./mapping_verification_report.md). It does not delete `MVP/`, does not authorize blind copying, and does not replace backend validation or explicit retirement sign-off.

## Current Mechanical State

| category | rows | decision posture |
|---|---:|---|
| Mechanically verified rows | 20,047 | Closed by filesystem evidence (`verified_*`) |
| Remaining follow-up rows | 7,843 | Closed only by the class decisions below plus explicit sign-off |
| `blocked_missing_active_target` | 7,755 | Not automatically copied; routed by triage bucket |
| `needs_reconcile_bytes` | 88 | Not automatically overwritten; routed by triage bucket |

## Class Decisions

| triage bucket | rows | closure decision | rationale |
|---|---:|---|---|
| `generated_output` | 5,480 | Treat as generated/report output; no active runtime migration by default. | Generated reports, generated consolidations, package metadata, and similar outputs are reproducible or historical artifacts, not authoritative runtime source. |
| `nested_repo_snapshot` | 1,360 | Treat as nested snapshot evidence; do not create active `repo/` subtree. | The active repository root is already authoritative; recreating a nested `repo/` tree would duplicate state and confuse ownership. |
| `runtime_state_or_database` | 431 | Treat as runtime state/local database evidence; do not migrate as source. | Run outputs, local DBs, `var/`, `instance/`, and runtime state are not stable source assets. |
| `legacy_mvp_reference` | 191 | Treat as canonical-doc/reference material; do not create new root `mvp/` or `governance/` runtime trees. | The canonical bundle and companion MVP docs are the active route for this material. Raw legacy paths stay reference-only unless explicitly re-targeted. |
| `validation_evidence` | 128 | Treat as historical evidence; preserve through canonical records when useful. | Raw validation logs are evidence, not executable source. |
| `nested_suite_snapshot` | 1 | Treat as duplicate nested suite snapshot; omit or preserve only as reference. | The path represents duplicate nested suite material. |
| `source_or_config` | 42 | Real active reconciliation candidates remain. | These rows target active repo source/config/test paths and need direct review before closure. |
| `fy_source_or_docs` | 210 | Real fy suite reconciliation candidates remain. | These rows target repo-local fy tooling/docs and should be reviewed with the mvpify/fy-suite ownership model. |

## Prioritized Remaining Work

The remaining first-pass reconciliation queue is **252** rows:

- **42** active source/config rows
- **210** fy suite source/docs rows

The active source/config queue is intentionally small after triage. It includes repository setup files, targeted scripts/tests, `story_runtime_core`, `tools/mcp_server`, and a few Postman/setup surfaces. Diffs sampled during continuation showed several active files are newer or more complete than the MVP copy, so active content must remain authoritative unless a specific missing requirement is proven from evidence.

## Retirement Interpretation

`MVP/` is **not cleared for deletion** by this record alone.

Deletion remains blocked until:

- backend validation is either completed or explicitly waived;
- the 252 prioritized source/config and fy suite rows receive reviewed decisions;
- generated/runtime/evidence/legacy-reference class decisions receive explicit sign-off as acceptable no-loss treatment;
- [`retirement_record.md`](./retirement_record.md) is updated with that sign-off immediately before any destructive action.

