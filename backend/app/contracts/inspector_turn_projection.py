"""Canonical read-only contracts for Inspector Suite single-turn diagnostics."""

from __future__ import annotations

from typing import Any

INSPECTOR_TURN_PROJECTION_SCHEMA_VERSION = "inspector_turn_projection_v2"
INSPECTOR_TIMELINE_PROJECTION_SCHEMA_VERSION = "inspector_timeline_projection_v2"
INSPECTOR_COMPARISON_PROJECTION_SCHEMA_VERSION = "inspector_comparison_projection_v2"
INSPECTOR_COVERAGE_HEALTH_PROJECTION_SCHEMA_VERSION = "inspector_coverage_health_projection_v2"
INSPECTOR_PROVENANCE_RAW_PROJECTION_SCHEMA_VERSION = "inspector_provenance_raw_projection_v2"
INSPECTOR_SECTION_STATUS_SUPPORTED = "supported"
INSPECTOR_SECTION_STATUS_UNSUPPORTED = "unsupported"
INSPECTOR_SECTION_STATUS_UNAVAILABLE = "unavailable"

INSPECTOR_REQUIRED_SECTION_KEYS: tuple[str, ...] = (
    "turn_identity",
    "planner_state_projection",
    "decision_trace_projection",
    "gate_projection",
    "validation_projection",
    "authority_projection",
    "fallback_projection",
    "provenance_projection",
    "comparison_ready_fields",
)


def make_supported_section(data: dict[str, Any] | list[Any] | None) -> dict[str, Any]:
    """Return a section envelope with explicit supported posture."""
    return {
        "status": INSPECTOR_SECTION_STATUS_SUPPORTED,
        "data": data,
        "unsupported_reason": None,
        "unavailable_reason": None,
    }


def make_unsupported_section(*, reason: str, data: dict[str, Any] | list[Any] | None = None) -> dict[str, Any]:
    """Return a section envelope for contract-supported but M1-unsupported slices."""
    return {
        "status": INSPECTOR_SECTION_STATUS_UNSUPPORTED,
        "data": data,
        "unsupported_reason": reason,
        "unavailable_reason": None,
    }


def make_unavailable_section(*, reason: str, data: dict[str, Any] | list[Any] | None = None) -> dict[str, Any]:
    """Return a section envelope for data that is structurally supported but absent."""
    return {
        "status": INSPECTOR_SECTION_STATUS_UNAVAILABLE,
        "data": data,
        "unsupported_reason": None,
        "unavailable_reason": reason,
    }


def build_inspector_turn_projection_root(
    *,
    trace_id: str | None,
    backend_session_id: str,
    world_engine_story_session_id: str | None,
    projection_status: str,
    sections: dict[str, dict[str, Any]],
    warnings: list[str] | None = None,
    raw_evidence_refs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build canonical Inspector Suite payload with deterministic keys."""
    payload: dict[str, Any] = {
        "schema_version": INSPECTOR_TURN_PROJECTION_SCHEMA_VERSION,
        "projection_status": projection_status,
        "trace_id": trace_id,
        "backend_session_id": backend_session_id,
        "world_engine_story_session_id": world_engine_story_session_id,
        "warnings": list(warnings or []),
        "raw_evidence_refs": raw_evidence_refs or {},
    }
    for key in INSPECTOR_REQUIRED_SECTION_KEYS:
        payload[key] = sections.get(
            key,
            make_unavailable_section(reason=f"section_missing:{key}"),
        )
    return payload


def build_inspector_view_projection_root(
    *,
    schema_version: str,
    trace_id: str | None,
    backend_session_id: str,
    world_engine_story_session_id: str | None,
    projection_status: str,
    section_key: str,
    section: dict[str, Any],
    warnings: list[str] | None = None,
    raw_evidence_refs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build canonical Inspector payload for a dedicated projection endpoint."""
    return {
        "schema_version": schema_version,
        "projection_status": projection_status,
        "trace_id": trace_id,
        "backend_session_id": backend_session_id,
        "world_engine_story_session_id": world_engine_story_session_id,
        "warnings": list(warnings or []),
        "raw_evidence_refs": raw_evidence_refs or {},
        section_key: section,
    }
