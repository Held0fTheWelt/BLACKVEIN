"""Feinsplit: Teilpayloads für Release-Readiness-Report (DS-020)."""

from __future__ import annotations

from typing import Any

from app.services.ai_stack_evidence_service import (
    _improvement_evidence_strength_map,
    _retrieval_tier_strong_enough_for_governance,
    _writers_room_retrieval_trace_tier,
)


def build_release_readiness_area_rows(
    *,
    writers_room_review: dict[str, Any] | None,
    improvement_package: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Returns (areas, decision_support_fields)."""

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

    areas = [
        {
            "area": "story_runtime_cross_layer",
            "status": "partial",
            "evidence_posture": "aggregate_only_not_session_scoped",
            "reason": (
                "This aggregate report does not inspect a live World-Engine session; "
                "use GET /admin/ai-stack/session-evidence/<id> after turns for bridged execution_truth."
            ),
        },
        {
            "area": "runtime_turn_graph_contract",
            "status": "ready",
            "evidence_posture": "repository_contract_verified_by_tests",
            "reason": (
                "Repository implements RuntimeTurnGraphExecutor with execution_health, "
                "fallback markers, and repro_metadata (verified in ai_stack/world-engine tests)."
            ),
        },
        {
            "area": "writers_room_review_artifacts",
            "status": "ready" if wr_governance_ready else "partial",
            "evidence_posture": "governance_review_state_present" if wr_governance_ready else "missing_review_state",
            "reason": "Persisted writers-room review with review_state"
            if wr_governance_ready
            else "no persisted writers-room review artifacts with review state",
        },
        {
            "area": "writers_room_retrieval_evidence_surface",
            "status": "ready" if wr_evidence_ready else "partial",
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
            "area": "writers_room_langgraph_orchestration_depth",
            "status": "partial",
            "evidence_posture": "seed_stub_intentionally_lightweight",
            "reason": (
                "Writers-Room workflow uses a LangGraph seed graph stub for workflow_seed; "
                "it is not runtime turn-graph parity (intentionally lightweight)."
            ),
        },
        {
            "area": "improvement_governance_evidence",
            "status": "ready" if improvement_governance_ready else "partial",
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
            "area": "improvement_retrieval_evidence_backing",
            "status": "ready" if improvement_retrieval_backing_ready else "partial",
            "evidence_posture": imp_backing_posture,
            "reason": imp_backing_reason,
        },
        {
            "area": "retrieval_subsystem_compact_traces",
            "status": "ready",
            "evidence_posture": "task4_trace_schema_and_calibrated_tier",
            "reason": (
                "build_retrieval_trace adds evidence_lane_mix, readiness_label, policy/dedup hints, and "
                "schema version retrieval_closure_v1; multi-hit evidence_tier is not strong-from-count alone "
                "on sparse-only or supporting-heavy packs. See docs/rag_task4_readiness_and_trace.md."
            ),
        },
    ]

    decision_support = {
        "committed_vs_diagnostic_authority": "world_engine_session_fields_and_history_vs_diagnostics_envelopes",
        "latest_writers_room_retrieval_tier": wr_rt,
        "latest_improvement_retrieval_context_class": imp_retrieval_class,
        "latest_improvement_selected_by": "max_generated_at_timestamp",
        "writers_room_review_ready_for_retrieval_graded_review": wr_evidence_ready,
        "improvement_review_ready_for_retrieval_graded_review": improvement_retrieval_backing_ready,
    }
    return areas, decision_support


def build_release_readiness_static_tail(*, trace_id: str) -> dict[str, Any]:
    """Top-level keys shared with assemble_release_readiness_report_payload."""
    retrieval_readiness_summary = {
        "trace_schema": "retrieval_closure_v1_via_build_retrieval_trace",
        "strengths": [
            "Hybrid and sparse retrieval paths with explicit degradation_mode and retrieval_route in capability payloads",
            "Source governance lanes and pack roles preserved from Task 3; traces expose lane mix and policy outcome hints",
            "Named evaluation scenarios in ai_stack/tests exercise runtime, writers_room, and improvement profiles",
        ],
        "known_degradations": [
            "Sparse-only route caps multi-hit strong tiers unless hybrid canonical/evaluative backing applies",
            "Local JSON corpus and single-host dense index; not a distributed vector service",
            "Partial dense persistence marks degraded_due_to_partial_persistence_problem and can cap evidence tiers",
        ],
        "evaluation_coverage": (
            "ai_stack/tests/test_rag.py (retrieval_eval_scenarios harness); "
            "ai_stack/tests/test_capabilities.py (build_retrieval_trace); "
            "backend tests for improvement and observability when retrieval payloads are mocked or live"
        ),
        "intentionally_deferred": [
            "External observability platform or long-term trace warehouse",
            "Full UI dashboards for retrieval analytics",
            "Cross-session retrieval quality trending",
        ],
    }
    return {
        "trace_id": trace_id,
        "retrieval_readiness_summary": retrieval_readiness_summary,
        "subsystem_maturity": [
            {
                "subsystem": "story_runtime_world_engine",
                "role": "authoritative_host",
                "maturity_note": "Committed state vs diagnostic envelopes are explicit in engine diagnostics API.",
            },
            {
                "subsystem": "writers_room_langgraph",
                "role": "workflow_seed",
                "maturity_note": "Seed graph only; orchestration depth is partial vs runtime turn graph.",
            },
            {
                "subsystem": "runtime_turn_langgraph",
                "role": "primary_turn_executor",
                "maturity_note": "Full node chain with explicit execution_health and fallback semantics.",
            },
            {
                "subsystem": "retrieval_rag_task4",
                "role": "knowledge_layer",
                "maturity_note": (
                    "Local hybrid/sparse RAG with governed lanes; compact traces (evidence_tier, lane mix, "
                    "readiness_label) for operators—no second hidden ranker in the trace layer."
                ),
            },
        ],
        "known_partiality": [
            "local_json_persistence_not_distributed",
            "no_signed_immutable_audit_store",
            "release_readiness_aggregate_does_not_substitute_for_session_evidence",
        ],
        "known_environment_sensitivities": [
            "writers_room_and_improvement_artifacts_depend_on_local_var_json_layout",
            "improvement_latest_package_requires_parseable_generated_at_iso_timestamps",
        ],
    }
