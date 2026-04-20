"""Prefer ``register_adapter_model`` in routing-sensitive tests (Task 2A+)."""

from __future__ import annotations

from app.runtime.adapter_registry import register_adapter_model
from app.runtime.ai_adapter import StoryAIAdapter
from app.runtime.model_routing_contracts import AdapterModelSpec


def register_routing_adapter(spec: AdapterModelSpec, adapter: StoryAIAdapter) -> None:
    """Register adapter + spec together (routing-visible)."""
    register_adapter_model(spec, adapter)
