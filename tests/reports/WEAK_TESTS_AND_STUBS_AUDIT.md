# Weak Tests & Stub Implementations Audit

**Date**: 2026-04-30  
**Coverage Target**: 86.05% (PASSING ✅)  
**Audit Scope**: Identify test weaknesses and incomplete implementations

---

## Executive Summary

Found **3 major categories** of weak tests and stub implementations:

| Category | Count | Severity | Status |
|----------|-------|----------|--------|
| Placeholder E2E Tests | 6 tests | 🔴 HIGH | Needs Implementation |
| Deferred API Stubs | 4 endpoints | 🟡 MEDIUM | Documented Deferral |
| Weak Test Assertions | 12+ tests | 🟡 MEDIUM | Needs Strengthening |

**Total Impact**: Low (existing coverage is real), but these represent future work.

---

## 1. Placeholder E2E Tests (High Priority)

### Issue: `tests/e2e/test_final_goc_annette_alain_e2e.py`

**Problem**: All E2E tests hardcode PASS status with empty evidence arrays. Tests don't exercise real behavior.

```python
# ❌ WEAK: Hardcoded evidence with zeros
evidence = {
    "test_id": "test_final_annette_e2e_evidence",
    "status": "PASS",  # Always PASS
    "validations": {
        "block_rendering": {
            "status": "PASS",
            "block_count": 0,        # ← Empty
            "evidence": []           # ← Never populated
        },
        "typewriter_deterministic": {
            "test_mode": True,
            "characters_per_second": 44,
            "evidence": []           # ← Never populated
        },
        # ... all evidence arrays empty
    },
    "transcript": {
        "run_id": None,
        "session_id": None,
        "turns": []                  # ← Never populated
    }
}
```

**Tests Affected**:
- `TestFinalAnnetteSoloRun::test_final_annette_e2e_evidence`
- `TestFinalAlainSoloRun::test_final_alain_e2e_evidence`
- `TestMVP5OperationalGate::test_docker_up_script_exists`
- `TestMVP5OperationalGate::test_run_tests_includes_mvp5_flag`
- `TestMVP5OperationalGate::test_github_workflows_include_frontend_tests`
- `TestMVP5OperationalGate::test_frontend_pyproject_toml_has_mvp5_markers`

**Why This Matters**: 
- Tests always pass regardless of actual behavior
- No proof that block rendering, typewriter, or skip/reveal actually work
- Evidence is never populated (zeros/nulls)
- Operational gates check file existence, not functionality

**Recommendations**:
1. **Replace with real Playwright tests** that launch browser and exercise UI:
   - Render actual blocks and verify DOM structure
   - Execute typewriter animation and measure character progress
   - Click skip/reveal buttons and verify state changes
   - Capture real transcript

2. **Intermediate fix** (if browser testing not yet available):
   - Use `unittest.mock` to simulate turn responses
   - Verify BlocksOrchestrator state changes
   - Populate `evidence[]` arrays with actual assertions

3. **Example real test**:
```python
@pytest.mark.mvp5
def test_final_annette_real_e2e(playwright_browser, admin_jwt):
    """Real E2E: Launch browser, play Annette, verify block rendering."""
    page = playwright_browser.new_page()
    page.goto(f"{BASE_URL}/play/start")
    
    # Select Annette
    page.click("button:has-text('Annette')")
    
    # Get initial blocks
    blocks = page.locator("[data-block-id]")
    assert blocks.count() > 0, "No blocks rendered"
    
    # Verify block structure
    for i in range(blocks.count()):
        block = blocks.nth(i)
        assert block.get_attribute("data-block-type") in [
            "narrator", "actor_line", "actor_action", 
            "stage_direction", "environmental"
        ]
```

---

## 2. Deferred API Stubs (Medium Priority)

### Issue: `backend/app/api/v1/session_routes.py`

**Problem**: 4 session endpoints return 501 "Not Implemented" with deferral notices.

```python
# Session endpoints that are deferred stubs:
- GET  /api/v1/sessions/<id>        → wos.session.get
- POST /api/v1/sessions/<id>/turns   → wos.session.execute_turn  
- GET  /api/v1/sessions/<id>/logs    → wos.session.logs
- GET  /api/v1/sessions/<id>/state   → wos.session.state

# All return 501 with message:
"reason": "deferred to W3.2 (persistence layer not yet implemented)"
```

**Why This Matters**:
- MCP clients cannot retrieve session state mid-game
- Session diagnostics unavailable
- Audit trails incomplete
- These are documented as Phase W3.2 work

**Status**: ✅ ACCEPTABLE (documented deferral, not blocking MVP5)

**Tests**: Tests verify the 501 responses correctly (not weak tests themselves)

**Future Work**: Implement in W3.2 persistence phase:
```python
@api_v1_bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """W3.2: Retrieve session state with full history."""
    # Implementation pending persistence layer
    session = Session.query.get(session_id)
    return jsonify({
        "session_id": session.session_id,
        "player": session.player,
        "current_turn": session.turn_counter,
        "turns": [turn.to_dict() for turn in session.turns],
    })
```

---

## 3. Weak Test Assertions (Medium Priority)

### Pattern A: Mock-only assertions without real behavior

**Example**: `backend/tests/improvement/test_improvement_model_routing_allowed.py`

```python
# ❌ WEAK: Only verifies mock was called, not behavior
def test_run_routed_bounded_call_adapter_success(self):
    adapters = {adapter_name: StubModelAdapter(success=True)}
    
    trace, excerpt = _run_routed_bounded_call(...)
    
    # Only checks if mocked adapter was called
    if trace.get("adapter_key") == adapter_name:
        assert trace["bounded_model_call"] is True
        assert excerpt == "Generated interpretation"
    else:
        # Routing may select different adapter ← Weak! Could always go here
        assert isinstance(trace, dict)
```

**Problem**: Test passes even if routing logic fails, because it accepts any adapter.

**Recommendation**: 
```python
# ✅ STRONG: Force routing to expected adapter
def test_run_routed_bounded_call_adapter_success(self):
    adapter_name = "expected_adapter"
    specs = [BuildSpec(adapter_name=adapter_name, ...)]  # Force this spec
    adapters = {adapter_name: StubModelAdapter(success=True)}
    
    trace, excerpt = _run_routed_bounded_call(
        specs=specs,  # ← Only one spec, routing has no choice
        adapters=adapters,
        ...
    )
    
    # Now we can assert the actual routing happened
    assert trace["adapter_key"] == adapter_name, "Routing failed"
    assert excerpt == "Generated interpretation"
```

---

### Pattern B: Status-code-only assertions

**Example**: `backend/tests/services/test_system_diagnosis_service.py`

```python
# ❌ WEAK: Only checks response structure, not correctness
def test_check_ai_stack_readiness_success(self):
    with patch(...) as mock_report:
        mock_report.return_value = {"overall_status": "ready"}
        
        result = _check_ai_stack_readiness(trace_id="trace-123")
        
        # Only checks that keys exist, not logic
        assert result["id"] == "ai_stack_release_readiness"
        assert result["status"] == "running"
        assert "latency_ms" in result
```

**Problem**: 
- `overall_status: "ready"` is mocked, so test always passes
- No verification that readiness logic actually evaluated components
- Doesn't check what conditions trigger "ready" vs "blocked"

**Recommendation**:
```python
# ✅ STRONG: Verify actual readiness logic
def test_check_ai_stack_readiness_blocks_on_missing_component(self):
    """Readiness should be blocked if any component is degraded."""
    # Don't mock—use real components or fixtures
    with patch("app.services.system_diagnosis_service.check_rag_readiness") as mock_rag:
        mock_rag.return_value = {
            "id": "rag_pipeline",
            "status": "fail",  # ← Degraded
            "message": "No documents indexed"
        }
        
        result = _check_ai_stack_readiness(trace_id="trace-123")
        
        # Assert that readiness IS blocked
        assert result["status"] == "blocked", "Should block on failed component"
        assert "rag_pipeline" in result.get("failures", [])
```

---

### Pattern C: Field-presence-only tests

**Example**: `backend/tests/test_play_qa_diagnostics_routes.py`

```python
# ❌ WEAK: Only checks JSON structure, not content
def test_qa_canonical_turn_projection(self):
    projection = get_projection()
    
    # Presence-only assertions
    assert projection["schema_version"] == "qa_canonical_turn_projection.v1"
    assert "tier_a_primary" in projection
    assert "tier_b_detailed" in projection
    assert "graph_execution_summary" in projection
    assert "raw_canonical_record_available" in projection
```

**Problem**:
- Doesn't verify the **content** of each tier
- Doesn't check tier_a_primary contains the right fields
- Doesn't validate graph_execution_summary structure
- Presence-only; could contain garbage data

**Recommendation**:
```python
# ✅ STRONG: Validate content and structure
def test_qa_canonical_turn_projection_tier_a_valid(self):
    projection = get_projection()
    
    # Validate Tier A structure
    tier_a = projection["tier_a_primary"]
    assert isinstance(tier_a, dict), "tier_a_primary must be dict"
    
    # Required fields in Tier A
    required = ["turn_id", "player_input", "blocks_rendered", 
                "actor_state_after_turn", "visible_output"]
    for field in required:
        assert field in tier_a, f"Missing required field: {field}"
        assert tier_a[field] is not None, f"Field cannot be null: {field}"
    
    # Content validation
    assert len(tier_a["blocks_rendered"]) > 0, "Turn must render blocks"
    assert tier_a["turn_id"].startswith("turn_"), "Invalid turn_id format"
```

---

## 4. Tests with Hardcoded Skip Logic

**Pattern**: `backend/tests/improvement/test_improvement_model_routing_allowed.py`

```python
# ❌ WEAK: Test can silently skip without failing
def test_run_routed_bounded_call_adapter_success_populates_excerpt(self):
    specs = build_writers_room_model_route_specs()
    if not specs:
        pytest.skip("No specs available for testing")  # ← Test silently skipped!
    
    # If specs aren't built yet, this test never runs
```

**Problem**:
- When specs aren't available, test skips silently
- Coverage metrics don't show the skip
- Test suite might be green but feature untested
- No indication that test is blocked on dependency

**Recommendation**:
```python
# ✅ STRONG: Fail fast with clear error
def test_run_routed_bounded_call_adapter_success_populates_excerpt(self):
    specs = build_writers_room_model_route_specs()
    assert specs, (
        "Writers room routing specs must be populated. "
        "Check: build_writers_room_model_route_specs() in writers_room.py. "
        "Specs required: at least one adapter_name with model routes."
    )
    
    # Now test proceeds with real specs
    adapter_name = specs[0].adapter_name
    # ...
```

---

## Severity & Action Items

### 🔴 HIGH: Implement Real MVP5 E2E Tests
**File**: `tests/e2e/test_final_goc_annette_alain_e2e.py`  
**Current**: Placeholder with hardcoded PASS, empty evidence  
**Target**: Real Playwright browser tests or integrated DOM tests  
**Estimate**: 2-3 days  
**Blocker**: None (MVP5 functional tests work, E2E is acceptance proof)

**Action**:
```bash
# Step 1: Implement browser-based E2E using Playwright
cd frontend && npm install --save-dev @playwright/test

# Step 2: Rewrite E2E tests to launch browser and exercise UI
python -m pytest tests/e2e/test_final_goc_annette_alain_e2e.py --with-playwright -v

# Step 3: Populate evidence arrays with real assertions
# Evidence will contain actual block counts, animation timing, etc.
```

---

### 🟡 MEDIUM: Strengthen Existing Test Assertions

**Files**: 
- `backend/tests/improvement/test_improvement_model_routing_allowed.py`
- `backend/tests/services/test_system_diagnosis_service.py`
- `backend/tests/test_play_qa_diagnostics_routes.py`

**Changes**: Remove mock-only assertions, add behavior validation  
**Estimate**: 1 day  
**Impact**: Increases confidence in routing and diagnostics

---

### 🟢 LOW: Document Deferred Stubs

**Files**:
- `backend/app/api/v1/session_routes.py`
- Tests for stubs in `backend/tests/`

**Status**: ✅ Already documented in code and passing tests  
**Action**: No change needed (documented deferral, tests verify 501 responses)

---

## Coverage Impact

Current state:
- **Test Coverage**: 86.05% (exceeds 85% target)
- **Weak Tests**: Do not significantly impact coverage (they're mostly structure tests that pass)
- **Stub Implementations**: Already covered by tests (verify correct 501 responses)

**Improving weak tests will NOT change coverage percentage** (already passing), but will **increase confidence in actual behavior**.

---

## Recommended Implementation Order

1. **Weeks 1-2**: Implement real MVP5 E2E tests (Playwright)
2. **Week 3**: Strengthen mock-based test assertions
3. **Week 4**: Add behavior validation to diagnostics tests
4. **Future (W3.2)**: Implement deferred session endpoints

---

## Example: Before & After

### Before (Weak Test)
```python
def test_final_annette_e2e_evidence(self, e2e_report_dir):
    evidence = {"status": "PASS", "validations": {...}}  # Hardcoded
    json.dump(evidence, open(...))
    assert evidence["status"] == "PASS"  # Always passes
```

### After (Real Test)
```python
def test_final_annette_e2e_evidence(playwright_browser):
    """Real E2E: Launch browser, play game, verify block rendering."""
    page = playwright_browser.new_page()
    page.goto(f"{BASE_URL}/play")
    page.click("text=Annette")
    
    # Verify blocks are rendered (actually in DOM)
    blocks = page.locator("[data-block-id]")
    assert blocks.count() > 0, f"No blocks found in DOM"
    
    # Verify typewriter animation progress
    first_block = blocks.first
    visible_text_before = first_block.inner_text()
    page.wait_for_timeout(100)  # Wait for animation
    visible_text_after = first_block.inner_text()
    assert len(visible_text_after) > len(visible_text_before), (
        "Typewriter should reveal more characters over time"
    )
    
    # Verify skip button works
    page.click("button:has-text('Skip')")
    fully_visible = first_block.inner_text()
    assert len(fully_visible) > len(visible_text_after)
```

---

## References

- **Weak Test Patterns**: [TEST_SUITE_CONTRACT.md](../testing/TEST_SUITE_CONTRACT.md)
- **Legacy Test Removal**: [LEGACY_TEST_REMOVAL_INVENTORY.md](LEGACY_TEST_REMOVAL_INVENTORY.md)
- **E2E Tests**: `tests/e2e/test_final_goc_annette_alain_e2e.py`
- **Deferred Stubs**: `backend/app/api/v1/session_routes.py`

---

**Audit Completed**: 2026-04-30  
**Next Review**: When E2E tests are implemented
