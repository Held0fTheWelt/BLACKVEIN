"""Feinsplit: Kernlogik für Inspector-Projektions-Sektionen (optional, nach DS-018/040)."""

from __future__ import annotations

from typing import Any

from app.contracts.inspector_turn_projection import make_supported_section, make_unavailable_section
from app.services.inspector_turn_projection_sections_constants import COMPARISON_RESERVED_FIELDS
from app.services.inspector_turn_projection_sections_assembly_filled import assemble_filled_inspector_sections
from app.services.inspector_turn_projection_sections_gate_payload import gate_projection_payload


def build_inspector_projection_sections_when_missing_inputs() -> dict[str, dict[str, Any]]:
    missing_reason = "no_turn_diagnostics_for_session"
    return {
        "turn_identity": make_unavailable_section(reason=missing_reason),
        "planner_state_projection": make_unavailable_section(reason=missing_reason),
        "decision_trace_projection": make_unavailable_section(reason=missing_reason),
        "gate_projection": make_unavailable_section(reason=missing_reason),
        "validation_projection": make_unavailable_section(reason=missing_reason),
        "authority_projection": make_unavailable_section(reason=missing_reason),
        "fallback_projection": make_unavailable_section(reason=missing_reason),
        "provenance_projection": make_unavailable_section(reason=missing_reason),
        "comparison_ready_fields": make_supported_section(
            {
                "supported_now": [],
                "reserved_for_future": list(COMPARISON_RESERVED_FIELDS),
                "status_note": "comparison engine not implemented in m1",
            }
        ),
    }


def build_inspector_projection_sections_filled(
    *,
    bundle: dict[str, Any],
    canonical_record: dict[str, Any],
    last_turn: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return assemble_filled_inspector_sections(
        bundle=bundle, canonical_record=canonical_record, last_turn=last_turn
    )


__all__ = [
    "gate_projection_payload",
    "build_inspector_projection_sections_when_missing_inputs",
    "build_inspector_projection_sections_filled",
]
