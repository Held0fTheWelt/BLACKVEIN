# ADR: Langfuse as Canonical AI/Runtime Observability Provider

**Status**: APPROVED

**Date**: 2026-04-24

**Decision Makers**: Runtime Architecture, DevOps, Observability Engineering

---

## Context

World of Shadows executes complex multi-turn AI narratives with:
- Dynamic actor selection and responder nomination
- Conditional generation paths (fallback, degradation, retry)
- Real-time validation with field-level guards
- Structured output parsing with recovery branches
- Story window packaging with visibility markers
- Vitality telemetry and passivity detection

Current diagnostics are:
- Session audit logs (after-the-fact, not correlated)
- Runtime turn contracts (in-memory, not persisted)
- Administration Tool readiness views (static config only)
- No unified trace correlation across services

Operators need to answer:
- Which AI model was actually invoked for this turn?
- What context was retrieved and sent?
- Why was the generated output rejected/degraded?
- Which service made which decision?
- What was the full execution trace for session X?

---

## Decision

**Implement Langfuse as the canonical observability provider for:**
- AI invocation tracing (provider, model, prompt, completion, latency, tokens)
- Retrieval tracing (query, context window, document count, failures)
- Validation/commit tracing (status, rejection reasons, guard outcomes)
- Runtime diagnostics correlation (session_id → trace_id → operator inspection)
- Administration Tool operator surfaces (enabled/disabled status, trace links)
- Release-readiness gates (Langfuse configured or explicitly disabled)

**Requirements:**
- Optional and disabled by default (no credentials required for local dev)
- One canonical adapter layer (no scattered direct Langfuse calls)
- Safe: graceful degradation if disabled or credentials missing
- Secure: redact secrets before tracing
- Correlated: all traces link to session/run/turn/module/scene

---

## Affected Services

1. **backend**
   - config.py: Add LangfuseConfig
   - observability/langfuse_adapter.py: Canonical adapter
   - factory_app.py: Initialize Langfuse on startup
   - api/v1/game_routes.py: Trace player session creation
   - api/v1/play_qa_diagnostics_routes.py: Include trace IDs in diagnostics

2. **world-engine/play-service**
   - config.py: Add Langfuse settings
   - app/story_runtime/manager.py: Trace turn execution, AI invocation, commit
   - app/story_runtime/commit_models.py: Trace validation outcomes

3. **ai_stack**
   - langgraph_runtime_executor.py: Trace model invocation, fallback paths
   - runtime_quality_semantics.py: Trace quality assessment
   - actor_survival_telemetry.py: Include trace_id in vitality telemetry

4. **frontend** (optional)
   - routes_play.py: Include trace_id in diagnostics view (operator-facing)

5. **administration-tool**
   - observability/langfuse_status.py: Readiness checks, current config
   - templates/diagnostics.html: Show trace links for recent turns

6. **.env.example** and Docker Compose
   - Add all Langfuse env vars with defaults

---

## Consequences

### Benefits
- **Observability**: Complete trace of AI decision-making and runtime behavior
- **Correlation**: Single trace_id links session → turn → provider → rejection → operator inspection
- **Privacy**: Redaction layer prevents secrets from being exposed
- **Optional**: Langfuse disabled is valid; no credentials required for development
- **Operator-friendly**: Administration Tool shows status and trace links

### Risks
- Langfuse client adds ~50KB to dependencies
- Network latency if Langfuse is slow (mitigated by sample_rate and async flush)
- Trace storage costs if enabled in production (offset by diagnostic value)
- Requires careful redaction to avoid leaking player data

### Mitigation
- Langfuse disabled by default; must be explicitly enabled
- No credentials required if disabled
- Redaction in strict mode by default (sanitizes prompts/outputs)
- Tests validate no-op mode doesn't break runtime
- Sample rate configurable

---

## Alternatives Considered

1. **No Observability** - Rejected: Too hard to debug production issues
2. **Custom Tracing** - Rejected: Duplicates Langfuse work, harder to maintain
3. **DataDog/New Relic** - Considered but Langfuse is lighter, AI/LLM focused
4. **Direct Langfuse Calls** - Rejected: Scattered across codebase, hard to redact/manage

---

## Implementation Steps

1. ✓ Create `backend/app/observability/langfuse_adapter.py` (canonical adapter)
2. Add Langfuse configuration to all services
3. Instrument AI invocation paths
4. Instrument retrieval paths
5. Instrument validation/commit paths
6. Add Administration Tool integration
7. Add tests (no-op mode, missing credentials, redaction)
8. Update documentation and Docker Compose
9. Create Langfuse client initialization hook
10. Validate with e2e tests

---

## Validation Evidence

- [ ] Tests prove no-op mode works
- [ ] Tests prove missing credentials don't break runtime
- [ ] Tests prove redaction strips secrets
- [ ] All AI invocation paths traced
- [ ] All retrieval operations traced
- [ ] All validation outcomes traced
- [ ] Administration Tool shows status
- [ ] Release-readiness handles enabled/disabled
- [ ] Docker Compose example shows Langfuse config

---

## Related Files

- Implementation: `backend/app/observability/langfuse_adapter.py`
- Configuration: `backend/app/config.py`, `.env.example`
- Tests: `tests/test_observability/test_langfuse_adapter.py`
- ADR: `docs/ADR/OBSERVABILITY_REDACTION_POLICY.md`

---

## References

- Langfuse Docs: https://langfuse.com/docs
- Correlation Policy: `docs/ADR/OBSERVABILITY_REDACTION_POLICY.md`
- Admin Readiness: `docs/ADR/ADMIN_READINESS_LANGFUSE.md`
