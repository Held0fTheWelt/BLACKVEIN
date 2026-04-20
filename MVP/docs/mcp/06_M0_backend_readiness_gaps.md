# Backend Readiness & Gaps (M0)

This file lists what is **already available** for Phase A (and later B/C) and where **gaps** exist.

## Available (Repo Evidence)

- Web health:
  - `GET /health` (backend/app/web/routes.py:40-43) ✅ **Implemented**
- Session REST API v1:
  - `POST /api/v1/sessions` (backend/app/api/v1/session_routes.py:27-71) ✅ **Implemented, returns 201 Created**
  - `GET /api/v1/sessions/<id>` (backend/app/api/v1/session_routes.py:74-82) ❌ **501 stub (deferred to W3.2)**
  - `POST /api/v1/sessions/<id>/turns` (backend/app/api/v1/session_routes.py:85-93) ❌ **501 stub (deferred to W3.2)**
  - `GET /api/v1/sessions/<id>/logs` (backend/app/api/v1/session_routes.py:96-104) ❌ **501 stub (deferred to W3.2)**
  - `GET /api/v1/sessions/<id>/state` (backend/app/api/v1/session_routes.py:107-115) ❌ **501 stub (deferred to W3.2)**

---

## Gaps (for Clean MCP Usage)

### GAP-1: Module/Content Read API (optional)

- For remote-only operator (without local repo), useful:
  - `GET /api/v1/story/modules`
  - `GET /api/v1/story/modules/<module_id>`
  - `GET /api/v1/story/modules/<module_id>/scenes/<scene_id>`

Status: **Not implemented** in current state → optional expansion.

---

### GAP-2: Guard Preview Endpoints

- For `wos.guard.preview_delta` and `wos.guard.preview_transition`:
  - `POST /api/v1/guard/preview-delta`
  - `POST /api/v1/guard/preview-transition`

Status: **Not implemented** → planned for B3.

---

### GAP-3: AuthZ/Service Token for Session API

- Session API is not visibly protected in current code (no decorators in file).
- For MCP operator tools, service/AuthZ layer should be provisioned.
- Session endpoints currently accept unauthenticated requests.

Status: **Must verify** (M0 gate).

---

### GAP-4: Story Persistence (W3.2)

- Session state is in-memory; backend documents W3.2 deferral.
- Four session endpoints return 501 pending persistence layer implementation.

Status: Outside MCP-A1 scope; critical for robust operator flows. **Blocks 4 of 6 P0 tools.**

---

### GAP-5: Session API Completion (CRITICAL for Phase A)

**NEWLY IDENTIFIED BLOCKER:**

Four P0 tools cannot function in Phase A because their backend endpoints are not implemented:

- `wos.session.get` → `GET /api/v1/sessions/<id>` (501 stub)
- `wos.session.execute_turn` → `POST /api/v1/sessions/<id>/turns` (501 stub)
- `wos.session.logs` → `GET /api/v1/sessions/<id>/logs` (501 stub)
- `wos.session.state` → `GET /api/v1/sessions/<id>/state` (501 stub)

All four stubs in `backend/app/api/v1/session_routes.py` return identical 501 error messages referencing "deferred to W3.2 (persistence layer not yet implemented)."

**Phase A readiness:** 2 of 6 P0 tools functional (33%). Session retrieval/inspection impossible until W3.2 persistence layer implemented.

Status: **Blocks MCP Phase A full deployment.** Only `wos.system.health` and `wos.session.create` are usable; remaining critical tools require W3.2 work package completion.
