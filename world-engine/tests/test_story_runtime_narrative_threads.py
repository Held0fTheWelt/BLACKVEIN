"""Tests for bounded narrative threads derived from Task B narrative commits."""

from __future__ import annotations

from typing import Any

import pytest

from app.story_runtime import StoryRuntimeManager, commit_models
from app.story_runtime.narrative_threads import (
    GRAPH_EXPORT_MAX_ACTIVE,
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
    return {
        "interpreted_input": interpreted_input,
        "generation": generation,
        "graph_diagnostics": {"errors": []},
        "retrieval": {"domain": "runtime", "status": "ok"},
        "routing": {"selected_model": "mock"},
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
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_end", "terminal": True}],
            "transition_hints": [{"from": "scene_1", "to": "scene_end"}],
            "terminal_scene_ids": ["scene_end"],
        },
    )
    manager.turn_graph = _RecordingFakeTurnGraph(  # type: ignore[assignment]
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8, "ambiguity": "t"},
            generation={"success": True, "metadata": {}},
        )
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
    assert fake.last_kwargs.get("active_narrative_threads") in (None, [])
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
