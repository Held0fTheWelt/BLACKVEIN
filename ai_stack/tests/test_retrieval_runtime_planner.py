from __future__ import annotations

from ai_stack.rag.rag_retrieval_dtos import RuntimeRetrievalConfig
from ai_stack.rag.retrieval_runtime_planner import (
    apply_authority_boundary_guard,
    build_retrieval_authority_metadata,
    build_runtime_retrieval_plan,
)


def test_runtime_retrieval_plan_uses_turn_capabilities_actor_and_phase() -> None:
    rc = RuntimeRetrievalConfig(retrieval_execution_mode="hybrid_dense_sparse", max_chunks=5)
    state = {
        "turn_number": 3,
        "player_input": "Ich drohe zu gehen.",
        "current_scene_id": "foyer",
        "module_id": "god_of_carnage",
        "selected_scene_function": "escalation",
        "actor_lane_context": {"active_actor_lane": "player"},
        "interpreted_input": {"input_kind": "speech", "intent": "threat"},
    }
    plan = build_runtime_retrieval_plan(state=state, retrieval_config=rc)
    payload = plan.to_dict()
    assert payload["turn_class"] in {"player_input", "npc_turn", "opening", "recovery"}
    assert payload["active_actor"] == "player"
    assert payload["max_chunks"] == 5
    assert payload["selected_capabilities"]
    assert "scene_event_log" in payload["allowed_memory_lanes"]


def test_authority_metadata_and_guard_mark_unverified_for_authority_critical_consumers() -> None:
    rc = RuntimeRetrievalConfig()
    plan = build_runtime_retrieval_plan(
        state={
            "turn_number": 1,
            "player_input": "Hallo",
            "current_scene_id": "scene_1",
            "module_id": "god_of_carnage",
        },
        retrieval_config=rc,
    )
    retrieval = {
        "retrieval_authority": build_retrieval_authority_metadata(
            plan=plan,
            retrieval_policy_version="task3_source_governance_v1",
            corpus_fingerprint="abc",
        )
    }
    guarded = apply_authority_boundary_guard(
        retrieval_payload=retrieval,
        consumer="unit_test.authority_path",
        authority_critical=True,
    )
    assert guarded["boundary_guard"]["authority_critical"] is True
    assert guarded["boundary_guard"]["retrieval_unverified"] is True
    assert guarded["boundary_guard"]["blocked_as_authority_truth"] is True

