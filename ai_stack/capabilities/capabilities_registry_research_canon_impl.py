"""Implementation: research/canon capability registrations (DS-013)."""

from __future__ import annotations

from typing import Any

from ai_stack.capabilities import CapabilityRegistry
from ai_stack.capabilities.capabilities_registry_research_canon_registration_groups import (
    register_canon_improvement_actions,
    register_canon_inspect_and_research_actions,
    register_research_claim_run_graph_capabilities,
    register_research_source_and_aspect_capabilities,
)


def register_research_canon_capabilities(
    registry: CapabilityRegistry,
    *,
    research_store: Any,
) -> None:
    """Describe what ``register_research_canon_capabilities`` does in one
    line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        registry: ``registry`` (CapabilityRegistry); meaning follows the type and call sites.
        research_store: ``research_store`` (Any); meaning follows the type and call sites.
    """
    register_research_source_and_aspect_capabilities(registry, research_store)
    register_research_claim_run_graph_capabilities(registry, research_store)
    register_canon_inspect_and_research_actions(registry, research_store)
    register_canon_improvement_actions(registry, research_store)
