# MCP Capability Layer in World of Shadows

Status: C2 repaired operational workflow baseline.

## Objective

Define MCP as a governed capability surface with explicit schemas, mode boundaries, audit semantics, and denial behavior.

## Capability categories

- Retrieval capabilities:
  - `wos.context_pack.build`
  - `wos.transcript.read`
- Action capabilities:
  - `wos.review_bundle.build`

Retrieval and action are separated by explicit `kind` metadata and mode gates.

## Actor and mode permissions

Allowed mode boundaries:

- `runtime`: retrieval-only capabilities needed for authoritative turn support.
- `writers_room`: retrieval + review bundle generation.
- `improvement`: retrieval + review bundle generation.
- `admin`: transcript and governance-facing access patterns.

Denied invocations emit typed `CapabilityAccessDeniedError` and are always audited.

## Capability definition contract

Each capability defines:

- capability name,
- input schema,
- result schema,
- allowed mode set,
- audit requirement flag,
- failure semantics.

This contract is implemented in `wos_ai_stack/capabilities.py`.

## Audit requirements

Every invocation writes an audit row with:

- timestamp,
- capability name,
- mode,
- actor,
- outcome (`allowed`, `denied`, `error`),
- trace id,
- error detail (if any).

Audit rows are surfaced in runtime graph diagnostics and governance endpoint responses.

## Runtime and workflow integration

Active workflow usage now includes:

- Runtime authoritative turn path:
  - `RuntimeTurnGraphExecutor` invokes `wos.context_pack.build` in `runtime` mode.
- Writers-Room production review path:
  - `writers_room_service.run_writers_room_review` invokes `wos.context_pack.build` in `writers_room` mode.
  - `writers_room_service.run_writers_room_review` invokes `wos.review_bundle.build` in `writers_room` mode.
- Improvement experiment/recommendation path:
  - `POST /api/v1/improvement/experiments/run` invokes `wos.context_pack.build` in `improvement` mode.
  - `POST /api/v1/improvement/experiments/run` invokes `wos.review_bundle.build` in `improvement` mode.
  - capability failure is explicit (`502 capability_workflow_failed`) with capability audit rows returned.

This is materially beyond capability registration-only behavior.

## Governance visibility

Backend exposes `GET /api/v1/sessions/<session_id>/capability-audit` for governance-side inspection of capability invocations recorded in world-engine diagnostics.

Improvement responses now also return `capability_audit` rows in-band for direct governance review of tool invocations in that workflow.

## MCP server alignment

`tools/mcp_server/tools_registry.py` now includes `wos.capabilities.catalog` to expose the guarded capability catalog through the MCP tool surface.

## Current intentionally out of scope

- signed/immutable long-term audit storage,
- external policy engines with environment-level claim delegation,
- broad write-action expansion outside recommendation-oriented governed workflows.
