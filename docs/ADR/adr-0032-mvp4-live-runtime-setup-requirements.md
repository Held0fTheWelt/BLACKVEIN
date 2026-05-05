# ADR-0032: MVP4 Live Runtime Setup Requirements

## Status

Accepted

## Date

2026-05-05

## MVP

4 - End-to-end live story execution

## Related ADRs

- [ADR-0030](adr-0030-docker-up-complete-bootstrap.md) - Docker bootstrap
- [ADR-0031](adr-0031-env-configuration-governance.md) - Environment governance

## Context

MVP4 is no longer defined by the original defect list alone. The live path has since been reworked across backend, frontend, play-service, observability, and governance storage.

The current requirements need to describe the implementation that now actually exists:

- backend forwards complete governed runtime projections
- world-engine rejects invalid governed session creates
- opening and turn diagnostics include truthful cost summaries
- deterministic phases are recorded truthfully as zero-token/zero-cost work
- `narrator_streaming` is forwarded through the live contract
- governance, cost, and evaluation data are available through backend operator routes
- Docker uses Redis to keep runtime-governance truth coherent across workers

This ADR supersedes earlier statements that treated the following as still-open core truths:

- actor ownership is generally lost in the live handoff
- `can_execute` may validly be `true` with an empty story window
- diagnostics errors are swallowed as normal behavior
- deterministic opening behavior is itself an MVP4 contract failure

Those are no longer the right baseline.

## Decision

MVP4 is defined by the following runtime requirements.

### 1. Governed session-create handoff is complete and enforced

Backend-to-world-engine session creation for governed live modules must carry:

- `selected_player_role`
- `human_actor_id`
- `npc_actor_ids`
- `actor_lanes`
- runtime/content identity fields needed for the profile handoff

World-engine must reject incomplete or inconsistent governed requests with a hard contract error exposed as HTTP `400`.

This is now a required live invariant, not a best-effort enrichment.

### 2. Opening and turn execution must be truthful, not cosmetically "live"

The system may use deterministic runtime phases such as LDSS, but they must be represented honestly:

- deterministic phases report `0` token usage and `0` cost
- cost attribution marks the work as non-billable deterministic execution
- later provider-backed phases can contribute real provider usage without being mixed with invented token numbers

MVP4 does not require every opening to be provider-backed. It requires the system to tell the truth about what happened.

### 3. Diagnostics are mandatory execution truth

Each committed turn must carry a diagnostics envelope that can explain:

- validation outcome
- quality class and degradation signals
- route/execution provenance
- cost summary and phase costs
- narrator streaming state when present

Diagnostics construction failures are not acceptable silent warnings on the happy path.

### 4. Frontend playability must follow story-window truth

The player-facing bundle must not present a session as executable when the story window is empty.

Current contract:

- `can_execute` is derived from real story-window entry count
- `narrator_streaming` is promoted through backend and frontend payloads
- empty-state behavior is explicit rather than silently interactive

### 5. Operator truth is part of MVP4

MVP4 is not only the player runtime. It also includes operator-visible truth for:

- session summary
- truthful daily and weekly cost reports
- token budget status
- active overrides
- evaluation recent-turns, baselines, and regression checks

These surfaces must be backed by the same runtime diagnostics and cost data produced by the live path.

### 6. Shared governance storage is required in Docker

For local Docker runtime, governance truth must survive multiple backend workers.

Therefore the standard MVP4 Docker setup includes:

- Redis service in Compose
- `REDIS_URL` in bootstrap environment
- backend initialization that attaches Redis-backed JSON storage when available

In-process fallback remains acceptable outside Docker or as degraded local fallback, but it is not the canonical Docker implementation.

## Implementation Notes

### Current fulfilled requirements

The implementation now includes:

- complete `runtime_projection` handoff from backend live session creation
- hard world-engine validation of governed direct session-create calls
- `StorySessionContractError` mapped to HTTP `400`
- top-level `narrator_streaming` propagation in backend and frontend session payloads
- truthful `diagnostics_envelope.cost_summary` ingestion into backend governance services
- session summaries and cost/evaluation operator routes under `/api/v1/admin/mvp4/...`
- Redis-backed runtime-governance storage initialization in backend app startup

### Remaining boundary of MVP4

MVP4 still stops at runtime and operator closure. It does not itself claim to complete every later frontend staging or final end-to-end UX proof expected in MVP5.

## Consequences

### Positive

- MVP4 is now documented as a truthful runtime contract instead of a stale bug ledger.
- Deterministic runtime work is accounted for without fake cost inflation.
- Operator dashboards and evaluation flows are part of the live-runtime requirement set.
- Docker deployment expectations now match the multi-worker backend reality.

### Negative / risks

- Any future docs that describe MVP4 purely as "provider-backed opening" will be misleading.
- If Redis is removed from Docker without replacement, operator truth becomes worker-local and unreliable.

## Verification

MVP4 should be considered satisfied only when the following remain true:

- [ ] governed session-create requests without actor ownership are rejected
- [ ] live player-session bundles expose coherent `can_execute` and `narrator_streaming`
- [ ] turn diagnostics include truthful `cost_summary` / `phase_costs`
- [ ] budget and cost aggregation consume live diagnostics output
- [ ] operator session summary, cost, and evaluation routes report real runtime data
- [ ] Docker runtime initializes shared governance storage through Redis

## References

- `backend/app/services/game_service.py`
- `backend/app/api/v1/game_routes.py`
- `backend/app/api/v1/operational_governance_routes.py`
- `backend/app/services/observability_governance_service.py`
- `frontend/app/routes_play.py`
- `world-engine/app/story_runtime/manager.py`
- `world-engine/app/api/http.py`
- `ai_stack/evaluation_pipeline.py`
- `docker-compose.yml`
- `docker-up.py`
