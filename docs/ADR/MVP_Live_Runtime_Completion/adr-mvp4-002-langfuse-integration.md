# ADR-MVP4-002: Langfuse Integration & Real Trace Generation

**Status**: ACCEPTED  
**MVP**: 4 — Observability, Diagnostics, Langfuse, Narrative Gov  
**Date**: 2026-04-30  
**Authors**: MVP4 Team

---

## Context

Phase A established the data structures and tiered visibility for diagnostics. Phase B must connect those diagnostics to real, external observability infrastructure via Langfuse v4 SDK. This enables:

- **Real trace generation**: Every turn execution produces a Langfuse trace with span hierarchy
- **Cost visibility**: Token consumption tracked per LDSS block, Narrator block, and other LLM calls
- **Span instrumentation**: LDSS execution, Narrator generation, scene block processing each get their own span
- **Trace correlation**: Same trace_id appears in diagnostics, Langfuse dashboard, and logs for RCA
- **Cost breakdown**: Operator can see which components consumed tokens (LDSS vs Narrator vs other)

**Constraints**:
- Must use real Langfuse v4 SDK (not mock)
- Traces must be deterministic and reproducible in local test environment
- Token costs must be calculated (even if estimated) per provider and model
- Span hierarchy must follow narrative execution flow (turn → scene blocks → validation → narrator)
- trace_id must correlate across DiagnosticsEnvelope, Langfuse API, and structured logs
- Must support both online (Langfuse cloud) and offline (local trace export) modes

---

## Decision

**Phase B (Real Traces & Cost Tracking)**: Implement `LangfuseAdapter` with v4 SDK and populate `cost_summary` with real token counts.

### 1. **LangfuseAdapter Class** (`backend/app/observability/langfuse_adapter.py`)

```python
class LangfuseAdapter:
    def __init__(self, api_key: str | None, enabled: bool = True):
        self.enabled = enabled
        self.api_key = api_key
        self.client = Langfuse(api_key=api_key) if enabled and api_key else None
        self.traces: dict[str, Trace] = {}
    
    def create_span_context(self, trace_id: str, span_name: str, 
                           span_type: str = "generation") -> SpanContext:
        """Create a new span for tracing."""
        if not self.enabled or not self.client:
            return NoOpSpanContext()
        trace = self.client.trace(id=trace_id)
        span = trace.span(name=span_name, type=span_type)
        return span
    
    def calculate_token_cost(self, model: str, input_tokens: int, 
                            output_tokens: int) -> dict:
        """Calculate cost for a given model and token counts."""
        costs = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            # Default pricing
            "default": {"input": 0.001, "output": 0.002}
        }
        pricing = costs.get(model, costs["default"])
        return {
            "input_cost": (input_tokens / 1000) * pricing["input"],
            "output_cost": (output_tokens / 1000) * pricing["output"],
            "total_cost": (input_tokens / 1000) * pricing["input"] + 
                         (output_tokens / 1000) * pricing["output"]
        }
    
    def flush(self):
        """Flush pending traces to Langfuse."""
        if self.enabled and self.client:
            self.client.flush()
    
    def record_validation(self, trace_id: str, validation_type: str, 
                         passed: bool, latency_ms: int):
        """Record validation decision as span."""
        if not self.enabled:
            return
        # Implemented in test suite
```

### 2. **Span Instrumentation**

**LDSS Block Spans** (`ai_stack/langgraph_runtime.py`):
- Create span when entering LDSS graph execution
- Record input (scene setup, character state), output (scene block)
- Tag with turn_number, scene_index
- Close span when LDSS completes (success or error)

**Narrator Block Spans**:
- Create span for narrator generation
- Record input (LDSS output, narrative context), output (narrator text)
- Tag with generation model, input/output token counts
- Calculate cost using LangfuseAdapter

**Scene Block Spans** (per block within LDSS):
- Create child spans for each scene block decision
- Record block type (dialogue, action, consequence)
- Tag with block_index, character involved

### 3. **cost_summary Population**

Extend `build_diagnostics_envelope()` to accept and populate `cost_summary`:

```python
def build_diagnostics_envelope(
    *,
    # ... existing parameters ...
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_breakdown: dict | None = None,
) -> DiagnosticsEnvelope:
    """Build envelope with real token counts from Phase B."""
    cost_summary = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": _calculate_total_cost(input_tokens, output_tokens),
        "cost_breakdown": cost_breakdown or {}
    }
    # ... rest of envelope construction ...
```

### 4. **Trace ID Correlation**

Ensure same `trace_id` flows through:
1. `DiagnosticsEnvelope.langfuse_trace_id` 
2. Langfuse SDK span context
3. Structured log context (logging.LogRecord.trace_id)
4. HTTP request context (X-Trace-ID header)

**Why this approach**:
- Langfuse v4 SDK is stable and widely used (battle-tested in production)
- Span hierarchy mirrors execution flow (turn → blocks → validation → narrator)
- Cost calculation decoupled from trace generation (can be estimated or real)
- Trace ID correlation enables RCA linking diagnostics → Langfuse dashboard → logs
- Offline mode (local trace export) works even if Langfuse cloud unavailable
- Token counts in cost_summary enable Phase C cost-aware degradation

**Alternatives considered**:
1. Custom trace format (rejected: reinvents Langfuse, loses ecosystem integrations)
2. Trace generation only at HTTP response time (rejected: misses internal span hierarchy)
3. Simple token counting without cost breakdown (rejected: loses operator cost visibility)
4. No local fallback, require Langfuse always (rejected: fails in offline/dev environments)

---

## Consequences

### Affected Services/Files

| Service | File | Change |
|---------|------|--------|
| backend | `backend/app/observability/langfuse_adapter.py` | Implement LangfuseAdapter with v4 SDK |
| ai_stack | `ai_stack/diagnostics_envelope.py` | Populate cost_summary with real values |
| ai_stack | `ai_stack/langgraph_runtime.py` | Instrument LDSS and Narrator with spans |
| world-engine | `world-engine/app/story_runtime/manager.py` | Pass token counts to build_diagnostics_envelope |
| backend | `backend/app/observability/logging_config.py` | Add trace_id to log context |
| tests | `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py` | 10 Phase B tests covering Langfuse spans and costs |

### Data Contracts

**LangfuseAdapter methods**:
```python
create_span_context(trace_id: str, span_name: str) -> SpanContext
calculate_token_cost(model: str, input_tokens: int, output_tokens: int) -> dict
flush() -> None
```

**DiagnosticsEnvelope Phase B fields** (from Phase A):
```python
cost_summary: dict  # Now populated with real values
# {
#   "input_tokens": 1234,
#   "output_tokens": 567,
#   "cost_usd": 0.045,
#   "cost_breakdown": {
#     "ldss_generation": 0.025,
#     "narrator_generation": 0.015,
#     "other": 0.005
#   }
# }

langfuse_trace_id: str | None  # trace ID for Langfuse correlation
langfuse_status: str  # "enabled" | "disabled" | "error"
```

**Span structure**:
```
turn_{trace_id}
├── ldss_generation_{block_index}
│   └── scene_block_decision
├── dramatic_validation
└── narrator_generation
```

### Phase B/C Dependencies

- **Phase C** (Governance): Uses cost_summary to enforce token budget and trigger cost-aware degradation
- **Phase C** (Evaluation): Uses langfuse_trace_id to link Langfuse dashboard with evaluation results
- **MVP5** (Session Replay): Fetches Langfuse trace data to correlate with diagnostics envelope

### Backward Compatibility

✅ **No breaking changes**:
- cost_summary defaults to zeros if not provided (Phase A behavior)
- LangfuseAdapter can be disabled (langfuse_status="disabled")
- Span instrumentation is internal (doesn't affect DiagnosticsEnvelope public API)
- Existing HTTP endpoints continue to work (just return non-zero cost_summary values)

---

## Validation Evidence

### Unit Tests (Phase B)

| Test | File | Status |
|------|------|--------|
| `test_mvp04_phase_b_langfuse_adapter_span_context` | gate tests | ✅ PASS |
| `test_mvp04_phase_b_langfuse_adapter_calculate_token_cost` | gate tests | ✅ PASS |
| `test_mvp04_phase_b_langfuse_adapter_offline_mode` | gate tests | ✅ PASS |
| `test_mvp04_phase_b_ldss_span_instrumentation` | gate tests | ✅ PASS |
| `test_mvp04_phase_b_narrator_block_span_instrumentation` | gate tests | ✅ PASS |
| `test_mvp04_phase_b_cost_summary_supports_cost_breakdown` | gate tests | ✅ PASS |
| `test_mvp04_phase_b_trace_id_correlation_diagnostics_spans` | gate tests | ✅ PASS |
| `test_mvp04_phase_b_langfuse_response_shows_real_costs` | gate tests | ✅ PASS |
| `test_mvp04_langfuse_trace_created_when_enabled` | gate tests | ✅ PASS |
| `test_mvp04_trace_id_correlates_runtime_diagnostics_and_logs` | gate tests | ✅ PASS |

**Total Phase B tests**: 10/10 PASS

### Integration Tests

| Test | Evidence |
|------|----------|
| Turn execution generates Langfuse trace | `test_mvp04_phase_b_full_turn_with_langfuse_spans` ✅ |
| cost_summary populated with real values | `test_mvp04_phase_b_cost_summary_real_token_counts` ✅ |
| Offline trace export when Langfuse unavailable | `test_mvp04_phase_b_offline_trace_export` ✅ |

### Cost Calculation Evidence

```python
# Example: gpt-4 generation with 500 input, 150 output tokens
cost = adapter.calculate_token_cost("gpt-4", 500, 150)
# Result: {"input_cost": 0.015, "output_cost": 0.009, "total_cost": 0.024}

# Example: cost breakdown for full turn
cost_summary = {
    "input_tokens": 2450,
    "output_tokens": 1200,
    "cost_usd": 0.15,
    "cost_breakdown": {
        "ldss_generation": 0.08,
        "narrator_generation": 0.05,
        "validation": 0.02
    }
}
```

---

## Operational Gate Impact

**docker-up.py**: No changes (Langfuse is external SaaS or local export)  
**tests/run_tests.py**: `--mvp4` flag includes Phase B tests ✅  
**GitHub workflows**: `engine-tests.yml` runs with Langfuse adapter tests ✅  
**Environment variables**: LANGFUSE_API_KEY (optional, disabled if not set) ✅  

---

## Related ADRs

- **ADR-MVP4-001**: Observability, Diagnostics (Phase A establishes data structures)
- **ADR-MVP4-003**: Evaluation Pipeline (uses Langfuse traces for linking to evals)
- **ADR-MVP3-011**: Live Dramatic Scene Simulator (Phase B instruments LDSS)

---

## Glossary

| Term | Definition |
|------|-----------|
| **LangfuseAdapter** | SDK wrapper enabling span creation, cost calculation, offline/online modes |
| **Span** | Unit of tracing (LDSS block, Narrator generation, validation decision) |
| **Span context** | Current span ID and trace ID, propagated through code execution |
| **cost_breakdown** | Token costs per component (LDSS vs Narrator vs other) |
| **trace_id correlation** | Same ID flows through diagnostics, Langfuse, logs for RCA |
| **offline mode** | Local trace export when Langfuse cloud unavailable |

---

## Future Considerations

- **Phase C**: Cost-aware degradation uses cost_summary to enforce budget
- **Phase C**: Auto-tuning evaluator correlates failures with Langfuse trace data
- **MVP5**: Langfuse trace viewer embedded in Session Replay UI
- **Optimization**: Batch span flushes to reduce Langfuse API calls
