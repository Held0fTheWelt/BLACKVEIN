"""Gate-Payload-Normalisierung für Inspector-Projektion."""

from __future__ import annotations

from typing import Any

from app.services.inspector_turn_projection_sections_constants import GATE_SCORE_SUMMARY_KEYS


def gate_projection_payload(gate_outcome: dict[str, Any]) -> dict[str, Any]:
    """Canonical dramatic-effect pass-through with score-only fields isolated."""
    score_summary: dict[str, Any] = {}
    canonical: dict[str, Any] = {}
    for key, value in gate_outcome.items():
        if key in GATE_SCORE_SUMMARY_KEYS:
            score_summary[key] = value
        else:
            canonical[key] = value
    if score_summary:
        canonical["score_summary"] = score_summary
    return canonical
