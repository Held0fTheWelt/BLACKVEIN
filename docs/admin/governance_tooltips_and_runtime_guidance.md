# Governance Tooltips and Runtime Guidance

This document defines the Administration Tool tooltip/help model for runtime governance surfaces.

## Tooltip categories

- `behavior`: What the field/section controls in actual code paths.
- `recommended`: Safe operator posture and sequencing.
- `warning`: Dangerous combinations, false-green risks, and policy boundaries.
- `authority`: Whether a value can affect readiness/commit/validation outcome.
- `evidence`: Local-only vs staging/live evidence meaning.
- `ownership`: `admin_editable`, `admin_read_only`, `env_only`, `backend_config_owned`.
- `source`: Provenance reference (ADR, service, route, policy doc).

## Evidence tier guidance

- `local_only`: local implementation/test/projection evidence only; not staging/live proof.
- `runtime_path_participation`: runtime path touched, but still not promotion-ready by itself.
- `staging_pending`: intended for staging verification, evidence incomplete.
- `staging_verified`: staged environment proof collected and reproducible.
- `live_verified`: production/live proof collected and reproducible.

Promotion claims must follow:

- `docs/MVPs/capability_matrix_live_claim_gates.md`
- `docs/MVPs/capability_matrix_status_and_adr_relations.md`

## ADR-0041 guidance posture

Critical ADR-0041 flags are env-owned and read-only in admin guidance surfaces:

- `ADR0041_VALIDATOR_DISPATCH_MODE`
- `ADR0041_SCOPED_CO_AUTHORITY_ENABLED`
- `ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED`
- `ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED`
- `ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED`
- `ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED`
- `ADR0041_PLAN_PROJECTION_ENABLED`

Authority boundaries:

- ADR-0041 readiness path is veto-only in bounded conditions.
- ADR-0041 cannot upgrade seam rejection to allow.
- Commit and `validation_outcome` remain governed by canonical seam authority.

Primary sources:

- `ai_stack/runtime_readiness_consumer.py`
- `ai_stack/runtime_aspect_ledger.py`
- `docs/ADR/adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md`

## AI Runtime recommended combinations

- Local development:
  - `safe_local`, `mock_only`, `local_only`
  - Retrieval `disabled` or `sparse_only`
  - Langfuse optional
  - No staging/live claims
- Staging validation:
  - provider credentials + model/route readiness green
  - Langfuse enabled and trace health confirmed
  - MCP diagnostics not blocking
  - capability evidence still policy-gated
- Runtime authority pilot:
  - ADR-0041 plan/projection surfaces enabled by env policy
  - readiness consumer only under governance-approved bounded rollout
  - local-only unless staging proof exists
- Production/live:
  - governance-approved flags only
  - no env-only mutation from admin UI
  - evidence-backed promotion only

Primary source:

- `backend/app/services/ai_engineer_suite_service.py`

## Inventory summary (Tooltip pass scope)

- Runtime Settings (`runtime_settings.html`): execution/retrieval/provider/profile guidance, evidence and authority warnings.
- AI Runtime Governance (`operational_governance.html`): entity-to-mode sequence and readiness interpretation.
- Observability Settings (`observability_settings.html`): credential readiness vs score proof distinction and danger-zone warning.
- Runtime Config Truth (`runtime_config_truth.html`): explicit `requires_http_probe` non-ready semantics.
- Governance Console (`governance_console.html`): ADR-0041, validator, evidence-tier, and ownership guidance.

## Tooltip inventory snapshot (classification)

- Runtime Settings: generation/validation/provider/profile/retrieval controls -> `needs_tooltip`, `should_show_recommended_mode`.
- Runtime Settings advanced toggles (`embeddings`, `corrective_feedback`, `verbosity`, `max_retry`) -> `dangerous_without_warning` for debug-heavy combinations.
- Runtime Config Truth statuses (`ready`, `partial`, `degraded`, `requires_http_probe`) -> `misleading_label` risk addressed with explicit probe warning.
- Observability credentials/status pills -> `needs_tooltip`, `dangerous_without_warning`, `should_link_to_docs`.
- Observability disable action -> `dangerous_without_warning`.
- Operational Governance provider/model/route forms -> `editable_but_backend_unclear` risk reduced with sequencing guidance and source labels.
- Operational runtime modes -> `should_show_recommended_mode`, `should_link_to_docs`.
- Governance Console ADR-0041 flags -> `read_only_but_looks_editable` risk reduced via `env_only` + `admin_read_only` chips.
- Capability Matrix rows -> `needs_tooltip`, `should_show_recommended_mode`, `should_link_to_docs`.
- Validator Registry rows -> `dangerous_without_warning` for unavailable validators if misunderstood; now explicitly marked non-passing.
- Langfuse/MCP evidence rows -> `misleading_label` risk addressed with local vs staging/live boundary copy.
- Narrative Runtime Systems rows -> `needs_tooltip` and `should_link_to_docs` for interpretation scope.

## Accessibility and interaction

- Desktop: info icon popovers on hover/focus.
- Keyboard: focusable info icon with visible tooltip.
- Small screens/touch: inline guidance cards remain visible without hover dependency.

## Non-goals

- No fake writable controls.
- No capability promotion action from UI.
- No contradiction with ADR-0039 evidence boundaries.
