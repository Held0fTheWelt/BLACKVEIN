# Testing guide — World of Shadows

This document describes how to run the **multi-component** test suites from the repository `tests/` directory. Tests live in **four separate trees** (not merged):

| Component | Directory |
|-----------|-----------|
| Backend | `backend/tests/` |
| Administration tool | `administration-tool/tests/` |
| World engine | `world-engine/tests/` |
| Database | `database/tests/` |

The root `tests/` folder holds the **orchestrator** (`run_tests.py`), smoke tests (`tests/smoke/`), and this file. It does **not** replace the component `tests/` roots.

---

## Quick start

From the `tests/` directory (repository root: `WorldOfShadows/tests/`):

```bash
cd tests
python run_tests.py
```

Cross-platform; use `python3` on Linux/macOS if needed.

---

## `run_tests.py` — options

| Option | Meaning |
|--------|---------|
| `--suite backend` | Run only the backend test tree (`cd backend && pytest …`). |
| `--suite administration` | Administration tool only. |
| `--suite engine` | World engine only. |
| `--suite database` | Database only. |
| `--suite backend database` | Run those two components in sequence. |
| `--suite all` | All four components (default if `--suite` is omitted). |
| `--quick` | No coverage; `-x` (stop on first failure). |
| `--coverage` | Extra HTML coverage report (`term-missing:skip-covered` + `html`). |
| `--verbose` | `-vv`, long tracebacks, `-s`. |
| `--scope …` | **Backend only:** filter by pytest marker (see below). |

### Backend scope (`--scope`)

Applies **only** when the backend suite is included. Other components always run their **full** `tests/` tree for that run.

| `--scope` value | Pytest filter |
|-----------------|---------------|
| `all` (default) | No marker filter. |
| `contracts` | `-m contract` |
| `integration` | `-m integration` |
| `e2e` | `-m e2e` |
| `security` | `-m security` |

Examples:

```bash
python run_tests.py --suite backend --scope contracts
python run_tests.py --suite all --quick
```

Marker definitions for the backend are in `backend/pytest.ini`.

---

## Coverage thresholds

- **Backend:** `run_tests.py` uses `--cov-fail-under=85` when running the backend suite, matching `backend/pytest.ini`.
- **Other components:** default fail-under is **80** in this runner (adjust in `run_tests.py` if you align their `pytest.ini`).

---

## Makefile (optional)

From `tests/`:

| Target | Command |
|--------|---------|
| `make test` | `python3 run_tests.py` |
| `make test-quick` | `python3 run_tests.py --quick` |
| `make test-coverage` | `python3 run_tests.py --coverage` |
| `make test-contracts` | `python3 run_tests.py --suite backend --scope contracts` |

Run `make help` after syncing the Makefile with this file.

---

## JUnit reports

`run_tests.py` writes JUnit XML under `tests/reports/` (`pytest_<component>_YYYYMMDD_HHMMSS.xml`).

---

## Running pytest manually (single component)

Always set the working directory to the component that owns the code under test:

```bash
cd backend
python -m pytest tests -v
```

Use markers as needed:

```bash
cd backend
python -m pytest tests -m security -v
```

---

## Backend test layout (overview)

The backend tree already uses meaningful subfolders, for example:

- `backend/tests/content/` — content modules
- `backend/tests/runtime/` — runtime engine tests

Large flat files may be split over time; prefer **descriptive file names** (what behavior is under test), not internal release codenames.

---

## CI example

```yaml
- run: pip install -r backend/requirements-dev.txt
- run: cd tests && python run_tests.py --suite backend --quick
```

For a full multi-component run in CI, install dependencies for each component as required, then `cd tests && python run_tests.py`.

---

## References

- [pytest](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
