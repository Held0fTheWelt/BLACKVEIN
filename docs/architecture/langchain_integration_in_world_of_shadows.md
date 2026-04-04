# LangChain Integration in World of Shadows

Status: active and wired in runtime-adjacent and writers-room paths (B1 repair).

## Where LangChain is used now

### 1) Runtime-adjacent turn execution path

- File: `wos_ai_stack/langgraph_runtime.py`
- Integration: `invoke_runtime_adapter_with_langchain(...)`
- Purpose:
  - LangChain prompt construction (`ChatPromptTemplate`)
  - Structured output parsing (`PydanticOutputParser`)
  - Unified metadata emitted into graph generation payload

### 2) Writers-room workflow path

- File: `backend/app/services/writers_room_service.py`
- Integrations:
  - Retriever bridge (`build_langchain_retriever_bridge`) for LangChain-style `Document` output
  - Capability tool bridge (`build_capability_tool_bridge`) for invoking capability registry through a LangChain `StructuredTool`
- Purpose:
  - reduce direct ad-hoc wiring for retrieval/tool access
  - keep governance capability invocation while adding standardized LangChain bridges

## Integration layer surface

- Package: `wos_ai_stack/langchain_integration/`
- Key primitives:
  - `invoke_runtime_adapter_with_langchain`
  - `RuntimeTurnStructuredOutput`
  - `build_langchain_retriever_bridge`
  - `build_capability_tool_bridge`

## What is intentionally not migrated yet

- Legacy backend in-process runtime modules outside the canonical World-Engine story path.
- Broad replacement of all direct adapter calls across unrelated subsystems.
- End-to-end LangChain agent framework migration (not required for B1 scope).

## Why this scope

The B1 goal is a real, exercised integration layer that reduces fragmentation now without introducing speculative architecture churn.
