"""Writers Room retrieval → routing → generation pipeline (internal).

Public API remains in ``writers_room_service``.
"""

from __future__ import annotations

from typing import Any

from app.services.writers_room_pipeline_context_preview import (
    _context_fingerprint,
    _langchain_preview_documents_from_context_pack,
)
from app.services.writers_room_pipeline_finalize_stage import run_writers_room_finalize_stage
from app.services.writers_room_pipeline_generation_stage import (
    _norm_wr_adapter,
    run_writers_room_generation_stage,
)
from app.services.writers_room_pipeline_manifest import (
    _append_workflow_stage,
    _utc_now,
    _workflow_stage_ids,
    _writers_room_artifact_manifest,
)
from app.services.writers_room_pipeline_packaging_stage import run_writers_room_packaging_stage
from app.services.writers_room_pipeline_retrieval_stage import run_writers_room_retrieval_stage
from app.services.writers_room_pipeline_workflow import (
    _WritersRoomWorkflow,
    _WORKFLOW,
    _get_workflow,
)


def _execute_writers_room_workflow_package(
    *,
    workflow: _WritersRoomWorkflow,
    module_id: str,
    focus: str,
    actor_id: str,
    trace_id: str | None,
) -> dict[str, Any]:
    """Run retrieval, generation, packaging, finalize (audits and package_out).

    Returns workflow fields for persistence (no review_id / review_state / revision_cycles).
    """
    manifest_stages: list[dict[str, Any]] = []
    rv = run_writers_room_retrieval_stage(
        seed_graph=workflow.seed_graph,
        capability_registry=workflow.capability_registry,
        module_id=module_id,
        focus=focus,
        actor_id=actor_id,
        manifest_stages=manifest_stages,
    )
    seed = rv.seed
    context_payload = rv.context_payload
    retrieval_inner = rv.retrieval_inner
    source_rows = rv.source_rows
    early_evidence_paths = rv.early_evidence_paths
    retrieval_trace = rv.retrieval_trace
    evidence_tag = rv.evidence_tag
    retrieval_text = rv.retrieval_text
    ctx_fingerprint = rv.ctx_fingerprint

    generation = run_writers_room_generation_stage(
        adapters=workflow.adapters,
        model_route_specs=workflow.model_route_specs,
        module_id=module_id,
        focus=focus,
        retrieval_text=retrieval_text,
        evidence_tag=evidence_tag,
    ).generation
    _t2a_routing = generation.get("task_2a_routing") if isinstance(generation.get("task_2a_routing"), dict) else {}
    preflight_trace: dict[str, Any] = (
        _t2a_routing["preflight"] if isinstance(_t2a_routing.get("preflight"), dict) else {}
    )

    packaging = run_writers_room_packaging_stage(
        review_bundle_tool=workflow.review_bundle_tool,
        manifest_stages=manifest_stages,
        generation=generation,
        module_id=module_id,
        focus=focus,
        evidence_tag=evidence_tag,
        source_rows=source_rows,
        retrieval_inner=retrieval_inner,
        retrieval_trace=retrieval_trace,
        ctx_fingerprint=ctx_fingerprint,
        preflight_trace=preflight_trace,
        early_evidence_paths=early_evidence_paths,
    )
    return run_writers_room_finalize_stage(
        capability_registry=workflow.capability_registry,
        model_route_specs=workflow.model_route_specs,
        manifest_stages=manifest_stages,
        generation=generation,
        evidence_tag=evidence_tag,
        evidence_paths=packaging.evidence_paths,
        langchain_documents=packaging.langchain_documents,
        langchain_preview_paths=packaging.langchain_preview_paths,
        issues=packaging.issues,
        recommendation_artifacts=packaging.recommendation_artifacts,
        review_bundle=packaging.review_bundle,
        proposal_package=packaging.proposal_package,
        comment_bundle=packaging.comment_bundle,
        patch_candidates=packaging.patch_candidates,
        variant_candidates=packaging.variant_candidates,
        review_summary=packaging.review_summary,
        module_id=module_id,
        focus=focus,
        trace_id=trace_id,
        seed=seed,
        context_payload=context_payload,
        retrieval_trace=retrieval_trace,
    )
