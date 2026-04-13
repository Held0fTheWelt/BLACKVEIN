# Operational Settings, AI Runtime Governance, World-Engine Control Center, and AI Engineer Suite

Phase 1 establishes operator-usable administration surfaces for the minimum viable AI runtime path and world-engine control posture.
Phase 2 adds an AI-engineering operations layer that is read-heavy, write-light, and explicitly bounded.

## Access control

- **AI Runtime Governance** (`/manage/ai-runtime-governance` and `/manage/operational-governance*`) requires the **`manage.ai_runtime_governance`** feature (admin-only by default). This matches the backend admin governance APIs, which are gated with the same feature identifier plus JWT. Enforcement uses the central feature access resolver (`app.auth.feature_access_resolver`); see [`backend/docs/AREA_ACCESS_CONTROL.md`](../../backend/docs/AREA_ACCESS_CONTROL.md) for the decision path.
- **World-Engine Control Center** reuses the hierarchical **`manage.world_engine_*`** capabilities (observe as minimum) because it shares the same play-service proxy surface as the console.
- **AI Engineer Suite pages** (`/manage/runtime-dashboard`, `/manage/rag-operations`, `/manage/ai-orchestration`) are gated with **`manage.ai_runtime_governance`** and intentionally route operators back to canonical Phase 1 surfaces for provider/model/route and world-engine control-plane changes.

## Canonical behavior

- Bootstrap/trust-anchor state is persisted in backend tables and surfaced via:
  - `GET /api/v1/bootstrap/public-status`
  - `GET /api/v1/admin/bootstrap/status`
  - `POST /api/v1/admin/bootstrap/initialize`
  - `POST /api/v1/admin/bootstrap/reopen`
- Runtime truth is resolved server-side and surfaced via:
  - `GET /api/v1/admin/runtime/resolved-config`
  - `POST /api/v1/admin/runtime/reload-resolved-config`
  - `GET /api/v1/internal/runtime-config` (token-protected)
- Runtime readiness/blockers are deterministic and surfaced via:
  - `GET /api/v1/admin/ai/runtime-readiness`
- World-engine control-center posture is aggregated via:
  - `GET /api/v1/admin/world-engine/control-center`
- AI Engineer Suite backend APIs (Phase 2):
  - `GET /api/v1/admin/ai/runtime-dashboard`
  - `GET /api/v1/admin/ai/rag/status`
  - `POST /api/v1/admin/ai/rag/probe`
  - `POST /api/v1/admin/ai/rag/actions/<action_id>`
  - `GET/PATCH /api/v1/admin/ai/rag/settings`
  - `GET /api/v1/admin/ai/orchestration/status`
  - `GET/PATCH /api/v1/admin/ai/orchestration/settings`

- Controlled runtime settings APIs (Phase 2.5):
  - `GET /api/v1/admin/ai/presets`
  - `POST /api/v1/admin/ai/presets/apply`
  - `GET/PATCH /api/v1/admin/ai/advanced-settings`
  - `GET /api/v1/admin/ai/effective-config`
  - `GET /api/v1/admin/ai/settings-changes`
  - `POST /api/v1/admin/ai/advanced-settings/reset-overrides`

## Secret handling

- Provider credentials are write-only.
- Raw secrets are never returned by normal APIs.
- Envelope encryption uses per-secret DEK and environment KEK (`SECRETS_KEK`).

## Integration guardrail

Legacy env/default paths may remain only as documented bootstrap or emergency fallback seams and must never silently override resolved governance values during normal operation.

## Phase 1.5 refinements

- **Navigation:** the administration header exposes **AI Runtime Governance** as the single nav label for this surface (no duplicate “Operational Governance” row). Legacy URLs under `/manage/operational-governance/…` remain registered and render the same page.
- **Runtime readiness:** `GET /api/v1/admin/ai/runtime-readiness` adds `readiness_legend` (plain-language decoding of `mock_only_required` and `ai_only_valid`) and keeps structured `provider_summary` / `model_summary` / `route_summary` for inventory-at-a-glance in the admin UI.
- **World-Engine Control Center:** `GET /api/v1/admin/world-engine/control-center` adds `posture_at_a_glance` (desired vs observed lines without echoing secret material), `drill_down` (canonical manage paths and hints), and `operator_controls` entries annotated with `requires_path_parameter` / `ui_surface` where the backend action is not directly invokable from the control-center buttons.

## Operator UI

Administration tool surfaces (Phase 1):

- `/manage/ai-runtime-governance` (canonical)
- `/manage/operational-governance` (compatible alias)
- `/manage/operational-governance/bootstrap`
- `/manage/operational-governance/providers`
- `/manage/operational-governance/models`
- `/manage/operational-governance/routes`
- `/manage/operational-governance/runtime`
- `/manage/operational-governance/costs`
- `/manage/world-engine-control-center` (canonical)
- `/manage/world-engine-console` (deep-dive detail view)

Administration tool surfaces (Phase 2 AI Engineer Suite):

- `/manage/runtime-dashboard` (aggregated blocker-first runtime picture)
- `/manage/runtime-settings` (controlled presets, bounded advanced settings, effective config, and settings change feed)
- `/manage/rag-operations` (RAG runtime status, retrieval probe, bounded safe actions)
- `/manage/ai-orchestration` (LangGraph/LangChain status and bounded runtime settings)

## Phase 2.5 controlled settings workflow

1. Open `/manage/runtime-settings` and review available presets.
2. Apply a preset intentionally; each preset shows stability and impact notes.
3. Use bounded advanced settings only for explicit overrides.
4. Review effective config to confirm:
   - active preset
   - override count
   - value-source visibility (preset vs override)
   - guardrail warnings
5. Use `Clear overrides to active preset` for safe recovery posture.
6. Review recent settings changes for audit-friendly operator visibility.

### Presets currently available

- `safe_local` (recommended)
- `balanced` (recommended)
- `quality_first` (safe)
- `debug_trace_local` (debug/local-focused)

### Boundedness and guardrails

- Operators can apply canonical presets and bounded fields only.
- Raw JSON/config editing is intentionally out of scope.
- Validation rejects unsupported keys and invalid ranges/enums.
- Guardrail warnings highlight debug verbosity or posture tensions.
- This remains a controlled operational layer, not an unrestricted AI tuning lab.

## Phase 2 operator workflow

1. Open `/manage/runtime-dashboard` to identify top blockers and next actions.
2. Open `/manage/rag-operations` to:
   - inspect corpus/index/embedding posture
   - run retrieval query probes with route/status visibility
   - run bounded safe actions (`refresh_corpus`, `rebuild_dense_index`, `reload_runtime_retriever`)
   - update bounded retrieval settings (`retrieval_execution_mode`, profile, top-k, minimum score, embeddings posture)
3. Open `/manage/ai-orchestration` to:
   - inspect LangGraph dependency/runtime posture and recent execution summaries
   - inspect LangChain bridge/parser health signals
   - update bounded orchestration settings (`runtime_profile`, diagnostics verbosity, max retry, corrective feedback)
4. Use links back to canonical fix surfaces:
   - `/manage/ai-runtime-governance` for provider/model/route governance
   - `/manage/world-engine-control-center` for play-service/world-engine control-plane posture

## docker-up bootstrap guidance

`python docker-up.py up` now checks bootstrap readiness through
`/api/v1/bootstrap/public-status` and prints the setup path when initialization is
still required.

## Operator workflow (Phase 1)

1. Initialize env/secrets: `python docker-up.py init-env`
2. Edit `.env` provider keys as needed:
   - `OPENAI_API_KEY`
   - `OPENROUTER_API_KEY`
   - `ANTHROPIC_API_KEY`
   - keep Ollama key empty (no key required by default)
3. Start stack: `python docker-up.py up`
4. Open `/manage/ai-runtime-governance`
5. Configure provider inventory with first-class types:
   - `openai` (cloud, key required)
   - `ollama` (local, key optional)
   - `openrouter` (cloud, key required; template/staged support)
   - `anthropic` (cloud, key required; template/staged support)
6. Configure models and task routes in the same governance page.
7. Review `Runtime readiness and blockers`:
   - `mock_only_required: true` means at least one required AI link is still missing.
   - `ai_only_valid: true` means non-mock providers/models/routes are valid for AI-only operation.
8. Switch runtime mode away from `mock_only` only after readiness confirms validity.
9. Open `/manage/world-engine-control-center` to verify:
   - desired vs observed play-service posture
   - backend ↔ play-service connectivity
   - active run/session summary
   - current blockers/warnings and safe actions.

## Explicitly out of Phase 1

This phase does **not** claim complete operations consoles for:

- full RAG administration
- full LangGraph runtime orchestration
- full LangChain bridge administration
- broad world-engine authority expansion beyond existing safe controls.

## Explicitly out of Phase 2

Phase 2 is an AI-engineering console, not a free-form AI authoring platform. It intentionally does **not** include:

- arbitrary prompt editing
- visual graph editing
- arbitrary chain composition
- unrestricted tool injection
- full vector-store and corpus authoring suites
- bypasses of governance/runtime validation.
