# Backend Runtime Classification (Block 2 — Gate)

**Status:** Binding for backend layout and naming. The Flask backend is **not** an equivalent live play host to the World Engine.

**Related:** [canonical_runtime_contract.md](./canonical_runtime_contract.md) (nested run V1, consumer/producer split).

## Where does the real run execute?

**Authoritative live play** (runs, nested-run V1, templates listing, terminate, transcripts as exposed by the play service) executes in the **World Engine** HTTP/WebSocket service. The backend integrates via `game_service` (HTTP client to `PLAY_SERVICE_*` URLs) and must treat that service as the single live runtime.

**Inside this repo’s `backend` package:**

- **In-process** `RuntimeManager` / `RuntimeEngine` / `JsonRunStore` are a **deprecated transitional mirror** for unit tests and local experiments only. They are **not** mounted on the production Flask app.
- **W2-style** `SessionState` flows (`session_start`, `session_store`, `turn_dispatcher`, `turn_executor`, AI path) are **deprecated transitional** simulation, tests, tooling, and operator/MCP endpoints—not a second live runtime.
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
| `helper_functions.py`, `short_term_context.py`, `lore_direction_context.py`, `relationship_context.py`, `progression_summary.py`, `next_situation.py`, `visibility.py` | Derived context and situation helpers over `SessionState` (bounded SLM-oriented helpers used on the in-process path and in tests). |
| `ai_adapter.py`, `ai_decision.py`, `ai_output.py`, `ai_decision_logging.py`, `role_contract.py`, `role_structured_decision.py` | Adapter and parsing contracts (reusable; used in-process and in tests). `AIRoleContract` separates interpreter, director, and responder sections in one structured payload; `parse_role_contract` in `role_structured_decision.py` normalizes **responder** content into `ParsedAIDecision` for execution while retaining interpreter/director slices for diagnostics only. |
| `agent_registry.py`, `orchestration_cache.py`, `supervisor_orchestrator.py`, `tool_loop.py` | Orchestration components for the in-process AI path (reusable building blocks). |
| `ai_failure_recovery.py` | Recovery policies and snapshots for the in-process path. |
| `npc_behaviors.py`, `adapter_registry.py` | Supporting registry/behavior hooks. |

### 2. Deprecated transitional logic

Code paths that **execute or host** narrative/runtime behavior **inside the backend process** or expose **volatile** session snapshots. Kept until callers/tests migrate to World Engine–only flows; must be labeled as non-authoritative.

| Artifact | Rationale to keep (for now) |
|----------|-----------------------------|
| `manager.py`, `engine.py`, `store.py` | In-process run loop + JSON store; exercised by `test_runtime_manager_engine.py` / `test_runtime_core.py`. Not a public duplicate play API after removal of `app.api.http`. |
| `session_start.py` | Bootstraps `SessionState` from content modules for tests/MCP/dev. |
| `session_store.py` | Volatile in-memory registry for `/api/v1/sessions/*` operator views. |
| `turn_dispatcher.py`, `turn_executor.py`, `ai_turn_executor.py` | In-process turn pipeline and AI integration for tests and tooling. |
| `session_service.py` (`create_session`) | Wires module load + `session_start` + `session_store` for POST `/api/v1/sessions`. |

### 3. Dead / legacy logic (removed in this gate)

| Artifact | Reason |
|----------|--------|
| `app/api/http.py` | Shadow FastAPI router duplicating play-service style endpoints; **never** mounted on `create_app()`. Removed to avoid implying a second live runtime. |
| `tests/test_api_http.py` | Only tested the removed router; redundant with `RuntimeManager` unit tests. |
| `runtime/w2_models.py` | Star-export compatibility shim with **zero** importers; removed. |

## API stance (`session_routes.py`)

- **POST `/api/v1/sessions`**: Creates an **in-process** `SessionState` and registers it in memory. Response includes explicit `warnings` that this is **not** the authoritative live runtime.
- **GET** snapshot/state/logs/diagnostics/export: Read **volatile** in-process state for operators; warnings already flag `in_memory_session_state_is_volatile` and limited history.
- **Service-token operator reads:** Selected JSON snapshot routes (session detail, state, logs, diagnostics, export) require `Authorization: Bearer <token>` where the bearer value is compared to the **`MCP_SERVICE_TOKEN`** environment variable using constant-time comparison. If the variable is unset, affected routes return **503** with a `MISCONFIGURED` error body (implementation: `backend/app/api/v1/auth.py`, `require_mcp_service_token`). This is an operator/MCP bridge surface, not player-session auth.

### Mutation and reference enforcement (W2-style proposals)

- **Mutation permission** is **deny-by-default**: `mutation_policy.py` whitelists story-world domains (for example character, relationship, scene, and conflict fields) and blocks protected roots such as session identity, metadata, runtime internals, and log-like subtrees. **Path syntax or entity existence alone does not grant mutation permission**; `validators.py` applies policy during delta validation.
- **Reference integrity** (`reference_policy.py`): character, relationship, scene, and trigger references in proposals are checked against module truth (and optional session context) before acceptance.

## Consumer rule

Any feature that needs **live** run identity, lobby, or turn execution must use **World Engine** via `game_service` (and contracts in `canonical_runtime_contract.md`), not `app.runtime.manager` or W2 session APIs alone.
