# domain_validation_matrix

Commands below are **recorded** for the touched destination domains. Run them from the **repository root** after `setup-test-environment.*` (or equivalent per-suite installs); see [`tests/TESTING.md`](../../../tests/TESTING.md) and [`tests/run_tests.py`](../../../tests/run_tests.py).

| destination domain | migrated source inputs | affected destination paths | required validation commands | expected evidence type | resulting status |
|---|---|---|---|---|---|
| backend | `MVP/backend/**` | `backend/` | `python tests/run_tests.py --suite backend` (optional `--quick`); smoke: `python -m pytest backend/tests/test_app_init.py -q` | unit / integration | **partial / user-skipped** — smoke subset **pass** (2026-04-21, 4 tests); `env PYTEST_ADDOPTS=-s python tests/run_tests.py --suite backend --quick` collected **4363** tests and ran with sustained passing output, then was stopped at user request due delay; no full-suite pass recorded |
| world-engine | `MVP/world-engine/**` | `world-engine/` | `python tests/run_tests.py --suite engine` | unit / integration | **pass** — `env PYTEST_ADDOPTS=-s python tests/run_tests.py --suite engine --quick` → **922 passed** in 1096.04s; XML: `tests/reports/pytest_engine_20260421_175439.xml` |
| ai_stack | `MVP/ai_stack/**` | `ai_stack/` | `python tests/run_tests.py --suite ai_stack` | unit / integration | **pass after compatibility fix** — initial Python 3.10 failure from `datetime.UTC` import (`tests/reports/pytest_ai_stack_20260421_181228.xml`), fixed in active `ai_stack`; rerun `env PYTEST_ADDOPTS=-s python tests/run_tests.py --suite ai_stack --quick` → **947 passed, 1 skipped** in 204.72s; XML: `tests/reports/pytest_ai_stack_20260421_181448.xml` |
| frontend | `MVP/frontend/**` | `frontend/` | `python tests/run_tests.py --suite frontend` | unit / integration | **pass** — `env PYTEST_ADDOPTS=-s python tests/run_tests.py --suite frontend --quick` → **76 passed** in 0.97s; XML: `tests/reports/pytest_frontend_20260421_175233.xml` |
| administration-tool | `MVP/administration-tool/**` | `administration-tool/` | `python tests/run_tests.py --suite administration` | unit / integration | **pass** — `env PYTEST_ADDOPTS=-s python tests/run_tests.py --suite administration --quick` → **1149 passed** in 35.31s; XML: `tests/reports/pytest_administration_20260421_175318.xml` |
| canonical docs | `MVP/docs/**` (merged by topic) | `docs/`, `docs/MVPs/` | Manual consistency: `docs/README.md`, `docs/INDEX.md`, `docs/MVPs/README.md` link to [`MVP_World_Of_Shadows_Canonical_Implementation_Bundle/README.md`](./README.md) not to raw `MVP/` paths | doc consistency / navigation | **pass** — entrypoints verified 2026-04-21 |

## Notes

- Byte-level reconciliation for `backend`, `world-engine`, `ai_stack`, `frontend`, `administration-tool`, and `docs` is captured in [`reconciliation_report.md`](./reconciliation_report.md) and [`integration_conflict_register.md`](./integration_conflict_register.md). As of 2026-04-21 autonomous alignment, **`mvp_reconcile.py` reports 0 conflicts** among those domains (MVP snapshot refreshed from active per [`migration_report.md`](./migration_report.md)).
- Runtime matrix is now complete for `world-engine`, `ai_stack`, `frontend`, `administration-tool`, and canonical docs. `backend` remains partial by explicit user direction to skip the delayed full run.
