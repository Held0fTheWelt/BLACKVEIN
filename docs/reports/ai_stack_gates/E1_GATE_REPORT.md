# E1 Gate Report — Harden Observability, Evidence, Governance, and Release Truthfulness

Date: 2026-04-04

## Scope completed

- Deepened **`build_session_evidence_bundle`** with **`execution_truth`** (committed narrative surface vs full diagnostic envelopes, last-turn graph mode, retrieval influence tier, tool/material capability influence).
- Replaced ambiguous **`degraded_signals`** placeholders with **`degraded_path_signals`** plus a **`degraded_signals`** copy listing only active degradation markers.
- Enriched **`repaired_layer_signals`**: runtime now includes **`execution_health`** and **`graph_path_summary`**; tools include **`material_influence`**; Writers-Room pulls retrieval tier, bundle ids, model adapter path, capability audit tail; Improvement uses compact **`evidence_influence`** (workflow stages, retrieval path count, transcript/governance flags) instead of dumping full nested evidence blobs.
- Refactored **`build_release_readiness_report`**: removed Writers-Room **`stack_components`** as a proxy for story-runtime observability; split areas for story bridge, runtime turn graph contract, Writers-Room artifacts, retrieval surface, LangGraph orchestration depth (always partial/seed), and improvement governance evidence; added **`subsystem_maturity`** notes.
- Added **`governance_truth`** to persisted Writers-Room review JSON (derived from existing workflow fields).
- Documented session-evidence semantics in **`docs/architecture/observability_and_governance_in_world_of_shadows.md`**.

## Files changed

- `backend/app/services/ai_stack_evidence_service.py`
- `backend/app/services/writers_room_service.py`
- `backend/tests/test_m11_ai_stack_observability.py`
- `backend/tests/test_writers_room_routes.py`
- `world-engine/tests/test_trace_middleware.py`
- `docs/architecture/observability_and_governance_in_world_of_shadows.md`
- `docs/reports/ai_stack_gates/E1_GATE_REPORT.md`
- `docs/reports/AI_STACK_REPAIR_A_TO_E_CLOSURE.md`

## What was deepened versus what already existed

| Already existed | Deepened in E1 |
|-----------------|----------------|
| Session evidence with `repaired_layer_signals` from `repro_metadata` only | Explicit **`execution_truth`**, graph **`execution_health`**, **`degraded_path_signals`**, retrieval **`evidence_tier`** from last turn |
| Release readiness with `runtime_observability` tied to Writers-Room | Layer-split areas; story runtime cross-layer **`partial`** in aggregate; WR LangGraph depth explicit **`partial`** |
| Writers-Room payloads with `retrieval_trace`, `capability_audit` | **`governance_truth`** summary block; session evidence aggregates tier + generation path + audit tail |
| Improvement packages with rich `evidence_bundle` in storage | Governance-facing **`evidence_influence`** summary in session evidence (no duplicate of full bundle) |

## Which repaired paths are now more observable

- **A (natural input / narrative commit)**: `execution_truth.committed_narrative_surface` vs diagnostic envelopes; trace continuity asserted in World-Engine tests for `committed_history_tail` vs full `diagnostics`.
- **B (LangChain / LangGraph)**: `last_turn_graph_mode`, `runtime.graph_path_summary`, `execution_health`, Writers-Room `model_adapter_invocation_mode` and `governance_truth.langgraph_orchestration_depth`.
- **C (RAG / tools)**: `retrieval_influence` tier/rationale; `tool_influence.material_influence`; improvement `evidence_influence.tool_influence_indicators`.
- **D (Writers-Room / Improvement)**: Richer `repaired_layer_signals` and persisted **`governance_truth`**; release-readiness areas per workflow without conflating layers.

## Evidence distinctions now explicit

- Committed runtime truth vs diagnostic-only orchestration envelopes (World-Engine warnings + `execution_truth` text + structure).
- Graph-driven health vs fallback vs degraded (`execution_health`, `fallback_path_taken`, `graph_path_summary`).
- Retrieval-backed vs weak evidence (`evidence_tier` / `evidence_strength` / `evidence_rationale` from `build_retrieval_trace`).
- Tool-influenced vs plain output (`material_capability_invocations`, `material_influence`).
- Improvement: retrieval paths, transcript tool, governance review bundle presence surfaced in **`evidence_influence`**.

## Governance / review surfaces more useful for decisions

- `GET /admin/ai-stack/session-evidence/<id>` exposes the above in one JSON document for moderator review.
- `GET /admin/ai-stack/release-readiness` separates contract-ready code (`runtime_turn_graph_contract`) from aggregate operational unknowns (`story_runtime_cross_layer` partial) and seed orchestration (`writers_room_langgraph_orchestration_depth` partial).

## What remains partial

- Aggregate release-readiness **cannot** prove a live bridged story session without caller context; **`story_runtime_cross_layer`** stays **`partial`** by design.
- Writers-Room LangGraph path remains a **seed stub**—not runtime turn-graph parity.
- Evidence persistence is still local JSON / in-process diagnostics; no signed immutable ledger.
- Improvement **`improvement_governance_evidence`** is **`ready`** only when stored packages include both comparison evidence and **`governance_review_bundle_id`** (full experiment path); packages from **`build_recommendation_package`** alone stay partial.

## Tests added or updated

- `backend/tests/test_m11_ai_stack_observability.py`: richer mocks for `execution_truth`, degraded path, release-readiness area keys; new **`test_session_evidence_surfaces_degraded_execution_health`**.
- `backend/tests/test_writers_room_routes.py`: asserts **`governance_truth`**.
- `world-engine/tests/test_trace_middleware.py`: trace id on **`committed_history_tail`** vs full diagnostic row (no `graph` on committed tail).

## Exact test commands run

```powershell
cd c:\Users\YvesT\PycharmProjects\WorldOfShadows\backend
python -m pytest tests/test_m11_ai_stack_observability.py tests/test_writers_room_routes.py::test_writers_room_review_runs_unified_stack_flow -v --tb=short
```

```powershell
cd c:\Users\YvesT\PycharmProjects\WorldOfShadows\backend
python -m pytest tests/test_improvement_routes.py tests/test_session_routes.py -k "diagnostics or capability_audit or evidence" -v --tb=short
```

```powershell
cd c:\Users\YvesT\PycharmProjects\WorldOfShadows\world-engine
python -m pytest tests/test_trace_middleware.py tests/test_story_runtime_api.py tests/test_story_runtime_rag_runtime.py -v --tb=short
```

```powershell
cd c:\Users\YvesT\PycharmProjects\WorldOfShadows
$env:PYTHONPATH="c:\Users\YvesT\PycharmProjects\WorldOfShadows\story-runtime-core\src;c:\Users\YvesT\PycharmProjects\WorldOfShadows"
python -m pytest wos_ai_stack/tests/test_capabilities.py wos_ai_stack/tests/test_langgraph_runtime.py -v --tb=short
```

## Verdict

**Pass**

## Reason for verdict

- Repaired paths are more traceable and explainable via **`execution_truth`** and enriched **`repaired_layer_signals`**.
- Evidence reflects influence (retrieval tier, material tools, improvement influence summary), not only step names.
- Governance APIs expose the new structure; release reporting no longer uses Writers-Room as a false proxy for story-runtime readiness and labels seed LangGraph depth honestly.
- Tests cover degraded graph health, trace on committed tail, and updated readiness areas.
- This report and readiness payloads explicitly document remaining partiality and non-final maturity.

## Remaining risk

- Operators may misread **`runtime_turn_graph_contract: ready`** as “production deployed”; it means **repository contract + tests**, not fleet-wide verification.
- Empty or stale `var/writers_room` / improvement stores keep multiple areas **`partial`**—by design, but requires discipline when interpreting **`overall_status`**.
