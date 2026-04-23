# Testing guide — World of Shadows

This document describes how to run the consolidated test suites using the orchestrator [`run_tests.py`](run_tests.py) in this directory. Pytest trees live across multiple repository areas; the runner exposes component suites and root `tests/*` suite groups in one canonical entrypoint.

The root `tests/` folder holds the **orchestrator** (`run_tests.py`), smoke assets (`tests/smoke/`), reports (`tests/reports/`), and this file. It does **not** replace each component’s own `tests/` root.

---

## Quick start

**First-time / fresh clone (installs all Python deps for `--suite all`):** from the repository root, run one of:

- **Linux / macOS / Git Bash:** `./setup-test-environment.sh` or `./scripts/install-full-test-env.sh` (same behavior)
- **Windows (cmd):** `setup-test-environment.bat` or `scripts\install-full-test-env.bat`
- **Windows (PowerShell):** `.\scripts\install-full-test-env.ps1`

That installs `backend/requirements-dev.txt`, `frontend/requirements-dev.txt`, `administration-tool/requirements-dev.txt`, `world-engine/requirements-dev.txt`, plus editable `story_runtime_core` and `ai_stack[test]`, and verifies the LangGraph export surface (`RuntimeTurnGraphExecutor`) expected by the **engine** and **ai_stack** suites. For **ai_stack tests only**, use `scripts/install-ai-stack-test-env.sh` (or `.ps1` / `.bat`) — smaller install.

### Automated setup — security and hygiene

The official setup entry points (`setup-test-environment.*`, `scripts/install-full-test-env.*`) are intended for **trusted checkout trees** and CI:

- **Local requirement files only** — installs use `pip install -r` against paths under this repository (no remote pipe-to-shell installers).
- **`python -m pip`** — reduces accidental use of a different `pip` on `PATH` (see scripts’ comments; G-B-03 asserts this for the shell setup).
- **World Engine pytest** forces a known non-production internal API key in `world-engine/tests/conftest.py` so automated runs do not depend on operator `.env` secrets for internal-route tests (do not reuse that value in production).

From the **repository root** (recommended):

```bash
python tests/run_tests.py
```

Or from `tests/`:

```bash
cd tests
python run_tests.py
```

Cross-platform; use `python3` on Linux/macOS if needed.

---

## Canonical `--suite` list

| CLI name | Working directory | Pytest path | Notes |
|----------|-------------------|-------------|--------|
| `backend` | `backend/` | `tests` | Collects entire `backend/tests/`, including `writers_room/` and `improvement/` subtrees. |
| `frontend` | `frontend/` | `tests` | Player/public Flask UI tests. |
| `administration` | `administration-tool/` | `tests` | Admin proxy and UI tests. |
| `engine` | `world-engine/` | `tests` | FastAPI runtime, HTTP/WS. |
| `database` | `database/` | `tests` | Schema/migration tests (often import `backend/app` models). |
| `writers_room` | `backend/` | `tests/writers_room` | **Slice** run: Writers-Room tests only (also collected under full `backend`). |
| `improvement` | `backend/` | `tests/improvement` | **Slice** run: improvement-loop tests only. |
| `ai_stack` | **repo root** | `ai_stack/tests` | Requires `PYTHONPATH` including repo root (runner sets this). |
| `root_core` | **repo root** | `tests/test_agency_capability_matrix_truth.py` | Root canonical truth contract test. |
| `root_integration` | **repo root** | `tests/integration` | Root integration checks. |
| `root_branching` | **repo root** | `tests/branching` | Branching behavior checks. |
| `root_smoke` | **repo root** | `tests/smoke` | Repository smoke checks. |
| `root_tools` | **repo root** | `tests/tools` | Tooling tests. |
| `root_requirements_hygiene` | **repo root** | `tests/requirements_hygiene` | Requirements and dependency hygiene checks. |
| `root_e2e_python` | **repo root** | `tests/e2e` | Python end-to-end verification files. |
| `root_experience_scoring` | **repo root** | `tests/experience_scoring_cli` | Experience scoring command tests. |

---

## `--suite all` semantics

`--suite all` (or default `--suite` omitted) runs all Python suite groups in deterministic order:

1. `backend`  
2. `frontend`  
3. `administration`  
4. `engine`  
5. `database`  
6. `ai_stack`  
7. `root_core`  
8. `root_integration`  
9. `root_branching`  
10. `root_smoke`  
11. `root_tools`  
12. `root_requirements_hygiene`  
13. `root_e2e_python`  
14. `root_experience_scoring`  

`writers_room` and `improvement` remain available as dedicated slices for focused execution, but are already covered under full backend collection.

To run **only** Writers-Room or improvement tests (e.g. focused coverage):

```bash
python tests/run_tests.py --suite writers_room
python tests/run_tests.py --suite improvement
```

---

## `--scope` (pytest marker filter)

`--scope` maps to `pytest -m <marker>` **only** for suites that define the markers in their `pytest.ini` / `pyproject.toml`.

| Suite | `contracts` | `integration` | `e2e` | `security` |
|-------|-------------|-----------------|-------|-------------|
| `backend` | `-m contract` | `-m integration` | `-m e2e` | `-m security` |
| `writers_room` | same | same | same | same |
| `improvement` | same | same | same | same |
| `administration` | `-m contract` | `-m integration` | **full suite** (no `e2e` marker) | `-m security` |
| `engine` | `-m contract` | `-m integration` | **full suite** (no `e2e` marker) | `-m security` |
| `frontend` | **ignored** — always full suite | | | |
| `database` | **ignored** — always full suite | | | |
| `ai_stack` | **ignored** — always full suite | | | |
| `root_*` suites | **ignored** — always full suite | | | |

When scope is set but not applied, the runner prints an `[INFO]` line (see `run_tests.py`).

---

## `--quick`, `--stats`, `--continue-on-failure`

| Flag | Effect |
|------|--------|
| `--quick` | Each suite: `pytest --no-cov -x` (stop on first **test** failure in that suite). **Skips** the pre-run `pytest --collect-only` stats pass (unless `--stats`). **Stops the orchestrator** after the first **suite** that fails (unless `--continue-on-failure`). |
| `--stats` | With `--quick`, still run the collect-only stats pass first. |
| `--continue-on-failure` | With `--quick`, run all selected suites even if one fails. |

Without `--quick`, the runner always runs collect-only first; a non-zero collection exit code **fails the whole run** before pytest executes.

---

## Coverage (`pytest-cov`) per suite

Behavior is implemented in [`run_tests.py`](run_tests.py) (`_cov_sources_for_suite`, `_cov_fail_under_for_suite`, `build_pytest_argv`).

| Suite | `--cov=` roots (each passed as its own flag) | `--cov-fail-under` |
|-------|-----------------------------------------------|---------------------|
| `backend` | `backend/app` | 85 |
| `frontend` | `frontend/app` | 92 |
| `writers_room` | `backend/app` | 50 |
| `improvement` | `backend/app` | 50 |
| `administration` | `--cov=.` + `administration-tool/.coveragerc` (flat tree; tests omitted) | 80 |
| `engine` | `world-engine/app` (path) | 80 |
| `database` | `backend/app` | *(none — instrumentation only; see semantics doc)* |
| `ai_stack` | `ai_stack/` (repo path) | 80 |

- **Default** (no `--coverage`, no `--verbose`): `-v --tb=short`, term-missing report, fail-under as above.  
- **`--coverage`**: adds HTML report and `term-missing:skip-covered`.  
- **`--verbose`**: `-vv --tb=long -s` plus same cov flags as default.  
- **`--quick`**: **no** coverage flags for pytest (`--no-cov`).

**Semantics:** coverage measures **in-process** Python lines touched by tests. It does **not** measure production realism (real network, browser, DB load, or LLM variability). See [`docs/testing/COVERAGE_SEMANTICS.md`](../docs/testing/COVERAGE_SEMANTICS.md).

---

## `run_tests.py` — option summary

| Option | Meaning |
|--------|---------|
| `--suite …` | One or more suite names, or `all` (see above). |
| `--scope …` | Marker filter where supported (see matrix). |
| `--with-playwright` | Add Playwright lane (`tests/e2e`, external toolchain). |
| `--with-compose-smoke` | Add compose-smoke lane (`tests/smoke/compose_smoke`). |
| `--quick` | Fast fail; see table above. |
| `--stats` | Force collect-only with `--quick`. |
| `--continue-on-failure` | Run all suites with `--quick` even after a failure. |
| `--coverage` | HTML + stricter cov reporting. |
| `--verbose` | Verbose pytest + long tracebacks. |

---

## Makefile (optional)

From `tests/`:

| Target | Command |
|--------|---------|
| `make test` | `python3 run_tests.py` |
| `make test-quick` | `python3 run_tests.py --quick` |
| `make test-coverage` | `python3 run_tests.py --coverage` |
| `make test-contracts` | `python3 run_tests.py --suite backend --scope contracts` |
| `make test-integration` | `python3 run_tests.py --suite backend --scope integration` |

---

## JUnit reports

`run_tests.py` writes JUnit XML under `tests/reports/` (`pytest_<suite>_YYYYMMDD_HHMMSS.xml`).

---

## Running pytest manually (single component)

Always set the working directory to the component that owns the code under test:

```bash
cd backend
python -m pytest tests -v
```

---

## Optional: Compose smoke lane

For a **production-narrow** path (real HTTP/WS, services up), see [`smoke/compose_smoke/README.md`](smoke/compose_smoke/README.md).

---

## Optional: Browser E2E (Playwright lane)

Critical UI flows (login, play shell) are scaffolded under [`e2e/`](e2e/README.md) (`@playwright/test`). Use `python tests/run_tests.py --suite all --with-playwright` to include this lane.

---

## CI example

```yaml
- run: pip install -r backend/requirements-dev.txt
- run: python tests/run_tests.py --suite backend --quick
```

Install dependencies per component before `python tests/run_tests.py --suite all`.

---

## Environment preflight

Before running pytest, `run_tests.py` calls `check_environment()` and runs **import probes per selected suite** so automated runs fail fast with install hints instead of mid-suite `ModuleNotFoundError`:

- **backend**, **writers_room**, **improvement**, **database** — Flask stack under `backend/` (same imports as `backend/tests/conftest.py`). If `ai_stack.langgraph_runtime` is not importable, an **informational** line suggests `pip install -e "./ai_stack[test]"` for tests that touch the graph.
- **frontend** — `flask`, `requests` with `cwd=frontend/` (`frontend/requirements-dev.txt`).
- **administration** — `flask`, `werkzeug` with `cwd=administration-tool/`.
- **engine** — FastAPI / SQLAlchemy / HTTPX for the engine app, then **LangChain / LangGraph** plus `from ai_stack import RuntimeTurnGraphExecutor` with repo root on `PYTHONPATH` (same bar as `.github/workflows/engine-tests.yml`).
- **ai_stack** — editable `story_runtime_core` + `ai_stack` resolvable from repo root, then the **same LangGraph lane** probe as engine (`langchain_core`, `langgraph`, export flag).

For **full** orchestrator parity (including `engine` + `ai_stack` graph lane), use `setup-test-environment.sh` / `setup-test-environment.bat` or `scripts/install-full-test-env.*` (see Quick start above). For AI-stack-only work, use `scripts/install-ai-stack-test-env.sh` (Linux/macOS) or `pip install -r ai_stack/requirements-test.txt` with editable installs per `ai_stack/requirements-test.txt` header comments.

---

## References

- [pytest](https://docs.pytest.org/)
- [Coverage.py](https://coverage.readthedocs.io/)
