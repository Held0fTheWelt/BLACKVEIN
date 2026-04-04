# Milestone 3 — Gate Review

**Date:** 2026-04-04  
**Status:** **PASS**  
**Recommendation:** **Proceed**

## Scope

- World-Engine as **authoritative host** for story session execution (create session, load projection, execute turn, state, diagnostics).
- Documented HTTP API (internal key–protected).
- Backend session `/turns` proxies to World-Engine; deprecated local authoritative execution called out in warnings.

## Files changed (M3 scope)

| Area | Path |
|------|------|
| World-Engine | `world-engine/app/story_runtime/manager.py`, `__init__.py` |
| World-Engine | `world-engine/app/api/http.py` (story routes) |
| World-Engine | `world-engine/app/main.py` (lifespan `story_manager`) |
| World-Engine | `world-engine/tests/conftest.py` (REPO_ROOT on path) |
| World-Engine | `world-engine/tests/test_story_runtime_api.py` (new) |
| Backend | `backend/app/services/game_service.py` (story HTTP client) |
| Backend | `backend/app/api/v1/session_routes.py` (POST `/turns` proxy) |
| Backend | `backend/app/__init__.py` (repo root on `sys.path` for `story_runtime_core`) |
| Backend | `backend/tests/test_session_routes.py` (proxy tests) |

## Design decisions

- **Canonical story execution HTTP surface:** `POST /api/story/sessions`, `POST /api/story/sessions/{id}/turns`, `GET .../state`, `GET .../diagnostics` on the **World-Engine** service (internal API key when configured).
- **Backend** compiles `runtime_projection` via `compile_module` when starting a proxied turn if no `world_engine_story_session_id` is stored yet in session metadata.
- **Deprecation:** Response warnings state that backend-local authoritative turn execution is deprecated in favor of engine-hosted execution.

## Tests run

```text
cd world-engine
python -m pytest tests/test_story_runtime_api.py -q --tb=short

cd backend
python -m pytest tests/test_session_routes.py -q --tb=short
```

**Result:** Pass.

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Story sessions executable authoritatively in World-Engine | **Pass** |
| Backend can use engine-hosted execution | **Pass** |
| Runtime authority unambiguous for HTTP story API | **Pass** |
| Tests cover create, turn, state, diagnostics | **Pass** |

## Gate review — required extras

### Canonical story execution API path?

- **World-Engine:** `POST /api/story/sessions/{session_id}/turns` with JSON `{"player_input": "..."}` (plus create/state/diagnostics as above), using internal play-service URL from backend.

### Deprecated backend-local paths?

- **In-process** full W2 turn stack remains for **tests/tools** but is **not** the path for `POST /api/v1/sessions/<id>/turns`, which **proxies** to the engine. Warnings on the proxy response document deprecation.

### Backward compatibility?

- Existing clients must send `player_input` (or legacy `operator_input` / `input` aliases) for `/turns`.
- Sessions gain `metadata["world_engine_story_session_id"]` lazily on first turn.

### What remains to move later?

- Full alignment of backend diagnostics/export bundles with engine transcripts; persistence of engine session ids across processes.

## Known limitations

- In-memory engine sessions unless persistence is added later.

## Risks

- Backend ↔ engine coupling depends on network and shared secret configuration.

## Recommendation

**Proceed** to M4.
