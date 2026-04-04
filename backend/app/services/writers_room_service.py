from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from story_runtime_core import RoutingPolicy
from story_runtime_core.adapters import build_default_model_adapters
from story_runtime_core.model_registry import build_default_registry
from wos_ai_stack import (
    build_runtime_retriever,
    build_seed_writers_room_graph,
    create_default_capability_registry,
)


@dataclass
class _WritersRoomWorkflow:
    capability_registry: Any
    routing: RoutingPolicy
    adapters: dict[str, Any]
    seed_graph: Any


_WORKFLOW: _WritersRoomWorkflow | None = None


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
    )
    return _WORKFLOW


def run_writers_room_review(*, module_id: str, focus: str, actor_id: str) -> dict[str, Any]:
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
    routing_decision = workflow.routing.choose(task_type="narrative_generation")
    selected_provider = routing_decision.selected_provider or "mock"
    adapter = workflow.adapters.get(selected_provider)
    prompt = (
        f"Writers-Room review for module={module_id}.\n"
        f"Focus: {focus}\n"
        f"Use evidence from retrieved context and produce concise recommendations.\n\n"
        f"{context_payload['context_text']}"
    )
    generation = {"provider": selected_provider, "success": False, "content": "", "error": None}
    if adapter:
        call = adapter.generate(prompt, timeout_seconds=12.0, retrieval_context=context_payload["context_text"])
        generation["success"] = call.success
        generation["content"] = call.content
        generation["error"] = call.metadata.get("error") if not call.success else None
    if not generation["success"]:
        fallback = workflow.adapters.get("mock")
        if fallback:
            call = fallback.generate(prompt, timeout_seconds=5.0, retrieval_context=context_payload["context_text"])
            generation["provider"] = "mock"
            generation["success"] = call.success
            generation["content"] = call.content
            generation["error"] = call.metadata.get("error") if not call.success else None

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
    if generation["content"]:
        recommendations.append(generation["content"][:220])

    review_bundle = workflow.capability_registry.invoke(
        name="wos.review_bundle.build",
        mode="writers_room",
        actor=f"writers_room:{actor_id}",
        payload={
            "module_id": module_id,
            "summary": f"Writers-Room review for {module_id} with focus '{focus}'.",
            "recommendations": recommendations,
            "evidence_sources": [source.get("source_path", "") for source in sources],
        },
    )

    return {
        "canonical_flow": "writers_room_unified_stack_workflow",
        "module_id": module_id,
        "focus": focus,
        "workflow_seed": seed,
        "retrieval": context_payload["retrieval"],
        "issues": issues,
        "recommendations": recommendations,
        "model_generation": generation,
        "review_bundle": review_bundle,
        "outputs_are_recommendations_only": True,
        "legacy_paths": [
            {
                "path": "writers-room legacy oracle route",
                "status": "transitional",
                "message": "Legacy direct chat is deprecated and no longer canonical.",
            }
        ],
        "capability_audit": workflow.capability_registry.recent_audit(limit=20),
        "stack_components": {
            "retrieval": "wos.context_pack.build",
            "orchestration": "langgraph_seed_writers_room_graph",
            "capabilities": ["wos.context_pack.build", "wos.review_bundle.build"],
            "model_routing": "story_runtime_core.RoutingPolicy",
        },
    }
