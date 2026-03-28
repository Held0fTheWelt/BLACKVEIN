"""W2.1-R3 — Canonical AI Adapter Registry

Lightweight registry for mapping adapter names to adapter instances.
Enables explicit, testable adapter selection without provider-specific hardcoding.

Registry pattern:
- register_adapter(name, adapter) — Register adapter by name
- get_adapter(name) — Look up adapter by name
- clear_registry() — Clear all registrations (test cleanup)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.ai_adapter import StoryAIAdapter


# Global registry: maps adapter name → adapter instance
_adapter_registry: dict[str, StoryAIAdapter] = {}


def register_adapter(name: str, adapter: StoryAIAdapter) -> None:
    """Register an AI adapter by name.

    Args:
        name: Canonical adapter name (e.g., "mock", "claude_story")
        adapter: StoryAIAdapter instance

    Raises:
        ValueError: If name is empty or adapter is None
    """
    if not name or not name.strip():
        raise ValueError("Adapter name cannot be empty")
    if adapter is None:
        raise ValueError("Adapter cannot be None")

    _adapter_registry[name.lower()] = adapter


def get_adapter(name: str) -> StoryAIAdapter | None:
    """Look up an adapter by name.

    Args:
        name: Adapter name to look up

    Returns:
        StoryAIAdapter if registered, None otherwise
    """
    if not name:
        return None
    return _adapter_registry.get(name.lower())


def clear_registry() -> None:
    """Clear all registered adapters. Primarily for test cleanup."""
    _adapter_registry.clear()


def adapter_registered(name: str) -> bool:
    """Check if an adapter is registered.

    Args:
        name: Adapter name to check

    Returns:
        True if adapter is registered, False otherwise
    """
    if not name:
        return False
    return name.lower() in _adapter_registry
