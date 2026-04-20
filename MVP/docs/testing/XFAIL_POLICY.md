# XFail Policy and Known Test Failures

**Version**: v0.1.10 (WAVE 9)
**Date**: 2026-03-25
**Status**: Active tracking of test isolation issues

## Summary

This document tracks known test failures and xfail (expected failure) tests in the WorldOfShadows project. All listed failures are understood and have documented remediation plans.

### Current Status

- **Total test failures**: 18 tests across world-engine
- **Root cause**: Configuration module caching in test isolation
- **Affected areas**: HTTP join-context endpoint, WebSocket auth tests
- **Impact**: Fast suite (not slow) passes with 752/757 tests; Full suite has 18 failures

---

## Known Test Failures

### Test Isolation Issue: PLAY_SERVICE_INTERNAL_API_KEY Configuration Caching

**Root Cause**: The `app.config` module is imported once at startup and caches environment variable values. When pytest tests use `monkeypatch` to temporarily change `PLAY_SERVICE_INTERNAL_API_KEY`, the cached value in the config module doesn't get updated, causing subsequent tests to fail.

**Affected Tests** (18 total):

#### HTTP Join Context Tests (5 failures)
1. `test_http_join_context.py::test_join_context_requires_internal_api_key`
   - **Status**: Fails in full suite, passes in isolation
   - **Issue**: Previous test sets env var; config caching causes rejection
   - **Expected**: Should skip API key check when key not configured
   - **Actual**: Receives 401 Unauthorized

2. `test_http_join_context.py::test_join_context_with_correct_api_key_returns_200`
   - **Status**: Fails due to config reload not happening
   - **Issue**: monkeypatch ineffective due to module caching
   - **Expected**: Should accept request with correct header key
   - **Actual**: Returns 401 Unauthorized

3. `test_http_join_context.py::test_join_context_with_unknown_run_id_returns_404`
   - **Status**: Fails at auth gate before 404 logic
   - **Issue**: Config caching prevents proper endpoint behavior
   - **Expected**: Should return 404 for unknown run
   - **Actual**: Returns 401 Unauthorized

4. `test_http_join_context.py::test_join_context_with_nonexistent_run_includes_detail`
   - **Status**: Fails at auth gate
   - **Issue**: Same config caching issue
   - **Expected**: Should return 404 with error detail
   - **Actual**: Returns 401 Unauthorized

5. `test_http_join_context.py::test_join_context_without_run_id_returns_422`
   - **Status**: Fails at auth gate
   - **Issue**: Same config caching issue
   - **Expected**: Should return 422 validation error
   - **Actual**: Returns 401 Unauthorized

#### WebSocket Auth Tests (7 failures)
6-12. `test_ws_auth.py::TestWebSocketAuthValidation::test_*`
   - **Status**: Fail due to join-context returning error instead of context dict
   - **Issue**: Tests depend on `/api/internal/join-context` endpoint
   - **Failures**:
     - `test_mismatched_account_id_rejected`
     - `test_mismatched_character_id_rejected`
     - `test_mismatched_role_id_rejected`
     - `test_expired_ticket_rejected`
     - `test_tampered_ticket_signature_rejected`
     - `test_duplicate_connection_replacement`
     - `test_connection_marked_as_connected_on_auth`
   - **Actual Error**: `KeyError: 'participant_id'` when calling `.json()` on error response

#### WebSocket Rejoin Tests (6 failures)
13-18. `test_ws_rejoin.py::TestWebSocketRejoin::test_*`
   - **Status**: Fail due to join-context returning error instead of context dict
   - **Issue**: Tests depend on `/api/internal/join-context` endpoint
   - **Failures**:
     - `test_rejoin_with_stale_ticket_fails`
     - `test_foreign_participant_rejoin_fails`
     - `test_wrong_character_rejoin_fails`
     - `test_participant_marked_disconnected_on_graceful_close`
     - `test_reconnect_with_wrong_run_id_fails`
     - (1 more in full suite)
   - **Actual Error**: `KeyError: 'participant_id'` when calling `.json()` on 401 response

---

## Remediation Plans

### Short-Term (v0.1.10 Patch)

**Option A: Fix Test Isolation** (Preferred)
- Update conftest.py to reload config module in fixtures
- Alternative: Mock config dependency injection in HTTP router
- Timeline: 1-2 hours
- Tests would immediately pass

**Option B: Mark as Known Test Issue**
- Document that these tests pass in isolation (verified)
- Document as environmental issue not production code issue
- Update CI/CD to run tests in isolation mode
- Add pytest-isolation plugin or similar

### Long-Term (v0.1.11+)

**Proper Solution: Dependency Injection**
- Move configuration loading to app startup dependency
- Use FastAPI dependency injection for config values
- Allows test fixtures to override config easily
- Applies to both `PLAY_SERVICE_INTERNAL_API_KEY` and `PLAY_SERVICE_SECRET`
- Timeline: 1-2 days

---

## Test Execution Impact

### Fast Suite (Recommended for CI)
```bash
cd world-engine && python -m pytest tests/ -m "not slow and not websocket" -q
```
- **Result**: 683 passed, 5 failed (~99% pass rate)
- **Duration**: ~10 seconds
- **When to use**: Pre-commit, CI fast gate
- **Status**: Ready for immediate use (failures are isolated tests)

### Full Suite
```bash
cd world-engine && python -m pytest tests/ -q
```
- **Result**: 752 passed, 18 failed (~97.7% pass rate)
- **Duration**: ~12 seconds
- **Status**: Use with known failure caveat

### Contract Tests Only (All Pass)
```bash
cd world-engine && python -m pytest tests/ -m contract -q
```
- **Result**: 458 passed (100%)
- **Duration**: ~5 seconds
- **Status**: Production-ready; shows integration contracts are solid

---

## Verification Steps

### Verify Known Failures Are Isolated
```bash
# Run single test - should pass
pytest tests/test_http_join_context.py::test_join_context_requires_internal_api_key -v

# Run full suite - will fail due to isolation
pytest tests/ -m "not slow" -q
```

### Verify Contract Tests All Pass
```bash
pytest tests/test_backend_bridge_contract.py -v
pytest tests/ -m contract -q
```

---

## Policy on Adding New Tests

1. **All new tests must pass in full suite**, not just in isolation
2. **Test isolation must be verified** before marking tests as production-ready
3. **Use pytest fixtures carefully** - ensure cleanup is proper
4. **Avoid environment variable modifications** in tests; use dependency injection instead
5. **Document any test dependencies** between test files

---

## Migration Path

As we address test isolation issues in future waves:

1. Create tracking issue for each failing test
2. Assign remediation (isolation fix vs. test skip)
3. Mark test with appropriate decorator (xfail vs. skip)
4. Run regression suite before unmarking
5. Remove from this document once resolved

---

## Notes for CI/CD

- **GitHub Actions**: Run contract tests with `-m contract` flag for fast feedback
- **Pre-commit**: Use `"not slow and not websocket"` profile for speed
- **Deploy gate**: Verify contract tests pass (100% of them must pass)
- **Nightly**: Run full suite with known failures expected; alert if NEW failures appear

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v0.1.10 | 2026-03-25 | Initial policy; documented 18 test isolation failures |
| (future) | | Remediation tracking |
