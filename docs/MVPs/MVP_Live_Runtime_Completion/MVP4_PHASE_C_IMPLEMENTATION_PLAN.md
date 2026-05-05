# MVP4 Phase C Implementation Plan

**Status**: Implementation Description (Phase A and Phase B exist; Phase C closes integration gaps)  
**Related**: `adr-0032-mvp4-live-runtime-setup-requirements.md`, `MVP4_PHASE_A_IMPLEMENTATION_PLAN.md`, `MVP4_PHASE_B_IMPLEMENTATION_PLAN.md`  
**Primary Goal**: Connect the existing governance, evaluation, and operator-surface scaffolding to the live runtime so operator evidence reflects real runtime truth instead of placeholders.

---

## Phase C Principle: Integrate Existing Truth, Do Not Re-Invent It

Phase C is not a greenfield build anymore.

Large parts of the intended governance stack already exist:

- token budget services
- override audit event types and granularity controls
- evaluation pipeline scaffolding
- operator routes under `/api/v1/admin/mvp4/...`
- narrative governance pages in the administration tool
- Phase B `phase_costs` and truthful `cost_summary`

The correct Phase C job is therefore:

1. Finish the still-open runtime contracts that affect governance and operator evidence.
2. Replace placeholders with live data.
3. Align existing routes, templates, and services with Phase A/B truth.
4. Remove stale assumptions from documentation and implementation notes.

Phase C must not treat already-implemented components as if they were missing. It must also not force a different runtime truth than Phase B intentionally established.

---

## What Phase C Means After Phase B

After Phase B, the runtime can already emit:

- truthful `DiagnosticsEnvelope`
- `degradation_timeline`
- per-phase `phase_costs`
- aggregated `cost_summary`
- Langfuse trace correlation on backend and world-engine paths

Phase C builds on that and completes:

1. cost-aware governance tied to actual `phase_costs`
2. operator panels fed by live diagnostics instead of placeholder values
3. override operations with auditable lifecycle evidence
4. evaluation baseline and regression workflows using real runtime outputs
5. narrative streaming contract completion for frontend and operator inspection
6. observability controls aligned with the current runtime setup only

---

## Contract Interpretation

### Contract 1: Backend -> World-Engine Handoff

Current state:

- Backend already validates runtime-profile handoff fields and merges them into `runtime_projection`.
- `game_service.create_story_session()` already sends the full `runtime_projection` to world-engine.

Phase C does **not** need to re-solve backend handoff. It should:

- surface actor ownership truth in operator views
- add world-engine-side hard validation for direct `/api/story/sessions` calls where appropriate
- make contract violations visible in governance/operator evidence

### Contract 2: Opening Truthfulness

Current state:

- GoC opening is intentionally deterministic LDSS in the current runtime path.
- Phase B now reports that truthfully as deterministic, non-billable, zero-cost provenance.

Phase C must **not** redefine this as a mandatory provider-backed opening.

Phase C should instead:

- evaluate whether the opening is experientially acceptable
- correlate opening diagnostics and trace evidence
- preserve the distinction between deterministic truth and provider truth

### Contract 3: Frontend Playability

Current state:

- `can_execute` is already tied to `story_window.entry_count > 0`.

Phase C should focus on:

- health-panel visibility for playability divergence
- player-session responses carrying the streaming handoff fields the frontend actually needs

### Contract 4: Diagnostics Truthfulness

Current state:

- Phase A and Phase B established truthful diagnostics and cost provenance.
- diagnostics construction errors are no longer silently swallowed in the story manager.

Phase C should:

- consume those diagnostics in governance services and operator surfaces
- avoid inventing separate cost counters that drift away from runtime truth

### Contract 5: Narrative Streaming

Current state:

- world-engine exposes `stream-narrator`
- story manager emits `narrator_streaming` internally during turn execution
- frontend streaming still points at a direct `/api/story/...` path and depends on top-level response fields that are not consistently provided through the player-session API

Phase C must finish this contract.

---

## Current Code Reality

Use the code that already exists.

| Area | Existing path | Current role |
|---|---|---|
| Token budget service | `backend/app/services/observability_governance_service.py` | Session budget config, consumption, degradation decisions |
| Cost dashboard service | `backend/app/services/observability_governance_service.py` | Session cost summary storage and aggregate report placeholders |
| Override audit types/config | `backend/app/auth/admin_security.py` | `OverrideAuditEvent`, `OverrideAuditConfig`, config manager, filtered logging |
| Evaluation pipeline | `ai_stack/evaluation_pipeline.py` | Rubric, baseline container, weights, score recording, regression scaffold |
| Backend governance routes | `backend/app/api/v1/operational_governance_routes.py` | `/admin/mvp4/...` token budget, overrides, evaluation, Langfuse toggle |
| Backend observability config routes | `backend/app/api/v1/observability_governance_routes.py` | Current Langfuse config, credential, test, disable flows |
| Runtime diagnostics truth | `ai_stack/diagnostics_envelope.py` | `DiagnosticsEnvelope`, `degradation_timeline`, `cost_summary` |
| Runtime phase cost truth | `ai_stack/runtime_cost_attribution.py` | canonical phase-cost shape and aggregation |
| World-engine diagnostics endpoint | `world-engine/app/api/http.py` | `/api/story/sessions/{session_id}/diagnostics-envelope` |
| World-engine streaming endpoint | `world-engine/app/api/http.py` | `/api/story/sessions/{session_id}/stream-narrator` |
| Narrative gov summary endpoint | `world-engine/app/api/http.py` | `/api/story/runtime/narrative-gov-summary` |
| Admin pages | `administration-tool/templates/manage/narrative_governance/` | runtime view, governance health panels, override pages |
| Admin page registration | `administration-tool/route_registration_manage_sections.py` | manage routes for narrative governance pages |
| Frontend streaming client | `frontend/static/play_narrative_stream.js` | EventSource-based narrator streaming |

Important correction:

- There is no `administration-tool/app/admin_routes.py` in the current implementation path.
- The previous Phase C document used outdated locations and should not be followed literally.

---

## Remaining Gaps

These are the real Phase C integration gaps.

### Gap 1: Frontend Streaming Contract Is Still Incomplete

Current problems:

- frontend EventSource still points to `/api/story/sessions/{session_id}/stream-narrator`
- player-session responses do not consistently expose top-level `narrator_streaming` in the shape the frontend expects
- operator and player paths do not yet present one clean streaming contract

Required result:

- player-session bootstrap and turn responses expose top-level `narrator_streaming` when active
- frontend uses the correct reachable route or proxy strategy
- streaming state can be correlated with the same runtime session and trace evidence

### Gap 2: World-Engine Direct Session Create Is Not Hardened The Way Backend Handoff Is

Current problems:

- backend already validates actor ownership before handoff
- direct world-engine session creation still trusts incoming `runtime_projection` more than the backend path does

Required result:

- for GoC solo and similar governed paths, direct world-engine session creation rejects missing or malformed ownership fields early
- diagnostics/operator evidence clearly reflect the reason for rejection

### Gap 3: Token Budget Logic Is Not Yet Connected To Phase B Cost Truth

Current problems:

- token budget primitives exist
- Phase B `phase_costs` exist
- the runtime path does not yet consistently update budget consumption from real turn diagnostics

Required result:

- budget consumption is computed from committed turn `cost_summary` and/or `phase_costs`
- cost-aware degradation decisions operate on real runtime evidence, not synthetic counters

### Gap 4: Cost Dashboard Still Uses Placeholder Aggregation

Current problems:

- `CostDashboard` exists
- daily/weekly reports are still placeholders
- no end-to-end feed from live diagnostics into aggregate operator reports

Required result:

- session summaries update from committed turns
- daily/weekly aggregates are derived from stored session cost truth
- operator dashboards no longer show hardcoded zero-style values except when runtime truth is genuinely zero

### Gap 5: Governance Health Panels Still Display Placeholder Data

Current problems:

- governance health panel page exists
- panel JS still uses placeholders or partial data
- diagnostics, budget, evaluation, and cost views are not yet fully joined

Required result:

- panels read live diagnostics envelope data
- panels show actual degradation timeline, cost summary, evaluation state, and override state
- UI labels reflect current implementation truth instead of earlier Phase A comments

### Gap 6: Evaluation Pipeline Is Scaffolded, Not Operationally Closed

Current problems:

- rubric, baseline object, weights, and manual tuning routes exist
- there is no real populated baseline workflow
- regression checking is still a structural placeholder

Required result:

- baseline dataset defined for governed runtime scenarios
- turn annotations persist in the intended store
- regression checks compare live/runtime evidence against the stored baseline

### Gap 7: Langfuse Controls Need To Match The Current Runtime Setup Only

Current problems:

- MVP4 admin routes include a per-session Langfuse toggle stub
- your runtime direction is “current setup only”, not legacy switch layers
- real observability configuration already lives under `/api/v1/admin/observability/...`

Required result:

- Phase C uses the current observability configuration model
- no unnecessary legacy-style per-session Langfuse control becomes a dependency
- any session-level control that remains must be justified by actual runtime behavior, not documentation drift

---

## What Is Already Correct And Must Be Preserved

Phase C must preserve the following truths established by earlier work:

1. Deterministic opening remains valid if it is labeled deterministic.
2. Zero tokens and zero cost remain valid for deterministic or mock phases.
3. `can_execute` remains tied to actual story window content.
4. Diagnostics failures remain visible and fail-fast rather than being hidden.
5. Operator surfaces should consume canonical diagnostics rather than reconstruct alternate truth.

---

## Implementation Order

### Step 1: Finish The Streaming Contract

Primary files:

- `frontend/static/play_narrative_stream.js`
- `backend/app/api/v1/game_routes.py`
- `world-engine/app/api/http.py`

Required work:

- expose top-level `narrator_streaming` in player-session bootstrap and turn responses
- ensure the frontend uses a reachable endpoint path for streaming
- keep session ID and trace correlation intact between player response and EventSource stream

Expected result:

```json
{
  "runtime_session_id": "...",
  "turn": {...},
  "narrator_streaming": {
    "status": "streaming",
    "session_id": "..."
  }
}
```

### Step 2: Harden World-Engine Session Validation For Governed Runtime Paths

Primary file:

- `world-engine/app/story_runtime/manager.py`

Required work:

- validate required ownership fields for governed GoC story session creation
- fail clearly when `human_actor_id`, `npc_actor_ids`, or `actor_lanes` are missing or malformed
- keep generic non-GoC paths flexible where governance does not require those fields

Expected result:

- backend handoff remains the normal path
- direct invalid world-engine calls do not produce misleading sessions

### Step 3: Connect Token Budgets To Real Turn Diagnostics

Primary files:

- `backend/app/services/observability_governance_service.py`
- `backend/app/api/v1/game_routes.py`
- `world-engine/app/story_runtime/manager.py`

Required work:

- update session cost summary from committed turn diagnostics
- derive token-budget consumption from truthful `cost_summary`
- call degradation logic using actual runtime usage, not guessed values

Recommended source of truth:

```json
{
  "cost_summary": {
    "input_tokens": 0,
    "output_tokens": 0,
    "cost_usd": 0.0,
    "phase_costs": {
      "ldss": {...},
      "narrator": {...}
    }
  }
}
```

### Step 4: Replace Cost Dashboard Placeholders With Live Aggregation

Primary files:

- `backend/app/services/observability_governance_service.py`
- `backend/app/api/v1/operational_governance_routes.py`

Required work:

- persist/update per-session cost summaries from live turns
- implement daily and weekly aggregation from stored session truth
- expose values that match Phase B aggregation semantics

Do not:

- scrape Langfuse cloud as the primary accounting source for runtime truth
- duplicate cost logic separately from Phase B cost attribution

### Step 5: Wire Governance Health Panels To Live Data

Primary files:

- `administration-tool/templates/manage/narrative_governance/governance_health_panels.html`
- `administration-tool/static/governance_health_panels.js`
- `backend/app/api/v1/operational_governance_routes.py`
- `world-engine/app/api/http.py`

Required work:

- fetch live diagnostics envelope data
- show actual `quality_class`, `degradation_timeline`, `cost_summary`, budget usage, and evaluation state
- remove comments and UI assumptions that still describe Phase A placeholder behavior

Panel data sources should be explicit:

- runtime diagnostics: world-engine diagnostics endpoints
- budget and overrides: backend `/api/v1/admin/mvp4/...`
- observability settings: backend `/api/v1/admin/observability/...`
- evaluation state: backend evaluation routes

### Step 6: Close The Evaluation Workflow

Primary files:

- `ai_stack/evaluation_pipeline.py`
- `backend/app/api/v1/operational_governance_routes.py`
- `administration-tool/templates/manage/narrative_governance/evaluations.html`

Required work:

- define baseline storage and population workflow
- record operator annotations against real turns
- run regression checks against live/recorded evidence
- make weight tuning and baseline state visible to operators

Phase C evaluation should answer:

- what baseline are we comparing against?
- what turns were annotated?
- what regression signals were detected?
- what rubric weights are active now?

### Step 7: Align Langfuse Controls With The Current Runtime Setup

Primary files:

- `backend/app/api/v1/observability_governance_routes.py`
- `backend/app/api/v1/operational_governance_routes.py`
- admin observability templates/scripts

Required work:

- prefer the current observability config and credential routes for actual enable/disable and connectivity state
- treat the Phase-C per-session toggle stub as optional or remove/reframe it if it is not backed by runtime behavior
- avoid introducing legacy-style switch matrices

For MVP4, the important operator truth is:

- whether Langfuse is configured
- whether credentials are present
- whether the runtime can connect
- whether traces are actually correlated across the live path

---

## Tests Required

Phase C is complete only when tests prove the integration, not just the shape of classes.

### Streaming Contract

- player-session create/turn responses expose `narrator_streaming` when appropriate
- frontend EventSource path matches the reachable runtime path
- streaming session ID matches the active runtime session

### Session Validation

- world-engine rejects governed story sessions with missing actor ownership
- backend happy path with valid ownership still passes

### Budget And Cost Integration

- committed turn diagnostics update stored session cost summary
- budget usage increases from truthful turn cost data
- warning and critical degradation thresholds trigger from real usage

### Operator Panels

- governance health panel endpoints return live structures
- JS renders real values instead of placeholder zero data when runtime data exists

### Evaluation

- rubric retrieval works
- baseline retrieval and persistence work
- turn annotation storage works
- regression check consumes populated baseline data

### Observability

- admin observability status reflects current config
- current runtime path still produces trace correlation after Phase C changes

---

## Stop Gate

Phase C is complete when all of the following are true:

1. player-session bootstrap and turn responses provide a working streaming contract
2. frontend narrator streaming connects to a reachable endpoint without path mismatch
3. governed world-engine session creation rejects malformed ownership handoff
4. token budget state is driven by real committed-turn cost truth
5. cost dashboard aggregates session truth instead of placeholders
6. governance health panels display live diagnostics, budget, and evaluation evidence
7. evaluation baseline and annotation flow operate on real runtime turns
8. observability controls reflect the current runtime setup only
9. Phase A and Phase B tests continue to pass
10. new Phase C integration tests prove behavior end to end

---

## Not Phase C

The following are out of scope for this document:

- replacing deterministic opening with mandatory provider-backed opening
- reintroducing synthetic token counts for deterministic runtime paths
- rebuilding admin routing from scratch in non-existent files
- treating Langfuse cloud queries as the sole source of runtime cost truth
- adding legacy observability switch layers you do not want

---

## Bottom Line

Phase C should now be understood as an **integration closure phase**, not a blank implementation phase.

The architecture is largely present. The remaining work is to connect:

- truthful runtime diagnostics
- budget and cost governance
- streaming handoff
- evaluation workflows
- operator surfaces

Once those links are finished, MVP4 has a coherent live-runtime governance layer that matches the implementation reality instead of an earlier target-state sketch.
