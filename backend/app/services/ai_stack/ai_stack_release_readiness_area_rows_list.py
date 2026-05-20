"""Standard release-readiness area row payloads from precomputed signals (DS-009)."""

from __future__ import annotations

from typing import Any


def build_readiness_areas_list(
    *,
    wr: dict[str, Any],
    imp: dict[str, Any],
    improvement_package: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    wr_governance_ready = wr["wr_governance_ready"]
    wr_rt = wr["wr_rt"]
    wr_has_trace = wr["wr_has_trace"]
    wr_evidence_ready = wr["wr_evidence_ready"]
    wr_evidence_posture = wr["wr_evidence_posture"]
    improvement_governance_ready = imp["improvement_governance_ready"]
    improvement_retrieval_backing_ready = imp["improvement_retrieval_backing_ready"]
    imp_backing_reason = imp["imp_backing_reason"]
    imp_backing_posture = imp["imp_backing_posture"]

    return [
        {
            "gate_id": "story_runtime_cross_layer",
            "status": "partial",
            "truth_source": "static_policy",
            "evidence_posture": "aggregate_only_not_session_scoped",
            "reason": (
                "This aggregate report does not inspect a live World-Engine session; "
                "use GET /admin/ai-stack/session-evidence/<id> after turns for bridged execution_truth."
            ),
        },
        {
            "gate_id": "runtime_turn_graph_contract",
            "status": "closed",
            "truth_source": "static_policy",
            "evidence_posture": "repository_contract_verified_by_tests",
            "reason": (
                "Repository implements RuntimeTurnGraphExecutor with execution_health, "
                "fallback markers, and repro_metadata (verified in ai_stack/world-engine tests)."
            ),
        },
        {
            "gate_id": "writers_room_review_artifacts",
            "status": "closed" if wr_governance_ready else "partial",
            "truth_source": "static_policy",
            "evidence_posture": "governance_review_state_present" if wr_governance_ready else "missing_review_state",
            "reason": "Persisted writers-room review with review_state"
            if wr_governance_ready
            else "no persisted writers-room review artifacts with review state",
        },
        {
            "gate_id": "writers_room_retrieval_evidence_surface",
            "status": "closed" if wr_evidence_ready else "partial",
            "truth_source": "static_policy",
            "evidence_posture": wr_evidence_posture,
            "reason": (
                "Latest writers-room review has retrieval_trace with moderate or strong evidence tier"
                if wr_evidence_ready
                else (
                    f"retrieval evidence tier is weak or none (tier={wr_rt!r}); "
                    "not treated as review-grade retrieval backing"
                    if wr_has_trace
                    else "no retrieval_trace on latest writers-room review"
                )
            ),
        },
        {
            "gate_id": "writers_room_langgraph_orchestration_depth",
            "status": "partial",
            "truth_source": "static_policy",
            "evidence_posture": "seed_stub_intentionally_lightweight",
            "reason": (
                "Writers-Room workflow uses a LangGraph seed graph stub for workflow_seed; "
                "it is not runtime turn-graph parity (intentionally lightweight)."
            ),
        },
        {
            "gate_id": "improvement_governance_evidence",
            "status": "closed" if improvement_governance_ready else "partial",
            "truth_source": "static_policy",
            "evidence_posture": (
                "comparison_and_governance_bundle_id_present"
                if improvement_governance_ready
                else "missing_comparison_or_governance_bundle_id"
            ),
            "reason": "Recommendation package includes comparison plus governance review bundle id"
            if improvement_governance_ready
            else (
                "improvement package missing governance_review_bundle_id or comparison evidence"
                if improvement_package
                else "no improvement recommendation package found"
            ),
        },
        {
            "gate_id": "improvement_retrieval_evidence_backing",
            "status": "closed" if improvement_retrieval_backing_ready else "partial",
            "truth_source": "static_policy",
            "evidence_posture": imp_backing_posture,
            "reason": imp_backing_reason,
        },
        {
            "gate_id": "retrieval_subsystem_compact_traces",
            "status": "closed",
            "truth_source": "static_policy",
            "evidence_posture": "task4_trace_schema_and_calibrated_tier",
            "reason": (
                "build_retrieval_trace adds evidence_lane_mix, readiness_label, policy/dedup hints, and "
                "schema version retrieval_closure_v1; multi-hit evidence_tier is not strong-from-count alone "
                "on sparse-only or supporting-heavy packs. See docs/rag_task4_readiness_and_trace.md."
            ),
        },
    ]
