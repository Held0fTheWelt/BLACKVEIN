# G Gate Report — Performance and Cost Hardening

Date: 2026-04-04

## 1. Scope completed

- **Improvement experiment HTTP path:** Process-lifetime singleton for `build_runtime_retriever` + `create_default_capability_registry`, avoiding repeated corpus/index setup on every `POST /improvement/experiments/run`.
- **Writers-Room workflow:** Eliminated the second `ContextRetriever.retrieve` that previously served only the LangChain document preview; preview `Document`s are built from the primary `wos.context_pack.build` sources (with per-hit `snippet` on context-pack sources).
- **LangChain bridge:** Hoisted `ChatPromptTemplate` and shared `PydanticOutputParser` instances for runtime and writers-room adapter invocations to remove repeated template construction per call.
- **Operational visibility:** Added `operational_cost_hints` on LangGraph `graph_diagnostics` (World-Engine story turn path) and on the improvement experiment JSON response — coarse, explicitly **non-financial** signals (retrieval route, embedding model id, execution health, adapter mode, fallback flags, prompt length bucket).

## 2. Files changed

- `ai_stack/operational_profile.py` (new)
- `ai_stack/rag.py`
- `ai_stack/langgraph_runtime.py`
- `ai_stack/langchain_integration/bridges.py`
- `ai_stack/tests/test_langgraph_runtime.py`
- `ai_stack/tests/test_langchain_integration.py`
- `ai_stack/tests/test_rag.py`
- `backend/app/api/v1/improvement_routes.py`
- `backend/app/services/writers_room_service.py`
- `backend/tests/test_improvement_routes.py`
- `backend/tests/test_writers_room_routes.py`
- `docs/reports/ai_stack_gates/G_GATE_REPORT.md`

## 3. What was hardened versus what already existed

- **Already existed:** World-Engine `StoryRuntimeManager` built retriever and compiled LangGraph once per app lifecycle; Writers-Room `_get_workflow()` already cached the workflow object; RAG persistent corpus load on `build_runtime_retriever`; improvement route called `build_runtime_retriever` on every experiment POST (now cached).
- **Hardened:** Improvement RAG/capability stack reuse; Writers-Room single-retrieval preview; LangChain setup reuse; structured operational hints without claiming dollar costs or production SLAs.

## 4. Paths that became materially faster or less wasteful

- **Backend improvement:** Second and subsequent experiment runs in the same process skip `build_runtime_retriever` / registry construction (verified by test counter).
- **Writers-Room:** One `ContextRetriever.retrieve` per review package instead of two for the same conceptual step (verified by monkeypatch counter on `ContextRetriever.retrieve`).
- **LangChain:** Fewer repeated template/parser object constructions on each adapter invocation (verified by singleton identity test).

## 5. Costs or expensive modes now more visible

- **Runtime turn:** `graph_diagnostics.operational_cost_hints` exposes retrieval route, embedding model id (when present), execution health, adapter invocation mode, fallback path flags, and prompt length bucket (`small` / `medium` / `large` character bands).
- **Improvement:** Response field `operational_cost_hints` mirrors retrieval-oriented signals for reviewers (`disclaimer: coarse_operational_signals_not_financial_estimates`).
- **Writers-Room:** `proposal_package.retrieval_digest.langchain_preview_source` documents that the LangChain preview is derived from `primary_context_pack` (not a second retrieval).

## 6. Deliberately not optimized

- No change to ranking quality, chunk counts, or model routing policy.
- No distributed cache, no cross-process RAG invalidation (cache is process-lifetime; corpus on-disk updates may require process restart to refresh the in-memory retriever).
- No micro-optimization of individual sparse/hybrid scoring loops or embedding encode internals.
- `LangChainRetrieverBridge.get_writers_room_documents` remains for other callers/tests; the canonical Writers-Room HTTP path no longer uses it for preview.

## 7. What remains environment-sensitive or intentionally lightweight

- RAG remains local JSON / optional dense sidecar (`fastembed`); hybrid vs sparse is environment-dependent and already surfaced via `retrieval_route`.
- Operational hints are **not** latency SLAs and **not** monetary estimates.
- Prompt length buckets are coarse character thresholds only.

## 8. Tests added or updated

- `test_improvement_experiment_reuses_cached_rag_stack` — counts `build_runtime_retriever` across two experiment runs.
- Autouse fixture resets improvement RAG singleton between tests; D2 retrieval materiality test clears cache when swapping mocked registries.
- `test_writers_room_unified_review_calls_context_retriever_once` — exactly one `ContextRetriever.retrieve` per review.
- `test_context_pack_exposes_attribution_and_selection_notes` — asserts `snippet` on assembled sources.
- `test_langchain_prompt_templates_are_module_singletons` — stable template objects across invocations.
- LangGraph tests assert `operational_cost_hints` on healthy and fallback paths.
- Improvement sandbox test asserts `operational_cost_hints` on HTTP response.
- Writers-Room tests updated for primary-pack preview paths and `langchain_preview_source`.

## 9. Exact test commands run

From repository root `c:\Users\YvesT\PycharmProjects\WorldOfShadows` (Windows, PowerShell):

```text
python -m pytest ai_stack/tests/test_langgraph_runtime.py ai_stack/tests/test_langchain_integration.py ai_stack/tests/test_rag.py ai_stack/tests/test_capabilities.py -q --tb=short
```

Result: **46 passed**

```text
python -m pytest backend/tests/test_improvement_routes.py backend/tests/test_writers_room_routes.py -q --tb=short
```

Result: **30 passed**

```text
python -m pytest world-engine/tests/test_performance_contracts.py -m contract -q --tb=short
```

Result: **10 passed**

```text
python -m pytest world-engine/tests/test_story_runtime_rag_runtime.py -q --tb=short
```

Result: **8 passed**

## 10. Verdict

**Pass**

## 11. Reason for verdict

- At least one runtime-adjacent path improved (LangChain bridge setup reuse on every story turn invocation; operational hints on `graph_diagnostics` consumed by World-Engine story flow).
- At least one retrieval/workflow path improved (Improvement RAG singleton; Writers-Room single retrieval + context-pack snippets).
- Cost/expensive-path visibility strengthened with explicit non-financial disclaimer.
- Changes are test-backed and tied to real HTTP or graph paths.
- Report states remaining local/lightweight limitations without claiming production-grade performance maturity.

## 12. Remaining risk

- Process-lifetime improvement RAG cache can retain a stale retriever if on-disk corpus is rebuilt externally without restarting the backend process; operators should restart after intentional full re-ingest in long-lived dev servers.
- Shared `PydanticOutputParser` module singletons assume parser instances are safe for concurrent reads under Flask; if future mutable parser state is introduced, revisit thread isolation.
