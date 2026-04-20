"""Focused tests for the narrative commit kernel (bounded authoritative commit vs diagnostics)."""

from __future__ import annotations

from typing import Any

import pytest

from app.story_runtime import StoryRuntimeManager
from app.story_runtime import commit_models
from app.story_runtime.commit_models import StoryNarrativeCommitRecord


class _FakeTurnGraph:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def run(self, **kwargs: Any) -> dict[str, Any]:
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


def test_no_proposal_continues_current_scene_with_bounded_consequences(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.9},
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
    turn = manager.execute_turn(session_id=session.session_id, player_input="Hello there.")
    nc = turn["narrative_commit"]
    assert nc["commit_reason_code"] == "no_scene_proposal"
    assert nc["situation_status"] == "continue"
    assert nc["committed_scene_id"] == "scene_1"
    assert any(c.startswith("interpretation_kind:") for c in nc["committed_consequences"])


def test_explicit_command_beats_model_and_token_scan(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={
                "kind": "explicit_command",
                "command_name": "move",
                "command_args": ["scene_2"],
                "confidence": 0.99,
            },
            generation={
                "success": True,
                "metadata": {
                    "structured_output": {
                        "narrative_response": "",
                        "proposed_scene_id": "scene_3",
                        "intent_summary": "",
                    }
                },
            },
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}, {"id": "scene_3"}],
            "transition_hints": [
                {"from": "scene_1", "to": "scene_2"},
                {"from": "scene_2", "to": "scene_3"},
            ],
        },
    )
    turn = manager.execute_turn(
        session_id=session.session_id,
        player_input="/move scene_2 scene_3 noise",
    )
    nc = turn["narrative_commit"]
    assert nc["selected_candidate_source"] == "explicit_command"
    assert nc["committed_scene_id"] == "scene_2"
    assert nc["allowed"] is True


def test_legal_model_proposal_commits_transition(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8},
            generation={
                "success": True,
                "metadata": {
                    "structured_output": {
                        "narrative_response": "You advance.",
                        "proposed_scene_id": "scene_2",
                        "intent_summary": "",
                    }
                },
            },
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
    turn = manager.execute_turn(session_id=session.session_id, player_input="I walk forward.")
    nc = turn["narrative_commit"]
    assert nc["allowed"] is True
    assert nc["situation_status"] == "transitioned"
    assert nc["selected_candidate_source"] == "model_structured_output"
    assert "scene_transition:scene_1->scene_2" in nc["committed_consequences"]


def test_illegal_proposal_is_blocked_committed_truth(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={
                "kind": "explicit_command",
                "command_name": "move",
                "command_args": ["scene_3"],
                "confidence": 0.99,
            },
            generation={"success": True, "metadata": {}},
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}, {"id": "scene_3"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )
    turn = manager.execute_turn(session_id=session.session_id, player_input="/move scene_3")
    nc = turn["narrative_commit"]
    assert nc["allowed"] is False
    assert nc["situation_status"] == "blocked"
    assert nc["commit_reason_code"] == "illegal_transition_not_allowed"
    assert nc["committed_scene_id"] == "scene_1"
    assert "proposal_blocked:illegal_transition" in nc["committed_consequences"]


def test_token_scan_proposal_commits_only_when_legal_and_known(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.7},
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
    turn = manager.execute_turn(
        session_id=session.session_id,
        player_input="We continue in scene_2 now.",
    )
    nc = turn["narrative_commit"]
    assert nc["selected_candidate_source"] == "player_input_token_scan"
    assert nc["allowed"] is True
    assert nc["committed_scene_id"] == "scene_2"


def test_already_in_scene_yields_continue_semantics(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={
                "kind": "explicit_command",
                "command_name": "move",
                "command_args": ["scene_1"],
                "confidence": 0.99,
            },
            generation={"success": True, "metadata": {}},
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}],
            "transition_hints": [],
        },
    )
    turn = manager.execute_turn(session_id=session.session_id, player_input="/move scene_1")
    nc = turn["narrative_commit"]
    assert nc["commit_reason_code"] == "already_in_scene"
    assert nc["situation_status"] == "continue"
    assert nc["committed_scene_id"] == "scene_1"
    assert "scene_continue:scene_1" in nc["committed_consequences"]


def test_history_holds_authoritative_commit_diagnostics_hold_envelope(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8},
            generation={"success": True, "metadata": {}},
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    manager.execute_turn(session_id=session.session_id, player_input="Hi")
    hist = manager.get_session(session.session_id).history[-1]
    diag = manager.get_session(session.session_id).diagnostics[-1]
    assert "narrative_commit" in hist
    assert "graph" not in hist
    assert "interpreted_input" not in hist
    assert "narrative_commit" in diag
    assert "graph" in diag
    assert "retrieval" in diag
    assert "interpreted_input" in diag


def test_get_state_and_get_diagnostics_reflect_separation(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.85, "ambiguity": "test_ambiguity"},
            generation={"success": True, "metadata": {}},
        )
    )
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )
    manager.execute_turn(session_id=session.session_id, player_input="thinking")
    state = manager.get_state(session.session_id)
    diag = manager.get_diagnostics(session.session_id)
    assert state["committed_state"]["last_narrative_commit"] is not None
    assert state["committed_state"]["last_narrative_commit_summary"]["situation_status"] == "continue"
    assert "committed_truth_vs_diagnostics" in diag
    assert diag["authoritative_history_tail"][-1]["narrative_commit"]["open_pressures"] == [
        "interpretation_ambiguity:test_ambiguity"
    ]
    assert "graph" in (diag["diagnostics"][-1])


def test_unknown_target_scene_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_resolve(**kwargs: Any) -> tuple[str | None, str | None, list[dict[str, Any]], str | None]:
        return (
            "scene_99",
            "player_input_token_scan",
            [{"source": "player_input_token_scan", "scene_id": "scene_99"}],
            None,
        )

    monkeypatch.setattr(commit_models, "_resolve_scene_proposal", _fake_resolve)
    manager = StoryRuntimeManager()
    manager.turn_graph = _FakeTurnGraph(
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
    turn = manager.execute_turn(session_id=session.session_id, player_input="x")
    nc = turn["narrative_commit"]
    assert nc["commit_reason_code"] == "unknown_target_scene"
    assert nc["situation_status"] == "blocked"


def test_terminal_scene_sets_terminal_status(manager: StoryRuntimeManager) -> None:
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_end", "terminal": True}],
            "transition_hints": [{"from": "scene_1", "to": "scene_end"}],
            "terminal_scene_ids": ["scene_end"],
        },
    )
    manager.turn_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={"kind": "speech", "confidence": 0.8},
            generation={
                "success": True,
                "metadata": {
                    "structured_output": {
                        "narrative_response": "Fin.",
                        "proposed_scene_id": "scene_end",
                        "intent_summary": "",
                    }
                },
            },
        )
    )
    turn = manager.execute_turn(session_id=session.session_id, player_input="The end.")
    nc = turn["narrative_commit"]
    assert nc["allowed"] is True
    assert nc["situation_status"] == "terminal"
    assert nc["is_terminal"] is True


def test_execute_turn_threads_previous_visible_reply_context_into_next_addressed_output(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SequentialTurnGraph:
        def __init__(self, payloads: list[dict[str, Any]]) -> None:
            self._payloads = payloads
            self._index = 0

        def run(self, **kwargs: Any) -> dict[str, Any]:
            payload = self._payloads[self._index]
            self._index += 1
            return payload

    records = [
        StoryNarrativeCommitRecord(
            turn_number=1,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
        StoryNarrativeCommitRecord(
            turn_number=2,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_call_reframed_as_humiliation_pressure"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
    ]

    def _fake_resolve(**kwargs: Any) -> StoryNarrativeCommitRecord:
        return records.pop(0)

    monkeypatch.setattr("app.story_runtime.manager.resolve_narrative_commit", _fake_resolve)

    manager = StoryRuntimeManager()
    manager.turn_graph = _SequentialTurnGraph(
        [
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "repair_or_stabilize",
                "selected_responder_set": [{"actor_id": "annette"}],
                "social_state_record": {"scene_pressure_state": "moderate_tension", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["She turns it back on him."]},
            },
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "withhold_or_evade",
                "selected_responder_set": [{"actor_id": "alain"}],
                "social_state_record": {"scene_pressure_state": "moderate_tension", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["He tries to slide away from it."]},
            },
        ]
    )  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "living_room_main", "scenes": [{"id": "living_room_main"}]},
    )

    manager.execute_turn(session_id=session.session_id, player_input="first")
    turn_two = manager.execute_turn(session_id=session.session_id, player_input="second")

    assert turn_two["shell_readout_projection"]["response_exchange_now"] == "Your act drew an evasive pressure answer because it put the phone under pressure again, buying a beat on the same phone instead of answering it, with the earlier humiliation line still sitting on the phone, and let the reply pull the room toward manageability without ever resolving it."
    assert turn_two["visible_output_bundle_addressed"]["gm_narration"][0].startswith(
        "Alain, from the guest side, answers in evasive pressure with guest-side humiliation on the phone, in a tired evasive hedge dressed up as mediation, buying a beat on the same phone instead of answering it, the earlier humiliation line still sitting on the phone — He tries to slide away from it."
    )
    state = manager.get_state(session.session_id)
    assert state["committed_state"]["previous_reply_continuity_context"]["exchange_label"] == "exposure"
    assert state["committed_state"]["previous_reply_continuity_context"]["surface_token"] == "phone"



def test_execute_turn_can_reuse_earlier_visible_reply_after_intervening_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SequentialTurnGraph:
        def __init__(self, payloads: list[dict[str, Any]]) -> None:
            self._payloads = payloads
            self._index = 0

        def run(self, **kwargs: Any) -> dict[str, Any]:
            payload = self._payloads[self._index]
            self._index += 1
            return payload

    records = [
        StoryNarrativeCommitRecord(
            turn_number=1,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["book_handling_reframed_as_status_judgment"],
            open_pressures=["art_book_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
        StoryNarrativeCommitRecord(
            turn_number=2,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
        StoryNarrativeCommitRecord(
            turn_number=3,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["book_handling_reframed_as_status_judgment_again"],
            open_pressures=["art_book_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
    ]

    def _fake_resolve(**kwargs: Any) -> StoryNarrativeCommitRecord:
        return records.pop(0)

    monkeypatch.setattr("app.story_runtime.manager.resolve_narrative_commit", _fake_resolve)

    manager = StoryRuntimeManager()
    manager.turn_graph = _SequentialTurnGraph(
        [
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "repair_or_stabilize",
                "selected_responder_set": [{"actor_id": "veronique"}],
                "social_state_record": {
                    "scene_pressure_state": "moderate_tension",
                    "social_risk_band": "high",
                    "responder_asymmetry_code": "alliance_reposition_active",
                },
                "visible_output_bundle": {"gm_narration": ["She tries to put manners back on it."]},
            },
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "withhold_or_evade",
                "selected_responder_set": [{"actor_id": "alain"}],
                "social_state_record": {"scene_pressure_state": "moderate_tension", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["He tries to slide past it."]},
            },
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "redirect_blame",
                "selected_responder_set": [{"actor_id": "annette"}],
                "social_state_record": {
                    "scene_pressure_state": "high_blame",
                    "social_risk_band": "high",
                    "responder_asymmetry_code": "alliance_reposition_active",
                },
                "visible_output_bundle": {"gm_narration": ["She brings it back to the books."]},
            },
        ]
    )  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "living_room_main", "scenes": [{"id": "living_room_main"}]},
    )

    manager.execute_turn(session_id=session.session_id, player_input="first")
    manager.execute_turn(session_id=session.session_id, player_input="second")
    turn_three = manager.execute_turn(session_id=session.session_id, player_input="third")

    assert turn_three["shell_readout_projection"]["response_exchange_now"] == "Your act drew an accusation answer because it put the books under pressure again, bringing the earlier accusation back onto the same books, with the earlier taste-and-status wound still sitting on the books, and let the reply pull the room back to exposed contradiction instead of letting manners cover it."
    assert turn_three["visible_output_bundle_addressed"]["gm_narration"][0].startswith(
        "Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, in a cutting contradiction that treats principle as performance, bringing the earlier accusation back onto the same books, the earlier taste-and-status wound still sitting on the books — She brings it back to the books."
    )
    state = manager.get_state(session.session_id)
    assert state["committed_state"]["previous_reply_continuity_context"]["exchange_label"] == "evasive pressure"
    assert state["committed_state"]["earlier_reply_continuity_context"]["exchange_label"] == "accusation"
    assert state["committed_state"]["earlier_reply_continuity_context"]["surface_token"] == "books"



def test_execute_turn_forces_reentry_after_same_surface_dodge(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SequentialTurnGraph:
        def __init__(self, payloads: list[dict[str, Any]]) -> None:
            self._payloads = payloads
            self._index = 0

        def run(self, **kwargs: Any) -> dict[str, Any]:
            payload = self._payloads[self._index]
            self._index += 1
            return payload

    records = [
        StoryNarrativeCommitRecord(
            turn_number=1,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
        StoryNarrativeCommitRecord(
            turn_number=2,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure_again"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
    ]

    def _fake_resolve(**kwargs: Any) -> StoryNarrativeCommitRecord:
        return records.pop(0)

    monkeypatch.setattr("app.story_runtime.manager.resolve_narrative_commit", _fake_resolve)

    manager = StoryRuntimeManager()
    manager.turn_graph = _SequentialTurnGraph(
        [
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "withhold_or_evade",
                "selected_responder_set": [{"actor_id": "alain"}],
                "social_state_record": {"scene_pressure_state": "moderate_tension", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["He tries to let the call swallow the point."]},
            },
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "redirect_blame",
                "selected_responder_set": [{"actor_id": "annette"}],
                "social_state_record": {"scene_pressure_state": "high_blame", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["She cuts back across the dodge."]},
            },
        ]
    )  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "living_room_main", "scenes": [{"id": "living_room_main"}]},
    )

    manager.execute_turn(session_id=session.session_id, player_input="first")
    turn_two = manager.execute_turn(session_id=session.session_id, player_input="second")

    assert turn_two["shell_readout_projection"]["response_exchange_now"] == "Your act drew an exposure answer because it put the phone under pressure again, cutting back in before the dodge on the same phone can go quiet, with the earlier humiliation line still sitting on the phone, and let the reply pull the room toward exposure instead of polite cover."
    assert turn_two["visible_output_bundle_addressed"]["gm_narration"][0].startswith(
        "Annette, from the guest side, answers in exposure with guest-side humiliation on the phone, in a contemptuous dismantling that strips courtesy down to appetite, cutting back in before the dodge on the same phone can go quiet, the earlier humiliation line still sitting on the phone — She cuts back across the dodge."
    )
    state = manager.get_state(session.session_id)
    assert state["committed_state"]["previous_reply_continuity_context"]["exchange_label"] == "evasive pressure"
    assert state["committed_state"]["previous_reply_continuity_context"]["surface_token"] == "phone"
    assert state["committed_state"]["earlier_reply_continuity_context"] is None



def test_execute_turn_marks_same_surface_evasion_as_buying_a_beat(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SequentialTurnGraph:
        def __init__(self, payloads: list[dict[str, Any]]) -> None:
            self._payloads = payloads
            self._index = 0

        def run(self, **kwargs: Any) -> dict[str, Any]:
            payload = self._payloads[self._index]
            self._index += 1
            return payload

    records = [
        StoryNarrativeCommitRecord(
            turn_number=1,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
        StoryNarrativeCommitRecord(
            turn_number=2,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure_again"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
    ]

    def _fake_resolve(**kwargs: Any) -> StoryNarrativeCommitRecord:
        return records.pop(0)

    monkeypatch.setattr("app.story_runtime.manager.resolve_narrative_commit", _fake_resolve)

    manager = StoryRuntimeManager()
    manager.turn_graph = _SequentialTurnGraph(
        [
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "redirect_blame",
                "selected_responder_set": [{"actor_id": "annette"}],
                "social_state_record": {"scene_pressure_state": "high_blame", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["She cuts directly at him."]},
            },
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "withhold_or_evade",
                "selected_responder_set": [{"actor_id": "alain"}],
                "social_state_record": {"scene_pressure_state": "moderate_tension", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["He stalls on the phone instead of answering."]},
            },
        ]
    )  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "living_room_main", "scenes": [{"id": "living_room_main"}]},
    )

    manager.execute_turn(session_id=session.session_id, player_input="first")
    turn_two = manager.execute_turn(session_id=session.session_id, player_input="second")

    assert turn_two["shell_readout_projection"]["response_exchange_now"] == "Your act drew an evasive pressure answer because it put the phone under pressure again, buying a beat on the same phone instead of answering it, with the earlier humiliation line still sitting on the phone, and let the reply pull the room toward manageability without ever resolving it."
    assert turn_two["visible_output_bundle_addressed"]["gm_narration"][0].startswith(
        "Alain, from the guest side, answers in evasive pressure with guest-side humiliation on the phone, in a tired evasive hedge dressed up as mediation, buying a beat on the same phone instead of answering it, the earlier humiliation line still sitting on the phone — He stalls on the phone instead of answering."
    )



def test_execute_turn_breaks_earlier_pause_back_over_same_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SequentialTurnGraph:
        def __init__(self, payloads: list[dict[str, Any]]) -> None:
            self._payloads = payloads
            self._index = 0

        def run(self, **kwargs: Any) -> dict[str, Any]:
            payload = self._payloads[self._index]
            self._index += 1
            return payload

    records = [
        StoryNarrativeCommitRecord(
            turn_number=1,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["hosting_surface_pressure_rising"],
            open_pressures=["hosting_surface_pressure", "drink_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
        StoryNarrativeCommitRecord(
            turn_number=2,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
        StoryNarrativeCommitRecord(
            turn_number=3,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["hosting_surface_pressure_rising_again"],
            open_pressures=["hosting_surface_pressure", "drink_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
    ]

    def _fake_resolve(**kwargs: Any) -> StoryNarrativeCommitRecord:
        return records.pop(0)

    monkeypatch.setattr("app.story_runtime.manager.resolve_narrative_commit", _fake_resolve)

    manager = StoryRuntimeManager()
    manager.turn_graph = _SequentialTurnGraph(
        [
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "withhold_or_evade",
                "selected_responder_set": [{"actor_id": "michel"}],
                "social_state_record": {"scene_pressure_state": "moderate_tension", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["He lets the hosting surface hold the pause."]},
            },
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "withhold_or_evade",
                "selected_responder_set": [{"actor_id": "alain"}],
                "social_state_record": {"scene_pressure_state": "moderate_tension", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["He tries to let the phone absorb it."]},
            },
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "redirect_blame",
                "selected_responder_set": [{"actor_id": "michel"}],
                "social_state_record": {
                    "scene_pressure_state": "high_blame",
                    "social_risk_band": "high",
                },
                "visible_output_bundle": {"gm_narration": ["He drags the hosting surface back into it."]},
            },
        ]
    )  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "living_room_main", "scenes": [{"id": "living_room_main"}]},
    )

    manager.execute_turn(session_id=session.session_id, player_input="first")
    manager.execute_turn(session_id=session.session_id, player_input="second")
    turn_three = manager.execute_turn(session_id=session.session_id, player_input="third")

    assert turn_three["shell_readout_projection"]["response_exchange_now"] == "Your act drew a containment answer because it put the hosting surface under pressure again, breaking the earlier pause back over the same hosting surface, with the earlier hospitality-and-hosting line still sitting over the hosting surface, and let the reply pull the room back toward manners instead of open alignment."
    assert turn_three["visible_output_bundle_addressed"]["gm_narration"][0].startswith(
        "Michel, from the host side, answers in containment with host-side hospitality strain over the hosting surface, in a smoothing deflection that offers hospitality instead of alignment, breaking the earlier pause back over the same hosting surface, the earlier hospitality-and-hosting line still sitting over the hosting surface — He drags the hosting surface back into it."
    )


def test_execute_turn_reopens_same_surface_through_dodge_before_point_can_die(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SequentialTurnGraph:
        def __init__(self, payloads: list[dict[str, Any]]) -> None:
            self._payloads = payloads
            self._index = 0

        def run(self, **kwargs: Any) -> dict[str, Any]:
            payload = self._payloads[self._index]
            self._index += 1
            return payload

    records = [
        StoryNarrativeCommitRecord(
            turn_number=1,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
        StoryNarrativeCommitRecord(
            turn_number=2,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure_again"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
        StoryNarrativeCommitRecord(
            turn_number=3,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure_again_again"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
    ]

    def _fake_resolve(**kwargs: Any) -> StoryNarrativeCommitRecord:
        return records.pop(0)

    monkeypatch.setattr("app.story_runtime.manager.resolve_narrative_commit", _fake_resolve)

    manager = StoryRuntimeManager()
    manager.turn_graph = _SequentialTurnGraph(
        [
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "redirect_blame",
                "selected_responder_set": [{"actor_id": "annette"}],
                "social_state_record": {"scene_pressure_state": "high_blame", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["She presses the phone back into the point."]},
            },
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "withhold_or_evade",
                "selected_responder_set": [{"actor_id": "alain"}],
                "social_state_record": {"scene_pressure_state": "moderate_tension", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["He tries to talk around the phone."]},
            },
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "redirect_blame",
                "selected_responder_set": [{"actor_id": "annette"}],
                "social_state_record": {"scene_pressure_state": "high_blame", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["She reopens the phone before the dodge can settle."]},
            },
        ]
    )  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "living_room_main", "scenes": [{"id": "living_room_main"}]},
    )

    manager.execute_turn(session_id=session.session_id, player_input="first")
    manager.execute_turn(session_id=session.session_id, player_input="second")
    turn_three = manager.execute_turn(session_id=session.session_id, player_input="third")

    assert turn_three["shell_readout_projection"]["response_exchange_now"] == "Your act drew an exposure answer because it put the phone under pressure again, reopening the same phone through the dodge before the point can die, with the earlier humiliation line still sitting on the phone, and let the reply pull the room toward exposure instead of polite cover."
    assert turn_three["visible_output_bundle_addressed"]["gm_narration"][0].startswith(
        "Annette, from the guest side, answers in exposure with guest-side humiliation on the phone, in a contemptuous dismantling that strips courtesy down to appetite, reopening the same phone through the dodge before the point can die, the earlier humiliation line still sitting on the phone — She reopens the phone before the dodge can settle."
    )
    state = manager.get_state(session.session_id)
    assert state["committed_state"]["previous_reply_continuity_context"]["exchange_label"] == "evasive pressure"
    assert state["committed_state"]["previous_reply_continuity_context"]["surface_token"] == "phone"
    assert state["committed_state"]["earlier_reply_continuity_context"]["exchange_label"] == "exposure"
    assert state["committed_state"]["earlier_reply_continuity_context"]["surface_token"] == "phone"



def test_execute_turn_relay_picks_same_surface_up_across_the_room(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SequentialTurnGraph:
        def __init__(self, payloads: list[dict[str, Any]]) -> None:
            self._payloads = payloads
            self._index = 0

        def run(self, **kwargs: Any) -> dict[str, Any]:
            payload = self._payloads[self._index]
            self._index += 1
            return payload

    records = [
        StoryNarrativeCommitRecord(
            turn_number=1,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
        StoryNarrativeCommitRecord(
            turn_number=2,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure_again"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
    ]

    def _fake_resolve(**kwargs: Any) -> StoryNarrativeCommitRecord:
        return records.pop(0)

    monkeypatch.setattr("app.story_runtime.manager.resolve_narrative_commit", _fake_resolve)

    manager = StoryRuntimeManager()
    manager.turn_graph = _SequentialTurnGraph(
        [
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "redirect_blame",
                "selected_responder_set": [{"actor_id": "annette"}],
                "social_state_record": {"scene_pressure_state": "high_blame", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["She keeps the phone line open."]},
            },
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "redirect_blame",
                "selected_responder_set": [{"actor_id": "veronique"}],
                "social_state_record": {"scene_pressure_state": "high_blame", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["She picks the phone line up from across the room."]},
            },
        ]
    )  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "living_room_main", "scenes": [{"id": "living_room_main"}]},
    )

    manager.execute_turn(session_id=session.session_id, player_input="first")
    turn_two = manager.execute_turn(session_id=session.session_id, player_input="second")

    assert turn_two["shell_readout_projection"]["response_exchange_now"] == "Your act drew an exposure answer because it put the phone under pressure again, picking up the same phone across the room before it can cool, with the earlier humiliation line still sitting on the phone, and let the reply pull the room back toward answerability instead of comfort."
    assert turn_two["visible_output_bundle_addressed"]["gm_narration"][0].startswith(
        "Veronique, from the host side, answers in exposure with host-side humiliation on the phone, in a wounded moral indictment that refuses to let the hurt sound private, picking up the same phone across the room before it can cool, the earlier humiliation line still sitting on the phone — She picks the phone line up from across the room."
    )



def test_execute_turn_lets_same_pressure_jump_speakers_before_the_dodge_can_settle(monkeypatch: pytest.MonkeyPatch) -> None:
    class _SequentialTurnGraph:
        def __init__(self, payloads: list[dict[str, Any]]) -> None:
            self._payloads = payloads
            self._index = 0

        def run(self, **kwargs: Any) -> dict[str, Any]:
            payload = self._payloads[self._index]
            self._index += 1
            return payload

    records = [
        StoryNarrativeCommitRecord(
            turn_number=1,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
        StoryNarrativeCommitRecord(
            turn_number=2,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure_again"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
        StoryNarrativeCommitRecord(
            turn_number=3,
            prior_scene_id="living_room_main",
            proposed_scene_id=None,
            committed_scene_id="living_room_main",
            situation_status="continue",
            allowed=False,
            authoritative_reason="stay",
            commit_reason_code="no_scene_proposal",
            selected_candidate_source=None,
            candidate_sources=[],
            model_structured_proposed_scene_id=None,
            committed_interpretation_summary={},
            committed_consequences=["phone_interrupt_reframed_as_humiliation_pressure_again_again"],
            open_pressures=["phone_pressure"],
            resolved_pressures=[],
            is_terminal=False,
        ),
    ]

    def _fake_resolve(**kwargs: Any) -> StoryNarrativeCommitRecord:
        return records.pop(0)

    monkeypatch.setattr("app.story_runtime.manager.resolve_narrative_commit", _fake_resolve)

    manager = StoryRuntimeManager()
    manager.turn_graph = _SequentialTurnGraph(
        [
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "redirect_blame",
                "selected_responder_set": [{"actor_id": "annette"}],
                "social_state_record": {"scene_pressure_state": "high_blame", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["She presses the phone back into the point."]},
            },
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "withhold_or_evade",
                "selected_responder_set": [{"actor_id": "alain"}],
                "social_state_record": {"scene_pressure_state": "moderate_tension", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["He tries to talk around the phone."]},
            },
            {
                "interpreted_input": {"kind": "speech", "confidence": 0.8},
                "generation": {"success": True, "metadata": {}},
                "graph_diagnostics": {"errors": []},
                "retrieval": {"domain": "runtime", "status": "ok"},
                "routing": {"selected_model": "mock"},
                "selected_scene_function": "redirect_blame",
                "selected_responder_set": [{"actor_id": "veronique"}],
                "social_state_record": {"scene_pressure_state": "high_blame", "social_risk_band": "high"},
                "visible_output_bundle": {"gm_narration": ["She takes the phone line back before the dodge can settle."]},
            },
        ]
    )  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "living_room_main", "scenes": [{"id": "living_room_main"}]},
    )

    manager.execute_turn(session_id=session.session_id, player_input="first")
    manager.execute_turn(session_id=session.session_id, player_input="second")
    turn_three = manager.execute_turn(session_id=session.session_id, player_input="third")

    assert turn_three["shell_readout_projection"]["response_exchange_now"] == "Your act drew an exposure answer because it put the phone under pressure again, letting the same phone pressure jump speakers across the room before the dodge can settle, with the earlier humiliation line still sitting on the phone, and let the reply pull the room back toward answerability instead of comfort."
    assert turn_three["visible_output_bundle_addressed"]["gm_narration"][0].startswith(
        "Veronique, from the host side, answers in exposure with host-side humiliation on the phone, in a wounded moral indictment that refuses to let the hurt sound private, letting the same phone pressure jump speakers across the room before the dodge can settle, the earlier humiliation line still sitting on the phone — She takes the phone line back before the dodge can settle."
    )
    state = manager.get_state(session.session_id)
    assert state["committed_state"]["previous_reply_continuity_context"]["exchange_label"] == "evasive pressure"
    assert state["committed_state"]["previous_reply_continuity_context"]["responder_actor"] == "alain"
    assert state["committed_state"]["earlier_reply_continuity_context"]["exchange_label"] == "exposure"
    assert state["committed_state"]["earlier_reply_continuity_context"]["responder_actor"] == "annette"
