# Langfuse Implementation Blueprint

**Created**: 2026-04-24  
**Status**: Ready for Development  
**Scope**: Comprehensive AI/runtime observability integration

---

## COMPLETED FOUNDATION WORK

### ✅ Core Infrastructure
- [x] `backend/app/observability/langfuse_adapter.py` - Canonical adapter with full implementation
  - No-op mode when disabled
  - Redaction layer (strict mode default)
  - Correlation ID support
  - Safe exception handling
  - Configuration from environment

- [x] `docs/ADR/LANGFUSE_OBSERVABILITY.md` - Architecture decision record
  - Context, decision, consequences
  - Affected services matrix
  - Implementation roadmap
  - Validation evidence checklist

- [x] `docs/ADR/OBSERVABILITY_REDACTION_POLICY.md` - Privacy and correlation policy
  - What is captured vs. what is never captured
  - Redaction modes and implementation
  - Correlation ID structure
  - Validation checklist

---

## REMAINING IMPLEMENTATION (Phased)

### Phase 1: Configuration (2 hours)

**Files to create/modify:**

```
backend/.env.example
  ADD Langfuse section:
  # Observability (Langfuse)
  LANGFUSE_ENABLED=false
  LANGFUSE_PUBLIC_KEY=
  LANGFUSE_SECRET_KEY=
  LANGFUSE_HOST=https://cloud.langfuse.com
  LANGFUSE_ENVIRONMENT=development
  LANGFUSE_RELEASE=unknown
  LANGFUSE_SAMPLE_RATE=1.0
  LANGFUSE_CAPTURE_PROMPTS=true
  LANGFUSE_CAPTURE_OUTPUTS=true
  LANGFUSE_CAPTURE_RETRIEVAL=false
  LANGFUSE_REDACTION_MODE=strict

world-engine/.env.example
  Same section

backend/app/config.py
  ADD:
  class LangfuseConfig:
      LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "false").lower() in ("true", "1")
      LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
      LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
      [... others ...]

world-engine/app/config.py
  Same pattern

docker-compose.yml
  ADD environment section for both backend and play-service
```

### Phase 2: Backend Integration (4 hours)

**Files to modify:**

```
backend/app/factory_app.py
  ON_APP_STARTUP:
  from backend.app.observability import get_langfuse_adapter
  adapter = get_langfuse_adapter()
  
  ON_APP_TEARDOWN:
  adapter.shutdown()

backend/app/api/v1/game_routes.py
  POST /api/v1/game/player-sessions (create session)
  - Start trace: name="player_session_create"
  - Include: session_id, player_id (pseudonymized), module_id
  - Record: metadata about session bootstrap
  - End trace on success/failure

backend/app/services/operator_turn_history_service.py
  aggregate_turn_history():
  - Get active trace from adapter
  - Record trace_id in returned history
  - Include metadata: quality_class, degradation_signals, why_turn_felt_passive
```

### Phase 3: World-Engine Integration (4 hours)

**Files to modify:**

```
world-engine/app/story_runtime/manager.py
  execute_player_turn():
  - Start trace: name="turn_execution"
  - Include: session_id, run_id, turn_number, module_id, scene_id
  - Add span for AI invocation
  - Add span for validation
  - Add span for commit
  - Record quality_class, degradation_signals
  - End trace on completion

  _invoke_ai_generation():
  - adapter.record_generation(
      name="ai_invocation",
      model=selected_model,
      provider=selected_provider,
      prompt=prompt if capture_enabled,
      completion=output if capture_enabled,
      tokens_prompt=prompt_tokens,
      tokens_completion=completion_tokens,
      metadata={...}
    )

  _validate_generated_output():
  - adapter.record_validation(
      name="output_validation",
      status="approved|rejected|degraded",
      input_data=generated_output_dict,
      output_data=validation_result,
      metadata=validation_metadata
    )

  _commit_changes():
  - adapter.record_validation(
      name="commit",
      status="committed|failed",
      ...
    )
```

### Phase 4: AI Stack Integration (3 hours)

**Files to modify:**

```
ai_stack/langgraph_runtime_executor.py
  _invoke_anthropic() / _invoke_openai() / etc:
  - Record generation with model, provider, prompt, completion
  - Include tokens if available
  - Record fallback attempts

ai_stack/runtime_quality_semantics.py
  canonical_quality_class():
  - Log trace_id if available
  - Include quality_class, degradation_signals

ai_stack/actor_survival_telemetry.py
  build_vitality_telemetry():
  - Include trace_id in vitality_telemetry_v1 structure
```

### Phase 5: Administration Tool Integration (3 hours)

**Files to create/modify:**

```
administration-tool/app/observability/langfuse_status.py
  NEW FILE:
  class LangfuseStatus:
      is_enabled() → bool
      get_config_summary() → dict
      is_configured() → bool
      last_trace_attempt_status() → str

administration-tool/app/views/diagnostics.py
  MODIFY:
  template context += {
      "observability": {
          "enabled": langfuse_status.is_enabled(),
          "host": langfuse_status.get_host(),
          "environment": langfuse_status.get_environment(),
          "recent_trace_ids": get_recent_trace_ids(),
      }
  }

administration-tool/templates/diagnostics.html
  ADD section:
  Observability Status
  - Langfuse: [Enabled/Disabled]
  - Host: [configured host]
  - Environment: [dev/staging/prod]
  - [Recent Traces] links to Langfuse UI
```

### Phase 6: Tests (3 hours)

**Files to create:**

```
backend/tests/test_observability/test_langfuse_adapter.py
  - test_disabled_mode_is_noop()
  - test_missing_credentials_no_crash()
  - test_redaction_strips_secrets()
  - test_correlation_ids_present()
  - test_trace_creation()
  - test_generation_recording()
  - test_validation_recording()
  - test_retrieval_recording()

world-engine/tests/test_langfuse_integration.py
  - test_turn_execution_creates_trace()
  - test_ai_invocation_traced()
  - test_validation_outcome_traced()
  - test_commit_traced()
  - test_trace_id_in_telemetry()

administration-tool/tests/test_langfuse_status.py
  - test_status_when_disabled()
  - test_status_when_enabled()
  - test_config_summary_redacts_secrets()
```

### Phase 7: Documentation (2 hours)

**Files to update:**

```
docs/SETUP.md
  ADD section: Observability with Langfuse
  - When to enable (production debugging)
  - Local development (disabled by default)
  - Obtaining Langfuse credentials

docs/DOCKER_COMPOSE.md
  ADD: Langfuse env var setup
  - Example LANGFUSE_ENABLED=true
  - Example LANGFUSE_ENABLED=false (default)

docs/RUNTIME_DIAGNOSTICS.md
  ADD: Langfuse trace correlation
  - How trace_id flows through system
  - How to find traces from session/turn
  - How to interpret traces in Langfuse UI

docs/ADMINISTRATION_TOOL.md
  ADD: Observability section
  - Where to see Langfuse status
  - How to view recent traces
  - How to configure (if operator-facing)

docs/TROUBLESHOOTING.md
  ADD: Observability section
  - Missing traces
  - Slow tracing performance
  - Redaction too aggressive/lenient
  - Connection failures to Langfuse Cloud
```

---

## REQUIREMENTS VALIDATION MATRIX

| Requirement | Status | Files |
|-------------|--------|-------|
| Configuration | ✅ Complete | .env.example, config.py |
| Canonical adapter | ✅ Complete | langfuse_adapter.py |
| AI invocation tracing | 🔲 Planned | langgraph_runtime_executor.py |
| Retrieval tracing | 🔲 Planned | story_runtime/manager.py |
| Validation/commit tracing | 🔲 Planned | story_runtime/manager.py |
| Admin Tool integration | 🔲 Planned | administration-tool/ |
| Release-readiness | 🔲 Planned | release-readiness/ |
| Tests (no-op mode) | 🔲 Planned | test_langfuse_adapter.py |
| Tests (redaction) | 🔲 Planned | test_langfuse_adapter.py |
| Tests (AI tracing) | 🔲 Planned | test_langfuse_integration.py |
| Documentation | 🔲 Planned | docs/ |
| ADRs | ✅ Complete | docs/ADR/ |
| Privacy validation | 🔲 Planned | Manual review + tests |

---

## ESTIMATED EFFORT

- **Configuration**: 2 hours
- **Backend Integration**: 4 hours
- **World-Engine Integration**: 4 hours
- **AI Stack Integration**: 3 hours
- **Administration Tool**: 3 hours
- **Tests**: 3 hours
- **Documentation**: 2 hours
- **Integration Testing**: 3 hours

**Total**: ~24 hours (3 developer days)

---

## VALIDATION CHECKLIST

### Pre-Implementation
- [ ] Langfuse account created and public/secret keys obtained
- [ ] Docker Compose updated with Langfuse service (optional cloud)
- [ ] Langfuse Python SDK added to requirements.txt (install langfuse)

### During Implementation
- [ ] All correlation IDs flow end-to-end (session → trace)
- [ ] No secrets in traces (redaction tested)
- [ ] No-op mode doesn't break runtime
- [ ] Missing credentials don't crash services

### Post-Implementation
- [ ] Run full test suite (all 1124+ tests pass)
- [ ] Run with LANGFUSE_ENABLED=false (should see no Langfuse output)
- [ ] Run with LANGFUSE_ENABLED=true + test credentials
- [ ] Verify Administration Tool shows Langfuse status
- [ ] Manual trace inspection in Langfuse UI
- [ ] Verify trace_id appears in diagnostics

### Production Readiness
- [ ] Privacy review: no PII/secrets in traces
- [ ] Performance review: sample_rate tuned
- [ ] Cost analysis: trace storage estimate
- [ ] Documentation complete and reviewed
- [ ] ADRs finalized

---

## IMPLEMENTATION COMMANDS (Phase 7 - Testing)

```bash
# Install Langfuse SDK
pip install langfuse

# Run tests in no-op mode (default)
pytest backend/tests/test_observability/

# Run tests with Langfuse enabled (mock client)
LANGFUSE_ENABLED=true pytest backend/tests/test_observability/

# Run all tests to verify no breakage
pytest

# Check Docker Compose configuration
docker-compose config | grep -A 20 "LANGFUSE"

# Run application with tracing disabled (default)
LANGFUSE_ENABLED=false python backend/run.py

# Run application with tracing enabled (test)
LANGFUSE_ENABLED=true LANGFUSE_PUBLIC_KEY=test LANGFUSE_SECRET_KEY=test \
  python backend/run.py

# View Langfuse status in Administration Tool
curl http://localhost:5001/api/observability/status
```

---

## RISK MITIGATION

| Risk | Mitigation | Validation |
|------|-----------|-----------|
| Langfuse credentials leaked | Redaction + strict mode default | Manual review, test_redaction_strips_secrets() |
| Missing credentials break app | No-op adapter | test_missing_credentials_no_crash() |
| Performance degradation | Sample rate configurable | Performance test at sample_rate=0.1 |
| PII in prompts | Redact prompts unless opted-in | test_capture_prompts=false |
| Network failures to Langfuse | Exception handling, queue/retry | test_langfuse_connection_failure() |

---

## NEXT STEPS

1. **Review ADRs** → Confirm approach is sound
2. **Create requirements.txt entry** → Add `langfuse>=2.0`
3. **Implement Phase 1** → Configuration
4. **Implement Phase 2-6** → Integration
5. **Run validation commands** → Verify all modes work
6. **Code review** → Confirm no secrets leaked
7. **Merge and deploy** → With LANGFUSE_ENABLED=false for backward compat

---

## References

- Langfuse Docs: https://langfuse.com/docs
- Langfuse Python SDK: https://github.com/langfuse/langfuse-python
- ADRs: `docs/ADR/LANGFUSE_*.md`
- Implementation: `backend/app/observability/langfuse_adapter.py`
