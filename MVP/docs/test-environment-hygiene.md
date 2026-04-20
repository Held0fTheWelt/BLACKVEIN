# Test Environment Hygiene and Reproducibility

This document explains how the repository reduces accidental local environment leakage and ensures tests are deterministic and reproducible.

## Problem: Why Environment Hygiene Matters

Without careful hygiene, tests can fail mysteriously in clean environments:
- "Works on my machine" syndrome
- CI/CD pipelines report false failures
- Developers waste time troubleshooting local vs. environment issues
- Hidden dependencies make onboarding slower

This repository addresses these issues systematically.

## Solution: Explicit Dependency and Configuration Management

### 1. Explicit Test Dependencies (No Hidden Imports)

**Files:** `backend/requirements-test.txt`

All packages needed for import-time test execution are declared explicitly:

```
pytest>=7.0,<9          # Core test runner
pytest-asyncio>=0.21,<1 # Required for async tests (import-time)
pytest-cov>=4.0,<6      # Coverage measurement
pytest-timeout>=2.1     # Timeout enforcement
anyio>=4.0,<5           # Explicit async primitives (clean installs)
```

**Why this matters:**
- `pytest-asyncio` is **import-time critical**: If a test file imports async fixtures, pytest fails to load the test without this plugin.
- Without explicit declaration, tests work locally (plugin installed via IDE setup) but fail in CI.
- `requirements-test.txt` makes dependencies auditable and clean-environment-reproducible.

**How to validate (no backend install):**
```bash
# From repository root — only checks that -r chains resolve on disk
python -m pip install 'pytest>=7,<9'
python -m pytest tests/requirements_hygiene/ -q
```

**How to validate (full backend test env):**
```bash
python -m venv clean_env
source clean_env/bin/activate  # Windows: clean_env\Scripts\activate
python -m pip install -r backend/requirements-test.txt
cd backend && pytest tests/ -q
```

### 2. Deterministic Pytest Configuration (No IDE Magic)

**Files:** `backend/pytest.ini`, `backend/pyproject.toml`

Pytest behavior is explicitly configured, not inferred from IDE settings:

```ini
[pytest]
pythonpath = . ..                  # Explicit import roots
testpaths = tests                  # Where to look for tests
python_files = test_*.py           # File naming convention
python_functions = test_*          # Function naming convention
asyncio_mode = strict              # Async determinism
```

**Why this matters:**
- Without explicit pythonpath, IDE configurations can differ from CI
- `asyncio_mode = strict` forces explicit await/async declarations (prevents subtle async bugs)
- Explicit testpaths prevent accidental test discovery of unrelated files

**How to validate:**
```bash
# Confirm pytest finds the right tests
pytest --collect-only tests/ | head -20

# Confirm pytest uses the right config
pytest --version && pytest -c backend/pytest.ini --co tests/ | wc -l
```

### 3. Test Fixtures with Safe Defaults (No Assumption Leakage)

**Files:** `backend/tests/conftest.py`

All fixtures provide safe, isolated defaults:

#### Database Isolation
```python
@pytest.fixture
def app():
    """Application with testing config and in-memory DB."""
    application = create_app(TestingConfig)
    # In-memory DB — no local DB state leaks between tests
    db.create_all()
    ensure_roles_seeded()
    ensure_areas_seeded()
    yield application
    # Cleanup after test
    db.drop_all()
    db.session.remove()
```

**Guarantees:**
- Each test gets a fresh in-memory database
- No test affects another test's database state
- No disk I/O (fast tests, safe for CI)

#### Rate Limiter Reset
```python
@pytest.fixture(autouse=True)
def clear_rate_limiter():
    """Clear rate limiter state before each test."""
    try:
        if hasattr(limiter, '_storage') and limiter._storage is not None:
            limiter.reset()
    except Exception:
        pass
    yield
    # Clean up after test
    limiter.reset()
```

**Guarantees:**
- Rate limiter state doesn't leak between tests
- Tests can safely call rate-limited endpoints repeatedly
- No need to configure rate limiter storage in tests

#### Role and Area Seeding
```python
db.create_all()
ensure_roles_seeded()     # Always seed required roles
ensure_areas_seeded()     # Always seed required areas
```

**Guarantees:**
- Tests never fail due to missing roles or areas
- Consistent test data across all test runs
- Safe to write tests assuming User, Admin, Moderator roles exist

### 4. Configuration Profiles (No "Works on My Machine")

**Files:** `backend/app/config.py`

Three configuration classes handle different test scenarios:

#### TestingConfig (Default, Isolated)
```python
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret-key"
    ROUTING_REGISTRY_BOOTSTRAP = False  # ← Prevent cross-test pollution
    WTF_CSRF_ENABLED = False
```

Guarantees:
- In-memory DB (fast, isolated)
- Routing registry isolated (no cross-test contamination)
- CSRF disabled for regular tests (enabled separately for CSRF tests)

#### TestingConfigWithRoutingBootstrap
```python
class TestingConfigWithRoutingBootstrap(TestingConfig):
    ROUTING_REGISTRY_BOOTSTRAP = True  # ← Enable routing for bootstrap tests
```

Guarantees:
- Tests can validate routing initialization behavior
- Still uses in-memory DB (fast)
- Can be mixed with regular tests safely (separate fixtures)

#### TestingConfigWithCSRF
```python
class TestingConfigWithCSRF(TestingConfig):
    WTF_CSRF_ENABLED = True  # ← Test CSRF protection explicitly
```

Guarantees:
- CSRF validation is tested explicitly, not implicitly
- Regular tests don't suffer CSRF failures
- Safe, separated CSRF test coverage

### 5. PYTHONPATH Hygiene (No Relative Path Guessing)

**Files:** `backend/pytest.ini`, `tests/smoke/conftest.py`

Import paths are explicit, not guessed:

```ini
pythonpath = . ..
```

**In conftest.py (smoke tests):**
```python
backend_path = os.path.join(os.path.dirname(__file__), '../../backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
```

**Guarantees:**
- Imports work from any directory (not just "backend/")
- Relative paths are resolved at conftest load time
- No need to set `PYTHONPATH` environment variable

### 6. Fixture Isolation (No Cross-Test Leakage)

**Files:** `backend/tests/conftest.py`

Fixtures are scoped to prevent leakage:

```python
@pytest.fixture              # Default scope: function
def app():
    # Fresh app for EACH test
    ...

@pytest.fixture(scope='session')
def backend_app():
    # Single app for all smoke tests (production-like)
    ...
```

**Guarantees:**
- Unit tests get fresh databases (isolated)
- Smoke tests reuse a single app (testing production-like behavior)
- App context is always properly managed (no SQLAlchemy warnings)

### 7. Explicit Test Markers (No Magic Test Selection)

**Files:** `backend/pytest.ini`

Test categories are explicit:

```ini
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (external deps)
    security: Security validation tests
    contract: API contract and interface tests
    e2e: End-to-end workflow tests
    persistence: Save/load tests
    slow: Slow running tests
```

**How to use:**
```python
@pytest.mark.unit
def test_fast_business_logic():
    # Fast, no DB, no external deps
    pass

@pytest.mark.integration
def test_with_database():
    # Uses real DB, auth, API calls
    pass
```

**Benefits:**
- Run fast tests only: `pytest -m unit`
- Skip slow tests in CI fast-feedback: `pytest -m "not slow"`
- No guessing about test type or speed

---

## Reducing Local Leakage: Checklist

The repository follows these principles to prevent local environment assumptions:

### ✅ Dependency Management
- [x] All test packages declared in requirements-test.txt
- [x] No undeclared import-time dependencies
- [x] pytest plugins listed explicitly (pytest-asyncio, pytest-cov)

### ✅ Configuration
- [x] pytest.ini exists with explicit pythonpath, testpaths, markers
- [x] All config classes defined in app/config.py
- [x] No reliance on IDE-specific environment variables

### ✅ Fixtures
- [x] Database fixtures use in-memory SQLite by default
- [x] Rate limiter is reset between tests
- [x] Roles and areas are auto-seeded
- [x] App context is properly managed

### ✅ PYTHONPATH
- [x] pytest.ini declares pythonpath
- [x] conftest.py has explicit path setup
- [x] Imports work from any directory

### ✅ Secrets
- [x] TestingConfig has fixed test secrets
- [x] No environment variables required for testing (optional for CI)
- [x] DEV_SECRETS_OK fallback for local development

### ✅ External Services
- [x] Play service URLs have test defaults
- [x] Email is disabled by default in tests
- [x] No tests require external API calls (or mock them)

---

## Known Remaining Assumptions

Some behaviors are **intentionally dependent on environment**:

### Real Database (Smoke Tests)
Smoke tests use a real SQLite file (not in-memory) to simulate production-like behavior. This requires:
- Writable directory (`backend/instance/`)
- SQLite available (standard in Python)
- No database locks from other processes

**Mitigation:** Smoke tests are designed to be fast and standalone, not run concurrently with other DB operations.

### Email Configuration (Optional)
Email tests require mail server configuration (or can be skipped):
```bash
MAIL_ENABLED=0 pytest tests/  # Skip email tests
MAIL_ENABLED=1 MAIL_SERVER=... pytest tests/  # Run email tests
```

### Play Service Integration (Optional)
Tests can validate Play Service integration with test defaults:
```python
PLAY_SERVICE_PUBLIC_URL = "http://play.example.test"  # Test default
```

---

## Validation: How to Ensure Hygiene

Run these checks regularly:

### 1. Clean Environment Test
```bash
python -m venv /tmp/clean_test
source /tmp/clean_test/bin/activate
cd backend
pip install -r requirements.txt -r requirements-test.txt
pytest tests/ -v --tb=short
# All tests should pass without local venv pollution
```

### 2. Check Dependencies
```bash
# List all packages used by requirements-test.txt
pip freeze | grep -E "pytest|flask|sqlalchemy"

# Verify no extra packages from local .venv are leaking
pip list --not-required
```

### 3. Validate pytest Configuration
```bash
cd backend
pytest --version
pytest -c pytest.ini --collect-only tests/ | wc -l
# Should show expected test count

# Verify asyncio mode
pytest --fixtures | grep -i asyncio
```

### 4. Check PYTHONPATH
```bash
python -c "import sys; print('\n'.join(sys.path))"
cd tests/smoke && python -c "from app import create_app; print('OK')"
```

---

## Guidelines for Maintaining Hygiene

When adding new tests or dependencies:

1. **Adding a dependency?** → Add to `backend/requirements.txt` or `requirements-test.txt` (not just local .venv)
2. **Using a new package at import time?** → Add to `requirements-test.txt`
3. **Adding a new test?** → Use a fixture from conftest or create an isolated fixture
4. **Need a config option?** → Add to app/config.py, not hardcoded values
5. **Local setup step?** → Document it in testing-setup.md
6. **Test requires external service?** → Mock it or test with defaults

Following these practices keeps the test suite reproducible and maintainable for the whole team.

