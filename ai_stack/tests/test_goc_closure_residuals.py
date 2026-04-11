"""Residual closure tests: operator projection, seam markers, scene_assessment schema, §3.6, YAML authority."""

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
from ai_stack.goc_frozen_vocab import DIRECTOR_IMMUTABLE_FIELDS, GOC_MODULE_ID
from ai_stack.goc_turn_seams import build_operator_canonical_turn_record, strip_director_overwrites_from_structured_output
from ai_stack.goc_yaml_authority import (
    cached_goc_yaml_title,
    clear_goc_yaml_slice_cache,
    detect_builtin_yaml_title_conflict,
)
from ai_stack.langgraph_runtime import RuntimeTurnGraphExecutor
from ai_stack.rag import ContextPackAssembler, ContextRetriever, RagIngestionPipeline
from ai_stack.scene_director_goc import goc_scene_assessment_has_minimal_fields

HOST_OK = {"template_id": "god_of_carnage_solo", "title": "God of Carnage"}


class JsonAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def __init__(self, narrative: str) -> None:
        self._narrative = narrative

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        payload = {
            "narrative_response": self._narrative,
            "proposed_scene_id": None,
            "intent_summary": "closure_residual_fixture",
        }
        return ModelCallResult(
            content=json.dumps(payload),
            success=True,
            metadata={"adapter": self.adapter_name},
        )


class GoodCommitAdapter(BaseModelAdapter):
    """Narrative that passes dramatic alignment for non-preview path."""

    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        payload = {
            "narrative_response": (
                "Annette meets your stare and admits what she knew; the truth she withheld about "
                "the children finally surfaces as she confesses the hidden fact."
            ),
            "proposed_scene_id": None,
            "intent_summary": "closure_good",
        }
        return ModelCallResult(
            content=json.dumps(payload),
            success=True,
            metadata={"adapter": self.adapter_name},
        )


def _executor(tmp_path: Path, *, openai: BaseModelAdapter | None = None) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage closure residual corpus.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    adapter = openai or GoodCommitAdapter()
    return RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters={"mock": adapter, "openai": adapter, "ollama": adapter},
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )


@pytest.fixture(autouse=True)
def _clear_goc_caches() -> None:
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()
    yield
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()


def test_build_operator_canonical_turn_record_shape(tmp_path: Path) -> None:
    graph = _executor(tmp_path)
    result = graph.run(
        session_id="s-closure-proj",
        module_id=GOC_MODULE_ID,
        current_scene_id="living_room",
        player_input="I press Annette on why she withheld the truth.",
        trace_id="trace-closure-proj",
        host_experience_template=HOST_OK,
    )
    rec = build_operator_canonical_turn_record(result)
    assert rec["turn_metadata"]["module_id"] == GOC_MODULE_ID
    assert rec["turn_metadata"]["trace_id"] == "trace-closure-proj"
    assert "interpreted_move" in rec
    assert "validation_outcome" in rec
    assert "graph_diagnostics_summary" in rec
    assert rec["graph_diagnostics_summary"].get("graph_name")
    assert isinstance(rec["graph_diagnostics_summary"].get("nodes_executed"), list)


def test_non_preview_productive_path_experiment_preview_false_when_validation_approved(tmp_path: Path) -> None:
    graph = _executor(tmp_path)
    result = graph.run(
        session_id="s-closure-preview",
        module_id=GOC_MODULE_ID,
        current_scene_id="living_room",
        player_input="I press Annette on why she withheld the truth.",
        trace_id="trace-closure-preview",
        host_experience_template=HOST_OK,
    )
    vo = result.get("validation_outcome") or {}
    assert vo.get("status") == "approved"
    assert vo.get("validator_lane") == "goc_rule_engine_v1"
    assert result.get("experiment_preview") is False
    cr = result.get("committed_result") or {}
    assert cr.get("commit_lane") == "goc_commit_seam_v1"


def test_validation_reject_records_failure_marker_and_preview(tmp_path: Path) -> None:
    fluff = (
        "The atmosphere thickens with unspoken tension as everyone senses something shifting beneath "
        "the polite surface; the mood deepens and a sense of uneasy anticipation fills the space."
    )
    graph = _executor(tmp_path, openai=JsonAdapter(fluff))
    result = graph.run(
        session_id="s-closure-reject",
        module_id=GOC_MODULE_ID,
        current_scene_id="living_room",
        player_input="I am furious and want to fight you right now.",
        trace_id="trace-closure-reject",
        host_experience_template=HOST_OK,
    )
    assert (result.get("validation_outcome") or {}).get("status") == "rejected"
    assert result.get("experiment_preview") is True
    markers = result.get("failure_markers") or []
    assert any(
        isinstance(m, dict) and m.get("failure_class") == "validation_reject" for m in markers
    )
    vrm = next(m for m in markers if isinstance(m, dict) and m.get("failure_class") == "validation_reject")
    assert vrm.get("closure_impacting") is False


def test_goc_scene_assessment_minimal_schema_on_resolved_yaml_path(tmp_path: Path) -> None:
    graph = _executor(tmp_path)
    result = graph.run(
        session_id="s-closure-sa",
        module_id=GOC_MODULE_ID,
        current_scene_id="living_room",
        player_input="Hello at the table.",
        trace_id="trace-closure-sa",
        host_experience_template=HOST_OK,
    )
    sa = result.get("scene_assessment")
    assert goc_scene_assessment_has_minimal_fields(sa if isinstance(sa, dict) else None)
    assert isinstance(sa, dict)
    assert str(sa.get("scene_core", "")).startswith("goc_scene:")


def test_strip_director_overwrites_all_immutable_fields() -> None:
    dirty: dict = {"narrative_response": "x"}
    for field in DIRECTOR_IMMUTABLE_FIELDS:
        if field == "silence_brevity_decision":
            dirty[field] = {"mode": "brief", "reason": "test"}
        elif field == "selected_responder_set":
            dirty[field] = [{"actor_id": "x", "reason": "y"}]
        else:
            dirty[field] = "tamper"
    cleaned, markers = strip_director_overwrites_from_structured_output(dirty)
    assert cleaned is not None
    for field in DIRECTOR_IMMUTABLE_FIELDS:
        assert field not in cleaned
    assert len(markers) == len(DIRECTOR_IMMUTABLE_FIELDS)


def test_detect_builtin_yaml_title_conflict_none_when_aligned() -> None:
    canonical = cached_goc_yaml_title()
    assert (
        detect_builtin_yaml_title_conflict(
            host_template_id="god_of_carnage_solo",
            host_template_title=canonical,
        )
        is None
    )


def test_detect_builtin_yaml_title_conflict_when_mismatched() -> None:
    conflict = detect_builtin_yaml_title_conflict(
        host_template_id="god_of_carnage_solo",
        host_template_title="Definitely Not Canonical",
    )
    assert conflict is not None
    assert conflict.get("failure_class") == "scope_breach"
    assert conflict.get("note") == "builtins_yaml_title_mismatch"
