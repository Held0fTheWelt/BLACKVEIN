"""Context pack, transcript, and writers-room capability registrations."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_stack.rag import ContextPackAssembler, ContextRetriever

from ai_stack.capabilities import (
    CapabilityDefinition,
    CapabilityKind,
    CapabilityRegistry,
)
from ai_stack.capabilities_registry_context_writers_handlers import (
    build_context_pack_handler,
    build_review_bundle_handler,
    build_transcript_read_handler,
)


def register_context_writers_capabilities(
    registry: CapabilityRegistry,
    *,
    retriever: "ContextRetriever",
    assembler: "ContextPackAssembler",
    repo_root: Path,
) -> None:
    """Describe what ``register_context_writers_capabilities`` does in one
    line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        registry: ``registry`` (CapabilityRegistry); meaning follows the type and call sites.
        retriever: ``retriever`` ('ContextRetriever'); meaning follows the type and call sites.
        assembler: ``assembler`` ('ContextPackAssembler'); meaning follows the type and call sites.
        repo_root: ``repo_root`` (Path); meaning follows the type and call sites.
    """
    context_pack_handler = build_context_pack_handler(retriever, assembler)
    transcript_read_handler = build_transcript_read_handler(repo_root)
    review_bundle_handler = build_review_bundle_handler()

    registry.register(
        CapabilityDefinition(
            name="wos.context_pack.build",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "profile": {"type": "string"},
                    "query": {"type": "string"},
                    "module_id": {"type": "string"},
                    "scene_id": {"type": "string"},
                    "max_chunks": {"type": "integer"},
                    "use_sparse_only": {"type": "boolean"},
                    "retrieval_min_score": {"type": ["number", "null"]},
                },
                "required": ["profile", "query"],
            },
            result_schema={
                "type": "object",
                "properties": {"retrieval": {"type": "object"}, "context_text": {"type": "string"}},
                "required": ["retrieval", "context_text"],
            },
            allowed_modes={"runtime", "writers_room", "improvement"},
            audit_required=True,
            failure_semantics="returns capability error and emits audit event",
            handler=context_pack_handler,
        )
    )
    # wos.transcript.read: used by the improvement sandbox experiment route (persisted run JSON
    # under world-engine var/runs). Runtime and admin remain secondary / optional call sites.
    registry.register(
        CapabilityDefinition(
            name="wos.transcript.read",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
            },
            result_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}, "content": {"type": "string"}},
                "required": ["run_id", "content"],
            },
            allowed_modes={"runtime", "improvement", "admin"},
            audit_required=True,
            failure_semantics="raises run_not_found error with audited trace",
            handler=transcript_read_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.review_bundle.build",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "module_id": {"type": "string"},
                    "summary": {"type": "string"},
                    "recommendations": {"type": "array"},
                    "evidence_sources": {"type": "array"},
                },
                "required": ["module_id"],
            },
            result_schema={
                "type": "object",
                "properties": {
                    "bundle_id": {"type": "string"},
                    "module_id": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["bundle_id", "module_id", "status"],
            },
            allowed_modes={"writers_room", "improvement", "admin"},
            audit_required=True,
            failure_semantics="returns recommendation-only bundle metadata",
            handler=review_bundle_handler,
        )
    )
