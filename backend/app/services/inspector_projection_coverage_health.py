"""Coverage/health projection from diagnostics rows — DS-053."""

from __future__ import annotations

from typing import Any

from ai_stack.semantic_planner_effect_surface import support_level_for_module

from app.contracts.inspector_turn_projection import (
    INSPECTOR_COVERAGE_HEALTH_PROJECTION_SCHEMA_VERSION,
    INSPECTOR_SECTION_STATUS_SUPPORTED,
    make_supported_section,
    make_unavailable_section,
)
from app.services.ai_stack_evidence_service import build_session_evidence_bundle
from app.services.inspector_projection_coverage_health_distribution import (
    build_coverage_health_supported_inner,
)
from app.services.inspector_projection_shared import _build_root, _diagnostics_rows


def build_inspector_coverage_health_projection(*, session_id: str, trace_id: str) -> dict[str, Any]:
    """Return evidence-backed coverage/health aggregates."""
    bundle = build_session_evidence_bundle(session_id=session_id, trace_id=trace_id)
    if bundle.get("error") == "backend_session_not_found":
        return bundle
    rows = _diagnostics_rows(bundle)
    if not rows:
        section = make_unavailable_section(
            reason="no_turn_diagnostics_for_session",
            data={
                "metrics": {},
                "distribution": {},
            },
        )
        return _build_root(
            bundle=bundle,
            session_id=session_id,
            schema_version=INSPECTOR_COVERAGE_HEALTH_PROJECTION_SCHEMA_VERSION,
            projection_status="partial",
            section_key="coverage_health_projection",
            section=section,
        )

    mid = bundle.get("module_id")
    session_support = support_level_for_module(mid if isinstance(mid, str) else "").value
    required_minimum = {
        "gate_outcome_distribution": INSPECTOR_SECTION_STATUS_SUPPORTED,
        "validation_outcome_distribution": INSPECTOR_SECTION_STATUS_SUPPORTED,
        "fallback_frequency": INSPECTOR_SECTION_STATUS_SUPPORTED,
        "effect_and_rejection_rationale_distribution": INSPECTOR_SECTION_STATUS_SUPPORTED,
        "empty_fluency_risk_distribution": INSPECTOR_SECTION_STATUS_SUPPORTED,
        "unsupported_unavailable_frequency": INSPECTOR_SECTION_STATUS_SUPPORTED,
    }
    inner = build_coverage_health_supported_inner(
        rows,
        session_support=session_support,
        required_minimum_metrics_status=required_minimum,
    )
    section = make_supported_section(inner)
    return _build_root(
        bundle=bundle,
        session_id=session_id,
        schema_version=INSPECTOR_COVERAGE_HEALTH_PROJECTION_SCHEMA_VERSION,
        projection_status="ok",
        section_key="coverage_health_projection",
        section=section,
    )
