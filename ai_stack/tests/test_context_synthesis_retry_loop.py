from __future__ import annotations

import json
from pathlib import Path

import pytest
from story_runtime_core import RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from story_runtime_core.model_registry import build_default_registry

pytest.importorskip(
    "ai_stack.langgraph.langgraph_runtime",
    reason="LangGraph/LangChain stack required for runtime retry tests",
)
from ai_stack.context_synthesis_engine import build_context_synthesis_bundle, context_synthesis_prompt_lines
from ai_stack.langgraph.langgraph_runtime import RuntimeTurnGraphExecutor
from ai_stack.rag import ContextPackAssembler, ContextRetriever, RagIngestionPipeline


class RetryPromptCaptureAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(
        self,
        prompt: str,
        *,
        timeout_seconds: float = 10.0,
        retrieval_context: str | None = None,
        model_name: str | None = None,
    ) -> ModelCallResult:
        self.prompts.append(prompt)
        payload = {
            "schema_version": "runtime_actor_turn_v1",
            "narration_summary": "The retry keeps actor lanes inside the approved response scope.",
            "narrative_response": "The retry keeps actor lanes inside the approved response scope.",
            "primary_responder_id": "annette_reille",
            "spoken_lines": [
                {
                    "speaker_id": "annette_reille",
                    "text": "\"We are not leaving that accusation unanswered.\"",
                }
            ],
            "action_lines": [],
            "initiative_events": [],
            "state_effects": [],
        }
        return ModelCallResult(content=json.dumps(payload), success=True, metadata={"adapter": self.adapter_name})


def test_self_correction_retry_prompt_includes_context_resynthesis(tmp_path: Path) -> None:
    content_file = tmp_path / "content" / "retry_context.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("Retry synthesis context sample.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    adapter = RetryPromptCaptureAdapter()
    graph = RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=RoutingPolicy(registry),
        registry=registry,
        adapters={"openai": adapter, "mock": adapter, "ollama": adapter},
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )
    retry_bundle = build_context_synthesis_bundle(
        retrieval={
            "status": "ok",
            "hit_count": 1,
            "sources": [
                {
                    "chunk_id": "chunk-1",
                    "source_path": "content/runtime/source.md",
                    "snippet": "Bounded support for retry context.",
                    "score": "0.9000",
                    "source_evidence_lane": "canonical",
                    "source_visibility_class": "model_visible",
                }
            ],
        },
        context_text="bounded support",
        scene_assessment={"scene_core": "retry scene"},
        semantic_move_record={"move_type": "answer"},
        social_state_record={"scene_pressure_state": "active"},
        turn_aspect_ledger={"validation": {"applicable": True, "status": "partial"}},
        hierarchical_memory_context={},
        validation_feedback={"codes": ["narrator_required_missing"]},
    )
    retry_prompt = (
        "Validation Feedback Resynthesis (proposal support, non-authoritative):\n"
        + "\n".join(context_synthesis_prompt_lines(retry_bundle))
    )
    generation, _proposed, attempt = graph._self_correct_generation(
        {
            "player_input": "Answer this.",
            "interpreted_input": {"kind": "speech"},
            "context_text": "bounded support",
            "model_prompt": "Initial model prompt.",
            "routing": {"selected_model": "openai:gpt-4o-mini"},
            "selected_timeout": 10.0,
            "selected_responder_set": [{"actor_id": "annette_reille"}],
            "dramatic_generation_packet": {"selected_responder_set": [{"actor_id": "annette_reille"}]},
        },
        {"content": "Too short.", "metadata": {}},
        [],
        ["narrator_required_missing"],
        1,
        retry_context_synthesis_bundle=retry_bundle,
        retry_context_synthesis_prompt=retry_prompt,
    )

    assert adapter.prompts
    assert "Validation Feedback Resynthesis (proposal support, non-authoritative):" in adapter.prompts[-1]
    assert "address_validation_feedback" in adapter.prompts[-1]
    assert generation["metadata"].get("context_synthesis_retry_attached") is True
    assert generation["metadata"].get("context_synthesis_retry_status")
    assert attempt.get("context_synthesis_retry_attached") is True
