"""Feinsplit: Teilpayloads für Release-Readiness-Report (DS-020, DS-009)."""

from __future__ import annotations

from typing import Any

from app.services.ai_stack.ai_stack_release_readiness_area_rows_list import build_readiness_areas_list
from app.services.ai_stack.ai_stack_release_readiness_signal_extractors import (
    extract_improvement_readiness_signals,
    extract_writers_room_readiness_signals,
)
from app.services.ai_stack.ai_stack_release_readiness_static_tail import build_release_readiness_static_tail


def build_release_readiness_area_rows(
    *,
    writers_room_review: dict[str, Any] | None,
    improvement_package: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Returns (areas, decision_support_fields)."""
    wr = extract_writers_room_readiness_signals(writers_room_review)
    imp = extract_improvement_readiness_signals(improvement_package)
    areas = build_readiness_areas_list(wr=wr, imp=imp, improvement_package=improvement_package)
    decision_support = {
        "committed_vs_diagnostic_authority": "world_engine_session_fields_and_history_vs_diagnostics_envelopes",
        "latest_writers_room_retrieval_tier": wr["wr_rt"],
        "latest_improvement_retrieval_context_class": imp["imp_retrieval_class"],
        "latest_improvement_selected_by": "max_generated_at_timestamp",
        "writers_room_review_ready_for_retrieval_graded_review": wr["wr_evidence_ready"],
        "improvement_review_ready_for_retrieval_graded_review": imp["improvement_retrieval_backing_ready"],
    }
    return areas, decision_support


# Re-export: Aufrufer importieren weiterhin aus report_payload_parts.
__all__ = ["build_release_readiness_area_rows", "build_release_readiness_static_tail"]
