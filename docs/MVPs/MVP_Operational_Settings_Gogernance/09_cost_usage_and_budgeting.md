# 09 Cost, Usage, and Budgeting

## Why cost governance is part of the MVP

The system allows flexible provider/model routing.
Without cost visibility, the operator cannot safely use:
- AI-only mode
- hybrid mode
- preview generation
- semantic validation
- research synthesis
- writers-room assistance

## Cost measurement methods

### `provider_reported`
Use provider-reported billing/usage when available.

Current story-runtime cost truth treats provider-reported token usage as the
only acceptable source for `billing_mode="provider_usage"`. If a provider call
succeeds but the adapter response does not include usage, the runtime records an
explicit unavailable cost record instead of estimating from generated text.

### `price_table_estimated`
Compute cost from token counts and configured price tables.

### `flat_per_request`
Use a flat configured cost per request.

### `none`
No cost estimation available.

Deterministic and mock runtime paths are not billing failures. They must record
zero cost with explicit provenance such as `billing_mode="deterministic"` /
`token_source="deterministic_no_model_call"` or `billing_mode="mock"` /
`token_source="mock_no_model_call"`.

## Usage event minimum capture

Each eligible runtime call should create an `AIUsageEvent` capturing:
- provider
- model
- task kind
- workflow scope
- success/failure
- latency
- tokens if available
- retry used
- fallback used
- degraded mode used
- estimated/actual cost

## Rollups

At minimum support:
- daily provider rollups
- daily model rollups
- daily workflow rollups
- retry/fallback cost impact visibility

## Budget policies

Budgets should support:
- global daily limit
- global monthly limit
- provider-level budget
- workflow-level budget
- warning threshold %
- optional hard-stop behavior

Current backend story-runtime preflight:
- `create_story_session(...)` checks governed cost hard-stop policies before
  opening a world-engine session.
- `execute_story_turn(...)` checks governed cost hard-stop policies and the
  local runtime token-budget status before sending the turn to world-engine.
- Exhausted runtime token budgets surface as
  `runtime_token_budget_exhausted` with HTTP 409 semantics.
- Governed cost-policy failures surface as the governance error code, e.g.
  `budget_limit_exceeded`, also before the world-engine call.

Provider-specific preflight is best-effort: it can only match a provider when
that provider is known from runtime projection or other pre-turn metadata. The
post-turn `cost_summary` remains the more complete attribution surface.

## Alerts

At minimum:
- budget warning threshold reached
- monthly budget exceeded
- unexpectedly high fallback cost rate
- provider usage spike
- expensive route in cost-aware profile

## UI requirements

### Costs & Usage page must show
- daily/monthly totals
- provider comparison
- model comparison
- workflow comparison
- cost method used
- missing billing confidence note if estimated only
- top expensive routes
- retry/fallback contribution

## Runtime configuration impact

The resolved runtime config must include enough pricing and budget policy data to:
- attribute usage correctly
- block invalid cost modes
- drive alerts and health summaries

Runtime diagnostic impact:
- World-engine committed turns expose canonical `cost_summary.phase_costs`.
- The local source of truth is `graph_state["phase_costs"]`; Langfuse is an
  export/correlation surface.
- Backend post-turn ingestion consumes `diagnostics_envelope.cost_summary` for
  runtime token-budget accounting.
- Local verification is not live-provider or staging proof unless paired with
  provider/environment metadata and trace/query identifiers.
