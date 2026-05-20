"""Writers Room workflow — manifest assembly, audits, governance snapshot, package_out (DS-002 stage 5)."""

from __future__ import annotations

from typing import Any

from app.runtime.model_routing_contracts import AdapterModelSpec
from app.services.writers_room.writers_room_pipeline_finalize_audits import build_finalize_audits_and_governance_truth
from app.services.writers_room.writers_room_pipeline_finalize_package_out import (
    build_finalize_package_out,
    build_langchain_preview,
)
from app.services.writers_room.writers_room_pipeline_manifest import _writers_room_artifact_manifest


def run_writers_room_finalize_stage(
    *,
    capability_registry: Any,
    model_route_specs: list[AdapterModelSpec],
    manifest_stages: list[dict[str, Any]],
    generation: dict[str, Any],
    evidence_tag: str,
    evidence_paths: list[Any],
    langchain_documents: list[Any],
    langchain_preview_paths: list[str],
    issues: list[dict[str, Any]],
    recommendation_artifacts: list[dict[str, Any]],
    review_bundle: dict[str, Any],
    proposal_package: dict[str, Any],
    comment_bundle: dict[str, Any],
    patch_candidates: list[dict[str, Any]],
    variant_candidates: list[dict[str, Any]],
    review_summary: dict[str, Any],
    module_id: str,
    focus: str,
    trace_id: str | None,
    seed: Any,
    context_payload: dict[str, Any],
    retrieval_trace: dict[str, Any],
) -> dict[str, Any]:
    """Build workflow_manifest, operator/capability audits, previews, and the persisted workflow package dict."""
    capability_audit_rows, operator_audit_wr, gov_truth = build_finalize_audits_and_governance_truth(
        capability_registry=capability_registry,
        model_route_specs=model_route_specs,
        generation=generation,
        module_id=module_id,
        evidence_tag=evidence_tag,
        evidence_paths=evidence_paths,
    )
    lc_preview = build_langchain_preview(
        module_id=module_id,
        langchain_documents=langchain_documents,
        langchain_preview_paths=langchain_preview_paths,
    )
    package_out = build_finalize_package_out(
        manifest_stages=manifest_stages,
        generation=generation,
        issues=issues,
        recommendation_artifacts=recommendation_artifacts,
        review_bundle=review_bundle,
        proposal_package=proposal_package,
        comment_bundle=comment_bundle,
        patch_candidates=patch_candidates,
        variant_candidates=variant_candidates,
        review_summary=review_summary,
        module_id=module_id,
        focus=focus,
        trace_id=trace_id,
        seed=seed,
        context_payload=context_payload,
        retrieval_trace=retrieval_trace,
        capability_audit_rows=capability_audit_rows,
        operator_audit_wr=operator_audit_wr,
        gov_truth=gov_truth,
        lc_preview=lc_preview,
    )
    package_out["writers_room_artifact_manifest"] = _writers_room_artifact_manifest(package_out)
    return package_out
