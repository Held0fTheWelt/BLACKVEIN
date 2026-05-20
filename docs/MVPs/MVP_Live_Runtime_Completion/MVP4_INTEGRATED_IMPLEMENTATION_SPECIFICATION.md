# MVP4 Integrated Implementation Specification

**Purpose**: Complete, cohesive package showing Phase A → Phase B → Phase C → Deployment flow with all gaps, blockers, dependencies, and implementation order.

**Status**: Framework Integration Complete — Ready for Implementation  
**Related**: adr-0032 (5 Core Runtime Contracts), MVP4_PHASE_A_IMPLEMENTATION_PLAN.md, MVP4_PHASE_B_IMPLEMENTATION_PLAN.md, MVP4_PHASE_C_IMPLEMENTATION_PLAN.md

---

## Executive Summary

MVP4 Observability & Diagnostics follows a **3-Phase architectural progression**:

1. **Phase A (COMPLETE)**: DiagnosticsEnvelope, degradation timeline, tiered visibility ✅
2. **Phase B (3 GAPS)**: Fill Scaffold token counts with real LLM data from all phases
3. **Phase C (5 BLOCKERS)**: Governance, evaluation, operator surfaces (blocked until Phase B + 5 defects fixed)

**Phase B is prerequisite for Phase C.** Phase B gates must pass before Phase C work can begin. Additionally, **5 critical runtime defects must be fixed** to satisfy Core Contracts. These 5 are NOT Phase B work — they are prerequisites that unlock Phase C.

**Complete Implementation Order (sequenced):**

```
Phase A: Diagnostics Infrastructure ✅ (DONE)
   ↓
Phase B: Real Cost Attribution (3 gaps to fill)
   ├─ Step 1: Narrative Token Attribution
   ├─ Step 2: LDSS Decision Span Token Attribution
   ├─ Step 3: Cost Summary Aggregation
   ├─ Step 4: Tests + Verification
   └─ Gate: test_goc_mvp04_observability_diagnostics_gate PASS
   ↓
PARALLEL: Phase C Blocker Fixes (5 critical defects)
   ├─ P1: Actor Ownership in Backend→WE handoff
   ├─ P2: can_execute validation with story_entries
   ├─ P3: Turn 0 truthfulness (real provider execution)
   ├─ P4: DiagnosticsEnvelope error handling
   └─ P5: SSE routing and narrator_streaming flag
   ↓
Phase C: Governance + Operator Surfaces
   ├─ Cost-Aware LDSS Degradation
   ├─ Audit Trail & Override Management
   ├─ Evaluation Pipeline
   ├─ 6 Health Panels
   └─ Cost Dashboard
   ↓
Deployment Ready
```

---

## Part 1: Phase A Recap (Complete — Foundation)

**Status**: ✅ DONE — All tests passing

**What Phase A delivered:**
- `DiagnosticsEnvelope` dataclass in `ai_stack/telemetry/diagnostics_envelope.py`
- `degradation_timeline` tracking DegradationEvent (quality_class, signals)
- `cost_summary` field (skeleton, all zeros for Phase B to fill)
- `to_response(context="operator"|"langfuse"|"super_admin")` tiered visibility
- Phase A tests: `test_mvp04_diagnostics_envelope_structure.py` PASS

**What Phase B builds on:**
- DiagnosticsEnvelope structure (exists, just needs real data)
- Degradation tracking (Phase B adds cost signals)
- Context-aware visibility (Phase B uses tiered redaction for costs)

---

## Part 2: Phase B — Real Cost Attribution (3 Implementation Gaps)

**Current State**: Infrastructure exists, but costs are Scaffold (all zeros)

**Problem**: Turn diagnostics show `cost_summary: {input_tokens: 0, output_tokens: 0, cost_usd: 0.0}` even though Langfuse spans are created. The problem is that:

1. **Narrative block spans end with mock tokens** — `input_tokens: 0, output_tokens: 0, model: "mock"`
2. **LDSS decision spans don't exist** — Decisions are made but not traced with token counts
3. **cost_summary doesn't aggregate real data** — Still iterating over Scaffold graph_costs

**Impact**: Phase C cannot make cost-aware governance decisions (token budgets, degradation) without real costs. Cost-aware LDSS shortening needs actual token counts to decide when to truncate context.

### Phase B Gap 1: Narrative Token Attribution

**File**: `ai_stack/story_runtime/narrative_runtime_agent.py` (lines ~224)

**Current (Scaffold):**
```python
span.end(
    output={...},
    metadata={
        "input_tokens": 0,          # ← WRONG: scaffold
        "output_tokens": 0,
        "model": "mock",
    }
)
```

**Target (Real tokens from LLM response):**

The narrator calls an LLM to generate narration. That LLM response includes `usage: {prompt_tokens: X, completion_tokens: Y}`. Extract that.

```python
# Get actual LLM response from narration call
llm_response = call_llm_for_narration(...)

# Extract real tokens
input_tokens = llm_response.get("usage", {}).get("prompt_tokens", 0)
output_tokens = llm_response.get("usage", {}).get("completion_tokens", 0)
model = llm_response.get("model", "")  # e.g., "gpt-4-turbo"

# Calculate cost (helper function added to langfuse_adapter)
cost_usd = calculate_token_cost(model, input_tokens, output_tokens)

span.end(
    output={"narration": narration},
    metadata={
        "input_tokens": input_tokens,      # ← REAL tokens
        "output_tokens": output_tokens,
        "model": model,
        "cost_usd": cost_usd,
        "latency_ms": elapsed_ms,
    }
)
```

**Helper Function** (add to `backend/app/observability/langfuse_adapter.py`):

```python
def calculate_token_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost based on model pricing."""
    pricing = {
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }
    rates = pricing.get(model, pricing.get("gpt-3.5-turbo"))
    input_cost = (input_tokens / 1000.0) * rates["input"]
    output_cost = (output_tokens / 1000.0) * rates["output"]
    return round(input_cost + output_cost, 6)
```

**Test**: `test_mvp4_narrative_spans_have_real_token_counts`
- Narrator spans must have `input_tokens > 0`
- Narrator spans must have `output_tokens > 0`
- Model must not be `"mock"`
- Cost must be `> 0.0`

---

### Phase B Gap 2: LDSS Decision Spans with Token Attribution

**File**: `ai_stack/live_dramatic_scene_simulator.py`

**Current State**: LDSS makes decisions but doesn't track them in Langfuse spans.

**Target**: Wrap each LDSS decision in a `ldss.decision` span, extract real token counts from the LLM call, end span with token metadata.

```python
# In decision-making function
parent_span = adapter.get_active_span()

if parent_span:
    decision_span = adapter.create_child_span(
        name="ldss.decision",
        input={"decision_context": decision_context},
        metadata={"decision_index": 0}
    )
else:
    decision_span = None

try:
    # Call LLM for decision
    llm_response = call_llm_for_decision(decision_context)
    
    # Extract real tokens
    input_tokens = llm_response.get("usage", {}).get("prompt_tokens", 0)
    output_tokens = llm_response.get("usage", {}).get("completion_tokens", 0)
    model = llm_response.get("model", "")
    cost = calculate_token_cost(model, input_tokens, output_tokens)
    
    # Parse decision
    decision = parse_decision(llm_response)
    
    # Log tokens to span
    if decision_span:
        decision_span.end(
            output={"decision": decision},
            metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "model": model,
                "cost_usd": cost,
            }
        )
    
    return decision

except Exception as e:
    if decision_span:
        decision_span.end(output={"error": str(e)})
    raise
```

**Test**: `test_mvp4_ldss_decision_spans_have_tokens`
- `ldss.decision` spans must exist in trace
- Each span must have `input_tokens`, `output_tokens`, `cost_usd` > 0
- Spans must be children of the root `world-engine.turn.execute` span

---

### Phase B Gap 3: Cost Summary Aggregation

**File**: `world-engine/app/story_runtime/manager.py` (lines ~2080-2115 in `_finalize_committed_turn()`)

**Current State**: Aggregation code exists but iterates over `graph_costs` (all zeros, never populated from real spans):

```python
for phase in ["profile", "lanes", "ldss", "narrator", ...]:
    tokens = graph_costs[phase].get("input_tokens", 0)  # ← always 0
```

**Target**: After each phase completes, capture span metadata with real tokens. Then aggregate those into `cost_summary`.

**Implementation Pattern**:

1. **During phase execution**, store span metadata:
   ```python
   # During LDSS phase
   ldss_span = adapter.get_active_span()
   ldss_result = execute_ldss_phase(graph_state)
   ldss_metadata = ldss_span.metadata if ldss_span else {}
   
   # During Narrator phase
   narrator_span = adapter.get_active_span()
   narrator_result = execute_narrator_phase(graph_state)
   narrator_metadata = narrator_span.metadata if narrator_span else {}
   ```

2. **In finalization**, aggregate real metadata:
   ```python
   total_input_tokens = 0
   total_output_tokens = 0
   total_cost_usd = 0.0
   cost_breakdown = {}
   
   # Gather from LDSS
   ldss_tokens = ldss_metadata.get("input_tokens", 0)
   ldss_output = ldss_metadata.get("output_tokens", 0)
   ldss_cost = ldss_metadata.get("cost_usd", 0.0)
   total_input_tokens += ldss_tokens
   total_output_tokens += ldss_output
   total_cost_usd += ldss_cost
   cost_breakdown["ldss"] = ldss_cost
   
   # Gather from Narrator
   narrator_tokens = narrator_metadata.get("input_tokens", 0)
   narrator_output = narrator_metadata.get("output_tokens", 0)
   narrator_cost = narrator_metadata.get("cost_usd", 0.0)
   total_input_tokens += narrator_tokens
   total_output_tokens += narrator_output
   total_cost_usd += narrator_cost
   cost_breakdown["narrator"] = narrator_cost
   
   # Build envelope with real costs
   diag_envelope = build_diagnostics_envelope(
       ...,
       cost_summary={
           "input_tokens": total_input_tokens,
           "output_tokens": total_output_tokens,
           "cost_usd": round(total_cost_usd, 6),
           "cost_breakdown": cost_breakdown,
       }
   )
   ```

**Test**: `test_mvp4_cost_summary_aggregates_real_values`
- `cost_summary["input_tokens"]` must be `> 0`
- `cost_summary["output_tokens"]` must be `> 0`
- `cost_summary["cost_usd"]` must be `> 0.0`
- `cost_breakdown` must exist with per-component costs

---

## Part 3: Phase B Completion Gate

Phase B is complete when **ALL** of these pass:

1. ✅ **Narrative block spans have real tokens:**
   - `test_mvp4_narrative_spans_have_real_token_counts` PASS
   - Every narrator span: `input_tokens > 0`, `output_tokens > 0`, `model != "mock"`, `cost_usd > 0`

2. ✅ **LDSS decision spans exist with token tracking:**
   - `test_mvp4_ldss_decision_spans_have_tokens` PASS
   - `ldss.decision` spans present with token metadata, child of root span

3. ✅ **Cost summary has real aggregated values:**
   - `test_mvp4_cost_summary_aggregates_real_values` PASS
   - `cost_summary` shows real totals, not zeros, with per-component breakdown

4. ✅ **Cost visibility works (tiered redaction):**
   - `test_mvp4_langfuse_context_shows_costs` PASS
   - `to_response("langfuse")` exposes costs
   - `to_response("operator")` redacts costs as `[REDACTED]`

5. ✅ **No regressions in Phase A:**
   - `python tests/run_tests.py --mvp4` — all tests green
   - DiagnosticsEnvelope structure unchanged
   - Degradation timeline still tracking quality_class

---

## Part 4: Phase B to Phase C Bridge — The 5 Critical Blockers

**Phase B gates must pass BEFORE starting Phase C blocker fixes.**

Once Phase B is complete, work CANNOT begin on Phase C governance features. Instead, **Phase B must be followed by fixing 5 critical runtime defects** that violate Core Contracts:

| Priority | Blocker | Contract(s) | Location | What to Fix |
|----------|---------|------------|----------|------------|
| **P1** | **D-007: Actor Ownership Lost** | Contract 1 | `backend/app/services/game/game_service.py:353-360` | Backend must send `human_actor_id`, `npc_actor_ids`, `actor_lanes` to WE in turn response |
| **P2** | **D-006: Empty Shell Playable** | Contract 3 | `backend/app/api/v1/game_routes.py:267` | Validate `story_entries.count > 0` before returning `can_execute=True` |
| **P3** | **D-001: Turn 0 Not Live** | Contract 2 | `world-engine/app/story_runtime/manager.py:2150` | Turn 0 must use real provider (not deterministic LDSS); mark turn_type correctly |
| **P4** | **D-013: Error Swallowing** | Contract 4 | `world-engine/app/story_runtime/manager.py:2114` | DiagnosticsEnvelope errors must fail fast + log to Langfuse, never suppressed |
| **P5** | **D-008: SSE Not Routed** | Contract 5 | `frontend/static/play_narrative_stream.js:17` | Add `narrator_streaming` flag to turn response; route EventSource to correct endpoint |

**These 5 defects must be fixed before Phase C can be implemented.** They are not Phase C work — they are prerequisites that enable Phase C to satisfy Core Contracts.

---

## Part 5: Complete Implementation Sequence

### Wave Ordering

Execution occurs in **3 sequential waves**:

**WAVE 1: Phase B (Real Cost Attribution)**
```
├─ Task 1.1: Add calculate_token_cost() helper to langfuse_adapter.py
├─ Task 1.2: Update Narrator Token Attribution (ai_stack/story_runtime/narrative_runtime_agent.py)
├─ Task 1.3: Add LDSS Decision Spans (ai_stack/live_dramatic_scene_simulator.py)
├─ Task 1.4: Wire Cost Summary Aggregation (world-engine/app/story_runtime/manager.py)
├─ Task 1.5: Add Phase B Tests (test_goc_mvp04_observability_diagnostics_gate.py)
└─ GATE 1: test_goc_mvp04_observability_diagnostics_gate PASS → All 5 Phase B tests green
```

**WAVE 2: Phase C Blocker Fixes (5 Critical Defects)**
```
├─ Task 2.1: Fix P1 — Actor Ownership (backend/app/services/game/game_service.py)
├─ Task 2.2: Fix P2 — Empty Shell Validation (backend/app/api/v1/game_routes.py)
├─ Task 2.3: Fix P3 — Turn 0 Truthfulness (world-engine/app/story_runtime/manager.py)
├─ Task 2.4: Fix P4 — Error Handling (world-engine/app/story_runtime/manager.py)
├─ Task 2.5: Fix P5 — SSE Routing (frontend/static/play_narrative_stream.js + routes)
└─ GATE 2: All 5 Blocker tests PASS → All Core Contracts satisfied
```

**WAVE 3: Phase C (Governance + Operator Surfaces)**
```
├─ Task 3.1: Cost-Aware LDSS Degradation (backend/app/services/governance/observability_governance_service.py)
├─ Task 3.2: Audit Trail & Override Management (backend/app/auth/admin_security.py)
├─ Task 3.3: Evaluation Pipeline (ai_stack/quality_lab/evaluation_pipeline.py)
├─ Task 3.4: Health Panels (administration-tool/templates/)
├─ Task 3.5: Cost Dashboard (administration-tool/)
└─ GATE 3: test_mvp4_governance_phase_complete PASS → Phase C ready for deployment
```

### Dependency Chain

```
Phase A Tests PASS (baseline)
        ↓
Phase B Gap 1 (Narrative tokens)
        ↓
Phase B Gap 2 (LDSS decision spans)
        ↓
Phase B Gap 3 (Cost aggregation)
        ↓
Phase B Tests PASS (real costs flowing)
        ↓
Phase C Blocker P1 (Actor ownership)
        ↓
Phase C Blocker P2 (Empty shell validation)
        ↓
Phase C Blocker P3 (Turn 0 truthfulness)
        ↓
Phase C Blocker P4 (Error handling)
        ↓
Phase C Blocker P5 (SSE routing)
        ↓
Core Contract Tests PASS
        ↓
Phase C Implementation (governance, evaluation, operators)
        ↓
MVP4 Deployment Ready
```

---

## Part 6: Infrastructure Dependencies

### Already Exist (Phase A/B Foundation)

✅ `backend/app/observability/langfuse_adapter.py` — LangfuseAdapter v4 SDK with:
- `client.start_observation(as_type="span", trace_context=...)`
- `adapter.start_trace()`
- `adapter.start_span_in_trace(trace_id, name, ...)`
- `adapter.create_child_span()`
- ContextVar `_active_span_context` for thread-safe span passing

✅ `world-engine/app/api/http.py` — HTTP handler creates root span `world-engine.turn.execute`, linked to Backend trace via `X-WoS-Trace-Id` header

✅ `ai_stack/telemetry/diagnostics_envelope.py` — DiagnosticsEnvelope with `cost_summary` field and `to_response(context)` method

✅ `world-engine/app/story_runtime/manager.py` — Span creation for phases, metadata collection readiness

✅ `backend/app/services/governance/observability_governance_service.py` — Token budget tracking (correct file path, not `backend/app/observability_governance_service.py`)

### Must Be Created (Phase B Implementation)

❌ `calculate_token_cost()` function (add to langfuse_adapter.py)

❌ Token extraction in `ai_stack/story_runtime/narrative_runtime_agent.py` (lines ~224)

❌ LDSS decision spans in `ai_stack/live_dramatic_scene_simulator.py`

❌ Metadata aggregation in `world-engine/app/story_runtime/manager.py` (lines ~2080)

❌ Phase B tests in `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py`

### Phase C Will Use (After Blockers Fixed)

- `backend/app/services/governance/observability_governance_service.py` — Cost-aware degradation decisions
- `backend/app/auth/admin_security.py` — Audit logging
- `administration-tool/app/admin_routes.py` — Governance UIs
- New: `ai_stack/quality_lab/evaluation_pipeline.py` — Baseline rubric, regression detection
- New: `administration-tool/templates/manage/narrative-gov/runtime.html` — 6 health panels

---

## Part 7: Success Criteria (How to Know MVP4 is Complete)

### Phase B Success Criteria

✅ All 5 Phase B tests PASS:
- `test_mvp4_narrative_spans_have_real_token_counts`
- `test_mvp4_ldss_decision_spans_have_tokens`
- `test_mvp4_cost_summary_aggregates_real_values`
- `test_mvp4_langfuse_context_shows_costs`
- No regressions in Phase A tests

✅ Real-world evidence:
- Langfuse dashboard shows narrator spans with `input_tokens > 0`
- Langfuse dashboard shows `ldss.decision` spans with token metadata
- Turn diagnostics envelope shows `cost_summary` with real values
- Trace hierarchy is correct: Backend root → WE root → phases → decisions/blocks

### Phase C Blocker Fixes Success Criteria

✅ All 5 blockers fixed:
- P1: Actor metadata in Backend→WE handoff (verified in test)
- P2: `can_execute=False` when story_entries empty (verified in test)
- P3: Turn 0 uses real provider (verified by tracing decision in Langfuse)
- P4: Diagnostics errors don't swallow, return 500 + log (verified in test)
- P5: SSE endpoint receives `narrator_streaming=True` (verified in test)

### Phase C Success Criteria

✅ All 6 health panels render and show live data:
- Content Module Health
- Runtime Profile Health
- Runtime Module Health
- LDSS Health
- Frontend Render Contract Health
- Actor Lane Health

✅ Evaluation pipeline:
- Baseline recorded for Turn 1-3 openings
- Regression detection working
- Quality_class updated in degradation_timeline

✅ No regressions in MVP1-3 tests

---

## Part 8: Risk Mitigation

### Risk: Span Metadata Not Propagating

**Mitigation**: ContextVar `_active_span_context` already exists and is thread-safe. Tests explicitly verify parent-child span relationships in Langfuse dashboard before considering Phase B complete.

### Risk: Token Counts Stuck at Zero

**Mitigation**: Tests for Phase B Gap 1, 2, 3 all assert `> 0` for token fields. If tests pass, counts are real. If tests fail, RCA is immediate.

### Risk: Phase C Blocked by Blocker Fixes Taking Too Long

**Mitigation**: Blocker fixes are small, targeted changes (typically 1-5 lines per blocker). Phase C work can begin immediately after blocker P1 and P3 are fixed (most critical for contracts). Other blockers can be fixed in parallel with Phase C work.

### Risk: Cost Calculation Incorrect

**Mitigation**: `calculate_token_cost()` uses published OpenAI pricing. Can be updated quarterly. Tests don't assert specific costs (USD), only that costs `> 0.0` and match token counts.

---

## Part 9: Deployment Checklist

Before deploying MVP4:

- [ ] Phase A tests PASS (diagnostics infrastructure)
- [ ] Phase B tests PASS (real costs flowing)
- [ ] All 5 Blocker tests PASS (contracts satisfied)
- [ ] Phase C tests PASS (governance + operator surfaces)
- [ ] No regressions in MVP1-3 gates
- [ ] Langfuse traces in production show real costs and trace hierarchy
- [ ] Health panels render with live data
- [ ] Audit trail logs operator actions
- [ ] Cost dashboard shows real session costs
- [ ] ADRs updated with deployment evidence

---

## References

- **adr-0032**: 5 Core Runtime Contracts (foundation of MVP4)
- **MVP4_PHASE_A_IMPLEMENTATION_PLAN.md**: Diagnostics infrastructure (DONE)
- **MVP4_PHASE_B_IMPLEMENTATION_PLAN.md**: Real cost attribution (THIS DOCUMENT)
- **MVP4_PHASE_C_IMPLEMENTATION_PLAN.md**: Governance + operator surfaces (blocked by P1-P5)
- **MVP4_TEST_GATE_PLAN.md**: Test execution and verification
- **04_observability_diagnostics_langfuse_narrative_gov.md**: Master overview

---

**This specification is complete and ready for implementation. All dependencies are known, all gaps are identified, and all blockers are documented.**
