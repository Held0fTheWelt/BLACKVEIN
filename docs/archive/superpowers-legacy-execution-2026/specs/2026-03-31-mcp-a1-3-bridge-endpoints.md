# MCP A1.3: Bridge Operator Endpoints (Design Spec)

**Date:** 2026-03-31
**Phase:** MCP Phase A1.3
**Scope:** Minimal read-only JSON endpoints for operator tooling
**Status:** Design approved, ready for implementation

---

## Overview

MCP A1.3 implements four read-only JSON endpoints that expose in-memory session data without adding persistence or logging infrastructure. These are **bridge endpoints**: they make existing runtime state safely accessible to operator tools while keeping W3.2 persistence work separate.

**Hard constraint:** No 501 stubs remain. All four endpoints return 200/404/401/503 with valid JSON.

---

## Philosophy

- **Minimal change:** Replace existing 501 stubs in-place, add small auth module.
- **Read-only:** No writes, no new side effects beyond token validation.
- **No new contracts:** Do not add logging, guarding, or tracing infrastructure.
- **Future-proof but honest:** Diagnostics envelope allows fields that will be populated in W3.2, but explicitly warn that they're not recorded yet.
- **Volatile by design:** All endpoints warn that data is in-memory and lost on restart.

---

## Endpoints

### 1. GET `/api/v1/sessions/<session_id>` — Session Snapshot

**Purpose:** Full session metadata + current canonical state snapshot.

**Auth:** Requires `Authorization: Bearer <MCP_SERVICE_TOKEN>` header.

**Success (200):**
```json
{
  "session_id": "sess-abc123",
  "module_id": "god_of_carnage",
  "module_version": "1.0.0",
  "current_scene_id": "act-1",
  "status": "active",
  "turn_counter": 3,
  "execution_mode": "mock",
  "adapter_name": "mock_adapter",
  "canonical_state": { /* full world state */ },
  "canonical_state_truncated": false,
  "warnings": ["in_memory_session_state_is_volatile"]
}
```

**Note on canonical_state:**
- If canonical_state is small (~< 50KB), return it fully as-is.
- If large, return `canonical_state_summary: { "keys": [...], "total_fields": N }` and set `canonical_state_truncated: true`.
- Implementation must be deterministic (same session always returns same truncation).

**Errors:**
- 401: Missing/invalid token
- 403: Misconfigured (MCP_SERVICE_TOKEN not set)
- 404: Session not found

---

### 2. GET `/api/v1/sessions/<session_id>/state` — Canonical State Only

**Purpose:** World state + current scene + metadata (minimal wrapper).

**Auth:** Requires Bearer token.

**Success (200):**
```json
{
  "session_id": "sess-abc123",
  "current_scene_id": "act-1",
  "canonical_state": { /* full world state */ },
  "canonical_state_truncated": false,
  "warnings": ["in_memory_session_state_is_volatile"]
}
```

**Errors:** Same as snapshot endpoint.

---

### 3. GET `/api/v1/sessions/<session_id>/logs` — Event History

**Purpose:** Turn summaries / event log (always returns 200 or 404, never 501).

**Auth:** Requires Bearer token.

**Success (200):**
```json
{
  "session_id": "sess-abc123",
  "events": [],
  "total": 0,
  "warnings": [
    "history_not_available_in_current_runtime",
    "in_memory_session_state_is_volatile"
  ]
}
```

**Behavior:**
- Always return 200 with empty `events` list in A1.3 (no logging infrastructure).
- If existing runtime already populates an event list (unlikely in current codebase), expose it read-only.
- Do NOT introduce new append-to-log behavior.

**Errors:** Same as snapshot endpoint.

---

### 4. GET `/api/v1/sessions/<session_id>/diagnostics` — Debug Bundle

**Purpose:** Future-proof diagnostics envelope + current runtime indicators.

**Auth:** Requires Bearer token.

**Success (200):**
```json
{
  "session_id": "sess-abc123",
  "turn_counter": 3,
  "current_scene_id": "act-1",
  "capabilities": {
    "has_turn_history": false,
    "has_guard_outcome": false,
    "has_trace_ids": false
  },
  "guard": {
    "outcome": null,
    "rejected_reasons": [],
    "last_error": null
  },
  "trace": {
    "trace_ids": []
  },
  "warnings": [
    "in_memory_session_state_is_volatile",
    "diagnostics_limited_to_current_runtime",
    "guard_and_trace_not_recorded_yet"
  ]
}
```

**Behavior:**
- Return the stable envelope with null/empty fields for guard/trace/etc.
- Populate `capabilities` booleans ONLY from fields that already exist in SessionState/RuntimeSession.
- Do NOT invent or add new state writes to populate guard/trace.
- Include explicit warnings about what's not yet recorded.

**Errors:** Same as snapshot endpoint.

---

## Service Token Authentication

### Decorator: `@require_mcp_service_token`

**Location:** `backend/app/api/v1/auth.py`

**Validation logic:**
1. Read `MCP_SERVICE_TOKEN` from environment (required, no config fallback, no default dev token).
2. If missing or empty string:
   - Return `{ "error": { "code": "MISCONFIGURED", "message": "MCP_SERVICE_TOKEN not configured" } }` with status **503**.
3. Extract token from header: `Authorization: Bearer <token>`.
4. If header missing or doesn't start with `Bearer `:
   - Return `{ "error": { "code": "UNAUTHORIZED", "message": "Missing or invalid Authorization header" } }` with status **401**.
5. Compare provided token to `MCP_SERVICE_TOKEN` using **constant-time comparison** (`hmac.compare_digest`).
6. If mismatch:
   - Return `{ "error": { "code": "UNAUTHORIZED", "message": "Invalid token" } }` with status **401**.
7. If valid, proceed to route handler.

**Scoping:**
- Apply `@require_mcp_service_token` ONLY to the 4 operator endpoints.
- Do NOT apply to public web routes (e.g., `/play/*`, `/login`, etc.).

---

## Error Envelope

All errors follow this consistent JSON shape:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

**Standard codes:**
- `UNAUTHORIZED` (401) — Invalid or missing token
- `MISCONFIGURED` (503) — MCP_SERVICE_TOKEN not set
- `NOT_FOUND` (404) — Session not found

---

## Data Source Consistency

### Turn Counter
- Use `SessionState.turn_counter` as the canonical source.
- Do NOT mix `runtime_session.turn_counter` and `state.turn_counter` in different endpoints.
- All four endpoints report the same turn counter for a given session.

### Canonical State
- Always read from `SessionState.canonical_state`.
- Apply truncation rules consistently (same logic in snapshot and state endpoints).

### Session Lookup
- Always use `session_store.get_session(session_id)` to retrieve RuntimeSession.
- Never access the internal `_runtime_sessions` dict directly.

---

## Files to Create / Modify

**New:**
- `backend/app/api/v1/auth.py` — Service token validation decorator (~50 lines)

**Modified:**
- `backend/app/api/v1/session_routes.py` — Replace 4 stubs with implementations
- `backend/tests/test_session_routes.py` — Add 10 new tests

---

## Testing Requirements

**Functional tests (add to test_session_routes.py):**
1. 401 when Authorization header missing
2. 401 when Authorization header has wrong token
3. 503 when MCP_SERVICE_TOKEN env var not set (and endpoint is called)
4. 404 for non-existent session
5. 200 for GET `/sessions/<id>` with valid token and existing session (check all fields)
6. 200 for GET `/sessions/<id>/state` with valid token (check state + warnings)
7. 200 for GET `/sessions/<id>/logs` returns empty events + warnings (never 501)
8. 200 for GET `/sessions/<id>/diagnostics` returns envelope with null guard/trace + warnings

**Additional tests:**
9. Ensure all responses include `warnings` array containing `"in_memory_session_state_is_volatile"` (snapshot, state, diagnostics).
10. Ensure canonical_state truncation behavior is deterministic (same session always truncates the same way).

---

## No Persistence / No Logging in A1.3

**Explicit out-of-scope for this phase:**
- ❌ Event logging during turn execution
- ❌ Guard outcome recording
- ❌ Trace ID collection
- ❌ Database persistence
- ❌ Session recovery / resumption

**Deferred to W3.2:** All of the above. A1.3 reads what's already in memory; W3.2 adds the infrastructure to record it durably.

---

## Implementation Guardrails

1. ✅ Replace stubs directly in `session_routes.py`.
2. ✅ Use small helper functions or inline JSON building (no new service layers).
3. ✅ Import from `session_store.get_session()` (stable API).
4. ✅ No circular imports; use local imports only if needed (add comments).
5. ✅ Constant-time token comparison (`hmac.compare_digest`).
6. ✅ All 4 endpoints must return 200/401/403/404, never 501.
7. ✅ Warnings are explicit and honest.

---

## Success Criteria

- [ ] All 4 endpoints implemented and return proper JSON (no 501 stubs).
- [ ] Service token auth decorator works and is scoped to operator endpoints only.
- [ ] 401/403/404 error responses include standard error envelope.
- [ ] All responses include appropriate warnings about in-memory volatility.
- [ ] Tests pass: auth (3), happy path (4), error cases (3).
- [ ] No new logging/guard/trace infrastructure added to runtime.
- [ ] turn_counter is consistent across all endpoints.
- [ ] canonical_state truncation (if implemented) is deterministic.

---

## Next Steps

After approval:
1. Write implementation plan (writing-plans skill).
2. Execute plan via subagent-driven-development (Haiku model for mechanical tasks).
3. Review code and run tests.
4. Commit with message: `feat(api): add A1.3 operator session read endpoints with service token auth`.
5. Update docs: `docs/mcp/A1_3_operator_endpoints.md` + `docs/mcp/06_M0_backend_readiness_gaps.md`.
