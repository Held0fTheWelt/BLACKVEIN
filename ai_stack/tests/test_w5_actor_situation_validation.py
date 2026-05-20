"""Phase 4A W5 validation tests.

These tests pin W5 actor-situation validation as a read-side addition to the
canonical validation seam. Actor Lane remains authoritative and W5 never rewrites
proposed output.
"""

from __future__ import annotations

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.goc_turn_seams import run_validation_seam
from ai_stack.actor_situation import (
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
    W5ValidationFailureCode,
    W5VisibilityScope,
    validate_w5_actor_situation,
)


TURN = 7


def _fact(
    *,
    fact_id: str,
    actor_id: str,
    dimension: W5Dimension,
    key: str,
    value: object,
    truth: W5TruthLevel = W5TruthLevel.OBSERVED,
    source: W5Source = W5Source.COMMITTED_ACTION,
    visibility: W5VisibilityScope = W5VisibilityScope.PUBLIC,
    status: W5FactStatus = W5FactStatus.ACTIVE,
    confidence: float = 1.0,
    actor_knowledge_scope: tuple[str, ...] = (),
) -> W5Fact:
    return W5Fact(
        fact_id=fact_id,
        actor_id=actor_id,
        dimension=dimension,
        key=key,
        value=value,
        source=source,
        truth_level=truth,
        visibility=visibility,
        valid_from_turn=TURN,
        last_confirmed_turn=TURN,
        status=status,
        confidence=confidence,
        actor_knowledge_scope=actor_knowledge_scope,
    )


def _situation(
    actor_id: str,
    *,
    actor_type: W5ActorType = W5ActorType.NPC,
    location: str | None = "salon",
    what: tuple[W5Fact, ...] = (),
    why: tuple[W5Fact, ...] = (),
) -> W5ActorSituation:
    where = ()
    if location is not None:
        where = (
            _fact(
                fact_id=f"w5f_{actor_id}_where",
                actor_id=actor_id,
                dimension=W5Dimension.WHERE,
                key="scene_location",
                value=location,
                truth=W5TruthLevel.OBSERVED,
                source=W5Source.PARTICIPANT_STATE_MOVE,
            ),
        )
    return W5ActorSituation(
        actor_id=actor_id,
        actor_type=actor_type,
        where=where,
        what=what,
        why=why,
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=TURN,
    )


def _snapshot(
    *situations: W5ActorSituation,
    conflicts: tuple[W5Conflict, ...] = (),
) -> W5Snapshot:
    return W5Snapshot(
        snapshot_id="w5s_validation",
        story_session_id="sess_validation",
        turn_number=TURN,
        created_at=f"w5:turn:{TURN}",
        actors={s.actor_id: s for s in situations},
        conflicts=conflicts,
    )


def _generation(*, spoken: list[dict] | None = None, actions: list[dict] | None = None) -> dict:
    return {
        "success": True,
        "metadata": {
            "structured_output": {
                "spoken_lines": spoken or [],
                "action_lines": actions or [],
            }
        },
    }


def _approved_effects() -> list[dict]:
    return [
        {
            "effect_type": "narrative_beat",
            "description": "Michel answers from the salon while the pressure in the room sharpens.",
        }
    ]


def test_w5_validation_disabled_leaves_seam_behavior_unchanged(monkeypatch) -> None:
    monkeypatch.delenv("W5_AST_VALIDATION_ENABLED", raising=False)
    generation = _generation(spoken=[{"speaker_id": "michel", "text": "No."}])

    baseline = run_validation_seam(
        module_id=GOC_MODULE_ID,
        proposed_state_effects=_approved_effects(),
        generation=generation,
    )
    with_snapshot = run_validation_seam(
        module_id=GOC_MODULE_ID,
        proposed_state_effects=_approved_effects(),
        generation=generation,
        w5_latest_snapshot=_snapshot(_situation("michel")).to_dict(),
    )

    assert baseline == with_snapshot
    assert "w5_validation" not in with_snapshot


def test_w5_validation_enabled_rejects_after_actor_lane_accepts(monkeypatch) -> None:
    monkeypatch.setenv("W5_AST_VALIDATION_ENABLED", "true")
    generation = _generation(spoken=[{"speaker_id": "michel", "text": "No."}])

    outcome = run_validation_seam(
        module_id=GOC_MODULE_ID,
        proposed_state_effects=_approved_effects(),
        generation=generation,
        actor_lane_context={
            "human_actor_id": "annette",
            "ai_forbidden_actor_ids": ["annette"],
        },
        w5_latest_snapshot=_snapshot(_situation("michel", location=None)).to_dict(),
    )

    assert outcome["status"] == "rejected"
    assert outcome["reason"] == W5ValidationFailureCode.W5_ACTOR_NOT_PRESENT.value
    assert outcome["validator_lane"] == "goc_rule_engine_v1"
    assert outcome["w5_validation"]["w5_validation_ran"] is True
    assert outcome["w5_validation"]["w5_validation_failure_codes"] == [
        W5ValidationFailureCode.W5_ACTOR_NOT_PRESENT.value
    ]


def test_actor_lane_rejection_is_not_masked_by_w5(monkeypatch) -> None:
    monkeypatch.setenv("W5_AST_VALIDATION_ENABLED", "true")
    generation = _generation(spoken=[{"speaker_id": "annette", "text": "I apologize."}])

    outcome = run_validation_seam(
        module_id=GOC_MODULE_ID,
        proposed_state_effects=_approved_effects(),
        generation=generation,
        actor_lane_context={
            "human_actor_id": "annette",
            "ai_forbidden_actor_ids": ["annette"],
        },
        w5_latest_snapshot=None,
    )

    assert outcome["status"] == "rejected"
    assert outcome["reason"] == "ai_controlled_human_actor"
    assert outcome["actor_lane_validation"]["status"] == "rejected"
    assert "w5_validation" not in outcome


def test_actor_absent_returns_w5_actor_not_present() -> None:
    result = validate_w5_actor_situation(
        snapshot=_snapshot(_situation("michel", location=None)),
        generation=_generation(spoken=[{"speaker_id": "michel", "text": "No."}]),
    )
    assert result["w5_validation_failed"] is True
    assert result["w5_validation_failure_codes"] == [
        W5ValidationFailureCode.W5_ACTOR_NOT_PRESENT.value
    ]
    assert result["failures"][0]["actor_id"] == "michel"


def test_legal_actor_present_has_no_presence_rejection() -> None:
    result = validate_w5_actor_situation(
        snapshot=_snapshot(_situation("michel", location="salon")),
        generation=_generation(spoken=[{"speaker_id": "michel", "text": "No."}]),
    )
    assert result["w5_validation_failed"] is False
    assert result["w5_validation_failure_codes"] == []


def test_narrator_only_output_does_not_trigger_actor_presence_rejection() -> None:
    result = validate_w5_actor_situation(
        snapshot=_snapshot(_situation("michel", location=None)),
        generation={
            "success": True,
            "metadata": {
                "structured_output": {
                    "narration_summary": "The salon falls silent.",
                    "spoken_lines": [],
                    "action_lines": [],
                }
            },
        },
    )
    assert result["w5_validation_failed"] is False
    assert result["w5_validation_failure_codes"] == []


def test_illegal_location_jump_returns_location_continuity_break() -> None:
    result = validate_w5_actor_situation(
        snapshot=_snapshot(_situation("michel", location="salon")),
        generation=_generation(
            actions=[
                {
                    "actor_id": "michel",
                    "text": "Michel gestures from the hallway.",
                    "location_id": "hallway",
                }
            ]
        ),
    )
    assert result["w5_validation_failure_codes"] == [
        W5ValidationFailureCode.W5_LOCATION_CONTINUITY_BREAK.value
    ]
    failure = result["failures"][0]
    assert failure["details"]["w5_scene_location"] == "salon"
    assert failure["details"]["claimed_location"] == "hallway"
    assert failure["fact_refs"][0]["truth_level"] == "observed"
    assert failure["fact_refs"][0]["source"] == "participant_state_move"
    assert "value" not in failure["fact_refs"][0]


def test_committed_target_location_does_not_trigger_location_break() -> None:
    result = validate_w5_actor_situation(
        snapshot=_snapshot(_situation("michel", location="salon")),
        generation=_generation(
            actions=[
                {
                    "actor_id": "michel",
                    "text": "Michel steps into the hallway.",
                    "location_id": "hallway",
                }
            ]
        ),
        player_action_frame={"target_location_id": "hallway"},
    )
    assert result["w5_validation_failed"] is False
    assert result["w5_validation_failure_codes"] == []


def test_private_inaccessible_fact_returns_perception_break() -> None:
    secret = _fact(
        fact_id="w5f_alain_secret",
        actor_id="alain",
        dimension=W5Dimension.WHY,
        key="motive",
        value="hide_panic",
        truth=W5TruthLevel.INFERRED,
        source=W5Source.CHARACTER_MIND_RECORD,
        visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
    )
    result = validate_w5_actor_situation(
        snapshot=_snapshot(_situation("michel"), _situation("alain", why=(secret,))),
        generation=_generation(
            spoken=[
                {
                    "speaker_id": "michel",
                    "text": "You are hiding panic.",
                    "referenced_fact_id": "w5f_alain_secret",
                }
            ]
        ),
    )
    assert result["w5_validation_failure_codes"] == [
        W5ValidationFailureCode.W5_PERCEPTION_BREAK.value
    ]
    assert result["failures"][0]["fact_refs"][0]["fact_id"] == "w5f_alain_secret"


def test_allowed_actor_knowledge_scope_does_not_trigger_perception_break() -> None:
    shared = _fact(
        fact_id="w5f_alain_shared",
        actor_id="alain",
        dimension=W5Dimension.WHY,
        key="motive",
        value="protect_annette",
        truth=W5TruthLevel.INFERRED,
        source=W5Source.CHARACTER_MIND_RECORD,
        visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
        actor_knowledge_scope=("michel",),
    )
    result = validate_w5_actor_situation(
        snapshot=_snapshot(_situation("michel"), _situation("alain", why=(shared,))),
        generation=_generation(
            spoken=[
                {
                    "speaker_id": "michel",
                    "text": "You are protecting Annette.",
                    "referenced_fact_id": "w5f_alain_shared",
                }
            ]
        ),
    )
    assert result["w5_validation_failed"] is False
    assert result["w5_validation_failure_codes"] == []


def test_player_private_fact_does_not_leak_to_npc_perception() -> None:
    private = _fact(
        fact_id="w5f_annette_private",
        actor_id="annette",
        dimension=W5Dimension.WHY,
        key="motive",
        value="hide_pain",
        truth=W5TruthLevel.INFERRED,
        source=W5Source.CHARACTER_MIND_RECORD,
        visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
        actor_knowledge_scope=("michel",),
    )
    result = validate_w5_actor_situation(
        snapshot=_snapshot(
            _situation("michel"),
            _situation("annette", actor_type=W5ActorType.HUMAN, why=(private,)),
        ),
        generation=_generation(
            spoken=[
                {
                    "speaker_id": "michel",
                    "text": "You are hiding pain.",
                    "referenced_fact_id": "w5f_annette_private",
                }
            ]
        ),
    )
    assert result["w5_validation_failure_codes"] == [
        W5ValidationFailureCode.W5_PERCEPTION_BREAK.value
    ]


def test_action_continuity_break_returns_w5_action_continuity_break() -> None:
    action_state = _fact(
        fact_id="w5f_michel_action_state",
        actor_id="michel",
        dimension=W5Dimension.WHAT,
        key="action_state",
        value="ongoing",
        truth=W5TruthLevel.OBSERVED,
    )
    result = validate_w5_actor_situation(
        snapshot=_snapshot(_situation("michel", what=(action_state,))),
        generation=_generation(
            actions=[{"actor_id": "michel", "text": "Michel starts over.", "action_state": "starting"}]
        ),
    )
    assert result["w5_validation_failure_codes"] == [
        W5ValidationFailureCode.W5_ACTION_CONTINUITY_BREAK.value
    ]
    assert result["failures"][0]["fact_refs"][0]["fact_id"] == "w5f_michel_action_state"


def test_stale_low_confidence_inferred_action_fact_warns_not_blocks() -> None:
    action_state = _fact(
        fact_id="w5f_michel_stale_action_state",
        actor_id="michel",
        dimension=W5Dimension.WHAT,
        key="action_state",
        value="ongoing",
        truth=W5TruthLevel.INFERRED,
        status=W5FactStatus.STALE,
        confidence=0.3,
    )
    result = validate_w5_actor_situation(
        snapshot=_snapshot(_situation("michel", what=(action_state,))),
        generation=_generation(
            actions=[{"actor_id": "michel", "text": "Michel starts over.", "action_state": "starting"}]
        ),
    )
    assert result["w5_validation_failed"] is False
    assert result["w5_validation_failure_codes"] == []
    assert result["warnings"][0]["code"] == W5ValidationFailureCode.W5_ACTION_CONTINUITY_BREAK.value
    assert result["warnings"][0]["severity"] == "warning"


def test_unresolved_observed_conflict_blocks_commit() -> None:
    f1 = _fact(
        fact_id="w5f_michel_salon",
        actor_id="michel",
        dimension=W5Dimension.WHERE,
        key="scene_location",
        value="salon",
        truth=W5TruthLevel.OBSERVED,
        source=W5Source.PARTICIPANT_STATE_MOVE,
    )
    f2 = _fact(
        fact_id="w5f_michel_hallway",
        actor_id="michel",
        dimension=W5Dimension.WHERE,
        key="scene_location",
        value="hallway",
        truth=W5TruthLevel.CANONICAL,
        source=W5Source.CANONICAL_CONTENT,
    )
    conflict = W5Conflict(
        conflict_id="w5c_location",
        actor_id="michel",
        dimension=W5Dimension.WHERE,
        competing_fact_ids=("w5f_michel_salon", "w5f_michel_hallway"),
        resolution_status=W5ConflictResolutionStatus.UNRESOLVED,
    )
    result = validate_w5_actor_situation(
        snapshot=_snapshot(
            W5ActorSituation(
                actor_id="michel",
                actor_type=W5ActorType.NPC,
                where=(f1, f2),
                freshness_status=W5FreshnessStatus.FRESH,
                last_confirmed_turn=TURN,
            ),
            conflicts=(conflict,),
        ),
        generation=_generation(spoken=[{"speaker_id": "michel", "text": "No."}]),
    )
    assert result["w5_validation_failure_codes"] == [
        W5ValidationFailureCode.W5_UNRESOLVED_CONFLICT.value
    ]
    assert result["failures"][0]["details"]["conflict_id"] == "w5c_location"


def test_inferred_why_conflict_warns_without_blocking_commit() -> None:
    f1 = _fact(
        fact_id="w5f_michel_why_1",
        actor_id="michel",
        dimension=W5Dimension.WHY,
        key="motive",
        value="deflect_blame",
        truth=W5TruthLevel.INFERRED,
        source=W5Source.CHARACTER_MIND_RECORD,
    )
    f2 = _fact(
        fact_id="w5f_michel_why_2",
        actor_id="michel",
        dimension=W5Dimension.WHY,
        key="motive",
        value="protect_annette",
        truth=W5TruthLevel.INFERRED,
        source=W5Source.NPC_AGENCY_SIMULATION,
    )
    conflict = W5Conflict(
        conflict_id="w5c_why",
        actor_id="michel",
        dimension=W5Dimension.WHY,
        competing_fact_ids=("w5f_michel_why_1", "w5f_michel_why_2"),
        resolution_status=W5ConflictResolutionStatus.UNRESOLVED,
    )
    result = validate_w5_actor_situation(
        snapshot=_snapshot(_situation("michel", why=(f1, f2)), conflicts=(conflict,)),
        generation=_generation(spoken=[{"speaker_id": "michel", "text": "No."}]),
    )
    assert result["w5_validation_failed"] is False
    assert result["w5_validation_failure_codes"] == []
    assert result["warnings"][0]["code"] == W5ValidationFailureCode.W5_UNRESOLVED_CONFLICT.value
    assert result["warnings"][0]["details"]["dimension"] == "why"


def test_missing_w5_snapshot_records_fallback_without_rejecting(monkeypatch) -> None:
    monkeypatch.setenv("W5_AST_VALIDATION_ENABLED", "true")
    outcome = run_validation_seam(
        module_id=GOC_MODULE_ID,
        proposed_state_effects=_approved_effects(),
        generation=_generation(spoken=[{"speaker_id": "michel", "text": "No."}]),
        w5_latest_snapshot=None,
    )
    assert outcome["status"] == "approved"
    assert outcome["w5_validation"]["w5_validation_ran"] is False
    assert outcome["w5_validation"]["w5_validation_source"] == "legacy_fallback"
    assert outcome["w5_validation"]["w5_validation_fallback_reason"] == "missing_w5_latest_snapshot"


def test_malformed_w5_snapshot_records_fallback_without_rejecting(monkeypatch) -> None:
    monkeypatch.setenv("W5_AST_VALIDATION_ENABLED", "true")
    outcome = run_validation_seam(
        module_id=GOC_MODULE_ID,
        proposed_state_effects=_approved_effects(),
        generation=_generation(spoken=[{"speaker_id": "michel", "text": "No."}]),
        w5_latest_snapshot={"malformed": "snapshot"},
    )
    assert outcome["status"] == "approved"
    assert outcome["w5_validation"]["w5_validation_ran"] is False
    assert outcome["w5_validation"]["w5_validation_source"] == "legacy_fallback"
    assert "snapshot_id" in outcome["w5_validation"]["w5_validation_fallback_reason"]
