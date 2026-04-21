# domain_validation_matrix

Commands below are **recorded** for the touched destination domains. Run them from the **repository root** after `setup-test-environment.*` (or equivalent per-suite installs); see [`tests/TESTING.md`](../../../tests/TESTING.md) and [`tests/run_tests.py`](../../../tests/run_tests.py).

| destination domain | migrated source inputs | affected destination paths | required validation commands | expected evidence type | resulting status |
|---|---|---|---|---|---|
| backend | `MVP/backend/**` | `backend/` | `python tests/run_tests.py --suite backend` (optional `--quick`); smoke: `python -m pytest backend/tests/test_app_init.py -q` | unit / integration | **partial** — smoke subset **pass** (2026-04-21, 4 tests); full `--quick` suite not run to completion in-session |
| world-engine | `MVP/world-engine/**` | `world-engine/` | `python tests/run_tests.py --suite engine` | unit / integration | **partial** — smoke from `world-engine/`: `python -m pytest tests/test_api.py -q` → **4 passed** (2026-04-21, 1 deprecation warning); full `run_tests.py --suite engine` not run to completion in-session |
| ai_stack | `MVP/ai_stack/**` | `ai_stack/` | `python tests/run_tests.py --suite ai_stack` | unit / integration | **pending** — same |
| frontend | `MVP/frontend/**` | `frontend/` | `python tests/run_tests.py --suite frontend` | unit / integration | **pending** — same |
| administration-tool | `MVP/administration-tool/**` | `administration-tool/` | `python tests/run_tests.py --suite administration` | unit / integration | **pending** — same |
| canonical docs | `MVP/docs/**` (merged by topic) | `docs/`, `docs/MVPs/` | Manual consistency: `docs/README.md`, `docs/INDEX.md`, `docs/MVPs/README.md` link to [`MVP_World_Of_Shadows_Canonical_Implementation_Bundle/README.md`](./README.md) not to raw `MVP/` paths | doc consistency / navigation | **pass** — entrypoints verified 2026-04-21 |

## Notes

- Byte-level reconciliation for `backend`, `world-engine`, `ai_stack`, `frontend`, `administration-tool`, and `docs` is captured in [`reconciliation_report.md`](./reconciliation_report.md) and [`integration_conflict_register.md`](./integration_conflict_register.md). As of 2026-04-21 autonomous alignment, **`mvp_reconcile.py` reports 0 conflicts** among those domains (MVP snapshot refreshed from active per [`migration_report.md`](./migration_report.md)).
- Runtime suites must be re-run in a CI or local venv with test dependencies installed; replace **pending** / **partial** with pass/fail plus log paths when executed.
