from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from ai_stack.rag import RetrievalDomain, RetrievalRequest


class RuntimeTurnStructuredOutput(BaseModel):
    """Normalized runtime output parsed through LangChain parser primitives."""

    narrative_response: str = Field(default="")
    proposed_scene_id: str | None = None
    intent_summary: str | None = None


class WritersRoomStructuredOutput(BaseModel):
    """Writers-room review generation output parsed through LangChain parser primitives."""

    review_notes: str = Field(default="")
    recommendations: list[str] = Field(default_factory=list)


_RUNTIME_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the World of Shadows runtime turn model. "
            "Return strictly valid JSON matching the requested schema.",
        ),
        (
            "human",
            "Player input:\n{player_input}\n\n"
            "Interpreted input:\n{interpreted_input}\n\n"
            "Runtime retrieval context:\n{retrieval_context}\n\n"
            "Format instructions:\n{format_instructions}",
        ),
    ]
)
_WRITERS_ROOM_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the World of Shadows writers-room review assistant. "
            "Return strictly valid JSON matching the requested schema.",
        ),
        (
            "human",
            "Module: {module_id}\n"
            "Review focus: {focus}\n\n"
            "Retrieved context for evidence:\n{retrieval_context}\n\n"
            "Format instructions:\n{format_instructions}",
        ),
    ]
)
_RUNTIME_OUTPUT_PARSER = PydanticOutputParser(pydantic_object=RuntimeTurnStructuredOutput)
_WRITERS_ROOM_OUTPUT_PARSER = PydanticOutputParser(pydantic_object=WritersRoomStructuredOutput)


@dataclass
class RuntimeInvocationResult:
    call: ModelCallResult
    prompt_text: str
    parsed_output: RuntimeTurnStructuredOutput | None
    parser_error: str | None


def invoke_runtime_adapter_with_langchain(
    *,
    adapter: BaseModelAdapter,
    player_input: str,
    interpreted_input: dict[str, Any],
    retrieval_context: str | None,
    timeout_seconds: float,
) -> RuntimeInvocationResult:
    parser = _RUNTIME_OUTPUT_PARSER
    rendered_messages = _RUNTIME_PROMPT_TEMPLATE.format_messages(
        player_input=player_input,
        interpreted_input=interpreted_input,
        retrieval_context=retrieval_context or "(none)",
        format_instructions=parser.get_format_instructions(),
    )
    prompt_text = "\n\n".join(f"{message.type.upper()}: {message.content}" for message in rendered_messages)
    call = adapter.generate(
        prompt_text,
        timeout_seconds=timeout_seconds,
        retrieval_context=retrieval_context,
    )
    if not call.success:
        return RuntimeInvocationResult(call=call, prompt_text=prompt_text, parsed_output=None, parser_error=None)
    try:
        parsed = parser.parse(call.content)
        return RuntimeInvocationResult(call=call, prompt_text=prompt_text, parsed_output=parsed, parser_error=None)
    except Exception as exc:  # pragma: no cover - parser error path exercised in tests via behavior assertions
        return RuntimeInvocationResult(call=call, prompt_text=prompt_text, parsed_output=None, parser_error=str(exc))


@dataclass
class WritersRoomInvocationResult:
    call: ModelCallResult
    prompt_text: str
    parsed_output: WritersRoomStructuredOutput | None
    parser_error: str | None


def invoke_writers_room_adapter_with_langchain(
    *,
    adapter: BaseModelAdapter,
    module_id: str,
    focus: str,
    retrieval_context: str | None,
    timeout_seconds: float,
) -> WritersRoomInvocationResult:
    parser = _WRITERS_ROOM_OUTPUT_PARSER
    rendered_messages = _WRITERS_ROOM_PROMPT_TEMPLATE.format_messages(
        module_id=module_id,
        focus=focus,
        retrieval_context=retrieval_context or "(none)",
        format_instructions=parser.get_format_instructions(),
    )
    prompt_text = "\n\n".join(f"{message.type.upper()}: {message.content}" for message in rendered_messages)
    call = adapter.generate(
        prompt_text,
        timeout_seconds=timeout_seconds,
        retrieval_context=retrieval_context,
    )
    if not call.success:
        return WritersRoomInvocationResult(call=call, prompt_text=prompt_text, parsed_output=None, parser_error=None)
    try:
        parsed = parser.parse(call.content)
        return WritersRoomInvocationResult(call=call, prompt_text=prompt_text, parsed_output=parsed, parser_error=None)
    except Exception as exc:  # pragma: no cover - parser error path exercised in tests
        return WritersRoomInvocationResult(call=call, prompt_text=prompt_text, parsed_output=None, parser_error=str(exc))


@dataclass
class LangChainRetrieverBridge:
    retriever: Any

    def get_runtime_documents(
        self,
        *,
        query: str,
        module_id: str,
        scene_id: str | None = None,
        max_chunks: int = 4,
    ) -> list[Document]:
        request = RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query=query,
            module_id=module_id,
            scene_id=scene_id,
            max_chunks=max_chunks,
        )
        result = self.retriever.retrieve(request)
        return [
            Document(
                page_content=hit.snippet,
                metadata={
                    "chunk_id": hit.chunk_id,
                    "source_path": hit.source_path,
                    "source_version": hit.source_version,
                    "domain": request.domain.value,
                    "content_class": hit.content_class,
                    "score": hit.score,
                    "index_version": result.index_version,
                    "corpus_fingerprint": result.corpus_fingerprint,
                },
            )
            for hit in result.hits
        ]

    def get_writers_room_documents(
        self,
        *,
        query: str,
        module_id: str,
        max_chunks: int = 6,
    ) -> list[Document]:
        """LangChain Document preview for writers-room domain (aligns with wos.context_pack.build writers_review)."""
        request = RetrievalRequest(
            domain=RetrievalDomain.WRITERS_ROOM,
            profile="writers_review",
            query=query,
            module_id=module_id,
            scene_id=None,
            max_chunks=max_chunks,
        )
        result = self.retriever.retrieve(request)
        return [
            Document(
                page_content=hit.snippet,
                metadata={
                    "chunk_id": hit.chunk_id,
                    "source_path": hit.source_path,
                    "source_version": hit.source_version,
                    "domain": request.domain.value,
                    "content_class": hit.content_class,
                    "score": hit.score,
                    "index_version": result.index_version,
                    "corpus_fingerprint": result.corpus_fingerprint,
                },
            )
            for hit in result.hits
        ]


def build_langchain_retriever_bridge(retriever: Any) -> LangChainRetrieverBridge:
    return LangChainRetrieverBridge(retriever=retriever)


def build_capability_tool_bridge(
    *,
    capability_registry: Any,
    capability_name: str,
    mode: str,
    actor: str,
) -> StructuredTool:
    def _invoke_capability(
        module_id: str,
        summary: str,
        recommendations: list[str],
        evidence_sources: list[str],
    ) -> dict[str, Any]:
        payload = {
            "module_id": module_id,
            "summary": summary,
            "recommendations": recommendations,
            "evidence_sources": evidence_sources,
        }
        return capability_registry.invoke(
            name=capability_name,
            mode=mode,
            actor=actor,
            payload=payload,
        )

    return StructuredTool.from_function(
        func=_invoke_capability,
        name=f"{capability_name}.tool_bridge",
        description=f"LangChain tool bridge for capability {capability_name}.",
    )
