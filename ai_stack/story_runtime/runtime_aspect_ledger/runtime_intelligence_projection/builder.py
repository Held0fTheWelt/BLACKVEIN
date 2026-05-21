"""Coordinator for runtime-intelligence projection assembly."""

from __future__ import annotations

from typing import Any, Callable

from ..records import _json_safe
from .adr_sidecar_projection import attach_adr_sidecar_projections
from .aspect_record_sources import collect_aspect_record_sources
from .capability_context import build_capability_context_sources
from .projection_payload import build_projection_payload
from .record_field_sources import collect_record_field_sources
from .semantic_dispatch import build_semantic_dispatch_sources


def build_runtime_intelligence_projection(
    ledger: dict[str, Any] | None,
    *,
    registry_for_turn_class: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Project canonical aspect-record storage into runtime diagnostics."""
    values = collect_aspect_record_sources(ledger)
    values.update(collect_record_field_sources(values))
    values.update(build_capability_context_sources(values))
    values.update(
        build_semantic_dispatch_sources(
            values,
            registry_for_turn_class=registry_for_turn_class,
        )
    )
    projection_payload = build_projection_payload(values)
    attach_adr_sidecar_projections(
        projection_payload,
        capability_context=values["capability_context"],
        semantic_validator_dispatch_report=values["semantic_validator_dispatch_report"],
    )
    return _json_safe(projection_payload)
