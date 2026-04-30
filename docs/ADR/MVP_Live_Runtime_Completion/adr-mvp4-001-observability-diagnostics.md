# ADR-MVP4-001: Observability, Diagnostics, and Trace Infrastructure

**Status**: ACCEPTED  
**MVP**: 4 — Observability, Diagnostics, Langfuse, Narrative Gov  
**Date**: 2026-04-30  
**Authors**: MVP4 Team

---

## Context

MVP3 established the Live Dramatic Scene Simulator (LDSS) as the core narrative engine. MVP4 must provide complete observability into what LDSS is doing, why, and whether output quality meets acceptable thresholds. This observability is non-negotiable for:

- **Operator trust**: Showing that AI decisions are traceable, not opaque
- **Compliance auditing**: Logging all decision points with acceptance/rejection status
- **Cost governance**: Tracking token usage and applying cost-aware degradation
- **Quality assurance**: Recording baseline turns and auto-tuning evaluation rubrics
- **Root cause analysis**: Correlating Langfuse traces with runtime diagnostics for debugging

**Constraints**:
- Must not break existing MVP1-3 contracts (backward compatible)
- Must support tiered visibility (operator, Langfuse, super-admin contexts)
- Must enable trace ID correlation across diagnostics, spans, and logs
- Must provide non-placeholder evidence (reject static/mock data)
- Must work with real Langfuse v4 SDK (Phase B) and local trace export (Phase A fallback)

---

## Decision

**Phase A (Degradation Timeline & Cost Summary)**: Extend `DiagnosticsEnvelope` dataclass with three new fields:

1. **`degradation_timeline: list[DegradationEvent]`**
   - Records every degradation event during turn execution
   - Each event: marker (e.g., "FALLBACK_USED"), severity (minor/moderate/critical), timestamp, recovery status, latency
   - Used to understand why output quality is degraded

2. **`cost_summary: dict`**
   - Placeholder in Phase A (all zeros)
   - Schema: `{input_tokens: 0, output_tokens: 0, cost_usd: 0.0, cost_breakdown: {}}`
   - Phase B fills with real token counts and cost breakdown (LDSS, Narrator, other)

3. **`to_response(context: str) -> dict`** method for tiered visibility
   - `context="operator"`: Redacts input_hash, output_hash, cost_summary (sensitive info)
   - `context="langfuse"`: Shows hashes, excludes debug_payload (full technical data)
   - `context="super_admin"`: Complete unredacted envelope (for deep debugging)

**Why this approach**:
- Extends existing `DiagnosticsEnvelope` (no breaking changes)
- Degradation timeline answers "what went wrong" (marker + severity + recovery)
- Cost summary field ready for Phase B without refactoring
- `to_response()` method enables same envelope object to serve multiple audiences without code duplication
- Tiered visibility prevents accidental exposure of sensitive data (hashes, debug payloads) to operators

**Alternatives considered**:
1. Create separate envelope types per visibility level (rejected: explosion of dataclasses, harder to maintain)
2. Redact in HTTP response handler (rejected: logic scattered, harder to test in isolation)
3. Use a single `visibility_level` string field (rejected: less type-safe, requires string parsing)

---

## Consequences

### Affected Services/Files

| Service | File | Change |
|---------|------|--------|
| ai_stack | `ai_stack/diagnostics_envelope.py` | Add DegradationEvent, extend DiagnosticsEnvelope, implement to_response() |
| world-engine | `world-engine/app/story_runtime/manager.py` | Collect degradation_events during turn execution |
| world-engine | `world-engine/app/api/http.py` | Call `to_response(context="operator")` in HTTP responses |
| backend | `backend/app/observability/langfuse_adapter.py` | Phase B: fill cost_summary with real values |
| tests | `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py` | 10 Phase A tests covering degradation timeline, cost summary, tiered visibility |

### Data Contracts

**DiagnosticsEnvelope now includes**:
```python
degradation_timeline: list[DegradationEvent]  # Empty if no degradation
cost_summary: dict  # {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
```

**DegradationEvent structure**:
```python
@dataclass
class DegradationEvent:
    marker: str  # e.g., "FALLBACK_USED", "RETRY_ACTIVE"
    severity: str  # "minor", "moderate", "critical"
    timestamp: str  # ISO8601
    recovery_successful: bool
    recovery_latency_ms: int | None
    context_snapshot: dict  # e.g., {"turn_number": 42}
    span_ids: list[str]  # Empty in Phase A, filled in Phase B
```

### Phase B/C Dependencies

- **Phase B** (Langfuse): Fills cost_summary with real token counts and cost_breakdown
- **Phase C** (Governance): Uses degradation_timeline to implement cost-aware degradation (LDSS shortening when budget critical)
- **Phase C** (Evaluation): Uses quality_class + degradation_signals to train auto-tuning evaluator

### Backward Compatibility

✅ **No breaking changes**:
- New fields have sensible defaults (empty list, zero dict)
- Existing code reading DiagnosticsEnvelope continues to work
- `to_response()` method is new, doesn't modify existing behavior
- HTTP endpoints can opt-in to redaction gradually

---

## Validation Evidence

### Unit Tests (Phase A)

| Test | File | Status |
|------|------|--------|
| `test_mvp04_degradation_timeline_has_severity_and_timestamp` | gate tests | ✅ PASS |
| `test_mvp04_degradation_timeline_populated_with_signals` | gate tests | ✅ PASS |
| `test_mvp04_cost_summary_present_with_zeros_in_phase_a` | gate tests | ✅ PASS |
| `test_mvp04_to_response_operator_redacts_hashes_and_costs` | gate tests | ✅ PASS |
| `test_mvp04_to_response_langfuse_has_full_technical_data` | gate tests | ✅ PASS |
| `test_mvp04_to_response_super_admin_has_everything` | gate tests | ✅ PASS |

**Total Phase A tests**: 10/10 PASS

### Integration Tests

| Test | Evidence |
|------|----------|
| Turn executes and produces DiagnosticsEnvelope | `test_mvp04_annette_turn_produces_diagnostics_envelope` ✅ |
| Degradation signals trigger DegradationEvent | `test_mvp04_degradation_timeline_populated_with_signals` ✅ |
| HTTP endpoint returns to_response("operator") | Integration tested in HTTP layer ✅ |

### Non-Placeholder Evidence Check

```python
def validate_evidence_consistency(self) -> tuple[bool, str | None]:
    """Reject empty/placeholder diagnostics."""
    # Fails if decision_count=0 and scene_block_count=0 (no LDSS evidence)
    # Fails if quality_class=normal but degradation_signals empty (inconsistent)
    # Fails if langfuse_enabled=True but trace_id empty (incomplete trace)
```

All Phase A tests verify that diagnostics are non-placeholder and tied to real session/turn/trace IDs.

---

## Operational Gate Impact

**docker-up.py**: No changes (no new services)  
**tests/run_tests.py**: `--mvp4` flag includes Phase A tests ✅  
**GitHub workflows**: `engine-tests.yml` runs architecture-gates job ✅  
**TOML/tooling**: pytest marker `@pytest.mark.mvp4` auto-discovered ✅  

---

## Related ADRs

- **ADR-MVP1-016**: Operational Test and Startup Gates (MVP4 inherits this discipline)
- **ADR-MVP3-011**: Live Dramatic Scene Simulator (MVP4 observes LDSS)
- **ADR-MVP4-002**: Langfuse Integration (Phase B fills cost_summary)
- **ADR-MVP4-003**: Evaluation Pipeline (uses degradation_timeline for tuning)

---

## Glossary

| Term | Definition |
|------|-----------|
| **DegradationEvent** | Single marker during turn execution (e.g., fallback invoked, retry active) |
| **degradation_timeline** | List of all DegradationEvents in a turn (empty if no degradation) |
| **cost_summary** | Token counts and cost per turn (zeros in Phase A, real values in Phase B) |
| **tiered visibility** | `to_response(context)` adapts envelope content based on audience (operator/langfuse/super-admin) |
| **trace_id correlation** | Same trace_id appears in diagnostics, Langfuse spans, and logs for RCA |

---

## Future Considerations

- **Phase B**: LangfuseAdapter populates cost_summary with real token counts
- **Phase C**: Cost-aware degradation uses degradation_timeline to decide LDSS shortening
- **Phase C**: Auto-tuning evaluator trains on degradation_timeline to predict failures
- **MVP5**: Session Replay UI correlates Langfuse trace with degradation_timeline for operator debugging
