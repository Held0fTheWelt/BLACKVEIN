from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from langchain_core.documents import Document
from story_runtime_core.adapters import build_default_model_adapters
from app.runtime.model_routing import route_model
from app.runtime.model_routing_contracts import (
    AdapterModelSpec,
    LatencyBudget,
    RoutingRequest,
    TaskKind,
    WorkflowPhase,
)
from app.services.writers_room_model_routing import build_writers_room_model_route_specs
from ai_stack import (
    build_capability_tool_bridge,
    build_langchain_retriever_bridge,
    build_retrieval_trace,
    build_runtime_retriever,
    build_seed_writers_room_graph,
    create_default_capability_registry,
    invoke_writers_room_adapter_with_langchain,
)


@dataclass
class _WritersRoomWorkflow:
    capability_registry: Any
    model_route_specs: list[AdapterModelSpec]
    adapters: dict[str, Any]
    seed_graph: Any
    langchain_retriever: Any
    review_bundle_tool: Any


_WORKFLOW: _WritersRoomWorkflow | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_workflow_stage(
    manifest_stages: list[dict[str, Any]],
    *,
    stage_id: str,
    artifact_key: str | None = None,
) -> None:
    entry: dict[str, Any] = {"id": stage_id, "completed_at": _utc_now()}
    if artifact_key:
        entry["artifact_key"] = artifact_key
    manifest_stages.append(entry)


def _workflow_stage_ids(manifest_stages: list[dict[str, Any]]) -> list[str]:
    return [str(s.get("id", "")) for s in manifest_stages if isinstance(s, dict)]


def _context_fingerprint(context_text: str, *, max_bytes: int = 2048) -> str:
    sample = context_text.encode("utf-8", errors="replace")[:max_bytes]
    return hashlib.sha256(sample).hexdigest()[:16]


def _langchain_preview_documents_from_context_pack(
    retrieval_inner: dict[str, Any],
    *,
    max_chunks: int = 3,
) -> tuple[list[Document], str]:
    """Build LangChain documents from the primary ``wos.context_pack.build`` payload (no second retrieve)."""
    sources = retrieval_inner.get("sources") if isinstance(retrieval_inner, dict) else None
    if not isinstance(sources, list):
        return [], "primary_context_pack_empty"
    docs: list[Document] = []
    for row in sources[:max_chunks]:
        if not isinstance(row, dict):
            continue
        path = str(row.get("source_path") or "")
        snippet = str(row.get("snippet") or "")
        if not path and not snippet:
            continue
        docs.append(
            Document(
                page_content=snippet or "(no snippet)",
                metadata={
                    "chunk_id": row.get("chunk_id", ""),
                    "source_path": path,
                    "source_version": row.get("source_version", ""),
                    "domain": str(retrieval_inner.get("domain") or ""),
                    "content_class": row.get("content_class", ""),
                    "score": row.get("score", ""),
                    "index_version": retrieval_inner.get("index_version", ""),
                    "corpus_fingerprint": retrieval_inner.get("corpus_fingerprint", ""),
                },
            )
        )
    label = "primary_context_pack" if docs else "primary_context_pack_no_hits"
    return docs, label


@dataclass
class WritersRoomStore:
    root: Path

    @classmethod
    def default(cls) -> "WritersRoomStore":
        root = Path(__file__).resolve().parents[2] / "var" / "writers_room"
        return cls(root=root)

    def ensure_dirs(self) -> None:
        (self.root / "reviews").mkdir(parents=True, exist_ok=True)

    def write_review(self, review_id: str, payload: dict[str, Any]) -> Path:
        self.ensure_dirs()
        path = self.root / "reviews" / f"{review_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

    def read_review(self, review_id: str) -> dict[str, Any]:
        path = self.root / "reviews" / f"{review_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))


def _get_workflow() -> _WritersRoomWorkflow:
    global _WORKFLOW
    if _WORKFLOW is not None:
        return _WORKFLOW
    repo_root = Path(__file__).resolve().parents[3]
    retriever, assembler, _corpus = build_runtime_retriever(repo_root)
    capability_registry = create_default_capability_registry(
        retriever=retriever,
        assembler=assembler,
        repo_root=repo_root,
    )
    _WORKFLOW = _WritersRoomWorkflow(
        capability_registry=capability_registry,
        model_route_specs=build_writers_room_model_route_specs(),
        adapters=build_default_model_adapters(),
        seed_graph=build_seed_writers_room_graph(),
        langchain_retriever=build_langchain_retriever_bridge(retriever),
        review_bundle_tool=build_capability_tool_bridge(
            capability_registry=capability_registry,
            capability_name="wos.review_bundle.build",
            mode="writers_room",
            actor="writers_room:tool_bridge",
        ),
    )
    return _WORKFLOW


def _execute_writers_room_workflow_package(
    *,
    workflow: _WritersRoomWorkflow,
    module_id: str,
    focus: str,
    actor_id: str,
    trace_id: str | None,
) -> dict[str, Any]:
    """Run retrieval → generation → packaging → governance tool → LangChain preview.

    Returns workflow fields for persistence (no review_id / review_state / revision_cycles).
    """
    manifest_stages: list[dict[str, Any]] = []
    _append_workflow_stage(manifest_stages, stage_id="request_intake")
    seed = workflow.seed_graph.invoke({"module_id": module_id})
    _append_workflow_stage(manifest_stages, stage_id="workflow_seed", artifact_key="workflow_seed")
    context_payload = workflow.capability_registry.invoke(
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
    _append_workflow_stage(manifest_stages, stage_id="retrieval_analysis", artifact_key="retrieval")
    retrieval_inner = context_payload.get("retrieval")
    retrieval_trace = build_retrieval_trace(retrieval_inner if isinstance(retrieval_inner, dict) else {})
    evidence_tag = retrieval_trace["evidence_tier"]
    retrieval_text = str(context_payload.get("context_text") or "")
    ctx_fingerprint = _context_fingerprint(retrieval_text)

    specs = workflow.model_route_specs
    preflight_req = RoutingRequest(
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        requires_structured_output=False,
        latency_budget=LatencyBudget.strict,
    )
    pre_decision = route_model(preflight_req, specs=specs)
    preflight_trace: dict[str, Any] = {
        "stage": "preflight",
        "workflow_phase": WorkflowPhase.preflight.value,
        "task_kind": TaskKind.cheap_preflight.value,
        "decision": pre_decision.model_dump(mode="json"),
    }
    pre_adapter = (
        workflow.adapters.get(pre_decision.selected_adapter_name)
        if pre_decision.selected_adapter_name
        else None
    )
    if pre_adapter and pre_decision.selected_adapter_name:
        pre_prompt = (
            f"Writers-Room retrieval preflight for module={module_id}. "
            f"In one or two sentences, is retrieved context likely sufficient for a canon review? "
            f"(yes/no + brief reason). evidence_tier={evidence_tag}.\n"
            f"Context excerpt:\n{(retrieval_text or '')[:1800]}"
        )
        try:
            pre_call = pre_adapter.generate(
                pre_prompt, timeout_seconds=5.0, retrieval_context=retrieval_text or None
            )
            preflight_trace["bounded_model_call"] = True
            preflight_trace["adapter_key"] = pre_decision.selected_adapter_name
            preflight_trace["call_success"] = pre_call.success
            preflight_trace["content_excerpt"] = (pre_call.content or "").strip()[:500]
        except Exception as exc:  # noqa: BLE001 — bounded diagnostic; workflow continues
            preflight_trace["bounded_model_call"] = True
            preflight_trace["adapter_key"] = pre_decision.selected_adapter_name
            preflight_trace["call_error"] = str(exc)
    else:
        preflight_trace["bounded_model_call"] = False
        preflight_trace["skip_reason"] = "no_eligible_adapter_or_missing_provider_adapter"

    synthesis_req = RoutingRequest(
        workflow_phase=WorkflowPhase.generation,
        task_kind=TaskKind.narrative_formulation,
        requires_structured_output=True,
    )
    syn_decision = route_model(synthesis_req, specs=specs)
    synthesis_trace: dict[str, Any] = {
        "stage": "synthesis",
        "workflow_phase": WorkflowPhase.generation.value,
        "task_kind": TaskKind.narrative_formulation.value,
        "decision": syn_decision.model_dump(mode="json"),
    }
    selected_provider = syn_decision.selected_adapter_name or "mock"
    adapter = workflow.adapters.get(selected_provider)
    generation: dict[str, Any] = {
        "provider": selected_provider,
        "success": False,
        "content": "",
        "error": None,
        "adapter_invocation_mode": None,
        "raw_fallback_reason": None,
        "metadata": {},
        "task_2a_routing": {"preflight": preflight_trace, "synthesis": synthesis_trace},
    }
    if adapter:
        wr_result = invoke_writers_room_adapter_with_langchain(
            adapter=adapter,
            module_id=module_id,
            focus=focus,
            retrieval_context=retrieval_text or None,
            timeout_seconds=12.0,
        )
        generation["success"] = wr_result.call.success
        generation["error"] = wr_result.call.metadata.get("error") if not wr_result.call.success else None
        generation["adapter_invocation_mode"] = "langchain_structured_primary"
        if wr_result.parsed_output is not None:
            notes = (wr_result.parsed_output.review_notes or "").strip()
            generation["content"] = notes or wr_result.call.content
            generation["metadata"] = {
                "langchain_prompt_used": True,
                "langchain_parser_error": None,
                "structured_output": wr_result.parsed_output.model_dump(mode="json"),
            }
        elif wr_result.call.success:
            generation["content"] = wr_result.call.content
            generation["metadata"] = {
                "langchain_prompt_used": True,
                "langchain_parser_error": wr_result.parser_error,
                "structured_output": None,
            }
        else:
            generation["content"] = ""
            generation["metadata"] = {
                "langchain_prompt_used": True,
                "langchain_parser_error": wr_result.parser_error,
                "structured_output": None,
            }
    else:
        generation["error"] = f"adapter_not_registered:{selected_provider}"
        generation["raw_fallback_reason"] = "primary_adapter_missing"

    if not generation["success"]:
        fallback = workflow.adapters.get("mock")
        fallback_prompt = (
            f"Writers-Room review for module={module_id}.\n"
            f"Focus: {focus}\n"
            f"Use evidence from retrieved context and produce concise recommendations.\n\n"
            f"{retrieval_text}"
        )
        if fallback:
            call = fallback.generate(fallback_prompt, timeout_seconds=5.0, retrieval_context=retrieval_text or None)
            generation["provider"] = "mock"
            generation["success"] = call.success
            generation["content"] = call.content
            generation["error"] = call.metadata.get("error") if not call.success else None
            generation["adapter_invocation_mode"] = "raw_adapter_fallback"
            generation["raw_fallback_reason"] = (
                generation.get("raw_fallback_reason") or "primary_failed_or_unavailable"
            )
            generation["metadata"] = {
                "langchain_prompt_used": False,
                "langchain_parser_error": None,
                "structured_output": None,
                "bypass_note": (
                    "Mock/raw fallback skips LangChain structured parse because default mock output is not JSON; "
                    "graph-runtime primary path uses the same pattern."
                ),
            }

    _append_workflow_stage(manifest_stages, stage_id="proposal_generation", artifact_key="model_generation")
    sources = (
        context_payload.get("retrieval", {}).get("sources", [])
        if isinstance(context_payload.get("retrieval"), dict)
        else []
    )
    source_rows = [row for row in sources if isinstance(row, dict)]
    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else None
    model_confidence_note = (
        "structured_output_present"
        if structured
        else ("raw_generation_only" if generation.get("content") else "no_model_content")
    )

    issues = [
        {
            "id": f"issue_{index}",
            "severity": "medium",
            "type": "consistency",
            "description": f"Review source {source.get('source_path', '')} for canon alignment in {module_id}.",
            "evidence_source": source.get("source_path", ""),
            "linked_source_path": source.get("source_path", ""),
            "evidence_tier": evidence_tag,
            "confidence_kind": "retrieval_heuristic",
            "revision_sensitivity": "high" if evidence_tag in {"strong", "moderate"} else "standard",
            "rationale": f"Issue derived from ranked retrieval hit for {source.get('source_path', 'unknown')}.",
        }
        for index, source in enumerate(source_rows[:3], start=1)
    ]
    recommendations = [
        "Verify scene-level continuity against retrieved evidence before publishing.",
        "Prioritize contradictory characterization notes for human review.",
        "Preserve recommendation-only status until admin approval.",
    ]
    if structured:
        for item in structured.get("recommendations") or []:
            if item:
                recommendations.append(str(item))
    if generation["content"]:
        recommendations.append(generation["content"][:220])

    _append_workflow_stage(manifest_stages, stage_id="artifact_packaging")
    proposal_id = f"proposal_{uuid4().hex}"
    comment_bundle_id = f"comments_{uuid4().hex}"
    review_bundle = workflow.review_bundle_tool.invoke(
        {
            "module_id": module_id,
            "summary": (
                f"[evidence_tier:{evidence_tag}] Writers-Room review for {module_id} with focus '{focus}'."
            ),
            "recommendations": recommendations,
            "evidence_sources": [row.get("source_path", "") for row in source_rows],
        }
    )
    _append_workflow_stage(manifest_stages, stage_id="governance_envelope", artifact_key="review_bundle")
    bundle_id = review_bundle.get("bundle_id") if isinstance(review_bundle, dict) else None

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

    evidence_paths = [row.get("source_path", "") for row in source_rows]
    retrieval_hit_count = len(source_rows)
    if isinstance(retrieval_inner, dict):
        raw_hits = retrieval_inner.get("hit_count")
        if raw_hits is not None:
            try:
                retrieval_hit_count = int(raw_hits)
            except (TypeError, ValueError):
                retrieval_hit_count = len(source_rows)

    proposal_package = {
        "proposal_id": proposal_id,
        "module_id": module_id,
        "focus": focus,
        "generated_at": _utc_now(),
        "issues": issues,
        "recommendations": recommendations,
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
    comment_bundle = {
        "bundle_id": comment_bundle_id,
        "comments": [
            {
                "comment_id": f"comment_{idx}",
                "severity": issue["severity"],
                "text": issue["description"],
                "evidence_source": issue["evidence_source"],
                "evidence_tier": issue.get("evidence_tier"),
            }
            for idx, issue in enumerate(issues, start=1)
        ],
    }
    _severity_confidence = {"high": 0.9, "medium": 0.7, "low": 0.4}
    patch_candidates = [
        {
            "candidate_id": f"patch_{index}",
            "target": source.get("source_path", ""),
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
            "linked_source_path": source.get("source_path", ""),
            "rationale": f"Patch candidate anchored to retrieval path {source.get('source_path', '')!r}.",
        }
        for index, source in enumerate(source_rows[:2], start=1)
    ]
    variant_candidates = [
        {
            "variant_id": f"variant_{index}",
            "summary": recommendation,
            "evidence_anchor": evidence_paths[0] if evidence_paths else "",
            "confidence": 0.55 if index > 1 else 0.62,
            "confidence_kind": "model_structured" if structured and index == 1 else "workflow_default",
            "revision_sensitivity": "standard",
        }
        for index, recommendation in enumerate(recommendations[:3], start=1)
    ]
    review_summary = {
        "issue_count": len(issues),
        "recommendation_count": len(recommendations),
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
    workflow_manifest = {
        "workflow": "writers_room_unified_stack_workflow",
        "stages": manifest_stages,
    }
    workflow_stages = _workflow_stage_ids(manifest_stages)

    capability_audit_rows = workflow.capability_registry.recent_audit(limit=20)
    return {
        "canonical_flow": "writers_room_unified_stack_workflow",
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
        "recommendations": recommendations,
        "model_generation": generation,
        "review_bundle": review_bundle,
        "proposal_package": proposal_package,
        "comment_bundle": comment_bundle,
        "patch_candidates": patch_candidates,
        "variant_candidates": variant_candidates,
        "outputs_are_recommendations_only": True,
        "legacy_paths": [
            {
                "path": "writers-room legacy oracle route",
                "status": "transitional",
                "message": "Legacy direct chat is deprecated and no longer canonical.",
            }
        ],
        "capability_audit": capability_audit_rows,
        "governance_truth": {
            "retrieval_evidence_tier": evidence_tag,
            "model_generation_path": generation.get("adapter_invocation_mode"),
            "capabilities_invoked": [
                row.get("capability_name")
                for row in capability_audit_rows
                if isinstance(row, dict) and isinstance(row.get("capability_name"), str)
            ],
            "langgraph_orchestration_depth": "seed_graph_stub",
            "outputs_are_recommendations_only": True,
        },
        "langchain_retriever_preview": {
            "document_count": len(langchain_documents),
            "sources": [doc.metadata.get("source_path") for doc in langchain_documents],
        },
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


def run_writers_room_review(
    *, module_id: str, focus: str, actor_id: str, trace_id: str | None = None
) -> dict[str, Any]:
    storage = WritersRoomStore.default()
    workflow = _get_workflow()
    package = _execute_writers_room_workflow_package(
        workflow=workflow,
        module_id=module_id,
        focus=focus,
        actor_id=actor_id,
        trace_id=trace_id,
    )
    review_id = f"review_{uuid4().hex}"
    review_state = {
        "status": "pending_human_review",
        "updated_at": _utc_now(),
        "updated_by": actor_id,
        "history": [
            {
                "status": "pending_human_review",
                "changed_at": _utc_now(),
                "changed_by": actor_id,
                "note": "Initial workflow package created.",
            }
        ],
    }
    report = {
        **package,
        "review_id": review_id,
        "review_state": review_state,
        "revision_cycles": [],
        "artifact_provenance": {
            "kind": "writers_room_workflow_output",
            "workflow": "writers_room_unified_stack_workflow",
            "created_at": _utc_now(),
            "module_id": module_id,
            "trace_id": trace_id,
        },
    }
    storage.write_review(review_id, report)
    return report


def get_writers_room_review(*, review_id: str) -> dict[str, Any]:
    storage = WritersRoomStore.default()
    return storage.read_review(review_id)


def apply_writers_room_decision(
    *,
    review_id: str,
    actor_id: str,
    decision: str,
    note: str | None = None,
) -> dict[str, Any]:
    storage = WritersRoomStore.default()
    review = storage.read_review(review_id)
    state = review.get("review_state", {})
    current_status = str(state.get("status", "pending_human_review"))
    normalized = decision.strip().lower()
    if normalized not in {"accept", "reject", "revise"}:
        raise ValueError("decision_must_be_accept_reject_or_revise")
    if current_status in {"accepted", "rejected"}:
        raise ValueError("review_already_finalized")
    if current_status not in {"pending_human_review", "pending_revision"}:
        raise ValueError("invalid_review_state_for_decision")

    history = state.get("history", [])
    if not isinstance(history, list):
        history = []

    if normalized == "revise":
        next_status = "pending_revision"
        history.append(
            {
                "decision": "revise",
                "status": next_status,
                "changed_at": _utc_now(),
                "changed_by": actor_id,
                "note": note or "",
            }
        )
        state["status"] = next_status
        state["updated_at"] = _utc_now()
        state["updated_by"] = actor_id
        state["history"] = history
        review["review_state"] = state
        review["last_hitl_action"] = {
            "decision": "revise",
            "actor_id": actor_id,
            "acted_at": _utc_now(),
            "note": note or "",
        }
        storage.write_review(review_id, review)
        return review

    next_status = "accepted" if normalized == "accept" else "rejected"
    history.append(
        {
            "decision": normalized,
            "status": next_status,
            "changed_at": _utc_now(),
            "changed_by": actor_id,
            "note": note or "",
        }
    )
    state["status"] = next_status
    state["updated_at"] = _utc_now()
    state["updated_by"] = actor_id
    state["history"] = history
    review["review_state"] = state
    review["human_decision"] = {
        "decision": normalized,
        "decided_by": actor_id,
        "decided_at": _utc_now(),
        "note": note or "",
    }
    storage.write_review(review_id, review)
    return review


_REVISION_SNAPSHOT_KEYS = frozenset(
    {
        "proposal_package",
        "review_bundle",
        "review_summary",
        "workflow_manifest",
        "issues",
        "recommendations",
        "patch_candidates",
        "variant_candidates",
        "comment_bundle",
        "model_generation",
        "langchain_retriever_preview",
        "retrieval",
        "retrieval_trace",
    }
)


def submit_writers_room_revision(
    *,
    review_id: str,
    actor_id: str,
    focus: str | None = None,
    note: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Re-run workflow while persisting prior artifact snapshot; only from pending_revision."""
    storage = WritersRoomStore.default()
    review = storage.read_review(review_id)
    state = review.get("review_state", {})
    if str(state.get("status", "")) != "pending_revision":
        raise ValueError("revision_submit_requires_pending_revision")

    module_id = str(review.get("module_id") or "")
    if not module_id:
        raise ValueError("review_missing_module_id")

    focus_resolved = (focus or "").strip() or str(review.get("focus") or "canon consistency and dramaturgy")

    prior_snapshot = {k: review[k] for k in _REVISION_SNAPSHOT_KEYS if k in review}
    cycles = review.get("revision_cycles")
    if not isinstance(cycles, list):
        cycles = []

    workflow = _get_workflow()
    package = _execute_writers_room_workflow_package(
        workflow=workflow,
        module_id=module_id,
        focus=focus_resolved,
        actor_id=actor_id,
        trace_id=trace_id or review.get("trace_id"),
    )

    cycle_id = f"revcycle_{uuid4().hex}"
    cycles.append(
        {
            "cycle_id": cycle_id,
            "submitted_at": _utc_now(),
            "submitted_by": actor_id,
            "actor_note": note or "",
            "focus": focus_resolved,
            "prior_snapshot": prior_snapshot,
        }
    )

    merged = dict(review)
    for key, value in package.items():
        merged[key] = value
    merged["review_id"] = review_id
    merged["focus"] = focus_resolved
    merged["revision_cycles"] = cycles

    history = state.get("history", [])
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "event": "revision_submitted",
            "cycle_id": cycle_id,
            "status": "pending_human_review",
            "changed_at": _utc_now(),
            "changed_by": actor_id,
            "note": note or "",
        }
    )
    state["status"] = "pending_human_review"
    state["updated_at"] = _utc_now()
    state["updated_by"] = actor_id
    state["history"] = history
    merged["review_state"] = state
    merged.pop("human_decision", None)
    merged.pop("last_hitl_action", None)

    storage.write_review(review_id, merged)
    return merged
