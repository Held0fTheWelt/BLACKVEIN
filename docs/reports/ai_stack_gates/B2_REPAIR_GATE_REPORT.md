# B2 Repair Gate Report — LangGraph Execution Hardening and Runtime Truthfulness

Date: 2026-04-04

Verification run: 2026-04-04 (repair block re-audit)

## 1. Scope completed

- Added explicit **`execution_health`** on runtime turn graph diagnostics to distinguish healthy primary-model completion from **model fallback**, **degraded generation** (primary failed and no recovery), and **graph_error** (recorded graph errors).
- Kept existing signals: `fallback_path_taken`, `nodes_executed`, `errors`, and `ensure_langgraph_available()` for missing-dependency failures.
- Extended tests to assert `execution_health` on both the direct graph runner and the World-Engine-integrated fallback scenario.

## 2. Files changed

- `wos_ai_stack/langgraph_runtime.py`
- `wos_ai_stack/tests/test_langgraph_runtime.py`
- `world-engine/tests/test_story_runtime_rag_runtime.py`
- `docs/reports/ai_stack_gates/B2_REPAIR_GATE_REPORT.md`

## 3. Where LangGraph truly drives execution

- **Runtime turn graph** (`RuntimeTurnGraphExecutor`): full node chain `interpret_input` → `retrieve_context` → `route_model` → `invoke_model` → (`fallback_model` if needed) → `package_output`.
- **Seed graphs** (`build_seed_writers_room_graph`, `build_seed_improvement_graph`): single-node stubs documented in tests as non-production workflow orchestration.

## 4. Where fallback / degraded behavior exists

- **Model fallback:** when primary adapter fails or returns `success=False`, graph routes to `fallback_model` (mock adapter when registered). Diagnostics report `fallback_path_taken: true` and `execution_health: "model_fallback"`.
- **Degraded generation:** if primary fails and fallback does not recover (no successful generation), `execution_health` can be `degraded_generation` when `graph_errors` is empty but `success` is false — rare when mock fallback is present.
- **Graph errors:** e.g. missing fallback adapter populates `graph_errors` and sets `execution_health` to `graph_error`.
- **Dependency missing:** `ensure_langgraph_available()` raises a clear `RuntimeError` before graph construction (test-covered via import-error monkeypatch).

## 5. Tests added/updated

- Updated `wos_ai_stack/tests/test_langgraph_runtime.py::test_runtime_turn_graph_executes_nodes_and_emits_trace` — expects `execution_health == "healthy"`.
- Updated `world-engine/tests/test_story_runtime_rag_runtime.py::test_story_runtime_graph_uses_fallback_branch_on_model_failure` — expects `execution_health == "model_fallback"`.
- Re-ran `test_langgraph_missing_dependency_raises_honest_runtime_error` and LangChain integration tests for regression safety.

## 6. Exact test commands run

```powershell
cd ..
$env:PYTHONPATH='.'
python -m pytest wos_ai_stack/tests/test_langgraph_runtime.py wos_ai_stack/tests/test_langchain_integration.py -v --tb=short
```

```powershell
cd world-engine
python -m pytest tests/test_story_runtime_rag_runtime.py -k "fallback" -v --tb=short
```

## 7. Pass / Partial / Fail

**Pass**

## 8. Reason for verdict

- LangGraph imports and executes in the verification environment; missing dependency path fails with an explicit message.
- Real graph execution is test-proven; fallback is explicitly labeled in diagnostics, not silent.
- Runtime surfaces better distinguish healthy vs fallback execution via `execution_health`.

## 9. Dependency / environment notes

- Requires `langgraph` (and LangChain core packages) installed per `backend/requirements.txt` and `world-engine/requirements.txt`.
- Seed graphs for writers-room and improvement remain **minimal stubs**; consumers must not treat them as full product workflows (see stub tests in `test_langgraph_runtime.py`).
