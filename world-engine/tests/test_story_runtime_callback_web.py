"""Tests for Π17 callback-web continuity evidence.

ADR-0039 scope: assertions use policy-derived bounds, schema constants, graph
export fields, and RuntimeAspectLedger projection, not example callback prose.
"""

from __future__ import annotations

import copy
from typing import Any

from ai_stack.callback_web_contracts import (
    callback_web_bounds_from_policy,
    callback_web_policy_from_module_runtime,
    validate_callback_web_record,
)
from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.runtime_aspect_ledger import ASPECT_CALLBACK_WEB
from app.story_runtime import StoryRuntimeManager
from story_runtime_core.callbacks import (
    CALLBACK_WEB_FEEDBACK_CONTRACT,
    build_callback_web_record,
    build_graph_callback_web_export,
)


class _RecordingFakeTurnGraph:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.last_kwargs: dict[str, Any] = {}

    def run(self, **kwargs: Any) -> dict[str, Any]:
        self.last_kwargs = dict(kwargs)
        return copy.deepcopy(self._payload)


def _callback_policy() -> dict[str, Any]:
    module_policy = load_module_runtime_policy("god_of_carnage").to_dict()
    return callback_web_policy_from_module_runtime(module_policy)


def _derived_continuity_class(policy: dict[str, Any]) -> str:
    classes = policy["allowed_continuity_classes"]
    assert classes
    return str(classes[0])


def _payload(continuity_class: str) -> dict[str, Any]:
    return {
        "interpreted_input": {"kind": "speech", "confidence": 0.8},
        "generation": {"success": True, "metadata": {}, "content": "x" * 120},
        "graph_diagnostics": {"errors": []},
        "retrieval": {"domain": "runtime", "status": "ok"},
        "routing": {"selected_model": "mock"},
        "validation_outcome": {"status": "approved", "reason": "test_fixture"},
        "visible_output_bundle": {"gm_narration": ["Fixture narration for tests."]},
        "committed_result": {"commit_applied": True, "committed_effects": []},
        "continuity_impacts": [{"class": continuity_class}],
    }


def test_callback_web_record_derives_edges_from_policy_continuity_class() -> None:
    policy = _callback_policy()
    continuity_class = _derived_continuity_class(policy)
    history = [
        {
            "canonical_turn_id": "turn-1",
            "turn_number": 1,
            "narrative_commit": {
                "committed_scene_id": "scene_1",
                "planner_truth": {"continuity_impacts": [{"class": continuity_class}]},
            },
        },
        {
            "canonical_turn_id": "turn-2",
            "turn_number": 2,
            "narrative_commit": {
                "committed_scene_id": "scene_2",
                "planner_truth": {"continuity_impacts": [{"class": continuity_class}]},
            },
        },
    ]

    record = build_callback_web_record(
        story_session_id="callback-test-session",
        module_id="god_of_carnage",
        history=history,
        bounds=callback_web_bounds_from_policy(policy),
    )
    validation = validate_callback_web_record(record, policy=policy)
    export = build_graph_callback_web_export(record, max_edges=policy["max_graph_edges"])

    assert validation["contract_pass"] is True
    assert record["snapshot"]["edge_count"] >= 1
    assert any(continuity_class in edge["continuity_classes"] for edge in record["edges"])
    assert export is not None
    assert export["feedback_contract"] == CALLBACK_WEB_FEEDBACK_CONTRACT
    assert export["exported_edge_count"] <= policy["max_graph_edges"]
    assert "evidence" not in export["edges"][0]


def test_manager_passes_callback_web_to_graph_and_records_ledger_aspect() -> None:
    policy = _callback_policy()
    continuity_class = _derived_continuity_class(policy)
    fake = _RecordingFakeTurnGraph(_payload(continuity_class))
    manager = StoryRuntimeManager()
    manager.turn_graph = fake  # type: ignore[assignment]
    session = manager.create_session(
        module_id="god_of_carnage",
        runtime_projection={
            "start_scene_id": "scene_1",
            "module_id": "god_of_carnage",
            "human_actor_id": "annette_reille",
            "selected_player_role": "annette_reille",
            "npc_actor_ids": ["michel_longstreet", "veronique_vallon", "alain_reille"],
            "actor_lanes": {
                "annette_reille": "human",
                "michel_longstreet": "npc",
                "veronique_vallon": "npc",
                "alain_reille": "npc",
            },
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
        },
    )

    manager.execute_turn(session_id=session.session_id, player_input="first")
    manager.execute_turn(session_id=session.session_id, player_input="second")

    prior = fake.last_kwargs["prior_callback_web_state"]
    assert prior["feedback_contract"] == CALLBACK_WEB_FEEDBACK_CONTRACT
    assert prior["edge_count"] >= 1
    assert prior["exported_edge_count"] <= policy["max_graph_edges"]

    latest = session.history[-1]
    aspect = latest["turn_aspect_ledger"]["turn_aspect_ledger"][ASPECT_CALLBACK_WEB]
    assert aspect["status"] == "passed"
    assert aspect["actual"]["contract_pass"] is True
    assert aspect["actual"]["edge_count"] >= 1
    state = manager.get_state(session.session_id)
    assert state["committed_state"]["callback_web_continuity"]["edge_count"] >= 1
