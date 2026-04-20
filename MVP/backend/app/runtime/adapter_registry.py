"""W2.1-R3 — Canonical AI Adapter Registry

Lightweight registry for mapping adapter names to adapter instances.
Enables explicit, testable adapter selection without provider-specific hardcoding.

Registry pattern:
- register_adapter(name, adapter) — Register adapter by name
- get_adapter(name) — Look up adapter by name
- clear_registry() — Clear all registrations (test cleanup)

Task 2A adds model-aware registration:
- register_adapter_model(spec, adapter) — Register adapter plus AdapterModelSpec
- get_model_spec(name) / iter_model_specs() — Read routing metadata
- clear_registry() clears both legacy adapters and model specs
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.runtime.ai_adapter import StoryAIAdapter

from app.runtime.model_routing_contracts import AdapterModelSpec

# Global registry: maps adapter name → adapter instance
_adapter_registry: dict[str, StoryAIAdapter] = {}

# Task 2A: model spec per adapter name (lowercased key)
_model_spec_by_name: dict[str, AdapterModelSpec] = {}


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


def register_adapter_model(spec: AdapterModelSpec, adapter: StoryAIAdapter) -> None:
    """Register an adapter together with its Task 2A model routing spec.

    Writes to the legacy adapter map and the model-spec store. ``adapter.adapter_name``
    must match ``spec.adapter_name`` (trimmed) for a single canonical name.

    Raises:
        ValueError: On invalid name, None adapter, or name mismatch.
    """
    if not spec.adapter_name or not spec.adapter_name.strip():
        raise ValueError("Adapter name cannot be empty")
    if adapter is None:
        raise ValueError("Adapter cannot be None")
    if adapter.adapter_name.strip() != spec.adapter_name.strip():
        raise ValueError(
            "adapter.adapter_name must match spec.adapter_name: "
            f"{adapter.adapter_name!r} != {spec.adapter_name!r}"
        )

    key = spec.adapter_name.lower()
    _adapter_registry[key] = adapter
    _model_spec_by_name[key] = spec


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


def get_model_spec(name: str) -> AdapterModelSpec | None:
    """Return the Task 2A model spec for an adapter name, if registered."""
    if not name:
        return None
    return _model_spec_by_name.get(name.lower())


def iter_model_specs() -> list[AdapterModelSpec]:
    """Snapshot of all registered model specs (deterministic iteration order by adapter name)."""
    return [_model_spec_by_name[k] for k in sorted(_model_spec_by_name.keys())]


def clear_registry() -> None:
    """Clear legacy adapters and Task 2A model specs (primarily for tests)."""
    _adapter_registry.clear()
    _model_spec_by_name.clear()


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


def has_model_spec(name: str) -> bool:
    """Return True if a Task 2A ``AdapterModelSpec`` exists for this adapter name."""
    return get_model_spec(name) is not None


def legacy_adapter_without_model_spec(name: str) -> bool:
    """True when an adapter instance exists but no model spec is registered for that name."""
    if not name:
        return False
    key = name.lower()
    return key in _adapter_registry and key not in _model_spec_by_name


def snapshot_registry_keys() -> tuple[list[str], list[str]]:
    """Return sorted legacy adapter names and sorted model-spec names (diagnostics / Task 2 inventory)."""

    return (sorted(_adapter_registry.keys()), sorted(_model_spec_by_name.keys()))

