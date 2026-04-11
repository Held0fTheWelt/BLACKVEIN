"""Review-Bundle, Rationale, Evidence-Store — zweite Phase der Improvement-Capability-Pipeline (DS-016)."""

from __future__ import annotations

from typing import Any, Callable

from app.api.v1.improvement_experiment_pipeline import ImprovementExperimentCapabilityOutcome
from app.contracts.improvement_operating_loop import ImprovementLoopStage
from app.services.improvement_service import (
    ImprovementStore,
    build_evidence_strength_map,
    build_recommendation_rationale,
    finalize_recommendation_rationale_with_retrieval_digest,
    recompute_semantic_compliance_validation,
)
from app.services.improvement_task2a_routing import enrich_improvement_package_with_task2a_routing


def finalize_improvement_experiment_capability_phase(
    *,
    package_response: dict[str, Any],
    context_payload: dict[str, Any],
    retrieval_trace: dict[str, Any],
    retrieval_inner: Any,
    transcript_meta: dict[str, Any],
    experiment: dict[str, Any],
    evidence_sources: list[str],
    capability_registry: Any,
    actor_id: str,
    trace_id: str | None,
    workflow_stages: list[dict[str, Any]],
    utc_iso: Callable[[], str],
) -> ImprovementExperimentCapabilityOutcome:
    evaluation_block = (
        package_response.get("evaluation") if isinstance(package_response.get("evaluation"), dict) else {}
    )
    evidence_bundle = dict(package_response.get("evidence_bundle") or {})
    evidence_bundle["retrieval_source_paths"] = list(evidence_sources)
    evidence_bundle["transcript_evidence"] = {
        "run_id": transcript_meta.get("run_id"),
        "turn_count": transcript_meta.get("turn_count"),
        "repetition_turn_count": transcript_meta.get("repetition_turn_count"),
        "content_length": transcript_meta.get("content_length"),
    }
    evidence_bundle["metrics_snapshot"] = evaluation_block.get("metrics")
    evidence_bundle["baseline_metrics_snapshot"] = evaluation_block.get("baseline_metrics")
    evidence_bundle["comparison_snapshot"] = evaluation_block.get("comparison")
    package_response["evidence_bundle"] = evidence_bundle

    evidence_tag = retrieval_trace["evidence_tier"]
    review_bundle = capability_registry.invoke(
        name="wos.review_bundle.build",
        mode="improvement",
        actor=f"improvement:{actor_id}",
        trace_id=trace_id,
        payload={
            "module_id": experiment["baseline_id"],
            "summary": (
                f"[evidence_tier:{evidence_tag}] [transcript:{transcript_meta.get('run_id', '')}] "
                f"Improvement recommendation for variant {experiment['variant_id']}."
            ),
            "recommendations": [package_response["recommendation_summary"]],
            "evidence_sources": evidence_sources,
        },
    )
    workflow_stages.append(
        {
            "id": "governance_review_bundle",
            "loop_stage": ImprovementLoopStage.bounded_proposal_generation.value,
            "completed_at": utc_iso(),
            "artifact_key": "wos.review_bundle.build",
            "resource_id": (review_bundle.get("bundle_id") if isinstance(review_bundle, dict) else None),
        }
    )
    evidence_bundle_final = dict(package_response["evidence_bundle"])
    if isinstance(review_bundle, dict):
        evidence_bundle_final["governance_review_bundle_id"] = review_bundle.get("bundle_id")
        evidence_bundle_final["governance_review_bundle_status"] = review_bundle.get("status")

    hit_count = len(evidence_sources)
    if isinstance(retrieval_inner, dict) and retrieval_inner.get("hit_count") is not None:
        try:
            hit_count = int(retrieval_inner["hit_count"])
        except (TypeError, ValueError):
            hit_count = len(evidence_sources)

    rationale_fresh = build_recommendation_rationale(
        evaluation=package_response["evaluation"],
        recommendation_summary=package_response["recommendation_summary"],
        retrieval_hit_count=hit_count,
        retrieval_source_paths=evidence_sources,
        transcript_meta=transcript_meta,
    )
    rationale_final = finalize_recommendation_rationale_with_retrieval_digest(
        rationale_fresh,
        context_text=str(context_payload.get("context_text") or ""),
        retrieval_source_paths=evidence_sources,
        hit_count=hit_count,
    )
    package_response["recommendation_rationale"] = rationale_final
    package_response["evidence_strength_map"] = build_evidence_strength_map(
        evaluation=package_response["evaluation"],
        retrieval_hit_count=hit_count,
        transcript_tool_ok=bool(
            transcript_meta.get("turn_count") is not None and not transcript_meta.get("tool_error")
        ),
        governance_bundle_attached=isinstance(review_bundle, dict) and bool(review_bundle.get("bundle_id")),
    )
    evidence_bundle_final["retrieval_context_fingerprint_sha256_16"] = rationale_final.get(
        "retrieval_context_fingerprint_sha256_16"
    )
    evidence_bundle_final["recommendation_driver_categories"] = [
        d.get("category")
        for d in (rationale_final.get("drivers") or [])
        if isinstance(d, dict) and d.get("category")
    ]
    evidence_bundle_final["retrieval_readiness"] = {
        "evidence_tier": retrieval_trace.get("evidence_tier"),
        "confidence_posture": retrieval_trace.get("confidence_posture"),
        "evidence_lane_mix": retrieval_trace.get("evidence_lane_mix"),
        "lane_anchor_counts": retrieval_trace.get("lane_anchor_counts"),
        "retrieval_posture_summary": retrieval_trace.get("retrieval_posture_summary"),
        "governance_influence_compact": retrieval_trace.get("governance_influence_compact"),
        "readiness_label": retrieval_trace.get("readiness_label"),
        "policy_outcome_hint": retrieval_trace.get("policy_outcome_hint"),
        "retrieval_quality_hint": retrieval_trace.get("retrieval_quality_hint"),
        "retrieval_trace_schema_version": retrieval_trace.get("retrieval_trace_schema_version"),
    }

    package_response["evidence_bundle"] = evidence_bundle_final
    enrich_improvement_package_with_task2a_routing(
        package_response,
        context_text=str(context_payload.get("context_text") or ""),
        baseline_id=experiment["baseline_id"],
        variant_id=experiment["variant_id"],
    )
    workflow_stages.append(
        {
            "id": "semantic_compliance_validation",
            "loop_stage": ImprovementLoopStage.semantic_compliance_validation.value,
            "completed_at": utc_iso(),
            "artifact_key": "semantic_compliance_validation",
            "resource_id": package_response.get("package_id"),
        }
    )
    package_response["workflow_stages"] = workflow_stages
    recompute_semantic_compliance_validation(package_response)
    ImprovementStore.default().write_json(
        "recommendations",
        str(package_response["package_id"]),
        package_response,
    )

    return ImprovementExperimentCapabilityOutcome(
        package_response=package_response,
        context_payload=context_payload,
        retrieval_trace=retrieval_trace,
        transcript_meta=transcript_meta,
        review_bundle=review_bundle,
        workflow_stages=workflow_stages,
    )
