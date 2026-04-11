"""Process-wide Writers Room workflow singleton (DS-002 optional extraction)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from story_runtime_core.adapters import build_default_model_adapters
from app.runtime.model_routing_contracts import AdapterModelSpec
from app.services.writers_room_model_routing import build_writers_room_model_route_specs
from ai_stack import (
    build_capability_tool_bridge,
    build_langchain_retriever_bridge,
    build_runtime_retriever,
    build_seed_writers_room_graph,
    create_default_capability_registry,
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
