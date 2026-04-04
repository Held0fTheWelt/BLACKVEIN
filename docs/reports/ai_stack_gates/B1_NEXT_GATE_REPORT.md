# B1-next Gate Report — Deepen LangChain integration layer

Date: 2026-04-04

## 1. Scope completed

- Added **writers-room structured invocation** (`invoke_writers_room_adapter_with_langchain`, `WritersRoomStructuredOutput`, `WritersRoomInvocationResult`) alongside the existing runtime-turn bridge.
- Wired **`run_writers_room_review`** primary model path through LangChain (prompt + Pydantic parse); merged structured `recommendations` into the review payload when parse succeeds.
- **Explicit raw fallback** when primary fails and mock recovery runs: `adapter_invocation_mode: raw_adapter_fallback`, `metadata.langchain_prompt_used: false`, and `bypass_note` explaining non-JSON mock output (bounded, not hidden).
- **Retriever coherence:** `LangChainRetrieverBridge.get_writers_room_documents` uses `RetrievalDomain.WRITERS_ROOM` / `writers_review` for preview documents, aligned with `wos.context_pack.build` writers-room payloads (runtime turn graph **unchanged**: still native `RetrievalRequest` + assembler in `retrieve_context`).
- **Honest stack metadata:** `stack_components.langchain_integration` lists `runtime_turn_bridge`, `writers_room_generation_bridge`, `writers_room_document_preview`, retriever/tool bridges (renamed key `runtime_bridge` → `runtime_turn_bridge` for accuracy).

## 2. Files changed

- `wos_ai_stack/langchain_integration/bridges.py`
- `wos_ai_stack/langchain_integration/__init__.py`
- `wos_ai_stack/__init__.py`
- `backend/app/services/writers_room_service.py`
- `wos_ai_stack/tests/test_langchain_integration.py`
- `backend/tests/test_writers_room_routes.py`
- `docs/architecture/langchain_integration_in_world_of_shadows.md`
- `docs/reports/ai_stack_gates/B1_NEXT_GATE_REPORT.md`

## 3. What was deepened versus what already existed

- **Already existed:** `invoke_runtime_adapter_with_langchain`, retriever bridge (runtime domain only), capability tool bridge, graph `_invoke_model` using the runtime bridge.
- **Deepened:** Second **production** path (writers-room generation) now uses the same integration pattern (LangChain prompt + structured parse + metadata). Writers-room document preview now uses the **writers_room** retrieval domain instead of reusing the runtime-turn profile for LangChain `Document` lists. Fallback bypass is **documented in API payload**, not implied.

## 4. Where LangChain is now more canonical

- **Runtime turn graph** primary invoke (unchanged): still `invoke_runtime_adapter_with_langchain`.
- **Writers-room review:** primary generation goes through `invoke_writers_room_adapter_with_langchain`; preview docs through `get_writers_room_documents`.

## 5. Where bypass / direct paths still remain

- **Writers-room mock/raw fallback:** `adapter.generate` without LangChain parser when recovering via mock after primary failure — **intentional** (mock output is not JSON).
- **LangGraph `fallback_model`:** still raw mock `generate` (B2-next will label orchestration-level truth more explicitly; not part of B1-next scope beyond writers-room honesty).
- **Runtime graph `retrieve_context`:** direct `ContextRetriever` + `ContextPackAssembler` (or capability path) — **justified:** pack assembly for the graph is not the same as LangChain `Document` preview; forcing Documents would add churn without removing the assembler.

## 6. Why remaining paths exist

- Structured Pydantic parse requires JSON-shaped model output; **default mock adapters do not emit JSON**, so raw fallback avoids fake “structured success.”
- Graph retrieval stays on the RAG types the executor already consumes (`ContextPack` / dict-shaped retrieval), while LangChain Documents remain an integration surface for tooling and writers-room preview.

## 7. Tests added/updated

- `wos_ai_stack/tests/test_langchain_integration.py`: writers-room happy-path parse, parser-error with successful raw content, `get_writers_room_documents` domain assertion.
- `backend/tests/test_writers_room_routes.py`: `model_generation` / `metadata` / `stack_components.langchain_integration.writers_room_generation_bridge` assertions.

## 8. Exact test commands run

```powershell
cd C:\Users\YvesT\PycharmProjects\WorldOfShadows
$env:PYTHONPATH="."
python -m pytest wos_ai_stack/tests/test_langchain_integration.py wos_ai_stack/tests/test_langgraph_runtime.py -v --tb=short
```

```powershell
cd C:\Users\YvesT\PycharmProjects\WorldOfShadows\backend
$env:PYTHONPATH=".."
python -m pytest tests/test_writers_room_routes.py -v --tb=short
```

## 9. Verdict

**Pass**

## 10. Reason for verdict

- LangChain remains a real dependency; **two meaningful active paths** (runtime graph primary invoke, writers-room generation) use the normalized integration pattern.
- Structured output handling is **more consistent** on writers-room primary path (metadata mirrors runtime conventions).
- Retriever/tool bridging is **more coherent** for writers-room preview (correct domain/profile).
- Tests prove imports, parse paths, and HTTP flow surface integration fields; **fallback is explicit** when present.
- Report does not claim LangChain is universal across the repo.

## 11. Remaining risk

- Environments that route only to failing non-mock primaries rely on mock fallback behavior; operational JSON compliance for real providers still depends on adapter/model configuration.
- `stack_components` key rename (`runtime_bridge` → `runtime_turn_bridge`) may affect external consumers that read the old key (low risk; grep showed no tests depending on it).

## 12. Dependency / environment notes

- Same as existing stack: `langchain-core`, `pydantic`, `story_runtime_core` adapters; `PYTHONPATH` must include repo root when running `wos_ai_stack` tests from subpackages.
