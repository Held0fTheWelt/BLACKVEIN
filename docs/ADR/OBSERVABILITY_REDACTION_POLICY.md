# ADR: Observability Redaction and Trace Correlation Policy

**Status**: APPROVED

**Date**: 2026-04-24

---

## Context

Langfuse traces will contain:
- Prompts sent to AI models (may contain context about players/world)
- Retrieved documents (context from database)
- Validation decisions (field-level changes)
- Runtime metadata (session IDs, turn numbers, module IDs)
- Generated outputs (AI-produced narrative)

**Privacy concern**: Traces could expose:
- Player names or identifying information
- Plot details not yet revealed
- Session-specific context that should remain private
- Internal system details (database queries, row IDs)

---

## Decision

### What IS Captured

With LANGFUSE_CAPTURE_PROMPTS=true:
- Prompts sent to LLM (includes context summary, not raw unstructured data)
- Model name, provider name
- Token counts
- Latency metrics
- Validation status and reasons

With LANGFUSE_CAPTURE_OUTPUTS=true:
- LLM completion text (AI-generated narrative)
- Structured output (parsed spoken_lines, action_lines with actor IDs)
- Parsing errors if any

With LANGFUSE_CAPTURE_RETRIEVAL=true (default false):
- Retrieval query (what was asked)
- Document count retrieved
- First 5 documents only (metadata, not full text)
- Retrieval failures

### What is NEVER Captured

- Player real names (use player_id instead)
- Authentication tokens, cookies, session secrets
- Database passwords or service credentials
- API keys or bearer tokens
- Private user metadata beyond pseudonymized IDs
- Raw unredacted passwords or PII

### Redaction Behavior

**Strict Mode** (default):
- All values matching key patterns like "password", "token", "secret", "auth", "apikey", "bearer", "cookie" are redacted to "***" or partially masked
- Prompts/outputs are captured but NOT stored unencrypted
- All metadata keys are checked; any with sensitive names are masked

**Relaxed Mode**:
- Same as strict but allows full prompts/outputs if explicitly enabled
- Redacts only explicitly marked secrets (env vars, creds)

**None Mode**:
- No redaction (only for fully disconnected local/test environments)
- Not recommended for production

---

## Correlation IDs

Every trace includes:

```json
{
  "session_id": "sess_xxx",
  "run_id": "run_yyy",
  "turn_id": "turn_123",
  "module_id": "god_of_carnage",
  "scene_id": "scene_hallway_zzz",
  "player_id": "player_pseudonymized_hash",
  "request_id": "req_trace_id",
  "trace_id": "trace_id",
  "runtime_mode": "live",
  "model": "claude-3-sonnet",
  "provider": "anthropic",
  "fallback_used": false,
  "degraded_mode": false
}
```

These fields allow:
- Trace → Session → Player (pseudonymized)
- Trace → Turn (for sequence analysis)
- Trace → Module (for feature-specific analysis)
- Correlation with admin diagnostics

---

## Implementation

### LangfuseAdapter Redaction

```python
def _redact_value(self, value: Any, key: str = "") -> Any:
    """Redact sensitive values based on key patterns."""
    sensitive_patterns = [
        "password", "token", "secret", "key", "auth",
        "credential", "apikey", "bearer", "cookie"
    ]
    if any(pattern in key.lower() for pattern in sensitive_patterns):
        if len(value) > 4:
            return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
        return "***"
    return value
```

### Prompt Capture Control

```python
# Respect LANGFUSE_CAPTURE_PROMPTS setting
if self.config.capture_prompts:
    prompt_to_send = prompt  # Include full prompt
else:
    prompt_to_send = "[REDACTED]"  # Replace with marker

# Always redact secrets from prompts
prompt_to_send = self._sanitize_metadata({"prompt": prompt_to_send})
```

### Player Pseudonymization

Never send raw player names or IDs:
```python
# WRONG:
"player_name": player.name  # Exposes real identity

# RIGHT:
"player_id": hash(player.id + salt)  # Pseudonymized, consistent
```

---

## Validation

- [ ] Test redaction removes passwords/tokens
- [ ] Test captured prompts don't include raw player data
- [ ] Test LANGFUSE_CAPTURE_PROMPTS=false works
- [ ] Test LANGFUSE_CAPTURE_RETRIEVAL=false is default
- [ ] Test correlation IDs present in all traces
- [ ] Manual review of a full trace for PII leakage

---

## References

- Langfuse: https://langfuse.com/docs/security/data-residency
- Implementation: `backend/app/observability/langfuse_adapter.py`
- Configuration: `.env.example`
