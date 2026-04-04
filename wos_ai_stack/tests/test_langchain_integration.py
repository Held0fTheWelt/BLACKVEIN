from __future__ import annotations

from pathlib import Path

from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from wos_ai_stack import ContextRetriever, RagIngestionPipeline
from wos_ai_stack.langchain_integration import (
    build_capability_tool_bridge,
    build_langchain_retriever_bridge,
    bridges,
    invoke_runtime_adapter_with_langchain,
    invoke_writers_room_adapter_with_langchain,
)


class JsonAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(
            content='{"narrative_response":"ok","proposed_scene_id":"scene_2","intent_summary":"advance"}',
            success=True,
            metadata={"adapter": self.adapter_name, "prompt_length": len(prompt)},
        )


class WritersRoomJsonAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(
            content=(
                '{"review_notes":"Canon alignment looks sound.","recommendations":'
                '["Tighten beat three","Check door continuity"]}'
            ),
            success=True,
            metadata={"adapter": self.adapter_name, "prompt_length": len(prompt)},
        )


class NonJsonSuccessAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(
            content="plain text, not json",
            success=True,
            metadata={"adapter": self.adapter_name},
        )


class RecordingCapabilityRegistry:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def invoke(self, *, name: str, mode: str, actor: str, payload: dict) -> dict:
        self.calls.append({"name": name, "mode": mode, "actor": actor, "payload": payload})
        return {"ok": True, "payload": payload}


def test_langchain_prompt_templates_are_module_singletons() -> None:
    rt = bridges._RUNTIME_PROMPT_TEMPLATE
    wr = bridges._WRITERS_ROOM_PROMPT_TEMPLATE
    adapter = JsonAdapter()
    invoke_runtime_adapter_with_langchain(
        adapter=adapter,
        player_input="x",
        interpreted_input={"kind": "speech"},
        retrieval_context="ctx",
        timeout_seconds=5.0,
    )
    assert bridges._RUNTIME_PROMPT_TEMPLATE is rt
    wadapter = WritersRoomJsonAdapter()
    invoke_writers_room_adapter_with_langchain(
        adapter=wadapter,
        module_id="m",
        focus="f",
        retrieval_context="c",
        timeout_seconds=5.0,
    )
    assert bridges._WRITERS_ROOM_PROMPT_TEMPLATE is wr


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


def test_langchain_writers_room_invocation_parses_structured_output() -> None:
    adapter = WritersRoomJsonAdapter()
    result = invoke_writers_room_adapter_with_langchain(
        adapter=adapter,
        module_id="god_of_carnage",
        focus="canon",
        retrieval_context="scene notes",
        timeout_seconds=5.0,
    )
    assert result.call.success is True
    assert result.parsed_output is not None
    assert "Canon" in result.parsed_output.review_notes
    assert "Tighten beat three" in result.parsed_output.recommendations
    assert result.parser_error is None


def test_langchain_writers_room_invocation_keeps_raw_content_on_parser_error() -> None:
    adapter = NonJsonSuccessAdapter()
    result = invoke_writers_room_adapter_with_langchain(
        adapter=adapter,
        module_id="m1",
        focus="structure",
        retrieval_context=None,
        timeout_seconds=5.0,
    )
    assert result.call.success is True
    assert result.parsed_output is None
    assert result.parser_error
    assert result.call.content == "plain text, not json"


def test_langchain_retriever_bridge_returns_documents(tmp_path: Path) -> None:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage retriever bridge context.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    bridge = build_langchain_retriever_bridge(ContextRetriever(corpus))
    docs = bridge.get_runtime_documents(query="carnage context", module_id="god_of_carnage", max_chunks=2)
    assert docs
    assert docs[0].metadata.get("source_path")
    assert docs[0].metadata.get("chunk_id")
    assert docs[0].metadata.get("source_version")
    assert docs[0].metadata.get("index_version")


def test_langchain_retriever_bridge_writers_room_domain(tmp_path: Path) -> None:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("Writers room canon review corpus line.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    bridge = build_langchain_retriever_bridge(ContextRetriever(corpus))
    docs = bridge.get_writers_room_documents(
        query="canon review",
        module_id="god_of_carnage",
        max_chunks=2,
    )
    assert docs
    assert docs[0].metadata.get("domain") == "writers_room"


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


def test_all_three_bridge_types_are_functional_in_same_run(tmp_path: Path) -> None:
    """Cross-path test: proves runtime adapter, retriever, and capability bridges all work together."""
    # 1. runtime adapter bridge
    adapter = JsonAdapter()
    runtime_result = invoke_runtime_adapter_with_langchain(
        adapter=adapter,
        player_input="I push the door open",
        interpreted_input={"kind": "movement"},
        retrieval_context="scene_1 context: a locked corridor",
        timeout_seconds=5.0,
    )
    assert runtime_result.call.success is True
    assert runtime_result.parsed_output is not None
    assert runtime_result.parser_error is None

    # 2. retriever bridge
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage corridor conflict scene.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever_bridge = build_langchain_retriever_bridge(ContextRetriever(corpus))
    docs = retriever_bridge.get_runtime_documents(query="corridor conflict", module_id="god_of_carnage", max_chunks=2)
    assert docs
    assert docs[0].metadata.get("source_path")

    # 3. capability tool bridge
    registry = RecordingCapabilityRegistry()
    tool = build_capability_tool_bridge(
        capability_registry=registry,
        capability_name="wos.review_bundle.build",
        mode="improvement",
        actor="improvement:test",
    )
    cap_result = tool.invoke(
        {
            "module_id": "god_of_carnage",
            "summary": "corridor scene tension",
            "recommendations": ["slow pacing"],
            "evidence_sources": ["content/god_of_carnage.md"],
        }
    )
    assert cap_result["ok"] is True
    assert registry.calls[-1]["name"] == "wos.review_bundle.build"
    assert registry.calls[-1]["mode"] == "improvement"
