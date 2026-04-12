"""Review-Bundle, Rationale, Evidence-Store — zweite Phase der Improvement-Capability-Pipeline (DS-016)."""

from __future__ import annotations

from typing import Any, Callable

from app.api.v1.improvement_experiment_pipeline_types import ImprovementExperimentCapabilityOutcome
from app.api.v1.improvement_experiment_pipeline_finalize_phases import (
    apply_rationale_strength_and_final_evidence_bundle,
    enrich_validate_and_store_package,
    hydrate_evidence_bundle_from_evaluation,
    invoke_governance_review_bundle,
)


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
    hydrate_evidence_bundle_from_evaluation(
        package_response,
        evidence_sources=evidence_sources,
        transcript_meta=transcript_meta,
    )
    evidence_tag = retrieval_trace["evidence_tier"]
    review_bundle = invoke_governance_review_bundle(
        package_response=package_response,
        experiment=experiment,
        evidence_sources=evidence_sources,
        evidence_tag=evidence_tag,
        transcript_meta=transcript_meta,
        actor_id=actor_id,
        trace_id=trace_id,
        capability_registry=capability_registry,
        workflow_stages=workflow_stages,
        utc_iso=utc_iso,
    )
    apply_rationale_strength_and_final_evidence_bundle(
        package_response,
        context_payload=context_payload,
        retrieval_trace=retrieval_trace,
        retrieval_inner=retrieval_inner,
        transcript_meta=transcript_meta,
        evidence_sources=evidence_sources,
        review_bundle=review_bundle,
    )
    enrich_validate_and_store_package(
        package_response,
        context_payload=context_payload,
        experiment=experiment,
        workflow_stages=workflow_stages,
        utc_iso=utc_iso,
    )

    return ImprovementExperimentCapabilityOutcome(
        package_response=package_response,
        context_payload=context_payload,
        retrieval_trace=retrieval_trace,
        transcript_meta=transcript_meta,
        review_bundle=review_bundle,
        workflow_stages=workflow_stages,
    )
