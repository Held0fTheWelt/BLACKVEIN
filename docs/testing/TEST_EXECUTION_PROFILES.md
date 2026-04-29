# Test Execution Profiles

This document describes practical test execution patterns for the WorldOfShadows project with exact commands. Use these profiles to efficiently run different test suites across the backend, administration tool, and world engine components.

## Overview

The project is organized into three main testing contexts:
- **Backend** - Flask API and core business logic (1,950+ tests)
- **Administration Tool** - Admin interface and management features (1,039 tests)
- **World Engine** - Game runtime and WebSocket communication (788 tests)

Each profile below includes the exact command, expected test counts, typical execution time, and quality gate requirements.

**Updated**: v1.0 (WAVE 9+) with quality gate documentation
**Coverage Thresholds**: Backend 85% minimum; others documented in QUALITY_GATES.md
**Note**: Some cross-service tests have known test isolation issues; see XFAIL_POLICY.md.

**Cross-reference**: See QUALITY_GATES.md for comprehensive quality gate requirements, thresholds, and CI/CD integration guidance.

---

## Admin Tool Test Profiles

### Fast Admin Suite
Runs admin tests excluding slow/integration tests.

**Purpose**: Quick validation of admin functionality during development.

**Command**:
```bash
cd administration-tool && python -m pytest tests/ -m "not slow" -v
```

**Expected Test Count**: 25-35 tests
**Typical Execution Time**: 5-10 seconds
**When to Use**: Before committing changes to admin tool code; rapid feedback loop.

---

### Full Admin Suite
Runs all admin tests including slow integration tests.

**Purpose**: Complete validation before deployment; verifies all admin features.

**Command**:
```bash
cd administration-tool && python -m pytest tests/ -v
```

**Expected Test Count**: 35-45 tests
**Typical Execution Time**: 15-30 seconds
**When to Use**: Pre-deployment testing; final validation before merging to main.

---

## World Engine Test Profiles

### Fast World Engine Suite
Core world engine tests excluding slow and WebSocket tests.

**Purpose**: Quick validation of world engine core logic (stores, runs, snapshots).

**Command**:
```bash
cd world-engine && python -m pytest tests/ -m "not slow and not websocket" -v
```

**Expected Test Count**: 683 tests (5 known failures)
**Typical Execution Time**: ~10 seconds
**When to Use**: During development; quick feedback on core engine changes.
**Note**: Known test isolation issues affect 5 tests; they pass in isolation but fail in suite. See XFAIL_POLICY.md.

---

### Full World Engine Suite
All world engine tests including slow and WebSocket tests.

**Purpose**: Comprehensive validation of world engine including real-time features.

**Command**:
```bash
cd world-engine && python -m pytest tests/ -v
```

**Expected Test Count**: 770 tests (18 known failures)
**Typical Execution Time**: ~12 seconds
**When to Use**: Pre-deployment; validating complete world engine functionality.
**Note**: Known test isolation issues affect 18 tests in full suite run; they pass in isolation. See XFAIL_POLICY.md.

---

## Cross-Service Test Profiles

### Security Tests Only
Runs all security-related tests across both projects.

**Purpose**: Focused security validation; ensures authentication, authorization, and encryption features work.

**Command**:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows && pytest -m security -v
```

**Expected Test Count**:
- World-engine: 159 security tests
- Admin-tool: 240 security tests
- **Total: 399+ security tests**

**Typical Execution Time**: 15-25 seconds
**When to Use**: When making auth/security changes; security audit runs.

---

### Contract Tests Only
Runs all contract tests (API contracts, data contracts, cross-service contracts).

**Purpose**: Validates API contracts and cross-service integration; ensures services can communicate.

**Command**:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows && pytest -m contract -v
```

**Expected Test Count**:
- World-engine: 458 contract tests (100% passing)
- Admin-tool: 721 contract tests (100% passing)
- **Total: 1179+ contract tests (ALL PASSING)**

**Typical Execution Time**: 20-30 seconds
**When to Use**: When changing API signatures or cross-service integration points.
**Status**: All contract tests PASS - production-ready cross-service validation.

---

### Backend-WorldEngine Bridge Tests
Runs backend-to-world-engine integration tests specifically.

**Purpose**: Validates that backend-issued tickets work with world engine; tests cross-service contracts.

**Command**:
```bash
cd world-engine && python -m pytest tests/test_backend_bridge_contract.py -v
```

**Expected Test Count**: 24 tests
**Typical Execution Time**: ~0.3 seconds
**Test Status**: 24/24 PASSING (100%)
**When to Use**: When modifying backend/world-engine integration; ticket format changes.
**Production Ready**: YES - All critical cross-service contracts verified.

---

### WebSocket Tests Only
World engine WebSocket tests for real-time communication.

**Purpose**: Validates WebSocket connection, message handling, and real-time features.

**Command**:
```bash
cd world-engine && python -m pytest tests/test_ws*.py -v
```

**Expected Test Count**: 25-35 tests
**Typical Execution Time**: 15-25 seconds
**When to Use**: When changing WebSocket behavior or message formats.

---

## Multi-Suite Test Execution

### Run All Tests Across All Suites

**Purpose**: Complete project validation.

**Command**:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows && python run_tests.py --suite all
```

**Expected Test Count**: 1,800+ total tests
**Breakdown**:
- Backend: (built into run_tests.py)
- Administration Tool: 1,038 tests
- World Engine: 770 tests

**Typical Execution Time**: 30-45 seconds total
**When to Use**: Pre-release testing; major feature validation.

---

### Run Fast Tests (All Suites)

Fast validation excluding slow/integration tests.

**Command**:
```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows && python run_tests.py --suite all && pytest -m "not slow and not websocket" -v
```

**Expected Test Count**: 120-160 tests
**Typical Execution Time**: 20-40 seconds
**When to Use**: During continuous development; regular check-ins.

---

## Individual Test File Execution

### Run a Single Test File

To run tests in a specific file:

```bash
cd world-engine && python -m pytest tests/test_ticket_manager.py -v
```

### Run a Specific Test Class

To run all tests in a test class:

```bash
cd world-engine && python -m pytest tests/test_api.py::TestCreateRunBehavior -v
```

### Run a Specific Test Function

To run a single test function:

```bash
cd world-engine && python -m pytest tests/test_api.py::TestCreateRunBehavior::test_create_run_returns_valid_run_structure -v
```

---

## Debug Execution

### Verbose Output with Detailed Tracebacks

For detailed debugging information:

```bash
cd world-engine && python -m pytest tests/test_api.py -vv --tb=long
```

**Flags Explained**:
- `-vv` - Extra verbose (shows more details, variable values)
- `--tb=long` - Long traceback format (shows local variables on failure)

---

### Show Print Statements During Test Execution

Capture output from print statements in tests:

```bash
cd world-engine && python -m pytest tests/test_api.py -s -v
```

**Flags Explained**:
- `-s` - Show output (capture=no); prints to stdout

---

### Stop on First Failure

Exit test run immediately on first failure (useful for debugging):

```bash
cd world-engine && python -m pytest tests/test_api.py -x -v
```

**Flags Explained**:
- `-x` - Exit on first failure

---

### Run Only Failed Tests (After Initial Run)

After running tests, re-run only the ones that failed:

```bash
cd world-engine && python -m pytest tests/ --lf -v
```

**Flags Explained**:
- `--lf` - Last failed (re-run only previously failed tests)

---

### Watch Mode (Run Tests on File Changes)

Use pytest-watch plugin for automatic re-run on file changes:

```bash
cd world-engine && pip install pytest-watch
ptw tests/ -v
```

---

## Coverage Requirements

### Generate Coverage Report

Generate a coverage report showing test coverage:

```bash
cd world-engine && python -m pytest tests/ --cov=app --cov-report=html -v
```

This creates an HTML coverage report in `htmlcov/index.html`.

### Check Coverage for Specific Module

```bash
cd world-engine && python -m pytest tests/ --cov=app.auth.tickets --cov-report=term-missing -v
```

**Typical Targets**:
- `app.auth` - Authentication (tickets, WebSocket auth)
- `app.api` - API endpoints (HTTP and WebSocket)
- `app.runtime` - Game runtime (manager, stores)

### Coverage Thresholds

For CI/CD integration, enforce minimum coverage:

```bash
cd world-engine && python -m pytest tests/ --cov=app --cov-fail-under=75 -v
```

This fails the test run if coverage is below 75%.

---

## CI/CD Integration Suggestions

### GitHub Actions Workflow Example

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run fast tests
        run: |
          cd world-engine && python -m pytest tests/ -m "not slow" -v
          cd ../administration-tool && python -m pytest tests/ -m "not slow" -v

      - name: Run contract tests
        run: pytest -m contract -v

      - name: Run security tests
        run: pytest -m security -v
```

### Pre-commit Hook

Add test execution before commits:

```bash
#!/bin/bash
# .git/hooks/pre-commit

cd world-engine
python -m pytest tests/ -m "not slow and not websocket" -v --tb=short || exit 1

cd ../administration-tool
python -m pytest tests/ -m "not slow" -v --tb=short || exit 1
```

---

## Test Markers and Tags

Tests are marked with pytest markers for selective execution:

### Available Markers

- `@pytest.mark.unit` - Unit tests (no dependencies, fast)
- `@pytest.mark.integration` - Integration tests (may be slow)
- `@pytest.mark.contract` - API/service contract tests
- `@pytest.mark.security` - Security and authentication tests
- `@pytest.mark.slow` - Tests known to take longer (>1 second)
- `@pytest.mark.websocket` - WebSocket-specific tests

### Run Tests by Marker

```bash
# Only unit tests
cd world-engine && python -m pytest tests/ -m unit -v

# Integration tests only
cd world-engine && python -m pytest tests/ -m integration -v

# Contract and security tests
cd world-engine && python -m pytest tests/ -m "contract or security" -v

# Not slow tests
cd world-engine && python -m pytest tests/ -m "not slow" -v
```

---

## Test Report Generation

### Generate JUnit XML Report

For CI/CD systems:

```bash
cd world-engine && python -m pytest tests/ --junit-xml=test_reports/junit.xml -v
```

### Generate HTML Report

```bash
cd world-engine && pip install pytest-html
python -m pytest tests/ --html=test_reports/report.html -v
```

---

## Performance Profiling

### Profile Slow Tests

Find out which tests are slowest:

```bash
cd world-engine && python -m pytest tests/ --durations=10 -v
```

Shows the 10 slowest tests.

### Benchmark Tests

For performance regression detection:

```bash
cd world-engine && pip install pytest-benchmark
python -m pytest tests/ --benchmark-only -v
```

---

## Troubleshooting Common Issues

### Tests Hanging on WebSocket

Use the timeout protection in conftest:

```python
# Already configured in conftest.py
def receive_until_snapshot(websocket, predicate, attempts: int = 6, timeout: float = 5.0):
    """Receive with timeout protection."""
```

### Database Lock Errors

Clear temporary test data:

```bash
rm -rf world-engine/.pytest_cache
rm -rf administration-tool/.pytest_cache
```

### Import Errors

Ensure Python path includes project root:

```bash
export PYTHONPATH=/mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows:$PYTHONPATH
```

### Port Already in Use

Tests use different ports; clean up:

```bash
lsof -i :5000  # Find what's using port 5000
kill -9 <PID>
```

---

## Quick Reference Table

| Profile | Command | Tests | Time | Status | Use Case | Quality Gate |
|---------|---------|-------|------|--------|----------|--------------|
| Fast Admin | `cd admin && pytest -m "not slow"` | 1,000+ | 10-15s | ✓ All pass | Dev iteration | Soft |
| Full Admin | `cd admin && pytest` | 1,039 | 15-20s | ✓ All pass | Pre-deploy | Hard |
| Fast WE | `cd world-engine && pytest -m "not slow and not websocket"` | 683 | ~10s | 99%+ pass* | Dev iteration | Soft |
| Full WE | `cd world-engine && pytest` | 788 | ~12s | 97.7% pass* | Full validation | Soft |
| Fast Backend | `cd backend && pytest -m "not slow"` | 1,900+ | 20-30s | ✓ All pass | Dev iteration | Soft |
| Full Backend | `cd backend && pytest --cov=app --cov-fail-under=85` | 1,950+ | 40-60s | ✓ 85% coverage | Pre-deploy | Hard |
| Security | `pytest -m security` | 219+ | 15-20s | ✓ All pass | Security audit | Hard |
| Contracts | `pytest -m contract` | 900+ | 20-30s | ✓ All pass (100%) | API changes | Hard |
| Bridge | `cd world-engine && pytest test_backend_bridge_contract.py` | 24 | 0.3s | ✓ All pass (100%) | Integration changes | Hard |
| All Fast | `python run_tests.py --suite all --quick` | 3,500+ | ~40s | See notes | Dev gates | Soft |
| All Full | `python run_tests.py --suite all --coverage` | 3,777+ | ~90-120s | See notes | Release testing | Hard |

**\* Known test isolation issues documented in XFAIL_POLICY.md**

**Quality Gate Levels**:
- **Soft**: Nice to have; informational; can proceed if most pass
- **Hard**: Required; gate blocks merging; must pass at 100% (except Engine at 97.7%+)

---

## Notes

- All commands assume you're in the project root unless `cd` is specified
- Test counts are approximate and may vary with code changes
- Execution times are measured on typical development hardware
- Use `-v` flag for verbose output (recommended during development)
- Use `-q` flag for quiet mode (recommended in CI/CD pipelines)
- All paths are absolute to avoid confusion with working directory

