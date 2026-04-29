# Release Gate Policy

**Version**: 1.0
**Date**: 2026-03-25
**Status**: ACTIVE

This document defines release governance, promotion criteria, and quality gates for production deployments.

---

## Release Promotion Pipeline

```
Development (PR)
  → Quality Gate 1 (Fast Tests)
  → Quality Gate 2 (Full Suite + Coverage)
  → Quality Gate 3 (Security)
  → Quality Gate 4 (Contracts)
  → Staging
  → Quality Gate 5 (Smoke Tests)
  → Production
```

---

## Quality Gate Definitions

### Gate 1: Fast Tests (Pre-Merge)

**When**: Every PR/commit
**Required For**: Merge to master
**Command**:
```bash
python run_tests.py --suite all --quick
```

**Acceptance Criteria**:
- Backend: 1,900+ tests, 100% pass rate
- Admin: 1,000+ tests, 100% pass rate
- Engine: 683 tests, 99%+ pass rate
- Duration: <45s
- **Type**: HARD GATE (blocks merge)

**Failure Response**:
1. Identify failed test
2. Run in isolation: `pytest tests/test_file.py::TestClass::test_name -vv`
3. Fix code or test
4. Re-run gate
5. Comment on PR with fix justification

---

### Gate 2: Full Suite + Coverage (Pre-Merge)

**When**: Before master merge
**Required For**: Production merge
**Command**:
```bash
python run_tests.py --suite all --coverage
```

**Acceptance Criteria**:
- Backend: 1,950+ tests, 100% pass rate, 85%+ coverage
- Admin: 1,039 tests, 100% pass rate
- Engine: 788 tests, 97.7%+ pass rate (18 known failures documented)
- Coverage measurement: Backend 85% hard gate
- Duration: <150s
- **Type**: HARD GATE (blocks merge to main)

**Coverage Failure Response**:
1. Generate coverage report: `cd backend && pytest --cov=app --cov-report=html`
2. Open `htmlcov/index.html`
3. Identify uncovered lines
4. Write unit/integration tests
5. Verify coverage increases to 85%+
6. Re-run gate

---

### Gate 3: Security Tests (Pre-Merge)

**When**: For any auth/security changes
**Required For**: Merge if code touched auth/security
**Command**:
```bash
pytest -m security -v --tb=short
```

**Acceptance Criteria**:
- Total: 219+ security tests
- Pass Rate: 100% (0 failures)
- Duration: <25s
- No authentication bypasses
- No authorization violations
- **Type**: HARD GATE (blocks merge if touched)

**Scope**:
- Backend security: 49+ tests
- Admin security: 56+ tests
- Engine security: 114+ tests

**Failure Response**:
1. Review test to understand what's being validated
2. Check if code fix or test fix is needed
3. For auth bypass: FIX CODE IMMEDIATELY (security issue)
4. For test issue: document why test is wrong, get review
5. Re-run gate

---

### Gate 4: Contract Tests (Pre-Merge)

**When**: For any API changes
**Required For**: Merge if API touched
**Command**:
```bash
pytest -m contract -v --tb=short
```

**Acceptance Criteria**:
- Total: 900+ contract tests
- Pass Rate: 100% (0 failures)
- Duration: <35s
- No API signature changes
- No response format changes
- **Type**: HARD GATE (blocks merge if touched)

**Scope**:
- Backend contracts: 215+ tests
- Admin contracts: 228+ tests
- Engine contracts: 458 tests

**Failure Response**:
1. Review which API contracts failed
2. Determine if contract change is intentional
3. If intentional: Update contract tests AND API consumers
4. If regression: Fix code to match contract
5. Re-run gate

---

### Gate 5: Smoke Tests (Pre-Staging)

**When**: Before staging deployment
**Required For**: Staging promotion
**Command**:
```bash
python run_tests.py --suite all --quick && \
pytest -m "contract or (security and unit)" -v
```

**Acceptance Criteria**:
- Fast tests: All 3,500+ pass
- Contract tests: 900+ pass
- Security tests: 100+ pass
- Duration: <60s
- **Type**: SOFT GATE (warning, can override with justification)

**Failure Response**:
1. Investigate specific failure
2. If regression: Fix code before staging
3. If known issue: Verify documented in XFAIL_POLICY.md
4. Get approval from tech lead
5. Proceed to staging with documented override

---

## Release Candidate (RC) Validation

### Pre-RC Checklist

Before cutting a release candidate:

- [ ] All code changes merged to master
- [ ] All PRs closed and merged
- [ ] Fast tests: 100% pass
- [ ] Full suite: 100% pass (backend+admin), 97.7%+ (engine)
- [ ] Coverage: Backend 85%+
- [ ] Security tests: 100% pass
- [ ] Contract tests: 100% pass
- [ ] No new XFAIL entries since last release
- [ ] CHANGELOG.md updated
- [ ] Version bumped in all packages
- [ ] Release notes drafted

### RC Promotion Command

```bash
# Run full validation
python run_tests.py --suite all --coverage && \
pytest -m "security or contract" -v --tb=short && \
echo "RC validation complete - ready for promotion"
```

### RC Acceptance Criteria

**Must Have**:
- Backend: 1,950+ tests, 100% pass, 85%+ coverage
- Admin: 1,039 tests, 100% pass
- Engine: 788 tests, 97.7%+ pass
- Security: 219+ tests, 100% pass
- Contracts: 900+ tests, 100% pass

**Should Have**:
- All performance targets met
- All metrics stable vs baseline
- No regression in test count
- Documentation updated
- CHANGELOG complete

---

## Production Promotion

### Pre-Production Checklist

Before promoting RC to production:

- [ ] RC validation passed
- [ ] Staging smoke tests passed
- [ ] Load testing completed
- [ ] Rollback plan documented
- [ ] Database migration validated
- [ ] API consumers notified of changes
- [ ] Monitoring alerts configured
- [ ] On-call engineer assigned
- [ ] Release window scheduled

### Production Promotion Command

```bash
# Final validation before production
python run_tests.py --suite all --quick && \
pytest -m "contract" -v --tb=short && \
echo "Production validation complete - ready for deployment"
```

### Deployment Validation

After deployment to production:

1. **Health Checks** (first 5 minutes)
   - API responding
   - Database connectivity
   - Cache connectivity
   - Log aggregation working

2. **Smoke Tests** (first 30 minutes)
   - User registration works
   - Login works
   - Core API endpoints responding
   - No 5xx errors in logs

3. **Metrics Monitoring** (first 24 hours)
   - Error rate baseline
   - Response time baseline
   - Resource utilization baseline
   - Known issue tracking

---

## Rollback Procedure

### Automatic Rollback Triggers

Rollback automatically if any of these occur in first 5 minutes:
- 5xx error rate > 1%
- API response time > 5s (p95)
- Database connectivity lost
- Cache completely unavailable

### Manual Rollback Triggers

Consider manual rollback if:
- Unexpected behavior in production
- Data corruption detected
- Critical security issue discovered
- Customer impact confirmed

### Rollback Steps

```bash
# 1. Identify bad commit
git log --oneline | head -5

# 2. Create hotfix branch
git checkout -b hotfix/rollback-VERSION

# 3. Revert problematic commits
git revert <COMMIT_HASH>

# 4. Run validation
python run_tests.py --suite all --quick

# 5. Promote to production
# (CI will auto-deploy when merged to main)
```

---

## Gate Waiver Process

### When to Request a Waiver

Waivers are ONLY for:
1. Known documented issues (XFAIL_POLICY.md)
2. Environment-specific failures (not in code)
3. External service issues (not in code)
4. Verified false-positive tests

### Waiver NOT Granted For

- New code with low coverage (<85% backend)
- New test failures without root cause investigation
- Skipping security tests
- Known code quality issues
- Performance regressions

### Waiver Request Process

1. File issue: `[WAIVER] Gate: <gate_name>`
2. Provide evidence:
   - Why gate is failing
   - Why it's not a code issue
   - Testing performed
   - Risk assessment
3. Get approval from:
   - Tech lead (code quality)
   - Security team (if security gate)
   - DevOps (if infrastructure gate)
4. Document in XFAIL_POLICY.md with expiration date
5. Remove waiver after fix or expiration

---

## Baseline Stability Requirements

### No Regression Rules

When promoting to production, the following MUST NOT decrease:

1. **Test Count**
   - Backend: >1,900 (fast) / >1,950 (full)
   - Admin: >1,000 (fast) / >1,039 (full)
   - Engine: >650 (fast) / >788 (full)

2. **Pass Rate**
   - Backend: 100%
   - Admin: 100%
   - Engine: 97.7%+ (with documented waivers)

3. **Coverage**
   - Backend: 85%+ (hard gate)
   - Admin: >95% (recommended)
   - Engine: >95% (recommended)

4. **Performance**
   - Fast profile: <45s
   - Full profile: <150s
   - Security profile: <25s

### Waiver Changes Require

- Documentation update to this policy
- Comment in XFAIL_POLICY.md
- Justification in commit message
- Expiration date for temporary waivers

---

## Metrics Tracking

### Dashboard Metrics

Track these in deployment dashboard:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Backend test pass rate | 100% | <99% |
| Admin test pass rate | 100% | <99% |
| Engine test pass rate | 97.7%+ | <97% |
| Backend coverage | 85%+ | <85% |
| Total test count | 3,777+ | <3,700 |
| Fast profile duration | <45s | >60s |
| Full profile duration | <150s | >180s |

### Weekly Review

Every Friday, review:
1. Test count stability
2. Pass rate trends
3. Coverage trends
4. Performance trends
5. New XFAIL entries
6. Waiver expirations

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-25 | Initial release gate policy; 5-gate pipeline |
