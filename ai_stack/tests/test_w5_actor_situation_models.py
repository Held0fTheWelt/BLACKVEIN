"""Closed-enum and invariant tests for W5 Actor Situation models (ADR-0063)."""

from __future__ import annotations

import pytest

from ai_stack.w5_actor_situation.models import (
    W5_FACT_SCHEMA_VERSION,
    W5_PROJECTION_SCHEMA_VERSION,
    W5_SNAPSHOT_SCHEMA_VERSION,
    W5ActionState,
    W5ActorSituation,
    W5ActorType,
    W5Conflict,
    W5ConflictResolutionStatus,
    W5Dimension,
    W5Fact,
    W5FactStatus,
    W5FreshnessStatus,
    W5Projection,
    W5ProjectionConsumer,
    W5Snapshot,
    W5Source,
    W5TruthLevel,
    W5ValidationFailureCode,
    W5VisibilityScope,
)


def test_dimension_closed_enum_values() -> None:
    assert {d.value for d in W5Dimension} == {"who", "where", "what", "how", "why"}


def test_truth_level_closed_enum_values() -> None:
    assert {t.value for t in W5TruthLevel} == {
        "canonical",
        "observed",
        "declared",
        "director_assigned",
        "inferred",
        "projected",
    }


def test_source_closed_enum_values() -> None:
    assert {s.value for s in W5Source} == {
        "canonical_content",
        "committed_action",
        "participant_state_move",
        "free_player_action_resolution",
        "director_gathering_state",
        "director_composition",
        "npc_agency_simulation",
        "character_mind_record",
        "sensory_context_engine",
        "souffleuse",
        "narrator_composition",
        "admin_override",
    }


def test_visibility_closed_enum_values() -> None:
    assert {v.value for v in W5VisibilityScope} == {
        "public",
        "private_to_actor",
        "gm_only",
        "director_only",
    }


def test_fact_status_closed_enum_values() -> None:
    assert {s.value for s in W5FactStatus} == {
        "active",
        "stale",
        "superseded",
        "contradicted",
        "resolved",
        "pending_validation",
    }


def test_freshness_closed_enum_values() -> None:
    assert {f.value for f in W5FreshnessStatus} == {"fresh", "aging", "stale"}


def test_actor_type_closed_enum_values() -> None:
    assert {a.value for a in W5ActorType} == {"human", "npc", "narrator"}


def test_projection_consumer_closed_enum_values() -> None:
    assert {c.value for c in W5ProjectionConsumer} == {
        "narrator",
        "npc",
        "director",
        "player_shell",
        "admin",
        "diagnostics",
    }


def test_action_state_closed_enum_values() -> None:
    assert {a.value for a in W5ActionState} == {
        "starting",
        "ongoing",
        "completed",
        "interrupted",
        "stale",
    }


def test_conflict_resolution_closed_enum_values() -> None:
    assert {c.value for c in W5ConflictResolutionStatus} == {
        "unresolved",
        "resolved",
        "pending_director",
    }


def test_validation_failure_code_closed_enum_values() -> None:
    assert {c.value for c in W5ValidationFailureCode} == {
        "w5_actor_not_present",
        "w5_location_continuity_break",
        "w5_perception_break",
        "w5_action_continuity_break",
        "w5_unresolved_conflict",
    }


def _build_minimal_fact(**overrides) -> W5Fact:
    defaults = dict(
        fact_id="w5f_test",
        actor_id="annette",
        dimension=W5Dimension.WHERE,
        key="scene_location",
        value="foyer",
        source=W5Source.PARTICIPANT_STATE_MOVE,
        truth_level=W5TruthLevel.OBSERVED,
        valid_from_turn=1,
        last_confirmed_turn=1,
        visibility=W5VisibilityScope.PUBLIC,
        status=W5FactStatus.ACTIVE,
    )
    defaults.update(overrides)
    return W5Fact(**defaults)


def test_w5fact_schema_version_constant() -> None:
    fact = _build_minimal_fact()
    assert fact.schema_version == W5_FACT_SCHEMA_VERSION == "w5_fact.v1"


def test_w5fact_rejects_invalid_schema_version() -> None:
    with pytest.raises(ValueError):
        _build_minimal_fact(schema_version="w5_fact.v0")


def test_w5fact_rejects_empty_fact_id() -> None:
    with pytest.raises(ValueError):
        _build_minimal_fact(fact_id="")


def test_w5fact_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValueError):
        _build_minimal_fact(confidence=1.5)
    with pytest.raises(ValueError):
        _build_minimal_fact(confidence=-0.1)


def test_w5fact_forbids_projected_truth_level() -> None:
    with pytest.raises(ValueError):
        _build_minimal_fact(truth_level=W5TruthLevel.PROJECTED)


def test_w5fact_forbids_observed_why() -> None:
    """why.* facts must use truth_level inferred / canonical / declared / director_assigned."""

    with pytest.raises(ValueError):
        _build_minimal_fact(
            dimension=W5Dimension.WHY,
            key="motive",
            value="protect_son",
            truth_level=W5TruthLevel.OBSERVED,
        )


def test_w5fact_round_trip_dict() -> None:
    fact = _build_minimal_fact()
    assert W5Fact.from_dict(fact.to_dict()) == fact


def test_w5snapshot_schema_version_constant() -> None:
    snap = W5Snapshot(
        snapshot_id="w5s_x",
        story_session_id="sess_1",
        turn_number=0,
        created_at="w5:turn:0",
    )
    assert snap.schema_version == W5_SNAPSHOT_SCHEMA_VERSION == "w5_snapshot.v1"


def test_w5snapshot_round_trip_dict() -> None:
    fact = _build_minimal_fact()
    situation = W5ActorSituation(
        actor_id="annette",
        actor_type=W5ActorType.HUMAN,
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=1,
        where=(fact,),
    )
    snap = W5Snapshot(
        snapshot_id="w5s_a",
        story_session_id="sess_1",
        turn_number=1,
        created_at="w5:turn:1",
        actors={"annette": situation},
        conflicts=(
            W5Conflict(
                conflict_id="w5c_a",
                actor_id="annette",
                dimension=W5Dimension.WHAT,
                competing_fact_ids=("f1", "f2"),
                resolution_status=W5ConflictResolutionStatus.UNRESOLVED,
            ),
        ),
        derived_from_event_ids=("evt_1",),
    )
    restored = W5Snapshot.from_dict(snap.to_dict())
    assert restored == snap


def test_w5projection_schema_version_constant() -> None:
    proj = W5Projection(target_consumer=W5ProjectionConsumer.NARRATOR)
    assert proj.schema_version == W5_PROJECTION_SCHEMA_VERSION == "w5_projection.v1"


def test_w5projection_round_trip_dict() -> None:
    proj = W5Projection(
        target_consumer=W5ProjectionConsumer.NPC,
        actor_id="alain",
        who_summary={"actor_type": "npc"},
        how_summary={"tone": "tense"},
        source_attribution={"how.tone": "director_composition"},
        truth_attribution={"how.tone": "director_assigned"},
    )
    assert W5Projection.from_dict(proj.to_dict()) == proj
