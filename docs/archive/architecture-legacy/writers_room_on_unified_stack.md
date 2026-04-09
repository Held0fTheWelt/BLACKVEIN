# Writers-Room on Unified Stack

Status: Canonical Milestone 9 architecture and implementation baseline.

## Canonical flow

Writers-Room now uses a backend workflow endpoint (`POST /api/v1/writers-room/reviews`) as the primary architecture.

Workflow stages (see `workflow_manifest.stages` in review payloads for timestamps):

1. JWT-authenticated request intake (`request_intake`).
2. LangGraph Writers-Room seed workflow invocation (`workflow_seed`).
3. Shared retrieval capability call (`wos.context_pack.build`, domain `writers_room`) (`retrieval_analysis`).
4. Shared model routing invocation (story-runtime-core routing + adapters with fallback) (`proposal_generation`).
5. Structured artifact packaging (`proposal_package`, `comment_bundle`, patch/variant candidates) (`artifact_packaging`).
6. Guarded review bundle capability call (`wos.review_bundle.build`) (`governance_envelope`).
7. LangChain retriever bridge preview (`retrieval_bridge_preview`) for cross-stack visibility.
8. Human review pending (`human_review_pending`) with explicit HITL decisions: `accept`, `reject`, or `revise` (non-terminal; may repeat).

API: `POST /api/v1/writers-room/reviews/<review_id>/decision` with `decision` in `accept` | `reject` | `revise`.

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
- typed `recommendation_artifacts` (roadmap §7.3 metadata each),
- review bundle metadata,
- capability audit trail.

Publishing authority remains in backend/admin governance.

## Authoritative output semantics

- `recommendation_artifacts`: advisory, typed records (`analysis_artifact`) for human review.
- `review_bundle`: governance envelope (`proposal_artifact` typing on the merged payload), not auto-apply.
- `governance_outcome_artifact`: present only after terminal `accept` or `reject` (not during `pending_human_review` / `pending_revision`).
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
