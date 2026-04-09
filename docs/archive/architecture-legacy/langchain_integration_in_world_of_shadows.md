# LangChain Integration in World of Shadows

Status: active and wired in runtime-adjacent and writers-room paths (B1 repair, B1-next hardening).

## Where LangChain is used now

### 1) Runtime-adjacent turn execution path

- File: `ai_stack/langgraph_runtime.py`
- Integration: `invoke_runtime_adapter_with_langchain(...)`
- Purpose:
  - LangChain prompt construction (`ChatPromptTemplate`)
  - Structured output parsing (`PydanticOutputParser`)
  - Unified metadata emitted into graph generation payload

### 2) Writers-room workflow path

- File: `backend/app/services/writers_room_service.py`
- Integrations:
  - **Primary model generation:** `invoke_writers_room_adapter_with_langchain` (Chat prompt + `WritersRoomStructuredOutput` parse); `model_generation.metadata` mirrors runtime graph (`langchain_prompt_used`, `structured_output`, `langchain_parser_error`).
  - **Document preview:** `LangChainRetrieverBridge.get_writers_room_documents` uses domain `writers_room` / profile `writers_review` (aligned with `wos.context_pack.build`), not the runtime-turn retriever profile.
  - Capability tool bridge (`build_capability_tool_bridge`) for review bundle invocation.
- **Bounded bypass:** If the primary adapter fails (or is missing) and recovery uses the default **mock** adapter, generation uses **raw** `adapter.generate` with explicit `adapter_invocation_mode: raw_adapter_fallback` and a `bypass_note` — mock output is not JSON, so structured LangChain parse is skipped on that path (same honesty pattern as LangGraph `fallback_model`).

## Integration layer surface

- Package: `ai_stack/langchain_integration/`
- Key primitives:
  - `invoke_runtime_adapter_with_langchain` / `RuntimeTurnStructuredOutput`
  - `invoke_writers_room_adapter_with_langchain` / `WritersRoomStructuredOutput`
  - `build_langchain_retriever_bridge` (`get_runtime_documents`, `get_writers_room_documents`)
  - `build_capability_tool_bridge`

## What is intentionally not migrated yet

- Legacy backend in-process runtime modules outside the canonical World-Engine story path.
- Broad replacement of all direct adapter calls across unrelated subsystems.
- End-to-end LangChain agent framework migration (not required for B1 scope).

## Why this scope

The B1 goal is a real, exercised integration layer that reduces fragmentation now without introducing speculative architecture churn.
