# Retrieval subsystem closure (English)

## Status

**PASS** — Gates A–G satisfied in code, tests, and this document as of the closure commit. Schema tag: `retrieval_closure_v1`.

## What changed

- **`build_retrieval_trace`** ([`ai_stack/capabilities.py`](../ai_stack/capabilities.py)): Evidence tier caps for policy-hard pool reshape (including single- and two-hit strong), thin canonical anchor density (multi-hit), existing sparse/degraded/supporting-heavy caps; new compact fields `lane_anchor_counts`, `confidence_posture`, `governance_influence_compact`, `retrieval_posture_summary`; readiness label leads with `confidence=` and includes lane anchor counts (length-capped).
- **Context packs** ([`ai_stack/rag.py`](../ai_stack/rag.py)): Shorter `why_selected` lines; footer `retrieval_posture` includes `lane_mix` and `confidence`; `pack_trace_summary` echoes `retrieval_posture_summary`; summary line includes `domain` and `profile` for cross-workflow distinction.
- **Operational / backend surfaces**: [`ai_stack/operational_profile.py`](../ai_stack/operational_profile.py) passes `retrieval_confidence_posture` and `retrieval_posture_summary`; [`improvement_routes.py`](../backend/app/api/v1/improvement_routes.py) `evidence_bundle.retrieval_readiness` adds the same plus `lane_anchor_counts` and `governance_influence_compact`; [`ai_stack_evidence_service.py`](../backend/app/services/ai_stack_evidence_service.py) extends `retrieval_influence` and Writers-Room `review_readiness` with compact trace fields.
- **Evaluation harness** ([`ai_stack/tests/retrieval_eval_scenarios.py`](../ai_stack/tests/retrieval_eval_scenarios.py)): Extended corpus scenarios (hard-exclusion tier, internal-review Writers-Room case, pack trace assertions); deterministic **`RETRIEVAL_TRACE_EVAL_CASES`** for trace-only tier/confidence/rationale checks.

## Gates (summary)

| Gate | Scope | Enforced by |
|------|--------|-------------|
| A | Named deterministic scenarios (runtime / writers_room / improvement), canonical vs evaluative, dup/sparse/policy, trace + pack assertions | `RETRIEVAL_EVAL_SCENARIOS`, `RETRIEVAL_TRACE_EVAL_CASES`, `test_rag.py` |
| B | Compact, decision-useful trace (posture, lanes, policy/dedup, readiness) | `build_retrieval_trace`, `ContextPackAssembler` footer lines |
| C | Tier not hit-count-naive; confidence grounded | `_compute_evidence_tier_task4`, `_confidence_posture`, unit + trace eval tests |
| D | Governed pack output, domain/profile visible | `ContextPack` summary + sources + `pack_trace_summary` |
| E | Backend payloads align with ai_stack trace | `improvement_routes`, `ai_stack_evidence_service`, `operational_profile` |
| F | Same truth in code, tests, diagnostics | Shared `build_retrieval_trace`; schema `retrieval_closure_v1` |
| G | This document | — |

Task 1–3 retrieval semantics (ranking notes ordering, governance lanes, profile sections) are unchanged except additive trace/pack metadata.

## How evaluation, trace, and readiness work

1. **Corpus scenarios** build a temp tree, run `ContextRetriever` + `ContextPackAssembler`, then assert top path, lanes, visibility, pack sections, route, dedup, and trace fields including schema and `confidence_posture`.
2. **Trace-only cases** pass synthetic retrieval dicts into `build_retrieval_trace` to lock tier/rationale/confidence without scores in assertions.
3. **Readiness** is a bounded string: tier, lanes, route, policy/quality hints, anchor counts; **confidence_posture** is `low` / `medium` / `high` from tier + route + degradation + whether any `capped_*` appears in the tier rationale (not a probability).

## Intentionally deferred (out of scope)

- Replacement of hybrid/rerank core or external observability products.
- UI/dashboard work.
- Broader policy engine or embedding backend redesign beyond trace/tier closure.

## References

- Prior task notes: [`docs/rag_task4_readiness_and_trace.md`](rag_task4_readiness_and_trace.md) (schema updated to `retrieval_closure_v1`).
- [`docs/rag_task4_evaluation_harness.md`](rag_task4_evaluation_harness.md) — scenario pattern still applies; trace eval cases supplement it.
