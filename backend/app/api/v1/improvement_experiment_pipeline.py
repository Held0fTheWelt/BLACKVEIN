"""Capability/RAG enrichment for improvement sandbox experiment (DS-016 split)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from app.contracts.improvement_operating_loop import ImprovementLoopStage
from ai_stack import build_retrieval_trace


@dataclass(frozen=True)
class ImprovementExperimentCapabilityOutcome:
    package_response: dict[str, Any]
    context_payload: dict[str, Any]
    retrieval_trace: dict[str, Any]
    transcript_meta: dict[str, Any]
    review_bundle: Any
    workflow_stages: list[dict[str, Any]]


def apply_capability_pipeline_to_improvement_package(
    *,
    experiment: dict[str, Any],
    package: dict[str, Any],
    actor_id: str,
    trace_id: str | None,
    repo_root: Path,
    capability_registry: Any,
    workflow_stages: list[dict[str, Any]],
    utc_iso: Callable[[], str],
    transcript_tool_evidence: Callable[
        ...,
        tuple[str, dict[str, Any]],
    ],
) -> ImprovementExperimentCapabilityOutcome:
    """Run context pack, transcript tool, review bundle, rationale, evidence store write."""
    context_payload = capability_registry.invoke(
        name="wos.context_pack.build",
        mode="improvement",
        actor=f"improvement:{actor_id}",
        trace_id=trace_id,
        payload={
            "domain": "improvement",
            "profile": "improvement_eval",
            "query": f"{experiment['baseline_id']} {package['candidate']['candidate_summary']} "
            "variant evaluation recommendation",
            "module_id": experiment["baseline_id"],
            "max_chunks": 5,
        },
    )
    workflow_stages.append(
        {
            "id": "retrieval_improvement_context",
            "loop_stage": ImprovementLoopStage.evidence_collection.value,
            "completed_at": utc_iso(),
            "artifact_key": "wos.context_pack.build",
        }
    )
    retrieval_inner = context_payload.get("retrieval")
    retrieval_trace = build_retrieval_trace(retrieval_inner if isinstance(retrieval_inner, dict) else {})
    evidence_tag = retrieval_trace["evidence_tier"]
    transcript_suffix, transcript_meta = transcript_tool_evidence(
        repo_root=repo_root,
        experiment=experiment,
        capability_registry=capability_registry,
        actor_id=actor_id,
        trace_id=trace_id,
    )
    workflow_stages.append(
        {
            "id": "transcript_tool_evidence",
            "loop_stage": ImprovementLoopStage.evidence_collection.value,
            "completed_at": utc_iso(),
            "artifact_key": "wos.transcript.read",
            "resource_id": transcript_meta.get("run_id"),
        }
    )
    evidence_sources = [
        source.get("source_path", "")
        for source in context_payload.get("retrieval", {}).get("sources", [])
        if isinstance(source, dict)
    ]
    package_response = dict(package)
    base_summary = str(package_response["recommendation_summary"])
    if transcript_meta.get("repetition_turn_count", 0) >= 2:
        package_response["deterministic_recommendation_base"] = "revise_before_review"
        package_response["recommendation_summary"] = "revise_before_review" + transcript_suffix
    else:
        package_response["deterministic_recommendation_base"] = base_summary
        package_response["recommendation_summary"] = base_summary + transcript_suffix
    package_response["transcript_evidence"] = transcript_meta

    from app.api.v1.improvement_experiment_pipeline_finalize import (
        finalize_improvement_experiment_capability_phase,
    )

    return finalize_improvement_experiment_capability_phase(
        package_response=package_response,
        context_payload=context_payload,
        retrieval_trace=retrieval_trace,
        retrieval_inner=retrieval_inner,
        transcript_meta=transcript_meta,
        experiment=experiment,
        evidence_sources=evidence_sources,
        capability_registry=capability_registry,
        actor_id=actor_id,
        trace_id=trace_id,
        workflow_stages=workflow_stages,
        utc_iso=utc_iso,
    )
