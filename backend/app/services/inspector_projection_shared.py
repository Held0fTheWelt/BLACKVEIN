"""Shared inspector projection helpers (leaf module — breaks import cycles).

DS-001c: ``inspector_projection_coverage_health`` needed ``_build_root`` / ``_diagnostics_rows``
from ``inspector_projection_service`` while the service delegated coverage-health back — cycle.
"""

from __future__ import annotations

from typing import Any

from app.contracts.inspector_turn_projection import build_inspector_view_projection_root


def _diagnostics_rows(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics = bundle.get("world_engine_diagnostics")
    if not isinstance(diagnostics, dict):
        return []
    rows = diagnostics.get("diagnostics")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _build_root(
    *,
    bundle: dict[str, Any],
    session_id: str,
    schema_version: str,
    projection_status: str,
    section_key: str,
    section: dict[str, Any],
) -> dict[str, Any]:
    return build_inspector_view_projection_root(
        schema_version=schema_version,
        trace_id=bundle.get("trace_id"),
        backend_session_id=str(bundle.get("backend_session_id") or session_id),
        world_engine_story_session_id=bundle.get("world_engine_story_session_id"),
        projection_status=projection_status,
        section_key=section_key,
        section=section,
        warnings=list(bundle.get("degraded_path_signals") or []),
        raw_evidence_refs={
            "source": "world_engine_diagnostics_session_bridge",
        },
    )
