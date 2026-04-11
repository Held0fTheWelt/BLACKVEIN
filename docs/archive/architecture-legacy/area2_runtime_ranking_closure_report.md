# Area 2 — Runtime canonical ranking stage closure report

This report records **Area 2 Closure Task 1B — Canonical Ranking Stage Closure**: `ranking` is a **first-class, unambiguous** canonical Runtime stage in the staged pipeline (`backend/app/runtime/runtime_ai_stages.py`), aligned across execution, evidence, operator truth, inventory/coverage, and documentation.

**Explicit unchanged semantics:** Task 2A **`route_model` policy precedence and routing semantics**, the **`StoryAIAdapter` contract**, **guard legality**, **commit semantics**, **reject semantics**, and **authoritative Runtime mutation rules** in `execute_turn` were **not** changed. Additions are **observability and documentation only**, mirroring existing `runtime_orchestration_summary` facts into compact operator surfaces.

**Explicit non-canonical exceptions (outside G-CANON-RANK scope):**

- **Supervisor `agent_orchestration`**: staged Runtime is **preempted**; `runtime_orchestration_summary` records `staged_pipeline_preempted: agent_orchestration`. No ranking stage runs; compact ranking summaries are **absent** (`runtime_ranking_summary: null` in `area2_operator_truth` when no ranking keys exist on the summary).
- **Legacy single-pass Runtime**: `runtime_staged_orchestration: false` uses one `route_model` + one generate path. Ranking stage does not apply.
- These paths are **documented** here so they do **not** dilute canonical-ranking requirements for the **default staged Runtime** path.

---

## Binding canonical ranking interpretation

| Topic | Definition |
|-------|------------|
| **What ranking is responsible for** | After **signal / consistency**, **narrows, prioritizes, or ranks** bounded candidate interpretations (`RankingStageOutput`: hypotheses, confidence, ambiguity residual) and **refines whether LLM synthesis** should run, via deterministic merge in `compute_synthesis_gate_after_ranking`. |
| **What ranking is not responsible for** | It does **not** emit canonical story JSON (`scene_interpretation`, proposed deltas, etc.); that is **synthesis** (or deterministic SLM-only packaging). It does **not** replace signal’s repetition/consistency or coarse **`needs_llm_synthesis`** role. |
| **vs `signal_consistency`** | Signal is the **coarse interpretation / consistency / base synthesis gate** (`SignalStageOutput`, `needs_llm_synthesis`). Ranking **refines** the branch when the base gate still allows or requests synthesis; it does not re-validate signal fields. |
| **vs `synthesis`** | Synthesis is **generation** (`WorkflowPhase.generation`, narrative task kinds, e.g. `narrative_formulation`). Ranking stays in **interpretation** (`WorkflowPhase.interpretation`, `TaskKind.ranking`) with **only** `RankingStageOutput`. |
| **Contribution to staged Runtime truth** | Produces **`ranking_effect`**, **`synthesis_gate_reason`** refinements (e.g. `ranking_skip_synthesis`, degraded ranking reasons), **`final_path`** labels (`ranked_then_llm`, `ranked_slm_only`, etc.), and bounded trace rows that downstream packaging may reference when ranked-skip applies. |
| **Visibility when skipped or degraded** | **SLM-only:** always a **`ranking`** trace row with intended `build_ranking_routing_request` payload, `decision: null`, `bounded_model_call: false`, `skip_reason: ranking_not_required_signal_allows_slm_only`. **No-eligible adapter:** trace row with `skip_reason: no_eligible_adapter_for_ranking_stage`. **Parse failure after bounded call:** trace records parse failure; gate forces synthesis with `degraded_ranking_parse_forcing_synthesis` per policy. |
| **Traces, summaries, rollups, audit, compact truth** | **Traces:** `runtime_stage_traces` include `stage_id: ranking`. **Summary:** `runtime_orchestration_summary` includes `ranking_effect`, `ranking_bounded_model_call`, `ranking_suppressed_for_slm_only`, `ranking_no_eligible_adapter`. **Rollup:** `model_routing_trace.ranking_context` is always present (dict) on staged outcomes. **Audit:** `operator_audit.audit_timeline` includes `stage_key: ranking` when traced. **Compact:** `operator_audit.audit_summary` and `area2_operator_truth.legibility.runtime_ranking_summary` mirror the four orchestration ranking keys when canonical staged summary is present. |
| **Second-class / non-canonical treatment** | Examples: ranking **missing** from `runtime_stage_traces` on a default staged path; **`ranking_effect`** or **`ranking_context`** missing while synthesis gate claims ranking-driven outcome; **compact** operator surfaces showing ranking **only** indirectly via synthesis skip with **no** mirrored ranking fields; **inventory** or **healthy bootstrap** proofs that omit **`TaskKind.ranking`** routability while `RUNTIME_STAGED_REQUIRED` includes it; documentation describing a pipeline **without** ranking while code requires it for staged Runtime. |

---

## G-CANON-RANK gate outcomes (PASS/FAIL)

| Gate | Pass condition | Failure meaning | Result |
|------|----------------|-----------------|--------|
| **G-CANON-RANK-01** | `RuntimeStageId.ranking` exists; staged execution orders signal → ranking → synthesis when synthesis runs | Ranking not canonical in identity or pipeline | **PASS** (`test_runtime_ranking_stage_id_is_canonical`, `test_runtime_ranking_follows_signal_before_synthesis_in_stages`) |
| **G-CANON-RANK-02** | Distinct contracts and routes: signal vs `RankingStageOutput` vs synthesis `RoutingRequest` | Semantic collapse or wrong phase/task_kind | **PASS** (`test_runtime_ranking_signal_and_synthesis_routing_contracts_distinct`) |
| **G-CANON-RANK-03** | Ranking in traces, summary, rollup `ranking_context`, audit timeline | Ranking only in deep traces | **PASS** (`test_runtime_ranking_surfaces_in_traces_summary_rollup_and_audit`) |
| **G-CANON-RANK-04** | `audit_summary` and `legibility.runtime_ranking_summary` both mirror orchestration ranking keys | Operator must infer ranking from synthesis alone | **PASS** (`test_runtime_ranking_compact_operator_truth_matches_orchestration_summary` + cross-surface / operational-bootstrap tests) |
| **G-CANON-RANK-05** | SLM-only, ranked-skip, ranked-then-LLM, degraded parse paths retain full canonical ranking surfaces | Important path treats ranking as implicit | **PASS** (`test_runtime_ranking_surfaces_preserved_across_path_variants`) |
| **G-CANON-RANK-06** | `RUNTIME_STAGED_REQUIRED` includes ranking; closure docs reference `build_ranking_routing_request`; healthy bootstrap routes ranking tuple | Inventory or startup truth omits ranking | **PASS** (`test_runtime_ranking_required_in_staged_inventory_and_closure_doc` + `test_bootstrap_registry_populates_adapter_specs_for_staged_tuples`) |
| **G-CANON-RANK-07** | Architecture docs + this report reference Task 1B / G-CANON-RANK and binding interpretation | Documentation drift | **PASS** (`test_runtime_ranking_documentation_lists_canonical_gate_ids`) |
| **G-CANON-RANK-08** | Ranked-skip and ranked-then-LLM complete with `success` and `guard_outcome` | Authority regression on ranking paths | **PASS** (`test_runtime_ranking_paths_complete_with_guard_outcomes`) |

---

## Semantic boundary summary

- **Signal:** coarse gate and consistency narrative; `TaskKind.repetition_consistency_check`, `runtime_stage: signal_consistency`.
- **Ranking:** narrowing / prioritization; `TaskKind.ranking`, `RankingStageOutput` only (no story JSON).
- **Synthesis:** final story-oriented structured generation path; `WorkflowPhase.generation`, default `narrative_formulation`.

---

## Canonical visibility summary

- **Enum:** `RuntimeStageId.ranking` → `"ranking"`.
- **Parser / model:** `parse_ranking_payload`, `RankingStageOutput` in `runtime_ai_stages.py`.
- **Rollup:** `build_legacy_model_routing_rollup` always attaches `ranking_context` (additive dict).
- **Orchestration summary:** `ranking_effect`, `ranking_bounded_model_call`, `ranking_suppressed_for_slm_only`, `ranking_no_eligible_adapter`.

---

## Operator equality summary

- **`operator_audit.audit_summary`:** includes the four keys **when** present on `runtime_orchestration_summary` (canonical staged path).
- **`area2_operator_truth.legibility.runtime_ranking_summary`:** dict with the same four keys **when** orchestration summary carries ranking truth; otherwise `null` (non-runtime surfaces or non-canonical preempted/legacy paths).
- Constants: `RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS` in `operator_audit.py`.

---

## Inventory / startup truth summary

- **Tuple:** `RUNTIME_STAGED_REQUIRED` includes `(WorkflowPhase.interpretation, TaskKind.ranking, requires_structured_output=True)`.
- **Healthy bootstrap:** `test_bootstrap_registry_populates_adapter_specs_for_staged_tuples` exercises `route_model(build_ranking_routing_request(...))` alongside preflight, signal, and synthesis.

---

## Tests run and results

From repository `backend/` as current working directory (last run for this closure):

```text
python -m pytest tests/runtime/test_runtime_ranking_closure_gates.py tests/runtime/test_runtime_staged_orchestration.py tests/runtime/test_runtime_task4_hardening.py tests/runtime/test_area2_convergence_gates.py tests/runtime/test_area2_final_closure_gates.py tests/runtime/test_cross_surface_operator_audit_contract.py tests/test_bootstrap_staged_runtime_integration.py tests/runtime/test_model_inventory_bootstrap.py -q --tb=short --no-cov
```

Last verified: **62 passed**, **0 failed** (`--no-cov`, Windows/Python 3.13.12).

---

## Changed files (this closure)

- `backend/app/runtime/operator_audit.py` — compact ranking keys on `audit_summary`; `RUNTIME_RANKING_ORCHESTRATION_SUMMARY_KEYS`.
- `backend/app/runtime/area2_operator_truth.py` — `runtime_orchestration_summary` parameter; `legibility.runtime_ranking_summary`.
- `backend/app/runtime/ai_turn_executor.py` — pass orchestration summary into `enrich_operator_audit_with_area2_truth`.
- `backend/tests/runtime/test_runtime_ranking_closure_gates.py` — G-CANON-RANK-01..08 tests.
- `backend/tests/runtime/test_area2_convergence_gates.py` — `runtime_ranking_summary` legibility key; G-CONV-02 ranking routability; staged compact ranking assertions.
- `backend/tests/runtime/test_cross_surface_operator_audit_contract.py` — runtime compact ranking assertions.
- `docs/architecture/area2_runtime_ranking_closure_report.md` (this file)
- `docs/architecture/llm_slm_role_stratification.md`
- `docs/architecture/ai_story_contract.md`

---

## Residual risks

- **Registry coverage:** Adapters must keep `supported_task_kinds` including **`ranking`** where interpretation-phase ranking should execute; otherwise honest `no_eligible_adapter_for_ranking_stage` applies.
- **Rollup consumers:** `ranking_context` and `slm_only_after_ranking_skip` remain additive; unknown keys should be ignored by legacy readers.

---

## Cross-reference

- Enforcement: `backend/tests/runtime/test_runtime_ranking_closure_gates.py` (G-CANON-RANK-01 .. G-CANON-RANK-08).
- **Routing policy (`route_model`) and authoritative Runtime semantics remain unchanged** aside from **invoking** additional stage-shaped `route_model` calls when the base synthesis gate is true, as documented in Task 1; Task 1B adds **mirrored compact fields** only.
