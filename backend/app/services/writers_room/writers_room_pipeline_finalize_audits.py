"""Writers Room finalize stage — capability rows, operator audit, governance truth snapshot."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.contracts.writers_room_artifact_class import (
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


def build_finalize_audits_and_governance_truth(
    *,
    capability_registry: Any,
    model_route_specs: list[AdapterModelSpec],
    generation: dict[str, Any],
    module_id: str,
    evidence_tag: str,
    evidence_paths: list[Any],
) -> tuple[list[Any], dict[str, Any], dict[str, Any]]:
    """Return capability audit rows, enriched operator audit, and governance_truth dict."""
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
    gov_truth: dict[str, Any] = {
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
    return capability_audit_rows, operator_audit_wr, gov_truth
