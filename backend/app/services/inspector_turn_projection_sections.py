"""Inspector turn projection section assembly (DS-018 split from inspector_turn_projection_service)."""

from __future__ import annotations

from typing import Any

from app.services.inspector_turn_projection_sections_assembly import (
    build_inspector_projection_sections_filled,
    build_inspector_projection_sections_when_missing_inputs,
)


def build_inspector_projection_sections(
    *,
    bundle: dict[str, Any],
    canonical_record: dict[str, Any] | None,
    last_turn: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if canonical_record is None or last_turn is None:
        return build_inspector_projection_sections_when_missing_inputs()
    return build_inspector_projection_sections_filled(
        bundle=bundle,
        canonical_record=canonical_record,
        last_turn=last_turn,
    )
