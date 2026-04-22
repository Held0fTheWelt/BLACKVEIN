"""
``ai_stack/langchain_integration/bridges.py`` — expand purpose, primary
entrypoints, and invariants for maintainers.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from ai_stack.rag_retrieval_dtos import RetrievalRequest
from ai_stack.rag_types import RetrievalDomain


def _adapter_generate_kwargs(adapter: BaseModelAdapter, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Return ``kwargs`` restricted to names accepted by ``adapter.generate``.

    Production adapters accept ``model_name``; lightweight test doubles often omit it.
    Filtering avoids ``TypeError`` while still forwarding new optional parameters when implemented.
    """
    try:
        sig = inspect.signature(adapter.generate)
    except (TypeError, ValueError):
        return dict(kwargs)
    params = list(sig.parameters.values())
    if not params:
        return {}
    rest = params[1:] if params[0].name == "self" else params
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in rest):
        return dict(kwargs)
    allowed = {
        p.name
        for p in rest
        if p.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    return {k: v for k, v in kwargs.items() if k in allowed}


class RuntimeTurnStructuredOutput(BaseModel):
    """Normalized runtime output parsed through LangChain parser primitives."""

    narrative_response: str = Field(default="")
    proposed_scene_id: str | None = None
    intent_summary: str | None = None

    responder_id: str | None = None
    function_type: str | None = None
    emotional_shift: dict | None = None
    social_outcome: str | None = None
    dramatic_direction: str | None = None


class WritersRoomStructuredOutput(BaseModel):
    """Writers-room review generation output parsed through LangChain parser
    primitives.
    """

    review_notes: str = Field(default="")
    recommendations: list[str] = Field(default_factory=list)


def _build_runtime_prompt_template() -> ChatPromptTemplate:
    """Build runtime prompt template from catalog with hardcoded fallback.

    Attempts to load from CanonicalPromptCatalog for governance integration.
    Falls back to hardcoded template if catalog unavailable.

    Returns:
        ChatPromptTemplate for runtime turn model invocation
    """
    try:
        from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog
        catalog = CanonicalPromptCatalog()
        return catalog.get_runtime_turn_template()
    except (ImportError, KeyError, Exception):
        # Fallback to hardcoded template if catalog fails
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are the World of Shadows runtime turn model. "
                    "Return strictly valid JSON matching the requested schema.\n\n"
                    "NARRATIVE FORMATTING: The narrative_response field should be well-structured prose "
                    "with multiple paragraphs separated by \\n\\n (double newlines). "
                    "Break the narrative at natural points: scene setup, action/dialogue, consequences/reflection. "
                    "Each paragraph should be 2-4 sentences. This creates readable, human-friendly output when displayed.",
                ),
                (
                    "human",
                    "{full_context}"
                    "{correction_block}"
                    "IMPORTANT - Narrative Structure: Write the narrative_response as 3-4 short paragraphs separated by \\n\\n (double newlines). "
                    "Each paragraph should be 2-4 sentences. Structure: (1) scene/setting, (2) action/dialogue, (3) consequence/emotion. "
                    "This makes the narrative human-readable when displayed.\n\n"
                    "Format instructions:\n{format_instructions}",
                ),
            ]
        )


_RUNTIME_PROMPT_TEMPLATE = _build_runtime_prompt_template()
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
    """``RuntimeInvocationResult`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
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
    model_prompt: str | None = None,
    prior_output: str | None = None,
    feedback_codes: list[str] | None = None,
    rewrite_instruction: str | None = None,
    model_name: str | None = None,
) -> RuntimeInvocationResult:
    """Describe what ``invoke_runtime_adapter_with_langchain`` does in one
    line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        adapter: ``adapter`` (BaseModelAdapter); meaning follows the type and call sites.
        player_input: ``player_input`` (str); meaning follows the type and call sites.
        interpreted_input: ``interpreted_input`` (dict[str, Any]); meaning follows the type and call sites.
        retrieval_context: ``retrieval_context`` (str |
            None); meaning follows the type and call sites.
        timeout_seconds: ``timeout_seconds`` (float); meaning follows the type and call sites.
    
    Returns:
        RuntimeInvocationResult:
            Returns a value of type ``RuntimeInvocationResult``; see the function body for structure, error paths, and sentinels.
    """
    parser = _RUNTIME_OUTPUT_PARSER
    correction_block = ""
    if rewrite_instruction:
        fb = ", ".join(str(x) for x in (feedback_codes or []) if str(x).strip()) or "(none)"
        correction_block = (
            "Self-correction pass:\n"
            f"Prior draft (reference only):\n{(prior_output or '').strip() or '(none)'}\n\n"
            f"Instruction:\n{rewrite_instruction}\n\n"
            f"Feedback codes: {fb}\n\n"
        )
    if model_prompt:
        full_context = model_prompt
    else:
        interp_str = "\n".join(f"- {k}: {v}" for k, v in interpreted_input.items()) if interpreted_input else "(none)"
        full_context = (
            f"Player input:\n{player_input}\n\n"
            f"Interpreted input:\n{interp_str}\n\n"
            f"Runtime retrieval context:\n{retrieval_context or '(none)'}"
        )
    rendered_messages = _RUNTIME_PROMPT_TEMPLATE.format_messages(
        full_context=full_context,
        correction_block=correction_block,
        format_instructions=parser.get_format_instructions(),
    )
    prompt_text = "\n\n".join(f"{message.type.upper()}: {message.content}" for message in rendered_messages)
    gen_kw: dict[str, Any] = {
        "timeout_seconds": timeout_seconds,
        "retrieval_context": retrieval_context,
    }
    if model_name:
        gen_kw["model_name"] = model_name
    call = adapter.generate(prompt_text, **_adapter_generate_kwargs(adapter, gen_kw))
    if not call.success:
        return RuntimeInvocationResult(call=call, prompt_text=prompt_text, parsed_output=None, parser_error=None)
    try:
        parsed = parser.parse(call.content)
        return RuntimeInvocationResult(call=call, prompt_text=prompt_text, parsed_output=parsed, parser_error=None)
    except Exception as exc:  # pragma: no cover - parser error path exercised in tests via behavior assertions
        return RuntimeInvocationResult(call=call, prompt_text=prompt_text, parsed_output=None, parser_error=str(exc))


@dataclass
class WritersRoomInvocationResult:
    """``WritersRoomInvocationResult`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
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
    """Describe what ``invoke_writers_room_adapter_with_langchain`` does in
    one line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        adapter: ``adapter`` (BaseModelAdapter); meaning follows the type and call sites.
        module_id: ``module_id`` (str); meaning follows the type and call sites.
        focus: ``focus`` (str); meaning follows the type and call sites.
        retrieval_context: ``retrieval_context`` (str |
            None); meaning follows the type and call sites.
        timeout_seconds: ``timeout_seconds`` (float); meaning follows the type and call sites.
    
    Returns:
        WritersRoomInvocationResult:
            Returns a value of type ``WritersRoomInvocationResult``; see the function body for structure, error paths, and sentinels.
    """
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
    """``LangChainRetrieverBridge`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    retriever: Any

    def get_runtime_documents(
        self,
        *,
        query: str,
        module_id: str,
        scene_id: str | None = None,
        max_chunks: int = 4,
    ) -> list[Document]:
        """Describe what ``get_runtime_documents`` does in one line
        (verb-led summary for this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            query: ``query`` (str); meaning follows the type and call sites.
            module_id: ``module_id`` (str); meaning follows the type and call sites.
            scene_id: ``scene_id`` (str | None); meaning follows the type and call sites.
            max_chunks: ``max_chunks`` (int); meaning follows the type and call sites.
        
        Returns:
            list[Document]:
                Returns a value of type ``list[Document]``; see the function body for structure, error paths, and sentinels.
        """
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
        """LangChain Document preview for writers-room domain (aligns with
        wos.context_pack.build writers_review).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            query: ``query`` (str); meaning follows the type and call sites.
            module_id: ``module_id`` (str); meaning follows the type and call sites.
            max_chunks: ``max_chunks`` (int); meaning follows the type and call sites.
        
        Returns:
            list[Document]:
                Returns a value of type ``list[Document]``; see the function body for structure, error paths, and sentinels.
        """
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
    """Describe what ``build_langchain_retriever_bridge`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        retriever: ``retriever`` (Any); meaning follows the type and call sites.
    
    Returns:
        LangChainRetrieverBridge:
            Returns a value of type ``LangChainRetrieverBridge``; see the function body for structure, error paths, and sentinels.
    """
    return LangChainRetrieverBridge(retriever=retriever)


def build_capability_tool_bridge(
    *,
    capability_registry: Any,
    capability_name: str,
    mode: str,
    actor: str,
) -> StructuredTool:
    """Describe what ``build_capability_tool_bridge`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        capability_registry: ``capability_registry`` (Any); meaning follows the type and call sites.
        capability_name: ``capability_name`` (str); meaning follows the type and call sites.
        mode: ``mode`` (str); meaning follows the type and call sites.
        actor: ``actor`` (str); meaning follows the type and call sites.
    
    Returns:
        StructuredTool:
            Returns a value of type ``StructuredTool``; see the function body for structure, error paths, and sentinels.
    """
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
