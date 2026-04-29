"""Tests for bounded narrative threads derived from Task B narrative commits."""

from __future__ import annotations

from typing import Any

import pytest

from app.story_runtime import StoryRuntimeManager, commit_models
from app.story_runtime.narrative_threads import (
    GRAPH_EXPORT_MAX_ACTIVE,
    StoryNarrativeThread,
    StoryNarrativeThreadSet,
    THREAD_PRESSURE_SUMMARY_MAX,
    update_narrative_threads,
)


class _RecordingFakeTurnGraph:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.last_kwargs: dict[str, Any] = {}

    def run(self, **kwargs: Any) -> dict[str, Any]:
        self.last_kwargs = dict(kwargs)
        return self._payload


def _envelope(
    *,
    interpreted_input: dict[str, Any],
    generation: dict[str, Any],
) -> dict[str, Any]:
    gen = dict(generation)
    if "content" not in gen and "model_raw_text" not in gen:
        gen["content"] = "x" * 120
    return {
        "interpreted_input": interpreted_input,
        "generation": gen,
        "graph_diagnostics": {"errors": []},
        "retrieval": {"domain": "runtime", "status": "ok"},
        "routing": {"selected_model": "mock"},
        "validation_outcome": {"status": "approved", "reason": "test_fixture"},
        "visible_output_bundle": {"gm_narration": ["Fixture opening narration for tests."]},
        "committed_result": {"commit_applied": True, "committed_effects": []},
    }


@pytest.fixture
def manager() -> StoryRuntimeManager:
    return StoryRuntimeManager()


def test_thread_creation_from_repeated_ambiguity(manager: StoryRuntimeManager) -> None:
    g = _RecordingFakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8, "ambiguity": "vague"},
            generation={"success": True, "metadata": {}},
        )
    )
    manager.turn_graph = g  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    manager.execute_turn(session_id=session.session_id, player_input="a")
    assert len(session.narrative_threads.active) >= 1
    assert any(t.thread_kind == "interpretation_pressure" for t in session.narrative_threads.active)
    manager.execute_turn(session_id=session.session_id, player_input="b")
    ip = [t for t in session.narrative_threads.active if t.thread_kind == "interpretation_pressure"]
    assert ip and ip[0].intensity >= 1


def test_same_scene_escalation_across_turns(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _RecordingFakeTurnGraph(  # type: ignore[assignment]
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8, "ambiguity": "x"},
            generation={"success": True, "metadata": {}},
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    for _ in range(3):
        manager.execute_turn(session_id=session.session_id, player_input="?")
    kinds = [t.status for t in session.narrative_threads.active if t.thread_kind == "interpretation_pressure"]
    assert any(s == "escalating" for s in kinds)


def test_deadlock_hold_pattern_blocked(monkeypatch: pytest.MonkeyPatch, manager: StoryRuntimeManager) -> None:
    def _fake_resolve(**kwargs: Any) -> tuple[str | None, str | None, list[dict[str, Any]], str | None]:
        return (
            "scene_99",
            "player_input_token_scan",
            [{"source": "player_input_token_scan", "scene_id": "scene_99"}],
            None,
        )

    monkeypatch.setattr(commit_models, "_resolve_scene_proposal", _fake_resolve)

    manager.turn_graph = _RecordingFakeTurnGraph(  # type: ignore[assignment]
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8},
            generation={"success": True, "metadata": {}},
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )
    for _ in range(2):
        manager.execute_turn(session_id=session.session_id, player_input="x")
    blocked_threads = [t for t in session.narrative_threads.active if t.thread_kind == "progression_blocked"]
    assert blocked_threads
    assert any(t.status == "holding" for t in blocked_threads)


def test_de_escalation_from_clean_continue(manager: StoryRuntimeManager) -> None:
    fake = _RecordingFakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8, "ambiguity": "z"},
            generation={"success": True, "metadata": {}},
        )
    )
    manager.turn_graph = fake  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    manager.execute_turn(session_id=session.session_id, player_input="one")
    before = next(t.intensity for t in session.narrative_threads.active if t.thread_kind == "interpretation_pressure")
    fake._payload = _envelope(
        interpreted_input={"kind": "speech", "confidence": 0.9},
        generation={"success": True, "metadata": {}},
    )
    manager.execute_turn(session_id=session.session_id, player_input="two")
    after_threads = [t for t in session.narrative_threads.active if t.thread_kind == "interpretation_pressure"]
    after = after_threads[0].intensity if after_threads else 0
    assert after < before


def test_terminal_resolves_active_threads(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _RecordingFakeTurnGraph(  # type: ignore[assignment]
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8, "ambiguity": "t"},
            generation={"success": True, "metadata": {}},
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_end", "terminal": True}],
            "transition_hints": [{"from": "scene_1", "to": "scene_end"}],
            "terminal_scene_ids": ["scene_end"],
        },
    )
    manager.execute_turn(session_id=session.session_id, player_input="pressure")
    assert session.narrative_threads.active
    manager.turn_graph = _RecordingFakeTurnGraph(  # type: ignore[assignment]
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8},
            generation={
                "success": True,
                "metadata": {
                    "structured_output": {
                        "narrative_response": "End",
                        "proposed_scene_id": "scene_end",
                        "intent_summary": "",
                    }
                },
            },
        )
    )
    manager.execute_turn(session_id=session.session_id, player_input="finish")
    assert not session.narrative_threads.active
    assert session.narrative_threads.resolved_recent


def test_deterministic_eviction_at_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.story_runtime.narrative_threads.MAX_ACTIVE_THREADS", 2)
    prior = StoryNarrativeThreadSet(active=[], resolved_recent=[])
    tail: list[dict[str, Any]] = []
    scenes = ["s1", "s2", "s3"]
    for i, sc in enumerate(scenes):
        commit = {
            "committed_scene_id": sc,
            "situation_status": "blocked",
            "committed_consequences": ["proposal_blocked:illegal_transition"],
            "open_pressures": [],
            "is_terminal": False,
            "committed_interpretation_summary": {},
        }
        prior, _trace = update_narrative_threads(
            prior=prior,
            latest_commit=commit,
            history_tail=list(tail),
            committed_scene_id=sc,
            turn_number=i + 1,
        )
        tail.append({"turn_number": i + 1, "narrative_commit": commit})
    assert len(prior.active) <= 2


def test_get_state_exposes_thread_continuity(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _RecordingFakeTurnGraph(  # type: ignore[assignment]
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8, "ambiguity": "g"},
            generation={"success": True, "metadata": {}},
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    manager.execute_turn(session_id=session.session_id, player_input="x")
    state = manager.get_state(session.session_id)
    nc = state["committed_state"]["narrative_thread_continuity"]
    assert "narrative_threads" in nc
    assert "thread_count" in nc
    assert "dominant_thread_kind" in nc
    assert "thread_pressure_level" in nc
    assert "last_narrative_thread_update_summary" in nc


def test_get_diagnostics_trace_separate_from_continuity(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _RecordingFakeTurnGraph(  # type: ignore[assignment]
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8, "ambiguity": "h"},
            generation={"success": True, "metadata": {}},
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    manager.execute_turn(session_id=session.session_id, player_input="y")
    diag = manager.get_diagnostics(session.session_id)
    assert "narrative_thread_diagnostics" in diag
    assert diag["narrative_thread_diagnostics"]["last_update_trace"] is not None
    assert "authoritative" in diag["committed_truth_vs_diagnostics"].lower() or "narrative_thread" in diag[
        "committed_truth_vs_diagnostics"
    ]


def test_compact_thread_context_passed_to_graph_bounded(manager: StoryRuntimeManager) -> None:
    fake = _RecordingFakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8, "ambiguity": "p"},
            generation={"success": True, "metadata": {}},
        )
    )
    manager.turn_graph = fake  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    manager.execute_turn(session_id=session.session_id, player_input="t1")
    t1_threads = fake.last_kwargs.get("active_narrative_threads")
    assert t1_threads is None or t1_threads == [] or isinstance(t1_threads, list)
    manager.execute_turn(session_id=session.session_id, player_input="t2")
    threads = fake.last_kwargs.get("active_narrative_threads")
    assert isinstance(threads, list)
    assert len(threads) <= GRAPH_EXPORT_MAX_ACTIVE
    for item in threads:
        assert isinstance(item, dict)
        assert set(item.keys()) <= {
            "thread_id",
            "thread_kind",
            "status",
            "intensity",
            "related_entities",
            "resolution_hint",
        }
        assert "evidence_tokens" not in item
    summ = fake.last_kwargs.get("thread_pressure_summary")
    if isinstance(summ, str):
        assert len(summ) <= THREAD_PRESSURE_SUMMARY_MAX


def test_prior_social_state_passed_to_graph_from_committed_planner_truth(
    manager: StoryRuntimeManager,
) -> None:
    manager.turn_graph = _RecordingFakeTurnGraph(  # type: ignore[assignment]
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8},
            generation={"success": True, "metadata": {}},
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    prior_record = {
        "prior_continuity_classes": ["blame_pressure"],
        "scene_pressure_state": "high_blame",
        "active_thread_count": 1,
        "thread_pressure_summary_present": True,
        "guidance_phase_key": "phase_2_moral_negotiation",
        "responder_asymmetry_code": "blame_on_host_spouse_axis",
        "social_risk_band": "high",
        "social_continuity_status": "initial_social_state",
    }
    session.history.append(
        {
            "turn_number": 99,
            "narrative_commit": {
                "planner_truth": {
                    "social_state_summary": {
                        "summary_source": "social_state_record",
                        "record": prior_record,
                    }
                }
            },
        }
    )

    fake = _RecordingFakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8},
            generation={"success": True, "metadata": {}},
        )
    )
    manager.turn_graph = fake  # type: ignore[assignment]
    manager.execute_turn(session_id=session.session_id, player_input="continue")

    assert fake.last_kwargs["prior_social_state_record"] == prior_record


def test_prior_planner_truth_passed_to_graph_from_committed_truth(
    manager: StoryRuntimeManager,
) -> None:
    manager.turn_graph = _RecordingFakeTurnGraph(  # type: ignore[assignment]
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8},
            generation={"success": True, "metadata": {}},
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    planner_truth = {
        "selected_scene_function": "redirect_blame",
        "responder_id": "michel_longstreet",
        "responder_scope": ["michel_longstreet", "annette_reille"],
        "function_type": "pressure_probe",
        "pacing_mode": "compressed",
        "scene_assessment_core": {"pressure_state": "thread_pressure_high"},
        "social_outcome": "tension_escalates",
        "dramatic_direction": "humiliation_spikes",
        "continuity_impacts": [{"class": "blame_pressure"}],
        "validator_layers_used": ["dramatic_effect_gate"],
    }
    session.history.append(
        {
            "turn_number": 99,
            "narrative_commit": {
                "planner_truth": planner_truth,
            },
        }
    )

    fake = _RecordingFakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8},
            generation={"success": True, "metadata": {}},
        )
    )
    manager.turn_graph = fake  # type: ignore[assignment]
    manager.execute_turn(session_id=session.session_id, player_input="continue")

    prior = fake.last_kwargs["prior_planner_truth"]
    assert prior["selected_scene_function"] == "redirect_blame"
    assert prior["responder_scope"] == ["michel_longstreet", "annette_reille"]
    assert prior["function_type"] == "pressure_probe"
    assert prior["continuity_impacts"] == [{"class": "blame_pressure"}]
    assert "validator_layers_used" not in prior


def test_prior_narrative_thread_state_passed_to_graph_from_session_threads(
    manager: StoryRuntimeManager,
) -> None:
    manager.turn_graph = _RecordingFakeTurnGraph(  # type: ignore[assignment]
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8},
            generation={"success": True, "metadata": {}},
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    session.narrative_threads = StoryNarrativeThreadSet(
        active=[
            StoryNarrativeThread(
                thread_id="threadabcdef123456",
                thread_kind="progression_blocked",
                status="holding",
                scene_anchor="scene_1",
                intensity=4,
                persistence_turns=2,
                related_scenes=["scene_1"],
                related_entities=["alain_reille"],
                evidence_tokens=["blocked"],
                last_updated_turn=1,
                resolution_hint="blocked",
            )
        ],
        resolved_recent=[],
    )

    fake = _RecordingFakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8},
            generation={"success": True, "metadata": {}},
        )
    )
    manager.turn_graph = fake  # type: ignore[assignment]
    manager.execute_turn(session_id=session.session_id, player_input="continue")

    state = fake.last_kwargs["prior_narrative_thread_state"]
    assert state["source"] == "session.narrative_threads"
    assert state["dominant_thread_kind"] == "progression_blocked"
    assert state["thread_pressure_level"] == 4
    assert state["active_threads"][0]["related_entities"] == ["alain_reille"]


def test_committed_dramatic_context_reaches_history_story_window_and_shell(
    manager: StoryRuntimeManager,
) -> None:
    payload = _envelope(
        interpreted_input={"kind": "speech", "confidence": 0.8},
        generation={"success": True, "metadata": {}},
    )
    payload.update(
        {
            "selected_scene_function": "redirect_blame",
            "selected_responder_set": [{"actor_id": "michel_longstreet"}],
            "responder_id": "michel_longstreet",
            "function_type": "pressure_probe",
            "pacing_mode": "compressed",
            "silence_brevity_decision": {"mode": "brief"},
            "scene_assessment": {
                "pressure_state": "thread_pressure_high",
                "thread_pressure_state": "thread_pressure_high",
                "assessment_summary": "Blame is being redirected through the room.",
            },
            "social_outcome": "tension_escalates",
            "dramatic_direction": "humiliation_spikes",
            "social_state_record": {
                "prior_continuity_classes": ["blame_pressure"],
                "scene_pressure_state": "high_blame",
                "active_thread_count": 1,
                "thread_pressure_summary_present": True,
                "guidance_phase_key": "phase_2_moral_negotiation",
                "responder_asymmetry_code": "blame_on_host_spouse_axis",
                "social_risk_band": "high",
                "social_continuity_status": "initial_social_state",
            },
            "continuity_impacts": [{"class": "blame_pressure"}],
            "retrieval": {
                "domain": "runtime",
                "status": "ok",
                "retrieval_route": "sparse_fallback",
                "continuity_query_signal": {
                    "attached": True,
                    "sources": ["prior_planner_truth"],
                },
            },
        }
    )
    fake = _RecordingFakeTurnGraph(payload)
    manager.turn_graph = fake  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    turn = manager.execute_turn(session_id=session.session_id, player_input="continue")

    context = turn["dramatic_context_summary"]
    assert context["contract"] == "bounded_dramatic_context.v1"
    assert context["selected_scene_function"] == "redirect_blame"
    assert context["responder"]["responder_id"] == "michel_longstreet"
    assert context["scene_assessment"]["pressure_state"] == "thread_pressure_high"
    assert context["social_state"]["social_risk_band"] == "high"
    assert context["retrieval_context"]["continuity_query_attached"] is True
    assert turn["runtime_governance_surface"]["dramatic_context_summary"] == context
    assert session.history[-1]["dramatic_context_summary"] == context

    state = manager.get_state(session.session_id)
    assert state["module_scope_truth"]["requested_module_id"] == "m"
    assert state["module_scope_truth"]["requested_module_supported"] is False
    assert state["committed_state"]["module_scope_truth"]["runtime_scope"] == "module_specific"
    shell_context = state["committed_state"]["player_shell_context"]
    assert shell_context["contract"] == "player_shell_dramatic_context.v1"
    assert shell_context["selected_scene_function"] == "redirect_blame"
    assert shell_context["pressure_state"] == "thread_pressure_high"
    latest_entry = state["story_window"]["latest_entry"]
    assert latest_entry["dramatic_context_summary"]["contract"] == "story_window_dramatic_context.v1"
    assert latest_entry["authority_summary"]["dramatic_context"]["social_risk_band"] == "high"


def test_no_trace_history_accumulation_on_session(manager: StoryRuntimeManager) -> None:
    fake = _RecordingFakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8, "ambiguity": "q"},
            generation={"success": True, "metadata": {}},
        )
    )
    manager.turn_graph = fake  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    manager.execute_turn(session_id=session.session_id, player_input="a")
    manager.execute_turn(session_id=session.session_id, player_input="b")
    assert session.last_thread_update_trace is not None
    assert len(session.last_thread_update_trace.rules_fired) <= 16
    assert not hasattr(session, "thread_update_trace_history")
