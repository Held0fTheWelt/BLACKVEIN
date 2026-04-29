# Test Matrix Quick Reference Guide

**Purpose**: Rapidly navigate test coverage expectations and implementation requirements.

---

## Key Documents

1. **ADMIN_TOOL_TARGET_TEST_MATRIX.md** - Flask frontend (administration-tool/)
   - 8 layers, 147 target tests
   - Focus: Security, routing, proxy, i18n
   
2. **WORLD_ENGINE_TARGET_TEST_MATRIX.md** - FastAPI engine (world-engine/)
   - 9 layers, 274 target tests
   - Focus: API contracts, WebSocket, persistence, performance

---

## Test Layers by Project

### Administration Tool (8 Layers)

| Layer | Tests | Type | Focus |
|-------|-------|------|-------|
| 1. Config & Init | 34 | unit, contract | Secret key, backend URL, session setup |
| 2. Routing | 37 | integration, contract | All routes, template resolution |
| 3. Proxy | 28 | integration, security, contract | Request forwarding, admin blocking, headers |
| 4. Security Headers | 13 | security, contract | CSP, X-Frame-Options, HSTS |
| 5. Session & Cookies | 8 | security, integration, contract | Cookie flags, session lifetime |
| 6. i18n | 11 | integration, contract | Language detection, translations |
| 7. Context Processor | 8 | integration, contract | Template variables, config injection |
| 8. Error Handling | 8 | integration, contract | 404, 500, error mapping |

**Total**: ~147 tests across 12-15 test files

### World Engine (9 Layers)

| Layer | Tests | Type | Focus |
|-------|-------|------|-------|
| 1. Config & Auth | 25 | unit, security, contract | Secrets, database URLs, API keys |
| 2. HTTP API | 53 | contract, integration | Endpoints, response schemas, status codes |
| 3. WebSocket | 34 | websocket, contract, integration | Connections, messages, broadcasts |
| 4. Runtime | 47 | unit, integration | Game loop, commands, entities |
| 5. Persistence | 34 | persistence, integration, contract | JSON/SQL stores, snapshots, recovery |
| 6. Security | 34 | security, contract, unit | Tickets, tokens, authorization |
| 7. Advanced Contracts | 25 | contract | Pagination, filtering, idempotency, caching |
| 8. Performance | 12 | slow, integration | Response times, concurrency, memory |
| 9. Recovery & Errors | 10 | integration, persistence | Crash recovery, corruption handling |

**Total**: ~274 tests across 20-25 test files

---

## Quick Marker Reference

```bash
# Run only fast tests (unit + no external deps)
pytest -m unit

# Run integration suite (all layer interactions)
pytest -m integration

# Run security-critical tests
pytest -m "security or contract"

# Run WebSocket tests only (World Engine)
pytest -m websocket

# Run persistence tests (storage, snapshots, recovery)
pytest -m persistence

# Exclude slow/performance tests
pytest -m "not slow"

# Run specific layer (example: Layer 2)
pytest -m contract -k "api"  # World Engine Layer 2
pytest -m "integration and contract" -k "routing"  # Admin Tool Layer 2
```

---

## Finding Specific Tests

### By Security Requirement
```bash
# All security-focused tests
pytest -m security

# Admin Tool: Check proxy blocks admin paths
pytest administration-tool/tests/test_proxy_security.py -v

# World Engine: Check ticket validation
pytest world-engine/tests/test_api_security.py -v
```

### By Layer
```bash
# Admin Tool: Layer 1 (Config)
pytest administration-tool/tests/test_config.py
pytest administration-tool/tests/test_config_contract.py

# World Engine: Layer 5 (Persistence)
pytest world-engine/tests/ -m persistence
```

### By Component
```bash
# Admin Tool: Session management
pytest administration-tool/tests/test_session_security.py -v

# World Engine: WebSocket connections
pytest world-engine/tests/ -m websocket -k "connect"
```

---

## Test Implementation Checklist

When adding a new test:

1. **Choose Layer**: Reference appropriate test matrix
2. **Check Markers**: Apply correct markers (unit/integration/security/contract/etc.)
3. **Add Documentation**: Link test name to matrix row
4. **Implement Negative Case**: Include failure scenario
5. **Verify Status Codes**: Check expected response
6. **Check Security**: Does it touch auth/secrets?
7. **Run Collection**: `pytest --collect-only` passes
8. **Run Test**: `pytest test_file.py::test_name -v`

### Example: Adding a new Admin Tool proxy test

```python
# In administration-tool/tests/test_proxy_security.py

@pytest.mark.security  # Layer 3, proxy security
@pytest.mark.contract  # Response contract
def test_proxy_blocks_upload_to_admin(client, monkeypatch):
    """Layer 3: Proxy & Backend Integration
    
    Verify that POST requests to /_proxy/admin/* return 403.
    Negative test: unauthorized path access blocked.
    """
    # Test implementation
    response = client.post("/_proxy/admin/users", json={"name": "test"})
    assert response.status_code == 403
```

---

## Performance Baselines (World Engine)

From Layer 8 (Performance & Scalability):

```
Health check:            <10ms
List endpoints:          <100ms
Get single resource:     <50ms
Create run:              <500ms
WebSocket message:       <100ms latency
```

Use `pytest -m slow --durations=20` to identify slow tests.

---

## Execution Profiles

### For Local Development
```bash
# Fast feedback loop
pytest -m "unit or (integration and not slow)"

# Before commit
pytest -m "not slow"

# Pre-push (everything)
pytest
```

### For CI Pipeline
```bash
# Quick sanity check (5 min)
pytest -m unit

# Full suite (20 min)
pytest

# Nightly (full + slow tests)
pytest --durations=30
```

---

## File Organization

```
administration-tool/
├── tests/
│   ├── test_config*.py          # Layer 1 (Config)
│   ├── test_routes*.py          # Layer 2 (Routing)
│   ├── test_proxy*.py           # Layer 3 (Proxy)
│   ├── test_security*.py        # Layer 4 (Headers)
│   ├── test_session*.py         # Layer 5 (Sessions)
│   ├── test_*i18n*.py           # Layer 6 (i18n)
│   ├── test_context*.py         # Layer 7 (Context)
│   └── test_error*.py           # Layer 8 (Errors)
└── pytest.ini

world-engine/
├── tests/
│   ├── test_config*.py          # Layer 1 (Config)
│   ├── test_*api*.py            # Layer 2 (HTTP API)
│   ├── test_websocket*.py       # Layer 3 (WebSocket)
│   ├── test_runtime*.py         # Layer 4 (Runtime)
│   ├── test_*persistence*.py    # Layer 5 (Persistence)
│   ├── test_*security*.py       # Layer 6 (Security)
│   ├── test_*contract*.py       # Layer 7 (Advanced)
│   ├── test_performance*.py     # Layer 8 (Performance)
│   └── test_*recovery*.py       # Layer 9 (Recovery)
└── pytest.ini
```

---

## Common Pitfalls

❌ **Don't**: Add new tests without checking the matrix first
✅ **Do**: Reference the specific matrix layer and component

❌ **Don't**: Forget to mark security-critical tests
✅ **Do**: Use `@pytest.mark.security` on auth/secret/access control tests

❌ **Don't**: Make real HTTP calls in unit tests
✅ **Do**: Mock/stub external services in unit layer

❌ **Don't**: Put WebSocket tests in regular integration suite
✅ **Do**: Mark with `@pytest.mark.websocket`

❌ **Don't**: Ignore negative test cases
✅ **Do**: Test both happy path and error paths

---

## Contact & Questions

For questions about test structure:
- See ADMIN_TOOL_TARGET_TEST_MATRIX.md for Flask frontend details
- See WORLD_ENGINE_TARGET_TEST_MATRIX.md for FastAPI engine details
- See README.md for implementation timeline and project status

For implementation help:
- Review existing tests in the appropriate layer
- Follow the naming pattern: `test_component_behavior.py`
- Use fixtures from conftest.py

---

**Last Updated**: 2026-03-25
**WAVE 0 Status**: Complete
**Next**: WAVE 1 Implementation
