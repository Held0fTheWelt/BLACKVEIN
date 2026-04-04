# AI Stack M0-M5 Closure Report

Date: 2026-04-04  
Scope: Milestones 0 through 5

## Evidence and test commands

- **Per-milestone gate reviews:** `docs/reports/ai_stack_gates/M0_GATE_REVIEW.md` … `M5_GATE_REVIEW.md`
- **Representative test runs (executed 2026-04-04):**

```text
cd backend
python -m pytest tests/test_session_routes.py tests/runtime/test_session_store.py tests/content/test_content_compiler.py tests/test_game_content_service.py -q --tb=short

cd <repo-root>
python -m pytest story_runtime_core/tests -q --tb=short

cd world-engine
python -m pytest tests/test_story_runtime_api.py -q --tb=short
```

## Git / commit discipline note

Milestone boundaries are recorded primarily in the gate review artifacts above. The implementation landed as **one integration commit** on the working branch because the same modules (for example `session_routes.py` and `story_runtime_core`) carry cross-cutting M0–M5 concerns; splitting into six historical commits would require a scripted replay or file splits. For audit, use the gate files plus this closure report as the authoritative milestone record.

## Milestone 0 - Architecture Freeze and Hygiene Repairs

### Implemented

- Added canonical architecture baseline:
  - `docs/architecture/ai_stack_in_world_of_shadows.md`
  - `docs/architecture/runtime_authority_decision.md`
- Marked drifted runtime command document as historical/non-canonical:
  - `docs/features/RUNTIME_COMMANDS.md`
- Fixed session-start hygiene:
  - `backend/app/runtime/session_start.py` now returns `module` in `SessionStartResult`
  - `backend/app/services/session_service.py` removed duplicate module load
  - `backend/app/runtime/session_store.py` now rejects duplicate session registration
- Fixed startup error mapping and JSON validation:
  - `backend/app/api/v1/session_routes.py` with explicit reason-to-status mapping

### Tests added/updated

- `backend/tests/test_session_routes.py`
  - `no_start_scene -> 422`
  - invalid JSON -> 400
  - turn endpoint contract updated for new routing path
- `backend/tests/runtime/test_session_store.py`
  - duplicate registration regression test

### Canonical now

- Architecture baseline and runtime authority docs are explicitly canonical.

### Transitional

- Backend in-process session snapshots remain transitional and volatile.

### Deferred to M6+

- Full LangGraph/LangChain/RAG/MCP runtime orchestration integration.

### Residual risks

- Backend in-process session shell still exists for compatibility and operator views.

---

## Milestone 1 - Canonical Content Model and Compiler Pipeline

### Implemented

- Formalized canonical authored model decision:
  - `docs/architecture/canonical_authored_content_model.md`
- Added compiler package:
  - `backend/app/content/compiler/models.py`
  - `backend/app/content/compiler/compiler.py`
  - `backend/app/content/compiler/__init__.py`
- Compiler outputs:
  - `runtime_projection`
  - `retrieval_corpus_seed`
  - `review_export_seed`
- Integrated compilation into publishing flow:
  - `backend/app/services/game_content_service.py`
  - published/seeded payloads now carry `canonical_compilation` when canonical module is resolvable

### Tests added/updated

- Added deterministic God of Carnage compiler proof:
  - `backend/tests/content/test_content_compiler.py`
- Updated publishing tests:
  - `backend/tests/test_game_content_service.py` validates canonical compilation in seed payloads

### Canonical now

- Scene/trigger/ending-oriented `ContentModule` source remains the canonical authored source.

### Transitional

- Experience templates continue to coexist as downstream runtime-facing content artifacts.

### Deferred to M6+

- Full retrieval ingestion pipeline and admin review tooling over review export seed.

### Residual risks

- Canonical module mapping from template id is currently heuristic for compatibility.

---

## Milestone 2 - Shared Story Runtime Core Extraction

**Gate status:** **PARTIAL** — shared core is real and tested, but full backend turn execution / validation remains backend-local (see `docs/reports/ai_stack_gates/M2_GATE_REVIEW.md`).

### Implemented

- Added shared runtime core package:
  - `story_runtime_core/pyproject.toml`
  - `story_runtime_core/models.py`
  - `story_runtime_core/input_interpreter.py`
  - `story_runtime_core/model_registry.py`
  - `story_runtime_core/adapters.py`
  - `story_runtime_core/__init__.py`
- Added backend transitional shim consuming shared core:
  - `backend/app/runtime/input_interpreter.py`
- Added architecture note about shared extraction:
  - `docs/architecture/backend_runtime_classification.md`

### Tests added/updated

- `story_runtime_core/tests/test_input_interpreter.py`
- `story_runtime_core/tests/test_model_registry.py`
- `story_runtime_core/tests/test_adapters.py`

### Canonical now

- Input interpretation and model-routing contracts are shared in `story_runtime_core`.

### Transitional

- Backend-local legacy runtime components still exist for compatibility and tests.

### Deferred to M6+

- Deeper extraction of full turn execution and validation policies into shared core.

### Residual risks

- Some runtime execution logic still lives in backend-local modules and is not yet fully relocated.

---

## Milestone 3 - World-Engine as Story Runtime Host

### Implemented

- Added World-Engine hosted story runtime manager:
  - `world-engine/app/story_runtime/manager.py`
  - `world-engine/app/story_runtime/__init__.py`
- Added story runtime API surface:
  - `POST /api/story/sessions`
  - `POST /api/story/sessions/{session_id}/turns`
  - `GET /api/story/sessions/{session_id}/state`
  - `GET /api/story/sessions/{session_id}/diagnostics`
  - implemented in `world-engine/app/api/http.py`
- Wired manager startup:
  - `world-engine/app/main.py`
  - `world-engine/tests/conftest.py`
- Switched backend turn path toward World-Engine-hosted execution:
  - `backend/app/services/game_service.py` story-runtime client functions
  - `backend/app/api/v1/session_routes.py` now proxies turn execution to World-Engine

### Tests added/updated

- Added world-engine host test:
  - `world-engine/tests/test_story_runtime_api.py`
- Updated backend route tests to validate proxy path:
  - `backend/tests/test_session_routes.py`

### Canonical now

- Story turn execution authority is hosted in World-Engine story runtime endpoints.

### Transitional

- Backend still keeps in-memory session shell as compatibility bridge.

### Deferred to M6+

- Full migration of all legacy backend-local runtime execution call sites.

### Residual risks

- Backend proxy path currently depends on in-process session metadata linkage to engine session id.

---

## Milestone 4 - Real Model Layer (LLM/SLM) and Routing Policy

### Implemented

- Added concrete adapters in shared core:
  - `OpenAIChatAdapter`
  - `OllamaAdapter`
  - `MockModelAdapter`
  - in `story_runtime_core/adapters.py`
- Added model registry and routing policy:
  - `story_runtime_core/model_registry.py`
  - explicit LLM vs SLM classes, timeout, structured-output capability, cost/latency classes
- Startup/runtime registration:
  - `build_default_registry()` used by World-Engine story runtime manager
- Registered concrete adapter instances at story manager startup via `build_default_model_adapters()` (mock, OpenAI, Ollama).
- Added model-choice observability in turn diagnostics:
  - selected model/provider
  - route reason
  - fallback model
  - timeout
  - structured-output capability marker
  - `registered_adapter_providers` and per-turn `generation` (`attempted`, `success`, `error`) from the selected provider adapter

### Tests added/updated

- `story_runtime_core/tests/test_model_registry.py`
- `story_runtime_core/tests/test_adapters.py`
- `world-engine/tests/test_story_runtime_api.py` checks route metadata presence

### Canonical now

- Model selection is explicit, policy-driven, and visible in diagnostics.

### Transitional

- Hosted model calls are available, but production provider hardening is still pending.

### Deferred to M6+

- Rich provider-specific reliability layers, retries, and budget controls.

### Residual risks

- Real provider behavior depends on environment credentials and endpoint availability.

---

## Milestone 5 - Natural-Language Runtime Input Understanding

### Implemented

- Added interpretation contract document:
  - `docs/architecture/player_input_interpretation_contract.md`
- Implemented structured interpreter:
  - `story_runtime_core/input_interpreter.py`
  - categories: speech, action, reaction, mixed, intent_only, explicit_command, meta, ambiguous
- Integrated interpreter into authoritative story turn path:
  - `world-engine/app/story_runtime/manager.py`
- Preserved command support as special path:
  - explicit command classification and command fields in interpretation output
- Added diagnostics visibility for:
  - raw input
  - interpreted mode
  - ambiguity/confidence
  - selected handling/model route path

### Tests added/updated

- `story_runtime_core/tests/test_input_interpreter.py`
  - dialogue, action, mixed, explicit command, ambiguous, meta, reaction, intent-only coverage
- `world-engine/tests/test_story_runtime_api.py`
  - end-to-end story turn interpretation and diagnostics validation

### Canonical now

- Natural-language interpretation is a real runtime layer.

### Transitional

- Heuristic interpreter exists now; policy can later combine heuristic + model-assisted interpretation.

### Deferred to M6+

- LangGraph-based interpretation workflows and confidence arbitration policies.

### Residual risks

- Heuristic interpretation may require iterative tuning for nuanced edge narratives.

---

## Open Follow-ups for M6+

- Integrate LangChain as reusable integration abstraction over providers and tools.
- Introduce LangGraph orchestration for turn planning, tool use, and commit gates.
- Build RAG ingestion and retrieval serving over compiler retrieval corpus outputs.
- Expand MCP capability surface for controlled runtime actions and external integrations.
- Migrate Writers-Room from lightweight direct-model usage to canonical stack layers.
- Add iterative improvement/practice loop:
  - telemetry-driven quality review,
  - policy tuning,
  - prompt and routing refinement.
