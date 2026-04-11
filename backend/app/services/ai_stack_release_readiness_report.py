"""Release readiness report assembly (DS-020 split from ai_stack_evidence_service)."""

from __future__ import annotations

from typing import Any

from app.services.ai_stack_release_readiness_report_sections import assemble_release_readiness_report_payload


def build_release_readiness_report_payload(
    *,
    trace_id: str,
    writers_room_review: dict[str, Any] | None,
    improvement_package: dict[str, Any] | None,
) -> dict[str, Any]:
    return assemble_release_readiness_report_payload(
        trace_id=trace_id,
        writers_room_review=writers_room_review,
        improvement_package=improvement_package,
    )
