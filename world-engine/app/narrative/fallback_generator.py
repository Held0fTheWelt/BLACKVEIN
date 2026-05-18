"""Guaranteed safe fallback output path for live continuity."""

from __future__ import annotations

from app.narrative.package_models import SceneFallbackBundle
from app.narrative.runtime_output_models import RuntimeTurnStructuredOutputV2


def build_safe_fallback_output(
    *,
    fallback_bundle: SceneFallbackBundle | None,
    reason: str,
) -> RuntimeTurnStructuredOutputV2:
    """Generate explicit fallback output for blocked turns."""
    line = "Fallback: turn generation was blocked; no substitute narration was committed."
    return RuntimeTurnStructuredOutputV2(
        narrative_response=line,
        intent_summary="safe_fallback",
        responder_actor_ids=[],
        detected_triggers=[],
        conflict_vector="",
        proposed_state_effects=[],
        confidence=1.0,
        blocked_turn_reason=reason,
    )
