# LangChain integration

LangChain is used for **prompt construction**, **structured output parsing**, and **retriever bridging**—not as a second runtime authority.

## Runtime-adjacent path

- **File:** `ai_stack/langgraph_runtime.py`
- **Function:** `invoke_runtime_adapter_with_langchain(...)`
- **Role:** `ChatPromptTemplate`, `PydanticOutputParser`, unified metadata on the generation payload inside the LangGraph `invoke_model` node.

## Writers’ Room path

- **File:** `backend/app/services/writers_room_service.py`
- **Primary generation:** `invoke_writers_room_adapter_with_langchain` with `WritersRoomStructuredOutput`; metadata mirrors runtime (`langchain_prompt_used`, `structured_output`, `langchain_parser_error`).
- **Document preview:** `LangChainRetrieverBridge.get_writers_room_documents` uses domain `writers_room` / profile `writers_review` (aligned with `wos.context_pack.build`), not the runtime-turn profile.
- **Capability bridge:** `build_capability_tool_bridge` for review bundle tooling.

## Bounded bypass

If the primary adapter fails and recovery uses the default **mock** adapter, generation may use raw `adapter.generate` with `adapter_invocation_mode: raw_adapter_fallback` and a `bypass_note` — structured parse is skipped when mock output is not JSON (same honesty pattern as LangGraph `fallback_model`).

## Package surface

`ai_stack/langchain_integration/`: runtime and Writers’ Room invoke helpers, retriever bridge, capability tool bridge.

## Related

- [`LangGraph.md`](LangGraph.md)
- [`../ai/ai-stack-overview.md`](../ai/ai-stack-overview.md)
