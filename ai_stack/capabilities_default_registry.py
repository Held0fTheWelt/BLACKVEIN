"""Default capability registry factory (handlers + register wiring)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_stack.rag import ContextPackAssembler, ContextRetriever

from ai_stack.capabilities import CapabilityRegistry
from ai_stack.capabilities_registry_context_writers import register_context_writers_capabilities
from ai_stack.capabilities_registry_research_canon import register_research_canon_capabilities


def create_default_capability_registry(
    *,
    retriever: "ContextRetriever",
    assembler: "ContextPackAssembler",
    repo_root: Path,
) -> CapabilityRegistry:
    from ai_stack.research_langgraph import research_store_from_repo_root

    registry = CapabilityRegistry()
    research_store = research_store_from_repo_root(repo_root)
    register_context_writers_capabilities(
        registry,
        retriever=retriever,
        assembler=assembler,
        repo_root=repo_root,
    )
    register_research_canon_capabilities(registry, research_store=research_store)
    return registry
