"""Default capability registry factory (handlers + register wiring)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_stack.rag import ContextPackAssembler, ContextRetriever

from ai_stack.capabilities import CapabilityRegistry
from ai_stack.capabilities.capabilities_registry_context_writers import register_context_writers_capabilities
from ai_stack.capabilities.capabilities_registry_research_canon import register_research_canon_capabilities


def create_default_capability_registry(
    *,
    retriever: "ContextRetriever",
    assembler: "ContextPackAssembler",
    repo_root: Path,
) -> CapabilityRegistry:
    """Describe what ``create_default_capability_registry`` does in one
    line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        retriever: ``retriever`` ('ContextRetriever'); meaning follows the type and call sites.
        assembler: ``assembler`` ('ContextPackAssembler'); meaning follows the type and call sites.
        repo_root: ``repo_root`` (Path); meaning follows the type and call sites.
    
    Returns:
        CapabilityRegistry:
            Returns a value of type ``CapabilityRegistry``; see the function body for structure, error paths, and sentinels.
    """
    from ai_stack.research.research_langgraph import research_store_from_repo_root

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
