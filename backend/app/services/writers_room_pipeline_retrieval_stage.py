"""Writers Room workflow — retrieval / context-pack stage (DS-002 stage 2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.contracts.writers_room_artifact_class import (
    WritersRoomArtifactClass,
    build_writers_room_artifact_record,
)
from ai_stack import build_retrieval_trace

from app.services.writers_room_pipeline_context_preview import _context_fingerprint
from app.services.writers_room_pipeline_manifest import _append_workflow_stage


@dataclass(frozen=True)
class WritersRoomRetrievalStageResult:
    """Outputs of intake → seed → context retrieval through context fingerprint."""

    seed: Any
    context_payload: dict[str, Any]
    retrieval_inner: Any
    source_rows: list[dict[str, Any]]
    early_evidence_paths: list[str]
    retrieval_trace: dict[str, Any]
    evidence_tag: str
    retrieval_text: str
    ctx_fingerprint: str


def run_writers_room_retrieval_stage(
    *,
    seed_graph: Any,
    capability_registry: Any,
    module_id: str,
    focus: str,
    actor_id: str,
    manifest_stages: list[dict[str, Any]],
) -> WritersRoomRetrievalStageResult:
    """Run request intake, workflow seed, and context-pack retrieval; build retrieval trace."""
    _append_workflow_stage(manifest_stages, stage_id="request_intake")
    seed = seed_graph.invoke({"module_id": module_id})
    _append_workflow_stage(manifest_stages, stage_id="workflow_seed", artifact_key="workflow_seed")
    raw_payload = capability_registry.invoke(
        name="wos.context_pack.build",
        mode="writers_room",
        actor=f"writers_room:{actor_id}",
        payload={
            "domain": "writers_room",
            "profile": "writers_review",
            "query": f"{module_id} {focus} canon consistency dramaturgy structure",
            "module_id": module_id,
            "max_chunks": 6,
        },
    )
    context_payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}
    _append_workflow_stage(manifest_stages, stage_id="retrieval_analysis", artifact_key="retrieval")
    retrieval_inner = context_payload.get("retrieval")
    sources_early = retrieval_inner.get("sources", []) if isinstance(retrieval_inner, dict) else []
    source_rows = [row for row in sources_early if isinstance(row, dict)]
    early_evidence_paths = [str(r.get("source_path", "") or "") for r in source_rows if r.get("source_path")]
    retrieval_trace = build_retrieval_trace(retrieval_inner if isinstance(retrieval_inner, dict) else {})
    retrieval_trace = {
        **retrieval_trace,
        **build_writers_room_artifact_record(
            artifact_id=f"retrieval_trace_{module_id}_{uuid4().hex[:10]}",
            artifact_class=WritersRoomArtifactClass.analysis_artifact,
            source_module_id=module_id,
            evidence_refs=early_evidence_paths[:20],
            proposal_scope="retrieval_governance_trace",
            approval_state="pending_review",
        ),
    }
    evidence_tag = retrieval_trace["evidence_tier"]
    retrieval_text = str(context_payload.get("context_text") or "")
    ctx_fingerprint = _context_fingerprint(retrieval_text)
    return WritersRoomRetrievalStageResult(
        seed=seed,
        context_payload=context_payload,
        retrieval_inner=retrieval_inner,
        source_rows=source_rows,
        early_evidence_paths=early_evidence_paths,
        retrieval_trace=retrieval_trace,
        evidence_tag=evidence_tag,
        retrieval_text=retrieval_text,
        ctx_fingerprint=ctx_fingerprint,
    )
