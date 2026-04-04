"""LangChain-facing integration layer for World of Shadows.

Primary entry points (use these instead of ad hoc LangChain imports elsewhere):

- ``invoke_runtime_adapter_with_langchain`` — Chat prompt + Pydantic parse around ``BaseModelAdapter`` (runtime turn graph).
- ``invoke_writers_room_adapter_with_langchain`` — Chat prompt + Pydantic parse for writers-room review generation.
- ``build_langchain_retriever_bridge`` — wraps ``ContextRetriever`` as LangChain ``Document`` lists.
- ``build_capability_tool_bridge`` — exposes a ``CapabilityRegistry`` entry as a ``StructuredTool`` (e.g. writers-room flows).
"""

from .bridges import (
    LangChainRetrieverBridge,
    RuntimeInvocationResult,
    RuntimeTurnStructuredOutput,
    WritersRoomInvocationResult,
    WritersRoomStructuredOutput,
    build_capability_tool_bridge,
    build_langchain_retriever_bridge,
    invoke_runtime_adapter_with_langchain,
    invoke_writers_room_adapter_with_langchain,
)

__all__ = [
    "LangChainRetrieverBridge",
    "RuntimeInvocationResult",
    "RuntimeTurnStructuredOutput",
    "WritersRoomInvocationResult",
    "WritersRoomStructuredOutput",
    "build_capability_tool_bridge",
    "build_langchain_retriever_bridge",
    "invoke_runtime_adapter_with_langchain",
    "invoke_writers_room_adapter_with_langchain",
]
