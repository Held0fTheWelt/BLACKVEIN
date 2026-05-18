# Backend Runtime Classification (Block 2 — Gate)

**Status:** Binding for backend layout and naming. The Flask backend is **not** an equivalent live play host to the World Engine.

**Related:** [canonical_runtime_contract.md](./canonical_runtime_contract.md) (nested run V1, consumer/producer split).

## Where does the real run execute?

**Authoritative live play** (runs, nested-run V1, templates listing, terminate, transcripts as exposed by the play service) executes in the **World Engine** HTTP/WebSocket service. The backend integrates via `game_service` (HTTP client to `PLAY_SERVICE_*` URLs) and must treat that service as the single live runtime.

**Inside this repo’s `backend` package:**

- **In-process** `RuntimeManager` / `RuntimeEngine` / `JsonRunStore` are a **deprecated transitional mirror** for unit tests and local experiments only. They are **not** mounted on the production Flask app.
- **W2-style** `SessionState` flows (`session_start`, `session_store`, `turn_dispatcher`, `turn_executor`, AI path) are **deprecated transitional** simulation/test tooling—not a mounted player or operator session API.
- Shared extraction direction is now active through `story_runtime_core/` for reusable input interpretation and model routing contracts.

## Classification (exactly three classes)

### 1. Canonical reusable logic

Shared **schemas**, **validation**, **presentation**, and **serialization** that remain valid to import from the backend without implying “execution is live here.”

| Artifact | Role |
|----------|------|
| `runtime_models.py` | Pydantic models for `SessionState`, deltas, logs (shape + tests + persistence). |
| `models.py` | `RuntimeInstance`, participants, transcript DTOs for template/run JSON shapes. |
| `validators.py`, `decision_policy.py`, `mutation_policy.py`, `reference_policy.py` | Pure validation / policy rules for W2-style state. |
| `scene_legality.py` | Scene/ending legality rules (shared by validators and `next_situation`). |
| `scene_presenter.py`, `history_presenter.py`, `debug_presenter.py` | Map `SessionState` to operator/debug-oriented views (no execution authority). |
| `preview_delta.py`, `preview_models.py` | Dry-run preview (guard semantics without committing live engine state). |
| `event_log.py`, `session_persistence.py` | Event shape and JSON (de)serialization helpers. |
| `helper_functions.py`, `short_term_context.py`, `lore_direction_context.py`, `relationship_context.py`, `progression_summary.py`, `next_situation.py`, `visibility.py` | Derived context and situation helpers over `SessionState` (bounded SLM-oriented helpers used in transitional simulation/tests). |
| `ai_adapter.py`, `ai_decision.py`, `ai_output.py`, `ai_decision_logging.py`, `role_contract.py`, `role_structured_decision.py` | Adapter and parsing contracts (reusable; used in-process and in tests). `AIRoleContract` separates interpreter, director, and responder sections in one structured payload; `parse_role_contract` in `role_structured_decision.py` normalizes **responder** content into `ParsedAIDecision` for execution while retaining interpreter/director slices for diagnostics only. |
| `agent_registry.py`, `orchestration_cache.py`, `supervisor_orchestrator.py`, `tool_loop.py` | Orchestration components for the in-process AI path (reusable building blocks). |
| `ai_failure_recovery.py` | Recovery policies and snapshots for the in-process path. |
| `npc_behaviors.py`, `adapter_registry.py` | Supporting registry/behavior hooks. |

### 2. Deprecated transitional logic

Code paths that **execute or host** narrative/runtime behavior **inside the backend process** for tests or local simulation. They are not mounted as a second live runtime.

| Artifact | Rationale to keep (for now) |
|----------|-----------------------------|
| `manager.py`, `engine.py`, `store.py` | In-process run loop + JSON store; exercised by `test_runtime_manager_engine.py` / `test_runtime_core.py`. Not a public duplicate play API after removal of `app.api.http`. |
| `session_start.py` | Bootstraps `SessionState` from content modules for tests/dev. |
| `session_store.py` | Volatile in-memory registry for transitional tests/dev helpers; no public session route owns it. |
| `turn_dispatcher.py`, `turn_executor.py`, `ai_turn_executor.py` | In-process turn pipeline and AI integration for tests and tooling. |

### 3. Dead / legacy logic (removed in this gate)

| Artifact | Reason |
|----------|--------|
| `app/api/http.py` | Shadow FastAPI router duplicating play-service style endpoints; **never** mounted on `create_app()`. Removed to avoid implying a second live runtime. |
| `tests/test_api_http.py` | Only tested the removed router; redundant with `RuntimeManager` unit tests. |
| `runtime/w2_models.py` | Star-export compatibility shim with **zero** importers; removed. |
| `app/api/v1/session_routes.py` | Removed backend session bridge; canonical player sessions use `app/api/v1/game_routes.py`. |
| `app/api/v1/player_routes.py` | Removed legacy player facade; canonical player turns use `/api/v1/game/player-sessions/<run_id>/turns`. |
| `app/services/session_service.py` | Removed service wrapper for the old in-process session API. |

## API stance

- **Create/resume player session:** `POST /api/v1/game/player-sessions`.
- **Read player session:** `GET /api/v1/game/player-sessions/<run_id>`.
- **Execute player turn:** `POST /api/v1/game/player-sessions/<run_id>/turns`.
- **Diagnostics/evidence:** Governance and operator diagnostics use World-Engine story-session ids through their own admin/operator routes.

### Mutation and reference enforcement (W2-style proposals)

- **Mutation permission** is **deny-by-default**: `mutation_policy.py` whitelists story-world domains (for example character, relationship, scene, and conflict fields) and blocks protected roots such as session identity, metadata, runtime internals, and log-like subtrees. **Path syntax or entity existence alone does not grant mutation permission**; `validators.py` applies policy during delta validation.
- **Reference integrity** (`reference_policy.py`): character, relationship, scene, and trigger references in proposals are checked against module truth (and optional session context) before acceptance.

## Package map (import ergonomics)

For explicit layering without moving dozens of modules: **`app.runtime.canonical`** and **`app.runtime.transitional`** lazily load the same `app.runtime.<module>` files; membership is defined in **`app.runtime.package_classification`** (enforced by `backend/tests/runtime/test_runtime_package_classification.py`). Prefer existing `from app.runtime import <module>` in mature code; use the subpackages when you want the classification visible at the import site.

## Consumer rule

Any feature that needs **live** run identity, lobby, or turn execution must use **World Engine** via `game_service` (and contracts in `canonical_runtime_contract.md`), not `app.runtime.manager` or W2 session APIs alone.
