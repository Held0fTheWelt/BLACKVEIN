"""Phase 5 GoC final MVP closure: breadth, 6+ turn playability, diagnostics, and regression confidence."""

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
    content_file.write_text("God of Carnage phase-5 scenario corpus.", encoding="utf-8")
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
            "intent_summary": "phase5_fixture",
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
            metadata={"adapter": self.adapter_name, "error": "phase5_simulated_generation_failure"},
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
            prior_continuity = prior_continuity[-10:]
        dr = ((result.get("graph_diagnostics") or {}).get("dramatic_review") or {})
        sig = dr.get("dramatic_signature") if isinstance(dr.get("dramatic_signature"), dict) else {}
        if sig:
            intent = ((result.get("interpreted_move") or {}).get("player_intent") or "")
            prior_signature = {**{k: str(v) for k, v in sig.items()}, "player_intent": str(intent)}
        else:
            prior_signature = {"player_intent": f"step_{idx}"}
    return results


def _run_is_credible(results: list[dict[str, Any]]) -> bool:
    return all(
        r.get("experiment_preview") is False
        and gate_turn_integrity(r) == "pass"
        and gate_diagnostic_sufficiency(r) in ("pass", "conditional_pass")
        and gate_dramatic_quality(r) == "pass"
        for r in results
    )


def test_phase5_breadth_has_ten_non_preview_paths_and_seven_gate_strong(tmp_path: Path) -> None:
    scenarios = [
        (
            "s-p5-escalate",
            "living_room",
            "I am furious and attack your accusation right now.",
            "escalate_conflict",
            "Michel raises his voice, attacks your accusation, and threatens another fight if you continue.",
        ),
        (
            "s-p5-dignity",
            "phase_3",
            "You humiliated me and mocked me in front of everyone.",
            "redirect_blame",
            "Veronique names your humiliation as blame and accuses you of cruelty that wounded her dignity.",
        ),
        (
            "s-p5-blame",
            "living_room",
            "This is your fault and I blame you directly.",
            "redirect_blame",
            "Annette points at you and says this fault belongs to you, then denies carrying your blame.",
        ),
        (
            "s-p5-probe",
            "phase_3",
            "Why did you do this, what is your motive?",
            "probe_motive",
            "Annette asks why now and demands your reason, pressing motive and justification without relief.",
        ),
        (
            "s-p5-repair",
            "phase_3",
            "I am sorry, we should repair this now.",
            "repair_or_stabilize",
            "Alain apologizes, asks for calm, and proposes a truce to repair the room before it breaks.",
        ),
        (
            "s-p5-thin",
            "living_room",
            "thin edge awkward pause I say nothing",
            "withhold_or_evade",
            "You hold still in silence and say nothing while the awkward pause punishes everyone at the table.",
        ),
        (
            "s-p5-contain",
            "living_room",
            "Let's discuss the weather forecast and football match instead.",
            "scene_pivot",
            "We stay here in the apartment and return to this dinner conflict now, not weather or football.",
        ),
        (
            "s-p5-alliance",
            "phase_3",
            "Michel, I side with Annette against your wife.",
            "scene_pivot",
            "Michel sides with Annette against his wife, and the alliance shift changes who now carries pressure.",
        ),
        (
            "s-p5-reveal",
            "phase_3",
            "Reveal the truth and admit what you knew.",
            "reveal_surface",
            "Annette admits the hidden truth, reveals what she knew, and confesses the fact directly to the room.",
        ),
        (
            "s-p5-multipressure",
            "phase_3",
            "I am sorry but reveal the truth now, multi pressure.",
            "reveal_surface",
            "Alain says sorry, then demands you reveal the truth and confess the secret fact before this room collapses.",
        ),
        (
            "s-p5-establish",
            "courtesy",
            "We sit at the table and wait.",
            "establish_pressure",
            "The room stays tight and quiet at the table while everyone watches and waits for the next move.",
        ),
    ]

    strong_count = 0
    non_preview_count = 0
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
        if result.get("experiment_preview") is False:
            non_preview_count += 1
        if (
            result.get("experiment_preview") is False
            and gate_turn_integrity(result) == "pass"
            and gate_diagnostic_sufficiency(result) in ("pass", "conditional_pass")
            and gate_dramatic_quality(result) == "pass"
        ):
            strong_count += 1

    assert non_preview_count >= 10
    assert strong_count >= 7


def test_phase5_run_d_credible_escalation_bend_repair_renewed_pressure(tmp_path: Path) -> None:
    steps = [
        TurnStep(
            "living_room",
            "I am angry and attack your claim now.",
            JsonAdapter("Michel attacks your claim, raises his voice, and turns this argument into open conflict."),
            "trace-p5-d1",
        ),
        TurnStep(
            "living_room",
            "This is your fault and you know it.",
            JsonAdapter("Annette redirects blame to you and denies responsibility for your accusation."),
            "trace-p5-d2",
        ),
        TurnStep(
            "phase_3",
            "I pause and do not answer for a beat.",
            JsonAdapter("You hold silence in an awkward pause, and everyone waits under pressure."),
            "trace-p5-d3",
        ),
        TurnStep(
            "phase_3",
            "I am sorry, let's repair this.",
            JsonAdapter("Alain apologizes and asks for calm repair before the argument tears apart again."),
            "trace-p5-d4",
        ),
        TurnStep(
            "phase_4",
            "Why did you do this anyway?",
            JsonAdapter("Annette demands your motive and asks why you chose this line under public pressure."),
            "trace-p5-d5",
        ),
        TurnStep(
            "phase_4",
            "I blame you again for this scene.",
            JsonAdapter("Michel denies your accusation and throws blame back at you, restarting pressure."),
            "trace-p5-d6",
        ),
    ]
    results = _run_chain(tmp_path, session_id="s-p5-run-d", steps=steps)
    assert len(results) == 6
    assert _run_is_credible(results) is True
    scene_functions = [r.get("selected_scene_function") for r in results]
    assert "repair_or_stabilize" in scene_functions
    assert scene_functions[0] == "escalate_conflict"
    assert scene_functions[-1] == "redirect_blame"


def test_phase5_run_e_credible_with_alliance_shift_and_multiple_pressure_movements(tmp_path: Path) -> None:
    steps = [
        TurnStep(
            "living_room",
            "I blame Michel for this mess.",
            JsonAdapter("You blame Michel directly, and he denies fault while pressure locks onto him."),
            "trace-p5-e1",
        ),
        TurnStep(
            "phase_3",
            "Michel, I side with Annette against your wife.",
            JsonAdapter("Michel sides with Annette against his wife, and the alliance shift becomes visible."),
            "trace-p5-e2",
        ),
        TurnStep(
            "phase_3",
            "Why are you doing this now?",
            JsonAdapter("Annette asks why now, probing motive after the alliance shift changed the social field."),
            "trace-p5-e3",
        ),
        TurnStep(
            "phase_4",
            "I am sorry, but this fault is still yours.",
            JsonAdapter("Alain apologizes for tone while blame pressure remains active and unresolved."),
            "trace-p5-e4",
        ),
        TurnStep(
            "phase_4",
            "thin edge awkward pause I say nothing",
            JsonAdapter("You say nothing, hold still, and let silence carry social pressure between all four adults."),
            "trace-p5-e5",
        ),
        TurnStep(
            "phase_4",
            "I reveal the truth now.",
            JsonAdapter("Annette reveals the truth and admits what she knew, forcing a new pressure line."),
            "trace-p5-e6",
        ),
    ]
    results = _run_chain(tmp_path, session_id="s-p5-run-e", steps=steps)
    assert len(results) == 6
    assert _run_is_credible(results) is True
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
    shift_count = sum(
        1
        for r in results
        if (((r.get("graph_diagnostics") or {}).get("dramatic_review") or {}).get("pressure_shift_detected") is True)
    )
    assert shift_count >= 2


def test_phase5_run_f_credible_with_multiple_pressure_movements(tmp_path: Path) -> None:
    steps = [
        TurnStep(
            "courtesy",
            "We sit at the table and wait.",
            JsonAdapter("The room stays tight and quiet at the table while everyone watches the next move."),
            "trace-p5-f1",
        ),
        TurnStep(
            "living_room",
            "You humiliated me in front of everyone.",
            JsonAdapter("Veronique calls your humiliation a blame move and accuses you of dignity injury."),
            "trace-p5-f2",
        ),
        TurnStep(
            "phase_3",
            "Why did you choose this?",
            JsonAdapter("Annette asks why and demands your motive under rising social pressure."),
            "trace-p5-f3",
        ),
        TurnStep(
            "phase_3",
            "I am sorry, let's stop this now.",
            JsonAdapter("Alain apologizes and proposes calm repair, trying to bend pressure without denying conflict."),
            "trace-p5-f4",
        ),
        TurnStep(
            "phase_4",
            "I blame you for this again.",
            JsonAdapter("Michel denies your blame and redirects fault back at you with renewed pressure."),
            "trace-p5-f5",
        ),
        TurnStep(
            "phase_4",
            "I reveal the secret truth.",
            JsonAdapter("Annette reveals the secret truth and confesses what she knew to everyone present."),
            "trace-p5-f6",
        ),
    ]
    results = _run_chain(tmp_path, session_id="s-p5-run-f", steps=steps)
    assert len(results) == 6
    assert _run_is_credible(results) is True
    shift_count = sum(
        1
        for r in results
        if (((r.get("graph_diagnostics") or {}).get("dramatic_review") or {}).get("pressure_shift_detected") is True)
    )
    assert shift_count >= 2


def test_phase5_run_h_mixed_by_design_with_honest_degradation_and_diagnostics(tmp_path: Path) -> None:
    steps = [
        TurnStep(
            "courtesy",
            "Why are you saying this now?",
            JsonAdapter("Annette asks why now and presses your reason under thin civility."),
            "trace-p5-h1",
        ),
        TurnStep(
            "living_room",
            "I am furious and attack this claim.",
            JsonAdapter("The atmosphere shifts in dramatic terms and the dialogue represents rising conflict."),
            "trace-p5-h2",
        ),
        TurnStep(
            "phase_3",
            "I blame you for this.",
            ErrorAdapter(),
            "trace-p5-h3",
        ),
        TurnStep(
            "phase_3",
            "thin edge awkward pause I say nothing",
            JsonAdapter("You hold still in silence and say nothing while everyone waits."),
            "trace-p5-h4",
        ),
        TurnStep(
            "phase_4",
            "I am sorry, we should repair this.",
            JsonAdapter("Alain apologizes and asks for repair, trying to stabilize pressure in the room."),
            "trace-p5-h5",
        ),
        TurnStep(
            "phase_4",
            "I reveal the truth now.",
            JsonAdapter("Annette reveals the truth, admits what she knew, and forces new pressure again."),
            "trace-p5-h6",
        ),
    ]
    results = _run_chain(tmp_path, session_id="s-p5-run-h", steps=steps)
    assert len(results) == 6
    outcomes = [gate_dramatic_quality(r) for r in results]
    assert "fail" in outcomes
    assert "conditional_pass" in outcomes

    # Diagnostics-only explainability requirement (no prompt inspection).
    fail_dr = ((results[1].get("graph_diagnostics") or {}).get("dramatic_review") or {})
    degraded_dr = ((results[2].get("graph_diagnostics") or {}).get("dramatic_review") or {})
    assert fail_dr.get("run_classification") == "fail"
    assert degraded_dr.get("run_classification") == "degraded_explainable"
    assert "alignment_reject" in str(fail_dr.get("dramatic_alignment_summary") or "")
    assert "validation_status=" in str(degraded_dr.get("weak_run_explanation") or "")

    # Later turns remain scene-coherent and pass seam checks despite weak middle turns.
    assert gate_turn_integrity(results[3]) == "pass"
    assert gate_turn_integrity(results[4]) == "pass"
    assert gate_turn_integrity(results[5]) == "pass"


def test_phase5_character_specific_reactions_for_same_move_type(tmp_path: Path) -> None:
    base_input = "I watch the table without naming anyone."
    adapter = JsonAdapter("The room tightens and someone reacts immediately under carried pressure.")
    graph = _executor(tmp_path, adapter=adapter)

    no_prior = graph.run(
        session_id="s-p5-char-0",
        module_id="god_of_carnage",
        current_scene_id="courtesy",
        player_input=base_input,
        trace_id="trace-p5-char-0",
        host_experience_template=HOST_OK,
    )
    blame_prior = graph.run(
        session_id="s-p5-char-1",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input=base_input,
        trace_id="trace-p5-char-1",
        host_experience_template=HOST_OK,
        prior_continuity_impacts=[{"class": "blame_pressure", "note": "seed"}],
    )
    revealed_prior = graph.run(
        session_id="s-p5-char-2",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input=base_input,
        trace_id="trace-p5-char-2",
        host_experience_template=HOST_OK,
        prior_continuity_impacts=[{"class": "revealed_fact", "note": "seed"}],
    )
    repair_prior = graph.run(
        session_id="s-p5-char-3",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input=base_input,
        trace_id="trace-p5-char-3",
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


def test_phase5_binary_acceptance_for_four_long_runs(tmp_path: Path) -> None:
    run_d = _run_chain(
        tmp_path,
        session_id="s-p5-bin-d",
        steps=[
            TurnStep("living_room", "I am angry and attack your claim now.", JsonAdapter("Michel attacks your claim and escalates conflict immediately."), "bin-d1"),
            TurnStep("living_room", "This is your fault and you know it.", JsonAdapter("Annette redirects blame to you, denies your accusation, and says this fault remains yours alone tonight."), "bin-d2"),
            TurnStep("phase_3", "I pause and do not answer for a beat.", JsonAdapter("You hold silence while the room waits under pressure."), "bin-d3"),
            TurnStep("phase_3", "I am sorry, let's repair this.", JsonAdapter("Alain apologizes and asks for repair and calm."), "bin-d4"),
            TurnStep("phase_4", "Why did you do this anyway?", JsonAdapter("Annette demands a motive and asks why now."), "bin-d5"),
            TurnStep("phase_4", "I blame you again for this scene.", JsonAdapter("Michel denies blame and redirects fault back to you."), "bin-d6"),
        ],
    )
    run_e = _run_chain(
        tmp_path,
        session_id="s-p5-bin-e",
        steps=[
            TurnStep("living_room", "I blame Michel for this mess.", JsonAdapter("You blame Michel and he denies fault under pressure."), "bin-e1"),
            TurnStep("phase_3", "Michel, I side with Annette against your wife.", JsonAdapter("Michel sides with Annette against his wife in a visible alliance shift."), "bin-e2"),
            TurnStep("phase_3", "Why are you doing this now?", JsonAdapter("Annette asks why now and probes motive."), "bin-e3"),
            TurnStep("phase_4", "I am sorry, but this fault is still yours.", JsonAdapter("Alain apologizes while blame pressure remains active."), "bin-e4"),
            TurnStep("phase_4", "thin edge awkward pause I say nothing", JsonAdapter("You say nothing and hold an awkward pause."), "bin-e5"),
            TurnStep("phase_4", "I reveal the truth now.", JsonAdapter("Annette reveals the truth and confesses the hidden fact."), "bin-e6"),
        ],
    )
    run_f = _run_chain(
        tmp_path,
        session_id="s-p5-bin-f",
        steps=[
            TurnStep("courtesy", "We sit at the table and wait.", JsonAdapter("The room stays tight and quiet at the table."), "bin-f1"),
            TurnStep("living_room", "You humiliated me in front of everyone.", JsonAdapter("Veronique calls your humiliation a blame move and dignity injury."), "bin-f2"),
            TurnStep("phase_3", "Why did you choose this?", JsonAdapter("Annette asks why and probes motive under pressure."), "bin-f3"),
            TurnStep("phase_3", "I am sorry, let's stop this now.", JsonAdapter("Alain apologizes and asks for repair."), "bin-f4"),
            TurnStep("phase_4", "I blame you for this again.", JsonAdapter("Michel denies your blame and redirects fault back."), "bin-f5"),
            TurnStep("phase_4", "I reveal the secret truth.", JsonAdapter("Annette reveals the secret truth and confesses what she knew."), "bin-f6"),
        ],
    )
    run_h = _run_chain(
        tmp_path,
        session_id="s-p5-bin-h",
        steps=[
            TurnStep("courtesy", "Why are you saying this now?", JsonAdapter("Annette asks why now and presses your reason."), "bin-h1"),
            TurnStep("living_room", "I am furious and attack this claim.", JsonAdapter("The atmosphere shifts in dramatic terms and the dialogue represents conflict."), "bin-h2"),
            TurnStep("phase_3", "I blame you for this.", ErrorAdapter(), "bin-h3"),
            TurnStep("phase_3", "thin edge awkward pause I say nothing", JsonAdapter("You hold still in silence while everyone waits."), "bin-h4"),
            TurnStep("phase_4", "I am sorry, we should repair this.", JsonAdapter("Alain apologizes and asks for repair."), "bin-h5"),
            TurnStep("phase_4", "I reveal the truth now.", JsonAdapter("Annette reveals the truth and admits what she knew."), "bin-h6"),
        ],
    )

    runs = [run_d, run_e, run_f, run_h]
    credible = sum(1 for r in runs if _run_is_credible(r))
    mixed = sum(1 for r in runs if not _run_is_credible(r))
    assert credible == 3
    assert mixed == 1
