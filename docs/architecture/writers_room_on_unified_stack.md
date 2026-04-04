# Writers-Room on Unified Stack

Status: Canonical Milestone 9 architecture and implementation baseline.

## Canonical flow

Writers-Room now uses a backend workflow endpoint (`POST /api/v1/writers-room/reviews`) as the primary architecture.

Workflow stages:

1. JWT-authenticated request intake.
2. LangGraph Writers-Room seed workflow invocation.
3. Shared retrieval capability call (`wos.context_pack.build`, domain `writers_room`).
4. Shared model routing invocation (story-runtime-core routing + adapters with fallback).
5. Recommendation synthesis and evidence collation.
6. Guarded review bundle capability call (`wos.review_bundle.build`).
7. Response package for human review (recommendations only, not direct publish edits).

## Shared-stack dependencies

- Retrieval: `wos.context_pack.build`
- Orchestration: `build_seed_writers_room_graph()`
- Capability layer: `CapabilityRegistry`
- Model routing/adapters: `story_runtime_core` routing + adapters

No isolated direct-model-call path is treated as canonical.

## Human-in-the-loop points

Outputs are explicitly recommendation-only and include:

- retrieved evidence sources,
- identified issues,
- recommendation list,
- review bundle metadata,
- capability audit trail.

Publishing authority remains in backend/admin governance.

## Authoritative output semantics

- `recommendations`: advisory output for human review.
- `review_bundle`: governance artifact, not auto-apply payload.
- `outputs_are_recommendations_only`: explicit true flag in response contract.

## Governance handoff

Governance/API visibility is provided via:

- Writers-Room review response payload (bundle + evidence + audit),
- capability audit endpoints in session governance routes.

## Legacy handling

Legacy direct chat (`writers-room` oracle route) is retained as transitional only:

- moved to explicit `/legacy-oracle` route,
- canonical UI now points to unified workflow first,
- legacy mode is marked deprecated in UI and service output metadata.

## Deferred beyond M9

- richer admin UI for bundle triage and decision workflow,
- asynchronous queue orchestration for large review jobs,
- deeper dramaturgy scoring dimensions.
