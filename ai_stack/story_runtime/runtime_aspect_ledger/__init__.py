"""Public API for the story runtime aspect ledger.

The package stores canonical per-aspect turn records, derives runtime
intelligence projections, and exposes ADR-0041 authority diagnostics. The
implementation lives in named modules by responsibility; this facade preserves
legacy imports and keeps the authority registry hook monkeypatchable for tests.
"""

from __future__ import annotations

from typing import Any

from .authority_preview import (
    adr0041_validator_registry_for_turn_class,
    build_adr0041_validation_authority_preview,
    build_adr0041_validator_dispatch_harness_report,
    classify_adr0041_validation_authority_drift,
)
from .capability_projection import (
    _build_adr0041_plan_projection_sibling,
    _infer_adr0041_turn_class_from_situation,
    _select_semantic_capabilities_from_runtime_context,
    build_semantic_capability_selection_projection,
    build_semantic_validator_dispatch_report_projection,
    build_semantic_validator_execution_plan_projection,
)
from .constants import *
from .feature_flags import (
    resolve_adr0041_plan_projection_enabled,
    resolve_adr0041_readiness_co_authority_preview_enabled,
    resolve_adr0041_runtime_readiness_consumer_enabled,
    resolve_adr0041_scoped_co_authority_enabled,
    resolve_adr0041_scoped_readiness_aggregation_enabled,
    resolve_adr0041_scoped_readiness_enforcement_enabled,
)
from .projection_helpers import _first_text, _record_block, _record_nested_value, _record_reasons
from .records import RuntimeAspectLedger, _json_safe, empty_aspect_record, make_aspect_record, stable_ledger_json
from . import authority_preview as _authority_preview
from . import normalization as _normalization
from . import runtime_intelligence_projection as _runtime_intelligence_projection
from . import score_metadata as _score_metadata


def build_runtime_intelligence_projection(ledger: dict[str, Any] | None) -> dict[str, Any]:
    """Build the diagnostic projection using the package-level registry hook."""
    return _runtime_intelligence_projection.build_runtime_intelligence_projection(
        ledger,
        registry_for_turn_class=adr0041_validator_registry_for_turn_class,
    )


def normalize_runtime_aspect_ledger(ledger: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize a ledger and rebuild projections through the public facade."""
    return _normalization.normalize_runtime_aspect_ledger(
        ledger,
        projection_builder=build_runtime_intelligence_projection,
    )


def initialize_runtime_aspect_ledger(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Create a new ledger while honoring patched package-level projections."""
    kwargs.setdefault("normalizer", normalize_runtime_aspect_ledger)
    return _normalization.initialize_runtime_aspect_ledger(*args, **kwargs)


def ensure_runtime_aspect_ledger(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Return an existing normalized ledger or attach a new one to state."""
    kwargs.setdefault("normalizer", normalize_runtime_aspect_ledger)
    return _normalization.ensure_runtime_aspect_ledger(*args, **kwargs)


def set_aspect_record(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Replace one aspect record and rebuild derived projections."""
    kwargs.setdefault("normalizer", normalize_runtime_aspect_ledger)
    return _normalization.set_aspect_record(*args, **kwargs)


def get_aspect_record(ledger: dict[str, Any], aspect_key: str) -> dict[str, Any]:
    """Return one normalized aspect record by key."""
    return _normalization.get_aspect_record(ledger, aspect_key)


def aspect_score_metadata(ledger: dict[str, Any] | None) -> dict[str, Any]:
    """Return Langfuse/governance score metadata for the current ledger."""
    return _score_metadata.aspect_score_metadata(
        ledger,
        normalizer=normalize_runtime_aspect_ledger,
        record_getter=get_aspect_record,
    )


def _build_adr0041_plan_enforced_runtime_projection_dispatch(**kwargs: Any) -> dict[str, Any]:
    """Build the ADR-0041 graph sidecar through the package-level registry hook."""
    kwargs.setdefault("registry_for_turn_class", adr0041_validator_registry_for_turn_class)
    return _authority_preview._build_adr0041_plan_enforced_runtime_projection_dispatch(**kwargs)
