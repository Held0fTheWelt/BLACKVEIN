# Task 4 — Retrieval trace, evidence tier, and readiness

## Trace schema

`build_retrieval_trace` (in `ai_stack/capabilities.py`) sets `retrieval_trace_schema_version` to **`retrieval_closure_v1`** (retrieval subsystem closure; supersedes the earlier `task4_compact_trace_v1` tag). Downstream code can rely on this tag when parsing.

## Evidence tier (honest, compact heuristics)

The four levels **`none` / `weak` / `moderate` / `strong`** remain operator-facing. Task 4 changes **multi-hit** behavior only:

- **Before:** Three or more hits could yield `strong` from hit count alone.
- **After:** Multi-hit defaults to **`moderate`** (`multi_hit_baseline`). Promotion to **`strong`** requires explicit signals, for example:
  - Hybrid route with top score ≥ 7.0 and at least one packed source in the **`canonical`** lane, or
  - Hybrid route with top score ≥ 8.5 (very high top score), or
  - Hybrid route with top score ≥ 7.0 and evaluative lane mix (`evaluative_present` / `evaluative_mixed`).

**Caps** (still compact, documented):

- **`sparse_fallback`** on multi-hit packs: tier is not promoted to `strong` via those hybrid rules; rationale includes `sparse_route_multi_hit_context`.
- **`degradation_mode`** in `{ sparse_fallback_due_to_no_backend, sparse_fallback_due_to_encode_failure, sparse_fallback_due_to_invalid_or_missing_dense_index, degraded_due_to_partial_persistence_problem }`: if tier would be `strong`, it is capped to `moderate` (`capped_degraded_path`).
- **`supporting_heavy`** lane mix with no canonical or evaluative anchors: `strong` is capped to `moderate` (`capped_supporting_heavy_no_canonical_or_evaluative`).

Single-hit and two-hit rules are unchanged from the pre–Task 4 behavior.

## Additional trace fields (not scores)

| Field | Meaning |
|-------|---------|
| `evidence_lane_mix` | `canonical_heavy`, `mixed`, `supporting_heavy`, `evaluative_present`, `evaluative_mixed`, or `unknown`. |
| `retrieval_quality_hint` | Semicolon-separated tags: e.g. `sparse_signal_path`, `dedup_shaped_selection`, `hard_policy_pool_shaped`, `degradation_marker_present`. |
| `policy_outcome_hint` | `hard_pool_exclusions_applied` or `no_hard_pool_exclusions_in_notes` (from ranking note scan). |
| `dedup_shaped_selection` | Boolean: `dup_suppressed` appeared in ranking notes. |
| `hard_policy_exclusion_count` | Parsed from `policy_hard_excluded_pool_count=` when present. |
| `readiness_label` | One-line English summary for humans (truncated if very long). |

## Context pack polish

`ContextPackAssembler` (`ai_stack/rag.py`) uses a clearer header line (“Evidence pack”), adds a single **`retrieval_posture`** footer (status, route, degradation, hit count), and tightens the summary string. Task 1–3 ranking note ordering in `ranking_notes` is unchanged.

## Backend surfaces

- **Improvement experiment** responses: `retrieval_trace` includes the new fields; `evidence_bundle.retrieval_readiness` carries a compact subset for stored packages.
- **`build_operational_cost_hints_from_retrieval`**: adds `retrieval_evidence_tier`, `retrieval_readiness_label`, `evidence_lane_mix`, `retrieval_quality_hint`, `retrieval_trace_schema_version`.
- **Release readiness** (`GET /admin/ai-stack/release-readiness`): new area `retrieval_subsystem_compact_traces`, top-level `retrieval_readiness_summary`, and `subsystem_maturity` entry `retrieval_rag_task4`.

## Task 1–3 semantics

Lifecycle fields, hybrid/rerank/dedup core, and source governance gates are **unchanged**; Task 4 only adds summarization and tests above the existing pipeline.

## Deferred after Task 4

- Distributed vector databases and cross-host indices
- External observability warehouses or full analytics dashboards
- Long-term automated retrieval drift monitoring in production
