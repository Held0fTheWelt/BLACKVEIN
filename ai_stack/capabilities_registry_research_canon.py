"""Research and canon-improvement capability registrations (DS-013 facade)."""

from __future__ import annotations

from typing import Any

from ai_stack.capabilities import CapabilityRegistry
from ai_stack.capabilities_registry_research_canon_impl import register_research_canon_capabilities as _register

__all__ = ["register_research_canon_capabilities"]


def register_research_canon_capabilities(
    registry: CapabilityRegistry,
    *,
    research_store: Any,
) -> None:
    _register(registry, research_store=research_store)
