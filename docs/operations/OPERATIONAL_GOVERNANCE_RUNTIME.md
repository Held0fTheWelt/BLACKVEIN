# Operational Settings, AI Runtime Governance, and World-Engine Control Center

Phase 1 establishes operator-usable administration surfaces for the minimum viable AI runtime path and world-engine control posture.

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

## Secret handling

- Provider credentials are write-only.
- Raw secrets are never returned by normal APIs.
- Envelope encryption uses per-secret DEK and environment KEK (`SECRETS_KEK`).

## Integration guardrail

Legacy env/default paths may remain only as documented bootstrap or emergency fallback seams and must never silently override resolved governance values during normal operation.

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
