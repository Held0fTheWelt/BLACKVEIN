"""Gate-Payload-Normalisierung für Inspector-Projektion."""

from __future__ import annotations

from typing import Any

from app.services.inspector_turn_projection_sections_constants import LEGACY_GATE_SUMMARY_KEYS


def gate_projection_payload(gate_outcome: dict[str, Any]) -> dict[str, Any]:
    """Canonical dramatic-effect pass-through with legacy scores isolated."""
    legacy: dict[str, Any] = {}
    canonical: dict[str, Any] = {}
    for key, value in gate_outcome.items():
        if key in LEGACY_GATE_SUMMARY_KEYS:
            legacy[key] = value
        else:
            canonical[key] = value
    if legacy:
        canonical["legacy_compatibility_summary"] = legacy
    return canonical
