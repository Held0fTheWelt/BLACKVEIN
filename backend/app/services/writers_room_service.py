from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from story_runtime_core import RoutingPolicy
from story_runtime_core.adapters import build_default_model_adapters
from story_runtime_core.model_registry import build_default_registry
from wos_ai_stack import (
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
    routing: RoutingPolicy
    adapters: dict[str, Any]
    seed_graph: Any
    langchain_retriever: Any
    review_bundle_tool: Any


_WORKFLOW: _WritersRoomWorkflow | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    registry = build_default_registry()
    _WORKFLOW = _WritersRoomWorkflow(
        capability_registry=capability_registry,
        routing=RoutingPolicy(registry),
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


def run_writers_room_review(
    *, module_id: str, focus: str, actor_id: str, trace_id: str | None = None
) -> dict[str, Any]:
    storage = WritersRoomStore.default()
    workflow = _get_workflow()
    seed = workflow.seed_graph.invoke({"module_id": module_id})
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
    retrieval_inner = context_payload.get("retrieval")
    retrieval_trace = build_retrieval_trace(retrieval_inner if isinstance(retrieval_inner, dict) else {})
    evidence_tag = retrieval_trace["evidence_tier"]
    routing_decision = workflow.routing.choose(task_type="narrative_generation")
    selected_provider = routing_decision.selected_provider or "mock"
    adapter = workflow.adapters.get(selected_provider)
    retrieval_text = str(context_payload.get("context_text") or "")
    generation: dict[str, Any] = {
        "provider": selected_provider,
        "success": False,
        "content": "",
        "error": None,
        "adapter_invocation_mode": None,
        "raw_fallback_reason": None,
        "metadata": {},
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

    sources = context_payload["retrieval"].get("sources", [])
    issues = [
        {
            "id": f"issue_{index}",
            "severity": "medium",
            "type": "consistency",
            "description": f"Review source {source['source_path']} for canon alignment in {module_id}.",
            "evidence_source": source["source_path"],
        }
        for index, source in enumerate(sources[:3], start=1)
    ]
    recommendations = [
        "Verify scene-level continuity against retrieved evidence before publishing.",
        "Prioritize contradictory characterization notes for human review.",
        "Preserve recommendation-only status until admin approval.",
    ]
    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else None
    if structured:
        for item in structured.get("recommendations") or []:
            if item:
                recommendations.append(str(item))
    if generation["content"]:
        recommendations.append(generation["content"][:220])

    review_bundle = workflow.review_bundle_tool.invoke(
        {
            "module_id": module_id,
            "summary": (
                f"[evidence_tier:{evidence_tag}] Writers-Room review for {module_id} with focus '{focus}'."
            ),
            "recommendations": recommendations,
            "evidence_sources": [source.get("source_path", "") for source in sources],
        }
    )
    langchain_documents = workflow.langchain_retriever.get_writers_room_documents(
        query=f"{module_id} {focus} canon consistency dramaturgy structure",
        module_id=module_id,
        max_chunks=3,
    )
    review_id = f"review_{uuid4().hex}"
    proposal_package = {
        "proposal_id": f"proposal_{uuid4().hex}",
        "module_id": module_id,
        "focus": focus,
        "generated_at": _utc_now(),
        "issues": issues,
        "recommendations": recommendations,
        "evidence_sources": [source.get("source_path", "") for source in sources],
    }
    comment_bundle = {
        "bundle_id": f"comments_{uuid4().hex}",
        "comments": [
            {
                "comment_id": f"comment_{idx}",
                "severity": issue["severity"],
                "text": issue["description"],
                "evidence_source": issue["evidence_source"],
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
        }
        for index, source in enumerate(sources[:2], start=1)
    ]
    variant_candidates = [
        {
            "variant_id": f"variant_{index}",
            "summary": recommendation,
        }
        for index, recommendation in enumerate(recommendations[:3], start=1)
    ]
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
        "canonical_flow": "writers_room_unified_stack_workflow",
        "trace_id": trace_id,
        "review_id": review_id,
        "module_id": module_id,
        "focus": focus,
        "workflow_seed": seed,
        "workflow_stages": [
            "analysis_completed",
            "proposal_packaged",
            "human_review_pending",
        ],
        "retrieval": context_payload["retrieval"],
        "retrieval_trace": retrieval_trace,
        "issues": issues,
        "recommendations": recommendations,
        "model_generation": generation,
        "review_bundle": review_bundle,
        "proposal_package": proposal_package,
        "comment_bundle": comment_bundle,
        "patch_candidates": patch_candidates,
        "variant_candidates": variant_candidates,
        "review_state": review_state,
        "outputs_are_recommendations_only": False,
        "legacy_paths": [
            {
                "path": "writers-room legacy oracle route",
                "status": "transitional",
                "message": "Legacy direct chat is deprecated and no longer canonical.",
            }
        ],
        "capability_audit": workflow.capability_registry.recent_audit(limit=20),
        "langchain_retriever_preview": {
            "document_count": len(langchain_documents),
            "sources": [doc.metadata.get("source_path") for doc in langchain_documents],
        },
        "stack_components": {
            "retrieval": "wos.context_pack.build",
            "orchestration": "langgraph_seed_writers_room_graph",
            "capabilities": ["wos.context_pack.build", "wos.review_bundle.build"],
            "model_routing": "story_runtime_core.RoutingPolicy",
            "langchain_integration": {
                "enabled": True,
                "runtime_turn_bridge": "invoke_runtime_adapter_with_langchain",
                "writers_room_generation_bridge": "invoke_writers_room_adapter_with_langchain",
                "retriever_bridge": "build_langchain_retriever_bridge",
                "writers_room_document_preview": "LangChainRetrieverBridge.get_writers_room_documents",
                "tool_bridge": "build_capability_tool_bridge",
            },
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
    if normalized not in {"accept", "reject"}:
        raise ValueError("decision_must_be_accept_or_reject")
    if current_status in {"accepted", "rejected"}:
        raise ValueError("review_already_finalized")
    next_status = "accepted" if normalized == "accept" else "rejected"
    history = state.get("history", [])
    if not isinstance(history, list):
        history = []
    history.append(
        {
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
