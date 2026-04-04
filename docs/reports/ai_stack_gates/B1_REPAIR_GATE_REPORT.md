# B1 Repair Gate Report — LangChain Integration Layer

Date: 2026-04-04

## 1. Scope completed

- Introduced a concrete LangChain integration package in `wos_ai_stack/langchain_integration/`.
- Wired runtime-adjacent model invocation to LangChain prompt/parser flow inside the active runtime turn graph.
- Wired writers-room path to LangChain retriever and tool bridges.
- Added dependency declarations for LangChain in backend and world-engine runtime requirement sets.
- Added integration tests covering parser, retriever bridge, tool bridge, and runtime graph usage.

## 2. Files changed

- `wos_ai_stack/langchain_integration/bridges.py`
- `wos_ai_stack/langchain_integration/__init__.py`
- `wos_ai_stack/langgraph_runtime.py`
- `wos_ai_stack/__init__.py`
- `wos_ai_stack/tests/test_langchain_integration.py`
- `wos_ai_stack/tests/test_langgraph_runtime.py`
- `backend/app/services/writers_room_service.py`
- `backend/tests/test_writers_room_routes.py`
- `backend/requirements.txt`
- `world-engine/requirements.txt`
- `docs/architecture/langchain_integration_in_world_of_shadows.md`
- `docs/reports/ai_stack_gates/B1_REPAIR_GATE_REPORT.md`

## 3. What is truly wired

- Runtime turn graph now executes model invocation through `invoke_runtime_adapter_with_langchain`, including LangChain prompt rendering and structured output parse attempts.
- Runtime generation metadata now records LangChain usage (`langchain_prompt_used`, parser error state, parsed structured payload).
- Writers-room review now uses:
  - LangChain retriever bridge for document-level retrieval preview
  - LangChain `StructuredTool` bridge for `wos.review_bundle.build` capability invocation
- API-visible writers-room response now reports LangChain integration state in `stack_components.langchain_integration`.

## 4. What remains incomplete

- LangChain is not yet used across every historical AI path; the rollout is focused to canonical runtime-adjacent and writers-room flows.
- Structured output is currently parsed opportunistically from adapter content; stricter provider-native JSON mode can be expanded in later milestones.

## 5. Tests added/updated

- Added: `wos_ai_stack/tests/test_langchain_integration.py`
  - parser execution
  - retriever bridge output
  - tool bridge invocation
- Updated: `wos_ai_stack/tests/test_langgraph_runtime.py`
  - verifies runtime graph generation metadata confirms LangChain prompt usage
- Updated: `backend/tests/test_writers_room_routes.py`
  - verifies writers-room response exposes active LangChain integration markers

## 6. Exact test commands run

```powershell
cd ..
$env:PYTHONPATH='.'
python -m pytest wos_ai_stack/tests/test_langchain_integration.py wos_ai_stack/tests/test_langgraph_runtime.py
```

```powershell
cd backend
python -m pytest tests/test_writers_room_routes.py
```

```powershell
cd ..\world-engine
python -m pytest tests/test_story_runtime_api.py tests/test_story_runtime_rag_runtime.py
```

## 7. Pass / Partial / Fail

Pass

## 8. Reason for the verdict

- LangChain is declared as a real dependency in runtime environment requirement files.
- The new LangChain layer is not dead code: it is exercised by active runtime and writers-room paths.
- Tests verify prompt/parser execution, retriever/tool bridges, and runtime graph integration metadata.
- The integration consolidates previously ad-hoc glue while staying limited to high-value active paths.

## 9. Risks introduced or remaining

- Parser strictness can produce non-fatal parse errors when providers return non-JSON text; this is surfaced in metadata and does not crash turn execution.
- Writers-room tool bridge currently centralizes capability invocation through one structured tool; future actor-specific attribution hardening may be desirable.
