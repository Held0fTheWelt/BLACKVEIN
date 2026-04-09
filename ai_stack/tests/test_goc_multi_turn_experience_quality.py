"""Phase 3 GoC: multi-turn richness, continuity stability, and reviewability evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
from ai_stack.goc_gate_evaluation import gate_diagnostic_sufficiency, gate_dramatic_quality, gate_turn_integrity
from ai_stack.goc_yaml_authority import cached_goc_yaml_title, clear_goc_yaml_slice_cache

HOST_OK = {"template_id": "god_of_carnage_solo", "title": "God of Carnage"}


def _executor(
    tmp_path: Path,
    *,
    adapter: BaseModelAdapter,
    graph_fallback_adapter: BaseModelAdapter | None = None,
) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage phase-3 scenario corpus.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    mock_ad = graph_fallback_adapter if graph_fallback_adapter is not None else adapter
    merged = {"mock": mock_ad, "openai": adapter, "ollama": adapter}
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
            "intent_summary": "phase3_fixture",
        }
        return ModelCallResult(
            content=json.dumps(payload),
            success=True,
            metadata={"adapter": self.adapter_name},
        )


class ErrorAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(
            content="",
            success=False,
            metadata={"adapter": self.adapter_name, "error": "simulated_generation_failure"},
        )


@dataclass
class TurnStep:
    current_scene_id: str
    player_input: str
    adapter: BaseModelAdapter
    trace_id: str
    graph_fallback_adapter: BaseModelAdapter | None = None


@pytest.fixture(autouse=True)
def _clear_goc_caches() -> None:
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()
    yield
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()


def _run_chain(tmp_path: Path, *, session_id: str, steps: list[TurnStep]) -> list[dict[str, Any]]:
    prior_continuity: list[dict[str, Any]] = []
    prior_signature: dict[str, str] | None = None
    results: list[dict[str, Any]] = []
    for idx, step in enumerate(steps):
        graph = _executor(
            tmp_path,
            adapter=step.adapter,
            graph_fallback_adapter=step.graph_fallback_adapter,
        )
        result = graph.run(
            session_id=session_id,
            module_id="god_of_carnage",
            current_scene_id=step.current_scene_id,
            player_input=step.player_input,
            trace_id=step.trace_id,
            host_experience_template=HOST_OK,
            prior_continuity_impacts=list(prior_continuity),
            prior_dramatic_signature=dict(prior_signature) if prior_signature else None,
        )
        results.append(result)
        impacts = result.get("continuity_impacts")
        if isinstance(impacts, list) and impacts:
            prior_continuity.extend(x for x in impacts if isinstance(x, dict))
            prior_continuity = prior_continuity[-4:]
        dr = ((result.get("graph_diagnostics") or {}).get("dramatic_review") or {})
        sig = dr.get("dramatic_signature") if isinstance(dr.get("dramatic_signature"), dict) else {}
        if sig:
            intent = ((result.get("interpreted_move") or {}).get("player_intent") or "")
            prior_signature = {**{k: str(v) for k, v in sig.items()}, "player_intent": str(intent)}
        else:
            prior_signature = {"player_intent": f"step_{idx}"}
    return results


def test_phase3_run_a_non_preview_multiturn_pass(tmp_path: Path) -> None:
    steps = [
        TurnStep(
            current_scene_id="living_room",
            player_input="I am angry and I want to fight you right now.",
            adapter=JsonAdapter(
                "Michel speaks with a loud angry voice, he accuses you directly and threatens to fight if you keep attacking him."
            ),
            trace_id="trace-p3-a1",
        ),
        TurnStep(
            current_scene_id="living_room",
            player_input="thin edge silent say nothing",
            adapter=JsonAdapter("You hold still in silence and say nothing while everyone watches the table."),
            trace_id="trace-p3-a2",
        ),
        TurnStep(
            current_scene_id="phase_3",
            player_input="Why did you choose this motive and reason now?",
            adapter=JsonAdapter(
                "Annette asks why you acted this way and demands a reason, pushing you to explain your motive without relief."
            ),
            trace_id="trace-p3-a3",
        ),
    ]
    results = _run_chain(tmp_path, session_id="s-p3-a", steps=steps)
    assert len(results) == 3
    scene_functions = [r.get("selected_scene_function") for r in results]
    assert "escalate_conflict" in scene_functions
    assert "withhold_or_evade" in scene_functions
    assert "probe_motive" in scene_functions
    for r in results:
        assert r.get("experiment_preview") is False
        assert gate_turn_integrity(r) == "pass"
        assert gate_diagnostic_sufficiency(r) in ("pass", "conditional_pass")
        assert gate_dramatic_quality(r) == "pass"
    dr = ((results[1].get("graph_diagnostics") or {}).get("dramatic_review") or {})
    assert "review_explanations" in dr
    vis_lines = (results[1].get("visible_output_bundle") or {}).get("gm_narration") or []
    assert isinstance(vis_lines, list) and len(vis_lines) >= 2


def test_phase3_run_b_continuity_changes_later_behavior_more_than_once(tmp_path: Path) -> None:
    steps = [
        TurnStep(
            current_scene_id="living_room",
            player_input="I blame Michel for this fault at the table.",
            adapter=JsonAdapter(
                "You blame Michel directly, accuse him of fault, and insist he is responsible for the damage tonight."
            ),
            trace_id="trace-p3-b1",
        ),
        TurnStep(
            current_scene_id="living_room",
            player_input="I watch the table without naming anyone.",
            adapter=JsonAdapter(
                "Michel hears the blame still circling him; he denies fault and argues that your accusation remains unfair."
            ),
            trace_id="trace-p3-b2",
        ),
        TurnStep(
            current_scene_id="phase_3",
            player_input="I am sorry, we need to stop this now.",
            adapter=JsonAdapter(
                "Alain says sorry and asks everyone to calm down, calling for a truce before the room breaks again."
            ),
            trace_id="trace-p3-b3",
        ),
        TurnStep(
            current_scene_id="phase_3",
            player_input="I watch the table without naming anyone.",
            adapter=JsonAdapter(
                "The room tightens; blame remains in the air as Alain pushes calm language to keep a fragile truce alive."
            ),
            trace_id="trace-p3-b4",
        ),
    ]
    results = _run_chain(tmp_path, session_id="s-p3-b", steps=steps)
    assert len(results) == 4
    assert all(gate_turn_integrity(r) == "pass" for r in results)
    assert all(gate_dramatic_quality(r) == "pass" for r in results)

    r2 = results[1]
    r3 = results[2]
    r4 = results[3]
    assert r2.get("selected_scene_function") == "redirect_blame"
    assert r3.get("selected_scene_function") == "repair_or_stabilize"
    assert r4.get("selected_scene_function") == "redirect_blame"
    responder2 = ((r2.get("selected_responder_set") or [{}])[0]).get("actor_id")
    responder4 = ((r4.get("selected_responder_set") or [{}])[0]).get("actor_id")
    assert responder2 != responder4
    assert responder2 == "michel_longstreet"
    assert responder4 == "alain_reille"


def test_experience_multiturn_primary_failure_fallback_and_degraded_explained(tmp_path: Path) -> None:
    steps = [
        TurnStep(
            current_scene_id="courtesy",
            player_input="Why do you think this happened?",
            adapter=JsonAdapter("Annette asks why and demands a reason, pressing you to explain what truly happened."),
            trace_id="trace-p3-c1",
        ),
        TurnStep(
            current_scene_id="living_room",
            player_input="I am angry and want to fight now.",
            adapter=JsonAdapter(
                "The atmosphere thickens with a sense of mood and something shifts while everyone feels the moment hang."
            ),
            trace_id="trace-p3-c2",
        ),
        TurnStep(
            current_scene_id="living_room",
            player_input="I blame you for what happened.",
            adapter=ErrorAdapter(),
            trace_id="trace-p3-c3",
            graph_fallback_adapter=JsonAdapter(
                "Annette meets your blame head-on: she refuses to carry the fault alone, snaps that the table "
                "will not scapegoat her tonight, and forces the accusation back into the open air where everyone "
                "must answer for what they did."
            ),
        ),
    ]
    results = _run_chain(tmp_path, session_id="s-p3-c", steps=steps)
    assert len(results) == 3
    assert gate_dramatic_quality(results[0]) == "pass"
    assert gate_dramatic_quality(results[1]) == "fail"
    assert gate_dramatic_quality(results[2]) == "pass"

    dr2 = ((results[1].get("graph_diagnostics") or {}).get("dramatic_review") or {})
    dr3 = ((results[2].get("graph_diagnostics") or {}).get("dramatic_review") or {})
    assert dr2.get("dramatic_quality_status") == "fail"
    assert "alignment_reject" in str(dr2.get("dramatic_alignment_summary") or "")
    assert dr3.get("dramatic_quality_status") == "pass"
    nodes3 = (results[2].get("graph_diagnostics") or {}).get("nodes_executed") or []
    assert "fallback_model" in nodes3
    assert (results[2].get("generation") or {}).get("fallback_used") is True
    repro = ((results[2].get("graph_diagnostics") or {}).get("repro_metadata") or {})
    assert repro.get("model_fallback_used") is True
    assert repro.get("model_success") is True
    assert (results[2].get("validation_outcome") or {}).get("status") == "approved"
    assert "truth_aligned" in (results[2].get("visibility_class_markers") or [])
    assert results[2].get("experiment_preview") is False


def test_phase3_anti_repetition_same_move_diff_continuity(tmp_path: Path) -> None:
    base_graph = _executor(
        tmp_path,
        adapter=JsonAdapter("The room stays tight and quiet as everyone watches the table without speaking first."),
    )
    no_prior = base_graph.run(
        session_id="s-p3-r0",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I watch the table without naming anyone.",
        trace_id="trace-p3-r0",
        host_experience_template=HOST_OK,
    )
    with_prior = _executor(
        tmp_path,
        adapter=JsonAdapter("Michel still denies blame and says your accusation keeps circling him in this room."),
    ).run(
        session_id="s-p3-r1",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I watch the table without naming anyone.",
        trace_id="trace-p3-r1",
        host_experience_template=HOST_OK,
        prior_continuity_impacts=[{"class": "blame_pressure", "note": "seed"}],
        prior_dramatic_signature={
            "scene_function": str(no_prior.get("selected_scene_function") or ""),
            "responder": str(((no_prior.get("selected_responder_set") or [{}])[0]).get("actor_id") or ""),
            "pacing_mode": str(no_prior.get("pacing_mode") or ""),
            "silence_mode": str(((no_prior.get("silence_brevity_decision") or {}).get("mode") or "")),
            "player_intent": str(((no_prior.get("interpreted_move") or {}).get("player_intent") or "")),
        },
    )
    assert no_prior.get("selected_scene_function") != with_prior.get("selected_scene_function")
    dr = ((with_prior.get("graph_diagnostics") or {}).get("dramatic_review") or {})
    assert dr.get("pattern_repetition_risk") is False
    assert "pattern_variation" in str(dr.get("pattern_repetition_note") or "")

