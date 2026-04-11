"""Payload builders for Writers Room packaging stage (DS-002 — further extractions).

Keeps ``run_writers_room_packaging_stage`` as a thin orchestrator; same shapes/keys as inline logic.
"""

from __future__ import annotations

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


def structured_output_from_generation(generation: dict[str, Any]) -> dict[str, Any] | None:
    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else None
    return structured


def model_confidence_descriptor(generation: dict[str, Any]) -> str:
    if structured_output_from_generation(generation):
        return "structured_output_present"
    if generation.get("content"):
        return "raw_generation_only"
    return "no_model_content"


def evidence_paths_from_source_rows(source_rows: list[dict[str, Any]]) -> list[str]:
    return [row.get("source_path", "") for row in source_rows]


def retrieval_hit_count(
    source_rows: list[dict[str, Any]],
    retrieval_inner: Any,
) -> int:
    retrieval_hit_count = len(source_rows)
    if isinstance(retrieval_inner, dict):
        raw_hits = retrieval_inner.get("hit_count")
        if raw_hits is not None:
            try:
                retrieval_hit_count = int(raw_hits)
            except (TypeError, ValueError):
                retrieval_hit_count = len(source_rows)
    return retrieval_hit_count


def review_bundle_tool_input(
    *,
    module_id: str,
    focus: str,
    evidence_tag: str,
    source_rows: list[dict[str, Any]],
    recommendation_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "module_id": module_id,
        "summary": (
            f"[evidence_tier:{evidence_tag}] Writers-Room review for {module_id} with focus '{focus}'."
        ),
        "recommendations": [r["body"] for r in recommendation_artifacts],
        "evidence_sources": [row.get("source_path", "") for row in source_rows],
    }


def seal_review_bundle_with_governance_envelope(
    review_bundle: Any,
    *,
    manifest_stages: list[dict[str, Any]],
    module_id: str,
    evidence_paths: list[str],
) -> dict[str, Any]:
    _append_workflow_stage(manifest_stages, stage_id="governance_envelope", artifact_key="review_bundle")
    if not isinstance(review_bundle, dict):
        sealed: dict[str, Any] = {}
    else:
        sealed = dict(review_bundle)
    _rb_id = str(sealed.get("bundle_id") or f"bundle_pending_{uuid4().hex[:10]}")
    sealed.update(
        build_writers_room_artifact_record(
            artifact_id=_rb_id,
            artifact_class=WritersRoomArtifactClass.proposal_artifact,
            source_module_id=module_id,
            evidence_refs=[p for p in evidence_paths if p][:20],
            proposal_scope="review_bundle_envelope",
            approval_state="pending_review",
        )
    )
    return sealed


def langchain_preview_bundle(retrieval_inner: Any) -> tuple[list[Any], Any, list[str]]:
    langchain_documents, langchain_preview_source = _langchain_preview_documents_from_context_pack(
        retrieval_inner if isinstance(retrieval_inner, dict) else {},
        max_chunks=3,
    )
    langchain_preview_paths = [
        str(doc.metadata.get("source_path") or "")
        for doc in langchain_documents
        if doc.metadata.get("source_path")
    ]
    return langchain_documents, langchain_preview_source, langchain_preview_paths


def build_proposal_package_dict(
    *,
    proposal_id: str,
    module_id: str,
    focus: str,
    evidence_paths: list[str],
    evidence_tag: str,
    retrieval_trace: dict[str, Any],
    ctx_fingerprint: str,
    langchain_preview_paths: list[str],
    langchain_preview_source: Any,
    preflight_trace: dict[str, Any],
    issues: list[dict[str, Any]],
    recommendation_artifacts: list[dict[str, Any]],
    retrieval_hit_count: int,
    bundle_id: Any,
) -> dict[str, Any]:
    pp_meta = build_writers_room_artifact_record(
        artifact_id=proposal_id,
        artifact_class=WritersRoomArtifactClass.proposal_artifact,
        source_module_id=module_id,
        evidence_refs=[p for p in evidence_paths if p],
        proposal_scope="writers_room_proposal_package",
        approval_state="pending_review",
    )
    return {
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


def build_comment_bundle_dict(
    *,
    comment_bundle_id: str,
    module_id: str,
    evidence_paths: list[str],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
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
    return {**cb_root, "bundle_id": comment_bundle_id, "comments": comments_out}


_SEVERITY_CONFIDENCE = {"high": 0.9, "medium": 0.7, "low": 0.4}


def build_patch_candidates(
    *,
    source_rows: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    module_id: str,
    evidence_tag: str,
    bundle_id: Any,
) -> list[dict[str, Any]]:
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
                "confidence": _SEVERITY_CONFIDENCE.get(
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
    return patch_candidates


def build_variant_candidates(
    *,
    recommendation_artifacts: list[dict[str, Any]],
    structured: dict[str, Any] | None,
    module_id: str,
    rec_refs: list[str],
    evidence_paths: list[str],
) -> list[dict[str, Any]]:
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
    return variant_candidates


def build_review_summary_dict(
    *,
    proposal_id: str,
    comment_bundle_id: str,
    module_id: str,
    evidence_paths: list[str],
    evidence_tag: str,
    retrieval_hit_count: int,
    bundle_id: Any,
    review_bundle: dict[str, Any],
    issues: list[dict[str, Any]],
    recommendation_artifacts: list[dict[str, Any]],
    retrieval_trace: dict[str, Any],
    model_confidence_note: str,
) -> dict[str, Any]:
    rs_meta = build_writers_room_artifact_record(
        artifact_id=f"review_summary_{proposal_id}",
        artifact_class=WritersRoomArtifactClass.analysis_artifact,
        source_module_id=module_id,
        evidence_refs=[p for p in evidence_paths if p][:20],
        proposal_scope="review_summary_aggregate",
        approval_state="pending_review",
    )
    return {
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
