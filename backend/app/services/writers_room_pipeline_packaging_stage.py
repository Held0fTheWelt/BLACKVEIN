"""Writers Room workflow — issues, recommendations, review bundle, proposal package (DS-002 stage 4).

DS-002: Payload assembly in ``writers_room_pipeline_packaging_payloads``; early/tail orchestration
split into module-private phases for a smaller ``run_writers_room_packaging_stage`` surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.contracts.writers_room_artifact_class import (
    WritersRoomArtifactClass,
    build_writers_room_artifact_record,
)

from app.services.writers_room_pipeline_manifest import _append_workflow_stage
from app.services.writers_room_pipeline_packaging_issue_extraction import (
    extract_issues_from_packaging,
)
from app.services.writers_room_pipeline_packaging_payloads import (
    build_comment_bundle_dict,
    build_patch_candidates,
    build_proposal_package_dict,
    build_review_summary_dict,
    build_variant_candidates,
    evidence_paths_from_source_rows,
    langchain_preview_bundle,
    model_confidence_descriptor,
    retrieval_hit_count,
    review_bundle_tool_input,
    seal_review_bundle_with_governance_envelope,
    structured_output_from_generation,
)
from app.services.writers_room_pipeline_packaging_recommendation_bundling import (
    bundle_recommendations_from_output,
)


@dataclass(frozen=True)
class WritersRoomPackagingStageResult:
    issues: list[dict[str, Any]]
    recommendation_artifacts: list[dict[str, Any]]
    review_bundle: dict[str, Any]
    proposal_package: dict[str, Any]
    comment_bundle: dict[str, Any]
    patch_candidates: list[dict[str, Any]]
    variant_candidates: list[dict[str, Any]]
    review_summary: dict[str, Any]
    langchain_documents: list[Any]
    langchain_preview_paths: list[str]
    evidence_paths: list[Any]


@dataclass(frozen=True)
class _PackagingEarlyPhase:
    model_confidence_note: str
    structured: dict[str, Any] | None
    issues: list[dict[str, Any]]
    proposal_id: str
    comment_bundle_id: str
    evidence_paths: list[str]
    rec_refs: list[str]
    recommendation_artifacts: list[dict[str, Any]]
    review_bundle: dict[str, Any]
    bundle_id: Any


def _run_packaging_early_through_review(
    *,
    review_bundle_tool: Any,
    manifest_stages: list[dict[str, Any]],
    generation: dict[str, Any],
    module_id: str,
    focus: str,
    evidence_tag: str,
    source_rows: list[dict[str, Any]],
    early_evidence_paths: list[str],
) -> _PackagingEarlyPhase:
    _append_workflow_stage(manifest_stages, stage_id="proposal_generation", artifact_key="model_generation")
    generation.update(
        build_writers_room_artifact_record(
            artifact_id=f"model_gen_{uuid4().hex[:16]}",
            artifact_class=WritersRoomArtifactClass.analysis_artifact,
            source_module_id=module_id,
            evidence_refs=early_evidence_paths[:20],
            proposal_scope="bounded_model_generation_trace",
            approval_state="pending_review",
        )
    )
    model_confidence_note = model_confidence_descriptor(generation)
    structured = structured_output_from_generation(generation)
    issues = extract_issues_from_packaging(
        source_rows=source_rows,
        module_id=module_id,
        evidence_tag=evidence_tag,
    )
    _append_workflow_stage(manifest_stages, stage_id="artifact_packaging")
    proposal_id = f"proposal_{uuid4().hex}"
    comment_bundle_id = f"comments_{uuid4().hex}"
    evidence_paths = evidence_paths_from_source_rows(source_rows)
    rec_refs = [p for p in evidence_paths if p][:5]
    recommendation_artifacts = bundle_recommendations_from_output(
        structured=structured,
        generation=generation,
        proposal_id=proposal_id,
        module_id=module_id,
        evidence_paths=evidence_paths,
    )
    raw_review = review_bundle_tool.invoke(
        review_bundle_tool_input(
            module_id=module_id,
            focus=focus,
            evidence_tag=evidence_tag,
            source_rows=source_rows,
            recommendation_artifacts=recommendation_artifacts,
        )
    )
    review_bundle = seal_review_bundle_with_governance_envelope(
        raw_review,
        manifest_stages=manifest_stages,
        module_id=module_id,
        evidence_paths=evidence_paths,
    )
    bundle_id = review_bundle.get("bundle_id")
    return _PackagingEarlyPhase(
        model_confidence_note=model_confidence_note,
        structured=structured,
        issues=issues,
        proposal_id=proposal_id,
        comment_bundle_id=comment_bundle_id,
        evidence_paths=evidence_paths,
        rec_refs=rec_refs,
        recommendation_artifacts=recommendation_artifacts,
        review_bundle=review_bundle,
        bundle_id=bundle_id,
    )


@dataclass(frozen=True)
class _PackagingTailPayloads:
    proposal_package: dict[str, Any]
    comment_bundle: dict[str, Any]
    patch_candidates: list[dict[str, Any]]
    variant_candidates: list[dict[str, Any]]
    review_summary: dict[str, Any]
    langchain_documents: list[Any]
    langchain_preview_paths: list[str]


def _build_packaging_tail_payloads(
    *,
    early: _PackagingEarlyPhase,
    manifest_stages: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    retrieval_inner: Any,
    retrieval_trace: dict[str, Any],
    ctx_fingerprint: str,
    preflight_trace: dict[str, Any],
    module_id: str,
    focus: str,
    evidence_tag: str,
) -> _PackagingTailPayloads:
    langchain_documents, langchain_preview_source, langchain_preview_paths = langchain_preview_bundle(
        retrieval_inner
    )
    _append_workflow_stage(
        manifest_stages, stage_id="retrieval_bridge_preview", artifact_key="langchain_retriever_preview"
    )
    hit_count = retrieval_hit_count(source_rows, retrieval_inner)
    proposal_package = build_proposal_package_dict(
        proposal_id=early.proposal_id,
        module_id=module_id,
        focus=focus,
        evidence_paths=early.evidence_paths,
        evidence_tag=evidence_tag,
        retrieval_trace=retrieval_trace,
        ctx_fingerprint=ctx_fingerprint,
        langchain_preview_paths=langchain_preview_paths,
        langchain_preview_source=langchain_preview_source,
        preflight_trace=preflight_trace,
        issues=early.issues,
        recommendation_artifacts=early.recommendation_artifacts,
        retrieval_hit_count=hit_count,
        bundle_id=early.bundle_id,
    )
    comment_bundle = build_comment_bundle_dict(
        comment_bundle_id=early.comment_bundle_id,
        module_id=module_id,
        evidence_paths=early.evidence_paths,
        issues=early.issues,
    )
    patch_candidates = build_patch_candidates(
        source_rows=source_rows,
        issues=early.issues,
        module_id=module_id,
        evidence_tag=evidence_tag,
        bundle_id=early.bundle_id,
    )
    variant_candidates = build_variant_candidates(
        recommendation_artifacts=early.recommendation_artifacts,
        structured=early.structured,
        module_id=module_id,
        rec_refs=early.rec_refs,
        evidence_paths=early.evidence_paths,
    )
    review_summary = build_review_summary_dict(
        proposal_id=early.proposal_id,
        comment_bundle_id=early.comment_bundle_id,
        module_id=module_id,
        evidence_paths=early.evidence_paths,
        evidence_tag=evidence_tag,
        retrieval_hit_count=hit_count,
        bundle_id=early.bundle_id,
        review_bundle=early.review_bundle,
        issues=early.issues,
        recommendation_artifacts=early.recommendation_artifacts,
        retrieval_trace=retrieval_trace,
        model_confidence_note=early.model_confidence_note,
    )
    return _PackagingTailPayloads(
        proposal_package=proposal_package,
        comment_bundle=comment_bundle,
        patch_candidates=patch_candidates,
        variant_candidates=variant_candidates,
        review_summary=review_summary,
        langchain_documents=langchain_documents,
        langchain_preview_paths=langchain_preview_paths,
    )


def run_writers_room_packaging_stage(
    *,
    review_bundle_tool: Any,
    manifest_stages: list[dict[str, Any]],
    generation: dict[str, Any],
    module_id: str,
    focus: str,
    evidence_tag: str,
    source_rows: list[dict[str, Any]],
    retrieval_inner: Any,
    retrieval_trace: dict[str, Any],
    ctx_fingerprint: str,
    preflight_trace: dict[str, Any],
    early_evidence_paths: list[str],
) -> WritersRoomPackagingStageResult:
    """Stamp model generation artifact, build issues/recommendations, review bundle, proposal package, summaries."""
    early = _run_packaging_early_through_review(
        review_bundle_tool=review_bundle_tool,
        manifest_stages=manifest_stages,
        generation=generation,
        module_id=module_id,
        focus=focus,
        evidence_tag=evidence_tag,
        source_rows=source_rows,
        early_evidence_paths=early_evidence_paths,
    )
    tail = _build_packaging_tail_payloads(
        early=early,
        manifest_stages=manifest_stages,
        source_rows=source_rows,
        retrieval_inner=retrieval_inner,
        retrieval_trace=retrieval_trace,
        ctx_fingerprint=ctx_fingerprint,
        preflight_trace=preflight_trace,
        module_id=module_id,
        focus=focus,
        evidence_tag=evidence_tag,
    )
    _append_workflow_stage(manifest_stages, stage_id="human_review_pending", artifact_key="review_state")

    return WritersRoomPackagingStageResult(
        issues=early.issues,
        recommendation_artifacts=early.recommendation_artifacts,
        review_bundle=early.review_bundle,
        proposal_package=tail.proposal_package,
        comment_bundle=tail.comment_bundle,
        patch_candidates=tail.patch_candidates,
        variant_candidates=tail.variant_candidates,
        review_summary=tail.review_summary,
        langchain_documents=tail.langchain_documents,
        langchain_preview_paths=tail.langchain_preview_paths,
        evidence_paths=early.evidence_paths,
    )
