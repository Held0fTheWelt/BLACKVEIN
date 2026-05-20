"""Maps source-plan §4.4 off-stage gates to Stage F ``BLOCKER_*`` enums (Sub-Plan 3 PR-3B)."""

from __future__ import annotations

import pytest

from ai_stack.story_runtime.off_stage_updates import (
    BLOCKER_CANONICAL_PATH_ADVANCE_ATTEMPTED,
    BLOCKER_FREE_TEXT_BODY,
    BLOCKER_MANDATORY_BEAT_CONSUME_ATTEMPTED,
    BLOCKER_NEW_PERSON,
    BLOCKER_NEW_PLOT_FACT,
    BLOCKER_NEW_ROOM,
    OffStageUpdateInputs,
    build_off_stage_update_candidate,
    validate_external_candidate,
)

# Source plan §4.4 hard gates → implementation blockers (closed enum).
SOURCE_PLAN_GATE_MATRIX: tuple[tuple[str, str], ...] = (
    ("no_canonical_path_effect", BLOCKER_CANONICAL_PATH_ADVANCE_ATTEMPTED),
    ("no_new_person", BLOCKER_NEW_PERSON),
    ("no_new_room", BLOCKER_NEW_ROOM),
    ("no_plot_bearing_facts", BLOCKER_NEW_PLOT_FACT),
    ("no_free_text_body", BLOCKER_FREE_TEXT_BODY),
    ("no_mandatory_beat_consume", BLOCKER_MANDATORY_BEAT_CONSUME_ATTEMPTED),
)


@pytest.mark.parametrize("plan_gate,blocker_enum", SOURCE_PLAN_GATE_MATRIX)
def test_source_plan_gate_maps_to_closed_blocker_enum(plan_gate: str, blocker_enum: str) -> None:
    assert plan_gate
    assert blocker_enum in {
        BLOCKER_CANONICAL_PATH_ADVANCE_ATTEMPTED,
        BLOCKER_NEW_PERSON,
        BLOCKER_NEW_ROOM,
        BLOCKER_NEW_PLOT_FACT,
        BLOCKER_FREE_TEXT_BODY,
        BLOCKER_MANDATORY_BEAT_CONSUME_ATTEMPTED,
    }


def test_validate_external_candidate_rejects_canonical_advance() -> None:
    cand = {
        "relationship_update_candidate": {
            "schema_version": "off_stage_relationship_update_candidate.v1",
            "actor_pair": ["alain_reille", "annette_reille"],
        },
        "canonical_path_advance": True,
        "mandatory_beat_consume": False,
    }
    blockers = validate_external_candidate(
        candidate=cand,
        known_actor_ids=["alain_reille", "annette_reille"],
        known_room_ids=["foyer"],
    )
    assert BLOCKER_CANONICAL_PATH_ADVANCE_ATTEMPTED in blockers


def test_build_candidate_invariants_match_plan_gates() -> None:
    out = build_off_stage_update_candidate(
        OffStageUpdateInputs(
            tick_id="t-gate-matrix",
            chosen_actor_id="alain_reille",
            chosen_action_kind="local_mundane_action",
            motivation_scores={"alain_reille": 0.8},
            visible_npc_ids=["annette_reille"],
            known_actor_ids=["alain_reille", "annette_reille"],
            known_room_ids=["foyer", "kitchen"],
            gathering_paused=False,
        )
    )
    assert out.get("canonical_path_advanced") is False
    assert out.get("mandatory_beat_consumed") is False
