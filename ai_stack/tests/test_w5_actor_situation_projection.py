"""Unit tests for the W5 narrator projection builder (ADR-0063 Phase 2).

Covers:

- ``build_w5_projection_for_narrator`` returns a typed ``W5Projection`` whose
  ``target_consumer`` is ``narrator``.
- All five W5 dimensions appear in the projection (who/where/what/how/why).
- ``how_summary`` is first-class and is not folded into ``what_summary``.
- INFERRED ``why.*`` survives as ``truth_level="inferred"`` (via
  ``truth_attribution`` and never as OBSERVED).
- ``source_attribution`` and ``truth_attribution`` are populated.
- The builder accepts both a typed ``W5Snapshot`` and a persisted dict.
- ``where_summary.location_changed`` mirrors the legacy
  ``transition_from_previous.location_changed`` truth: when previous and
  current snapshots disagree on ``scene_location``, the flag is True; when
  they agree, the flag is False.
"""

from __future__ import annotations

import pytest

from ai_stack.actor_situation import (
    W5_PROJECTION_SCHEMA_VERSION,
    W5ActorSituation,
    W5ActorType,
    W5Dimension,
    W5Fact,
    W5FactStatus,
    W5FreshnessStatus,
    W5Projection,
    W5ProjectionConsumer,
    W5Snapshot,
    W5Source,
    W5TruthLevel,
    W5VisibilityScope,
    build_w5_projection_for_director,
    build_w5_projection_for_narrator,
    build_w5_projection_for_npc,
)


TURN = 3
ACTOR = "veronique"


def _fact(
    *,
    fact_id: str,
    actor_id: str = ACTOR,
    dimension: W5Dimension,
    key: str,
    value: object,
    source: W5Source,
    truth: W5TruthLevel,
    visibility: W5VisibilityScope = W5VisibilityScope.PUBLIC,
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
        valid_from_turn=TURN,
        last_confirmed_turn=TURN,
        visibility=visibility,
        status=W5FactStatus.ACTIVE,
        actor_knowledge_scope=actor_knowledge_scope,
    )


def _situation_with_all_dimensions(
    *,
    actor_id: str = ACTOR,
    actor_type: W5ActorType = W5ActorType.HUMAN,
    location: str = "foyer",
    current_action: str = "accuses",
    tone: str = "sharp",
) -> W5ActorSituation:
    where = (
        _fact(
            fact_id="w5f_where_1",
            actor_id=actor_id,
            dimension=W5Dimension.WHERE,
            key="scene_location",
            value=location,
            source=W5Source.PARTICIPANT_STATE_MOVE,
            truth=W5TruthLevel.OBSERVED,
        ),
    )
    what = (
        _fact(
            fact_id="w5f_what_1",
            actor_id=actor_id,
            dimension=W5Dimension.WHAT,
            key="interaction_type",
            value="confrontation",
            source=W5Source.COMMITTED_ACTION,
            truth=W5TruthLevel.OBSERVED,
        ),
        _fact(
            fact_id="w5f_what_2",
            actor_id=actor_id,
            dimension=W5Dimension.WHAT,
            key="current_action",
            value=current_action,
            source=W5Source.COMMITTED_ACTION,
            truth=W5TruthLevel.OBSERVED,
        ),
    )
    how = (
        _fact(
            fact_id="w5f_how_1",
            actor_id=actor_id,
            dimension=W5Dimension.HOW,
            key="tone",
            value=tone,
            source=W5Source.COMMITTED_ACTION,
            truth=W5TruthLevel.OBSERVED,
        ),
        _fact(
            fact_id="w5f_how_2",
            actor_id=actor_id,
            dimension=W5Dimension.HOW,
            key="intensity",
            value="rising",
            source=W5Source.DIRECTOR_COMPOSITION,
            truth=W5TruthLevel.DIRECTOR_ASSIGNED,
        ),
    )
    why = (
        _fact(
            fact_id="w5f_why_1",
            actor_id=actor_id,
            dimension=W5Dimension.WHY,
            key="motive",
            value="defend_son",
            source=W5Source.CHARACTER_MIND_RECORD,
            truth=W5TruthLevel.INFERRED,
            visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
        ),
    )
    return W5ActorSituation(
        actor_id=actor_id,
        actor_type=actor_type,
        actor_role_in_scene="aggressor",
        involvement_type="primary",
        where=where,
        what=what,
        how=how,
        why=why,
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=TURN,
    )


def _snapshot(situation: W5ActorSituation, *, turn: int = TURN) -> W5Snapshot:
    return W5Snapshot(
        snapshot_id=f"w5s_test_{turn}",
        story_session_id="sess_proj_test",
        turn_number=turn,
        created_at=f"w5:turn:{turn}",
        actors={situation.actor_id: situation},
    )


def test_projection_target_consumer_is_narrator() -> None:
    proj = build_w5_projection_for_narrator(_snapshot(_situation_with_all_dimensions()))
    assert isinstance(proj, W5Projection)
    assert proj.target_consumer is W5ProjectionConsumer.NARRATOR
    assert proj.schema_version == W5_PROJECTION_SCHEMA_VERSION


def test_projection_contains_all_five_dimensions_with_semantic_values() -> None:
    proj = build_w5_projection_for_narrator(_snapshot(_situation_with_all_dimensions()))
    assert proj.who_summary["actor_type"] == "human"
    assert proj.who_summary["actor_role_in_scene"] == "aggressor"
    assert proj.where_summary["current_location"] == "foyer"
    assert proj.what_summary["facts"]["interaction_type"] == "confrontation"
    assert proj.what_summary["facts"]["current_action"] == "accuses"
    # how_summary is first-class with its own keys, not folded into what.
    assert proj.how_summary["facts"]["tone"] == "sharp"
    assert proj.how_summary["facts"]["intensity"] == "rising"
    assert "tone" not in proj.what_summary["facts"]
    assert "intensity" not in proj.what_summary["facts"]
    assert proj.why_summary["facts"]["motive"] == "defend_son"


def test_how_summary_is_not_folded_into_what_summary() -> None:
    proj = build_w5_projection_for_narrator(_snapshot(_situation_with_all_dimensions()))
    # How keys must live under how_summary only; what_summary must not absorb them.
    how_keys = set(proj.how_summary.get("facts", {}).keys())
    what_keys = set(proj.what_summary.get("facts", {}).keys())
    assert how_keys, "expected how_summary to have first-class facts"
    assert how_keys.isdisjoint(what_keys)
    # Attribution paths must distinguish how_summary from what_summary.
    assert any(p.startswith("how_summary.facts.") for p in proj.source_attribution)
    assert any(p.startswith("what_summary.facts.") for p in proj.source_attribution)


def test_inferred_why_stays_truth_level_inferred() -> None:
    proj = build_w5_projection_for_narrator(_snapshot(_situation_with_all_dimensions()))
    assert proj.why_summary["facts"]["motive"] == "defend_son"
    assert proj.truth_attribution["why_summary.facts.motive"] == "inferred"
    assert proj.source_attribution["why_summary.facts.motive"] == "character_mind_record"


def test_projection_source_and_truth_attribution_are_populated() -> None:
    proj = build_w5_projection_for_narrator(_snapshot(_situation_with_all_dimensions()))
    # The projection must carry attribution for at least one entry per
    # dimension that the narrator can audit.
    paths = set(proj.source_attribution.keys())
    truths = set(proj.truth_attribution.keys())
    assert "who_summary.actor_type" in paths
    assert "where_summary.facts.scene_location" in paths
    assert "what_summary.facts.interaction_type" in paths
    assert "how_summary.facts.tone" in paths
    assert "why_summary.facts.motive" in paths
    # Every source-attribution path has a matching truth-attribution entry.
    assert paths == truths
    # Truth values are non-empty strings from the closed enum.
    legal = {t.value for t in W5TruthLevel}
    for value in proj.truth_attribution.values():
        assert value in legal


def test_projection_builder_accepts_typed_snapshot_and_persisted_dict() -> None:
    typed = _snapshot(_situation_with_all_dimensions())
    persisted = typed.to_dict()
    proj_typed = build_w5_projection_for_narrator(typed)
    proj_dict = build_w5_projection_for_narrator(persisted)
    # Same projection content regardless of input form.
    assert proj_typed.to_dict() == proj_dict.to_dict()


def test_director_projection_builder_accepts_typed_snapshot_and_persisted_dict() -> None:
    typed = W5Snapshot(
        snapshot_id="w5s_director_multi",
        story_session_id="sess_proj_test",
        turn_number=TURN,
        created_at=f"w5:turn:{TURN}",
        actors={
            "annette": _situation_with_all_dimensions(
                actor_id="annette",
                location="study",
                current_action="listens",
                tone="quiet",
            ),
            "michel": _situation_with_all_dimensions(
                actor_id="michel",
                location="study",
                current_action="objects",
                tone="dry",
            ),
        },
    )
    proj_typed = build_w5_projection_for_director(typed)
    proj_dict = build_w5_projection_for_director(typed.to_dict())
    assert proj_typed.to_dict() == proj_dict.to_dict()
    assert proj_typed.target_consumer is W5ProjectionConsumer.DIRECTOR
    assert proj_typed.where_summary["derived_actor_locations"] == {
        "annette": "study",
        "michel": "study",
    }


def test_director_projection_exposes_compact_actor_where_and_all_w5_dimensions() -> None:
    situation = _situation_with_all_dimensions(actor_id="annette", location="study")
    visibility_fact = _fact(
        fact_id="w5f_where_visibility",
        actor_id="annette",
        dimension=W5Dimension.WHERE,
        key="visibility_audibility",
        value="not_audible",
        source=W5Source.FREE_PLAYER_ACTION_RESOLUTION,
        truth=W5TruthLevel.DECLARED,
    )
    situation = W5ActorSituation(
        actor_id=situation.actor_id,
        actor_type=situation.actor_type,
        actor_role_in_scene=situation.actor_role_in_scene,
        involvement_type=situation.involvement_type,
        where=(*situation.where, visibility_fact),
        what=situation.what,
        how=situation.how,
        why=situation.why,
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=TURN,
    )
    proj = build_w5_projection_for_director(_snapshot(situation))
    assert proj.target_consumer is W5ProjectionConsumer.DIRECTOR
    assert proj.who_summary["actors"]["annette"]["actor_type"] == "human"
    actor_where = proj.where_summary["actors"]["annette"]
    assert actor_where["where"]["scene_location"] == "study"
    assert actor_where["where"]["visibility_audibility"] == "not_audible"
    assert actor_where["freshness_status"] == "fresh"
    assert actor_where["last_confirmed_turn"] == TURN
    assert proj.where_summary["derived_actor_locations"] == {"annette": "study"}
    assert proj.what_summary["actors"]["annette"]["facts"]["current_action"] == "accuses"
    assert proj.how_summary["actors"]["annette"]["facts"]["tone"] == "sharp"
    assert proj.why_summary["actors"]["annette"]["facts"]["motive"] == "defend_son"
    assert (
        proj.source_attribution["where_summary.actors.annette.where.scene_location"]
        == "participant_state_move"
    )
    assert (
        proj.truth_attribution["where_summary.actors.annette.where.visibility_audibility"]
        == "declared"
    )


def test_npc_projection_target_consumer_and_actor_id_match_requested_npc() -> None:
    snap = _snapshot(
        _situation_with_all_dimensions(
            actor_id="michel",
            actor_type=W5ActorType.NPC,
            location="study",
            current_action="deflects",
            tone="dry",
        )
    )
    proj = build_w5_projection_for_npc(snap, actor_id="michel")
    assert proj.target_consumer is W5ProjectionConsumer.NPC
    assert proj.actor_id == "michel"
    assert proj.where_summary["facts"]["scene_location"] == "study"


def test_npc_projection_contains_all_dimensions_and_how_is_first_class() -> None:
    snap = _snapshot(
        _situation_with_all_dimensions(
            actor_id="michel",
            actor_type=W5ActorType.NPC,
            location="study",
            current_action="deflects",
            tone="dry",
        )
    )
    proj = build_w5_projection_for_npc(snap, actor_id="michel")
    assert proj.who_summary["actor_type"] == "npc"
    assert proj.where_summary["facts"]["scene_location"] == "study"
    assert proj.what_summary["facts"]["current_action"] == "deflects"
    assert proj.how_summary["facts"]["tone"] == "dry"
    assert proj.why_summary["facts"]["motive"] == "defend_son"
    assert "tone" not in proj.what_summary["facts"]
    assert proj.truth_attribution["why_summary.facts.motive"] == "inferred"


def test_npc_projection_accepts_typed_snapshot_and_persisted_dict() -> None:
    typed = _snapshot(
        _situation_with_all_dimensions(
            actor_id="michel",
            actor_type=W5ActorType.NPC,
            location="study",
            current_action="deflects",
            tone="dry",
        )
    )
    proj_typed = build_w5_projection_for_npc(typed, actor_id="michel")
    proj_dict = build_w5_projection_for_npc(typed.to_dict(), actor_id="michel")
    assert proj_typed.to_dict() == proj_dict.to_dict()
    assert proj_dict.source_attribution["how_summary.facts.tone"] == "committed_action"
    assert proj_dict.truth_attribution["how_summary.facts.tone"] == "observed"


def test_npc_projection_does_not_expose_other_actor_private_why_without_scope() -> None:
    michel = _situation_with_all_dimensions(
        actor_id="michel",
        actor_type=W5ActorType.NPC,
        location="study",
        current_action="deflects",
        tone="dry",
    )
    alain = _situation_with_all_dimensions(
        actor_id="alain",
        actor_type=W5ActorType.NPC,
        location="study",
        current_action="watches",
        tone="contained",
    )
    snap = W5Snapshot(
        snapshot_id="w5s_npc_privacy",
        story_session_id="sess_proj_test",
        turn_number=TURN,
        created_at=f"w5:turn:{TURN}",
        actors={"michel": michel, "alain": alain},
    )
    proj = build_w5_projection_for_npc(snap, actor_id="michel")
    assert proj.why_summary["facts"]["motive"] == "defend_son"
    assert "known_actors" not in proj.why_summary
    assert "alain" not in repr(proj.why_summary)


def test_npc_projection_exposes_other_npc_private_why_when_scope_allows() -> None:
    michel = _situation_with_all_dimensions(
        actor_id="michel",
        actor_type=W5ActorType.NPC,
        location="study",
        current_action="deflects",
        tone="dry",
    )
    alain_private_why = _fact(
        fact_id="w5f_alain_shared_why",
        actor_id="alain",
        dimension=W5Dimension.WHY,
        key="motive",
        value="protect_annette",
        source=W5Source.CHARACTER_MIND_RECORD,
        truth=W5TruthLevel.INFERRED,
        visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
        actor_knowledge_scope=("michel",),
    )
    alain = W5ActorSituation(
        actor_id="alain",
        actor_type=W5ActorType.NPC,
        where=(
            _fact(
                fact_id="w5f_alain_where",
                actor_id="alain",
                dimension=W5Dimension.WHERE,
                key="scene_location",
                value="study",
                source=W5Source.PARTICIPANT_STATE_MOVE,
                truth=W5TruthLevel.OBSERVED,
            ),
        ),
        why=(alain_private_why,),
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=TURN,
    )
    snap = W5Snapshot(
        snapshot_id="w5s_npc_scope",
        story_session_id="sess_proj_test",
        turn_number=TURN,
        created_at=f"w5:turn:{TURN}",
        actors={"michel": michel, "alain": alain},
    )
    proj = build_w5_projection_for_npc(snap, actor_id="michel")
    assert proj.why_summary["known_actors"]["alain"]["facts"]["motive"] == "protect_annette"
    assert (
        proj.truth_attribution["why_summary.known_actors.alain.facts.motive"]
        == "inferred"
    )


def test_npc_projection_never_leaks_player_private_facts() -> None:
    michel = _situation_with_all_dimensions(
        actor_id="michel",
        actor_type=W5ActorType.NPC,
        location="study",
        current_action="deflects",
        tone="dry",
    )
    player_private_why = _fact(
        fact_id="w5f_annette_private_why",
        actor_id="annette",
        dimension=W5Dimension.WHY,
        key="motive",
        value="hide_pain",
        source=W5Source.CHARACTER_MIND_RECORD,
        truth=W5TruthLevel.INFERRED,
        visibility=W5VisibilityScope.PRIVATE_TO_ACTOR,
        actor_knowledge_scope=("michel",),
    )
    annette = W5ActorSituation(
        actor_id="annette",
        actor_type=W5ActorType.HUMAN,
        why=(player_private_why,),
        freshness_status=W5FreshnessStatus.FRESH,
        last_confirmed_turn=TURN,
    )
    snap = W5Snapshot(
        snapshot_id="w5s_player_private",
        story_session_id="sess_proj_test",
        turn_number=TURN,
        created_at=f"w5:turn:{TURN}",
        actors={"michel": michel, "annette": annette},
    )
    proj = build_w5_projection_for_npc(snap, actor_id="michel")
    assert "known_actors" not in proj.why_summary
    assert "hide_pain" not in repr(proj.to_dict())


def test_projection_centers_requested_actor_not_sorted_fallback() -> None:
    """A multi-actor snapshot must honor the requested narrator actor.

    Without the explicit actor selection, ``alain`` would win sorted fallback
    over ``veronique`` and the narrator would receive the wrong situation.
    """

    alain = _situation_with_all_dimensions(
        actor_id="alain",
        location="foyer",
        current_action="deflects",
        tone="controlled",
    )
    veronique = _situation_with_all_dimensions(
        actor_id="veronique",
        location="parlor",
        current_action="accuses",
        tone="sharp",
    )
    snap = W5Snapshot(
        snapshot_id="w5s_multi_actor",
        story_session_id="sess_proj_test",
        turn_number=TURN,
        created_at=f"w5:turn:{TURN}",
        actors={"alain": alain, "veronique": veronique},
    )
    proj = build_w5_projection_for_narrator(snap, actor_id="veronique")
    assert proj.actor_id == "veronique"
    assert proj.where_summary["current_location"] == "parlor"
    assert proj.what_summary["facts"]["current_action"] == "accuses"
    assert proj.how_summary["facts"]["tone"] == "sharp"


def test_projection_builder_rejects_garbage_input_type() -> None:
    with pytest.raises(TypeError):
        build_w5_projection_for_narrator(object())  # type: ignore[arg-type]


def test_projection_empty_snapshot_returns_safe_defaults() -> None:
    proj = build_w5_projection_for_narrator(None)
    assert proj.target_consumer is W5ProjectionConsumer.NARRATOR
    assert proj.where_summary["location_changed"] is False
    assert proj.who_summary == {}
    assert proj.what_summary == {}
    assert proj.how_summary == {}
    assert proj.why_summary == {}


def test_location_changed_true_when_previous_location_differs() -> None:
    current = _snapshot(_situation_with_all_dimensions(location="parlor"), turn=3)
    previous = _snapshot(_situation_with_all_dimensions(location="foyer"), turn=2)
    proj = build_w5_projection_for_narrator(current, previous_snapshot=previous)
    assert proj.where_summary["current_location"] == "parlor"
    assert proj.where_summary["previous_location"] == "foyer"
    assert proj.where_summary["location_changed"] is True


def test_location_changed_false_when_locations_match() -> None:
    current = _snapshot(_situation_with_all_dimensions(location="foyer"), turn=3)
    previous = _snapshot(_situation_with_all_dimensions(location="foyer"), turn=2)
    proj = build_w5_projection_for_narrator(current, previous_snapshot=previous)
    assert proj.where_summary["current_location"] == "foyer"
    assert proj.where_summary["location_changed"] is False


def test_legacy_location_changed_parity_with_transition_from_previous() -> None:
    """Phase 2 parity: when ``transition_from_previous.location_changed`` is
    True for a turn, ``where_summary.location_changed`` must also be True.
    """

    # Build matching W5 snapshots: previous foyer -> current parlor mirrors
    # the legacy transition flag that prev != current => location_changed True.
    previous = _snapshot(_situation_with_all_dimensions(location="foyer"), turn=2)
    current = _snapshot(_situation_with_all_dimensions(location="parlor"), turn=3)
    legacy_transition_location_changed = True
    proj = build_w5_projection_for_narrator(current, previous_snapshot=previous)
    assert proj.where_summary["location_changed"] == legacy_transition_location_changed


def test_location_changed_parity_with_goc_narrator_path_fixture() -> None:
    from ai_stack.narrator.goc_narrator_path import build_goc_narrator_path_opening

    narrator_path = build_goc_narrator_path_opening(session_output_language="de")
    blocks = [
        block
        for block in narrator_path.get("scene_blocks", [])
        if isinstance(block, dict)
    ]
    transition = next(
        (
            (block.get("source_facts") or {}).get("transition_from_previous")
            for block in blocks
            if isinstance(block.get("source_facts"), dict)
            and (
                (block.get("source_facts") or {}).get("transition_from_previous")
                or {}
            ).get("location_changed")
        ),
        None,
    )
    assert isinstance(transition, dict)
    previous_location = transition["previous_location"]["id"]
    current_location = transition["current_location"]["id"]

    previous = _snapshot(
        _situation_with_all_dimensions(location=previous_location),
        turn=2,
    )
    current = _snapshot(
        _situation_with_all_dimensions(location=current_location),
        turn=3,
    )
    proj = build_w5_projection_for_narrator(current, previous_snapshot=previous)
    assert transition["location_changed"] is True
    assert proj.where_summary["previous_location"] == previous_location
    assert proj.where_summary["current_location"] == current_location
    assert proj.where_summary["location_changed"] is True


def test_projection_does_not_leak_raw_ledger() -> None:
    """Projection must expose compact summaries, not the raw per-fact ledger."""

    proj = build_w5_projection_for_narrator(_snapshot(_situation_with_all_dimensions()))
    payload = proj.to_dict()
    # No giant arrays of W5Fact dicts (those carry fact_id, valid_from_turn etc).
    for key in ("who_summary", "where_summary", "what_summary", "how_summary", "why_summary"):
        section = payload[key]
        # The section is a dict of compact fields; never a list of fact dicts.
        assert isinstance(section, dict)
        # Specifically: no "fact_id" or "valid_from_turn" leaked.
        flat = repr(section)
        assert "fact_id" not in flat
        assert "valid_from_turn" not in flat


def test_observed_why_remains_forbidden_centralized_policy() -> None:
    """Phase 2 keeps OBSERVED why.* forbidden; the rule is centralized in
    ``why_truth_level_is_admitted`` so a future Why-commit ADR can relax it.
    """

    with pytest.raises(ValueError, match="why_truth_level_is_admitted"):
        W5Fact(
            fact_id="w5f_bad_why",
            actor_id=ACTOR,
            dimension=W5Dimension.WHY,
            key="motive",
            value="x",
            source=W5Source.COMMITTED_ACTION,
            truth_level=W5TruthLevel.OBSERVED,
            valid_from_turn=TURN,
            last_confirmed_turn=TURN,
            visibility=W5VisibilityScope.PUBLIC,
            status=W5FactStatus.ACTIVE,
        )
