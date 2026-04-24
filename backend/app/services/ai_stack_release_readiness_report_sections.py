"""Release-Readiness-Payload-Bausteine (DS-020)."""

from __future__ import annotations

from typing import Any

from app.services.ai_stack_release_readiness_report_payload_parts import (
    build_release_readiness_area_rows,
    build_release_readiness_static_tail,
)


def assemble_release_readiness_report_payload(
    *,
    trace_id: str,
    writers_room_review: dict[str, Any] | None,
    improvement_package: dict[str, Any] | None,
) -> dict[str, Any]:
    """Honest multi-area readiness: no proxying story-runtime signals from Writers-Room artifacts."""

    areas, decision_support = build_release_readiness_area_rows(
        writers_room_review=writers_room_review,
        improvement_package=improvement_package,
    )
    overall = "ready" if all(area["status"] == "closed" for area in areas) else "partial"
    tail = build_release_readiness_static_tail(trace_id=trace_id)
    return {
        **tail,
        "overall_status": overall,
        "areas": areas,
        "decision_support": decision_support,
    }
