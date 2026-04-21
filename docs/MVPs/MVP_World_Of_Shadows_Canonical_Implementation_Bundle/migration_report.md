# Migration Report

## Directly Migrated

- Canonical recomposed route materials from `MVP/docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/` were carried into this bundle as the primary source family for the implementation narrative.

## Merged Into Canonical Sections

- Core MVP companion files from `MVP/docs/MVPs/world_of_shadows_canonical_mvp/` were merged into:
  - `scope_and_goals.md`
  - `architecture_and_system_shape.md`
  - `content_and_experience_contract.md`
  - `implementation_sequence.md`
  - `acceptance_and_validation.md`
- Operational, developer, user, governance, and API/MCP families under `MVP/docs/` were merged by topic into the same canonical section set.

## Preserved as Reference

- Historical audit and archive families were preserved as reference-only context through mapping-table destinations and follow-on documentation.
- Runtime-generated evidence payloads and non-canonical operational artifacts were preserved as reference where useful for traceability.

## Omitted With Justification

- Cache, generated run outputs, backup artifacts, and non-canonical tool emissions were marked `OMIT_WITH_JUSTIFICATION` in `source_to_destination_mapping_table.md`.
- Omission rationale is explicitly stored per row (non-normative generated output, reproducible cache, or auxiliary artifact).

## Wording and Noise Removed

- Wave framing
- Re-audit/repair-track framing from canonical implementation sections
- Unexplained shorthand where not required
- Duplicated process commentary without implementation value

## 2026-04-21 automation pass

- Regenerated intake artifacts (`source_baseline_lock.txt`, manifest, `mvp_source_inventory.md`, `source_to_destination_mapping_table.md`) via `tools/mvp_reintegration_intake.py` against the current `MVP/` tree.
- Regenerated `reconciliation_report.md` and `integration_conflict_register.md` via `scripts/mvp_reconcile.py` (portable `--repo-root`).
- Refreshed `domain_validation_matrix.md`, `verification_record.md`, `retirement_record.md`, and `navigation_update_record.md` to match observed gate state (conflicts and pytest env **pending**).
- Verified `copied_missing_files.txt` paths: all targets already present in the active tree (no additional file copies required in this pass).

## 2026-04-21 phase continuation (reconcile hygiene + verification)

- Tightened `scripts/mvp_reconcile.py` skip list: `node_modules/`, `instance/`, and `.coverage` files are excluded from byte comparison so the conflict register stays focused on merge-relevant sources.
- Re-ran `python scripts/mvp_reconcile.py --repo-root .` → **1684** reconciliation rows, **500** conflicts (down from 1686 / 502 after removing spurious artifact pairs).
- Recorded backend **smoke** verification (`python -m pytest backend/tests/test_app_init.py -q`) in `verification_record.md`; full `run_tests.py --suite backend --quick` remains a separate long-run obligation.
- No bulk content merges from `MVP/` into active runtime files in this pass (active tree remains authoritative per register policy).

## 2026-04-21 backend config reconciliation batch

**Decision:** keep **active** `backend/.env.example`, `backend/Dockerfile`, and `backend/pyproject.toml` as the shipped source of truth.

**Evidence:**

- `.env.example`: active tree documents `WOS_REPO_ROOT` / `WOS_CONTENT_MODULES_ROOT`, optional `DOCS_SITE_URL` / `OPENAPI_SPEC_PATH`, and expanded play-service vs Docker host guidance; MVP snapshot omitted those lines.
- `Dockerfile`: active image ships `docker-entrypoint.sh`, `docs/api/openapi.yaml`, and `content/modules` into the runtime image; MVP snapshot lacked those layers.
- `pyproject.toml`: active optional `test`/`dev` pins (for example `pytest-asyncio`) differ from MVP; active matches current backend test expectations.

**Action taken:** copied the three active files into `MVP/backend/` (snapshot refresh only), then re-ran `python scripts/mvp_reconcile.py --repo-root .` — conflict count dropped **500 → 497**; `REC-00003`, `REC-00007`, and `REC-00008` now report **identical** byte match.

**Validation:** `python -m pytest backend/tests/test_app_init.py -q` → **4 passed** after the snapshot sync (no edits under active `backend/` beyond prior state).

## 2026-04-21 backend README and requirements batch

**Decision:** keep **active** `backend/README.md`, `backend/requirements-dev.txt`, and `backend/requirements-test.txt`.

**Evidence:**

- `README.md`: active **Tests** section links to the supported invocation matrix in [`docs/dev/contributing.md`](../docs/dev/contributing.md#supported-test-invocation-matrix-m2); MVP snapshot used a shorter instruction line without that cross-link.
- `requirements-dev.txt` / `requirements-test.txt`: active pins `pytest-asyncio>=1.3,<2`, matching `backend/pyproject.toml` and current async test usage; MVP snapshots still had `pytest-asyncio>=0.21,<1`.

**Action taken:** copied the three active files into `MVP/backend/`, re-ran `python scripts/mvp_reconcile.py --repo-root .` and `tools/mvp_reintegration_intake.py` — conflict count **497 → 494** (open divergences only; no changes under active `backend/`).

## 2026-04-21 backend/docs markdown batch

**Decision:** keep **active** copies of the six divergent operator docs under `backend/docs/`.

**Files:** `AREA_ACCESS_CONTROL.md`, `DEMO_FALLBACK_GUIDE.md`, `DEMO_SCRIPTS.md`, `MVP_BOUNDARY.md`, `NEXT_CONTENT_WAVE.md`, `UI_USABILITY.md`.

**Action taken:** copied each from `backend/docs/` into `MVP/backend/docs/`, then `mvp_reconcile.py` + intake — conflict count **494 → 488** (active tree unchanged).

## 2026-04-21 full compared-domain snapshot alignment (autonomous pass)

**Goal:** clear all byte-level `CON-*` rows for domains compared by `scripts/mvp_reconcile.py` (`backend`, `world-engine`, `ai_stack`, `frontend`, `administration-tool`, `docs`) without editing the active tree.

**Tool:** [`scripts/mvp_sync_domain_snapshot_from_register.py`](../../../scripts/mvp_sync_domain_snapshot_from_register.py) — parses the current [`integration_conflict_register.md`](./integration_conflict_register.md), then for each unique `MVP/<domain>/…` row copies the paired active file into the MVP snapshot.

**Runs (unique paths synced per domain):**

| Domain | MVP prefix | Active prefix | Unique paths synced |
|--------|------------|-----------------|---------------------|
| backend | `MVP/backend/` | `backend/` | 190 |
| world-engine | `MVP/world-engine/` | `world-engine/` | 73 |
| ai_stack | `MVP/ai_stack/` | `ai_stack/` | 67 |
| frontend | `MVP/frontend/` | `frontend/` | 10 |
| administration-tool | `MVP/administration-tool/` | `administration-tool/` | 27 |
| docs | `MVP/docs/` | `docs/` | 121 |

**Follow-up (structural drift):** `MVP/backend/tests/test_game_service.py` had no counterpart at `backend/tests/test_game_service.py` (active test lives at `backend/tests/services/test_game_service.py`). Removed the legacy MVP path, created `MVP/backend/tests/services/test_game_service.py` from active, re-ran intake — **`source_file_list_sha256` changed** (see [`source_baseline_lock.txt`](./source_baseline_lock.txt)); file count remains **27890**.

**Outcome:** `python scripts/mvp_reconcile.py --repo-root .` reports **`conflicts=0`**; [`integration_conflict_register.md`](./integration_conflict_register.md) is empty of data rows (see **Current status** section emitted by the reconciler). [`reconciliation_report.md`](./reconciliation_report.md) has **no** `pending` reconciliation rows for compared domains after the game-service test path fix.

**`scripts/mvp_reconcile.py`:** when zero conflicts remain, the generated register now appends a short **Current status** note for handoff clarity.

## 2026-04-21 forward-integration candidate report

- **Tool:** [`scripts/mvp_forward_integration_candidates.py`](../../../scripts/mvp_forward_integration_candidates.py) — emits [`forward_integration_candidates.md`](./forward_integration_candidates.md) using the same `_destination_for` heuristics as intake.
- **Filter:** rows whose MVP or mapped destination path contains the nested artefact prefix `'fy'-suites/'fy'-suites/` are excluded from the candidate count.
- **Bundle README:** `README.md` in this folder links the report and states that **`'fy'-suites/`** at repo root is the **canonical home** for bundled migration/rules tooling (original intended for this repository), while the candidate list flags missing active paths vs the MVP snapshot.
- **`mvpify`:** for **governed migration of MVP bundle content** (normalize imports, mirror documentation under `docs/MVPs/imports/<id>`, coordinate follow-on fy suites), operators should prefer **`'fy'-suites/mvpify/`** over ad-hoc bulk copies — see [`'fy'-suites/mvpify/README.md`](../../../'fy'-suites/mvpify/README.md).
