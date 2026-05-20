"""Writers Room finalize stage: LangChain preview and persisted workflow package dict."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.contracts.writers_room_artifact_class import (
    GOC_SHARED_SEMANTIC_CONTRACT_VERSION,
    WritersRoomArtifactClass,
    build_writers_room_artifact_record,
)
from app.services.writers_room.writers_room_pipeline_manifest import _workflow_stage_ids


def build_langchain_preview(
    *,
    module_id: str,
    langchain_documents: list[Any],
    langchain_preview_paths: list[str],
) -> dict[str, Any]:
    """Return the langchain_retriever_preview payload."""
    lc_preview: dict[str, Any] = {
        "document_count": len(langchain_documents),
        "sources": [doc.metadata.get("source_path") for doc in langchain_documents],
    }
    lc_preview.update(
        build_writers_room_artifact_record(
            artifact_id=f"langchain_preview_{module_id}_{uuid4().hex[:10]}",
            artifact_class=WritersRoomArtifactClass.analysis_artifact,
            source_module_id=module_id,
            evidence_refs=langchain_preview_paths[:10],
            proposal_scope="langchain_primary_context_preview",
            approval_state="pending_review",
        )
    )
    return lc_preview


def build_finalize_package_out(
    *,
    manifest_stages: list[dict[str, Any]],
    generation: dict[str, Any],
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
    capability_audit_rows: list[Any],
    operator_audit_wr: dict[str, Any],
    gov_truth: dict[str, Any],
    lc_preview: dict[str, Any],
) -> dict[str, Any]:
    """Assemble package_out before writers_room_artifact_manifest attachment."""
    workflow_manifest = {
        "workflow": "writers_room_unified_stack_workflow",
        "stages": manifest_stages,
    }
    workflow_stages = _workflow_stage_ids(manifest_stages)
    return {
        "canonical_flow": "writers_room_unified_stack_workflow",
        "shared_semantic_contract_version": GOC_SHARED_SEMANTIC_CONTRACT_VERSION,
        "trace_id": trace_id,
        "module_id": module_id,
        "focus": focus,
        "workflow_seed": seed,
        "workflow_manifest": workflow_manifest,
        "workflow_stages": workflow_stages,
        "review_summary": review_summary,
        "retrieval": context_payload.get("retrieval", {}),
        "retrieval_trace": retrieval_trace,
        "issues": issues,
        "recommendation_artifacts": recommendation_artifacts,
        "model_generation": generation,
        "review_bundle": review_bundle,
        "proposal_package": proposal_package,
        "comment_bundle": comment_bundle,
        "patch_candidates": patch_candidates,
        "variant_candidates": variant_candidates,
        "outputs_are_recommendations_only": True,
        "capability_audit": capability_audit_rows,
        "operator_audit": operator_audit_wr,
        "governance_truth": gov_truth,
        "langchain_retriever_preview": lc_preview,
        "stack_components": {
            "retrieval": "wos.context_pack.build",
            "orchestration": "langgraph_seed_writers_room_graph",
            "capabilities": ["wos.context_pack.build", "wos.review_bundle.build"],
            "model_routing": "app.runtime.model_routing.route_model + writers_room_model_route_specs",
            "langchain_integration": {
                "enabled": True,
                "runtime_turn_bridge": "invoke_runtime_adapter_with_langchain",
                "writers_room_generation_bridge": "invoke_writers_room_adapter_with_langchain",
                "retriever_bridge": "build_langchain_retriever_bridge",
                "writers_room_document_preview": "primary_context_pack_sources_to_langchain_documents",
                "tool_bridge": "build_capability_tool_bridge",
            },
        },
    }
