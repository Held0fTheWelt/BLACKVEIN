"""Writers-room and improvement readiness signals for release-readiness area rows (DS-009)."""

from __future__ import annotations

from typing import Any

from app.services.ai_stack_evidence_internals import (
    _improvement_evidence_strength_map,
    _retrieval_tier_strong_enough_for_governance,
    _writers_room_retrieval_trace_tier,
)


def extract_writers_room_readiness_signals(
    writers_room_review: dict[str, Any] | None,
) -> dict[str, Any]:
    wr_governance_ready = bool(
        writers_room_review and (writers_room_review.get("review_state") or {}).get("status")
    )
    wr_rt = _writers_room_retrieval_trace_tier(writers_room_review)
    wr_has_trace = bool(
        writers_room_review and isinstance(writers_room_review.get("retrieval_trace"), dict)
    )
    wr_evidence_ready = bool(wr_has_trace and _retrieval_tier_strong_enough_for_governance(wr_rt))
    wr_evidence_posture = (
        "missing_retrieval_trace"
        if not wr_has_trace
        else (
            "strong_enough_for_review"
            if _retrieval_tier_strong_enough_for_governance(wr_rt)
            else f"weak_retrieval_tier:{wr_rt}"
        )
    )
    return {
        "wr_governance_ready": wr_governance_ready,
        "wr_rt": wr_rt,
        "wr_has_trace": wr_has_trace,
        "wr_evidence_ready": wr_evidence_ready,
        "wr_evidence_posture": wr_evidence_posture,
    }


def extract_improvement_readiness_signals(
    improvement_package: dict[str, Any] | None,
) -> dict[str, Any]:
    improvement_ready = bool(
        improvement_package and (improvement_package.get("evidence_bundle") or {}).get("comparison")
    )
    improvement_governance_ready = bool(
        improvement_ready
        and (improvement_package.get("evidence_bundle") or {}).get("governance_review_bundle_id")
    )
    imp_map = _improvement_evidence_strength_map(improvement_package)
    imp_retrieval_class = imp_map.get("retrieval_context") if imp_map else None
    improvement_retrieval_backing_ready = bool(
        improvement_package and imp_map is not None and imp_retrieval_class not in (None, "none")
    )
    if not improvement_package:
        imp_backing_reason = "no improvement recommendation package found"
        imp_backing_posture = "no_package"
    elif imp_map is None:
        imp_backing_reason = "latest package has no evidence_strength_map (legacy or incomplete)"
        imp_backing_posture = "missing_strength_map"
    elif imp_retrieval_class == "none":
        imp_backing_reason = (
            "latest package has governance artifacts but retrieval_context strength is none "
            "(recommendation not materially retrieval-backed)"
        )
        imp_backing_posture = "weak_retrieval_backing"
    else:
        imp_backing_reason = "retrieval_context strength is not none on latest package"
        imp_backing_posture = "retrieval_backed"
    return {
        "improvement_ready": improvement_ready,
        "improvement_governance_ready": improvement_governance_ready,
        "imp_map": imp_map,
        "imp_retrieval_class": imp_retrieval_class,
        "improvement_retrieval_backing_ready": improvement_retrieval_backing_ready,
        "imp_backing_reason": imp_backing_reason,
        "imp_backing_posture": imp_backing_posture,
    }
