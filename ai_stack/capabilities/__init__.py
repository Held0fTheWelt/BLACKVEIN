"""Capability registry, selector, and validator surfaces for the AI stack."""

from __future__ import annotations

from typing import Any

from .capabilities import (
    CapabilityAccessDeniedError,
    CapabilityDefinition,
    CapabilityInvocationError,
    CapabilityKind,
    CapabilityRegistry,
    CapabilityValidationError,
    RETRIEVAL_TRACE_SCHEMA_VERSION,
    build_retrieval_trace,
    capability_catalog,
    evidence_lane_mix_from_sources,
)

__all__ = [
    "CapabilityAccessDeniedError",
    "CapabilityDefinition",
    "CapabilityInvocationError",
    "CapabilityKind",
    "CapabilityRegistry",
    "CapabilityValidationError",
    "RETRIEVAL_TRACE_SCHEMA_VERSION",
    "build_retrieval_trace",
    "capability_catalog",
    "create_default_capability_registry",
    "evidence_lane_mix_from_sources",
]


def __getattr__(name: str) -> Any:
    if name == "create_default_capability_registry":
        from .capabilities_default_registry import create_default_capability_registry

        return create_default_capability_registry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
