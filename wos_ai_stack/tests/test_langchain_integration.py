from __future__ import annotations

from pathlib import Path

from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from wos_ai_stack import ContextRetriever, RagIngestionPipeline
from wos_ai_stack.langchain_integration import (
    build_capability_tool_bridge,
    build_langchain_retriever_bridge,
    invoke_runtime_adapter_with_langchain,
)


class JsonAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(
            content='{"narrative_response":"ok","proposed_scene_id":"scene_2","intent_summary":"advance"}',
            success=True,
            metadata={"adapter": self.adapter_name, "prompt_length": len(prompt)},
        )


class RecordingCapabilityRegistry:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def invoke(self, *, name: str, mode: str, actor: str, payload: dict) -> dict:
        self.calls.append({"name": name, "mode": mode, "actor": actor, "payload": payload})
        return {"ok": True, "payload": payload}


def test_langchain_runtime_invocation_parses_structured_output() -> None:
    adapter = JsonAdapter()
    result = invoke_runtime_adapter_with_langchain(
        adapter=adapter,
        player_input="I move to scene_2",
        interpreted_input={"kind": "action"},
        retrieval_context="scene context",
        timeout_seconds=5.0,
    )
    assert result.call.success is True
    assert result.parsed_output is not None
    assert result.parsed_output.proposed_scene_id == "scene_2"
    assert result.parser_error is None


def test_langchain_retriever_bridge_returns_documents(tmp_path: Path) -> None:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage retriever bridge context.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    bridge = build_langchain_retriever_bridge(ContextRetriever(corpus))
    docs = bridge.get_runtime_documents(query="carnage context", module_id="god_of_carnage", max_chunks=2)
    assert docs
    assert docs[0].metadata.get("source_path")


def test_langchain_tool_bridge_invokes_capability_registry() -> None:
    registry = RecordingCapabilityRegistry()
    tool = build_capability_tool_bridge(
        capability_registry=registry,
        capability_name="wos.review_bundle.build",
        mode="writers_room",
        actor="writers_room:test",
    )
    result = tool.invoke(
        {
            "module_id": "god_of_carnage",
            "summary": "s",
            "recommendations": ["r1"],
            "evidence_sources": ["content/god_of_carnage.md"],
        }
    )
    assert result["ok"] is True
    assert registry.calls
    assert registry.calls[-1]["name"] == "wos.review_bundle.build"
