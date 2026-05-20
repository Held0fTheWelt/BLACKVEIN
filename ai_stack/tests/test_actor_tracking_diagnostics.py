"""Phase 4B compact W5 admin/runtime diagnostics."""

from __future__ import annotations

from ai_stack.actor_tracking import (
    W5ActorSituation,
    W5ActorType,
    W5Conflict,
    W5ConflictResolutionStatus,
    W5Dimension,
    W5Fact,
    W5FactStatus,
    W5FreshnessStatus,
    W5Snapshot,
    W5Source,
    W5TruthLevel,
    W5VisibilityScope,
    build_w5_admin_actor_view,
    build_w5_admin_conflicts_view,
    build_w5_admin_narrator_projection_preview,
    build_w5_admin_npc_projection_preview,
    build_w5_admin_snapshot_view,
    build_w5_admin_validation_view,
    build_w5_langfuse_metadata,
    build_w5_runtime_metadata,
)


def _fact(
    fact_id: str,
    *,
    actor_id: str,
    dimension: W5Dimension,
    key: str,
    value: object,
    truth: W5TruthLevel = W5TruthLevel.OBSERVED,
    source: W5Source = W5Source.COMMITTED_ACTION,
    visibility: W5VisibilityScope = W5VisibilityScope.PUBLIC,
    scope: tuple[str, ...] = (),
    status: W5FactStatus = W5FactStatus.ACTIVE,
) -> W5Fact:
    return W5Fact(
        fact_id=fact_id,
        actor_id=actor_id,
        dimension=dimension,
        key=key,
        value=value,
        source=source,
        truth_level=truth,
        valid_from_turn=4,
        last_confirmed_turn=4,
        visibility=visibility,
        actor_knowledge_scope=scope,
        status=status,
    )


def _snapshot() -> W5Snapshot:
    michel = W5ActorSituation(
        actor_id="michel",
        actor_type=W5ActorType.NPC,
        actor_role_in_scene="mediator",
        involvement_type="primary",
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=4,
        where=(
            _fact(
                "f_where_michel",
                actor_id="michel",
                dimension=W5Dimension.WHERE,
                key="scene_location",
                value="study",
                source=W5Source.PARTICIPANT_STATE_MOVE,
            ),
        ),
        what=(
            _fact(
                "f_what_michel",
                actor_id="michel",
                dimension=W5Dimension.WHAT,
                key="current_action",
                value="listens",
            ),
        ),
        how=(
            _fact(
                "f_how_michel",
                actor_id="michel",
                dimension=W5Dimension.HOW,
                key="tone",
                value="dry",
            ),
        ),
        why=(
            _fact(
                "f_why_michel",
                actor_id="michel",
                dimension=W5Dimension.WHY,
                key="motive",
                value="avoid_blame",
                truth=W5TruthLevel.INFERRED,
                source=W5Source.CHARACTER_MIND_RECORD,
                visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
            ),
        ),
    )
    annette = W5ActorSituation(
        actor_id="annette",
        actor_type=W5ActorType.HUMAN,
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=4,
        why=(
            _fact(
                "f_why_annette_private",
                actor_id="annette",
                dimension=W5Dimension.WHY,
                key="motive",
                value="hide_pain",
                truth=W5TruthLevel.INFERRED,
                source=W5Source.CHARACTER_MIND_RECORD,
                visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
                scope=("michel",),
            ),
        ),
    )
    stale = _fact(
        "f_where_stale",
        actor_id="alain",
        dimension=W5Dimension.WHERE,
        key="scene_location",
        value="hallway",
        status=W5FactStatus.STALE,
    )
    alain = W5ActorSituation(
        actor_id="alain",
        actor_type=W5ActorType.NPC,
        freshness_status=W5FreshnessStatus.AGING,
        last_confirmed_turn=3,
        where=(stale,),
    )
    conflict = W5Conflict(
        conflict_id="conf_location_michel",
        actor_id="michel",
        dimension=W5Dimension.WHERE,
        competing_fact_ids=("f_where_michel", "f_where_stale"),
        resolution_status=W5ConflictResolutionStatus.UNRESOLVED,
    )
    return W5Snapshot(
        snapshot_id="w5s_admin",
        story_session_id="sess_admin",
        turn_number=4,
        created_at="w5:turn:4",
        actors={"michel": michel, "annette": annette, "alain": alain},
        conflicts=(conflict,),
    )


def test_admin_snapshot_is_compact_and_does_not_expose_w5_history() -> None:
    view = build_w5_admin_snapshot_view(_snapshot().to_dict())
    assert view["snapshot_id"] == "w5s_admin"
    assert view["stats"]["actor_count"] == 3
    assert view["stats"]["has_how"] is True
    assert view["stats"]["has_inferred_why"] is True
    assert view["actor_summaries"]["michel"]["where"]["value"] == "study"
    assert "w5_history" not in view
    assert view["raw_w5_history_exposed"] is False


def test_per_actor_view_exposes_five_dimensions_with_how_first_class_and_inferred_why() -> None:
    view = build_w5_admin_actor_view(_snapshot(), actor_id="michel")
    dims = view["dimensions"]
    assert dims["who"]["actor_type"] == "npc"
    assert dims["where"]["facts"][0]["value"] == "study"
    assert dims["what"]["facts"][0]["value"] == "listens"
    assert dims["how"]["facts"][0]["key"] == "tone"
    assert dims["how"]["facts"][0]["value"] == "dry"
    assert "tone" not in {fact["key"] for fact in dims["what"]["facts"]}
    assert dims["why"]["facts"][0]["truth_level"] == "inferred"
    assert dims["why"]["facts"][0]["truth_label"] == "soft_inferred"


def test_npc_projection_preview_uses_privacy_scoped_projection_builder() -> None:
    preview = build_w5_admin_npc_projection_preview(_snapshot(), actor_id="michel")
    projection = preview["projection"]
    assert projection["target_consumer"] == "npc"
    assert projection["actor_id"] == "michel"
    assert projection["how_summary"]["facts"]["tone"] == "dry"
    assert projection["why_summary"]["facts"]["motive"] == "avoid_blame"
    assert "hide_pain" not in repr(projection)
    assert projection["raw_w5_ledger_exposed"] is False


def test_narrator_projection_preview_uses_typed_projection_builder() -> None:
    preview = build_w5_admin_narrator_projection_preview(_snapshot().to_dict(), actor_id="michel")
    projection = preview["projection"]
    assert projection["target_consumer"] == "narrator"
    assert projection["where_summary"]["current_location"] == "study"
    assert projection["how_summary"]["facts"]["tone"] == "dry"
    assert projection["truth_attribution"]["why_summary.facts.motive"] == "inferred"
    assert projection["raw_w5_ledger_exposed"] is False


def test_conflicts_view_returns_unresolved_conflicts_compactly() -> None:
    view = build_w5_admin_conflicts_view(_snapshot())
    assert view["unresolved_count"] == 1
    conflict = view["conflicts"][0]
    assert conflict["conflict_id"] == "conf_location_michel"
    assert conflict["resolution_status"] == "unresolved"
    assert conflict["competing_fact_refs"][0]["fact_id"] == "f_where_michel"
    assert "valid_from_turn" not in repr(conflict)


def test_validation_runtime_and_langfuse_metadata_are_compact() -> None:
    outcome = {
        "status": "rejected",
        "w5_validation": {
            "w5_validation_enabled": True,
            "w5_validation_ran": True,
            "w5_validation_failed": True,
            "w5_validation_failure_codes": ["w5_actor_not_present"],
            "w5_snapshot_id": "w5s_admin",
            "w5_validation_source": "w5_snapshot",
        },
    }
    validation = build_w5_admin_validation_view(_snapshot(), latest_validation_outcome=outcome)
    assert validation["validation"]["w5_validation_ran"] is True
    assert validation["validation"]["w5_validation_failure_codes"] == ["w5_actor_not_present"]

    runtime = build_w5_runtime_metadata(_snapshot(), latest_validation_outcome=outcome)
    assert runtime["w5_snapshot_id"] == "w5s_admin"
    assert runtime["w5_actor_count"] == 3
    assert runtime["w5_conflict_count"] == 1
    assert runtime["w5_has_how"] is True
    assert runtime["w5_has_inferred_why"] is True
    assert runtime["w5_validation_failure_codes"] == ["w5_actor_not_present"]

    langfuse = build_w5_langfuse_metadata(_snapshot(), latest_validation_outcome=outcome)
    assert langfuse["w5.snapshot_id"] == "w5s_admin"
    assert langfuse["w5.unresolved_conflict_count"] == 1
    assert langfuse["w5.has_how"] is True
    assert langfuse["w5.validation_failed"] is True
    assert "avoid_blame" not in repr(langfuse)


def test_missing_or_malformed_snapshot_returns_safe_empty_response() -> None:
    view = build_w5_admin_snapshot_view(None)
    assert view["status"] == "unavailable"
    assert view["diagnostic"]["safe_empty"] is True
    assert view["read_only"] is True
    assert build_w5_admin_actor_view({"not": "a snapshot"}, actor_id="michel")["status"] == "unavailable"
