"""Writers Room workflow — manifest assembly, audits, governance snapshot, package_out (DS-002 stage 5)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.contracts.writers_room_artifact_class import (
    GOC_SHARED_SEMANTIC_CONTRACT_VERSION,
    WritersRoomArtifactClass,
    build_writers_room_artifact_record,
)
from app.runtime.area2_operator_truth import (
    bounded_traces_from_task_2a_routing,
    enrich_operator_audit_with_area2_truth,
    resolve_routing_bootstrap_enabled,
)
from app.runtime.area2_routing_authority import AUTHORITY_SOURCE_WRITERS_ROOM
from app.runtime.model_routing_contracts import AdapterModelSpec
from app.runtime.operator_audit import build_bounded_surface_operator_audit
from app.services.writers_room_pipeline_manifest import (
    _workflow_stage_ids,
    _writers_room_artifact_manifest,
)


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
    workflow_manifest = {
        "workflow": "writers_room_unified_stack_workflow",
        "stages": manifest_stages,
    }
    workflow_stages = _workflow_stage_ids(manifest_stages)

    capability_audit_rows = capability_registry.recent_audit(limit=20)
    t2a_routing = generation.get("task_2a_routing") if isinstance(generation.get("task_2a_routing"), dict) else {}
    operator_audit_wr = build_bounded_surface_operator_audit(
        surface="writers_room",
        task_2a_routing=t2a_routing,
        execution_hints={
            "adapter_invocation_mode": generation.get("adapter_invocation_mode"),
            "raw_fallback_reason": generation.get("raw_fallback_reason"),
            "executed_provider": generation.get("provider"),
        },
    )
    enrich_operator_audit_with_area2_truth(
        operator_audit_wr,
        surface="writers_room",
        authority_source=AUTHORITY_SOURCE_WRITERS_ROOM,
        bootstrap_enabled=resolve_routing_bootstrap_enabled(),
        registry_model_spec_count=len(model_route_specs),
        specs_for_coverage=list(model_route_specs),
        bounded_traces=bounded_traces_from_task_2a_routing(t2a_routing),
    )
    gov_truth = {
        "retrieval_evidence_tier": evidence_tag,
        "model_generation_path": generation.get("adapter_invocation_mode"),
        "capabilities_invoked": [
            row.get("capability_name")
            for row in capability_audit_rows
            if isinstance(row, dict) and isinstance(row.get("capability_name"), str)
        ],
        "langgraph_orchestration_depth": "seed_graph_stub",
        "outputs_are_recommendations_only": True,
    }
    gov_truth.update(
        build_writers_room_artifact_record(
            artifact_id=f"governance_truth_{module_id}_{uuid4().hex[:10]}",
            artifact_class=WritersRoomArtifactClass.analysis_artifact,
            source_module_id=module_id,
            evidence_refs=[p for p in evidence_paths if p][:20],
            proposal_scope="writers_room_operational_governance_snapshot",
            approval_state="pending_review",
        )
    )
    lc_preview = {
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
    legacy_notice = {
        **build_writers_room_artifact_record(
            artifact_id="notice_legacy_oracle_route",
            artifact_class=WritersRoomArtifactClass.analysis_artifact,
            source_module_id=module_id,
            evidence_refs=[],
            proposal_scope="deprecation_policy_notice",
            approval_state="not_applicable",
        ),
        "body": "Legacy direct chat is deprecated and no longer canonical.",
    }
    package_out: dict[str, Any] = {
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
        "legacy_paths": [legacy_notice],
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
    package_out["writers_room_artifact_manifest"] = _writers_room_artifact_manifest(package_out)
    return package_out
