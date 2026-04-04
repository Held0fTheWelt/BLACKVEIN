# Improvement Loop in World of Shadows

Status: D2 repaired mutation/evaluation baseline.

## Canonical loop

1. Select baseline (`baseline_id`, e.g. `god_of_carnage`).
2. Create candidate variant with explicit lineage.
3. Execute sandbox experiment (isolated from authoritative publish state).
4. Evaluate run outputs with concrete metrics.
5. Build recommendation package for governance review.
6. Expose packages through backend governance API.

`POST /api/v1/improvement/experiments/run` returns **`workflow_stages`**: ordered steps with UTC timestamps (`variant_resolution`, `baseline_context`, `sandbox_execution`, `evaluation_and_recommendation_draft`, `retrieval_improvement_context`, `transcript_tool_evidence`, `governance_review_bundle`). The same list is persisted on the stored **`recommendation_package`**.

**`evidence_bundle`** on the recommendation package explicitly attaches **`retrieval_source_paths`** (from `wos.context_pack.build`), **`transcript_evidence`** (run id, turn counts from `wos.transcript.read`), metric snapshots, and **`governance_review_bundle_id`** / **`governance_review_bundle_status`** after `wos.review_bundle.build`. Recommendation JSON is written **after** this enrichment so governance consumers see a single coherent artifact.

## Mutation flow

1. Create candidate variant from baseline with explicit lineage.
2. Attach concrete mutation plan (`mutation_plan`) to candidate.
3. Execute candidate in sandbox over controlled inputs.
4. Execute baseline transcript in parallel for direct comparison.

Candidate variants now include mutation intent rather than summary-only placeholders.

## Variant and experiment model

Implemented JSON-backed models:

- Variant:
  - `variant_id`
  - `baseline_id`
  - `candidate_summary`
  - `metadata`
  - `mutation_plan`
  - `lineage`
  - `review_status`
- Experiment:
  - `experiment_id`
  - `variant_id`
  - `baseline_id`
  - sandbox transcript
  - baseline transcript
  - execution metadata
- Recommendation package:
  - baseline and candidate references
  - evaluation payload
  - comparison deltas
  - evidence bundle references
  - recommendation summary
  - governance review state

## Sandbox execution boundary

Sandbox experiments run through controlled simulation (`execution_mode=sandbox`) and are explicitly marked non-authoritative (`publish_state=isolated_non_authoritative`).

No direct live publish mutation occurs in this path.

## Evaluation flow

Evaluation now computes:

- candidate metrics,
- baseline metrics,
- comparison deltas between candidate and baseline,
- notable failures.

Recommendation outcome is determined by guard/repetition thresholds plus negative comparison deltas on quality/flow.

## Evaluation dimensions implemented

- `guard_reject_rate`
- `trigger_coverage`
- `repetition_signal`
- `structure_flow_health`
- `transcript_quality_heuristic`
- `scene_marker_coverage`
- notable failure flags
- baseline metric mirror set
- comparison deltas:
  - `guard_reject_rate_delta`
  - `repetition_signal_delta`
  - `structure_flow_health_delta`
  - `quality_heuristic_delta`

## Evidence model

Recommendation packages carry explicit evidence:

- variant lineage and mutation plan,
- experiment and baseline identifiers,
- evaluation comparison payload,
- artifact references to persisted experiment/variant records.

## Recommendation and review package

Packages include:

- baseline reference,
- candidate reference,
- experiment reference,
- evaluation evidence and metrics,
- comparison evidence bundle,
- recommendation summary (`promote_for_human_review` or `revise_before_review`),
- governance review status (`pending_governance_review`).

## Governance integration surface

Backend APIs:

- `POST /api/v1/improvement/variants`
- `POST /api/v1/improvement/experiments/run`
- `GET /api/v1/improvement/recommendations`

These provide governance-side inspection and decision support without automatic publish.

## Deferred beyond M10

- richer statistical experiment comparison across large run sets,
- dedicated admin UI for recommendation triage and approvals,
- robust persistent database-backed experiment storage and migrations.
