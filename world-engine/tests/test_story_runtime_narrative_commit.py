"""Focused tests for the narrative commit kernel (bounded authoritative commit vs diagnostics)."""

from __future__ import annotations

import concurrent.futures
from typing import Any

import pytest

from app.story_runtime import StoryRuntimeManager
from app.story_runtime import commit_models


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
        "visible_output_bundle": {"gm_narration": ["Fixture narration for commit tests."]},
        "committed_result": {"commit_applied": True, "committed_effects": []},
    }


def _opening_envelope(start_scene_id: str) -> dict[str, Any]:
    """Stable fake graph output for Turn 0 opening (stay on ``start_scene_id``)."""
    return _envelope(
        interpreted_input={"kind": "speech", "confidence": 0.9},
        generation={
            "success": True,
            "metadata": {
                "structured_output": {
                    "narrative_response": "Opening fixture.",
                    "proposed_scene_id": start_scene_id,
                    "intent_summary": "",
                }
            },
        },
    )


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


def test_runtime_projection_scene_id_only_shape_commits_legal_transition(manager: StoryRuntimeManager) -> None:
    """Backward-compat: compiler-shaped rows used ``scene_id`` without ``id`` (audit F-C1)."""
    command_graph = _FakeTurnGraph(
        _envelope(
            interpreted_input={
                "kind": "explicit_command",
                "command_name": "go",
                "command_args": ["phase_2"],
                "confidence": 0.99,
            },
            generation={"success": True, "metadata": {}},
        )
    )
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("phase_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "phase_1",
            "scenes": [
                {"scene_id": "phase_1", "name": "p1", "sequence": 1, "description": ""},
                {"scene_id": "phase_2", "name": "p2", "sequence": 2, "description": ""},
            ],
            "transition_hints": [{"from": "phase_1", "to": "phase_2"}],
        },
    )
    manager.turn_graph = command_graph  # type: ignore[assignment]
    turn = manager.execute_turn(session_id=session.session_id, player_input="/go phase_2")
    nc = turn["narrative_commit"]
    assert nc["allowed"] is True
    assert nc["committed_scene_id"] == "phase_2"
    assert nc["selected_candidate_source"] == "explicit_command"


def test_explicit_command_beats_model_and_token_scan(manager: StoryRuntimeManager) -> None:
    turn_graph = _FakeTurnGraph(
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
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
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
    manager.turn_graph = turn_graph  # type: ignore[assignment]
    turn = manager.execute_turn(
        session_id=session.session_id,
        player_input="/move scene_2 scene_3 noise",
    )
    nc = turn["narrative_commit"]
    assert nc["selected_candidate_source"] == "explicit_command"
    assert nc["committed_scene_id"] == "scene_2"
    assert nc["allowed"] is True


def test_legal_model_proposal_commits_transition(manager: StoryRuntimeManager) -> None:
    turn_graph = _FakeTurnGraph(
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
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )
    manager.turn_graph = turn_graph  # type: ignore[assignment]
    turn = manager.execute_turn(session_id=session.session_id, player_input="I walk forward.")
    nc = turn["narrative_commit"]
    assert nc["allowed"] is True
    assert nc["situation_status"] == "transitioned"
    assert nc["selected_candidate_source"] == "model_structured_output"
    assert "scene_transition:scene_1->scene_2" in nc["committed_consequences"]


def test_illegal_proposal_is_blocked_committed_truth(manager: StoryRuntimeManager) -> None:
    turn_graph = _FakeTurnGraph(
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
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}, {"id": "scene_3"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )
    manager.turn_graph = turn_graph  # type: ignore[assignment]
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
    turn_graph = _FakeTurnGraph(
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
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}],
            "transition_hints": [],
        },
    )
    manager.turn_graph = turn_graph  # type: ignore[assignment]
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
    assert "committed_turn_authority" in hist
    assert "graph" not in hist
    assert "interpreted_input" not in hist
    assert "narrative_commit" in diag
    assert "committed_turn_authority" in diag
    assert "graph" in diag
    assert "retrieval" in diag
    assert "interpreted_input" in diag
    authority = hist["committed_turn_authority"]
    assert authority["authority_record_version"] == "committed_turn_authority.v1"
    assert authority["narrative_commit"] == hist["narrative_commit"]
    assert authority["graph_commit"] == diag["committed_result"]


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
    assert state["committed_state"]["last_committed_turn_authority"] is not None
    assert state["committed_state"]["last_narrative_commit_summary"]["situation_status"] == "continue"
    assert "committed_truth_vs_diagnostics" in diag
    assert diag["authoritative_history_tail"][-1]["narrative_commit"]["open_pressures"] == [
        "interpretation_ambiguity:test_ambiguity"
    ]
    assert "graph" in (diag["diagnostics"][-1])


def test_get_state_exposes_actor_turn_summary_fields(
    manager: StoryRuntimeManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        manager,
        "_apply_experience_packaging",
        lambda raw_bundle, _policy: raw_bundle,
    )
    payload = _envelope(
        interpreted_input={"kind": "speech", "confidence": 0.92},
        generation={
            "success": True,
            "metadata": {
                "structured_output": {
                    "primary_responder_id": "annette_reille",
                    "secondary_responder_ids": ["alain_reille"],
                    "initiative_events": [
                        {"actor_id": "annette_reille", "type": "interrupt"},
                        {"actor_id": "alain_reille", "type": "counter"},
                    ],
                    "social_outcome": "tension_escalates",
                    "dramatic_direction": "escalate",
                }
            },
        },
    )
    payload["responder_id"] = "annette_reille"
    payload["selected_responder_set"] = [
        {"actor_id": "annette_reille"},
        {"actor_id": "alain_reille"},
    ]
    payload["selected_scene_function"] = "escalate_conflict"
    payload["social_outcome"] = "tension_escalates"
    payload["dramatic_direction"] = "escalate"
    payload["validation_outcome"] = {
        "status": "approved",
        "reason": "fixture_actor_lane",
        "actor_lane_validation": {"status": "approved"},
    }
    payload["visible_output_bundle"] = {
        "gm_narration": ["Pressure rises in the room."],
        "spoken_lines": [
            {"speaker_id": "annette_reille", "text": "No, that is not what happened."},
            {"speaker_id": "alain_reille", "text": "Let her finish."},
        ],
        "action_lines": [{"actor_id": "annette_reille", "text": "steps forward"}],
    }
    manager.turn_graph = _FakeTurnGraph(payload)
    session = manager.create_session(
        module_id="m",
        runtime_projection={"start_scene_id": "scene_1", "scenes": [{"id": "scene_1"}]},
    )

    manager.execute_turn(session_id=session.session_id, player_input="I push the argument.")
    state = manager.get_state(session.session_id)

    actor_summary = state["committed_state"]["last_actor_turn_summary"]
    assert actor_summary["contract"] == "actor_turn_summary.v1"
    assert actor_summary["primary_responder_id"] == "annette_reille"
    assert actor_summary["secondary_responder_ids"] == ["alain_reille"]
    assert actor_summary["spoken_line_count"] == 2
    assert actor_summary["action_line_count"] == 1
    assert actor_summary["initiative_summary"]["event_count"] == 2
    assert actor_summary["actor_lane_validation_status"] == "approved"
    assert "initiative_events=2" in (actor_summary["last_actor_outcome_summary"] or "")

    summary = state["committed_state"]["last_narrative_commit_summary"]
    assert summary["primary_responder_id"] == "annette_reille"
    assert summary["spoken_line_count"] == 2
    assert summary["action_line_count"] == 1
    assert summary["initiative_summary"]["event_count"] == 2
    assert state["committed_state"]["last_actor_outcome_summary"] == actor_summary["last_actor_outcome_summary"]


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


def test_concurrent_turns_serialize_per_session(manager: StoryRuntimeManager) -> None:
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

    def _one() -> None:
        manager.execute_turn(session_id=session.session_id, player_input="ping")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: _one(), range(16)))

    assert manager.get_session(session.session_id).turn_counter == 16


def test_terminal_scene_sets_terminal_status(manager: StoryRuntimeManager) -> None:
    manager.turn_graph = _FakeTurnGraph(_opening_envelope("scene_1"))  # type: ignore[assignment]
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
    )  # type: ignore[assignment]
    turn = manager.execute_turn(session_id=session.session_id, player_input="The end.")
    nc = turn["narrative_commit"]
    assert nc["allowed"] is True
    assert nc["situation_status"] == "terminal"
    assert nc["is_terminal"] is True


def test_execute_turn_propagates_vitality_telemetry_to_event_and_governance(
    manager: StoryRuntimeManager,
) -> None:
    payload = _envelope(
        interpreted_input={"kind": "speech", "confidence": 0.9},
        generation={"success": True, "metadata": {}},
    )
    payload["actor_survival_telemetry"] = {
        "vitality_telemetry_v1": {
            "schema_version": "vitality_telemetry_v1",
            "selected_primary_responder_id": "annette_reille",
            "selected_secondary_responder_ids": ["michel_longstreet"],
            "realized_actor_ids": ["annette_reille"],
            "realized_secondary_responder_ids": [],
            "rendered_actor_ids": ["annette_reille"],
            "generated_spoken_line_count": 1,
            "validated_spoken_line_count": 1,
            "rendered_spoken_line_count": 1,
            "generated_action_line_count": 0,
            "validated_action_line_count": 0,
            "rendered_action_line_count": 0,
            "initiative_generated_count": 1,
            "initiative_preserved_count": 1,
            "initiative_seizer_id": "annette_reille",
            "initiative_loser_id": "veronique_vallon",
            "initiative_pressure_label": "contested",
            "pacing_mode": "thin_edge",
            "silence_mode": "withheld",
            "thin_edge_applied": True,
            "withheld_applied": True,
            "compressed_applied": False,
            "prior_tension_present": True,
            "quality_class": "healthy",
            "degradation_signals": [],
            "fallback_used": False,
            "degraded_commit": False,
            "retry_exhausted": False,
            "response_present": True,
            "initiative_present": True,
            "multi_actor_realized": False,
            "sparse_input_recovery_applied": True,
        },
        "operator_diagnostic_hints": {
            "why_turn_felt_passive": [],
            "primary_passivity_factors": [],
        },
    }
    manager.turn_graph = _FakeTurnGraph(payload)
    session = manager.create_session(
        module_id="m",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}],
        },
    )

    manager.execute_turn(session_id=session.session_id, player_input="I answer directly.")
    diag = manager.get_diagnostics(session.session_id)
    row = diag["diagnostics"][-1]
    telemetry = row.get("actor_survival_telemetry") or {}
    vitality = telemetry.get("vitality_telemetry_v1") or {}
    assert vitality.get("schema_version") == "vitality_telemetry_v1"
    gov = row.get("runtime_governance_surface") or {}
    assert isinstance(gov.get("vitality_telemetry_v1"), dict)
    assert gov.get("vitality_telemetry_v1", {}).get("selected_primary_responder_id") == "annette_reille"
