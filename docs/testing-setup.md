# Testing Setup and Reproducible Validation Guide

This document explains how to install test dependencies, run tests, understand test profiles, and validate the repository in clean environments.

## Quick Start

### CRITICAL: Install Dependencies First

**Tests CANNOT run without installing dependencies.** This is the mandatory first step.

#### Automatic Setup (Recommended)

Run the setup script to install all dependencies automatically:

```bash
# macOS / Linux
./setup-test-environment.sh

# Windows
setup-test-environment.bat
```

This script will:
1. Run `python -m pip install -r backend/requirements-test.txt` from `backend/` (that file starts with `-r requirements.txt`, so **production + test** deps install together)
2. Verify that critical packages (flask, sqlalchemy, pytest, etc.) are installed
3. Report any missing packages

#### Manual Setup

If you prefer to install manually, run **one** of:

```bash
python -m pip install -r backend/requirements-test.txt
```

```bash
cd backend && python -m pip install -r requirements-test.txt
```

Or, for development (includes testing plus optional dev tools):

```bash
cd backend
pip install -r requirements-dev.txt
```

#### Verify Installation

To verify dependencies are installed:

```bash
python -c "import flask, sqlalchemy, flask_sqlalchemy, flask_migrate, flask_limiter, pytest, pytest_asyncio; print('All dependencies installed')"
```

If you see `ModuleNotFoundError`, dependencies are **not installed**. Re-run the setup script.

### Run Canonical Smoke Suite

To run a quick validation of core repository health:

```bash
# From repository root
python -m pytest tests/smoke/ -v --tb=short
```

Expected result: ~140 tests pass in <15 seconds.

### Run Backend Unit Tests

To run all backend tests with coverage:

```bash
cd backend
python -m pytest tests/ -v
```

## Test Profiles: What They Mean

The repository supports three explicit test execution profiles:

### 1. **testing_isolated** (Default Backend Tests)

**What it is:** Tests run against `TestingConfig` with an **in-memory SQLite database**, **no routing bootstrap**, and **CSRF disabled by default**.

**When to use:**
- Running unit tests for rapid development feedback
- Testing business logic in isolation
- CI/CD pipelines where database state must not leak between tests

**Configuration:**
- `SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"`
- `ROUTING_REGISTRY_BOOTSTRAP = False` (prevents process-global router contamination)
- `WTF_CSRF_ENABLED = False` (enabled separately for CSRF-specific tests)
- Fixed secrets (safe for CI)

**How to select:**
```bash
cd backend
pytest tests/ -v
```

**Fixtures available:**
- `app` — Flask app with in-memory DB, ready for testing
- `client` — Test client for the app
- `test_user` — Pre-created regular user (username: testuser, password: Testpass1)
- `auth_headers` — JWT headers for test_user
- `moderator_user`, `moderator_headers` — Moderator role
- `admin_user`, `admin_headers` — Admin role
- `super_admin_user`, `super_admin_headers` — Admin with level 100
- `runner` — Flask CLI runner for command testing

**Example test:**
```python
def test_example(app, test_user, auth_headers):
    with app.app_context():
        # Your test code
        pass
```

---

### 2. **testing_bootstrap_on** (Production-like Routing Tests)

**What it is:** Tests run with `ROUTING_REGISTRY_BOOTSTRAP = True`, simulating production-like routing initialization. Uses the same in-memory database and test fixtures, but enables routing registry bootstrap.

**When to use:**
- Validating Area 2 convergence and final closure gates
- Testing HTTP proofs that depend on routing initialization
- Verifying production-like configuration behavior

**Configuration:**
- `SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"`
- `ROUTING_REGISTRY_BOOTSTRAP = True` (enables routing initialization)
- `WTF_CSRF_ENABLED = False`
- Fixed secrets

**How to select:**
```python
# In your test, inject the bootstrap-on fixtures instead of regular ones:

def test_with_bootstrap(app_bootstrap_on, client_bootstrap_on, auth_headers_bootstrap_on):
    # Tests run with routing bootstrap enabled
    response = client_bootstrap_on.get("/api/v1/areas/convergence")
    assert response.status_code == 200
```

**Bootstrap-specific fixtures:**
- `app_bootstrap_on` — App with `ROUTING_REGISTRY_BOOTSTRAP = True`
- `client_bootstrap_on` — Client for bootstrap-on app
- `test_user_bootstrap` — Test user in bootstrap-on app's DB
- `auth_headers_bootstrap_on` — JWT for bootstrap-on test user

**Note:** Bootstrap-on tests have their own isolated database lifecycle, separate from regular `app` tests. Do not mix fixtures.

---

### 3. **testing_isolated_production_like** (Smoke Tests)

**What it is:** Production-like configuration (database file, bootstrap enabled, full initialization) for validation tests that simulate real deployment startup behavior.

**When to use:**
- Smoke testing: rapid checks that core services initialize
- Validating production configuration defaults
- Testing real database file operations (not in-memory)

**Configuration:**
- Uses production `Config` class (not `TestingConfig`)
- `ROUTING_REGISTRY_BOOTSTRAP = True` (default)
- Real database file (not in-memory)
- Fixtures from backend test suite imported

**How to select:**
```bash
# From repository root
python -m pytest tests/smoke/ -v
```

**Fixtures available:** All backend fixtures (test_user, auth_headers, etc.) are available via pytest plugin loading.

---

## Canonical Smoke Suite

A lightweight validation to catch major breakage quickly:

```bash
python -m pytest tests/smoke/ -v --tb=short
```

This runs ~140 tests covering:
- **Backend startup:** App creation, config, database connection
- **Engine startup:** World Engine dependencies and initialization
- **Content modules:** W0 and W1 contract validation, YAML structure

**Expected result:** All pass in ~10–15 seconds.

**What it validates:**
- Core Flask app starts without errors
- Database is connectable and has required tables
- Runtime routing bootstrap works (smoke profile)
- Content module YAML is valid and internally consistent
- Core API endpoints respond

**Not covered by smoke:** Area 2 dual-workstream closure gates (**G-A-01** … **G-A-07**, **G-B-01** … **G-B-07**) and the full `backend/tests/runtime` convergence suites — run those explicitly from `backend/` (see below).

---

## Area 2 dual-workstream validation (canonical)

Focused regression for **Workstream A** (practical convergence) and **Workstream B** (reproducibility). Gate tables: [`docs/architecture/area2_workstream_a_gates.md`](architecture/area2_workstream_a_gates.md), [`docs/architecture/area2_workstream_b_gates.md`](architecture/area2_workstream_b_gates.md). Combined report: [`docs/architecture/area2_dual_workstream_closure_report.md`](architecture/area2_dual_workstream_closure_report.md).

**Command surface (code):** [`backend/app/runtime/area2_validation_commands.py`](../backend/app/runtime/area2_validation_commands.py) — `AREA2_DUAL_CLOSURE_PYTEST_MODULES`, `area2_dual_closure_pytest_invocation()`.

**Prerequisites:** Install dependencies (`./setup-test-environment.sh`, `setup-test-environment.bat`, or `python -m pip install -r backend/requirements-test.txt`).

**Run from `backend/`** (required so `backend/pytest.ini` sets `pythonpath` and `testpaths`). Pass **`--no-cov`** because `pytest.ini` defaults include coverage `addopts`:

```bash
cd backend
python -m pytest tests/runtime/test_area2_workstream_a_closure_gates.py tests/runtime/test_area2_workstream_b_closure_gates.py tests/runtime/test_area2_task2_closure_gates.py tests/runtime/test_area2_convergence_gates.py tests/runtime/test_area2_final_closure_gates.py tests/runtime/test_cross_surface_operator_audit_contract.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_model_inventory_bootstrap.py -q --tb=short --no-cov
```

**G-B-01** startup profile determinism, **G-B-02** bootstrap reproducibility, **G-B-03** clean-environment validation, **G-B-04** dependency/setup explicitness, **G-B-05** test-profile stability, **G-B-06** validation-command reality, and **G-B-07** documentation truth are enforced in `backend/tests/runtime/test_area2_workstream_b_closure_gates.py`.

---

## Area 2 Task 4 full closure validation (canonical)

**Gates:** **G-T4-01** (E2E truth, three surfaces), **G-T4-02** (bootstrap validation), **G-T4-03** (cross-surface contract), **G-T4-04** (negative/degraded honesty), **G-T4-05** (drift resistance), **G-T4-06** (validation-command reality), **G-T4-07** (required proof-suite stability via subprocess), **G-T4-08** (documentation truth). Gate table: [`docs/architecture/area2_task4_closure_gates.md`](architecture/area2_task4_closure_gates.md). Closure report: [`docs/architecture/area2_validation_hardening_closure_report.md`](architecture/area2_validation_hardening_closure_report.md).

**Command surface (code):** [`backend/app/runtime/area2_validation_commands.py`](../backend/app/runtime/area2_validation_commands.py) — `AREA2_TASK4_FULL_CLOSURE_PYTEST_MODULES`, `area2_task4_full_closure_pytest_invocation()`.

**Working directory:** `backend/` (same as dual-workstream: `pytest.ini` `pythonpath` and `testpaths`).

**Module list (must match code, in order):** `tests/runtime/test_area2_workstream_a_closure_gates.py`, `tests/runtime/test_area2_workstream_b_closure_gates.py`, `tests/runtime/test_area2_task2_closure_gates.py`, `tests/runtime/test_area2_convergence_gates.py`, `tests/runtime/test_area2_final_closure_gates.py`, `tests/runtime/test_cross_surface_operator_audit_contract.py`, `tests/test_bootstrap_staged_runtime_integration.py`, `tests/runtime/test_model_inventory_bootstrap.py`, `tests/runtime/test_area2_task3_closure_gates.py`, `tests/runtime/test_runtime_task4_hardening.py`, `tests/runtime/test_task4_drift_resistance.py`, `tests/runtime/test_runtime_staged_orchestration.py`, `tests/runtime/test_runtime_ranking_closure_gates.py`, `tests/improvement/test_improvement_task2a_routing_negative.py`, `tests/runtime/test_ai_turn_executor.py::test_agent_orchestration_executes_real_separate_subagents_and_logs_trace`, `tests/runtime/test_area2_task4_closure_gates.py`.

```bash
cd backend
python -m pytest tests/runtime/test_area2_workstream_a_closure_gates.py tests/runtime/test_area2_workstream_b_closure_gates.py tests/runtime/test_area2_task2_closure_gates.py tests/runtime/test_area2_convergence_gates.py tests/runtime/test_area2_final_closure_gates.py tests/runtime/test_cross_surface_operator_audit_contract.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_model_inventory_bootstrap.py tests/runtime/test_area2_task3_closure_gates.py tests/runtime/test_runtime_task4_hardening.py tests/runtime/test_task4_drift_resistance.py tests/runtime/test_runtime_staged_orchestration.py tests/runtime/test_runtime_ranking_closure_gates.py tests/improvement/test_improvement_task2a_routing_negative.py tests/runtime/test_ai_turn_executor.py::test_agent_orchestration_executes_real_separate_subagents_and_logs_trace tests/runtime/test_area2_task4_closure_gates.py -q --tb=short --no-cov
```

---

## Running Broader Test Subsets

### All Backend Tests (with coverage)

```bash
cd backend
python -m pytest tests/ -v --cov=app --cov-report=html
```

This covers:
- Unit tests (fast, no external deps)
- Integration tests (DB, auth, API)
- Security tests (OWASP, input validation, authZ)
- Contract tests (API stability)
- E2E tests (full workflows)

### Fast Mode: Only Unit Tests

```bash
cd backend
python -m pytest tests/ -m unit -v
```

Skips integration and slow tests.

### Security-Specific Tests

```bash
cd backend
python -m pytest tests/ -m security -v
```

### Content Module Tests

```bash
python -m pytest tests/smoke/test_w0_contracts.py tests/smoke/test_w1_module.py -v
```

---

## Pytest Configuration Files

The repository uses pytest configuration in two places for consistency:

### `backend/pytest.ini`

Classic pytest INI format. Defines:
- `pythonpath`: Includes `.` and `..` for flexible import paths
- `testpaths`: `tests/` directory
- `markers`: Unit, integration, security, contract, e2e, persistence, slow
- `asyncio_mode`: strict (required for async test determinism)
- `addopts`: Verbose output, coverage, short tracebacks

### `backend/pyproject.toml`

Duplicate configuration in TOML format (for tools that prefer TOML). Includes pytest, coverage, and path settings.

Both files must stay in sync. If you modify one, update the other.

---

## Test Dependency Declarations

### `backend/requirements.txt`

Production dependencies only. Used by:
- Production deployments
- Test environments (as a base)
- Any environment that needs the app to run

### `backend/requirements-test.txt`

**Test dependencies explicitly declared** (first directive is `-r requirements.txt` in the same directory, so production deps install in one step).

Used for clean-environment testing (pick one):

```bash
# From repository root (recommended in CI and fresh clones)
python -m pip install -r backend/requirements-test.txt

# From backend/
cd backend && python -m pip install -r requirements-test.txt
```

You do **not** need a separate `pip install -r requirements.txt` when using `requirements-test.txt` — the file already includes it.

**Portable checks** (no Flask/app imports; only pytest required):

```bash
python -m pip install 'pytest>=7,<9'
python -m pytest tests/requirements_hygiene/ -q
```

Includes (among others):
- `flask>=3.0.6,<4` — explicit anchor for the Flask app under test (also in `requirements.txt` via `-r`)
- `pytest>=7.0,<9` — test runner
- `pytest-asyncio>=0.21,<1` — async test support (import-time requirement)
- `pytest-cov>=4.0,<6` — coverage measurement
- `pytest-timeout>=2.1` — timeout enforcement
- `anyio` — explicit async primitives for consistent clean installs
- `exceptiongroup` — Python 3.10 compatibility for pytest/async (environment marker)

**Does NOT include** dev-only tools like formatters, linters, type checkers.

### `backend/requirements-dev.txt`

Development dependencies (super-set of test requirements).

Used by developers:
```bash
pip install -r requirements-dev.txt
```

Includes:
- All of requirements.txt
- All test requirements (via requirements-test.txt)
- Optional dev tools (commented, can be uncommented)

---

## Environment-Sensitive Behavior

The following aspects may vary between environments and are **intentionally left configurable**:

### Database URI
- **Default:** SQLite file at `backend/instance/wos.db`
- **Override:** Set `DATABASE_URI` environment variable
- **Testing:** In-memory SQLite (set automatically by TestingConfig)

### Secrets (Development Only)
- **Production:** Requires `SECRET_KEY` and `JWT_SECRET_KEY` environment variables
- **Development:** Set `DEV_SECRETS_OK=1` to enable fallback secrets (NEVER in production)
- **Testing:** Fixed secrets in TestingConfig (safe for CI)

### CORS Origins
- **Default:** None (same-origin only)
- **Override:** Set `CORS_ORIGINS=http://localhost:3000,https://example.com`

### Email Configuration
- **Default:** Disabled (`MAIL_ENABLED=0`)
- **Override:** Set `MAIL_ENABLED=1`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`

### Routing Bootstrap
- **Production:** Enabled by default (`ROUTING_REGISTRY_BOOTSTRAP=True` in Config)
- **Unit tests:** Disabled (`ROUTING_REGISTRY_BOOTSTRAP=False` in TestingConfig) to avoid cross-test contamination
- **Smoke tests:** Enabled (production-like behavior)
- **Bootstrap tests:** Use `app_bootstrap_on` fixture to override

---

## Clean-Environment Validation (for CI/CD)

To validate that the repository can be tested in a fresh environment:

1. **Install dependencies:**
   ```bash
   python -m pip install --no-cache-dir -r backend/requirements-test.txt
   ```

2. **Run canonical smoke suite:**
   ```bash
   python -m pytest tests/smoke/ -v --tb=short
   ```

3. **Run broader test suite:**
   ```bash
   cd backend
   python -m pytest tests/ -v --tb=short
   ```

For Area 2 operational closure, also run the **Area 2 dual-workstream** command from the [`Area 2 dual-workstream validation (canonical)`](#area-2-dual-workstream-validation-canonical) section (same install prerequisites; **`cd backend`** and **`--no-cov`**).

If smoke and backend suites pass, the environment is valid for those scopes. If tests fail, check:
- All required packages are in requirements files
- PYTHONPATH is correctly set (`backend/pytest.ini` handles this when cwd is `backend/`)
- Database is readable/writable (if using file-based SQLite)
- No local environment assumptions are leaked

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'app.database'"
- This is a fixed import error in the repository. Use `from app.extensions import db` instead.
- Smoke tests have been updated to use the correct import.

### "fixture 'auth_headers' not found"
- Ensure pytest loads plugins correctly. Smoke tests import backend fixtures via `pytest_plugins`.
- If running a custom test outside smoke/backend, add this to your conftest:
  ```python
  pytest_plugins = ['backend.tests.conftest']
  ```

### "ROUTING_REGISTRY_BOOTSTRAP is not set" or "RuntimeError: working outside of application context"
- Use the correct fixture for your profile:
  - `app` for isolated tests
  - `app_bootstrap_on` for bootstrap tests
  - Ensure you're inside the app context when accessing app globals

### Tests run slowly
- Run only unit tests: `pytest tests/ -m unit`
- Skip slow tests: `pytest tests/ -m "not slow"`
- Use pytest-xvs for early exit on failure: `pytest tests/ -xvs`

### Database errors or "table does not exist"
- The test fixtures automatically create all tables. If you see this:
  1. Ensure the `app` fixture is used (it calls `db.create_all()`)
  2. Check that migrations are properly applied (if using a real DB)
  3. Verify `SQLALCHEMY_DATABASE_URI` is set correctly in TestingConfig

---

## Glossary

**testing_isolated:** Default profile; uses in-memory DB, no routing bootstrap, CSRF disabled. For unit tests.

**testing_bootstrap_on:** Production-like routing with in-memory DB and test fixtures. For area-specific tests.

**testing_isolated_production_like:** Full production config (real DB file, bootstrap, etc.). For smoke tests.

**ROUTING_REGISTRY_BOOTSTRAP:** When true, initializes the global routing registry at startup. Must be false in isolated unit tests to prevent cross-test contamination.

**Smoke test:** Lightweight, quick test of core functionality (not heavy integration testing). Validates startup, basic health, and key paths.

**Fixture:** Pytest fixture; a reusable test setup (e.g., `app`, `test_user`, `auth_headers`). Defined in conftest.py.

**Profile:** A named test configuration (e.g., testing_isolated, testing_bootstrap_on). Determines what config class is used and what fixtures are available.

