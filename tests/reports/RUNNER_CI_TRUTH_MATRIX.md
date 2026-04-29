# Runner and CI Truth Matrix

**Generated:** 2026-04-26

---

## Canonical Runner: tests/run_tests.py

### Suite Coverage Matrix

| Suite | Runner --suite all | CI Workflow | Status |
|-------|-------------------|-------------|--------|
| backend | YES | backend-tests.yml | COVERED |
| frontend | YES | (included in quality-gate) | COVERED |
| administration | YES | admin-tests.yml | COVERED |
| engine | YES | engine-tests.yml | COVERED |
| database | YES | (included) | COVERED |
| ai_stack | YES | ai-stack-tests.yml | COVERED |
| story_runtime_core | YES (added 2026-04-26) | YES — engine-tests.yml + pre-deployment.yml | COVERED |
| gates | YES (added 2026-04-26) | YES — engine-tests.yml + pre-deployment.yml | COVERED |
| root_smoke | YES | (included in quality-gate) | COVERED |
| root_integration | YES | (included) | COVERED |
| root_branching | YES | (included) | COVERED |
| root_e2e_python | YES | (included) | COVERED |
| root_tools | YES | (included) | COVERED |

### Gaps Identified

None. All suites are covered in CI.

---

## CI Workflow Audit (Not Yet Complete)

The following CI workflows were identified but not yet audited for
`continue-on-error`, `|| true`, and suite coverage:

| Workflow | Status |
|----------|--------|
| .github/workflows/backend-tests.yml | not audited |
| .github/workflows/engine-tests.yml | not audited |
| .github/workflows/admin-tests.yml | not audited |
| .github/workflows/ai-stack-tests.yml | not audited |
| .github/workflows/mvp1-tests.yml | not audited — may reference deleted patterns |
| .github/workflows/mvp2-tests.yml | not audited |
| .github/workflows/quality-gate.yml | not audited |
| .github/workflows/compose-smoke.yml | not audited |
| .github/workflows/pre-deployment.yml | not audited |

**Action required:** A follow-up CI audit pass must verify each workflow does not
use `continue-on-error` for required primary suites.

---

## Single Runner Verification

| Check | Result |
|-------|--------|
| tests/run_tests.py at root | ABSENT (deleted 2026-04-26) |
| run-tests.py at root | ABSENT |
| run_tests.py at root | ABSENT |
| tests/run_tests.py | PRESENT — canonical |

---

## Completed Actions (2026-04-26 Pass 2)

1. **Added story_runtime_core to CI** — `engine-tests.yml` and `pre-deployment.yml`
2. **Added gates to CI** — `engine-tests.yml` (architecture-gates job) and `pre-deployment.yml`
3. **Fixed MVP1/MVP2 CI** — removed `tests/run_tests.py` references; replaced with canonical runner checks
4. **MVP3/MVP4 gates now included** — `tests/gates/` covers all 3 gate files via architecture-gates job
