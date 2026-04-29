# Legacy Runner and CI Artifacts

**Generated:** 2026-04-26

---

## Root Runner (DELETED)

| File | Status | Action |
|------|--------|--------|
| tests/run_tests.py (repo root) | DELETED | Removed — forbidden root runner |

`tests/run_tests.py` was a wrapper around `tests/run_tests.py` that violated the single-runner
requirement. It has been deleted. All test invocation must use `tests/run_tests.py` directly.

---

## Canonical Runner (UPDATED)

| File | Status |
|------|--------|
| tests/run_tests.py | ACTIVE — canonical runner |

Updates made:
- Added `story_runtime_core` suite (was silently excluded from `--suite all`)
- Added `gates` suite (was silently excluded from `--suite all`)
- Both suites added to `ALL_SUITE_SEQUENCE`
- `gates` added to backend stack probe requirements

---

## CI Workflows Reviewed

| Workflow | Status | Notes |
|----------|--------|-------|
| .github/workflows/backend-tests.yml | needs_review | Not audited in this pass |
| .github/workflows/engine-tests.yml | needs_review | Not audited in this pass |
| .github/workflows/admin-tests.yml | needs_review | Not audited in this pass |
| .github/workflows/ai-stack-tests.yml | needs_review | Not audited in this pass |
| .github/workflows/mvp1-tests.yml | needs_review | MVP1 specific — may reference deleted patterns |
| .github/workflows/mvp2-tests.yml | needs_review | MVP2 specific |
| .github/workflows/quality-gate.yml | needs_review | Quality gate |
| .github/workflows/compose-smoke.yml | needs_review | Compose smoke |
| .github/workflows/pre-deployment.yml | needs_review | Pre-deployment |

CI workflows were not modified in this cleanup pass. A follow-up CI audit is required
to verify that CI mirrors `tests/run_tests.py --suite all` exactly and does not use
`continue-on-error` for required gates.

---

## Root-Level Runner Variants

| Pattern | Status |
|---------|--------|
| tests/run_tests.py | DELETED |
| run-tests.py | NOT FOUND (was never present) |
| run_tests.py (root) | NOT FOUND (was never present) |
| tests/run_tests.py | ACTIVE — canonical |

---

## smoke/compose_smoke

| File | Status |
|------|--------|
| tests/smoke/compose_smoke/ | Optional external lane — not a primary gate |
| tests/smoke/compose_smoke/smoke_curl.sh | Exists — requires docker compose v2 |

---

## setup-test-environment scripts

| File | Status |
|------|--------|
| setup-test-environment.sh | ACTIVE — installs all test dependencies |
| setup-test-environment.bat | ACTIVE — Windows equivalent |
| run-smoke-tests.sh | needs_review — may reference deleted patterns |
| run-smoke-tests.bat | needs_review — may reference deleted patterns |
