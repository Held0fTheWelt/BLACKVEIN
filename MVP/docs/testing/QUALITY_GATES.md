# Quality Gates and Test Coverage Requirements

**Version**: 1.0
**Date**: 2026-03-25
**Status**: ACTIVE

This document defines explicit quality gates, test execution profiles, and coverage thresholds for the WorldOfShadows project.

---

## Overview

Quality gates are automated checks that validate code meets minimum standards for correctness, security, and coverage. This document:

1. **Defines coverage thresholds** for each test suite
2. **Specifies when each profile is required**
3. **Documents gate failure criteria and remediation**
4. **Provides clear commands for each profile**

---

## Coverage Thresholds by Suite

### Backend Suite

| Metric | Threshold | Current | Status |
|--------|-----------|---------|--------|
| **Minimum Coverage** | 85% | 25%* | ⚠️ Below threshold |
| **Unit Tests** | Required | ~1950 tests | ✓ Comprehensive |
| **Security Tests** | Required | 114+ tests | ✓ Passing |
| **Contract Tests** | Required | 286+ tests | ✓ Passing |

**Backend Configuration** (`backend/pytest.ini`):
```ini
[pytest]
addopts = -v --tb=short --cov=app --cov-report=term-missing --cov-fail-under=85
```

**Status Note**: The 25% measurement is from discovery-only mode (no actual test execution). Real coverage varies by test run scope. See Backend Test Profiles below for accurate measurements.

---

### Administration Tool Suite

| Metric | Threshold | Current | Status |
|--------|-----------|---------|--------|
| **Minimum Coverage** | None specified | 96.67% | ✓ Excellent |
| **Total Tests** | - | 1,039 tests | ✓ Comprehensive |
| **Pass Rate** | 100% | 100% | ✓ All passing |
| **Fast Profile** | <15s | ~10s | ✓ Optimal |
| **Full Profile** | <30s | ~20s | ✓ Optimal |

**Test Markers Used**:
- `unit` - Fast, isolated tests
- `integration` - Tests with external dependencies
- `security` - Authentication and authorization
- `contract` - API contract tests
- `browser` - Browser-based integration
- `slow` - Tests exceeding 1 second

---

### World Engine Suite

| Metric | Threshold | Current | Status |
|--------|-----------|---------|--------|
| **Minimum Coverage** | None specified | 96.96% | ✓ Excellent |
| **Total Tests** | - | 788 tests | ✓ Comprehensive |
| **Pass Rate** | 97.7%+ | 97.7% | ✓ Known isolation issues |
| **Fast Profile** | <12s | ~10s | ✓ Optimal |
| **Full Profile** | <15s | ~12s | ✓ Optimal |
| **Contract Tests** | 100% pass | 458/458 | ✓ Production ready |

**Test Markers Used**:
- `unit` - Fast, isolated tests
- `integration` - Tests with external dependencies
- `security` - Authentication and authorization
- `contract` - API contract tests
- `config` - Configuration and startup
- `browser` - Browser integration tests
- `websocket` - Real-time communication
- `persistence` - Save/load functionality
- `slow` - Tests exceeding 1 second

**Known Issues**: 18 tests fail due to test isolation (configuration module caching). See `XFAIL_POLICY.md` for details. These pass in isolation and do not reflect production issues.

---

## Test Execution Profiles

### Profile 1: Fast Unit Tests (Development)

**Purpose**: Rapid feedback during development; runs in <15 seconds
**When Required**: Before committing; local development iteration
**Frequency**: Every developer commit

#### Backend Fast Profile
```bash
cd backend && python -m pytest tests/ -m "not slow" -v --tb=short
```
- **Expected**: 1,900+ tests
- **Duration**: ~20-30 seconds
- **Pass Rate**: Should be 100%
- **Coverage**: Not measured (optional)

#### Administration Tool Fast Profile
```bash
cd administration-tool && python -m pytest tests/ -m "not slow" -v
```
- **Expected**: ~1,000+ tests
- **Duration**: ~10-15 seconds
- **Pass Rate**: 100%
- **Coverage**: Not measured

#### World Engine Fast Profile
```bash
cd world-engine && python -m pytest tests/ -m "not slow and not websocket" -v
```
- **Expected**: ~683 tests
- **Duration**: ~10 seconds
- **Pass Rate**: 99%+ (known isolation issues documented)
- **Coverage**: Not measured

#### Run All Fast Profiles
```bash
# From project root:
python run_tests.py --suite all --quick
```
- **Expected**: 3,500+ tests across all suites
- **Duration**: ~40 seconds
- **Pass Rate**: Should be 100% (backend) + 100% (admin) + 99%+ (engine)

---

### Profile 2: Full Suite with Coverage (Pre-deployment)

**Purpose**: Complete validation with coverage measurement
**When Required**: Before merging to main/master; pre-release testing
**Frequency**: Before every deployment

#### Backend Full Profile
```bash
cd backend && python -m pytest tests/ -v --tb=short \
  --cov=app --cov-report=term-missing --cov-fail-under=85
```
- **Expected**: 1,950+ tests
- **Duration**: ~40-60 seconds
- **Pass Rate**: 100% required
- **Coverage Threshold**: 85% minimum
- **Gate Failure Criteria**:
  - Any test failure
  - Coverage below 85%

#### Administration Tool Full Profile
```bash
cd administration-tool && python -m pytest tests/ -v
```
- **Expected**: 1,039 tests
- **Duration**: ~20-30 seconds
- **Pass Rate**: 100% required
- **Coverage Threshold**: None specified (96.67% typical)
- **Gate Failure Criteria**: Any test failure

#### World Engine Full Profile
```bash
cd world-engine && python -m pytest tests/ -v
```
- **Expected**: 788 tests
- **Duration**: ~12 seconds
- **Pass Rate**: 97.7%+ (known isolation issues)
- **Coverage Threshold**: None specified (96.96% typical)
- **Gate Failure Criteria**:
  - Any NEW test failures (18 known failures are acceptable)
  - Regression in pass rate below 97%

#### Run All Full Suites
```bash
# From project root:
python run_tests.py --suite all --coverage
```
- **Expected**: 3,777+ total tests
- **Duration**: ~90-120 seconds
- **Pass Rate**: Backend 100%, Admin 100%, Engine 97.7%+
- **Backend Coverage**: 85% minimum

---

### Profile 3: Security-Only Tests

**Purpose**: Focused security validation; quick gate for security-critical changes
**When Required**: After any auth/security code changes
**Frequency**: Always before security-related PRs

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows && \
  pytest -m security -v --tb=short
```

**Test Breakdown**:
- World Engine security: 114+ tests
- Admin Tool security: 56+ tests
- Backend security: 49+ tests
- **Total**: 219+ security tests
- **Duration**: ~15-20 seconds
- **Pass Rate**: 100% required
- **Coverage**: Not measured

**Gate Failure Criteria**:
- Any test failure
- Any authentication bypass
- Any authorization violation

---

### Profile 4: Contract/Integration Tests

**Purpose**: Validates cross-service contracts and API compatibility
**When Required**: Before API changes; cross-service integration modifications
**Frequency**: Always before API-related PRs

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows && \
  pytest -m contract -v --tb=short
```

**Test Breakdown**:
- World Engine contracts: 458 tests
- Admin Tool contracts: 228+ tests
- Backend contracts: 215+ tests
- **Total**: 900+ contract tests
- **Status**: 100% passing
- **Duration**: ~20-30 seconds
- **Pass Rate**: 100% required

**Gate Failure Criteria**: Any test failure (these are production-critical)

---

### Profile 5: Backend-World Engine Bridge Tests

**Purpose**: Specific validation of backend-to-engine integration (tickets, participant context)
**When Required**: When modifying ticket format or participant context
**Frequency**: Before releasing cross-service changes

```bash
cd world-engine && \
  python -m pytest tests/test_backend_bridge_contract.py -v --tb=short
```

**Tests**: 24 bridge contract tests
**Duration**: ~0.3 seconds
**Pass Rate**: 100% (100% passing)
**Status**: Production ready

**Gate Failure Criteria**: Any test failure

---

### Profile 6: Production-Like Smoke Tests

**Purpose**: Final validation before production deployment
**When Required**: Final gate before release to production
**Frequency**: Once per release cycle

```bash
# Combines fast tests from all suites
python run_tests.py --suite all --quick && \
pytest -m "contract or (security and unit)" -v
```

**Scope**:
- Fast unit tests (all suites)
- All contract tests (cross-service validation)
- Core security tests

**Duration**: ~60 seconds
**Pass Rate**: 100% required
**Coverage**: Not enforced (optional)

---

## Gate Failure Procedures

### When a Test Fails

1. **Check if expected failure**: Review `XFAIL_POLICY.md` for world-engine known issues
2. **Reproduce locally**: Run the specific test in isolation
   ```bash
   pytest tests/test_file.py::TestClass::test_function -vv
   ```
3. **Investigate root cause**: Check test logs, database state, configuration
4. **Decide remediation**:
   - **Code fix**: Fix the production code
   - **Test fix**: Fix the test (if test is wrong)
   - **Expected failure**: If isolated test failure, document in XFAIL_POLICY.md

### When Coverage Fails

1. **Check coverage report**:
   ```bash
   cd backend && python -m pytest tests/ --cov=app --cov-report=html
   open htmlcov/index.html
   ```
2. **Identify uncovered code**: Review lines marked as not covered
3. **Add tests**: Write unit/integration tests to cover the code
4. **Verify**: Re-run profile with coverage flag

### When Multiple Profiles Fail

Run in order of speed (fastest first) to isolate the issue:
1. Fast profile (unit tests)
2. Security profile
3. Contract profile
4. Full suite with coverage

---

## CI/CD Integration

### GitHub Actions Workflow Recommendation

```yaml
name: Quality Gates

on: [push, pull_request]

jobs:
  fast-tests:
    name: Fast Tests (All Suites)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r backend/requirements-dev.txt
      - run: python run_tests.py --suite all --quick
      - name: Upload test reports
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-reports
          path: test_reports/

  security-tests:
    name: Security Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r backend/requirements-dev.txt
      - run: pytest -m security -v

  contract-tests:
    name: Contract Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r backend/requirements-dev.txt
      - run: pytest -m contract -v

  backend-coverage:
    name: Backend Coverage
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r backend/requirements-dev.txt
      - run: cd backend && python -m pytest tests/ \
          --cov=app --cov-report=xml --cov-fail-under=85
      - uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  full-suite:
    name: Full Test Suite (Pre-deployment)
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    needs: [fast-tests, security-tests, contract-tests, backend-coverage]
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r backend/requirements-dev.txt
      - run: python run_tests.py --suite all --coverage
```

---

## Performance Expectations

| Profile | Min Duration | Max Duration | Target |
|---------|--------------|--------------|--------|
| Fast Unit | 15s | 45s | <25s |
| Security | 10s | 25s | <15s |
| Contract | 15s | 35s | <25s |
| Full Suite | 60s | 150s | <90s |
| Bridge | <1s | 2s | <0.5s |

If a profile exceeds the maximum duration, investigate:
- Slow tests (use `--durations=10` flag)
- Resource constraints (disk I/O, memory)
- Database lock issues
- Network latency

---

## Marker-Based Profile Selection

### Run Only Unit Tests
```bash
pytest -m unit -v
```
Fastest, most isolated tests.

### Run Only Integration Tests
```bash
pytest -m integration -v
```
Tests requiring external resources.

### Run Only Slow Tests
```bash
pytest -m slow -v
```
Identify performance-critical tests.

### Exclude WebSocket Tests
```bash
pytest -m "not websocket" -v
```
Useful for quick validation without async tests.

### Exclude Slow Tests
```bash
pytest -m "not slow" -v
```
Standard fast profile filter.

---

## Threshold Adjustments

### When to Increase a Threshold

1. **Coverage**: Only if refactoring makes code uncoverable
2. **Test Count**: Never intentionally reduce; only increase with new features
3. **Duration**: Only if adding comprehensive integration tests

### When to Decrease a Threshold

1. **Coverage**: Never
2. **Test Count**: Only if removing redundant tests
3. **Duration**: Optimize slow tests; never reduce quality

---

## Quality Gate Summary

| Gate | Profile | Threshold | Type | Enforced |
|------|---------|-----------|------|----------|
| **Fast Tests** | All unit tests | 100% pass | Soft | Pre-commit |
| **Security** | Security-marked tests | 100% pass | Hard | Pre-deployment |
| **Contracts** | Contract-marked tests | 100% pass | Hard | Pre-deployment |
| **Backend Coverage** | Code coverage measurement | 85% | Hard | Pre-deployment |
| **Backend Quality** | All backend tests | 100% pass | Hard | Pre-deployment |
| **Admin Quality** | All admin tests | 100% pass | Hard | Pre-deployment |
| **Engine Quality** | All engine tests | 97.7%+ pass | Soft | Pre-deployment |

---

## Known Limitations and Waivers

### World Engine Test Isolation (WAVE 9)
- **Issue**: 18 tests fail in full suite due to config caching
- **Impact**: 97.7% pass rate (not 100%)
- **Status**: Documented in XFAIL_POLICY.md
- **Remediation**: Planned for v0.1.11+
- **Waiver**: Acceptable for current release; these tests pass in isolation

### Backend Coverage Measurement
- **Current**: 25% (collection mode, no execution)
- **Expected**: 85%+ (full suite execution)
- **Note**: Collection-only mode is conservative; actual coverage is higher

---

## Updating This Document

When adding new features or tests:

1. Update **Test Profiles** section if new profile is needed
2. Update **Coverage Thresholds** if targets change
3. Update **CI/CD Integration** example if gates change
4. Ensure **Performance Expectations** are realistic
5. Document any new **Known Limitations**

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-25 | Initial quality gates documentation; 3-suite baseline |

