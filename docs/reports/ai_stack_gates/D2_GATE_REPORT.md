# D2 Gate Report — Improvement Mutation / Evaluation / Recommendation Loop

Date: 2026-04-04

## Scope completed

- Added explicit **`workflow_stages`** to **`POST /api/v1/improvement/experiments/run`** HTTP JSON and to the persisted **`recommendation_package`** (same ordered list).
- Moved persistence of recommendation packages to **after** retrieval, transcript-tool evidence, review-bundle invocation, and **`evidence_bundle`** enrichment (previously the package was written too early).
- Deepened **`evidence_bundle`** with:
  - **`retrieval_source_paths`** — paths passed through to `wos.review_bundle.build`
  - **`transcript_evidence`** — `run_id`, `turn_count`, `repetition_turn_count`, `content_length`
  - **`metrics_snapshot`**, **`baseline_metrics_snapshot`**, **`comparison_snapshot`** — copies of evaluation fields for review without chasing nested-only structure
  - **`governance_review_bundle_id`**, **`governance_review_bundle_status`** — from `wos.review_bundle.build` output
- Documented the above in **`docs/architecture/improvement_loop_in_world_of_shadows.md`**.

## Files changed

- `backend/app/api/v1/improvement_routes.py`
- `backend/tests/test_improvement_routes.py`
- `docs/architecture/improvement_loop_in_world_of_shadows.md`
- `docs/reports/ai_stack_gates/D2_GATE_REPORT.md`

## What was created versus what already existed

- **Already existed**: variant creation, sandbox + baseline transcript, `evaluate_experiment` metrics and comparison, `build_recommendation_package`, `wos.context_pack.build`, `wos.transcript.read`, `wos.review_bundle.build`, transcript-derived suffix on `recommendation_summary`, capability failure surfacing (502).
- **Created / deepened**: **`workflow_stages`** contract; richer **`evidence_bundle`** explicitly tying retrieval paths, transcript tool meta, evaluation snapshots, and governance bundle ids; correct write ordering for stored recommendations; **route test** proving different mocked retrieval paths change **`review_bundle.evidence_sources`** and stored **`evidence_bundle.retrieval_source_paths`**.

## Workflow stages now explicit

| Stage id | Meaning |
|----------|---------|
| `variant_resolution` | Incoming `variant_id` |
| `baseline_context` | `baseline_id` from experiment |
| `sandbox_execution` | Sandbox experiment record |
| `evaluation_and_recommendation_draft` | Package from `build_recommendation_package` |
| `retrieval_improvement_context` | `wos.context_pack.build` |
| `transcript_tool_evidence` | `wos.transcript.read` |
| `governance_review_bundle` | `wos.review_bundle.build` |

## How evidence is captured and attached

- **Transcript file** written under `world-engine/app/var/runs/`, read back via **`wos.transcript.read`**; meta drives **`recommendation_summary`** suffix and is copied into **`evidence_bundle.transcript_evidence`**.
- **Retrieval** sources are copied to **`evidence_bundle.retrieval_source_paths`** and fed to the review bundle payload.
- **Evaluation** metrics / baseline / comparison are duplicated into the evidence bundle for traceable, flat review.
- **Governance bundle** ids/status are appended after `wos.review_bundle.build` returns.

## How baseline vs candidate comparison works

- Unchanged: **`run_sandbox_experiment`** still records **`transcript`** and **`baseline_transcript`**; **`evaluate_experiment`** computes candidate and baseline metrics and **`comparison`** deltas; **`recommendation_package.evaluation`** holds the full structure; snapshots in **`evidence_bundle`** mirror that data for the package consumer.

## Where retrieval / tool usage is truly involved

- **Retrieval**: `wos.context_pack.build` supplies sources that flow into **`review_bundle.evidence_sources`**, **`retrieval_trace`**, and **`evidence_bundle.retrieval_source_paths`**. Test **`test_improvement_retrieval_paths_materially_affect_review_bundle_and_stored_evidence`** swaps mocked source paths between two runs and asserts different evidence.
- **Tools**: **`wos.transcript.read`** remains required for the transcript suffix path; **`wos.review_bundle.build`** supplies governance bundle metadata now mirrored in **`evidence_bundle`**. Existing tests still prove transcript bypass and capability failure behavior.

## What remains intentionally lightweight

- Sandbox execution is still **local simulation** (semantic input interpretation + heuristics), not an external cluster sandbox.
- Mutation plans are still **human/policy-oriented** descriptions, not autonomous code mutation search.

## Tests added / updated

- Extended **`test_sandbox_execution_evaluation_and_recommendation_package`** for **`evidence_bundle`** enrichment, **`workflow_stages`**, and alignment of top-level vs package **`workflow_stages`**.
- Added **`test_improvement_retrieval_paths_materially_affect_review_bundle_and_stored_evidence`**.

## Exact test commands run

```powershell
cd backend
python -m pytest tests/test_improvement_routes.py -q --tb=line
```

Result: **10 passed**, exit code **0**. `backend/pytest.ini` enables **`--cov=app`** by default, so the run includes coverage (runtime ~172s on this Windows environment).

## Verdict

**Pass**

## Reason for verdict

- The improvement path is **workflow-shaped** with explicit **stages** and a **single** persisted recommendation artifact that includes **enriched evidence**.
- **Baseline vs candidate** comparison remains **explicit** in evaluation and is **copied** into the evidence bundle.
- **Retrieval** materially affects **review_bundle** and **stored evidence** (test-proven).
- **Tool** usage (**transcript read**, **review bundle**) remains **material** to outputs and is covered by existing and new tests.

## Remaining risk

- Full suite runtime is **slow** on Windows in this repo (heavy imports/coverage); CI should set timeouts accordingly.
- Mocked-registry tests validate **wiring**; production regressions in **`create_default_capability_registry`** still depend on integration-style tests hitting the real registry.
