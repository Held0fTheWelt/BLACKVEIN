"""Phase 2 Stage G — safe off-stage commit path tests."""

from __future__ import annotations

from typing import Any

from ai_stack.hierarchical_memory_contracts import (
    HIERARCHICAL_MEMORY_WRITE_SCHEMA_VERSION,
)
from ai_stack.phase2_autonomous_tick import (
    AutonomousTickInputs,
    evaluate_autonomous_tick,
)
from ai_stack.phase2_off_stage_updates import (
    BLOCKER_FREE_TEXT_BODY,
    BLOCKER_NEW_PERSON,
    BLOCKER_NEW_PLOT_FACT,
    BLOCKER_NEW_ROOM,
    CANDIDATE_KIND_OFF_STAGE_MEMORY_NOTE,
    CANDIDATE_KIND_RELATIONSHIP_TENSION_UPDATE,
    COMMIT_TARGET_HIERARCHICAL_MEMORY,
    COMMIT_TARGET_RELATIONSHIP_STATE,
    OffStageCommitInputs,
    OffStageUpdateInputs,
    SAFETY_GATE_BLOCKED,
    SAFETY_GATE_PASS,
    build_off_stage_update_candidate,
    commit_off_stage_update_candidates,
)
from ai_stack.relationship_state_contracts import (
    RelationshipAxisState,
    RelationshipPairState,
    RelationshipStateRecord,
)


def _candidate_result() -> dict[str, Any]:
    return build_off_stage_update_candidate(
        OffStageUpdateInputs(
            tick_id="tick-stage-g",
            chosen_actor_id="npc_a",
            chosen_action_kind="speak",
            motivation_scores={"npc_a": 0.72},
            visible_npc_ids=["npc_b"],
            known_actor_ids=["npc_a", "npc_b"],
            known_room_ids=["room_a"],
        )
    )


def _policy(
    *,
    enabled: bool = True,
    allowed: list[str] | None = None,
    max_commits: int = 2,
) -> dict[str, Any]:
    return {
        "auto_commit_enabled": enabled,
        "allowed_candidate_kinds": allowed
        if allowed is not None
        else [
            CANDIDATE_KIND_RELATIONSHIP_TENSION_UPDATE,
            CANDIDATE_KIND_OFF_STAGE_MEMORY_NOTE,
        ],
        "require_safety_gate_pass": True,
        "max_commits_per_tick": max_commits,
    }


def _relationship_state() -> dict[str, Any]:
    return RelationshipStateRecord(
        turn_number=4,
        pair_states=[
            RelationshipPairState(
                relationship_id="rel_a_b",
                character_ids=["npc_a", "npc_b"],
                axis_ids=["axis_a_b"],
                tension_score=0.25,
                trust_score=0.65,
                stability_band="stable",
            )
        ],
        axis_states=[
            RelationshipAxisState(
                axis_id="axis_a_b",
                relationship_ids=["rel_a_b"],
                tension_score=0.25,
                stability_band="stable",
                active=True,
            )
        ],
        active_relationship_axis_ids=["axis_a_b"],
        dominant_relationship_axis_id="axis_a_b",
        rationale_codes=["relationship_state_policy_applied"],
    ).to_runtime_dict()


def _memory_policy() -> dict[str, Any]:
    return {
        "schema_version": "hierarchical_memory_policy.v1",
        "enabled": True,
        "write_requires_committed_turn": True,
        "allow_uncommitted_writes": False,
        "tiers": [
            {
                "id": "actor",
                "enabled": True,
                "max_items": 4,
                "max_context_items": 2,
            }
        ],
    }


def _commit(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "candidate_result": _candidate_result(),
        "policy": _policy(),
        "known_actor_ids": ["npc_a", "npc_b"],
        "known_room_ids": ["room_a"],
        "relationship_state_record": _relationship_state(),
        "hierarchical_memory_policy": _memory_policy(),
        "module_id": "module_alpha",
        "runtime_profile_id": "profile_alpha",
        "turn_number": 5,
    }
    kwargs.update(overrides)
    return commit_off_stage_update_candidates(OffStageCommitInputs(**kwargs))


def test_auto_commit_disabled_leaves_candidate_preview_only() -> None:
    candidate = _candidate_result()
    result = _commit(candidate_result=candidate, policy=_policy(enabled=False))

    assert candidate["relationship_update_candidate"]
    assert candidate["memory_update_candidate"]
    assert result["attempted"] is True
    assert result["committed"] is False
    assert result["reason"] == "auto_commit_disabled"
    assert result["committed_targets"] == []


def test_safety_gate_fail_blocks_commit_even_with_payloads() -> None:
    candidate = _candidate_result()
    candidate["off_stage_safety_gate_result"] = SAFETY_GATE_BLOCKED

    result = _commit(candidate_result=candidate)

    assert result["committed"] is False
    assert result["reason"] == "safety_gate_not_pass"
    assert result["safety_gate_result"] == SAFETY_GATE_BLOCKED


def test_unknown_actor_blocks_all_targets() -> None:
    candidate = _candidate_result()
    candidate["relationship_update_candidate"]["actor_id"] = "intruder"
    candidate["memory_update_candidate"]["actor_id"] = "intruder"

    result = _commit(candidate_result=candidate, known_actor_ids=["npc_a"])

    assert result["committed"] is False
    assert all(BLOCKER_NEW_PERSON in row["reason"] for row in result["rejected_targets"])


def test_unknown_room_blocks_candidate() -> None:
    candidate = _candidate_result()
    candidate["memory_update_candidate"]["room_id"] = "unlisted_room"

    result = _commit(candidate_result=candidate, known_room_ids=["room_a"])

    assert COMMIT_TARGET_HIERARCHICAL_MEMORY not in result["committed_targets"]
    assert any(BLOCKER_NEW_ROOM in row["reason"] for row in result["rejected_targets"])


def test_plot_fact_blocker_prevents_commit() -> None:
    candidate = _candidate_result()
    candidate["relationship_update_candidate"]["plot_fact"] = "new canonical reveal"

    result = _commit(candidate_result=candidate)

    assert COMMIT_TARGET_RELATIONSHIP_STATE not in result["committed_targets"]
    assert any(BLOCKER_NEW_PLOT_FACT in row["reason"] for row in result["rejected_targets"])


def test_unrecognized_candidate_kind_is_rejected() -> None:
    candidate = _candidate_result()
    candidate["relationship_update_candidate"]["candidate_kind"] = "unknown_update"
    candidate["memory_update_candidate"]["candidate_kind"] = "unknown_update"

    result = _commit(candidate_result=candidate)

    assert result["committed"] is False
    assert all(
        row["reason"] == "candidate_kind_unrecognized"
        for row in result["rejected_targets"]
    )


def test_relationship_candidate_commits_only_through_relationship_contract() -> None:
    result = _commit(
        policy=_policy(allowed=[CANDIDATE_KIND_RELATIONSHIP_TENSION_UPDATE]),
    )

    assert result["committed_targets"] == [COMMIT_TARGET_RELATIONSHIP_STATE]
    rel = result["target_results"][0]
    assert rel["relationship_state_validation"]["status"] == "approved"
    assert rel["relationship_state_record"]["transition_events"][-1]["transition_code"] == (
        "npc_initiative_pressure"
    )
    assert all(
        target != COMMIT_TARGET_HIERARCHICAL_MEMORY
        for target in result["committed_targets"]
    )


def test_memory_candidate_commits_only_through_hierarchical_memory_contract() -> None:
    result = _commit(
        policy=_policy(allowed=[CANDIDATE_KIND_OFF_STAGE_MEMORY_NOTE]),
    )

    assert result["committed_targets"] == [COMMIT_TARGET_HIERARCHICAL_MEMORY]
    mem = [
        row
        for row in result["target_results"]
        if row["target"] == COMMIT_TARGET_HIERARCHICAL_MEMORY
    ][0]
    assert mem["write_result"]["schema_version"] == HIERARCHICAL_MEMORY_WRITE_SCHEMA_VERSION
    assert (
        mem["write_result"]["written_items"][0]["schema_version"]
        == "hierarchical_memory_item.v1"
    )
    assert mem["hierarchical_memory_snapshot"]["item_count"] == 1
    assert all(
        target != COMMIT_TARGET_RELATIONSHIP_STATE
        for target in result["committed_targets"]
    )


def test_max_commits_per_tick_is_enforced() -> None:
    result = _commit(policy=_policy(max_commits=1))

    assert result["committed_targets"] == [COMMIT_TARGET_RELATIONSHIP_STATE]
    assert any(
        row["reason"] == "max_commits_per_tick_exceeded"
        for row in result["rejected_targets"]
    )


def test_commit_result_preserves_canonical_and_beat_invariants() -> None:
    result = _commit()

    assert result["canonical_path_advanced"] is False
    assert result["mandatory_beat_consumed"] is False
    assert result["safety_gate_result"] == SAFETY_GATE_PASS
    assert result["proof_level"] == "local_only"


def test_free_text_body_is_not_accepted() -> None:
    candidate = _candidate_result()
    candidate["memory_update_candidate"]["body"] = "unstructured prose must not land"

    result = _commit(candidate_result=candidate)

    assert COMMIT_TARGET_HIERARCHICAL_MEMORY not in result["committed_targets"]
    assert any(BLOCKER_FREE_TEXT_BODY in row["reason"] for row in result["rejected_targets"])


def test_commit_result_diagnostic_emitted_from_autonomous_tick_default_disabled() -> None:
    outcome = evaluate_autonomous_tick(
        AutonomousTickInputs(
            npc_ids=["npc_a"],
            scene_energy_output={"energy_level": "volatile"},
            social_pressure_output={"band": "high"},
            narrative_momentum_output={"state": "cresting"},
            actor_pressure_profiles={
                "profiles": {
                    "npc_a": {"pressure_markers": [{"kind": "pressure"} for _ in range(5)]}
                }
            },
            npc_motivation_score_policy={
                "base_threshold": 0.10,
                "score_weights": {
                    "scene_energy": 0.25,
                    "social_pressure": 0.30,
                    "relationship_axis_pressure": 0.25,
                    "narrative_momentum": 0.20,
                },
            },
            visible_npc_ids=[],
            known_actor_ids=["npc_a"],
            known_room_ids=["room_a"],
        ),
        enabled=True,
    )

    assert outcome.off_stage_update_candidate["off_stage_update_candidate"] is True
    assert outcome.off_stage_commit_result["attempted"] is True
    assert outcome.off_stage_commit_result["committed"] is False
    assert outcome.off_stage_commit_result["reason"] == "auto_commit_disabled"
