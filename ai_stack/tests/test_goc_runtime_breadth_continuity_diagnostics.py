"""Phase 2 GoC: breadth, continuity carry-forward, anti-seductive validation, multi-pressure diagnostics."""

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
from ai_stack.goc_gate_evaluation import (
    gate_diagnostic_sufficiency,
    gate_dramatic_quality,
    gate_turn_integrity,
)
from ai_stack.goc_yaml_authority import cached_goc_yaml_title, clear_goc_yaml_slice_cache, load_goc_canonical_module_yaml


HOST_OK = {"template_id": "god_of_carnage_solo", "title": "God of Carnage"}


def _executor(tmp_path: Path, **adapters: BaseModelAdapter) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage phase-2 scenario corpus.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    merged = {"mock": adapters["openai"], "openai": adapters["openai"], "ollama": adapters["openai"]}
    return RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters=merged,
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )


class JsonAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def __init__(self, narrative: str) -> None:
        self._narrative = narrative

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        payload = {
            "narrative_response": self._narrative,
            "proposed_scene_id": None,
            "intent_summary": "phase2_fixture",
        }
        return ModelCallResult(
            content=json.dumps(payload),
            success=True,
            metadata={"adapter": self.adapter_name},
        )


@pytest.fixture(autouse=True)
def _clear_goc_caches() -> None:
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()
    yield
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()


def _assert_non_preview_core(result: dict) -> None:
    assert result.get("experiment_preview") is False
    assert result["validation_outcome"].get("status") == "approved"
    assert result["committed_result"].get("commit_applied") is True
    assert gate_turn_integrity(result) == "pass"
    assert gate_diagnostic_sufficiency(result) in ("pass", "conditional_pass")
    assert gate_dramatic_quality(result) == "pass"


def test_scenario_standard_escalation_non_preview(tmp_path: Path) -> None:
    narrative = (
        "Michel's voice rises sharply; he accuses you of insulting his judgment and slams his hand "
        "on the table, furious that you would attack him here."
    )
    graph = _executor(tmp_path, openai=JsonAdapter(narrative))
    result = graph.run(
        session_id="s-p2-escalate",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I am so angry I want to fight and shout at Michel now.",
        trace_id="trace-p2-escalate",
        host_experience_template=HOST_OK,
    )
    assert result.get("selected_scene_function") == "escalate_conflict"
    assert result.get("pacing_mode") == "standard"
    _assert_non_preview_core(result)
    sa = result.get("scene_assessment") or {}
    assert sa.get("guidance_phase_key") == "phase_2_moral_negotiation"


def test_scenario_thin_edge_silence_non_preview(tmp_path: Path) -> None:
    narrative = (
        "You stay silent at the table; you say nothing aloud while others watch you hold still and quiet."
    )
    graph = _executor(tmp_path, openai=JsonAdapter(narrative))
    result = graph.run(
        session_id="s-p2-thin",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="thin edge silent say nothing",
        trace_id="trace-p2-thin",
        host_experience_template=HOST_OK,
    )
    assert result.get("pacing_mode") == "thin_edge"
    assert (result.get("silence_brevity_decision") or {}).get("mode") == "withheld"
    assert result.get("selected_scene_function") == "withhold_or_evade"
    _assert_non_preview_core(result)
    vis = result.get("visible_output_bundle") or {}
    lines = vis.get("gm_narration") or []
    assert len(lines) >= 1
    assert any("Director staging" in str(x) for x in lines) or len(" ".join(str(x) for x in lines)) > 40
    assert "bounded_ambiguity" in (result.get("visibility_class_markers") or [])


def test_scenario_multi_pressure_non_preview(tmp_path: Path) -> None:
    narrative = (
        "I'm sorry you hid this from us; you must reveal the truth now and admit what you knew about "
        "the incident so we can face the fact together."
    )
    graph = _executor(tmp_path, openai=JsonAdapter(narrative))
    result = graph.run(
        session_id="s-p2-multi",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I'm sorry but you must reveal the truth now multi pressure",
        trace_id="trace-p2-multi",
        host_experience_template=HOST_OK,
    )
    assert result.get("pacing_mode") == "multi_pressure"
    assert result.get("selected_scene_function") == "reveal_surface"
    mpr = (result.get("scene_assessment") or {}).get("multi_pressure_resolution") or {}
    assert "repair_or_stabilize" in (mpr.get("candidates") or [])
    assert "reveal_surface" in (mpr.get("candidates") or [])
    assert mpr.get("chosen_scene_function") == "reveal_surface"
    assert "3.5" in str(mpr.get("rationale") or "")
    _assert_non_preview_core(result)
    dr = (result.get("graph_diagnostics") or {}).get("dramatic_review") or {}
    assert dr.get("multi_pressure_chosen") == "reveal_surface"


def test_scenario_out_of_scope_containment_non_preview(tmp_path: Path) -> None:
    narrative = (
        "We steer back to the apartment table; this dinner is here and now, not a story about Mars."
    )
    graph = _executor(tmp_path, openai=JsonAdapter(narrative))
    result = graph.run(
        session_id="s-p2-contain",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I talk about my vacation on Mars and the spaceship launch.",
        trace_id="trace-p2-contain",
        host_experience_template=HOST_OK,
    )
    assert result.get("pacing_mode") == "containment"
    assert result.get("selected_scene_function") == "scene_pivot"
    _assert_non_preview_core(result)


def test_anti_seductive_fluent_empty_rejected(tmp_path: Path) -> None:
    fluff = (
        "The atmosphere thickens with unspoken tension as everyone senses something shifting beneath "
        "the polite surface; the mood deepens and a sense of uneasy anticipation fills the space."
    )
    graph = _executor(tmp_path, openai=JsonAdapter(fluff))
    result = graph.run(
        session_id="s-p2-anti",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I am furious and want to fight you right now.",
        trace_id="trace-p2-anti",
        host_experience_template=HOST_OK,
    )
    assert result.get("selected_scene_function") == "escalate_conflict"
    vo = result.get("validation_outcome") or {}
    assert vo.get("status") == "rejected"
    assert str(vo.get("reason", "")).startswith("dramatic_effect_") or str(vo.get("reason", "")).startswith(
        "dramatic_alignment"
    )
    assert vo.get("dramatic_quality_gate") == "effect_gate_reject"
    assert gate_dramatic_quality(result) == "fail"
    dr = (result.get("graph_diagnostics") or {}).get("dramatic_review") or {}
    assert "alignment_reject" in str(dr.get("dramatic_alignment_summary") or "")


def test_continuity_changes_later_turn_behavior(tmp_path: Path) -> None:
    n1 = (
        "Michel stiffens; your blame lands squarely on him for ruining the evening, your voice sharp "
        "with accusation about his fault in the mess."
    )
    n2_carry = (
        "Michel shifts under your stare; the blame still circles him even as you watch the table in silence."
    )
    n2_fresh = (
        "The dinner table stays in uneasy quiet; you watch without naming anyone while the room stays tight."
    )
    graph = _executor(tmp_path, openai=JsonAdapter(n1))
    first = graph.run(
        session_id="s-p2-c1",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I blame Michel for ruining this evening.",
        trace_id="trace-p2-c1",
        host_experience_template=HOST_OK,
    )
    assert first.get("selected_scene_function") == "redirect_blame"
    prior = first.get("continuity_impacts") or []
    assert any(isinstance(x, dict) and x.get("class") == "blame_pressure" for x in prior)

    graph2 = _executor(tmp_path, openai=JsonAdapter(n2_carry))
    with_prior = graph2.run(
        session_id="s-p2-c2",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I watch the dinner table without naming anyone.",
        trace_id="trace-p2-c2",
        host_experience_template=HOST_OK,
        prior_continuity_impacts=list(prior),
    )
    assert with_prior.get("selected_scene_function") == "redirect_blame"
    assert (with_prior.get("selected_responder_set") or [{}])[0].get("actor_id") == "michel_longstreet"

    graph3 = _executor(tmp_path, openai=JsonAdapter(n2_fresh))
    without_prior = graph3.run(
        session_id="s-p2-c3",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I watch the dinner table without naming anyone.",
        trace_id="trace-p2-c3",
        host_experience_template=HOST_OK,
    )
    assert without_prior.get("selected_scene_function") == "establish_pressure"
    assert (without_prior.get("selected_responder_set") or [{}])[0].get("actor_id") == "annette_reille"


def test_yaml_module_still_authoritative(tmp_path: Path) -> None:
    yaml_mod = load_goc_canonical_module_yaml()
    assert yaml_mod.get("module_id") == "god_of_carnage"
