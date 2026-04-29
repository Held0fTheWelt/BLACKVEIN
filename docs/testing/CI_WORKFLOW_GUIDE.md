# CI/CD Workflow Guide

**Version**: 1.0
**Date**: 2026-03-25
**Status**: ACTIVE

This document describes the GitHub Actions CI/CD workflows for the WorldOfShadows project, their purpose, triggers, and integration strategies.

---

## Overview

The CI/CD pipeline consists of five separate workflows designed to provide fast feedback while enforcing quality gates:

1. **Backend Tests** - Backend-specific fast and full test suites with 85% coverage enforcement
2. **Admin Tests** - Administration tool fast and full test suites
3. **Engine Tests** - World engine fast and full test suites
4. **Quality Gate** - Cross-service security, contract, and bridge contract tests
5. **Pre-Deployment** - Full suite validation before production deployment

---

## Workflow Definitions

### 1. Backend Tests Workflow

**File**: `.github/workflows/backend-tests.yml`

**Triggers**:
- Push to `master`, `main`, `develop` branches (when `backend/` path changes)
- Pull request to `master`, `main`, `develop` branches (when `backend/` path changes)

**Jobs**:

#### Job 1: Backend Fast Tests
- **Name**: Backend Fast Tests (Unit Tests)
- **Runs On**: ubuntu-latest
- **Python**: 3.10
- **Command**: `cd backend && pytest tests/ -m "not slow" -v --tb=short`
- **Expected Tests**: 1,900+
- **Duration**: 20-30 seconds
- **Pass Requirement**: 100%
- **Artifacts**: test_reports/ (30 day retention)
- **Dependency**: None (runs first)
- **Classification**: Required on every push

#### Job 2: Backend Coverage Tests
- **Name**: Backend Coverage Tests (85% Gate)
- **Runs On**: ubuntu-latest
- **Python**: 3.10
- **Command**: Coverage-enabled full test suite with `--cov-fail-under=85`
- **Expected Tests**: 1,950+
- **Duration**: 40-60 seconds
- **Pass Requirement**: 100% + 85% coverage minimum
- **Artifacts**: test_reports/ + coverage.xml (30 day retention)
- **Dependency**: Requires backend-fast-tests to pass
- **Coverage Upload**: Codecov integration (non-blocking)
- **Classification**: Required on every push (hard gate)

**Coverage Threshold**: 85% (hard gate — if coverage below threshold, job fails)

---

### 2. Administration Tool Tests Workflow

**File**: `.github/workflows/admin-tests.yml`

**Triggers**:
- Push to `master`, `main`, `develop` branches (when `administration-tool/` path changes)
- Pull request to `master`, `main`, `develop` branches (when `administration-tool/` path changes)

**Jobs**:

#### Job 1: Admin Fast Tests
- **Name**: Admin Fast Tests (Unit Tests)
- **Runs On**: ubuntu-latest
- **Python**: 3.10
- **Command**: `cd administration-tool && pytest tests/ -m "not slow" -v --tb=short`
- **Expected Tests**: 1,000+
- **Duration**: 10-15 seconds
- **Pass Requirement**: 100%
- **Artifacts**: test_reports/ (30 day retention)
- **Dependency**: None (runs first)
- **Classification**: Required on every push

#### Job 2: Admin Full Tests
- **Name**: Admin Full Tests
- **Runs On**: ubuntu-latest
- **Python**: 3.10
- **Command**: `cd administration-tool && pytest tests/ -v --tb=short`
- **Expected Tests**: 1,039
- **Duration**: 15-20 seconds
- **Pass Requirement**: 100%
- **Artifacts**: test_reports/ (30 day retention)
- **Dependency**: Requires admin-fast-tests to pass
- **Classification**: Required on every push (hard gate)

---

### 3. World Engine Tests Workflow

**File**: `.github/workflows/engine-tests.yml`

**Triggers**:
- Push to `master`, `main`, `develop` branches (when `world-engine/` path changes)
- Pull request to `master`, `main`, `develop` branches (when `world-engine/` path changes)

**Jobs**:

#### Job 1: Engine Fast Tests
- **Name**: Engine Fast Tests (No Slow/WebSocket)
- **Runs On**: ubuntu-latest
- **Python**: 3.10
- **Command**: `cd world-engine && pytest tests/ -m "not slow and not websocket" -v --tb=short`
- **Expected Tests**: 683+
- **Duration**: ~10 seconds
- **Pass Requirement**: 100%
- **Artifacts**: test_reports/ (30 day retention)
- **Dependency**: None (runs first)
- **Classification**: Required on every push

#### Job 2: Engine Full Tests
- **Name**: Engine Full Tests (All Tests)
- **Runs On**: ubuntu-latest
- **Python**: 3.10
- **Command**: `cd world-engine && pytest tests/ -v --tb=short`
- **Expected Tests**: 788
- **Duration**: ~12 seconds
- **Pass Requirement**: 97.7%+ (18 known isolation failures acceptable)
- **Artifacts**: test_reports/ (30 day retention)
- **Dependency**: Requires engine-fast-tests to pass
- **Classification**: Required on every push (soft gate with known waiver)

**Known Limitation**: 18 tests fail in full suite due to configuration module caching. These tests pass in isolation; see `XFAIL_POLICY.md` for details.

---

### 4. Quality Gate Workflow

**File**: `.github/workflows/quality-gate.yml`

**Triggers**:
- Push to `master`, `main`, `develop` branches
- Pull request to `master`, `main`, `develop` branches

**Jobs** (independent, parallel execution):

#### Job 1: Security Tests
- **Name**: Security-Only Tests
- **Command**: `pytest -m security -v --tb=short`
- **Expected Tests**: 219+
- **Duration**: 15-20 seconds
- **Pass Requirement**: 100%
- **Classification**: Hard gate — blocks merging if failed

#### Job 2: Contract Tests
- **Name**: Contract Tests (API Contracts)
- **Command**: `pytest -m contract -v --tb=short`
- **Expected Tests**: 900+
- **Duration**: 20-30 seconds
- **Pass Requirement**: 100%
- **Status**: All contract tests passing (production-ready)
- **Classification**: Hard gate — blocks merging if failed

#### Job 3: Bridge Contract Tests
- **Name**: Bridge Contract Tests (Backend-Engine)
- **Command**: `cd world-engine && pytest tests/test_backend_bridge_contract.py -v --tb=short`
- **Expected Tests**: 24
- **Duration**: ~0.3 seconds
- **Pass Requirement**: 100%
- **Status**: All bridge tests passing (production-ready)
- **Classification**: Hard gate — blocks merging if failed

#### Job 4: Quality Gate Report
- **Name**: Quality Gate Report
- **Runs After**: All three test jobs complete
- **Collects**: All test artifacts
- **Generates**: Summary report in GitHub Actions summary
- **Dependency**: Needs all three test jobs (waits for completion)
- **Behavior**: Reports final status of all gates

---

### 5. Pre-Deployment Workflow

**File**: `.github/workflows/pre-deployment.yml`

**Triggers**:
- Push to `master` or `main` branch
- Manual trigger (`workflow_dispatch`)

**Jobs**:

#### Job 1: Full Suite
- **Name**: Full Test Suite (All Suites)
- **Python**: 3.10
- **Runs**: Only on push to main/master or manual trigger
- **Steps**:
  1. Run full backend suite with 85% coverage enforcement
  2. Run full admin suite
  3. Run full engine suite
  4. Upload coverage to codecov
  5. Upload all artifacts
- **Total Duration**: ~90-120 seconds
- **Pass Requirement**: Backend 100% + 85% coverage, Admin 100%, Engine 97.7%+
- **Artifacts**: 60 day retention (longer than other workflows)
- **Classification**: Hard gate for production deployment

#### Job 2: Pre-Deployment Report
- **Runs After**: Full suite completes
- **Status Check**: Verifies full suite passed
- **Output**: Deployment approval/rejection report
- **Behavior**: Fails if any suite test fails

---

## Job Classification Matrix

| Job | Trigger | Frequency | Failure Action | Block Merge | Block Deploy |
|-----|---------|-----------|----------------|-------------|--------------|
| **Backend Fast** | Every push | Per commit | Report | No | No |
| **Backend Coverage** | Every push | Per commit | Block | Yes | Yes |
| **Admin Fast** | Every push | Per commit | Report | No | No |
| **Admin Full** | Every push | Per commit | Block | Yes | Yes |
| **Engine Fast** | Every push | Per commit | Report | No | No |
| **Engine Full** | Every push | Per commit | Report (17/18 waived) | No | No |
| **Security** | Every push | Per commit | Block | Yes | Yes |
| **Contracts** | Every push | Per commit | Block | Yes | Yes |
| **Bridge Contracts** | Every push | Per commit | Block | Yes | Yes |
| **Full Suite** | Release only | Per release | Block | N/A | Yes |
| **Pre-Deploy Report** | Release only | Per release | Block | N/A | Yes |

---

## Execution Flow

### PR / Feature Branch Flow
```
On push to feature branch:
├── Backend Tests (fast + coverage)
├── Admin Tests (fast + full)
├── Engine Tests (fast + full)
└── Quality Gates (security + contracts + bridge)
    └── Quality Gate Report
```

**Total Time**: ~100-150 seconds (parallel execution)
**Merge Requirement**: All jobs must pass

### Main/Master Branch Flow
```
On push to main/master:
├── All PR checks (same as above)
└── Pre-Deployment Full Suite
    ├── Backend full + coverage
    ├── Admin full
    ├── Engine full
    └── Pre-Deployment Report
        └── Approve/Reject deployment
```

**Total Time**: ~150-250 seconds (sequential)
**Deployment Requirement**: Pre-deployment report must pass

---

## Coverage Enforcement Strategy

### Backend Coverage

| Threshold | Type | Enforcement |
|-----------|------|-------------|
| 85% | Hard gate | Pytest `--cov-fail-under=85` in backend-coverage-tests job |
| Failure Behavior | Hard block | Job fails if coverage < 85%; blocks merge |
| Codecov Integration | Optional | Coverage uploaded to codecov.io for historical tracking |

### Admin Coverage

| Threshold | Type | Enforcement |
|-----------|------|-------------|
| None specified | Soft reference | Current baseline: 96.67% (documented, not enforced) |
| Failure Behavior | Not enforced | No coverage gate; all tests pass if job succeeds |

### Engine Coverage

| Threshold | Type | Enforcement |
|-----------|------|-------------|
| None specified | Soft reference | Current baseline: 96.96% (documented, not enforced) |
| Failure Behavior | Soft gate (waived) | 18 known test isolation failures acceptable; see XFAIL_POLICY.md |

---

## Caching Strategy

All workflows use GitHub Actions native Python caching:

```yaml
cache: 'pip'  # Automatically caches pip dependencies
```

**Benefits**:
- Dependency installation time reduced from ~30s to ~5s
- Cache invalidates when `requirements-dev.txt` changes
- Separate caches for each Python version

---

## Artifact Retention

| Artifact | Retention | Workflow |
|----------|-----------|----------|
| Fast test results | 30 days | Backend, Admin, Engine |
| Coverage test results | 30 days | Backend only |
| Quality gate results | 30 days | Quality Gate |
| Full suite results | 60 days | Pre-Deployment |

**Storage**: GitHub Actions artifact storage (included in plan)

---

## Required Environment Variables / Secrets

### Codecov Integration

Only needed for coverage upload (currently non-blocking):

```
CODECOV_TOKEN: <token>  (Optional, for codecov.io integration)
```

**Current Status**: Non-blocking if missing (coverage reports still generated locally)

---

## Failure Scenarios and Recovery

### Test Failure in Fast Suite

**Scenario**: Backend fast tests fail

**Steps to Recover**:
1. Review test output in GitHub Actions
2. Run locally: `cd backend && pytest tests/ -m "not slow" -v`
3. Fix code or test
4. Push fix (automatically re-runs workflow)

### Coverage Failure

**Scenario**: Backend coverage below 85%

**Steps to Recover**:
1. Generate coverage report: `cd backend && pytest tests/ --cov=app --cov-report=html`
2. Review uncovered code in `htmlcov/index.html`
3. Add tests to cover the code
4. Verify: `pytest tests/ --cov=app --cov-fail-under=85`
5. Push changes

### Engine Test Isolation Failure

**Scenario**: Engine full suite has unexpected failures (more than 18)

**Steps**:
1. Run in isolation: `pytest tests/test_file.py::test_function -v`
2. If passes in isolation: Test isolation issue (documented)
3. If fails in isolation: New bug (requires fix)
4. Update XFAIL_POLICY.md if waiver needed

---

## Local Development Integration

Developers should run quality gates locally before pushing:

```bash
# Fast validation (matches what CI will run)
./scripts/run-quality-gates.sh fast-all

# Pre-deployment validation
./scripts/run-quality-gates.sh pre-deploy

# Specific suite validation
./scripts/run-quality-gates.sh backend-coverage
```

**Recommendation**: Add pre-commit hook to run fast gates automatically.

---

## Continuous Improvement

### Monitoring

Track workflow metrics in GitHub Actions dashboard:
- Average job duration (identify slow tests)
- Failure rate by job (identify unstable tests)
- Cache hit rate (optimize dependencies)

### Optimization

If jobs take longer than expected:
1. Identify slowest tests: `pytest --durations=10`
2. Mark slow tests appropriately: `@pytest.mark.slow`
3. Consider splitting jobs further
4. Increase machine specs if necessary (currently ubuntu-latest = 4 CPU, 16GB RAM)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-25 | Initial CI workflow definition; 5 workflows, 12 jobs, coverage enforcement |

---

## Quick Reference

### Workflow Files
- `.github/workflows/backend-tests.yml` - Backend fast + coverage
- `.github/workflows/admin-tests.yml` - Admin fast + full
- `.github/workflows/engine-tests.yml` - Engine fast + full
- `.github/workflows/quality-gate.yml` - Security + contracts + bridge
- `.github/workflows/pre-deployment.yml` - Full suite for releases

### Key Commands (Local Development)
```bash
# Match CI fast gates
./scripts/run-quality-gates.sh fast-all

# Match CI quality gates
./scripts/run-quality-gates.sh security
./scripts/run-quality-gates.sh contracts
./scripts/run-quality-gates.sh bridge

# Match CI full suite
./scripts/run-quality-gates.sh full-all
```

### Coverage Enforcement
- **Backend**: 85% (hard gate, enforced in CI)
- **Admin**: None (soft baseline: 96.67%)
- **Engine**: None (soft baseline: 96.96%, 18 waived failures)

### Hard Gates (Block Merge)
1. Backend coverage < 85%
2. Backend test failure (any test)
3. Admin test failure (any test)
4. Security test failure (any test)
5. Contract test failure (any test)
6. Bridge contract test failure (any test)

### Soft Gates (Informational)
1. Engine test failure (97.7%+ acceptable; 18 known isolation failures waived)

---

## See Also

- `QUALITY_GATES.md` - Quality gate definitions and thresholds
- `TEST_EXECUTION_PROFILES.md` - Manual test execution patterns
- `XFAIL_POLICY.md` - Known failures and waivers
- `scripts/run-quality-gates.sh` - Local quality gate runner
