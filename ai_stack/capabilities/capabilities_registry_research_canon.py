"""Research and canon-improvement capability registrations (DS-013 facade)."""

from __future__ import annotations

from typing import Any

from ai_stack.capabilities import CapabilityRegistry
from ai_stack.capabilities.capabilities_registry_research_canon_impl import register_research_canon_capabilities as _register

__all__ = ["register_research_canon_capabilities"]


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
    _register(registry, research_store=research_store)
