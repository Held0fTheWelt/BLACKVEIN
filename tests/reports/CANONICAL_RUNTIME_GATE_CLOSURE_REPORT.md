# Canonical Runtime Consolidation (P0) — Closure Report

## 1) Executive Verdict

**PASS**

## 2) Canonical Runtime Statement

World-Engine / Play-Service remains the single authoritative live runtime for run lifecycle execution (`/api/runs*`, join-context, transcript, terminate). Backend consumes that runtime via `game_service` and is not a competing runtime authority.

## 3) Scope of this closure pass

This pass focused on high-priority audit gaps and re-verification:

- Session bridge error semantics now match declared behavior for module errors (404/422 instead of broad 500 for known startup failures).
- Backend↔Play-Service integration test now validates the **published-content primary path** with a self-provisioned local feed, instead of disabling content sync.
- Canonical contract and runtime-classification/god-path docs were re-checked against code and tests.

## 4) Changed Files (this pass)

### Backend

- `backend/app/api/v1/session_routes.py`

### Tests

- `backend/tests/test_session_routes.py`
- `backend/tests/test_backend_playservice_integration.py`

## 5) Contract Table

| Endpoint | Canonical shape | Verification |
|---|---|---|
| `GET /api/templates` | List of template objects | `backend/tests/test_game_service.py`, `backend/tests/test_backend_playservice_integration.py` |
| `GET /api/runs` | List of run summaries | `backend/tests/test_game_service.py`, `backend/tests/test_game_routes.py` |
| `POST /api/runs` | V1 nested response `{ run, store, hint }`; identity at `run.id` | `world-engine/tests/test_canonical_runtime_contract.py`, `backend/tests/test_game_service.py`, `backend/tests/test_backend_playservice_integration.py` |
| `GET /api/runs/{run_id}` | V1 nested details with `run.id` path match; includes `template_source`, `template`, `store`, nullable `lobby` | `world-engine/tests/test_canonical_runtime_contract.py`, `backend/tests/test_game_service.py`, `backend/tests/test_backend_playservice_integration.py` |
| `POST /api/internal/runs/{run_id}/terminate` | V1 terminate envelope: `run_id`, `terminated: true`, `template_id`, `actor_display_name`, `reason` | `world-engine/tests/test_api.py`, `backend/tests/test_game_service.py`, `backend/tests/test_backend_playservice_integration.py` |
| `DELETE /api/runs/{run_id}` | Legacy alias returning the same V1 terminate envelope | `world-engine/tests/test_canonical_runtime_contract.py` |
| `POST /api/internal/join-context` | Join-context payload with run/participant/role identity | `backend/tests/test_game_service.py`, `backend/tests/test_backend_playservice_integration.py` |

## 6) Runtime Classification Summary

- **Kept (canonical reusable logic):** Shared models/policies/helpers under `backend/app/runtime/*` documented in `docs/architecture/backend_runtime_classification.md`.
- **Deprecated transitional:** In-process session/runtime execution for tests/operator surfaces only; explicitly marked non-authoritative.
- **Removed legacy (already present and re-verified):** `backend/app/api/http.py`, `backend/app/runtime/w2_models.py`, `backend/tests/test_api_http.py`.

## 7) God-of-Carnage Path Summary

- **Primary operational path:** Published backend content feed (`/api/v1/game/content/published`) consumed by World-Engine sync.
- **Fallback/test/demo path:** World-Engine builtin `god_of_carnage_solo`.
- **This pass evidence:** integration test now runs with sync enabled and a local HTTP feed, asserting `template_source == "backend_published"` on run details.

## 8) Test Evidence

### Commands run

```bash
cd backend
python -m pytest tests/test_game_service.py tests/test_game_routes.py tests/test_game_admin_routes.py tests/test_session_routes.py tests/runtime/test_runtime_manager_engine.py tests/runtime/test_runtime_core.py tests/test_backend_playservice_integration.py -q --tb=short
```

Result: **112 passed**

```bash
cd world-engine
python -m pytest tests/test_api.py tests/test_canonical_runtime_contract.py tests/test_backend_authored_content.py tests/test_runtime_manager.py -q --tb=short
```

Result: **21 passed**

### Pass/fail outcomes

- Contract shape coverage for create/details/terminate: **pass**
- Malformed/missing field behavior in backend consumer: **pass**
- Producer guarantees in world-engine contract tests: **pass**
- God-of-Carnage published-primary with builtin fallback controls: **pass**
- Backend↔Play-Service integration happy path with published feed: **pass**
- Session bridge known startup errors mapped to 404/422: **pass**

### Remaining failures

- None in the executed canonical gate matrix.

## 9) Residual Risks

- Backend still carries transitional in-process runtime/session surfaces by design; classification boundaries must remain enforced in future changes.
- Canonical runtime truth and stack-level behavior still need synchronized release-level confirmation via `tests/reports/E2E_ACCEPTANCE_REPORT.md` under the unified release gate.
