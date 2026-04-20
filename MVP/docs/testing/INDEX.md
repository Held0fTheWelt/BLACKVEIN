# World of Shadows Testing Documentation Index

**Project**: World of Shadows v0.1.10
**Scope**: Comprehensive Test Expansion WAVE 0
**Status**: ✅ COMPLETE
**Date**: 2026-03-25

---

## Documentation Hierarchy

### Level 1: Start Here
- **[README.md](README.md)** - Overview of all testing documentation
  - Quick introduction to each document
  - File organization guide
  - Current vs target test counts
  - Implementation timeline

### Level 2: Implementation Guides
- **[ADMIN_TOOL_TARGET_TEST_MATRIX.md](ADMIN_TOOL_TARGET_TEST_MATRIX.md)** - Flask frontend testing
  - 8 test layers
  - 147 target tests (current: 88)
  - Security guarantees and contracts
  - Use when: Adding tests to administration-tool/

- **[WORLD_ENGINE_TARGET_TEST_MATRIX.md](WORLD_ENGINE_TARGET_TEST_MATRIX.md)** - FastAPI engine testing
  - 9 test layers
  - 274 target tests (current: 117)
  - WebSocket and persistence contracts
  - Use when: Adding tests to world-engine/

### Level 3: Quick Reference
- **[MATRIX_QUICK_REFERENCE.md](MATRIX_QUICK_REFERENCE.md)** - Rapid lookup guide
  - Marker quick reference
  - Command examples
  - Test finding strategies
  - Implementation checklist
  - Common pitfalls
  - Use for: Quick answers during implementation

### Level 4: Execution Strategy
- **[TEST_EXECUTION_PROFILES.md](TEST_EXECUTION_PROFILES.md)** - How to run tests
  - Local development profiles
  - CI/CD integration
  - Performance optimization
  - Use for: Choosing right test execution strategy

- **[QUALITY_GATES.md](QUALITY_GATES.md)** - Quality standards and thresholds
  - Coverage thresholds per suite (Backend 85%, Admin/Engine documented)
  - Gate definitions and failure procedures
  - CI/CD workflow examples
  - Use for: Understanding quality requirements and automation

---

## Quick Navigation

### By Role

**Test Implementation Engineer**:
1. Start: [README.md](README.md) - Get overview
2. Reference: [ADMIN_TOOL_TARGET_TEST_MATRIX.md](ADMIN_TOOL_TARGET_TEST_MATRIX.md) or [WORLD_ENGINE_TARGET_TEST_MATRIX.md](WORLD_ENGINE_TARGET_TEST_MATRIX.md)
3. Quick lookup: [MATRIX_QUICK_REFERENCE.md](MATRIX_QUICK_REFERENCE.md)

**Project Manager**:
1. Status: Key Metrics at a Glance (below)
2. Timeline: Implementation Phases in test matrices
3. Metrics: Test Coverage Summary tables

**DevOps/CI Engineer**:
1. Gates: [QUALITY_GATES.md](QUALITY_GATES.md) - Quality requirements
2. Execution: [TEST_EXECUTION_PROFILES.md](TEST_EXECUTION_PROFILES.md)
3. Scripts: `scripts/run-quality-gates.sh` - Automated execution
4. Commands: [MATRIX_QUICK_REFERENCE.md](MATRIX_QUICK_REFERENCE.md) - Marker Reference

**Security Reviewer**:
1. Admin Tool: [ADMIN_TOOL_TARGET_TEST_MATRIX.md](ADMIN_TOOL_TARGET_TEST_MATRIX.md) - Layer 4-5 (Security)
2. World Engine: [WORLD_ENGINE_TARGET_TEST_MATRIX.md](WORLD_ENGINE_TARGET_TEST_MATRIX.md) - Layer 1, 6
3. Details: Security Guarantees sections

---

## Key Metrics at a Glance

### Administration Tool (Flask Frontend)
```
Current Tests:  88
Target Tests:   147
Gap:            +59 tests needed
Coverage:       8 layers
Focus:          Security, routing, proxy, i18n
```

### World Engine (FastAPI Engine)
```
Current Tests:  117
Target Tests:   274
Gap:            +157 tests needed
Coverage:       9 layers
Focus:          API contracts, WebSocket, persistence, performance
```

### Overall
```
Total Current:  205 tests
Total Target:   421 tests
Gap:            +216 tests to implement
Timeline:       3-4 months (WAVE 1-3)
```

---

## Test Layers Overview

### Administration Tool (8 Layers)

| Layer | Tests | Focus |
|-------|-------|-------|
| 1. Config & Init | 34 | Secret key, backend URL, session |
| 2. Routing | 37 | Routes, template resolution |
| 3. Proxy | 28 | Request forwarding, security |
| 4. Headers | 13 | CSP, HSTS, security headers |
| 5. Session | 8 | Cookie flags, session config |
| 6. i18n | 11 | Language detection, translations |
| 7. Context | 8 | Template variables, injection |
| 8. Errors | 8 | 404, 500, error mapping |

### World Engine (9 Layers)

| Layer | Tests | Focus |
|-------|-------|-------|
| 1. Config & Auth | 25 | Secrets, database, API keys |
| 2. HTTP API | 53 | Endpoints, schemas, status |
| 3. WebSocket | 34 | Connections, messages, broadcasts |
| 4. Runtime | 47 | Game loop, commands, entities |
| 5. Persistence | 34 | JSON/SQL, snapshots, recovery |
| 6. Security | 34 | Tickets, tokens, authorization |
| 7. Advanced | 25 | Pagination, filtering, caching |
| 8. Performance | 12 | Response times, concurrency |
| 9. Recovery | 10 | Crash recovery, error handling |

---

## Pytest Markers

### All Projects
```
@pytest.mark.unit          - Fast, isolated unit tests
@pytest.mark.integration   - Tests with external dependencies
@pytest.mark.security      - Security validation tests
@pytest.mark.contract      - API contracts and schemas
@pytest.mark.slow          - Slow tests (separate from CI)
```

### World Engine Specific
```
@pytest.mark.websocket     - WebSocket functionality tests
@pytest.mark.persistence   - Storage, snapshots, recovery
```

### Admin Tool Specific
```
@pytest.mark.browser       - Browser integration (future)
```

---

## Test Execution Profiles

```bash
# Fast development loop (5 seconds)
pytest -m unit

# Before commit (30 seconds)
pytest -m "not slow"

# Full validation (60-120 seconds)
pytest

# Security focus (40 seconds)
pytest -m "security or contract"

# WebSocket only (World Engine, 20 seconds)
pytest -m websocket
```

See [TEST_EXECUTION_PROFILES.md](TEST_EXECUTION_PROFILES.md) for complete profiles.

---

## Implementation Timeline

### WAVE 0: COMPLETE ✅
- ✅ Define 8 test layers (Admin Tool)
- ✅ Define 9 test layers (World Engine)
- ✅ Configure all pytest markers
- ✅ Document security guarantees
- ✅ Establish implementation roadmap

### WAVE 1 (Next: 4-6 weeks)
- Layer 1-2 gaps (~50 new tests)
- Config, auth, HTTP API completeness
- WebSocket foundation

### WAVE 2 (Following: 4-6 weeks)
- Layer 3-5 gaps (~50-80 new tests)
- Proxy security, persistence contracts
- Advanced runtime features

### WAVE 3 (Final: 4-6 weeks)
- Layer 6-9 gaps (~25-40 new tests)
- Advanced contracts, performance SLAs
- Recovery and error scenarios

---

## Security Highlights

### Admin Tool
- ✅ Session: Secure, HttpOnly, SameSite=Lax cookies
- ✅ Secrets: 32+ byte cryptographic random key
- ✅ Proxy: /_proxy/admin/* blocked (403)
- ✅ Headers: Dangerous headers filtered
- ✅ CSP: Inline scripts prevented

### World Engine
- ✅ Secrets: PLAY_SERVICE_SECRET enforced (32+ bytes)
- ✅ API Key: X-Play-Service-Key required
- ✅ Tickets: JWT with TTL and signature validation
- ✅ WebSocket: Ticket validation on handshake
- ✅ Isolation: Per-participant data separation

---

## File Locations

### Documentation Files
```
docs/testing/
├── INDEX.md                              (this file)
├── README.md                             (start here)
├── ADMIN_TOOL_TARGET_TEST_MATRIX.md      (Flask testing guide)
├── WORLD_ENGINE_TARGET_TEST_MATRIX.md    (FastAPI testing guide)
├── MATRIX_QUICK_REFERENCE.md             (quick lookup)
├── TEST_EXECUTION_PROFILES.md            (execution strategies)
├── QUALITY_GATES.md                      (quality standards)
├── XFAIL_POLICY.md                       (known failures)
└── WAVE_9_VALIDATION_REPORT.md           (validation results)
```

### Configuration Files
```
administration-tool/pytest.ini            (6 markers configured)
world-engine/pytest.ini                   (8 markers configured)
backend/pytest.ini                        (7 markers configured)
```

### Test Directories
```
administration-tool/tests/                (~20 test files, 767 tests)
world-engine/tests/                       (~30 test files, 150+ tests)
backend/tests/                            (~7 test suites, 429 tests)
```

---

## Navigation Help

### "I need to add tests to administration-tool"
1. Read: [README.md](README.md) - Overview
2. Reference: [ADMIN_TOOL_TARGET_TEST_MATRIX.md](ADMIN_TOOL_TARGET_TEST_MATRIX.md) - Find your layer
3. Check: [MATRIX_QUICK_REFERENCE.md](MATRIX_QUICK_REFERENCE.md) - Implementation checklist

### "I need to add tests to world-engine"
1. Read: [README.md](README.md) - Overview
2. Reference: [WORLD_ENGINE_TARGET_TEST_MATRIX.md](WORLD_ENGINE_TARGET_TEST_MATRIX.md) - Find your layer
3. Check: [MATRIX_QUICK_REFERENCE.md](MATRIX_QUICK_REFERENCE.md) - Implementation checklist

### "I need to run tests efficiently"
1. See: [TEST_EXECUTION_PROFILES.md](TEST_EXECUTION_PROFILES.md) - Choose your profile
2. Quick commands: [MATRIX_QUICK_REFERENCE.md](MATRIX_QUICK_REFERENCE.md) - Marker Reference

### "I need project status"
1. Check: Implementation Timeline section below
2. Review: Key Metrics in README.md

### "I need quick answers"
1. Check: [MATRIX_QUICK_REFERENCE.md](MATRIX_QUICK_REFERENCE.md) - Common questions section
2. Search: Matrix files for specific components

---

## Key Guarantees

### All Tests
- ✅ No TODOs or placeholders
- ✅ No hardcoded values
- ✅ Proper marker configuration
- ✅ Clear security expectations
- ✅ Negative test cases specified

### Security Tests
- ✅ Covers all authentication paths
- ✅ Tests authorization enforcement
- ✅ Validates input sanitization
- ✅ Checks error message safety
- ✅ Verifies secret non-exposure

### Contract Tests
- ✅ Response schema validation
- ✅ Status code verification
- ✅ Type safety checks
- ✅ Field presence validation
- ✅ Edge case coverage

---

## Getting Started Checklist

- [ ] Read [README.md](README.md) for overview
- [ ] Choose your project (Admin Tool or World Engine)
- [ ] Review relevant TARGET_TEST_MATRIX.md
- [ ] Bookmark [MATRIX_QUICK_REFERENCE.md](MATRIX_QUICK_REFERENCE.md)
- [ ] Check [TEST_EXECUTION_PROFILES.md](TEST_EXECUTION_PROFILES.md) for your workflow
- [ ] Review Implementation Timeline section for timeline
- [ ] Start implementing WAVE 1 tests (Layer 1-2)

---

## Questions?

**Documentation Issue**: File a GitHub issue referencing the document
**Test Implementation**: See [MATRIX_QUICK_REFERENCE.md](MATRIX_QUICK_REFERENCE.md) - Common Pitfalls
**Timeline Question**: See Implementation Timeline section above
**Marker Question**: Run `pytest --markers` in project directory

---

**WAVE 0 Status**: ✅ COMPLETE
**Last Updated**: 2026-03-25
**Next Phase**: WAVE 1 Implementation (Layer 1-2 gaps)
