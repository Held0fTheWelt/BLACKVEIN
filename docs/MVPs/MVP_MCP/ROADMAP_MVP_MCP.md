# MCP Roadmap · World of Shadows (Current State Compatible)

This roadmap describes the steps to integrate **MCP (Model Context Protocol)** into the current system — in sequence **A → B → C**:
- **A:** Operator/Dev tooling (out-of-band, read-only)
- **B:** MCP in AI path (in-loop, guarded, initially read-only/preview)
- **C:** Supervisor + Subagents (true orchestration, policies, hardening)

> **Core Principle:** **Guard/Validation remains law.** MCP/AI must not bypass the authoritative state.

---

## M0 — Framework & Architecture Decisions (Required)

**Goal:** Introduce MCP in a way that works in your setup (local + PythonAnywhere).

### Tasks

1. **Determine Host (who calls MCP?)**
   - A: IDE/Operator tools (local)
   - B/C: Backend AI host (adapter path)

2. **Choose Transport**
   - **stdio** (local, fast, simple) for A
   - **HTTP/Streamable** (service/network) if needed later

3. **Security Baseline**
   - Start: **read-only tools**
   - No state writes without Guard/policy

4. **Tool Naming Schema + Versioning**
   - `wos.goc.*`, `wos.session.*`, `wos.guard.*`, `wos.content.*`

5. **Deployment Decision**
   - MCP Server local (operator) speaks remotely to backend via HTTPS
   - or sidecar in same network as backend (Docker later)

### Acceptance Criteria
- Document **"MCP Contract v0"** exists (tools, inputs/outputs, auth, limits)
- Transport decision is locked in (at minimum for A)

---

## A1 — MCP as Operator/Dev Tooling (Out-of-Band)

**Goal:** Immediate value without changing the God of Carnage turn loop.

### A1.1 MCP Server Skeleton
- New module/repo e.g., `tools/mcp_server/`
- Implements:
  - `tools/list`
  - `tools/call`
  - Logging: request-id, `tool_name`, duration, status

### A1.2 Read-Only Tools (v0) for God of Carnage

**Recommended tool list (10–12 tools):**

1. `wos.goc.list_modules()` → available modules/IDs
2. `wos.goc.get_module(module_id)` → metadata, entry scene
3. `wos.session.list_active()` → active sessions (in-memory)
4. `wos.session.get(session_id)` → scene_id, turn_counter, flags snapshot
5. `wos.session.get_history(session_id)` → last N turns
6. `wos.guard.explain_last(session_id)` → last guard/validation
7. `wos.guard.preview_transition(session_id, target_scene_id)` → allow/deny + reasons
8. `wos.guard.preview_delta(session_id, delta)` → allow/deny + reasons
9. `wos.content.search(query)` → content search (scenes/beats/texts)
10. `wos.system.health()` → backend reachable, version, mode
11. (optional) `wos.session.export_bundle(session_id)` → diagnostics bundle
12. (optional) `wos.content.get_scene(module_id, scene_id)` → scene definition

**Implementation Variants:**
- **Recommended (remote-first):** MCP tools call **backend HTTP endpoints** (authenticated).
- Alternative: MCP server imports backend Python directly (only sensible in same runtime/environment).

### A1.3 Backend: Minimal Read Endpoints (if needed)

If data isn't yet accessible via existing APIs:
- `GET /api/session/<id>/snapshot`
- `GET /api/session/<id>/history?limit=N`
- `GET /api/session/<id>/guard/last`
- `GET /api/module/<id>`
- `GET /api/content/search?q=...`

### Acceptance Criteria
- MCP tools work against PythonAnywhere or locally
- Operator can live-inspect sessions (scene/state/history/guard)
- No changes to turn-flow required

---

## A2 — Observability & Reproducibility (Preparation for B/C)

**Goal:** Everything remains explainable and regression-testable.

### Tasks
- Unified **trace-id**: session-id, turn-id, request-id
- Structured logs:
  - Tool calls: name, args-hash, response-hash, duration, status
- Optional: diagnostics export (bundle)

### Acceptance Criteria
- A turn is reproducible/explainable ("Why reject?")
- Tool calls are traceable in debug

---

## B1 — MCP in AI Path: Context Enrichment (in-loop, read-only)

**Goal:** AI (when enabled) gets correct context via MCP before generating output.

### Tasks

1. **Make AI-mode controllable activation**
   - e.g., `execution_mode="ai"` via config/admin, not hidden

2. **Preflight context via MCP**
   - allowed actions, scene constraints, flags, history

3. Context in **structured form** in `AdapterRequest`

4. Guard unchanged: AI proposes, guard decides

### Acceptance Criteria
- AI turn runs without write-tools
- Tool calls logged
- Guard behavior identical to before (only better inputs)

---

## B2 — MCP Tool Loop (optional)

**Goal:** Model can request tools; host executes; model finalizes.

### Tasks
- Whitelist allowed tools per turn
- Max tool calls/turn (e.g., 3–5), timeouts, retries
- Tool transcript in debug panel

### Acceptance Criteria
- No infinite loops
- Deterministic limits enforced
- Debuggability: "which tool influenced which output?"

---

## B3 — Guarded Preview (no write)

**Goal:** AI can propose deltas and preview via MCP, but not apply them.

### Tasks
- `wos.guard.preview_delta(...)` as central loop
- Adapter uses preview feedback to correct

### Acceptance Criteria
- Guard reject-rate decreases without loss of safety
- State remains authoritative in backend/guard

---

## C1 — Agent Registry + Supervisor Layer (true subagents)

**Goal:** Supervisor/subagents become real (routing, multiple calls, consolidation).

### Tasks

1. **Agent registry (config + runtime)**
   - agent_id, role, allowed tools, budgets, model selection, status

2. **Supervisor orchestrator**
   - Plan → Execute → Merge → Finalize

3. Result format compatible with current turn contract

### Acceptance Criteria
- Subagents are true calls (not just text sections)
- Tool policies per agent (MCP whitelist) enforced
- Consolidation is traceable (why/trace)

---

## C2 — Production Hardening

**Goal:** Agentics becomes operationalizable.

### Tasks
- Budgets per turn (time, tokens, tool calls)
- Fallbacks / graceful degradation
- Caching (content reads, allowed actions, etc.)
- Audit: who called which tools?

### Acceptance Criteria
- Stable operation, no agent explosion
- Turn stays within defined limits

---

## Recommended Sequence

**A1 → A2 → B1 → (B2/B3 optional) → C1 → C2**

---

## Rough Effort Scale (realistic magnitude)

- **A1:** 1–3 days (skeleton + ~10 tools)
- **A2:** 1–2 days (tracing + logs + export)
- **B1:** 2–5 days (AI path + preflight + tests)
- **B2/B3:** 3–8 days (tool loop + limits + diagnostics)
- **C1:** 1–3 weeks (registry + supervisor + subagents + tests)
- **C2:** 1–2 weeks (policies, caching, failover, audit)

---

## Quick Checklist (DoD — Definition of Done)

- [ ] MCP server runs locally (stdio) and can reach backend remotely
- [ ] `wos.goc.*` tools deliver reliable session/content info
- [ ] Guard preview tools exist (`preview_delta`, `preview_transition`)
- [ ] Tracing/logs make turns reproducible
- [ ] AI path uses MCP read-only, guard remains law
- [ ] (optional) Tool loop is limited + auditable
- [ ] Supervisor/subagents only after stable A/B foundation
