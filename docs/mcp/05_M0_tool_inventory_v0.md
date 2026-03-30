# MCP Tool Inventory v0 (Phase A) · World of Shadows

Version: 0.1
Phase: **A (Operator/Dev Tooling, out-of-band)**

## ⚠️ PHASE A READINESS: PARTIAL

**Only 2 of 6 P0 tools are currently functional.** Four tools map to backend endpoints that return 501 "Not Implemented" stubs (deferred to W3.2 persistence work). See "Blocked P0 Tools" below.

## Tool Priorities

- **P0:** Must be available for A1 (for real operator value)
- **P1:** Optional for A1 (nice-to-have)
- **P2:** For later phases (B/C)

---

## P0 Tools (A1)

### 1) `wos.system.health` (read) ✅ READY

**Purpose:** Backend reachable, basic info.
**Backend mapping:** `GET /health` (web route)
**Status:** ✅ Fully implemented

**Input**
```json
{}
```

**Output (data)**
```json
{
  "status": "ok",
  "backend_time": "ISO",
  "version": "optional"
}
```

---

### 2) `wos.session.create` (read) ✅ READY

**Purpose:** Start story session (God of Carnage).
**Backend mapping:** `POST /api/v1/sessions`
**Repo evidence:** `backend/app/api/v1/session_routes.py:27-71`
**Status:** ✅ Fully implemented, returns 201 Created

**Input**
```json
{ "module_id": "god_of_carnage" }
```

**Output (data)**
```json
{
  "session_id": "string",
  "module_id": "string",
  "current_scene_id": "string",
  "turn_counter": 0,
  "execution_mode": "mock",
  "adapter_name": "mock"
}
```

---

### ❌ BLOCKED P0 TOOLS (4 of 6) — Deferred to W3.2

The following tools are documented but **cannot be used** in Phase A because their backend endpoints return 501 "Not Implemented" stubs:

### 3) `wos.session.get` (read) ❌ BLOCKED

**Purpose:** Retrieve session state snapshot.
**Backend mapping:** `GET /api/v1/sessions/<session_id>`
**Repo evidence:** `backend/app/api/v1/session_routes.py:74-82`
**Status:** ❌ Returns 501 "Session retrieval deferred to W3.2 (persistence layer not yet implemented)"
**Blocked:** Wait for W3.2 session persistence layer

**Expected input**
```json
{ "session_id": "string" }
```

**Expected output (data)**
```json
{
  "session_id": "string",
  "module_id": "string|null",
  "module_version": "string|null",
  "turn_counter": 0,
  "status": "active",
  "canonical_state": {},
  "context_layers": {
    "has_session_history": true,
    "has_short_term": true,
    "current_scene": "string|null"
  }
}
```

---

### 4) `wos.session.execute_turn` (read) ❌ BLOCKED

**Purpose:** Execute turn (player action/gameplay turn).
**Backend mapping:** `POST /api/v1/sessions/<session_id>/turns`
**Repo evidence:** `backend/app/api/v1/session_routes.py:85-93`
**Status:** ❌ Returns 501 "Turn execution deferred to W3.2 (persistence layer not yet implemented)"
**Blocked:** Wait for W3.2 persistence layer

**Expected input**
```json
{ "session_id": "string", "operator_input": "string" }
```

**Expected output (data)**
```json
{
  "turn_number": 1,
  "result_status": "success|error",
  "guard_outcome": "accepted|rejected|unknown",
  "updated_state": { "scene_id": "string|null", "turn_counter": 1 }
}
```

---

### 5) `wos.session.logs` (read) ❌ BLOCKED

**Purpose:** Retrieve event logs for session.
**Backend mapping:** `GET /api/v1/sessions/<session_id>/logs`
**Repo evidence:** `backend/app/api/v1/session_routes.py:96-104`
**Status:** ❌ Returns 501 "Event logs deferred to W3.2 (persistence layer not yet implemented)"
**Blocked:** Wait for W3.2 persistence layer

**Expected input**
```json
{ "session_id": "string" }
```

**Expected output (data)**
```json
{ "events": [], "total_turns": 0 }
```

---

### 6) `wos.session.state` (read) ❌ BLOCKED

**Purpose:** Get canonical world state for session.
**Backend mapping:** `GET /api/v1/sessions/<session_id>/state`
**Repo evidence:** `backend/app/api/v1/session_routes.py:107-115`
**Status:** ❌ Returns 501 "Canonical state retrieval deferred to W3.2 (persistence layer not yet implemented)"
**Blocked:** Wait for W3.2 persistence layer

**Expected input**
```json
{ "session_id": "string" }
```

**Expected output (data)**
```json
{ "scene_id": "string", "flags": {}, "..." : "..." }
```

---

## P1 Tools (Optional A1)

### 7) `wos.goc.list_modules` (read)

**Purpose:** List available content module IDs.
**Default implementation:** Local FS scan `content/modules/`

**Input**
```json
{}
```

**Output (data)**
```json
{ "modules": ["god_of_carnage", "..."] }
```

---

### 8) `wos.goc.get_module` (read)

**Purpose:** Get module metadata/files.
**Default implementation:** Local FS read.

**Input**
```json
{ "module_id": "god_of_carnage" }
```

**Output (data)**
```json
{
  "module_id": "god_of_carnage",
  "path": "content/modules/god_of_carnage",
  "files": ["..."],
  "version": "optional"
}
```

---

### 9) `wos.content.search` (read)

**Purpose:** Fast search in content files (GoC).
**Default:** Local FS search in `content/modules/god_of_carnage` + `direction/`

**Input**
```json
{ "query": "string", "scope": "goc|all", "max_hits": 50 }
```

**Output (data)**
```json
{
  "hits": [
    { "file": "path", "line": 123, "snippet": "..." }
  ]
}
```

---

## P2 Tools (B/C)

### 10) `wos.guard.preview_delta` (preview)

**Purpose:** Preview deltas (allow/deny + reasons).
**Status:** Not available in current state → documented as gap.

### 11) `wos.guard.preview_transition` (preview)

**Status:** As above.
