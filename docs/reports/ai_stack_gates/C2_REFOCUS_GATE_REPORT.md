# C2 REFOCUS Gate Report — Deepen Workflow Dependence on Capability Tooling

**Date:** 2026-04-04  
**Verdict:** **PASS**

## Scope completed

- **Audit quality:** `CapabilityRegistry` audit entries now include `result_summary` for successful invocations (structured, payload-safe). Denied and error outcomes record `result_summary: null` for a consistent schema.
- **Summaries by tool:** `wos.context_pack.build` audits expose `kind`, `hit_count`, `status`, `domain`, `profile`, optional `index_version`, and a short `corpus_fingerprint_prefix`. `wos.review_bundle.build` audits expose `evidence_source_count` and bundle identifiers. `wos.transcript.read` would expose length metadata when it succeeds (still not wired into workflows).
- **Workflow coupling:** `build_retrieval_trace()` normalizes capability retrieval output into `evidence_strength` (`strong` vs `none` from hit count) plus trace fields. **Improvement** (`improvement_routes`) and **writers-room** (`writers_room_service`) inject `[evidence:…]` into `wos.review_bundle.build` summaries and return `retrieval_trace` on their primary JSON payloads so clients and governance see retrieval-backed vs empty evidence explicitly.

## Files changed

- `wos_ai_stack/capabilities.py` — `_summarize_invocation_result`, `build_retrieval_trace`, audit `result_summary`
- `wos_ai_stack/__init__.py` — export `build_retrieval_trace`
- `backend/app/api/v1/improvement_routes.py` — `retrieval_trace`, evidence-tagged review summary
- `backend/app/services/writers_room_service.py` — same pattern on writers-room report
- `wos_ai_stack/tests/test_capabilities.py`
- `backend/tests/test_improvement_routes.py`
- `backend/tests/test_writers_room_routes.py`

## Workflows that now depend more strongly on tools

| Workflow | Change |
|----------|--------|
| Improvement experiment run | Response includes `retrieval_trace`; `review_bundle.summary` is prefixed from live `wos.context_pack.build` hit counts; route test proves `none` vs `strong` behavior under registry control. |
| Writers-room unified review | Report JSON includes `retrieval_trace`; review bundle summary carries the same evidence tag. |

## Tools central vs aspirational

| Tool | Role |
|------|------|
| `wos.context_pack.build` | **Central** — feeds trace, evidence strength, and review-bundle summary prefix in improvement and writers-room. |
| `wos.review_bundle.build` | **Central** — receives evidence-derived summary text and evidence paths from retrieval. |
| `wos.transcript.read` | **Aspirational** — registered and tested for invocability; not invoked by these workflows (no change to that honest status). |

## Tests added or updated

- `test_build_retrieval_trace_evidence_strength_follows_hit_count`
- `test_runtime_context_pack_capability_returns_retrieval_payload` — asserts `result_summary` on audit
- `test_review_bundle_audit_includes_evidence_source_count`
- Denied/validation audit tests assert `result_summary is None`
- `test_sandbox_execution_evaluation_and_recommendation_package` — `retrieval_trace`, audit `result_summary`, review summary prefix vs strength
- **New:** `test_improvement_experiment_reflects_empty_retrieval_in_trace_and_review_summary` (monkeypatched registry)
- Writers-room flow test asserts `retrieval_trace` presence

## Exact test commands run

```text
python -m pytest wos_ai_stack/tests/test_capabilities.py -v --tb=short
# 7 passed

cd backend && python -m pytest tests/test_improvement_routes.py tests/test_writers_room_routes.py -v --tb=short
# 12 passed

cd world-engine && python -m pytest tests/test_story_runtime_rag_runtime.py -v --tb=short
# 8 passed
```

## Reason for verdict

Tool results **materially change** HTTP/report payloads (`retrieval_trace`, review-bundle summary prefix), and audits now carry **operational hints** for real debugging without dumping full payloads. Permission/denial and validation paths remain explicit with `result_summary` cleared. A route-level test proves **empty vs non-empty retrieval** changes the response contract.

## Remaining risk

- `evidence_strength` is intentionally coarse (`strong` / `none` from hit count only); degraded retrieval statuses are visible via `retrieval_trace["status"]` but not yet mapped to a third strength tier.
- `wos.transcript.read` remains unused in these workflows until a stable transcript artifact contract is threaded through improvement.
