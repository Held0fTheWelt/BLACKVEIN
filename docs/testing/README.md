# Testing Documentation

This directory contains testing guidance and target matrices for the World of Shadows project.

**Multi-component test runner:** see **[tests/TESTING.md](../../tests/TESTING.md)** for `tests/run_tests.py` (`--suite`, `--scope`, Makefile).

---

## Documents Overview

### 1. [ADMIN_TOOL_TARGET_TEST_MATRIX.md](ADMIN_TOOL_TARGET_TEST_MATRIX.md)
**For**: Administration Tool (Flask public frontend)
- 8 test layers with 147 target tests
- Security guarantees and negative test cases
- Implementation phases (WAVE 0 → WAVE 3)
- Current: ~88 tests | Target: ~147 tests

**Key Sections**:
- Layer 1: Config & Initialization
- Layer 2: Routing & Template Resolution
- Layer 3: Proxy & Backend Integration
- Layer 4: Security Headers & CSP
- Layer 5: Session & Cookie Security
- Layer 6: Internationalization (i18n)
- Layer 7: Context Processor & Template Globals
- Layer 8: Error Handling & Edge Cases

**Read this if**: You're adding tests to the administration-tool/ directory

---

### 2. [WORLD_ENGINE_TARGET_TEST_MATRIX.md](WORLD_ENGINE_TARGET_TEST_MATRIX.md)
**For**: World Engine (FastAPI game runtime)
- 9 test layers with 274 target tests
- WebSocket, persistence, and performance contracts
- Implementation phases (WAVE 0 → WAVE 3)
- Current: ~117 tests | Target: ~274 tests

**Key Sections**:
- Layer 1: Configuration & Authentication
- Layer 2: HTTP API Layer
- Layer 3: WebSocket API Layer
- Layer 4: Runtime & Game Engine
- Layer 5: Persistence & Storage
- Layer 6: Security & Access Control
- Layer 7: API Contracts & Advanced Scenarios
- Layer 8: Performance & Scalability
- Layer 9: Recovery & Error Handling

**Read this if**: You're adding tests to the world-engine/ directory

---

### 3. [MATRIX_QUICK_REFERENCE.md](MATRIX_QUICK_REFERENCE.md)
**Purpose**: Quick lookup guide for test implementation

**Contents**:
- Layer summary tables
- Marker quick reference (bash commands)
- Test finding guides
- Implementation checklist
- Performance baselines
- Common pitfalls

**Read this for**: Quick answers and common commands

---

### 4. [TEST_EXECUTION_PROFILES.md](TEST_EXECUTION_PROFILES.md)
**Purpose**: Test execution strategies for different scenarios

**Covers**:
- Fast feedback loop (unit tests)
- Integration testing
- Security validation
- Performance testing
- CI/CD integration

**Read this for**: How to run tests efficiently

---

## Quick Start

### Find Tests for a Component
```bash
# By layer name (Administration Tool)
grep -r "Layer 2" docs/testing/ADMIN_TOOL_TARGET_TEST_MATRIX.md

# By test marker (World Engine)
pytest world-engine/tests -m contract --collect-only

# By file pattern
ls administration-tool/tests/test_proxy*.py
```

### Run Tests by Category
```bash
# Fast development loop
pytest -m unit

# Before commit (all except slow)
pytest -m "not slow"

# Security focus
pytest -m "security or contract"

# WebSocket only (World Engine)
pytest -m websocket
```

### Add a New Test
1. Determine the layer (reference appropriate matrix)
2. Choose the test file (follow file organization pattern)
3. Add @pytest.mark decorators (unit/integration/security/contract/etc.)
4. Reference the matrix row in docstring
5. Include negative test case
6. Run `pytest --collect-only` to verify

---

## Pytest Markers

All markers are configured in:
- `administration-tool/pytest.ini`
- `world-engine/pytest.ini`
- `backend/pytest.ini`

### Standard Markers (All Projects)
- `@pytest.mark.unit` - Fast, isolated tests (no external deps)
- `@pytest.mark.integration` - Tests with external dependencies
- `@pytest.mark.security` - Security validation tests
- `@pytest.mark.contract` - API contracts and response schemas
- `@pytest.mark.slow` - Tests that should run separately

### World Engine Specific
- `@pytest.mark.websocket` - WebSocket tests
- `@pytest.mark.persistence` - Storage, snapshots, recovery

### Admin Tool Specific
- `@pytest.mark.browser` - Browser integration (not yet implemented)

---

## Current vs Target Test Counts

### Administration Tool
| Layer | Current | Target | Gap |
|-------|---------|--------|-----|
| Config & Init | 30 | 34 | +4 |
| Routing & Templates | 20 | 37 | +17 |
| Proxy & Backend | 14 | 28 | +14 |
| Security Headers | 10 | 13 | +3 |
| Session & Cookies | 5 | 8 | +3 |
| i18n | 6 | 11 | +5 |
| Context Processor | 1 | 8 | +7 |
| Error Handling | 2 | 8 | +6 |
| **Total** | **88** | **147** | **+59** |

### World Engine
| Layer | Current | Target | Gap |
|-------|---------|--------|-----|
| Config & Auth | 16 | 25 | +9 |
| HTTP API | 27 | 53 | +26 |
| WebSocket | 15 | 34 | +19 |
| Runtime & Engine | 22 | 47 | +25 |
| Persistence & Storage | 17 | 34 | +17 |
| Security & Access | 19 | 34 | +15 |
| API Contracts | 0 | 25 | +25 |
| Performance | 0 | 12 | +12 |
| Recovery & Errors | 1 | 10 | +9 |
| **Total** | **117** | **274** | **+157** |

---

## Implementation Timeline

### WAVE 0 (COMPLETE ✅)
- Define test matrices
- Configure pytest markers
- Document security guarantees
- Establish implementation roadmap

### WAVE 1 (Phase 1)
- Layer 1 & 2: ~50 new tests
- Config validation and routing completeness
- Initial WebSocket contracts

### WAVE 2 (Phase 2)
- Layer 3-5: ~50-80 new tests
- Proxy security hardening
- Persistence contracts

### WAVE 3 (Phase 3)
- Layer 6-9: ~25-40 new tests
- Advanced contracts and performance SLAs
- Recovery scenarios

---

## Security Highlights

### Administration Tool
- Session cookies: Secure, HttpOnly, SameSite=Lax
- Secret key: 32+ bytes, cryptographically random
- Proxy: /_proxy/admin/* always blocked (403)
- Headers: Dangerous headers never forwarded
- CSP: Inline scripts prevented, CDN approved

### World Engine
- Secrets: PLAY_SERVICE_SECRET enforced (32+ bytes)
- API Key: Internal endpoints require X-Play-Service-Key header
- Tickets: JWT with TTL, signature validation
- WebSocket: Ticket validation on handshake
- Isolation: Participants cannot access other players' data

---

## Test File Organization

```
administration-tool/tests/
├── conftest.py
├── test_app_factory.py
├── test_config.py
├── test_config_contract.py
├── test_context_processor.py
├── test_error_responses.py
├── test_forum_routes.py
├── test_i18n.py
├── test_language_resolution.py
├── test_manage_routes.py
├── test_proxy.py
├── test_proxy_contract.py
├── test_proxy_error_mapping.py
├── test_proxy_security.py
├── test_public_routes.py
├── test_routes.py
├── test_routes_contracts.py
├── test_security.py
├── test_security_headers.py
└── test_session_security.py

world-engine/tests/
├── conftest.py
├── test_api.py
├── test_api_advanced_contracts.py
├── test_api_contracts.py
├── test_api_security.py
├── test_backend_bridge_contract.py
├── test_compatibility_contracts.py
├── test_config_contract.py
├── test_config_validation.py
├── test_data_integrity.py
├── test_environment_security.py
├── test_error_contracts.py
├── test_http_api_extended.py
├── test_http_health_and_templates.py
├── test_http_join_context.py
├── test_http_runs.py
├── test_http_snapshot_and_transcript.py
├── test_http_tickets.py
├── test_internal_api_key_guard.py
├── test_performance_contracts.py
├── test_persistence_contracts.py
├── test_recovery_contracts.py
├── test_runtime_commands.py
├── test_runtime_engine.py
├── test_runtime_lobby_rules.py
├── test_runtime_manager.py
├── test_runtime_open_world.py
├── test_runtime_visibility.py
├── test_store.py
└── test_store_json.py
```

---

## Questions & Support

1. **"Which matrix applies to my component?"**
   - Administration Tool (Flask): See ADMIN_TOOL_TARGET_TEST_MATRIX.md
   - World Engine (FastAPI): See WORLD_ENGINE_TARGET_TEST_MATRIX.md

2. **"How do I find tests for X?"**
   - Use MATRIX_QUICK_REFERENCE.md
   - Search by layer, component, or marker

3. **"What markers should I use?"**
   - See pytest.ini in respective project directory
   - Reference MATRIX_QUICK_REFERENCE.md for examples

4. **"How long should tests take?"**
   - Unit: <100ms each
   - Integration: 1-5 seconds each
   - Slow: 10+ seconds (run separately)

5. **"What test structure should I follow?"**
   - Review similar tests in the appropriate layer
   - Include docstring with layer reference
   - Add both positive and negative cases

---

## Related Documents

- [Backend Testing](../backend/tests/) - Backend test suite
- [API Documentation](../api/README.md) - API reference and endpoints
- [Security Guide](../security/README.md) - Security policies and audit
- [Development Guide](../development/README.md) - Development setup and practices

---

**Version**: 0.1.10
**Last Updated**: 2026-03-25
**WAVE 0 Status**: Complete ✅
**Next Phase**: WAVE 1 Implementation
