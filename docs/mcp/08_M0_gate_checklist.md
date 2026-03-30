# M0 Gate Checklist (Verification Only)

**Goal:** After placement of these documents, M0 requires only **verification** to close the gate.

## 1) Confirm Architectural Decisions

- [x] Host for Phase A is local (operator), MCP transport = stdio
- [x] MCP speaks to backend remotely via HTTPS (PythonAnywhere default)
- [x] Phase A remains read-only/preview-only (no write tools)

---

## 2) Verify Repo Evidence

### Backend Endpoints

- [x] `backend/app/api/__init__.py` registers Blueprint `/api/v1`
- [x] `backend/app/api/v1/session_routes.py` contains:
  - [x] `POST /api/v1/sessions` (lines 27-71) — ✅ **Implemented, 201 Created**
  - [x] `GET /api/v1/sessions/<id>` (lines 74-82) — ⚠️ **501 stub (deferred to W3.2)**
  - [x] `POST /api/v1/sessions/<id>/turns` (lines 85-93) — ⚠️ **501 stub (deferred to W3.2)**
  - [x] `GET /api/v1/sessions/<id>/logs` (lines 96-104) — ⚠️ **501 stub (deferred to W3.2)**
  - [x] `GET /api/v1/sessions/<id>/state` (lines 107-115) — ⚠️ **501 stub (deferred to W3.2)**
- [x] `backend/app/web/routes.py` contains `GET /health` (line 40-43)
- [x] Content module available: `content/modules/god_of_carnage/`

### Web UI Routes (NOT REST API, but documented for completeness)

- [x] `GET /play` (line 641-650) — Jinja session start form
- [x] `POST /play/start` (lines 653-692) — Session creation via form
- [x] `GET /play/<session_id>` (lines 695-728) — Jinja session shell
- [x] `POST /play/<session_id>/execute` (lines 805-930) — Turn execution via form

⚠️ **NOTE:** Web routes (`/play/*`) are HTML/Jinja UI, NOT JSON REST API. They do **not** satisfy `wos.session.*` tool contracts which require JSON REST endpoints.

---

## 3) Verify Stub Status

- [x] All four 501 endpoints return consistent error: "deferred to W3.2 (persistence layer not yet implemented)"
- [x] Endpoints are registered (not missing) but intentionally non-functional
- [x] Docstrings in `session_routes.py` document W3.2 deferral

---

## 4) Verify Security Baseline

- [x] Session API has no visible auth protection (no decorators, no token check)
- [x] Documented as **GAP-3** in Backend Readiness & Gaps
- [x] No credentials in error messages or logs
- [ ] Consider whether unauthenticated session creation acceptable for Phase A

**Decision needed:** Should Session API require service token before Phase A go-live? (Recommend: Yes, to prevent unauthorized access.)

---

## 5) Tool Inventory Assessment

- [x] P0 tools documented in `05_M0_tool_inventory_v0.md`
- [x] Tool status clearly marked: ✅ **Ready** vs ❌ **Blocked (501 stub)**
- [x] Phase A readiness marked: **PARTIAL (2 of 6 P0 tools functional)**

**Phase A tool availability:**
- `wos.system.health` ✅ Ready
- `wos.session.create` ✅ Ready
- `wos.session.get` ❌ Blocked (501)
- `wos.session.execute_turn` ❌ Blocked (501)
- `wos.session.logs` ❌ Blocked (501)
- `wos.session.state` ❌ Blocked (501)

P1 tools (local FS reads) all feasible in operator setup.

---

## Exit Criteria (M0 Gate Closed)

- [x] All docs translated to English
- [x] Docs match repo evidence (no false "implemented" claims for 501 stubs)
- [x] 501 stub endpoints explicitly documented as blocked
- [x] Phase A readiness clearly stated as PARTIAL (33% of P0 tools functional)
- [ ] Security decision on service token protection (recommend: implement before Phase A production use)
- [x] A1 can proceed with implementation constraints known (only 2 of 6 P0 tools available)

**Phase A can proceed with understanding that session inspection (retrieve, logs, state, turn-execution) is blocked until W3.2 persistence implementation completes.**
