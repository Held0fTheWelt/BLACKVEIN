"""Explicit roadmap-aligned retrieval-heavy corridor (gate G9 evidence prep).

Roadmap §6.9 scenario 6 requires retrieval-heavy context. Other phase tests always
construct a corpus; this test names the scenario and asserts governance visibility
on a multi-file corpus so the audit anchor is explicit.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from story_runtime_core import RoutingPolicy, interpret_player_input
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from story_runtime_core.model_registry import build_default_registry

pytest.importorskip(
    "ai_stack.langgraph_runtime",
    reason="LangGraph/LangChain stack required for GoC runtime graph tests",
)
from ai_stack.langgraph_runtime import RuntimeTurnGraphExecutor
from ai_stack.rag import ContextPackAssembler, ContextRetriever, RagIngestionPipeline
from ai_stack.goc_gate_evaluation import gate_turn_integrity
from ai_stack.goc_turn_seams import build_roadmap_dramatic_turn_record
from ai_stack.goc_g9_roadmap_scenarios import ROADMAP_SCENARIO_ID_RETRIEVAL_HEAVY
from ai_stack.goc_yaml_authority import cached_goc_yaml_title, clear_goc_yaml_slice_cache, load_goc_canonical_module_yaml

HOST_OK = {"template_id": "god_of_carnage_solo", "title": "God of Carnage"}


class _JsonAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def __init__(self, narrative: str) -> None:
        self._narrative = narrative

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        payload = {
            "narrative_response": self._narrative,
            "proposed_scene_id": None,
            "intent_summary": "retrieval_heavy_fixture",
        }
        return ModelCallResult(
            content=json.dumps(payload),
            success=True,
            metadata={"adapter": self._narrative, "retrieval_context_attached": bool(retrieval_context)},
        )


@pytest.fixture(autouse=True)
def _clear_goc_caches() -> None:
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()
    yield
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()


def test_roadmap_scenario_retrieval_heavy_governance_visible(tmp_path: Path) -> None:
    load_goc_canonical_module_yaml()
    content_dir = tmp_path / "content"
    content_dir.mkdir(parents=True)
    for i in range(10):
        (content_dir / f"goc_segment_{i:02d}.md").write_text(
            "God of Carnage dinner-table escalation and retrieval segment "
            f"{i}: Veronique, Michel, Annette, Alain — moral injury and civility.\n",
            encoding="utf-8",
        )
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    adapter = _JsonAdapter(
        "Michel's voice rises at the table; he demands you explain why you insulted him and justify "
        "your motive while blame stays sharp, the room tight and quiet as retrieved notes on prior insults shape the moment."
    )
    merged = {"mock": adapter, "openai": adapter, "ollama": adapter}
    graph = RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters=merged,
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )
    result = graph.run(
        session_id=f"s-{ROADMAP_SCENARIO_ID_RETRIEVAL_HEAVY}",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Explain what everyone at this table already knows from the written record about the incident.",
        trace_id="trace-roadmap-s6-retrieval-heavy",
        host_experience_template=HOST_OK,
    )
    assert result.get("experiment_preview") is False
    assert gate_turn_integrity(result) == "pass"
    retrieval = result.get("retrieval") or {}
    rgs = retrieval.get("retrieval_governance_summary")
    assert isinstance(rgs, dict), "retrieval_governance_summary must be attached for operator visibility"
    assert rgs.get("retrieval_policy_version")
    assert int(rgs.get("source_row_count") or 0) >= 1
    assert retrieval.get("hit_count", 0) >= 1
    assert rgs.get("authored_truth_refs") is not None
    assert rgs.get("derived_artifact_refs") is not None
    dtr = build_roadmap_dramatic_turn_record(result)
    rr = dtr.get("retrieval_record") or {}
    assert rr.get("authored_truth_refs") == rgs.get("authored_truth_refs")
    assert rr.get("derived_artifact_refs") == rgs.get("derived_artifact_refs")
