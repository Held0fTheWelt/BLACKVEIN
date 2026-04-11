"""Writers Room workflow — issues, recommendations, review bundle, proposal package (DS-002 stage 4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.contracts.writers_room_artifact_class import (
    WritersRoomArtifactClass,
    build_writers_room_artifact_record,
)

from app.services.writers_room_pipeline_context_preview import (
    _langchain_preview_documents_from_context_pack,
)
from app.services.writers_room_pipeline_manifest import _append_workflow_stage, _utc_now


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
    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else None
    model_confidence_note = (
        "structured_output_present"
        if structured
        else ("raw_generation_only" if generation.get("content") else "no_model_content")
    )

    issues: list[dict[str, Any]] = []
    for index, source in enumerate(source_rows[:3], start=1):
        path = str(source.get("source_path", "") or "")
        ib = build_writers_room_artifact_record(
            artifact_id=f"issue_{index}",
            artifact_class=WritersRoomArtifactClass.analysis_artifact,
            source_module_id=module_id,
            evidence_refs=[path] if path else [],
            proposal_scope="retrieval_linked_issue",
            approval_state="pending_review",
        )
        issues.append(
            {
                **ib,
                "id": ib["artifact_id"],
                "severity": "medium",
                "type": "consistency",
                "description": f"Review source {path} for canon alignment in {module_id}.",
                "evidence_source": path,
                "linked_source_path": path,
                "evidence_tier": evidence_tag,
                "confidence_kind": "retrieval_heuristic",
                "revision_sensitivity": "high" if evidence_tag in {"strong", "moderate"} else "standard",
                "rationale": f"Issue derived from ranked retrieval hit for {path or 'unknown'}.",
            }
        )

    _append_workflow_stage(manifest_stages, stage_id="artifact_packaging")
    proposal_id = f"proposal_{uuid4().hex}"
    comment_bundle_id = f"comments_{uuid4().hex}"

    recommendation_texts = [
        "Verify scene-level continuity against retrieved evidence before publishing.",
        "Prioritize contradictory characterization notes for human review.",
        "Preserve recommendation-only status until admin approval.",
    ]
    if structured:
        for item in structured.get("recommendations") or []:
            if item:
                recommendation_texts.append(str(item))
    if generation["content"]:
        recommendation_texts.append(generation["content"][:220])

    evidence_paths = [row.get("source_path", "") for row in source_rows]
    rec_refs = [p for p in evidence_paths if p][:5]
    recommendation_artifacts: list[dict[str, Any]] = []
    for idx, body in enumerate(recommendation_texts, start=1):
        rid = f"rec_{proposal_id}_{idx}"
        recommendation_artifacts.append(
            {
                **build_writers_room_artifact_record(
                    artifact_id=rid,
                    artifact_class=WritersRoomArtifactClass.analysis_artifact,
                    source_module_id=module_id,
                    evidence_refs=list(rec_refs),
                    proposal_scope="writers_room_bounded_recommendation",
                    approval_state="pending_review",
                ),
                "body": body,
            }
        )

    review_bundle = review_bundle_tool.invoke(
        {
            "module_id": module_id,
            "summary": (
                f"[evidence_tier:{evidence_tag}] Writers-Room review for {module_id} with focus '{focus}'."
            ),
            "recommendations": [r["body"] for r in recommendation_artifacts],
            "evidence_sources": [row.get("source_path", "") for row in source_rows],
        }
    )
    _append_workflow_stage(manifest_stages, stage_id="governance_envelope", artifact_key="review_bundle")
    if not isinstance(review_bundle, dict):
        review_bundle = {}
    else:
        review_bundle = dict(review_bundle)
    _rb_id = str(review_bundle.get("bundle_id") or f"bundle_pending_{uuid4().hex[:10]}")
    review_bundle.update(
        build_writers_room_artifact_record(
            artifact_id=_rb_id,
            artifact_class=WritersRoomArtifactClass.proposal_artifact,
            source_module_id=module_id,
            evidence_refs=[p for p in evidence_paths if p][:20],
            proposal_scope="review_bundle_envelope",
            approval_state="pending_review",
        )
    )
    bundle_id = review_bundle.get("bundle_id")

    langchain_documents, langchain_preview_source = _langchain_preview_documents_from_context_pack(
        retrieval_inner if isinstance(retrieval_inner, dict) else {},
        max_chunks=3,
    )
    langchain_preview_paths = [
        str(doc.metadata.get("source_path") or "")
        for doc in langchain_documents
        if doc.metadata.get("source_path")
    ]
    _append_workflow_stage(manifest_stages, stage_id="retrieval_bridge_preview", artifact_key="langchain_retriever_preview")

    retrieval_hit_count = len(source_rows)
    if isinstance(retrieval_inner, dict):
        raw_hits = retrieval_inner.get("hit_count")
        if raw_hits is not None:
            try:
                retrieval_hit_count = int(raw_hits)
            except (TypeError, ValueError):
                retrieval_hit_count = len(source_rows)

    pp_meta = build_writers_room_artifact_record(
        artifact_id=proposal_id,
        artifact_class=WritersRoomArtifactClass.proposal_artifact,
        source_module_id=module_id,
        evidence_refs=[p for p in evidence_paths if p],
        proposal_scope="writers_room_proposal_package",
        approval_state="pending_review",
    )
    proposal_package = {
        **pp_meta,
        "proposal_id": proposal_id,
        "module_id": module_id,
        "focus": focus,
        "generated_at": _utc_now(),
        "issues": issues,
        "recommendation_artifacts": recommendation_artifacts,
        "evidence_sources": evidence_paths,
        "retrieval_digest": {
            "hit_count": retrieval_hit_count,
            "evidence_tier": evidence_tag,
            "evidence_strength": retrieval_trace.get("evidence_strength", evidence_tag),
            "top_source_paths": evidence_paths[:5],
            "context_fingerprint_sha256_16": ctx_fingerprint,
            "langchain_preview_source": langchain_preview_source,
            "writers_room_preflight_called": bool(preflight_trace.get("bounded_model_call")),
            "writers_room_preflight_excerpt": (preflight_trace.get("content_excerpt") or "")[:400],
        },
        "langchain_preview_paths": langchain_preview_paths,
        "governance_readiness": {
            "outputs_are_recommendations_only": True,
            "review_bundle_id": bundle_id,
            "evidence_source_paths_count": len([p for p in evidence_paths if p]),
            "langchain_preview_path_count": len(langchain_preview_paths),
            "checklist": [
                {
                    "id": "cross_check_retrieval",
                    "status": "required",
                    "detail": "Confirm issues and patch hints match cited source paths.",
                },
                {
                    "id": "admin_publish_gate",
                    "status": "required",
                    "detail": "No automatic publish; route through administration governance.",
                },
            ],
        },
    }
    cb_root = build_writers_room_artifact_record(
        artifact_id=comment_bundle_id,
        artifact_class=WritersRoomArtifactClass.analysis_artifact,
        source_module_id=module_id,
        evidence_refs=[p for p in evidence_paths if p][:20],
        proposal_scope="comment_bundle_aggregate",
        approval_state="pending_review",
    )
    comments_out: list[dict[str, Any]] = []
    for idx, issue in enumerate(issues, start=1):
        path = str(issue.get("evidence_source", "") or "")
        cm = build_writers_room_artifact_record(
            artifact_id=f"comment_{comment_bundle_id}_{idx}",
            artifact_class=WritersRoomArtifactClass.analysis_artifact,
            source_module_id=module_id,
            evidence_refs=[path] if path else [],
            proposal_scope="comment_thread_item",
            approval_state="pending_review",
        )
        comments_out.append(
            {
                **cm,
                "comment_id": f"comment_{idx}",
                "severity": issue["severity"],
                "text": issue["description"],
                "evidence_source": issue["evidence_source"],
                "evidence_tier": issue.get("evidence_tier"),
            }
        )
    comment_bundle = {**cb_root, "bundle_id": comment_bundle_id, "comments": comments_out}
    _severity_confidence = {"high": 0.9, "medium": 0.7, "low": 0.4}
    patch_candidates: list[dict[str, Any]] = []
    for index, source in enumerate(source_rows[:2], start=1):
        spath = str(source.get("source_path", "") or "")
        pb = build_writers_room_artifact_record(
            artifact_id=f"patch_{index}",
            artifact_class=WritersRoomArtifactClass.candidate_authored_artifact,
            source_module_id=module_id,
            evidence_refs=[spath] if spath else [],
            proposal_scope="patch_candidate_hint",
            approval_state="pending_review",
        )
        patch_candidates.append(
            {
                **pb,
                "candidate_id": f"patch_{index}",
                "target": spath,
                "change_hint": "Adjust wording to maintain canon consistency.",
                "preview_summary": (
                    f"Revise {source.get('source_path', 'target')} to resolve canon inconsistency "
                    f"identified during {module_id} review."
                ),
                "confidence": _severity_confidence.get(
                    issues[index - 1]["severity"] if index - 1 < len(issues) else "medium",
                    0.7,
                ),
                "confidence_kind": "retrieval_heuristic",
                "evidence_tier": evidence_tag,
                "review_bundle_id": bundle_id,
                "linked_source_path": spath,
                "rationale": f"Patch candidate anchored to retrieval path {spath!r}.",
            }
        )
    variant_candidates: list[dict[str, Any]] = []
    for index, rec_art in enumerate(recommendation_artifacts[:3], start=1):
        vb = build_writers_room_artifact_record(
            artifact_id=f"variant_{index}",
            artifact_class=WritersRoomArtifactClass.candidate_authored_artifact,
            source_module_id=module_id,
            evidence_refs=list(rec_refs),
            proposal_scope="variant_candidate_summary",
            approval_state="pending_review",
        )
        variant_candidates.append(
            {
                **vb,
                "variant_id": f"variant_{index}",
                "summary": rec_art.get("body", ""),
                "evidence_anchor": evidence_paths[0] if evidence_paths else "",
                "confidence": 0.55 if index > 1 else 0.62,
                "confidence_kind": "model_structured" if structured and index == 1 else "workflow_default",
                "revision_sensitivity": "standard",
            }
        )
    rs_meta = build_writers_room_artifact_record(
        artifact_id=f"review_summary_{proposal_id}",
        artifact_class=WritersRoomArtifactClass.analysis_artifact,
        source_module_id=module_id,
        evidence_refs=[p for p in evidence_paths if p][:20],
        proposal_scope="review_summary_aggregate",
        approval_state="pending_review",
    )
    review_summary = {
        **rs_meta,
        "issue_count": len(issues),
        "recommendation_count": len(recommendation_artifacts),
        "evidence_tier": evidence_tag,
        "retrieval_hit_count": retrieval_hit_count,
        "bundle_id": bundle_id,
        "bundle_status": review_bundle.get("status") if isinstance(review_bundle, dict) else None,
        "top_issue_ids": [issue["id"] for issue in issues[:3]],
        "proposal_id": proposal_id,
        "comment_bundle_id": comment_bundle_id,
        "evidence_strength": retrieval_trace.get("evidence_strength", evidence_tag),
        "model_output_descriptor": model_confidence_note,
        "review_checkpoint": {
            "verify_retrieval_alignment": True,
            "verify_governance_bundle": bundle_id is not None,
            "verify_recommendation_only_semantics": True,
            "notes": "Evidence strength reflects retrieval tier; model output confidence is described separately.",
        },
    }
    _append_workflow_stage(manifest_stages, stage_id="human_review_pending", artifact_key="review_state")

    return WritersRoomPackagingStageResult(
        issues=issues,
        recommendation_artifacts=recommendation_artifacts,
        review_bundle=review_bundle,
        proposal_package=proposal_package,
        comment_bundle=comment_bundle,
        patch_candidates=patch_candidates,
        variant_candidates=variant_candidates,
        review_summary=review_summary,
        langchain_documents=langchain_documents,
        langchain_preview_paths=langchain_preview_paths,
        evidence_paths=evidence_paths,
    )
