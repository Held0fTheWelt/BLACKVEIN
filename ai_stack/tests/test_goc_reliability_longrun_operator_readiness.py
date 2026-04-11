"""Phase 4 GoC hardening: reliability, breadth, long-run stability, and operator readiness."""

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
from ai_stack.goc_gate_evaluation import (
    gate_diagnostic_sufficiency,
    gate_dramatic_quality,
    gate_turn_integrity,
)
from ai_stack.goc_yaml_authority import cached_goc_yaml_title, clear_goc_yaml_slice_cache

HOST_OK = {"template_id": "god_of_carnage_solo", "title": "God of Carnage"}


def _executor(tmp_path: Path, *, adapter: BaseModelAdapter) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage phase-4 scenario corpus.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    merged = {"mock": adapter, "openai": adapter, "ollama": adapter}
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
            "intent_summary": "phase4_fixture",
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
            metadata={"adapter": self.adapter_name, "error": "phase4_simulated_generation_failure"},
        )


@dataclass
class TurnStep:
    current_scene_id: str
    player_input: str
    adapter: BaseModelAdapter
    trace_id: str


@pytest.fixture(autouse=True)
def _clear_goc_caches() -> None:
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()
    yield
    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()


def _assert_credible_non_preview_turn(result: dict[str, Any]) -> None:
    assert result.get("experiment_preview") is False
    assert gate_turn_integrity(result) == "pass"
    assert gate_diagnostic_sufficiency(result) in ("pass", "conditional_pass")
    assert gate_dramatic_quality(result) == "pass"


def _run_chain(
    tmp_path: Path,
    *,
    session_id: str,
    steps: list[TurnStep],
    seed_prior_continuity: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    prior_continuity: list[dict[str, Any]] = list(seed_prior_continuity or [])
    prior_signature: dict[str, str] | None = None
    results: list[dict[str, Any]] = []
    for idx, step in enumerate(steps):
        graph = _executor(tmp_path, adapter=step.adapter)
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
            prior_continuity = prior_continuity[-8:]
        dr = ((result.get("graph_diagnostics") or {}).get("dramatic_review") or {})
        sig = dr.get("dramatic_signature") if isinstance(dr.get("dramatic_signature"), dict) else {}
        if sig:
            intent = ((result.get("interpreted_move") or {}).get("player_intent") or "")
            prior_signature = {**{k: str(v) for k, v in sig.items()}, "player_intent": str(intent)}
        else:
            prior_signature = {"player_intent": f"step_{idx}"}
    return results


def test_phase4_non_preview_breadth_has_six_distinct_paths(tmp_path: Path) -> None:
    scenarios = [
        (
            "s-p4-escalate",
            "living_room",
            "I am furious and attack your accusation now.",
            "escalate_conflict",
            "Michel raises his voice, attacks your accusation, and slams blame back across the table.",
        ),
        (
            "s-p4-blame",
            "living_room",
            "This is your fault and I blame you directly.",
            "redirect_blame",
            "Annette points at you and names your fault, refusing to absorb responsibility for the humiliation.",
        ),
        (
            "s-p4-probe",
            "phase_3",
            "Why did you do this, what is your motive?",
            "probe_motive",
            "Annette presses your motive in real time, demanding a reason while the room goes tight and silent.",
        ),
        (
            "s-p4-repair",
            "phase_3",
            "I am sorry, we should repair this now.",
            "repair_or_stabilize",
            "Alain asks for a truce, apologizes directly, and tries to stabilize the room before it tears again.",
        ),
        (
            "s-p4-thin",
            "living_room",
            "thin edge silent say nothing",
            "withhold_or_evade",
            "You say nothing, hold still, and let the awkward silence punish everyone at the table.",
        ),
        (
            "s-p4-contain",
            "living_room",
            "I want to discuss our Mars spaceship venture instead of this dinner.",
            "scene_pivot",
            "We stay in this apartment and return to the dinner conflict now; no one accepts the off-topic escape.",
        ),
    ]
    pass_count = 0
    for sid, scene_id, player_input, expected_fn, narrative in scenarios:
        result = _executor(tmp_path, adapter=JsonAdapter(narrative)).run(
            session_id=sid,
            module_id="god_of_carnage",
            current_scene_id=scene_id,
            player_input=player_input,
            trace_id=f"trace-{sid}",
            host_experience_template=HOST_OK,
        )
        assert result.get("selected_scene_function") == expected_fn
        _assert_credible_non_preview_turn(result)
        pass_count += 1
    assert pass_count >= 6


def test_phase4_run_a_five_turn_credible_pressure_humiliation_repair(tmp_path: Path) -> None:
    steps = [
        TurnStep(
            current_scene_id="living_room",
            player_input="I am angry and attack your claim.",
            adapter=JsonAdapter("Michel snaps, attacks your claim, and raises pressure in the room immediately."),
            trace_id="trace-p4-a1",
        ),
        TurnStep(
            current_scene_id="living_room",
            player_input="It is your fault and everyone knows it.",
            adapter=JsonAdapter("Annette redirects blame to you and insists your fault is now public and undeniable."),
            trace_id="trace-p4-a2",
        ),
        TurnStep(
            current_scene_id="phase_3",
            player_input="You humiliated me in front of everyone.",
            adapter=JsonAdapter(
                "Veronique says your humiliation is an accusation and your fault, marking a dignity injury that lingers."
            ),
            trace_id="trace-p4-a3",
        ),
        TurnStep(
            current_scene_id="phase_3",
            player_input="I am sorry, we should stop and repair this.",
            adapter=JsonAdapter("Alain apologizes and asks for a truce, trying to repair the room before collapse."),
            trace_id="trace-p4-a4",
        ),
        TurnStep(
            current_scene_id="phase_4",
            player_input="Why did you do that to me?",
            adapter=JsonAdapter("Annette demands your motive now, forcing an exposed answer while pressure stays active."),
            trace_id="trace-p4-a5",
        ),
    ]
    results = _run_chain(tmp_path, session_id="s-p4-run-a", steps=steps)
    assert len(results) == 5
    for r in results:
        _assert_credible_non_preview_turn(r)
    functions = [r.get("selected_scene_function") for r in results]
    assert {"escalate_conflict", "redirect_blame", "repair_or_stabilize", "probe_motive"} <= set(functions)


def test_phase4_run_b_five_turn_credible_alliance_and_pressure_shift(tmp_path: Path) -> None:
    steps = [
        TurnStep(
            current_scene_id="living_room",
            player_input="I blame Michel for this mess.",
            adapter=JsonAdapter("You blame Michel openly and force him to carry fault while the hosts stare at him."),
            trace_id="trace-p4-b1",
        ),
        TurnStep(
            current_scene_id="phase_3",
            player_input="Michel, I side with Annette against your wife now.",
            adapter=JsonAdapter("Michel sides with Annette against his wife, triggering a visible alliance shift in the room."),
            trace_id="trace-p4-b2",
        ),
        TurnStep(
            current_scene_id="phase_3",
            player_input="I watch the table without naming anyone.",
            adapter=JsonAdapter(
                "Michel keeps blame on you, denies fault again, and the room treats Veronique as isolated under alliance pressure."
            ),
            trace_id="trace-p4-b3",
        ),
        TurnStep(
            current_scene_id="phase_4",
            player_input="thin edge silent say nothing",
            adapter=JsonAdapter("You hold silence, forcing everyone to sit inside the alliance fracture without relief."),
            trace_id="trace-p4-b4",
        ),
        TurnStep(
            current_scene_id="phase_4",
            player_input="I am sorry but I still blame you for this.",
            adapter=JsonAdapter("Alain offers a strained apology while blame remains active, partially stabilizing without resolving."),
            trace_id="trace-p4-b5",
        ),
    ]
    results = _run_chain(tmp_path, session_id="s-p4-run-b", steps=steps)
    assert len(results) == 5
    for r in results:
        _assert_credible_non_preview_turn(r)
    continuity_classes = [
        c
        for r in results
        for c in [
            x.get("class")
            for x in (r.get("continuity_impacts") or [])
            if isinstance(x, dict) and x.get("class")
        ]
    ]
    assert "alliance_shift" in continuity_classes
    dr2 = ((results[1].get("graph_diagnostics") or {}).get("dramatic_review") or {})
    assert dr2.get("alliance_shift_detected") is True
    assert dr2.get("pressure_shift_detected") is True


def test_phase4_run_c_five_turn_degraded_and_fail_are_operator_explainable(tmp_path: Path) -> None:
    steps = [
        TurnStep(
            current_scene_id="courtesy",
            player_input="Why are you saying this now?",
            adapter=JsonAdapter("Annette asks why now and corners your motive in front of everyone."),
            trace_id="trace-p4-c1",
        ),
        TurnStep(
            current_scene_id="living_room",
            player_input="I am furious and ready to fight.",
            adapter=JsonAdapter("The atmosphere shifts and everyone feels something, as a commentator would note."),
            trace_id="trace-p4-c2",
        ),
        TurnStep(
            current_scene_id="phase_3",
            player_input="I blame you for this.",
            adapter=ErrorAdapter(),
            trace_id="trace-p4-c3",
        ),
        TurnStep(
            current_scene_id="phase_4",
            player_input="thin edge silent say nothing",
            adapter=JsonAdapter("You say nothing and force a brittle silence."),
            trace_id="trace-p4-c4",
        ),
        TurnStep(
            current_scene_id="phase_4",
            player_input="I want to discuss Mars instead.",
            adapter=JsonAdapter("We remain in the apartment conflict and reject the off-topic detour."),
            trace_id="trace-p4-c5",
        ),
    ]
    results = _run_chain(tmp_path, session_id="s-p4-run-c", steps=steps)
    assert len(results) == 5
    outcomes = [gate_dramatic_quality(r) for r in results]
    assert "fail" in outcomes
    assert "conditional_pass" in outcomes
    dr_fail = ((results[1].get("graph_diagnostics") or {}).get("dramatic_review") or {})
    dr_deg = ((results[2].get("graph_diagnostics") or {}).get("dramatic_review") or {})
    assert dr_fail.get("run_classification") == "fail"
    assert dr_deg.get("run_classification") == "degraded_explainable"
    assert "validation_status" in str(dr_deg.get("weak_run_explanation") or "")
    assert "alignment_reject" in str(dr_fail.get("dramatic_alignment_summary") or "")


def test_phase4_four_major_characters_show_distinct_pressure_defaults(tmp_path: Path) -> None:
    base_input = "I watch the table without naming anyone."
    adapter = JsonAdapter("The room tightens and someone reacts immediately to the pressure in play.")
    graph = _executor(tmp_path, adapter=adapter)

    no_prior = graph.run(
        session_id="s-p4-char-0",
        module_id="god_of_carnage",
        current_scene_id="courtesy",
        player_input=base_input,
        trace_id="trace-p4-char-0",
        host_experience_template=HOST_OK,
    )
    blame_prior = graph.run(
        session_id="s-p4-char-1",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input=base_input,
        trace_id="trace-p4-char-1",
        host_experience_template=HOST_OK,
        prior_continuity_impacts=[{"class": "blame_pressure", "note": "seed"}],
    )
    revealed_prior = graph.run(
        session_id="s-p4-char-2",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input=base_input,
        trace_id="trace-p4-char-2",
        host_experience_template=HOST_OK,
        prior_continuity_impacts=[{"class": "revealed_fact", "note": "seed"}],
    )
    repair_prior = graph.run(
        session_id="s-p4-char-3",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input=base_input,
        trace_id="trace-p4-char-3",
        host_experience_template=HOST_OK,
        prior_continuity_impacts=[{"class": "repair_attempt", "note": "seed"}],
    )

    responders = [
        ((no_prior.get("selected_responder_set") or [{}])[0]).get("actor_id"),
        ((blame_prior.get("selected_responder_set") or [{}])[0]).get("actor_id"),
        ((revealed_prior.get("selected_responder_set") or [{}])[0]).get("actor_id"),
        ((repair_prior.get("selected_responder_set") or [{}])[0]).get("actor_id"),
    ]
    assert responders[0] == "veronique_vallon"
    assert responders[1] == "michel_longstreet"
    assert responders[2] == "annette_reille"
    assert responders[3] == "alain_reille"
    assert len(set(responders)) == 4


def test_phase4_regression_preserves_phase123_strengths_while_broadening(tmp_path: Path) -> None:
    phase1_like = _executor(
        tmp_path,
        adapter=JsonAdapter("Annette reveals the truth she withheld and confesses the hidden fact directly."),
    ).run(
        session_id="s-p4-reg-1",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I press Annette to reveal what she knew.",
        trace_id="trace-p4-reg-1",
        host_experience_template=HOST_OK,
    )
    phase2_like = _executor(
        tmp_path,
        adapter=JsonAdapter("I am sorry, but reveal the truth now so we can repair this room."),
    ).run(
        session_id="s-p4-reg-2",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="I'm sorry but reveal the truth now multi pressure",
        trace_id="trace-p4-reg-2",
        host_experience_template=HOST_OK,
    )
    phase3_like_steps = [
        TurnStep(
            current_scene_id="living_room",
            player_input="I blame Michel for ruining this.",
            adapter=JsonAdapter("You blame Michel and keep pressure fixed on him."),
            trace_id="trace-p4-reg-3a",
        ),
        TurnStep(
            current_scene_id="phase_3",
            player_input="I watch the table without naming anyone.",
            adapter=JsonAdapter("Michel still carries blame and reacts defensively."),
            trace_id="trace-p4-reg-3b",
        ),
        TurnStep(
            current_scene_id="phase_3",
            player_input="I am sorry, stop this now.",
            adapter=JsonAdapter("Alain asks for calm and repair while pressure remains visible."),
            trace_id="trace-p4-reg-3c",
        ),
        TurnStep(
            current_scene_id="phase_4",
            player_input="I watch the table without naming anyone.",
            adapter=JsonAdapter("Alain now responds instead of Michel due to carried repair pressure."),
            trace_id="trace-p4-reg-3d",
        ),
        TurnStep(
            current_scene_id="phase_4",
            player_input="Why are you still doing this?",
            adapter=JsonAdapter("Annette probes motive under the stabilized but tense social field."),
            trace_id="trace-p4-reg-3e",
        ),
    ]
    phase3_like = _run_chain(tmp_path, session_id="s-p4-reg-3", steps=phase3_like_steps)

    for turn in [phase1_like, phase2_like, *phase3_like]:
        assert gate_turn_integrity(turn) == "pass"
        assert gate_diagnostic_sufficiency(turn) in ("pass", "conditional_pass")
    assert gate_dramatic_quality(phase1_like) == "pass"
    assert gate_dramatic_quality(phase2_like) == "pass"
    assert sum(1 for r in phase3_like if gate_dramatic_quality(r) == "pass") >= 4
